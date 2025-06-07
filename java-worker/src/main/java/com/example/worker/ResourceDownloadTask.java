package com.example.worker;

import java.util.UUID;

public record ResourceDownloadTask(UUID taskId, String userId, ResourceDownloadRequest request) {
}
