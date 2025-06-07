from aiogram import types, F
from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging
import config

from services.reaction_service import ReactionService
from utils.validators import validate_telegram_link
from utils.keyboards import (
    get_reactions_kb, get_amount_kb,
    get_speed_kb, get_yes_no_kb, get_bot_actions_kb, get_main_menu
)

reaction_service = ReactionService()

class ReactionStates(StatesGroup):
    ENTER_LINK = State()
    CHOOSE_TYPE = State()
    CHOOSE_REACTIONS = State()
    ENTER_AMOUNT = State()
    CHOOSE_SPEED = State()
    CONFIRM = State()

def setup_reaction_handlers(router):
    router.message.register(start_reaction_task, F.text == "Новая задача")
    router.message.register(process_link, ReactionStates.ENTER_LINK)
    router.message.register(process_type, ReactionStates.CHOOSE_TYPE)
    router.message.register(process_reactions, ReactionStates.CHOOSE_REACTIONS)
    router.message.register(process_amount, ReactionStates.ENTER_AMOUNT)
    router.message.register(process_speed, ReactionStates.CHOOSE_SPEED)
    router.message.register(confirm_task, ReactionStates.CONFIRM)

async def start_reaction_task(message: types.Message, state: FSMContext):
    await state.set_state(ReactionStates.ENTER_LINK)
    await message.answer(
        "Введите ссылку на пост или канал:",
        reply_markup=types.ReplyKeyboardRemove()
    )

async def process_link(message: types.Message, state: FSMContext):
    is_valid, link_type, error = validate_telegram_link(message.text)
    if not is_valid:
        await message.answer(f"Ошибка: {error}")
        return

    await state.update_data(link=message.text, link_type=link_type)
    
    if link_type == "channel":
        kb = get_reactions_kb()
        text = "Выберите тип действия:"
    else:
        kb = get_bot_actions_kb()
        text = "Выберите тип действия для бота:"
        
    await state.set_state(ReactionStates.CHOOSE_TYPE)
    await message.answer(text, reply_markup=kb)

async def process_type(message: types.Message, state: FSMContext):
    action_type = message.text
    data = await state.get_data()
    
    if data["link_type"] == "channel":
        if action_type == "Реакции":
            await state.set_state(ReactionStates.CHOOSE_REACTIONS)
            await message.answer(
                "Выберите реакции:",
                reply_markup=get_reactions_kb()
            )
        elif action_type == "Просмотры":
            await state.set_state(ReactionStates.ENTER_AMOUNT)
            await message.answer(
                "Введите количество просмотров:",
                reply_markup=get_amount_kb()
            )
    else:  # bot
        await state.update_data(action_type=action_type)
        await state.set_state(ReactionStates.ENTER_AMOUNT)
        await message.answer(
            "Введите количество действий:",
            reply_markup=get_amount_kb()
        )

async def process_reactions(message: types.Message, state: FSMContext):
    reaction = message.text
    data = await state.get_data()
    reactions = data.get("reactions", {})
    
    if reaction in ["👍", "❤️", "🔥", "😱", "🤬", "😢"]:
        reactions[reaction] = reactions.get(reaction, 0) + 1
        await state.update_data(reactions=reactions)
        
        total = sum(reactions.values())
        await message.answer(
            f"Добавлена реакция {reaction}\n"
            f"Всего реакций: {total}\n"
            "Добавить еще или продолжить?",
            reply_markup=get_reactions_kb(add_continue=True)
        )
    elif reaction == "Продолжить":
        await state.set_state(ReactionStates.CHOOSE_SPEED)
        await message.answer(
            "Выберите скорость выполнения:",
            reply_markup=get_speed_kb()
        )

async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        data = await state.get_data()
        
        if data.get("link_type") == "channel":
            max_amount = config.MAX_VIEWS_PER_TASK
        else:
            max_amount = config.MAX_BOT_ACTIONS_PER_TASK
            
        if amount > max_amount:
            await message.answer(f"Максимальное количество: {max_amount}")
            return
            
        await state.update_data(amount=amount)
        await state.set_state(ReactionStates.CHOOSE_SPEED)
        await message.answer(
            "Выберите скорость выполнения:",
            reply_markup=get_speed_kb()
        )
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число")

async def process_speed(message: types.Message, state: FSMContext):
    speed = message.text
    if not speed.endswith("мин/1000"):
        await message.answer("Неверный формат скорости")
        return
        
    await state.update_data(speed=speed)
    data = await state.get_data()
    
    summary = "Проверьте параметры задачи:\n\n"
    summary += f"Ссылка: {data['link']}\n"
    if "reactions" in data:
        summary += "Реакции:\n"
        for reaction, count in data["reactions"].items():
            summary += f"{reaction}: {count}\n"
    else:
        summary += f"Количество: {data['amount']}\n"
    summary += f"Скорость: {speed}\n"
    
    await state.set_state(ReactionStates.CONFIRM)
    await message.answer(
        f"{summary}\nПодтвердить создание задачи?",
        reply_markup=get_yes_no_kb()
    )

async def confirm_task(message: types.Message, state: FSMContext):
    if message.text.lower() == "да":
        try:
            data = await state.get_data()
            task_id = await reaction_service.create_task(
                user_id=message.from_user.id,
                **data
            )
            await message.answer(
                f"Задача #{task_id} успешно создана. Создать еще?",
                reply_markup=get_yes_no_kb()
            )
        except Exception as e:
            logging.error(f"Error creating task: {e}")
            await message.answer(
                "Произошла ошибка при создании задачи",
                reply_markup=get_main_menu()
            )
    else:
        await message.answer(
            "Создание задачи отменено",
            reply_markup=get_main_menu()
        )
    
    await state.clear()