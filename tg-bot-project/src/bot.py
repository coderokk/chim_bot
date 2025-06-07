from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import asyncio
import logging
import re
from typing import Dict, List, Optional, Union

import aiosqlite

import config
from database import Database

# Импортируйте или определите исключения для обработки ошибок номеров телефонов
try:
    from telethon.errors.rpcerrorlist import PhoneNumberInvalidError as PhoneNumberInvalid, PhoneNumberBannedError as PhoneNumberBanned, FloodWaitError
except ImportError:
    class PhoneNumberInvalid(Exception): pass
    class PhoneNumberBanned(Exception): pass
    class FloodWaitError(Exception):
        def __init__(self, seconds=60):
            self.seconds = seconds
from utils.keyboards import (
    get_main_menu,
    get_admin_menu,
    get_accounts_menu,
    get_task_type_kb,
    get_pagination_kb,
    get_reactions_kb,
    get_speed_kb,
    get_yes_no_kb
)
from models import Paginator, TaskStats, Task, Account

# Инициализация
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_BOT_TOKEN":
    raise ValueError("Токен бота не настроен. Проверьте файл .env")

logging.info(f"Используемый токен: '{config.BOT_TOKEN}'")
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()
db = Database(config.DB_PATH)

# Состояния FSM
class BotStates(StatesGroup):
    MAIN_MENU = State()
    NEW_TASK = State()
    ENTER_LINK = State()
    CHOOSE_ACTION = State()
    ENTER_REACTIONS = State()
    ENTER_VIEWS = State()
    ENTER_SCHEDULE = State()
    ADMIN_PANEL = State()
    ADD_ACCOUNT = State()
    ENTER_PHONE = State()
    ENTER_CODE = State()
    ENTER_PASSWORD = State()
    VIEW_TASKS = State()
    VIEW_ACCOUNTS = State()

# Функции для кнопок
def get_main_menu_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="Новая задача"), KeyboardButton(text="Мои задачи")],
        [KeyboardButton(text="Админ панель")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Добро пожаловать!", reply_markup=get_main_menu())
    await state.set_state(BotStates.MAIN_MENU)

@dp.message(F.text == "Новая задача")
async def new_task(message: types.Message, state: FSMContext):
    # Проверка количества активных задач
    tasks = await db.get_user_tasks(message.from_user.id)
    active_tasks = [t for t in tasks if t["status"] == "active"]
    
    if len(active_tasks) >= config.MAX_TASKS_PER_USER:
        await message.answer("Достигнут лимит активных задач")
        return
        
    await state.set_state(BotStates.ENTER_LINK)
    await message.answer("Введите ссылку:")

@dp.message(BotStates.ENTER_LINK)
async def process_link(message: types.Message, state: FSMContext):
    link = message.text
    await state.update_data(link=link)
    
    # Проверка на тип ссылки (канал или бот)
    if "t.me/" in link:
        if link.startswith("@") or "/bot" in link:
            kb = [
                [KeyboardButton(text="ПР"), KeyboardButton(text="ПРП"), KeyboardButton(text="ПРПС")],
                [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
            ]
        else:
            kb = [
                [KeyboardButton(text="Реакции"), KeyboardButton(text="Просмотры")],
                [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
            ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        await state.set_state(BotStates.CHOOSE_ACTION)
        await message.answer("Выберите действие:", reply_markup=reply_markup)
    else:
        await message.answer("Неверная ссылка. Попробуйте еще раз.")

# Добавим обработчики для разных типов задач
@dp.message(BotStates.CHOOSE_ACTION)
async def process_action(message: types.Message, state: FSMContext):
    action = message.text
    data = await state.get_data()
    
    if action == "Реакции":
        kb = [
            [KeyboardButton(text="👍"), KeyboardButton(text="❤️"), KeyboardButton(text="🔥")],
            [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        await state.set_state(BotStates.ENTER_REACTIONS)
        await message.answer("Выберите реакции:", reply_markup=reply_markup)
    
    elif action in ["ПР", "ПРП", "ПРПС"]:
        kb = [
            [KeyboardButton(text="24/7"), KeyboardButton(text="График")],
            [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
        ]
        await state.update_data(action=action)
        await state.set_state(BotStates.ENTER_SCHEDULE)
        await message.answer("Выберите расписание:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

# Админ-панель
@dp.message(F.text == "Админ панель")
async def admin_panel(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logging.info(f"Попытка доступа к админ-панели от пользователя {user_id}")
    logging.info(f"Текущие админы: {config.ADMIN_IDS}")
    
    if not isinstance(config.ADMIN_IDS, set):
        logging.error(f"ADMIN_IDS неверного типа: {type(config.ADMIN_IDS)}")
        await message.answer("Ошибка конфигурации админов")
        return
        
    if user_id not in config.ADMIN_IDS:
        logging.warning(f"Отказано в доступе пользователю {user_id}")
        await message.answer("Доступ запрещен")
        return
    
    logging.info(f"Доступ разрешен для админа {user_id}")
    kb = [
        [KeyboardButton(text="Аккаунты"), KeyboardButton(text="Задачи")],
        [KeyboardButton(text="Логи"), KeyboardButton(text="Назад")]
    ]
    await state.set_state(BotStates.ADMIN_PANEL)
    await message.answer("Админ-панель:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

# Управление аккаунтами
@dp.message(F.text == "Аккаунты")
async def manage_accounts(message: types.Message):
    kb = [
        [KeyboardButton(text="Добавить"), KeyboardButton(text="Список аккаунтов")],
        [KeyboardButton(text="Ошибки"), KeyboardButton(text="Назад")],
        [KeyboardButton(text="Главное меню")]
    ]
    await message.answer("Управление аккаунтами:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

# Добавление аккаунта
@dp.message(F.text == "Добавить")
async def add_account(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.ENTER_PHONE)
    await message.answer("Введите номер телефона:")

@dp.message(BotStates.ENTER_PHONE)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    logging.info(f"Получен номер телефона: {phone}")
    
    if not re.match(r'^\+7\d{10}$', phone):
        await message.answer(
            "Неверный формат номера.\n"
            "Используйте формат: +79991234567"
        )
        return

    await message.answer("⌛ Отправка кода... Подождите примерно 30 секунд.")
    
    try:
        sent_code_info = await db.send_auth_code(phone)
        
        await state.update_data(
            phone=phone,
            phone_code_hash=sent_code_info["phone_code_hash"]
        )
        
        await state.set_state(BotStates.ENTER_CODE)
        await message.answer(
            "✅ Код отправлен в Telegram!\n"
            "Проверьте уведомления в официальном приложении.\n"
            "Если код не пришел в течение минуты, нажмите 'Назад'."
        )
        
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Ошибка отправки кода: {error_msg}")
        
        if "wait of" in error_msg.lower():
            minutes = int(''.join(filter(str.isdigit, error_msg))) // 60
            await message.answer(
                f"⚠️ Нужно подождать {minutes} минут перед следующей попыткой.\n"
                "Это защита Telegram от спама."
            )
        else:
            await message.answer(
                "❌ Ошибка при отправке кода.\n"
                "Возможные причины:\n"
                "1. Неверный номер\n"
                "2. Слишком много попыток\n"
                "3. Технические проблемы\n\n"
                "Попробуйте позже или используйте другой номер."
            )
        await state.finish()

@dp.message(BotStates.ENTER_CODE)
async def process_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    data = await state.get_data()
    phone = data.get("phone")
    phone_code_hash = data.get("phone_code_hash")
    
    logging.info(f"Проверка кода для {phone}")
    
    if not all([phone, phone_code_hash]):
        await message.answer("Ошибка. Начните заново.")
        await state.clear()
        return
    
    try:
        result = await db.verify_code(phone, code, phone_code_hash)
        
        if result["success"]:
            # Код верный
            await db.add_account(phone, {"session": result["session"]})
            await message.answer("✅ Аккаунт успешно добавлен!", reply_markup=get_yes_no_kb())
            await state.clear()
            
        elif result.get("need_new_code"):
            # Код истек, отправляем новый
            await state.update_data(phone_code_hash=result["phone_code_hash"])
            await message.answer(
                "⚠️ Код истек. Отправлен новый код.\n"
                "Пожалуйста, введите его."
            )
            
        else:
            # Код неверный
            await message.answer(
                "❌ Неверный код. Попробуйте еще раз или нажмите 'Назад' для получения нового кода."
            )
            
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("Произошла ошибка. Попробуйте еще раз.")

# Управление задачами
@dp.message(F.text == "Мои задачи")
async def my_tasks(message: types.Message, state: FSMContext):
    tasks = await db.get_user_tasks(message.from_user.id)
    if not tasks:
        await message.answer("У вас нет активных задач")
        return
        
    paginator = Paginator(tasks)
    page_items, has_prev, has_next = paginator.get_page(1)
    
    tasks_text = "Ваши задачи:\n\n"
    for task in page_items:
        status = "🟢" if task.status == "active" else "🔴"
        tasks_text += f"#{task.id} - {task.type} {status}\n"
    
    kb = get_pagination_kb(has_prev, has_next)
    await message.answer(tasks_text, reply_markup=kb)
    await state.update_data(current_page=1)
    await state.set_state(BotStates.VIEW_TASKS)

# Обработка реакций
@dp.message(BotStates.ENTER_REACTIONS)
async def process_reactions(message: types.Message, state: FSMContext):
    if message.text in ["👍", "❤️", "🔥"]:
        data = await state.get_data()
        kb = [
            [KeyboardButton(text="10"), KeyboardButton(text="50"), KeyboardButton(text="100")],
            [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
        ]
        await state.update_data(reaction=message.text)
        await message.answer("Введите количество реакций:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

# Обработка просмотров
@dp.message(BotStates.ENTER_VIEWS)
async def process_views(message: types.Message, state: FSMContext):
    try:
        views = int(message.text)
        if views <= 0:
            raise ValueError
        
        kb = [
            [KeyboardButton(text="1 мин/1000"), KeyboardButton(text="5 мин/1000")],
            [KeyboardButton(text="Назад"), KeyboardButton(text="Главное меню")]
        ]
        await state.update_data(views=views)
        await message.answer("Выберите скорость:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число просмотров")

# Добавляем обработчики навигации
@dp.message(F.text == "Назад")
async def go_back(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == BotStates.MAIN_MENU:
        return
        
    states_map = {
        BotStates.ENTER_LINK: BotStates.MAIN_MENU,
        BotStates.CHOOSE_ACTION: BotStates.ENTER_LINK,
        BotStates.ENTER_REACTIONS: BotStates.CHOOSE_ACTION,
        BotStates.ENTER_VIEWS: BotStates.CHOOSE_ACTION,
        BotStates.ENTER_SCHEDULE: BotStates.CHOOSE_ACTION,
        # ...другие состояния
    }
    
    next_state = states_map.get(current_state, BotStates.MAIN_MENU)
    await state.set_state(next_state)
    
    if next_state == BotStates.MAIN_MENU:
        await message.answer("Главное меню", reply_markup=get_main_menu())
    else:
        # Восстанавливаем предыдущее состояние
        data = await state.get_data()
        await process_state(message, state, next_state, data)

@dp.message(F.text == "Главное меню")
async def to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(BotStates.MAIN_MENU)
    await message.answer("Главное меню", reply_markup=get_main_menu())

# Обработка выбора количества для реакций/просмотров
@dp.message(lambda message: message.text.isdigit())
async def process_amount(message: types.Message, state: FSMContext):
    amount = int(message.text)
    current_state = await state.get_state()
    data = await state.get_data()
    
    if amount <= 0:
        await message.answer("Количество должно быть положительным числом")
        return
        
    if current_state == BotStates.ENTER_REACTIONS:
        if amount > config.MAX_REACTIONS_PER_TASK:
            await message.answer(f"Максимальное количество реакций: {config.MAX_REACTIONS_PER_TASK}")
            return
        await state.update_data(reactions_amount=amount)
        await message.answer("Выберите скорость:", reply_markup=get_speed_kb())
        
    elif current_state == BotStates.ENTER_VIEWS:
        if amount > config.MAX_VIEWS_PER_TASK:
            await message.answer(f"Максимальное количество просмотров: {config.MAX_VIEWS_PER_TASK}")
            return
        await state.update_data(views_amount=amount)
        await message.answer("Выберите скорость:", reply_markup=get_speed_kb())

# Обработка скорости выполнения
@dp.message(lambda message: "мин/1000" in message.text)
async def process_speed(message: types.Message, state: FSMContext):
    speed = message.text.split()[0]  # "1" из "1 мин/1000"
    data = await state.get_data()
    
    task_params = {
        "speed": int(speed),
        "link": data["link"],
    }
    
    if "reactions_amount" in data:
        task_params["amount"] = data["reactions_amount"]
        task_params["reaction"] = data["reaction"]
        task_type = "reactions"
    else:
        task_params["amount"] = data["views_amount"]
        task_type = "views"
    
    try:
        task_id = await db.create_task(
            user_id=message.from_user.id,
            task_type=task_type,
            params=task_params
        )
        await message.answer(
            f"Задача #{task_id} успешно создана. Создать еще?",
            reply_markup=get_yes_no_kb()
        )
    except Exception as e:
        await message.answer(f"Ошибка при создании задачи: {str(e)}")

# Удаляем дублирующийся класс Paginator и функции валидации

async def process_state(message: types.Message, state: FSMContext, next_state: State, data: Dict):
    """Вспомогательная функция для обработки состояний"""
    if next_state == BotStates.CHOOSE_ACTION:
        await message.answer("Выберите действие:", reply_markup=get_task_type_kb(data.get("link", "")))
    elif next_state == BotStates.ENTER_REACTIONS:
        await message.answer("Выберите реакции:", reply_markup=get_reactions_kb())
    # ...добавьте другие состояния при необходимости

# Обработка списка аккаунтов с пагинацией
@dp.message(F.text == "Список аккаунтов")
async def list_accounts(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("Доступ запрещен")
        return
        
    accounts = await db.get_all_accounts()
    paginator = Paginator(accounts)
    page_items, has_prev, has_next = paginator.get_page(1)
    
    text = "Список аккаунтов:\n\n"
    for i, account in enumerate(page_items, 1):
        status = "🟢" if account.status == "active" else "🔴"
        text += f"{i}. {account.phone} {status}\n"
    
    kb = get_pagination_kb(has_prev, has_next)
    await message.answer(text, reply_markup=kb)
    await state.update_data(current_page=1)
    await state.set_state(BotStates.VIEW_ACCOUNTS)

@dp.message(BotStates.ENTER_CODE)
async def process_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    data = await state.get_data()
    phone = data.get("phone")
    phone_code_hash = data.get("phone_code_hash")
    
    logging.info(f"Проверка кода для {phone}")
    
    if not all([phone, phone_code_hash]):
        await message.answer("Ошибка. Начните заново.")
        await state.clear()
        return
    
    try:
        result = await db.verify_code(phone, code, phone_code_hash)
        
        if result["success"]:
            # Код верный
            await db.add_account(phone, {"session": result["session"]})
            await message.answer("✅ Аккаунт успешно добавлен!", reply_markup=get_yes_no_kb())
            await state.clear()
            
        elif result.get("need_new_code"):
            # Код истек, отправляем новый
            await state.update_data(phone_code_hash=result["phone_code_hash"])
            await message.answer(
                "⚠️ Код истек. Отправлен новый код.\n"
                "Пожалуйста, введите его."
            )
            
        else:
            # Код неверный
            await message.answer(
                "❌ Неверный код. Попробуйте еще раз или нажмите 'Назад' для получения нового кода."
            )
            
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("Произошла ошибка. Попробуйте еще раз.")

# Обработка ошибок
@dp.errors()
async def error_handler(update: types.Update, exception: Exception):
    logging.error(f"Ошибка при обработке update {update}: {exception}")
    if update.message:
        await update.message.answer(
            "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.",
            reply_markup=get_main_menu_kb()
        )

async def on_startup(dp: Dispatcher):
    try:
        # Инициализация БД
        await db.init()
        logging.info("Database initialized")
        
        # Получение активных задач
        tasks = await db.get_active_tasks()
        logging.info(f"Found {len(tasks)} active tasks")
        
        # Создание и запуск задач
        for task_data in tasks:
            if all(key in task_data for key in ["id", "user_id", "link", "type"]):
                task = Task(
                    task_id=task_data["id"],
                    user_id=task_data["user_id"],
                    link=task_data["link"],
                    task_type=task_data["type"]
                )
                asyncio.create_task(process_task(task))
            else:
                logging.error(f"Invalid task data: {task_data}")
        
    except Exception as e:
        logging.error(f"Startup error: {e}")
        raise

async def process_reactions_task(task):
    # TODO: Реализуйте обработку задачи с реакциями
    logging.info(f"Processing reactions task #{task.id}")
    await asyncio.sleep(1)  # Имитация работы

async def process_bot_task(task):
    # TODO: Реализуйте обработку задачи для типов "pr", "prp", "prps"
    logging.info(f"Processing bot task #{task.id}")
    await asyncio.sleep(1)  # Имитация работы

async def process_views_task(task):
    # TODO: Реализуйте обработку задачи с просмотрами
    logging.info(f"Processing views task #{task.id}")
    await asyncio.sleep(1)  # Имитация работы

async def process_task(task):
    while task.should_run():
        try:
            # Обработка задачи в зависимости от типа
            if task.type == "reactions":
                await process_reactions_task(task)
            elif task.type in ["pr", "prp", "prps"]:
                await process_bot_task(task)
            else:
                await process_views_task(task)
                
            await asyncio.sleep(config.TASK_CHECK_INTERVAL)
        except Exception as e:
            logging.error(f"Error processing task {task.id}: {e}")
            await asyncio.sleep(config.ERROR_RETRY_DELAY)

async def main():
    try:
        logging.info("Starting bot...")
        await on_startup(dp)
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
    finally:
        logging.info("Shutting down...")
        await bot.session.close()
        logging.info("Bot stopped")

if __name__ == "__main__":
    import sys
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main())