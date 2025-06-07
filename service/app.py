# app/services.py
"""
Utility helpers for the worker and FastAPI service.

Handles DynamoDB task updates, S3 uploads/checks and SQS message
acknowledgement. All configuration is taken from environment variables.
"""

import os
import time
import logging
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

# ---- Environment configuration ---------------------------------------------

AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
QUEUE_URL = os.getenv("RESOURCE_QUEUE_URL")
TABLE_NAME = os.getenv("TASK_STATE_TABLE")

S3_ENDPOINT = os.getenv("S3_ENDPOINT_URL")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY_ID")
S3_SECRET_KEY = os.getenv("S3_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
S3_REGION = os.getenv("S3_REGION_NAME", "ru-central1")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---- AWS clients -----------------------------------------------------------

sqs_client = boto3.client("sqs", region_name=AWS_REGION)

ddb_client = boto3.client("dynamodb", region_name=AWS_REGION)

s3_client = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=S3_REGION,
)

# ---- DynamoDB helpers ------------------------------------------------------


def update_status(task_id: str, status: str, extra: Optional[dict] = None) -> None:
    """
    Update status and other attributes for a task in DynamoDB.

    Parameters
    ----------
    task_id : str
        Identifier of the task.
    status : str
        New status value (PENDING, IN_PROGRESS, COMPLETED, FAILED).
    extra : dict, optional
        Additional attributes to store alongside the status.
    """
    expr = "SET #s=:s, lastModified=:t"
    values = {":s": {"S": status}, ":t": {"N": str(int(time.time()))}}
    names = {"#s": "status"}

    if extra:
        for key, val in extra.items():
            expr += f", {key}=:{key}"
            values[f":{key}"] = {"S": str(val)}

    logger.info("Updating task %s status to %s", task_id, status)
    ddb_client.update_item(
        TableName=TABLE_NAME,
        Key={"taskId": {"S": task_id}},
        UpdateExpression=expr,
        ExpressionAttributeValues=values,
        ExpressionAttributeNames=names,
    )


def complete_task(task_id: str, main_key: str, license_key: Optional[str]) -> None:
    """
    Mark task COMPLETED and store resulting S3 keys.

    Parameters
    ----------
    task_id : str
        Identifier of the task.
    main_key : str
        S3 key of the main file.
    license_key : str | None
        S3 key of the license file if present.
    """
    extra = {"mainKey": main_key}
    if license_key:
        extra["licenseKey"] = license_key
    update_status(task_id, "COMPLETED", extra)


def fail_task(task_id: str, error_message: str) -> None:
    """Mark task FAILED with an error description."""
    update_status(task_id, "FAILED", {"error": error_message})


# ---- S3 helpers ------------------------------------------------------------


def asset_in_cache(asset_id: str) -> bool:
    """
    Check whether the given asset already exists in the bucket.

    The worker considers an asset present if the object `<asset_id>/main`
    exists in the bucket. License file presence is optional.
    """
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=f"{asset_id}/main")
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "404":
            return False
        raise


def upload_file(local_path: str, s3_key: str) -> str:
    """Upload a file to S3 and return the S3 key that was used."""
    s3_client.upload_file(local_path, S3_BUCKET, s3_key)
    logger.info("Uploaded %s to s3://%s/%s", local_path, S3_BUCKET, s3_key)
    return s3_key


# ---- SQS helper ------------------------------------------------------------


def delete_message(receipt_handle: str) -> None:
    """Delete a processed message from the SQS queue."""
    sqs_client.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)
