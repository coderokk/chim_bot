from aiogram import types, F
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.filters.state import State, StatesGroup
import logging

from config import config
from services.account_service import AccountService
from services.task_service import TaskService
from utils.keyboards import (
    get_admin_menu, get_accounts_menu, get_tasks_menu,
    get_pagination_kb, get_yes_no_kb
)

class AdminStates(StatesGroup):
    MAIN = State()
    ADD_ACCOUNT = State()
    ENTER_PHONE = State()
    ENTER_CODE = State()
    ENTER_PASSWORD = State()
    VIEW_ACCOUNTS = State()
    VIEW_TASKS = State()
    VIEW_LOGS = State()
    CONFIRM_ACTION = State()

# Initialize services
account_service = AccountService()
task_service = TaskService()

async def check_admin(message: types.Message) -> bool:
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("Доступ запрещен")
        return False
    return True

async def admin_panel(message: types.Message, state: FSMContext):
    if not await check_admin(message):
        return
        
    await state.set_state(AdminStates.MAIN)
    await message.answer(
        "Админ-панель\n"
        "Выберите действие:",
        reply_markup=get_admin_menu()
    )

async def handle_accounts(message: types.Message, state: FSMContext):
    if not await check_admin(message):
        return
        
    await state.set_state(AdminStates.VIEW_ACCOUNTS)
    accounts = await account_service.get_all_accounts()
    text = "Аккаунты:\n\n"
    
    for acc in accounts:
        status = "🟢" if acc.status == "active" else "🔴"
        text += f"{acc.phone} {status}\n"
        
    await message.answer(text, reply_markup=get_accounts_menu())

async def handle_add_account(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.ENTER_PHONE)
    await message.answer(
        "Введите номер телефона в формате: +79991234567",
        reply_markup=types.ReplyKeyboardRemove()
    )

async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text
    is_valid, error = await account_service.validate_phone(phone)
    
    if not is_valid:
        await message.answer(f"Ошибка: {error}")
        return
        
    await state.update_data(phone=phone)
    await state.set_state(AdminStates.ENTER_CODE)
    await message.answer("Введите код из СМС:")

async def process_code(message: types.Message, state: FSMContext):
    try:
        code = message.text
        data = await state.get_data()
        phone = data.get("phone")
        
        success, error = await account_service.verify_code(phone, code)
        if not success:
            await message.answer(f"Ошибка: {error}")
            return
            
        if error == "needs_password":
            await state.set_state(AdminStates.ENTER_PASSWORD)
            await message.answer("Введите облачный пароль:")
            return
            
        await finalize_account_adding(message, state)
        
    except Exception as e:
        logging.error(f"Error processing code: {e}")
        await message.answer("Произошла ошибка при обработке кода")

async def finalize_account_adding(message: types.Message, state: FSMContext):
    data = await state.get_data()
    success, error = await account_service.add_account(
        phone=data["phone"],
        auth_data=data
    )
    
    if success:
        await message.answer(
            "Аккаунт успешно добавлен. Добавить еще?",
            reply_markup=get_yes_no_kb()
        )
    else:
        await message.answer(f"Ошибка: {error}")
        await state.set_state(AdminStates.MAIN)
        await message.answer("Вернуться в меню?", reply_markup=get_admin_menu())

def register_admin_handlers(dp: Dispatcher):
    dp.message.register(admin_panel, F.text == "Админ панель")
    dp.message.register(handle_accounts, F.text == "Аккаунты")
    dp.message.register(handle_add_account, F.text == "Добавить")
    dp.message.register(process_phone, AdminStates.ENTER_PHONE)
    dp.message.register(process_code, AdminStates.ENTER_CODE)
    
    # Добавьте остальные хендлеры по необходимости