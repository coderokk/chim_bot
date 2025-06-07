from typing import Tuple, Dict, List, Optional
import re

def validate_phone_number(phone: str) -> Tuple[bool, str]:
    """Валидация номера телефона (+7XXXXXXXXXX)"""
    pattern = r'^\+7[0-9]{10}$'
    if not re.match(pattern, phone):
        return False, "Неверный формат номера. Используйте формат: +79991234567"
    return True, ""

def validate_telegram_link(link: str) -> Tuple[bool, str, str]:
    """Валидация Telegram ссылки с определением типа"""
    patterns = {
        "channel": r'^(https?:\/\/)?(t\.me\/)[a-zA-Z0-9_]{5,}$',
        "bot": r'^(https?:\/\/)?(t\.me\/)[a-zA-Z0-9_]{5,}bot$',
        "post": r'^(https?:\/\/)?(t\.me\/)[a-zA-Z0-9_]{5,}\/\d+$'
    }
    
    for link_type, pattern in patterns.items():
        if re.match(pattern, link):
            return True, link_type, ""
    return False, "", "Неверный формат ссылки"

def validate_task_type(task_type: str, link_type: str) -> Tuple[bool, str]:
    """Валидация типа задачи в зависимости от типа ссылки"""
    channel_types = ['Реакции', 'Просмотры']
    bot_types = ['ПР', 'ПРП', 'ПРПС']
    
    if link_type == "channel" and task_type in channel_types:
        return True, ""
    if link_type == "bot" and task_type in bot_types:
        return True, ""
    return False, f"Недопустимый тип задачи для {link_type}"

def validate_schedule(schedule: str) -> Tuple[bool, Dict, str]:
    """Валидация расписания с поддержкой 24/7 и графика по часам"""
    if schedule == "24/7":
        return True, {"type": "constant", "active": True}, ""
        
    try:
        if "," in schedule:
            hours = [int(h.strip()) for h in schedule.split(",")]
            if not all(0 <= h <= 23 for h in hours):
                return False, {}, "Часы должны быть от 0 до 23"
            hours = sorted(list(set(hours)))
            return True, {"type": "hourly", "hours": hours}, ""
    except ValueError:
        pass
    return False, {}, "Неверный формат расписания"

def validate_reaction(reaction: str) -> Tuple[bool, str]:
    """Валидация реакции"""
    valid_reactions = ["👍", "❤️", "🔥", "😱", "🤬", "😢"]
    if reaction not in valid_reactions:
        return False, f"Недопустимая реакция. Доступные: {', '.join(valid_reactions)}"
    return True, ""

def validate_speed(speed: str) -> Tuple[bool, int, str]:
    """Валидация скорости выполнения"""
    pattern = r'^(\d+)\s*мин/1000$'
    match = re.match(pattern, speed)
    if not match:
        return False, 0, "Неверный формат скорости. Используйте формат: X мин/1000"
    
    minutes = int(match.group(1))
    if not 1 <= minutes <= 60:
        return False, 0, "Скорость должна быть от 1 до 60 минут на 1000 действий"
    return True, minutes, ""

def validate_amount(amount: int, task_type: str) -> Tuple[bool, str]:
    """Валидация количества действий"""
    limits = {
        "Реакции": 1000,
        "Просмотры": 10000,
        "ПР": 5000,
        "ПРП": 3000,
        "ПРПС": 2000
    }
    
    if not isinstance(amount, int) or amount <= 0:
        return False, "Количество должно быть положительным числом"
        
    if amount > limits.get(task_type, 0):
        return False, f"Превышен лимит для {task_type}: {limits[task_type]}"
    
    return True, ""