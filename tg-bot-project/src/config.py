# Configuration settings for the Telegram bot

import os
import logging
from dotenv import load_dotenv

# Загрузка .env файла
if not load_dotenv():
    raise RuntimeError("Не найден файл .env")

# Получение и проверка критически важных параметров API
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Проверка наличия и валидности API параметров
if not all([API_ID, API_HASH, BOT_TOKEN]):
    raise ValueError("Отсутствуют API_ID, API_HASH или BOT_TOKEN в .env файле")

try:
    API_ID = int(API_ID)
except ValueError:
    raise ValueError(f"API_ID должен быть числом, получено: {API_ID}")

logging.info(f"Загружена конфигурация API: ID={API_ID}, HASH={API_HASH[:4]}...")

# Основные параметры
DB_PATH = os.getenv("DB_PATH", "bot.db")
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")

# Проверка и конвертация значений
if not all([BOT_TOKEN, API_ID, API_HASH]):
    raise ValueError("Отсутствуют обязательные параметры в .env")

try:
    API_ID = int(API_ID)
except ValueError:
    raise ValueError("API_ID должен быть числом")

# Конвертация админов в set
ADMIN_IDS = {
    int(x.strip()) 
    for x in ADMIN_IDS_RAW.split(",") 
    if x.strip().isdigit()
}

# Системные настройки
TASK_CHECK_INTERVAL = int(os.getenv("TASK_CHECK_INTERVAL", "60"))
ERROR_RETRY_DELAY = int(os.getenv("ERROR_RETRY_DELAY", "300"))
MAX_TASKS_PER_USER = int(os.getenv("MAX_TASKS_PER_USER", "10"))

logging.info("Конфигурация загружена успешно")

# Проверка API параметров
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# Проверка и конвертация значений API
if not all([API_ID, API_HASH]):
    raise ValueError("API_ID или API_HASH не установлены в .env")

try:
    API_ID = int(API_ID)
except ValueError:
    raise ValueError(f"API_ID должен быть числом, получено: {API_ID}")