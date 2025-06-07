from typing import Dict, List
from datetime import datetime
from enum import Enum

class UserStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"
    VERIFICATION = "verification"

class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

class User:
    def __init__(self, user_id: int, username: str = None, role: UserRole = UserRole.USER):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.status = UserStatus.ACTIVE
        self.created_at = datetime.now()
        self.last_active = datetime.now()
        
        # Лимиты для задач
        self.limits = {
            "max_active_tasks": 10,
            "max_accounts": 100,
            "max_views_per_task": 10000,
            "max_reactions_per_task": 1000
        }
        
        # Статистика использования
        self.stats = {
            "total_tasks_created": 0,
            "active_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0
        }
        
        # Настройки пользователя
        self.settings = {
            "notifications_enabled": True,
            "default_schedule": "24/7",
            "preferred_speed": "medium"
        }

    def can_create_task(self) -> tuple[bool, str]:
        if self.status != UserStatus.ACTIVE:
            return False, f"Аккаунт {self.status.value}"
            
        if self.stats["active_tasks"] >= self.limits["max_active_tasks"]:
            return False, "Достигнут лимит активных задач"
            
        return True, ""

    def increment_task_stat(self, stat_type: str):
        if stat_type in self.stats:
            self.stats[stat_type] += 1
            
        if stat_type == "active_tasks":
            self.last_active = datetime.now()

    def update_settings(self, settings: Dict) -> bool:
        try:
            for key, value in settings.items():
                if key in self.settings:
                    self.settings[key] = value
            return True
        except Exception:
            return False

    def has_permission(self, permission: str) -> bool:
        permission_map = {
            UserRole.ADMIN: ["all"],
            UserRole.MODERATOR: ["view_all_tasks", "manage_tasks", "view_accounts"],
            UserRole.USER: ["create_task", "view_own_tasks"]
        }
        
        allowed_permissions = permission_map.get(self.role, [])
        return "all" in allowed_permissions or permission in allowed_permissions

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "limits": self.limits,
            "stats": self.stats,
            "settings": self.settings
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        user = cls(
            user_id=data["user_id"],
            username=data.get("username"),
            role=UserRole(data.get("role", "user"))
        )
        user.status = UserStatus(data.get("status", "active"))
        user.limits = data.get("limits", user.limits)
        user.stats = data.get("stats", user.stats)
        user.settings = data.get("settings", user.settings)
        return user

    def __repr__(self):
        return f"User(id={self.user_id}, role={self.role.value}, status={self.status.value})"