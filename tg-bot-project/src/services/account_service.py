from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import logging
from pyrogram import Client
from pyrogram.errors import (
    PhoneCodeInvalid, 
    PhoneCodeExpired,
    SessionPasswordNeeded,
    BadRequest
)

from models.account import Account, AccountStatus
from utils.validators import validate_phone_number
from config import config

class AccountService:
    def __init__(self, db):
        self.db = db
        self.daily_limits = config.ACCOUNT_DAILY_LIMITS
        self.error_threshold = config.MAX_ERRORS_BEFORE_BAN
        self._auth_locks = {}  # Блокировки для предотвращения одновременной авторизации
        self._clients = {}     # Кэш клиентов Telegram {phone: Client}

    async def _create_client(self, phone: str) -> Client:
        """Создание клиента Telegram"""
        session_name = f"sessions/{phone}"
        client = Client(
            session_name,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            phone_number=phone
        )
        return client

    async def authorize_account(self, phone: str, code: str = None, password: str = None) -> Tuple[bool, str, Dict]:
        """Авторизация аккаунта в Telegram"""
        try:
            client = await self._create_client(phone)
            
            if not code:
                # Первый этап - отправка кода
                await client.connect()
                code_sent = await client.send_code(phone)
                return False, "Код отправлен", {"sent_code": code_sent.phone_code_hash}
                
            # Второй этап - проверка кода
            try:
                await client.sign_in(phone, code)
                await client.disconnect()
                return True, "Успешная авторизация", {}
            except SessionPasswordNeeded:
                if password:
                    await client.check_password(password)
                    await client.disconnect()
                    return True, "Успешная авторизация", {}
                return False, "Требуется облачный пароль", {"needs_password": True}
            except (PhoneCodeInvalid, PhoneCodeExpired) as e:
                return False, str(e), {}
                
        except Exception as e:
            logging.error(f"Error authorizing account {phone}: {e}")
            return False, f"Ошибка авторизации: {str(e)}", {}

    async def check_account_status(self, phone: str) -> Tuple[bool, str]:
        """Проверка работоспособности аккаунта"""
        try:
            client = await self._create_client(phone)
            await client.connect()
            
            if not await client.is_user_authorized():
                await client.disconnect()
                return False, "Требуется повторная авторизация"
                
            # Проверяем возможность отправки сообщения
            await client.get_me()
            await client.disconnect()
            
            await self.db.update_account_status(phone, AccountStatus.ACTIVE.value)
            return True, "Аккаунт работает"
            
        except Exception as e:
            logging.error(f"Error checking account {phone}: {e}")
            await self.report_error(phone, str(e))
            return False, f"Ошибка при проверке аккаунта: {str(e)}"

    async def add_account(self, phone: str, auth_data: Dict) -> Tuple[bool, str, Dict]:
        # Проверяем, не заблокирована ли авторизация
        if phone in self._auth_locks and self._auth_locks[phone].locked():
            return False, "Аккаунт в процессе авторизации", {}
            
        async with self._get_auth_lock(phone):
            is_valid, error = validate_phone_number(phone)
            if not is_valid:
                return False, error, {}
                
            existing = await self.db.get_account(phone)
            if existing and existing["status"] != "error":
                return False, "Аккаунт уже существует", {}
                
            try:
                # Проверяем облачный пароль если он нужен
                if auth_data.get("needs_password", False):
                    if not auth_data.get("cloud_password"):
                        return False, "Требуется облачный пароль", {"needs_password": True}
                
                account = Account(phone)
                account.daily_usage = {k: 0 for k in self.daily_limits.keys()}
                account.error_count = 0
                account.last_used = datetime.now()
                
                await self.db.add_account(phone, {
                    "auth_data": auth_data,
                    "daily_usage": account.daily_usage,
                    "error_count": 0,
                    "last_used": account.last_used.isoformat(),
                    "banned_until": None
                })
                return True, "Аккаунт успешно добавлен", {}
                
            except Exception as e:
                logging.error(f"Error adding account {phone}: {str(e)}")
                return False, f"Ошибка при добавлении аккаунта: {str(e)}", {}

    def _get_auth_lock(self, phone: str) -> asyncio.Lock:
        if phone not in self._auth_locks:
            self._auth_locks[phone] = asyncio.Lock()
        return self._auth_locks[phone]

    async def get_available_accounts(self, task_type: str, count: int) -> List[Account]:
        all_accounts = await self.db.get_accounts_by_status("active")
        available_accounts = []
        
        for acc_data in all_accounts:
            if self._is_account_banned(acc_data):
                continue
                
            account = Account(acc_data["phone"])
            account.daily_usage = acc_data["data"].get("daily_usage", {})
            account.error_count = acc_data["data"].get("error_count", 0)
            
            if await self._can_perform_task(account, task_type):
                available_accounts.append(account)
                if len(available_accounts) >= count:
                    break
                    
        return available_accounts

    def _is_account_banned(self, acc_data: Dict) -> bool:
        banned_until = acc_data["data"].get("banned_until")
        if banned_until:
            try:
                ban_time = datetime.fromisoformat(banned_until)
                if ban_time > datetime.now():
                    return True
                # Если бан истек, можно его снять
                asyncio.create_task(self._remove_ban(acc_data["phone"]))
            except ValueError:
                return False
        return False

    async def _remove_ban(self, phone: str):
        account_data = await self.db.get_account(phone)
        if account_data:
            account_data["data"]["banned_until"] = None
            account_data["data"]["error_count"] = 0
            await self.db.update_account_data(phone, account_data["data"])

    def _can_perform_task(self, account: Account, task_type: str) -> bool:
        # Проверяем дневные лимиты
        current_usage = account.daily_usage.get(task_type, 0)
        daily_limit = self.daily_limits.get(task_type, 0)
        return current_usage < daily_limit

    async def update_account_usage(self, phone: str, task_type: str, amount: int = 1):
        account_data = await self.db.get_account(phone)
        if not account_data:
            return False
            
        daily_usage = account_data["data"].get("daily_usage", {})
        daily_usage[task_type] = daily_usage.get(task_type, 0) + amount
        
        await self.db.update_account_data(phone, {
            **account_data["data"],
            "daily_usage": daily_usage,
            "last_used": datetime.now().isoformat()
        })
        return True

    async def reset_daily_limits(self):
        """Сброс дневных лимитов в начале нового дня"""
        accounts = await self.db.get_all_accounts()
        for acc_data in accounts:
            daily_usage = {k: 0 for k in self.daily_limits.keys()}
            await self.db.update_account_data(acc_data["phone"], {
                **acc_data["data"],
                "daily_usage": daily_usage
            })

    async def get_account_stats(self, phone: str) -> Dict:
        """Получение статистики аккаунта"""
        account = await self.db.get_account(phone)
        if not account:
            return {}
            
        return {
            "daily_usage": account["data"].get("daily_usage", {}),
            "last_used": account["data"].get("last_used"),
            "status": account["status"]
        }

    async def report_error(self, phone: str, error: str):
        """Регистрация ошибки аккаунта"""
        account_data = await self.db.get_account(phone)
        if not account_data:
            return
            
        data = account_data["data"]
        data["error_count"] = data.get("error_count", 0) + 1
        
        if data["error_count"] >= self.error_threshold:
            # Баним аккаунт на 24 часа
            data["banned_until"] = (datetime.now() + timedelta(hours=24)).isoformat()
            await self.db.update_account_status(phone, "error")
            
        await self.db.update_account_data(phone, data)
        
        # Логируем ошибку
        logging.error(f"Account {phone} error: {error}")