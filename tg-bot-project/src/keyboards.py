from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Tuple

def get_main_menu() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="Новая задача"), KeyboardButton(text="Мои задачи")],
        [KeyboardButton(text="Админ панель")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_menu() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="Аккаунты"), KeyboardButton(text="Задачи")],
        [KeyboardButton(text="Логи"), KeyboardButton(text="Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_accounts_menu() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="Добавить"), KeyboardButton(text="Список аккаунтов")],
        [KeyboardButton(text="Ошибки"), KeyboardButton(text="Назад")],
        [KeyboardButton(text="Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_task_actions(task_type: str) -> ReplyKeyboardMarkup:
    if task_type == "channel":
        kb = [
            [KeyboardButton(text="Реакции"), KeyboardButton(text="Просмотры")],
            [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
        ]
    else:
        kb = [
            [KeyboardButton(text="ПР"), KeyboardButton(text="ПРП"), KeyboardButton(text="ПРПС")],
            [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
        ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_reactions_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="👍"), KeyboardButton(text="❤️"), KeyboardButton(text="🔥")],
        [KeyboardButton(text="😱"), KeyboardButton(text="🤬"), KeyboardButton(text="😢")],
        [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_amount_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="10"), KeyboardButton(text="50"), KeyboardButton(text="100")],
        [KeyboardButton(text="500"), KeyboardButton(text="1000")],
        [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_schedule_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="24/7")],
        [KeyboardButton(text="График по часам")],
        [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_speed_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="1 мин/1000"), KeyboardButton(text="3 мин/1000")],
        [KeyboardButton(text="5 мин/1000"), KeyboardButton(text="10 мин/1000")],
        [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_account_actions_kb(is_active: bool = True) -> ReplyKeyboardMarkup:
    buttons = []
    if is_active:
        buttons.append([KeyboardButton(text="Отключить"), KeyboardButton(text="Проверить")])
    else:
        buttons.append([KeyboardButton(text="Включить"), KeyboardButton(text="Авторизовать")])
    
    buttons.append([KeyboardButton(text="Проверить"), KeyboardButton(text="Удалить")])
    buttons.append([KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_task_status_kb(is_active: bool = True) -> ReplyKeyboardMarkup:
    kb = []
    if is_active:
        kb.append([KeyboardButton(text="Завершить"), KeyboardButton(text="Пауза")])
    else:
        kb.append([KeyboardButton(text="Возобновить"), KeyboardButton(text="Удалить")])
    
    kb.append([KeyboardButton(text="Статистика")])
    kb.append([KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_yes_no_kb(include_back: bool = True) -> ReplyKeyboardMarkup:
    kb = [[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]]
    if include_back:
        kb.append([KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_tasks_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="Активные"), KeyboardButton(text="Завершённые")],
        [KeyboardButton(text="С ошибкой"), KeyboardButton(text="Все задачи")],
        [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_task_list_kb(tasks: List[Dict], page: int = 1, items_per_page: int = 30) -> Tuple[str, ReplyKeyboardMarkup]:
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    current_tasks = tasks[start_idx:end_idx]
    
    text = "Список задач:\n\n"
    for task in current_tasks:
        status = "🟢" if task["status"] == "active" else "🔴"
        text += f"#{task['id']} - {task['type']} {status}\n"
    
    kb = []
    nav_row = []
    if page > 1:
        nav_row.append(KeyboardButton(text="◀️ Предыдущая"))
    if end_idx < len(tasks):
        nav_row.append(KeyboardButton(text="Следующая ▶️"))
    
    if nav_row:
        kb.append(nav_row)
    kb.append([KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")])
    
    return text, ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_error_accounts_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="Авторизовать все")],
        [KeyboardButton(text="Выбрать аккаунт")],
        [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_logs_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="Ошибки"), KeyboardButton(text="Все логи")],
        [KeyboardButton(text="По дате"), KeyboardButton(text="По типу")],
        [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
