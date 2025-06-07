# Chim Bot Integration Example

This repository contains a simplified example of integrating a Telegram
processing service with an AWS SQS queue and DynamoDB table. It consists of two
components written in Python:

* `service/` – a FastAPI application that communicates with a Telegram bot,
  downloads the resulting files, and uploads them to a configured S3 bucket.
* `worker/` – a small worker that polls an SQS queue for tasks, updates their
  status in DynamoDB, and calls the FastAPI service.

## Service

The applications read configuration from environment variables (you can copy
`.env.example` to `.env` and adjust values). Environment variables required:

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

`PORT` can be set to specify the listening port (default 8000).

## Worker

Environment variables required:

```
RESOURCE_QUEUE_URL   # SQS queue URL
TASK_STATE_TABLE     # DynamoDB table name
PY_SERVICE_URL       # URL of the FastAPI service (default http://localhost:8000/process)
AWS_REGION           # AWS region for SQS and DynamoDB
S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_BUCKET_NAME
S3_REGION_NAME
MAX_RETRIES        # number of attempts before marking a task FAILED (default 3)
```

Copy `.env.example` to `.env` in the project root and set these variables before
running the worker.

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
