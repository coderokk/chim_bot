package com.example.worker;

import java.util.UUID;
import com.fasterxml.jackson.annotation.JsonProperty;

public class ResourceDownloadTask {
    @JsonProperty("taskId")
    private UUID taskId;
    @JsonProperty("request")
    private ResourceDownloadRequest request;

    public UUID getTaskId() { return taskId; }
    public void setTaskId(UUID taskId) { this.taskId = taskId; }
    public ResourceDownloadRequest getRequest() { return request; }
    public void setRequest(ResourceDownloadRequest request) { this.request = request; }
    
    public String getUrl() { return request.getLink(); }
    public String getName() { 
        String[] parts = request.getLink().split("/");
        return parts[parts.length-1].split("\\?")[0];
    }
    public String getAssetId() { return getName(); }
}

class ResourceDownloadRequest {
    @JsonProperty("link")
    private String link;
    public String getLink() { return link; }
    public void setLink(String link) { this.link = link; }
}
