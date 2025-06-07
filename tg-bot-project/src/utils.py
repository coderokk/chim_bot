import re
import random
from typing import Tuple, List, Dict, Optional
from datetime import datetime, timedelta

class AccountValidator:
    PHONE_PATTERN = r'^\+7\d{10}$'
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str]:
        if not re.match(AccountValidator.PHONE_PATTERN, phone):
            return False, "Неверный формат номера. Используйте формат: +79991234567"
        return True, ""

class LinkValidator:
    @staticmethod
    def validate_link(link: str) -> Tuple[bool, str, str]:
        patterns = {
            "channel": r'^(https?:\/\/)?(t\.me\/)[a-zA-Z0-9_]{5,}$',
            "bot": r'^(https?:\/\/)?(t\.me\/)[a-zA-Z0-9_]{5,}bot$',
            "post": r'^(https?:\/\/)?(t\.me\/)[a-zA-Z0-9_]{5,}\/\d+$'
        }
        
        for link_type, pattern in patterns.items():
            if re.match(pattern, link):
                return True, link_type, ""
        return False, "", "Неверный формат ссылки"

class TaskScheduler:
    @staticmethod
    def parse_schedule(schedule: str) -> Tuple[bool, Dict, str]:
        if schedule == "24/7":
            return True, {"type": "constant", "active": True}, ""
            
        try:
            if "," in schedule:
                hours = [int(h.strip()) for h in schedule.split(",")]
                if not all(0 <= h <= 23 for h in hours):
                    return False, {}, "Часы должны быть от 0 до 23"
                hours = sorted(list(set(hours)))  # Удаляем дубликаты и сортируем
                return True, {"type": "hourly", "hours": hours}, ""
                
        except ValueError:
            return False, {}, "Неверный формат расписания"
        return False, {}, "Неподдерживаемый формат"

    @staticmethod
    def get_next_run_time(schedule: Dict) -> Optional[datetime]:
        if schedule["type"] == "constant":
            return datetime.now()
            
        if schedule["type"] == "hourly":
            current_hour = datetime.now().hour
            next_hours = [h for h in schedule["hours"] if h > current_hour]
            
            if next_hours:
                next_hour = next_hours[0]
                return datetime.now().replace(hour=next_hour, minute=0, second=0)
            else:
                # Следующий запуск будет завтра в первый указанный час
                tomorrow = datetime.now() + timedelta(days=1)
                return tomorrow.replace(hour=schedule["hours"][0], minute=0, second=0)
        return None

class ReactionManager:
    AVAILABLE_REACTIONS = ["👍", "❤️", "🔥", "😱", "🤬", "😢"]
    
    @staticmethod
    def distribute_reactions(total: int, available_reactions: List[str]) -> Dict[str, int]:
        """Распределяет реакции случайным образом"""
        if not available_reactions:
            available_reactions = ReactionManager.AVAILABLE_REACTIONS
            
        reaction_counts = {}
        remaining = total
        
        while remaining > 0:
            for reaction in available_reactions:
                if remaining <= 0:
                    break
                count = random.randint(1, max(1, remaining // len(available_reactions)))
                reaction_counts[reaction] = reaction_counts.get(reaction, 0) + count
                remaining -= count
                
        return reaction_counts

class StatsCalculator:
    @staticmethod
    def calculate_speed(views: int, minutes: int) -> float:
        """Рассчитывает скорость выполнения (просмотров в минуту)"""
        return views / minutes if minutes > 0 else 0

    @staticmethod
    def estimate_completion_time(total: int, current: int, speed: float) -> Optional[datetime]:
        """Оценивает время завершения задачи"""
        if speed <= 0:
            return None
        remaining = total - current
        minutes_left = remaining / speed
        return datetime.now() + timedelta(minutes=minutes_left)

class Paginator:
    def __init__(self, items: List, page_size: int = 30):
        self.items = items
        self.page_size = page_size
        self.total_pages = (len(items) + page_size - 1) // page_size

    def get_page(self, page: int) -> Tuple[List, bool, bool, Dict]:
        if page < 1:
            page = 1
        elif page > self.total_pages:
            page = self.total_pages

        start = (page - 1) * self.page_size
        end = start + self.page_size
        items = self.items[start:end]
        
        return items, page > 1, page < self.total_pages, {
            "current_page": page,
            "total_pages": self.total_pages,
            "total_items": len(self.items)
        }
