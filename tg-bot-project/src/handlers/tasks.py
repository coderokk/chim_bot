from aiogram import types, F
from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging
from datetime import datetime

import config
from models.task import Task, TaskType, TaskStatus
from services.task_service import TaskService
from ..utils.validators import validate_telegram_link
from utils.keyboards import (
    get_task_type_kb, get_schedule_kb,
    get_speed_kb, get_yes_no_kb,
    get_main_menu
)

# Initialize the task service
task_service = TaskService()

class TaskStates(StatesGroup):
    ENTER_LINK = State()
    CHOOSE_TYPE = State()
    ENTER_AMOUNT = State()
    CHOOSE_SCHEDULE = State()
    ENTER_HOURS = State()
    CHOOSE_SPEED = State()
    CONFIRM = State()

def setup_task_handlers(router):
    router.message.register(start_task, F.text == "Новая задача")
    router.message.register(process_link, TaskStates.ENTER_LINK)
    router.message.register(process_type, TaskStates.CHOOSE_TYPE)
    router.message.register(process_amount, TaskStates.ENTER_AMOUNT)
    router.message.register(process_schedule, TaskStates.CHOOSE_SCHEDULE)
    router.message.register(process_hours, TaskStates.ENTER_HOURS)
    router.message.register(process_speed, TaskStates.CHOOSE_SPEED)
    router.message.register(confirm_task, TaskStates.CONFIRM)

async def start_task(message: types.Message, state: FSMContext):
    # Проверяем количество активных задач
    user_tasks = await task_service.get_user_active_tasks(message.from_user.id)
    if len(user_tasks) >= config.MAX_TASKS_PER_USER:
        await message.answer(
            f"Достигнут лимит активных задач ({config.MAX_TASKS_PER_USER})",
            reply_markup=get_main_menu()
        )
        return

    await state.set_state(TaskStates.ENTER_LINK)
    await message.answer(
        "Введите ссылку на канал или бота:",
        reply_markup=types.ReplyKeyboardRemove()
    )

async def process_link(message: types.Message, state: FSMContext):
    is_valid, link_type, error = validate_telegram_link(message.text)
    if not is_valid:
        await message.answer(f"Ошибка: {error}")
        return

    # Проверяем существующие задачи для этой ссылки
    existing_task = await task_service.get_task_by_link(message.text)
    if existing_task and existing_task.status == TaskStatus.ACTIVE:
        await message.answer(
            f"Уже есть активная задача #{existing_task.id} для этой ссылки",
            reply_markup=get_main_menu()
        )
        return

    await state.update_data(link=message.text, link_type=link_type)
    await state.set_state(TaskStates.CHOOSE_TYPE)
    await message.answer(
        "Выберите тип задачи:",
        reply_markup=get_task_type_kb(link_type)
    )

async def process_type(message: types.Message, state: FSMContext):
    data = await state.get_data()
    task_type = message.text
    
    valid_types = {
        "channel": ["Реакции", "Просмотры"],
        "bot": ["ПР", "ПРП", "ПРПС"]
    }
    
    if task_type not in valid_types[data["link_type"]]:
        await message.answer("Неверный тип задачи")
        return

    await state.update_data(task_type=task_type)
    
    if task_type == "Реакции":
        await state.set_state(TaskStates.CHOOSE_SCHEDULE)
        await message.answer(
            "Выберите расписание:",
            reply_markup=get_schedule_kb()
        )
    else:
        await state.set_state(TaskStates.ENTER_AMOUNT)
        await message.answer(
            "Введите количество:",
            reply_markup=types.ReplyKeyboardRemove()
        )

async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        data = await state.get_data()
        
        # Проверяем лимиты в зависимости от типа задачи
        max_amount = config.TASK_LIMITS[data["task_type"]]
        if amount > max_amount:
            await message.answer(f"Максимальное количество: {max_amount}")
            return

        await state.update_data(amount=amount)
        await state.set_state(TaskStates.CHOOSE_SCHEDULE)
        await message.answer(
            "Выберите расписание выполнения:",
            reply_markup=get_schedule_kb()
        )
    except ValueError:
        await message.answer("Введите корректное число")

async def process_schedule(message: types.Message, state: FSMContext):
    schedule = message.text
    if schedule == "24/7":
        await state.update_data(schedule={"type": "constant"})
        await state.set_state(TaskStates.CHOOSE_SPEED)
        await message.answer(
            "Выберите скорость выполнения:",
            reply_markup=get_speed_kb()
        )
    elif schedule == "График по часам":
        await state.set_state(TaskStates.ENTER_HOURS)
        await message.answer(
            "Введите часы через запятую (0-23):",
            reply_markup=types.ReplyKeyboardRemove()
        )
    else:
        await message.answer("Неверный формат расписания")

async def process_hours(message: types.Message, state: FSMContext):
    try:
        hours = [int(h.strip()) for h in message.text.split(",")]
        if not all(0 <= h <= 23 for h in hours):
            await message.answer("Часы должны быть в диапазоне 0-23")
            return
        await state.update_data(schedule={"type": "hours", "hours": hours})
        await state.set_state(TaskStates.CHOOSE_SPEED)
        await message.answer(
            "Выберите скорость выполнения:",
            reply_markup=get_speed_kb()
        )
    except Exception:
        await message.answer("Введите часы через запятую, например: 9, 12, 18")

async def process_speed(message: types.Message, state: FSMContext):
    speed = message.text
    if not speed.endswith("мин/1000"):
        await message.answer("Неверный формат скорости")
        return

    data = await state.get_data()
    await state.update_data(speed=int(speed.split()[0]))
    
    # Формируем сводку задачи
    summary = (
        f"Проверьте параметры задачи:\n"
        f"Ссылка: {data['link']}\n"
        f"Тип: {data['task_type']}\n"
        f"Количество: {data['amount']}\n"
        f"Расписание: {data['schedule']['type']}\n"
        f"Скорость: {speed}"
    )
    
    await state.set_state(TaskStates.CONFIRM)
    await message.answer(
        f"{summary}\n\nСоздать задачу?",
        reply_markup=get_yes_no_kb()
    )

async def confirm_task(message: types.Message, state: FSMContext):
    if message.text == "Да":
        data = await state.get_data()
        task = Task(
            user_id=message.from_user.id,
            link=data["link"],
            task_type=data["task_type"],
            amount=data["amount"],
            schedule=data["schedule"],
            speed=data["speed"],
            status=TaskStatus.ACTIVE,
            created_at=datetime.now()
        )
        await task_service.create_task(task)
        await message.answer("Задача успешно создана!", reply_markup=get_main_menu())
    else:
        await message.answer("Создание задачи отменено.", reply_markup=get_main_menu())
    
    await state.clear()