from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from models.account import Account, AccountStatus
from services.account_service import AccountService
from ..utils.validators import validate_phone_number
from keyboards import (
    get_admin_menu, get_accounts_menu,
    get_account_actions_kb, get_yes_no_kb
)

router = Router()

class AccountStates(StatesGroup):
    ENTER_PHONE = State()
    ENTER_CODE = State()
    ENTER_PASSWORD = State()
    CONFIRM_ACTION = State()

class AccountHandler:
    def __init__(self, account_service: AccountService):
        self.account_service = account_service

    @router.message(F.text == "Добавить аккаунт")
    async def start_add_account(self, message: types.Message, state: FSMContext):
        if not await self._check_admin(message):
            return
            
        await state.set_state(AccountStates.ENTER_PHONE)
        await message.reply(
            "Введите номер телефона в формате +7XXXXXXXXXX:",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[[types.KeyboardButton(text="Отмена")]],
                resize_keyboard=True
            )
        )

    @router.message(AccountStates.ENTER_PHONE)
    async def process_phone(self, message: types.Message, state: FSMContext):
        if message.text == "Отмена":
            await state.clear()
            await message.reply("Действие отменено", reply_markup=get_admin_menu())
            return

        is_valid, error = validate_phone_number(message.text)
        if not is_valid:
            await message.reply(f"Ошибка: {error}")
            return

        await state.update_data(phone=message.text)
        await state.set_state(AccountStates.ENTER_CODE)
        await message.reply(
            "Введите код из SMS:",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[[types.KeyboardButton(text="Отмена")]],
                resize_keyboard=True
            )
        )

    @router.message(AccountStates.ENTER_CODE)
    async def process_code(self, message: types.Message, state: FSMContext):
        if message.text == "Отмена":
            await state.clear()
            await message.reply("Действие отменено", reply_markup=get_admin_menu())
            return

        data = await state.get_data()
        phone = data.get("phone")
        
        try:
            result, error, extra = await self.account_service.add_account(
                phone, {"auth_code": message.text}
            )
            
            if extra.get("needs_password"):
                await state.set_state(AccountStates.ENTER_PASSWORD)
        except Exception as e:
            logging.exception("Error while adding account")
            await message.reply(f"Произошла ошибка: {e}")
            await state.clear()
            return