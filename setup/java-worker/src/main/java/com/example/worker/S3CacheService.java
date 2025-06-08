package com.example.worker;

import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.*;

public class S3CacheService {
    private final S3Client s3;
    private final String bucket;

    public S3CacheService(S3Client s3, String bucket) {
        this.s3 = s3;
        this.bucket = bucket;
    }

    public boolean isAssetCached(String assetId) {
        try {
            s3.headObject(HeadObjectRequest.builder()
                .bucket(bucket)
                .key(assetId + "/main")
                .build());
            return true;
        } catch (S3Exception e) {
            if (e.statusCode() == 404) return false;
            throw e;
        }
    }

    public String getPublicUrl(String assetId, String fileType) {
        // прямой S3 URL; для прейсайна использовать S3Presigner
        return String.format("https://%s.s3.%s.amazonaws.com/%s/%s",
            bucket, s3.region(), assetId, fileType);
    }
}
