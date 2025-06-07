package com.example.worker;

import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.HeadObjectRequest;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;

public class S3CacheService {
    private final S3Client s3;
    private final String bucket;

    public S3CacheService(S3Client s3, String bucket) {
        this.s3 = s3;
        this.bucket = bucket;
    }

    public boolean isAssetInCache(String assetId) {
        try {
            s3.headObject(HeadObjectRequest.builder().bucket(bucket).key(assetId + "/main").build());
            return true;
        } catch (NoSuchKeyException e) {
            return false;
        } catch (Exception e) {
            // treat other errors as not cached
            return false;
        }
    }
}
