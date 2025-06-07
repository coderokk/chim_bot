from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
import asyncio

from config import config

class TaskService:
    def __init__(self, db, account_service):
        self.db = db
        self.account_service = account_service
        self.active_tasks = {}  # task_id: Task
        self._task_locks = {}  # task_id: Lock

    async def create_task(
        self, 
        user_id: int, 
        link: str, 
        task_type: str, 
        params: Dict
    ) -> Tuple[bool, str, int]:
        try:
            # Проверяем лимит активных задач пользователя
            user_tasks = await self.db.get_user_tasks(user_id)
            active_tasks = [t for t in user_tasks if t["status"] == "active"]
            if len(active_tasks) >= config.MAX_TASKS_PER_USER:
                return False, "Достигнут лимит активных задач", 0

            # Проверяем существующие задачи для этой ссылки
            existing = await self.db.get_task_by_link(link, task_type)
            if existing and existing["status"] == "active":
                return False, f"Задача #{existing['id']} уже существует для этой ссылки", 0

            # Проверяем параметры в зависимости от типа
            is_valid, error = self._validate_task_params(task_type, params)
            if not is_valid:
                return False, error, 0

            # Создаем задачу
            task_id = await self.db.create_task(
                user_id=user_id,
                task_type=task_type,
                link=link,
                params=params,
                status="pending"
            )

            # Запускаем задачу
            asyncio.create_task(self._process_task(task_id))
            return True, "Задача успешно создана", task_id

        except Exception as e:
            logging.error(f"Error creating task: {e}")
            return False, f"Ошибка при создании задачи: {str(e)}", 0

    def _validate_task_params(self, task_type: str, params: Dict) -> Tuple[bool, str]:
        try:
            if task_type in ["views", "pr", "prp", "prps"]:
                amount = params.get("amount", 0)
                if amount > config.MAX_VIEWS_PER_TASK:
                    return False, f"Превышен лимит просмотров ({config.MAX_VIEWS_PER_TASK})"
                    
            elif task_type == "reactions":
                total_reactions = sum(params.get("reactions", {}).values())
                if total_reactions > config.MAX_REACTIONS_PER_TASK:
                    return False, f"Превышен лимит реакций ({config.MAX_REACTIONS_PER_TASK})"

            # Проверяем расписание
            schedule = params.get("schedule", {})
            if not schedule or schedule.get("type") not in ["24/7", "hourly"]:
                return False, "Неверный формат расписания"

            return True, ""
        except Exception as e:
            return False, f"Ошибка валидации параметров: {str(e)}"

    async def _process_task(self, task_id: int):
        """Основной цикл обработки задачи"""
        while True:
            async with self._get_task_lock(task_id):
                task = await self.db.get_task(task_id)
                if not task or task["status"] not in ["active", "pending"]:
                    break

                try:
                    if self._should_process_task(task):
                        await self._execute_task_action(task)
                    
                    # Обновляем время следующего запуска
                    next_run = self._calculate_next_run(task)
                    await self.db.update_task_params(task_id, {
                        **task["params"],
                        "next_run": next_run.isoformat() if next_run else None
                    })

                except Exception as e:
                    logging.error(f"Error processing task {task_id}: {e}")
                    await self.db.update_task_status(task_id, "error")
                    break

            await asyncio.sleep(config.TASK_CHECK_INTERVAL)

    def _get_task_lock(self, task_id: int) -> asyncio.Lock:
        if task_id not in self._task_locks:
            self._task_locks[task_id] = asyncio.Lock()
        return self._task_locks[task_id]

    async def get_task_status(self, task_id: int) -> Dict:
        """Получает полный статус задачи"""
        task = await self.db.get_task(task_id)
        if not task:
            return {"error": "Задача не найдена"}

        return {
            "id": task_id,
            "status": task["status"],
            "type": task["type"],
            "link": task["link"],
            "progress": self._calculate_progress(task),
            "next_run": task["params"].get("next_run"),
            "error": task["params"].get("error")
        }