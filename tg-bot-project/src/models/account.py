from typing import Dict, Optional
from datetime import datetime, timedelta
from enum import Enum

class AccountStatus(Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    ERROR = "error"
    BANNED = "banned"
    VERIFICATION = "verification"

class Account:
    def __init__(self, phone: str, status: AccountStatus = AccountStatus.INACTIVE):
        self.phone = phone
        self.status = status
        self.session = None
        self.last_used = datetime.now()
        self.error_message = None
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
        self.error_count = 0
        self.success_rate = 100.0
        self.verification_tries = 0
        self.banned_until = None
        self.auth_data = {}

    def can_perform_action(self, action_type: str) -> tuple[bool, str]:
        self._reset_daily_limits_if_needed()
        
        if self.status != AccountStatus.ACTIVE:
            return False, f"Аккаунт неактивен (статус: {self.status.value})"
            
        if self.is_banned():
            return False, f"Аккаунт заблокирован до {self.banned_until}"
            
        current_usage = self.daily_usage.get(action_type, 0)
        limit = self.daily_limits.get(action_type, 0)
        
        if current_usage >= limit:
            return False, f"Достигнут дневной лимит для {action_type}"
            
        return True, ""

    def _reset_daily_limits_if_needed(self):
        last_reset = self.daily_usage["last_reset"]
        if datetime.now() - last_reset > timedelta(days=1):
            for key in self.daily_usage:
                if key != "last_reset":
                    self.daily_usage[key] = 0
            self.daily_usage["last_reset"] = datetime.now()

    def update_usage(self, action_type: str, amount: int = 1):
        self._reset_daily_limits_if_needed()
        self.daily_usage[action_type] = self.daily_usage.get(action_type, 0) + amount
        self.last_used = datetime.now()

    def report_error(self, error: str, max_errors: int = 5):
        self.error_count += 1
        self.error_message = error
        
        if self.error_count >= max_errors:
            self.status = AccountStatus.ERROR
            self.banned_until = datetime.now() + timedelta(hours=24)

    def activate(self):
        self.status = AccountStatus.ACTIVE
        self.error_message = None
        self.error_count = 0
        self.banned_until = None
        self.verification_tries = 0

    def deactivate(self, error: str = None):
        self.status = AccountStatus.ERROR if error else AccountStatus.INACTIVE
        self.error_message = error

    def is_banned(self) -> bool:
        if not self.banned_until:
            return False
        return datetime.now() < self.banned_until

    def to_dict(self) -> Dict:
        return {
            "phone": self.phone,
            "status": self.status.value,
            "last_used": self.last_used.isoformat(),
            "daily_usage": self.daily_usage,
            "error_count": self.error_count,
            "error_message": self.error_message,
            "banned_until": self.banned_until.isoformat() if self.banned_until else None,
            "success_rate": self.success_rate
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Account':
        account = cls(data["phone"])
        account.status = AccountStatus(data["status"])
        account.last_used = datetime.fromisoformat(data["last_used"])
        account.daily_usage = data["daily_usage"]
        account.error_count = data["error_count"]
        account.error_message = data["error_message"]
        if data.get("banned_until"):
            account.banned_until = datetime.fromisoformat(data["banned_until"])
        account.success_rate = data["success_rate"]
        return account

    def __repr__(self):
        return f"Account(phone={self.phone}, status={self.status.value}, error_count={self.error_count})"