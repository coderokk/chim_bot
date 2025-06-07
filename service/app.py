import os
import uuid
import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from telethon import TelegramClient
from telethon.sessions import StringSession
import httpx
import boto3
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH')
SESSION_STRING = os.getenv('SESSION_STRING')
BOT_USERNAME = os.getenv('TARGET_BOT_USERNAME', '@sp_envato_bot')
S3_ENDPOINT = os.getenv('S3_ENDPOINT_URL')
S3_ACCESS = os.getenv('S3_ACCESS_KEY_ID')
S3_SECRET = os.getenv('S3_SECRET_ACCESS_KEY')
S3_BUCKET = os.getenv('S3_BUCKET_NAME')
S3_REGION = os.getenv('S3_REGION_NAME', 'us-east-1')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not all([API_ID, API_HASH, SESSION_STRING]):
    logger.error('Telegram credentials missing')
    raise SystemExit('Telegram credentials missing')

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

s3_client = boto3.client(
    's3',
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS,
    aws_secret_access_key=S3_SECRET,
    region_name=S3_REGION,
)

app = FastAPI()


class ProcessRequest(BaseModel):
    task_id: str
    url: HttpUrl


def extract_asset_id(url: str) -> str:
    parsed = urlparse(url)
    name = os.path.basename(parsed.path.rstrip('/'))
    name = name.split('?')[0]
    return name or uuid.uuid4().hex


async def wait_for_links(task_id: str, url: str) -> tuple[str, Optional[str]]:
    await client.connect()
    message = await client.send_message(BOT_USERNAME, f"{url}?taskid={task_id}")
    main_link = None
    license_link = None
    async for resp in client.iter_messages(BOT_USERNAME, min_id=message.id):
        text = resp.text or ""
        if 'исходники успешно получены' in text.lower():
            main_link = resp.reply_markup.rows[0].buttons[0].url if resp.reply_markup else None
        if 'лицензия успешно скачана' in text.lower():
            license_link = resp.reply_markup.rows[0].buttons[0].url if resp.reply_markup else None
        if main_link:
            break
    if not main_link:
        raise ValueError('Main file link not received')
    return main_link, license_link


async def download_to_tmp(url: str, prefix: str) -> str:
    fname = f"{prefix}_{uuid.uuid4().hex}"
    os.makedirs('tmp', exist_ok=True)
    path = os.path.join('tmp', fname)
    async with httpx.AsyncClient(timeout=300) as client_http:
        resp = await client_http.get(url)
        resp.raise_for_status()
        with open(path, 'wb') as f:
            f.write(resp.content)
    return path


def upload_to_s3(path: str, object_name: str) -> str:
    s3_client.upload_file(path, S3_BUCKET, object_name)
    return object_name


@app.post('/process')
async def process(req: ProcessRequest):
    try:
        main_link, license_link = await wait_for_links(req.task_id, str(req.url))
        asset_id = extract_asset_id(str(req.url))
        main_path = await download_to_tmp(main_link, 'main')
        main_key = upload_to_s3(main_path, f"{asset_id}/main")
        license_key = None
        if license_link:
            license_path = await download_to_tmp(license_link, 'lic')
            license_key = upload_to_s3(license_path, f"{asset_id}/license")
        return {
            'taskId': req.task_id,
            'mainFileKey': main_key,
            'licenseFileKey': license_key,
        }
    except Exception as e:
        logger.exception('Processing failed')
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.getenv('PORT', '8000')))
