package com.example.worker;

import com.fasterxml.jackson.databind.ObjectMapper;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.DynamoDbEnhancedClient;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.sqs.SqsClient;
import software.amazon.awssdk.services.sqs.model.DeleteMessageRequest;
import software.amazon.awssdk.services.sqs.model.ReceiveMessageRequest;

import java.net.URI;
import java.net.URL;
import java.time.Duration;
import java.util.List;
import java.util.UUID;

public class WorkerApplication {
    private final SqsClient sqs;
    private final String queueUrl;
    private final ResourceDownloadTaskStateRepository repository;
    private final S3CacheService cacheService;
    private final String serviceUrl;
    private final int maxRetries;
    private final ObjectMapper mapper = new ObjectMapper();

    public WorkerApplication(SqsClient sqs, String queueUrl, ResourceDownloadTaskStateRepository repository,
                             S3CacheService cacheService, String serviceUrl, int maxRetries) {
        this.sqs = sqs;
        this.queueUrl = queueUrl;
        this.repository = repository;
        this.cacheService = cacheService;
        this.serviceUrl = serviceUrl;
        this.maxRetries = maxRetries;
    }

    public void poll() throws Exception {
        while (true) {
            var msgs = sqs.receiveMessage(ReceiveMessageRequest.builder()
                    .queueUrl(queueUrl)
                    .waitTimeSeconds(20)
                    .maxNumberOfMessages(1)
                    .build()).messages();
            if (msgs == null || msgs.isEmpty()) {
                continue;
            }

            msgs.forEach(msg -> {
                try {
                    processMessage(msg.body());
                } catch (Exception e) {
                    e.printStackTrace();
                } finally {
                    sqs.deleteMessage(DeleteMessageRequest.builder()
                            .queueUrl(queueUrl)
                            .receiptHandle(msg.receiptHandle())
                            .build());
                }
            });
        }
    }

    private void processMessage(String body) throws Exception {
        ResourceDownloadTask task = mapper.readValue(body, ResourceDownloadTask.class);
        UUID taskId = task.taskId();
        repository.findById(taskId.toString()).ifPresentOrElse(state -> {
            if (state.getStatus() != TaskStatus.PENDING) {
                return; // ignore
            }
        }, () -> {
            // task not found -> ignore
            return;
        });

        repository.updateStatus(taskId, TaskStatus.IN_PROGRESS);
        String assetId = extractAssetId(task.request().link());
        if (cacheService.isAssetInCache(assetId)) {
            repository.updateStatus(taskId, TaskStatus.COMPLETED);
            return;
        }

        int attempt = 0;
        boolean success = false;
        Exception lastErr = null;
        while (attempt < maxRetries && !success) {
            attempt++;
            try {
                URL postUrl = new URL(serviceUrl);
                var http = java.net.http.HttpClient.newBuilder()
                        .connectTimeout(Duration.ofSeconds(30))
                        .build();
                var req = java.net.http.HttpRequest.newBuilder(postUrl.toURI())
                        .timeout(Duration.ofMinutes(10))
                        .header("Content-Type", "application/json")
                        .POST(java.net.http.HttpRequest.BodyPublishers.ofString(
                                mapper.writeValueAsString(
                                        new java.util.HashMap<String,Object>(){{
                                            put("task_id", taskId.toString());
                                            put("url", task.request().link().toString());
                                        }}
                                )
                        ))
                        .build();
                var resp = http.send(req, java.net.http.HttpResponse.BodyHandlers.ofString());
                if (resp.statusCode() >= 200 && resp.statusCode() < 300) {
                    success = true;
                    repository.updateStatus(taskId, TaskStatus.COMPLETED);
                } else {
                    lastErr = new RuntimeException("HTTP " + resp.statusCode());
                }
            } catch (Exception e) {
                lastErr = e;
            }
        }
        if (!success) {
            repository.updateStatus(taskId, TaskStatus.FAILED);
            if (lastErr != null) {
                System.err.println("Task " + taskId + " failed: " + lastErr.getMessage());
            }
        }
    }

    private static String extractAssetId(URL url) {
        String path = url.getPath();
        String name = path.substring(path.lastIndexOf('/') + 1);
        int q = name.indexOf('?');
        if (q >= 0) name = name.substring(0, q);
        return name;
    }

    public static void main(String[] args) throws Exception {
        String queueUrl = System.getenv("RESOURCE_QUEUE_URL");
        String tableName = System.getenv("TASK_STATE_TABLE");
        String serviceUrl = System.getenv("PY_SERVICE_URL");
        String region = System.getenv("AWS_REGION");
        int retries = Integer.parseInt(System.getenv().getOrDefault("MAX_RETRIES", "3"));

        String accessKey = System.getenv("S3_ACCESS_KEY_ID");
        String secretKey = System.getenv("S3_SECRET_ACCESS_KEY");
        String s3Endpoint = System.getenv("S3_ENDPOINT_URL");
        String bucket = System.getenv("S3_BUCKET_NAME");

        var creds = StaticCredentialsProvider.create(AwsBasicCredentials.create(accessKey, secretKey));
        Region awsRegion = Region.of(region);

        DynamoDbClient ddb = DynamoDbClient.builder().region(awsRegion).credentialsProvider(creds).build();
        DynamoDbEnhancedClient enhanced = DynamoDbEnhancedClient.builder().dynamoDbClient(ddb).build();
        SqsClient sqs = SqsClient.builder().region(awsRegion).credentialsProvider(creds).build();
        S3Client s3 = S3Client.builder().region(awsRegion).credentialsProvider(creds)
                .endpointOverride(URI.create(s3Endpoint)).build();

        ResourceDownloadTaskStateRepository repo = new ResourceDownloadTaskStateRepository(ddb, enhanced, tableName);
        S3CacheService cacheService = new S3CacheService(s3, bucket);
        WorkerApplication app = new WorkerApplication(sqs, queueUrl, repo, cacheService, serviceUrl, retries);
        app.poll();
    }
}
