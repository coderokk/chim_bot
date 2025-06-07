from typing import Dict, List, Tuple
import random
import logging
import asyncio

# from models.task import Task  # Удалено, если не используется напрямую
from models.account import Account
from config import config

class ReactionService:
    def __init__(self, db, account_service):
        self.db = db
        self.account_service = account_service
        self.available_reactions = config.AVAILABLE_REACTIONS

    async def add_task(self, user_id: int, link: str, reactions: Dict[str, int]) -> Tuple[bool, str, int]:
        try:
            # Проверяем существующие активные задачи
            existing = await self.db.get_task_by_link(link, "reactions")
            if existing and existing["status"] == "active":
                return False, "Уже есть активная задача для этой ссылки", 0

            # Проверяем общее количество реакций
            total_reactions = sum(reactions.values())
            if total_reactions > config.MAX_REACTIONS_PER_TASK:
                return False, f"Превышен лимит реакций ({config.MAX_REACTIONS_PER_TASK})", 0

            # Проверяем доступность аккаунтов
            available_accounts = await self.account_service.get_available_accounts("reactions", total_reactions)
            if len(available_accounts) < total_reactions:
                return False, "Недостаточно доступных аккаунтов", 0

            task_id = await self.db.create_task(
                user_id=user_id,
                task_type="reactions",
                link=link,
                params={
                    "reactions": reactions,
                    "total": total_reactions,
                    "completed": 0,
                    "distributed": self._distribute_reactions(reactions)
                }
            )
            return True, "Задача успешно создана", task_id

        except Exception as e:
            logging.error(f"Error creating reaction task: {e}")
            return False, f"Ошибка при создании задачи: {str(e)}", 0

    def _distribute_reactions(self, reactions: Dict[str, int]) -> Dict[str, int]:
        """Распределяет реакции случайным образом"""
        distributed = {}
        remaining = {k: v for k, v in reactions.items()}
        
        while sum(remaining.values()) > 0:
            available = [r for r, c in remaining.items() if c > 0]
            if not available:
                break
                
            reaction = random.choice(available)
            remaining[reaction] -= 1
            distributed[reaction] = distributed.get(reaction, 0) + 1
            
        return distributed

    async def process_reactions(self, task_id: int) -> Tuple[bool, str]:
        task = await self.db.get_task(task_id)
        if not task:
            return False, "Задача не найдена"
            
        try:
            params = task["params"]
            completed = params["completed"]
            total = params["total"]
            distributed = params["distributed"]
            
            if completed >= total:
                await self.db.update_task_status(task_id, "completed")
                return True, "Задача завершена"

            # Получаем доступные аккаунты
            accounts = await self.account_service.get_available_accounts(
                "reactions",
                min(10, total - completed)  # Берем не более 10 реакций за раз
            )

            for account in accounts:
                reaction = self._get_next_reaction(distributed)
                if not reaction:
                    break
                    
                success = await self._send_reaction(account, task["link"], reaction)
                if success:
                    params["completed"] += 1
                    distributed[reaction] -= 1
                    await self.account_service.update_account_usage(account.phone, "reactions")
                else:
                    await self.account_service.report_error(account.phone, "Ошибка отправки реакции")

            await self.db.update_task_params(task_id, params)
            return True, f"Обработано {params['completed']}/{total} реакций"

        except Exception as e:
            logging.error(f"Error processing reactions for task {task_id}: {e}")
            return False, f"Ошибка при обработке реакций: {str(e)}"

    def _get_next_reaction(self, distributed: Dict[str, int]) -> str:
        """Возвращает следующую реакцию для отправки"""
        available = [r for r, c in distributed.items() if c > 0]
        return random.choice(available) if available else None

    async def _send_reaction(self, account: Account, link: str, reaction: str) -> bool:
        """Отправляет реакцию через аккаунт"""
        try:
            # Здесь должна быть реальная логика отправки реакции через Telegram API
            # Это заглушка для примера
            await asyncio.sleep(random.uniform(1, 3))  # Имитация задержки
            return True
        except Exception as e:
            logging.error(f"Error sending reaction from {account.phone}: {e}")
            return False

    async def get_task_status(self, task_id: int) -> Dict:
        """Получает статус задачи с реакциями"""
        task = await self.db.get_task(task_id)
        if not task:
            return {"error": "Задача не найдена"}
            
        params = task["params"]
        return {
            "status": task["status"],
            "completed": params["completed"],
            "total": params["total"],
            "remaining": {k: v for k, v in params["distributed"].items() if v > 0},
            "progress": f"{params['completed']}/{params['total']}"
        }