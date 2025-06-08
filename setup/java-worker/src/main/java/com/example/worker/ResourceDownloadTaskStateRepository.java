package com.example.worker;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import software.amazon.awssdk.enhanced.dynamodb.*;
import software.amazon.awssdk.enhanced.dynamodb.model.*;

public class ResourceDownloadTaskStateRepository {
    private final DynamoDbTable<TaskState> table;

    public ResourceDownloadTaskStateRepository(DynamoDbEnhancedClient enhanced, String tableName) {
        this.table = enhanced.table(tableName, TableSchema.fromBean(TaskState.class));
    }

    public Optional<TaskState> findById(String taskId) {
        return Optional.ofNullable(table.getItem(Key.builder().partitionValue(taskId).build()));
    }

    public void save(TaskState s) {
        s.setLastModified(Instant.now());
        table.putItem(s);
    }

    public void updateStatus(UUID taskId, TaskStatus status) {
        TaskState update = new TaskState();
        update.setTaskId(taskId.toString());
        update.setStatus(status);
        update.setLastModified(Instant.now());
        table.updateItem(r -> r.item(update));
    }

    public void updateTaskCompleted(UUID taskId, String mainUrl, String licenseUrl, String phone) {
        TaskState update = new TaskState();
        update.setTaskId(taskId.toString());
        update.setStatus(TaskStatus.COMPLETED);
        update.setMainFileUrl(mainUrl);
        update.setLicenseFileUrl(licenseUrl);
        update.setAccountPhone(phone);
        update.setLastModified(Instant.now());
        table.updateItem(r -> r.item(update));
    }
}
