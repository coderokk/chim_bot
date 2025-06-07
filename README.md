# Chim Bot Integration Example

This repository contains a simplified example of integrating a Telegram
processing service with an AWS SQS queue and DynamoDB table. It consists of two


```
API_ID, API_HASH, SESSION_STRING      # Telegram credentials
S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_BUCKET_NAME
S3_REGION_NAME                        # S3 region
TARGET_BOT_USERNAME                   # Telegram bot username
```

Run with:

```
cd service
pip install -r requirements.txt
python app.py
```


## Worker

Environment variables required:

```
RESOURCE_QUEUE_URL   # SQS queue URL
TASK_STATE_TABLE     # DynamoDB table name
PY_SERVICE_URL       # URL of the FastAPI service (default http://localhost:8000/process)
AWS_REGION           # AWS region for SQS and DynamoDB
S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_BUCKET_NAME
S3_REGION_NAME

Run with:

```
cd worker
pip install -r requirements.txt
python main.py
```

This code is a minimal working example and may require further adjustments for
production usage. The worker checks Yandex S3 for existing assets before
invoking the Telegram service. If files are already present, the task is marked
`COMPLETED` immediately.

