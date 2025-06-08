import os
import json
import time
import logging
from typing import Dict
from urllib.parse import urlparse

import boto3
import httpx
from dotenv import load_dotenv

load_dotenv()

# Проверка обязательных переменных
SQS_QUEUE_URL = os.getenv('RESOURCE_QUEUE_URL')
DDB_TABLE = os.getenv('TASK_STATE_TABLE')
if not DDB_TABLE:
    raise RuntimeError("TASK_STATE_TABLE не задана в .env")
if not SQS_QUEUE_URL:
    raise RuntimeError("RESOURCE_QUEUE_URL не задана в .env")

SERVICE_URL = os.getenv('PY_SERVICE_URL', 'http://localhost:8000/process')
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
AWS_REGION = os.getenv('AWS_REGION', 'eu-central-1')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('worker')

# Инициализация AWS клиентов
sqs = boto3.client('sqs', region_name=AWS_REGION)
ddb_resource = boto3.resource('dynamodb', region_name=AWS_REGION)
table = ddb_resource.Table(DDB_TABLE)
s3 = boto3.client('s3',
                   endpoint_url=os.getenv('S3_ENDPOINT_URL'),
                   aws_access_key_id=os.getenv('S3_ACCESS_KEY_ID'),
                   aws_secret_access_key=os.getenv('S3_SECRET_ACCESS_KEY'),
                   region_name=os.getenv('S3_REGION_NAME', 'us-east-1'))
S3_BUCKET = os.getenv('S3_BUCKET_NAME')

def update_status(task_id: str, status: str, extra: Dict | None = None):
    expr = 'SET #s=:s, lastModified=:t'
    values = {':s': status, ':t': int(time.time())}
    names = {'#s': 'status'}
    if extra:
        for k, v in extra.items():
            expr += f', {k}=:{k}'
            values[f':{k}'] = v
    table.update_item(Key={'taskId': task_id}, UpdateExpression=expr, ExpressionAttributeValues=values, ExpressionAttributeNames=names)


def complete_task(task_id: str, main_key: str, license_key: str | None):
    update_status(task_id, 'COMPLETED', {'mainKey': main_key, 'licenseKey': license_key})


def fail_task(task_id: str, error: str):
    update_status(task_id, 'FAILED', {'error': error})


def extract_asset_id(url: str) -> str:
    parsed = urlparse(url)
    name = os.path.basename(parsed.path.rstrip('/'))
    name = name.split('?')[0]
    return name


def asset_in_cache(asset_id: str) -> bool:
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=f"{asset_id}/main")
        return True
    except s3.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise


def process_task(task_id: str, link: str):
    asset_id = extract_asset_id(link)

    if asset_in_cache(asset_id):
        logger.info('Asset %s already in cache', asset_id)
        complete_task(task_id, f"{asset_id}/main", f"{asset_id}/license")
        return

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = httpx.post(SERVICE_URL, json={'task_id': task_id, 'url': link}, timeout=600)
            resp.raise_for_status()
            data = resp.json()
            complete_task(task_id, data['mainFileKey'], data.get('licenseFileKey'))
            logger.info('Task %s completed', task_id)
            return
        except Exception as e:
            logger.error('Attempt %s failed for task %s: %s', attempt, task_id, e)
            if attempt == MAX_RETRIES:
                fail_task(task_id, str(e))
                logger.error('Task %s failed after retries', task_id)
            else:
                time.sleep(5 * attempt)


def main():
    while True:
        msgs = sqs.receive_message(QueueUrl=SQS_QUEUE_URL, MaxNumberOfMessages=1, WaitTimeSeconds=20).get('Messages', [])
        if not msgs:
            continue
        for m in msgs:
            receipt = m['ReceiptHandle']
            body = json.loads(m['Body'])
            task = body.get('taskId')
            req = body.get('request', {})
            link = req.get('link')
            if not task or not link:
                sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt)
                continue
            item = table.get_item(Key={'taskId': task}).get('Item')
            if not item or item.get('status') != 'PENDING':
                sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt)
                continue
            update_status(task, 'IN_PROGRESS')
            process_task(task, link)
            sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt)

if __name__ == '__main__':
    main()
