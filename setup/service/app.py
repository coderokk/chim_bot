import os
import time
import logging
import asyncio
import re
from typing import Optional, Tuple

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- Настройка и логгер ---
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("service")

APP = FastAPI()

# --- Конфигурация из .env ---
AWS_REGION           = os.getenv("AWS_REGION", "eu-central-1")
TABLE_NAME           = os.getenv("TASK_STATE_TABLE")
S3_ENDPOINT          = os.getenv("S3_ENDPOINT_URL")
S3_ACCESS_KEY        = os.getenv("S3_ACCESS_KEY_ID")
S3_SECRET_KEY        = os.getenv("S3_SECRET_ACCESS_KEY")
S3_BUCKET            = os.getenv("S3_BUCKET_NAME")
S3_PUBLIC_BASE_URL   = os.getenv("S3_PUBLIC_BASE_URL", "").rstrip('/')
API_ID               = int(os.getenv("API_ID"))
API_HASH             = os.getenv("API_HASH")
SESSION_STRINGS_FILE = os.getenv("SESSIONS_FILE_PATH", "sessions.json")
MAX_BOT_RETRIES      = int(os.getenv("MAX_BOT_RETRIES", "3"))
RETRY_BACKOFF_SECONDS= int(os.getenv("RETRY_BACKOFF_SECONDS", "5"))

# --- AWS-клиенты ---
ddb = boto3.client("dynamodb", region_name=AWS_REGION)
s3  = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=AWS_REGION,
)

# --- Утилиты для DynamoDB ---
def update_status(task_id: str, status: str, extra: Optional[dict] = None):
    expr   = "SET #s=:s, lastModified=:t"
    values = {":s": {"S": status}, ":t": {"N": str(int(time.time()))}}
    names  = {"#s": "status"}
    if extra:
        for k, v in extra.items():
            expr += f", {k}=:{k}"
            values[f":{k}"] = {"S": str(v)}
    logger.info("DDB update %s → %s", task_id, status)
    ddb.update_item(
        TableName=TABLE_NAME,
        Key={"taskId": {"S": task_id}},
        UpdateExpression=expr,
        ExpressionAttributeValues=values,
        ExpressionAttributeNames=names,
    )

def complete_task(task_id: str, main_url: str, license_url: Optional[str], phone: str):
    extra = {"mainFileUrl": main_url, "accountPhone": phone}
    if license_url:
        extra["licenseFileUrl"] = license_url
    update_status(task_id, "COMPLETED", extra)

def fail_task(task_id: str, error: str):
    update_status(task_id, "FAILED", {"error": error})

# --- Извлечение URL из текста (fallback) ---
def extract_url(text: str) -> Optional[str]:
    m = re.search(r'https?://[^\s<>"]+', text or "")
    if not m:
        return None
    url = m.group(0).rstrip('.,;:!?')
    # убираем лишнюю скобку
    if url.startswith('(') and url.endswith(')'):
        url = url[1:-1]
    return url

# --- Инициализация Telegram клиентов ---
clients = {}
locks   = {}
async def init_clients():
    import json
    try:
        data = json.load(open(SESSION_STRINGS_FILE))
    except:
        data = {}
    for phone, ss in data.items():
        client = TelegramClient(StringSession(ss), API_ID, API_HASH)
        await client.connect()
        clients[ss] = client
        locks[ss]   = asyncio.Lock()

async def select_client() -> Optional[Tuple[str, TelegramClient, asyncio.Lock]]:
    if not clients:
        await init_clients()
    for ss, client in clients.items():
        if not locks[ss].locked() and await client.is_user_authorized():
            return ss, client, locks[ss]
    return None

# --- Диалог с ботом SP Download Bot ---
async def dialog(task_id: str, url: str) -> Tuple[str, Optional[str], str]:
    sel = await select_client()
    if not sel:
        raise RuntimeError("No Telegram client available")
    ss, client, lock = sel
    async with lock:
        conv = client.conversation("SP Download Bot", timeout=1800)
        async with conv:
            # Встраиваем taskid только если ещё нет
            if "taskid=" in url:
                url_with_task = url
            else:
                sep = "&" if "?" in url else "?"
                url_with_task = f"{url}{sep}taskid={task_id}"
            await conv.send_message(url_with_task)

            # Ждём кнопку «С лицензией»
            btn_msg = await conv.get_response(timeout=60)
            for row in btn_msg.buttons or []:
                for btn in row:
                    if "с лицензией" in btn.text.lower():
                        await btn.click()
                        break

            # Ждём финальные ссылки (кнопки или текст)
            main_link = license_link = None
            start = asyncio.get_event_loop().time()
            while (not main_link or not license_link) and asyncio.get_event_loop().time() - start < 120:
                m = await conv.get_response(timeout=30)
                txt = (m.text or "").lower()

                if "исходники успешно получены" in txt and not main_link:
                    # inline-кнопка
                    if m.buttons:
                        main_link = m.buttons[0][0].url
                    else:
                        main_link = extract_url(m.text)

                if "лицензия успешно скачана" in txt and not license_link:
                    if m.buttons:
                        license_link = m.buttons[0][0].url
                    else:
                        license_link = extract_url(m.text)

            if not main_link:
                raise RuntimeError("Не удалось получить ссылку на основной файл")
            return main_link, license_link, ss

# --- Скачивание и загрузка в S3 ---
async def download_file(url: str, task_id: str, prefix: str) -> str:
    import aiofiles, httpx
    out = f"/tmp/{task_id}_{prefix}"
    async with httpx.AsyncClient(timeout=600) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        f = await aiofiles.open(out, "wb")
        await f.write(resp.content)
        await f.close()
    return out

async def upload_file(path: str, key: str) -> str:
    s3.upload_file(path, S3_BUCKET, key)
    # публичный URL
    return f"{S3_PUBLIC_BASE_URL}/{key}"

# --- FastAPI Models + Endpoint ---
class ProcessRequest(BaseModel):
    task_id: str
    url: HttpUrl

class ProcessResponse(BaseModel):
    taskId: str
    mainFileUrl: str
    licenseFileUrl: Optional[str] = None
    accountPhone: Optional[str] = None

@APP.post("/process", response_model=ProcessResponse)
async def process_endpoint(req: ProcessRequest):
    task_id = req.task_id
    url     = str(req.url)

    # 1) ставим IN_PROGRESS
    update_status(task_id, "IN_PROGRESS")

    # 2) Телеграм-диалог с retry
    last_exc = None
    for i in range(1, MAX_BOT_RETRIES + 1):
        try:
            main_link, license_link, account_phone = await dialog(task_id, url)
            break
        except Exception as e:
            last_exc = e
            if i == MAX_BOT_RETRIES:
                fail_task(task_id, str(e))
                raise HTTPException(status_code=500, detail=str(e))
            await asyncio.sleep(RETRY_BACKOFF_SECONDS * i)

    # 3) Скачиваем и заливаем
    try:
        main_path = await download_file(main_link, task_id, "main")
        lic_path  = None
        if license_link:
            lic_path = await download_file(license_link, task_id, "license")

        main_key = f"{task_id}/main"
        lic_key  = f"{task_id}/license" if lic_path else None

        public_main = await upload_file(main_path, main_key)
        public_lic  = await upload_file(lic_path, lic_key) if lic_key else None

        # 4) помечаем SUCCESS
        complete_task(task_id, public_main, public_lic, account_phone)
        return ProcessResponse(
            taskId=task_id,
            mainFileUrl=public_main,
            licenseFileUrl=public_lic,
            accountPhone=account_phone
        )
    except Exception as e:
        fail_task(task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))

