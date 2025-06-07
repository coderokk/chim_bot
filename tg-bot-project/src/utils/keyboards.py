from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

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
    kb = []
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

def get_task_type_kb(link_type: str = "") -> ReplyKeyboardMarkup:
    if "bot" in link_type:
        kb = [
            [KeyboardButton(text="ПР"), KeyboardButton(text="ПРП"), KeyboardButton(text="ПРПС")],
            [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
        ]
    else:
        kb = [
            [KeyboardButton(text="Реакции"), KeyboardButton(text="Просмотры")],
            [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
        ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_pagination_kb(has_prev: bool, has_next: bool) -> ReplyKeyboardMarkup:
    kb = []
    nav_row = []
    if has_prev:
        nav_row.append(KeyboardButton(text="◀️ Назад"))
    if has_next:
        nav_row.append(KeyboardButton(text="Вперед ▶️"))
    if nav_row:
        kb.append(nav_row)
    kb.append([KeyboardButton(text="Главное меню")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_reactions_kb(add_continue: bool = False) -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="👍"), KeyboardButton(text="❤️"), KeyboardButton(text="🔥")],
        [KeyboardButton(text="😱"), KeyboardButton(text="🤬"), KeyboardButton(text="😢")]
    ]
    if add_continue:
        kb.append([KeyboardButton(text="Продолжить")])
    kb.append([KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_speed_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="1 мин/1000"), KeyboardButton(text="3 мин/1000")],
        [KeyboardButton(text="5 мин/1000"), KeyboardButton(text="10 мин/1000")],
        [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_yes_no_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
        [KeyboardButton(text="Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_schedule_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="24/7"), KeyboardButton(text="График")],
        [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)