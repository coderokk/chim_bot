from typing import Dict, Optional
from datetime import datetime, timedelta
from enum import Enum

class TaskType(Enum):
    REACTIONS = "reactions"
    VIEWS = "views"
    PR = "pr"          # Просмотр рекламы
    PRP = "prp"        # Просмотр + переход
    PRPS = "prps"      # Просмотр + переход + старт

class TaskStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

class Task:
    def __init__(self, task_id: int, user_id: int, link: str, task_type: TaskType):
        self.id = task_id
        self.user_id = user_id
        self.link = link
        self.type = task_type
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # Статистика выполнения
        self.stats = {
            "views": 0,
            "clicks": 0,
            "starts": 0,
            "reactions": {},
            "errors": []
        }
        
        # Целевые показатели
        self.targets = {
            "views": 0,
            "clicks": 0,
            "starts": 0,
            "reactions": {}
        }
        
        # Параметры выполнения
        self.schedule = {
            "type": "24/7",  # или "hourly"
            "hours": [],      # для hourly
            "last_run": None,
            "next_run": None
        }
        
        self.speed = {
            "views_per_minute": 0,
            "current_speed": 0,
            "min_interval": 0,
            "max_interval": 0
        }
        
        self.assigned_accounts = []
        self.error_count = 0
        self.max_errors = 10

    def set_targets(self, targets: Dict) -> bool:
        try:
            if self.type in [TaskType.VIEWS, TaskType.PR]:
                self.targets["views"] = targets["amount"]
            elif self.type == TaskType.PRP:
                self.targets["views"] = targets["amount"]
                self.targets["clicks"] = targets["amount"]
            elif self.type == TaskType.PRPS:
                self.targets["views"] = targets["amount"]
                self.targets["clicks"] = targets["amount"]
                self.targets["starts"] = targets["amount"]
            elif self.type == TaskType.REACTIONS:
                self.targets["reactions"] = targets["reactions"]
            return True
        except KeyError:
            return False

    def set_schedule(self, schedule_type: str, hours: list = None) -> bool:
        if schedule_type not in ["24/7", "hourly"]:
            return False
            
        self.schedule["type"] = schedule_type
        if schedule_type == "hourly" and hours:
            self.schedule["hours"] = sorted(list(set(h for h in hours if 0 <= h <= 23)))
        self._update_next_run()
        return True

    def _update_next_run(self):
        if self.schedule["type"] == "24/7":
            self.schedule["next_run"] = datetime.now()
        elif self.schedule["type"] == "hourly" and self.schedule["hours"]:
            current_hour = datetime.now().hour
            next_hours = [h for h in self.schedule["hours"] if h > current_hour]
            if next_hours:
                next_hour = next_hours[0]
            else:
                next_hour = self.schedule["hours"][0]
                
            next_run = datetime.now().replace(hour=next_hour, minute=0, second=0)
            if next_hour <= current_hour:
                next_run += timedelta(days=1)
            self.schedule["next_run"] = next_run

    def update_stats(self, stats_update: Dict):
        for key, value in stats_update.items():
            if key in self.stats:
                if isinstance(self.stats[key], dict):
                    self.stats[key].update(value)
                else:
                    self.stats[key] += value
        self.updated_at = datetime.now()
        self._check_completion()

    def _check_completion(self) -> bool:
        if self.type == TaskType.REACTIONS:
            total_reactions = sum(self.stats["reactions"].values())
            target_reactions = sum(self.targets["reactions"].values())
            if total_reactions >= target_reactions:
                self.status = TaskStatus.COMPLETED
                return True
        else:
            for key in ["views", "clicks", "starts"]:
                if self.targets[key] > 0 and self.stats[key] < self.targets[key]:
                    return False
            self.status = TaskStatus.COMPLETED
            return True
        return False

    def report_error(self, error: str):
        self.error_count += 1
        self.stats["errors"].append({
            "time": datetime.now().isoformat(),
            "error": error
        })
        if self.error_count >= self.max_errors:
            self.status = TaskStatus.ERROR

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "link": self.link,
            "type": self.type.value,
            "status": self.status.value,
            "stats": self.stats,
            "targets": self.targets,
            "schedule": self.schedule,
            "speed": self.speed,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def __repr__(self):
        return f"Task#{self.id} - {self.type.value} - Status: {self.status.value}"
    
    def should_run(self) -> bool:
        """Проверяет, должна ли задача выполняться"""
        return self.status == TaskStatus.ACTIVE