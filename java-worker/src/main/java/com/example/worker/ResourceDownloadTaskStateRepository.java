package com.example.worker;

import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.DynamoDbEnhancedClient;
import software.amazon.awssdk.services.dynamodb.TableSchema;
import software.amazon.awssdk.services.dynamodb.model.AttributeAction;
import software.amazon.awssdk.services.dynamodb.model.AttributeValue;
import software.amazon.awssdk.services.dynamodb.model.AttributeValueUpdate;
import software.amazon.awssdk.services.dynamodb.model.KeyType;
import software.amazon.awssdk.services.dynamodb.model.KeySchemaElement;
import software.amazon.awssdk.services.dynamodb.model.UpdateItemRequest;
import software.amazon.awssdk.enhanced.dynamodb.DynamoDbTable;
import software.amazon.awssdk.enhanced.dynamodb.Key;
import software.amazon.awssdk.enhanced.dynamodb.model.PutItemEnhancedRequest;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

public class ResourceDownloadTaskStateRepository {
    private final String tableName;
    private final DynamoDbClient client;
    private final DynamoDbEnhancedClient enhancedClient;
    private final DynamoDbTable<TaskState> table;

    public ResourceDownloadTaskStateRepository(DynamoDbClient client, DynamoDbEnhancedClient enhancedClient, String tableName) {
        this.client = client;
        this.enhancedClient = enhancedClient;
        this.tableName = tableName;
        this.table = enhancedClient.table(tableName, TableSchema.fromBean(TaskState.class));
    }

    public Optional<TaskState> findById(String taskId) {
        var key = Key.builder().partitionValue(taskId).build();
        TaskState item = table.getItem(key);
        return Optional.ofNullable(item);
    }

    public void save(TaskState state) {
        state.setLastModified(Instant.now());
        var req = PutItemEnhancedRequest.builder(TaskState.class).item(state).build();
        table.putItem(req);
    }

    public void updateStatus(UUID taskId, TaskStatus status) {
        Map<String, AttributeValue> itemKey = new HashMap<>();
        itemKey.put("taskId", AttributeValue.builder().s(taskId.toString()).build());

        Map<String, AttributeValueUpdate> updatedValues = new HashMap<>();
        updatedValues.put("status", AttributeValueUpdate.builder()
                .value(AttributeValue.builder().s(status.toString()).build())
                .action(AttributeAction.PUT)
                .build());
        updatedValues.put("lastModified", AttributeValueUpdate.builder()
                .value(AttributeValue.builder().n(Long.toString(Instant.now().getEpochSecond())).build())
                .action(AttributeAction.PUT)
                .build());

        var request = UpdateItemRequest.builder()
                .tableName(tableName)
                .key(itemKey)
                .attributeUpdates(updatedValues)
                .build();
        client.updateItem(request);
    }
}
