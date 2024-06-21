from config import dp
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from config import (
    get_all_ids,
    SessionLocal,
    get_admin_ids,
    get_student_ids,
    get_teacher_ids,
)

from keyboards import admin_keyboard, teacher_keyboard, student_keyboard, start_keyboard
from database.models import *


"""ОБЩИЕ КОМАНДЫ"""


async def get_main_keyboard(telegram_id):
    if telegram_id in get_admin_ids():
        return admin_keyboard
    elif telegram_id in get_teacher_ids():
        return teacher_keyboard
    elif telegram_id in get_student_ids():
        return student_keyboard


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_all_ids()
    and "отмена" in message.text.lower(),
    state="*",
)
async def cancel_operation(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    main_keyboard = await get_main_keyboard(str(message.from_user.id))
    if current_state is None:
        await message.reply(
            "Не запущено никаких процессов.", reply_markup=main_keyboard
        )
        return

    await state.finish()
    await message.reply("Операция отменена.", reply_markup=main_keyboard)


async def go_to_previous_state(
    message: types.Message, state: FSMContext, main_keyboard
):
    current_state = await state.get_state()

    if current_state is None:
        await message.reply(
            "Не запущено никаких процессов.", reply_markup=main_keyboard
        )
        return

    state_cls_name = current_state.split(":")[0]
    state_cls = None
    for subclass in StatesGroup.__subclasses__():
        if subclass.__name__ == state_cls_name:
            state_cls = subclass
            break

    if state_cls is None:
        await message.reply("Что-то пошло не так.", reply_markup=main_keyboard)
        return

    all_states = [s.state for s in state_cls.states]

    try:
        current_state_index = all_states.index(current_state)
        if current_state_index > 0:
            previous_state = all_states[current_state_index - 1]
            await state.set_state(previous_state)
            await message.reply(f"Вернулись к предыдущему этапу.")
        else:
            await message.reply("Назад вернуться нельзя.")
    except ValueError:
        await message.reply("Назад вернуться нельзя.")


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_all_ids()
    and "Назад" in message.text,
    state="*",
)
async def cancel_operation(message: types.Message, state: FSMContext):
    main_keyboard = await get_main_keyboard(str(message.from_user.id))
    await go_to_previous_state(message, state, main_keyboard)


"""КОМАНДЫ БЕЗ РОЛИ"""


@dp.message_handler(
    lambda message: str(message.from_user.id) not in get_all_ids()
    and "key:" in message.text,
)
async def set_key(message: types.Message):
    session = SessionLocal()
    user = User.get_user_by_api_key(session=session, api_key=message.text)

    if user:
        user.telegram_id = str(message.from_user.id)
        session.commit()
        response = f"Вы успешно авторизированы, {user.name}!"
        keyboard = start_keyboard
    else:
        response = f"Что-то пошло не так. Попробуйте еще раз."
        keyboard = types.ReplyKeyboardRemove()
    session.close()
    await message.reply(
        response,
        reply_markup=keyboard,
    )


@dp.message_handler(lambda message: str(message.from_user.id) not in get_all_ids())
async def set_key(message: types.Message):
    await message.reply(
        "Вы не авторизированны. \nПришлите свой ключ в формате key:1234.",
        reply_markup=types.ReplyKeyboardRemove(),
    )
