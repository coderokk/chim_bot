package com.example.worker;

import java.time.Instant;
import software.amazon.awssdk.enhanced.dynamodb.mapper.annotations.*;

@DynamoDbBean
public class TaskState {
    private String taskId, name, data;
    private TaskStatus status;
    private String mainFileUrl, licenseFileUrl, accountPhone;
    private Instant lastModified;

    @DynamoDbPartitionKey
    public String getTaskId() { return taskId; }
    public void setTaskId(String taskId) { this.taskId = taskId; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getData() { return data; }
    public void setData(String data) { this.data = data; }

    public TaskStatus getStatus() { return status; }
    public void setStatus(TaskStatus status) { this.status = status; }

    public String getMainFileUrl() { return mainFileUrl; }
    public void setMainFileUrl(String mainFileUrl) { this.mainFileUrl = mainFileUrl; }

    public String getLicenseFileUrl() { return licenseFileUrl; }
    public void setLicenseFileUrl(String licenseFileUrl) { this.licenseFileUrl = licenseFileUrl; }

    public String getAccountPhone() { return accountPhone; }
    public void setAccountPhone(String accountPhone) { this.accountPhone = accountPhone; }

    public Instant getLastModified() { return lastModified; }
    public void setLastModified(Instant lastModified) { this.lastModified = lastModified; }
}
