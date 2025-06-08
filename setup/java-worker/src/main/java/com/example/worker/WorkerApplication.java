package com.example.worker;

import com.fasterxml.jackson.databind.ObjectMapper;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.DynamoDbEnhancedClient;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.sqs.SqsClient;
import software.amazon.awssdk.services.sqs.model.*;

import java.net.URI;
import java.net.URL;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

public class WorkerApplication {
    private final SqsClient sqs;
    private final String queueUrl;
    private final ResourceDownloadTaskStateRepository repo;
    private final S3CacheService cache;
    private final String pythonServiceUrl;
    private final int maxRetries;
    private final ObjectMapper mapper = new ObjectMapper();
    private final HttpClient http = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(30))
        .build();

    public WorkerApplication(
        SqsClient sqs,
        String queueUrl,
        ResourceDownloadTaskStateRepository repo,
        S3CacheService cache,
        String pythonServiceUrl,
        int maxRetries
    ) {
        this.sqs = sqs;
        this.queueUrl = queueUrl;
        this.repo = repo;
        this.cache = cache;
        this.pythonServiceUrl = pythonServiceUrl;
        this.maxRetries = maxRetries;
    }

    public void poll() {
        while (true) {
            ReceiveMessageResponse resp = sqs.receiveMessage(r -> r
                .queueUrl(queueUrl)
                .waitTimeSeconds(20)
                .maxNumberOfMessages(1)
            );
            for (Message msg : resp.messages()) {
                handle(msg);
            }
        }
    }

    private void handle(Message msg) {
        String rcpt = msg.receiptHandle();
        try {
            ResourceDownloadTask task = mapper.readValue(msg.body(), ResourceDownloadTask.class);
            String id = task.getTaskId().toString();

            Optional<TaskState> st = repo.findById(id);
            // если уже не PENDING → ACK и skip
            if (st.isPresent() && st.get().getStatus() != TaskStatus.PENDING) {
                delete(rcpt);
                return;
            }
            // иначе, если нет — сохраняем PENDING
            if (st.isEmpty()) {
                TaskState init = new TaskState();
                init.setTaskId(id);
                init.setName(task.getName());
                init.setData(task.getUrl());
                init.setStatus(TaskStatus.PENDING);
                repo.save(init);
            }

            // IN_PROGRESS
            repo.updateStatus(task.getTaskId(), TaskStatus.IN_PROGRESS);

            // process
            processTask(task, rcpt);
        } catch (Exception e) {
            e.printStackTrace(); // дадим SQS вручную вернуть сообщение
        }
    }

    private void processTask(ResourceDownloadTask task, String rcpt) {
        String id = task.getTaskId().toString();
        String assetId = task.getAssetId();

        // 1) cache-hit?
        if (cache.isAssetCached(assetId)) {
            String url = cache.getPublicUrl(assetId, "main");
            repo.updateTaskCompleted(task.getTaskId(), url, null, "");
            delete(rcpt);
            return;
        }

        // 2) call Python service
        ProcessResponse pr = null;
        Exception last = null;
        for (int i = 1; i <= maxRetries; i++) {
            try {
                String body = mapper.writeValueAsString(Map.of(
                    "task_id", id,
                    "url", task.getUrl()
                ));
                HttpRequest request = HttpRequest.newBuilder(URI.create(pythonServiceUrl))
                    .timeout(Duration.ofMinutes(5))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .build();
                HttpResponse<String> resp = http.send(request, HttpResponse.BodyHandlers.ofString());
                if (resp.statusCode() / 100 == 2) {
                    pr = mapper.readValue(resp.body(), ProcessResponse.class);
                    break;
                } else {
                    last = new RuntimeException("HTTP " + resp.statusCode());
                }
            } catch (Exception e) {
                last = e;
            }
        }

        if (pr != null) {
            // success
            repo.updateTaskCompleted(
                task.getTaskId(),
                pr.getMainFileUrl(),
                pr.getLicenseFileUrl(),
                pr.getAccountPhone()
            );
            delete(rcpt);
        } else {
            // fail
            repo.updateStatus(task.getTaskId(), TaskStatus.FAILED);
            delete(rcpt);
            last.printStackTrace();
        }
    }

    private void delete(String rcpt) {
        sqs.deleteMessage(r -> r.queueUrl(queueUrl).receiptHandle(rcpt));
    }

    public static void main(String[] args) {
        String queueUrl    = System.getenv("RESOURCE_QUEUE_URL");
        String table       = System.getenv("TASK_STATE_TABLE");
        String pyService   = System.getenv("PY_SERVICE_URL");
        String region      = System.getenv("AWS_REGION");
        int retries        = Integer.parseInt(System.getenv().getOrDefault("MAX_RETRIES","3"));
        String accessKey   = System.getenv("AWS_ACCESS_KEY_ID");
        String secretKey   = System.getenv("AWS_SECRET_ACCESS_KEY");
        String s3Endpoint  = System.getenv("S3_ENDPOINT_URL");
        String bucket      = System.getenv("S3_BUCKET_NAME");

        var creds = StaticCredentialsProvider.create(
            AwsBasicCredentials.create(accessKey, secretKey)
        );
        Region r = Region.of(region);
        DynamoDbClient     ddb = DynamoDbClient.builder().region(r).credentialsProvider(creds).build();
        DynamoDbEnhancedClient enc = DynamoDbEnhancedClient.builder().dynamoDbClient(ddb).build();
        SqsClient          sqs = SqsClient.builder().region(r).credentialsProvider(creds).build();
        S3Client           s3  = S3Client.builder().region(r).credentialsProvider(creds)
            .endpointOverride(URI.create(s3Endpoint)).build();

        ResourceDownloadTaskStateRepository repo = new ResourceDownloadTaskStateRepository(enc, table);
        S3CacheService cache = new S3CacheService(s3, bucket);

        new WorkerApplication(sqs, queueUrl, repo, cache, pyService, retries).poll();
    }
}
