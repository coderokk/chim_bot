from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional, Union
from enum import Enum
import json

class TaskType(Enum):
    REACTIONS = "reactions"
    VIEWS = "views"
    PR = "pr"          # Просмотр рекламы
    PRP = "prp"        # Просмотр + переход
    PRPS = "prps"      # Просмотр + переход + старт
    
    @classmethod
    def get_available_actions(cls, link_type: str) -> List[str]:
        if link_type == "channel":
            return [cls.REACTIONS.value, cls.VIEWS.value]
        return [cls.PR.value, cls.PRP.value, cls.PRPS.value]

class TaskStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"
    PAUSED = "paused"

class AccountStatus(Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    ERROR = "error"
    BANNED = "banned"
    VERIFICATION = "verification"

class TaskStats:
    def __init__(self):
        self.views = 0
        self.clicks = 0
        self.starts = 0
        self.reactions = {}  # Dict[reaction_type: str, count: int]
        self.last_update = datetime.now()
        self.hourly_stats = {}  # Dict[hour: int, stats: Dict]
        self.errors = []
        self.success_rate = 100.0
        self.speed_stats = {
            "current_speed": 0,  # действий в минуту
            "average_speed": 0,
            "target_speed": 0
        }
        self.completion_estimate = None

    def update(self, views: int = 0, clicks: int = 0, starts: int = 0, reaction: str = None):
        self.views += views
        self.clicks += clicks
        self.starts += starts
        if reaction:
            self.reactions[reaction] = self.reactions.get(reaction, 0) + 1
        
        current_hour = datetime.now().hour
        if current_hour not in self.hourly_stats:
            self.hourly_stats[current_hour] = {"views": 0, "clicks": 0, "starts": 0}
        
        self.hourly_stats[current_hour]["views"] += views
        self.hourly_stats[current_hour]["clicks"] += clicks
        self.hourly_stats[current_hour]["starts"] += starts
        self.last_update = datetime.now()
        self._update_speed_stats()
        self._update_completion_estimate()

    def _update_speed_stats(self):
        if not self.hourly_stats:
            return
            
        current_hour = datetime.now().hour
        if current_hour in self.hourly_stats:
            total_actions = (
                self.hourly_stats[current_hour]["views"] +
                self.hourly_stats[current_hour]["clicks"] +
                self.hourly_stats[current_hour]["starts"]
            )
            self.speed_stats["current_speed"] = total_actions / 60  # в минуту

    def _update_completion_estimate(self):
        if not self.speed_stats["current_speed"]:
            return
            
        total_actions_needed = (
            self.completion_target["views"] - self.views +
            self.completion_target["clicks"] - self.clicks +
            self.completion_target["starts"] - self.starts
        )
        
        if total_actions_needed <= 0:
            self.completion_estimate = timedelta(0)
        else:
            minutes_needed = total_actions_needed / self.speed_stats["current_speed"]
            self.completion_estimate = timedelta(minutes=minutes_needed)

    def add_error(self, error: str):
        self.errors.append({"time": datetime.now(), "error": error})
        self._update_success_rate()

    def _update_success_rate(self):
        total_actions = self.views + self.clicks + self.starts + len(self.reactions)
        if total_actions > 0:
            self.success_rate = 100 * (1 - len(self.errors) / total_actions)

    def to_dict(self) -> Dict:
        return {
            "views": self.views,
            "clicks": self.clicks,
            "starts": self.starts,
            "reactions": self.reactions,
            "success_rate": self.success_rate,
            "last_update": self.last_update.isoformat()
        }

class Account:
    def __init__(self, phone: str):
        self.phone = phone
        self.status = AccountStatus.INACTIVE
        self.session = None
        self.last_used = datetime.now()
        self.error_message = None
        self.tasks_completed = 0
        self.daily_limits = {
            "views": 100,
            "clicks": 50,
            "starts": 30,
            "reactions": 40
        }
        self.daily_usage = {
            "views": 0,
            "clicks": 0,
            "starts": 0,
            "reactions": 0,
            "last_reset": datetime.now()
        }
        self.success_rate = 100.0
        self.errors = []
        self.verification_tries = 0
        self.limits_by_type = {
            TaskType.VIEWS.value: {"daily": 100, "hourly": 10},
            TaskType.REACTIONS.value: {"daily": 40, "hourly": 5},
            TaskType.PR.value: {"daily": 50, "hourly": 6},
            TaskType.PRP.value: {"daily": 40, "hourly": 5},
            TaskType.PRPS.value: {"daily": 30, "hourly": 4}
        }
        self.hourly_usage = {}
        self.last_action_time = {}

    def can_perform_action(self, action_type: str) -> Tuple[bool, str]:
        self._reset_daily_limits_if_needed()
        self._update_hourly_stats()
        
        if not self.is_within_hourly_limit(action_type):
            return False, "Превышен часовой лимит"
            
        if not self.is_within_daily_limit(action_type):
            return False, "Превышен дневной лимит"
            
        if not self.check_action_cooldown(action_type):
            return False, "Слишком частые действия"
            
        return True, ""

    def is_within_hourly_limit(self, action_type: str) -> bool:
        current_hour = datetime.now().hour
        if current_hour not in self.hourly_usage:
            return True
        return self.hourly_usage[current_hour].get(action_type, 0) < self.limits_by_type[action_type]["hourly"]

    def _reset_daily_limits_if_needed(self):
        if datetime.now() - self.daily_usage["last_reset"] > timedelta(days=1):
            for key in self.daily_usage:
                if key != "last_reset":
                    self.daily_usage[key] = 0
            self.daily_usage["last_reset"] = datetime.now()

    def activate(self):
        self.status = AccountStatus.ACTIVE
        self.error_message = None
        self.verification_tries = 0

    def deactivate(self, error: str = None):
        self.status = AccountStatus.ERROR if error else AccountStatus.INACTIVE
        self.error_message = error
        if error:
            self.errors.append({"time": datetime.now(), "error": error})

    def to_dict(self) -> Dict:
        return {
            "phone": self.phone,
            "status": self.status.value,
            "last_used": self.last_used.isoformat(),
            "tasks_completed": self.tasks_completed,
            "success_rate": self.success_rate,
            "daily_usage": self.daily_usage,
            "errors": self.errors
        }

class Task:
    def __init__(self, task_id: int, user_id: int, link: str):
        self.id = task_id
        self.user_id = user_id
        self.link = link
        self.type = None
        self.status = TaskStatus.PENDING
        self.params = {}
        self.stats = TaskStats()
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.assigned_accounts: List[str] = []  # List of phone numbers
        self.schedule = {}
        self.priority = 1
        self.max_errors = 10
        self.retry_delay = 300  # seconds
        self.completion_target = {
            "views": 0,
            "clicks": 0,
            "starts": 0,
            "reactions": {}
        }
        self.speed_settings = {
            "views_per_minute": 0,
            "min_interval": 0,
            "max_interval": 0
        }

    def set_schedule(self, schedule_type: str, params: Dict):
        self.schedule = {
            "type": schedule_type,  # "24/7" or "hourly"
            "params": params,
            "last_run": None,
            "next_run": None
        }
        self._update_next_run()

    def _update_next_run(self):
        if self.schedule["type"] == "24/7":
            self.schedule["next_run"] = datetime.now()
        elif self.schedule["type"] == "hourly":
            current_hour = datetime.now().hour
            next_hours = [h for h in self.schedule["params"]["hours"] if h > current_hour]
            if next_hours:
                next_hour = next_hours[0]
            else:
                next_hour = self.schedule["params"]["hours"][0]
                
            next_run = datetime.now().replace(hour=next_hour, minute=0, second=0)
            if next_hour <= current_hour:
                next_run += timedelta(days=1)
            self.schedule["next_run"] = next_run

    def should_run(self) -> bool:
        if self.status != TaskStatus.ACTIVE:
            return False
            
        if not self.schedule.get("next_run"):
            return True
            
        return datetime.now() >= self.schedule["next_run"]

    def update_stats(self, **kwargs):
        self.stats.update(**kwargs)
        self.updated_at = datetime.now()

    def set_completion_target(self, task_type: str, amount: int):
        if task_type == TaskType.VIEWS.value:
            self.completion_target["views"] = amount
        elif task_type == TaskType.PR.value:
            self.completion_target["views"] = amount
        elif task_type == TaskType.PRP.value:
            self.completion_target["views"] = amount
            self.completion_target["clicks"] = amount
        elif task_type == TaskType.PRPS.value:
            self.completion_target["views"] = amount
            self.completion_target["clicks"] = amount
            self.completion_target["starts"] = amount
        elif task_type == TaskType.REACTIONS.value:
            total_reactions = sum(self.completion_target["reactions"].values())
            if total_reactions + amount > 1000:
                raise ValueError("Превышен лимит реакций")
            self.completion_target["reactions"]["random"] = amount

    def is_completed(self) -> bool:
        for action, target in self.completion_target.items():
            if action == "reactions":
                total_reactions = sum(self.stats.reactions.values())
                if total_reactions < sum(target.values()):
                    return False
            else:
                current = getattr(self.stats, action)
                if current < target:
                    return False
        return True

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "link": self.link,
            "type": self.type.value if self.type else None,
            "status": self.status.value,
            "params": self.params,
            "stats": self.stats.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "schedule": self.schedule,
            "assigned_accounts": self.assigned_accounts
        }

class Paginator:
    def __init__(self, items: List, page_size: int = 30):
        self.items = items
        self.page_size = page_size
        self.total_pages = (len(items) + page_size - 1) // page_size

    def get_page(self, page: int) -> Tuple[List, bool, bool]:
        if page < 1:
            page = 1
        elif page > self.total_pages:
            page = self.total_pages

        start = (page - 1) * self.page_size
        end = start + self.page_size
        items = self.items[start:end]
        has_next = page < self.total_pages
        has_prev = page > 1
        
        return items, has_prev, has_next

    def get_page_info(self, page: int) -> Dict:
        return {
            "current_page": page,
            "total_pages": self.total_pages,
            "items_per_page": self.page_size,
            "total_items": len(self.items)
        }
