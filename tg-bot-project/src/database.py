from typing import Dict, Any, List, Optional, Tuple
import aiosqlite
import json
from datetime import datetime
import logging
import asyncio
from pyrogram import Client
from pyrogram.errors import (
    PhoneNumberInvalid,
    PhoneNumberBanned,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    FloodWait
)
from telethon import TelegramClient
from telethon.errors import *
import config  # Добавьте этот импорт, чтобы использовать config.API_ID и config.API_HASH
import random
import os

class Database:
    def __init__(self, db_path: str = "bot.db"):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None
        
    async def init(self):
        """Инициализация подключения к БД"""
        try:
            self.conn = await aiosqlite.connect(self.db_path)
            await self._create_tables()
            logging.info(f"Database initialized: {self.db_path}")
        except Exception as e:
            logging.error(f"Database initialization error: {e}")
            raise

    async def _create_tables(self):
        """Создание необходимых таблиц"""
        if not self.conn:
            raise RuntimeError("Database not initialized")
            
        async with self.conn.cursor() as cur:
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    link TEXT NOT NULL,
                    params TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await self.conn.commit()

    # Методы для работы с аккаунтами
    async def add_account(self, phone: str, data: Dict[str, Any]):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO accounts 
                (phone, status, data, last_used, daily_usage) 
                VALUES (?, ?, ?, ?, ?)""",
                (phone, "active", json.dumps(data), 
                 datetime.now().isoformat(),
                 json.dumps({"views": 0, "clicks": 0, "starts": 0, "reactions": 0}))
            )
            await db.commit()

    async def get_account(self, phone: str) -> Dict:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM accounts WHERE phone = ?", (phone,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {"phone": row[0], "status": row[1], "data": json.loads(row[2])}
                return None

    async def update_account_status(self, phone: str, status: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE accounts SET status = ? WHERE phone = ?", (status, phone))
            await db.commit()

    async def get_accounts_by_status(self, status: str) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            accounts = []
            async with db.execute("SELECT * FROM accounts WHERE status = ?", (status,)) as cursor:
                async for row in cursor:
                    accounts.append({
                        "phone": row[0],
                        "status": row[1],
                        "data": json.loads(row[2])
                    })
            return accounts

    async def get_available_accounts(self, task_type: str, limit: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            query = """
                SELECT * FROM accounts 
                WHERE status = 'active' 
                AND json_extract(daily_usage, ?) < ?
                ORDER BY last_used ASC
                LIMIT ?
            """
            usage_field = f"$.{task_type}"
            daily_limit = self._get_daily_limit(task_type)
            
            accounts = []
            async with db.execute(query, (usage_field, daily_limit, limit)) as cursor:
                async for row in cursor:
                    accounts.append(self._parse_account_row(row))
            return accounts

    # Методы для работы с задачами
    async def add_task(self, user_id: int, task_type: str, link: str, params: Dict) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO tasks (user_id, type, link, params, status) VALUES (?, ?, ?, ?, ?)",
                (user_id, task_type, link, json.dumps(params), "active")
            )
            await db.commit()
            return cursor.lastrowid

    async def create_task(self, user_id: int, task_type: str, link: str, 
                         params: Dict, schedule: Dict) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO tasks 
                (user_id, type, link, params, status, schedule, stats) 
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, task_type, link, json.dumps(params),
                 "active", json.dumps(schedule),
                 json.dumps({"views": 0, "clicks": 0, "starts": 0, "reactions": {}}))
            )
            await db.commit()
            return cursor.lastrowid

    async def get_user_tasks(self, user_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            tasks = []
            async with db.execute("SELECT * FROM tasks WHERE user_id = ?", (user_id,)) as cursor:
                async for row in cursor:
                    tasks.append({
                        "id": row[0],
                        "user_id": row[1],
                        "type": row[2],
                        "link": row[3],
                        "params": json.loads(row[4]),
                        "status": row[5]
                    })
            return tasks

    async def update_task_status(self, task_id: int, status: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
            await db.commit()

    async def update_task_stats(self, task_id: int, stats: Dict):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE tasks 
                SET stats = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?""",
                (json.dumps(stats), task_id)
            )
            await db.commit()

    async def get_active_tasks(self) -> List[Dict]:
        """Получение активных задач"""
        if not self.conn:
            raise RuntimeError("Database not initialized")
            
        async with self.conn.cursor() as cur:
            await cur.execute(
                "SELECT id, user_id, type, link, params, status FROM tasks WHERE status = 'active'"
            )
            rows = await cur.fetchall()
            
            return [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "type": row[2],
                    "link": row[3],
                    "params": json.loads(row[4]) if row[4] else {},
                    "status": row[5]
                }
                for row in rows
            ]

    # Методы для работы с ошибками
    async def log_error(self, task_id: int, account_phone: str, 
                       action_type: str, error_message: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO logs 
                (task_id, account_phone, action_type, status, error_message)
                VALUES (?, ?, ?, ?, ?)""",
                (task_id, account_phone, action_type, "error", error_message)
            )
            await db.commit()

    # Методы для статистики
    async def get_task_stats(self, task_id: int) -> Dict:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT stats FROM tasks WHERE id = ?", 
                (task_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return json.loads(row[0]) if row else {}

    async def get_account_stats(self, phone: str) -> Dict:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT daily_usage FROM accounts WHERE phone = ?",
                (phone,)
            ) as cursor:
                row = await cursor.fetchone()
                return json.loads(row[0]) if row else {}

    # Вспомогательные методы
    def _get_daily_limit(self, task_type: str) -> int:
        limits = {
            "views": 100,
            "clicks": 50,
            "starts": 30,
            "reactions": 40
        }
        return limits.get(task_type, 0)

    def _parse_account_row(self, row: Tuple) -> Dict:
        return {
            "phone": row[0],
            "status": row[1],
            "data": json.loads(row[2]),
            "last_used": row[3],
            "error_count": row[4],
            "daily_usage": json.loads(row[5]),
            "created_at": row[6]
        }

    async def send_auth_code(self, phone: str) -> dict:
        """Отправка кода авторизации"""
        logging.info(f"Отправка кода на {phone}")
        
        # Проверяем наличие директории для сессий
        if not os.path.exists("sessions"):
            os.makedirs("sessions")

        try:
            client = TelegramClient(
                f"sessions/{phone}",
                config.API_ID,
                config.API_HASH
            )

            await client.connect()
            
            if await client.is_user_authorized():
                logging.warning(f"Аккаунт {phone} уже авторизован")
                await client.disconnect()
                raise Exception("Этот номер уже добавлен")

            sent_code = await client.send_code_request(phone)
            await client.disconnect()
            
            logging.info(f"Код успешно отправлен на {phone}")
            
            return {
                "phone_code_hash": sent_code.phone_code_hash
            }
            
        except Exception as e:
            logging.error(f"Ошибка при отправке кода: {str(e)}")
            raise
            
        finally:
            try:
                if 'client' in locals() and client:
                    await client.disconnect()
            except:
                pass

    async def verify_code(self, phone: str, code: str, phone_code_hash: str) -> dict:
        """Проверка кода подтверждения"""
        logging.info(f"Проверка кода для {phone}")
        
        try:
            client = TelegramClient(
                f"sessions/{phone}",
                config.API_ID,
                config.API_HASH
            )
            
            await client.connect()

            try:
                # Пытаемся войти с кодом
                await client.sign_in(phone, code, phone_code_hash)
                
                # Если дошли до сюда - код верный
                await client.disconnect()
                
                logging.info(f"Успешная авторизация для {phone}")
                return {
                    "success": True,
                    "session": f"sessions/{phone}.session"  # Возвращаем путь к файлу сессии
                }
                
            except PhoneCodeInvalidError:
                logging.warning(f"Неверный код для {phone}")
                return {"success": False}
                
            except SessionPasswordNeededError:
                logging.warning(f"Требуется пароль для {phone}")
                return {
                    "success": False,
                    "need_password": True
                }
                
        except Exception as e:
            logging.error(f"Ошибка проверки кода: {str(e)}")
            raise
            
        finally:
            try:
                if 'client' in locals():
                    await client.disconnect()
            except:
                pass

    async def save_session(self, phone: str, session: str):
        """Сохранение сессии в БД"""
        async with self.conn.cursor() as cur:
            await cur.execute(
                "UPDATE accounts SET session_string = ?, status = 'active' WHERE phone = ?",
                (session, phone)
            )
            await self.conn.commit()
