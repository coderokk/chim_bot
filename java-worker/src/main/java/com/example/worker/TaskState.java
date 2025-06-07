package com.example.worker;

import java.time.Instant;
import java.util.UUID;

public class TaskState {
    private UUID taskId;
    private String name;
    private String data;
    private TaskStatus status;
    private String mainKey;
    private String licenseKey;
    private Instant lastModified;

    public UUID getTaskId() { return taskId; }
    public void setTaskId(UUID taskId) { this.taskId = taskId; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getData() { return data; }
    public void setData(String data) { this.data = data; }

    public TaskStatus getStatus() { return status; }
    public void setStatus(TaskStatus status) { this.status = status; }

    public String getMainKey() { return mainKey; }
    public void setMainKey(String mainKey) { this.mainKey = mainKey; }

    public String getLicenseKey() { return licenseKey; }
    public void setLicenseKey(String licenseKey) { this.licenseKey = licenseKey; }

    public Instant getLastModified() { return lastModified; }
    public void setLastModified(Instant lastModified) { this.lastModified = lastModified; }
}
