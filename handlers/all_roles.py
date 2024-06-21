from config import dp
from aiogram import types
from aiogram.dispatcher import FSMContext

from config import (
    get_all_ids,
    SessionLocal,
    get_admin_ids,
    get_student_ids,
    get_teacher_ids,
)
from keyboards import admin_keyboard, teacher_keyboard, student_keyboard


async def get_main_keyboard(telegram_id):
    if telegram_id in get_admin_ids():
        return admin_keyboard
    elif telegram_id in get_teacher_ids():
        return teacher_keyboard
    elif telegram_id in get_student_ids():
        return student_keyboard


"""ВСЕ НЕУЧТЕННОЕ С РОЛЬЮ"""


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_all_ids(),
    state="*",
)
async def process_confirm(message: types.Message, state: FSMContext):
    main_keyboard = await get_main_keyboard(str(message.from_user.id))
    await message.reply(
        (
            f"Я вас не понимаю. Доступные команды показаны на клавиатуре."
            if message.text != "Начать👋"
            else "Вам доступны следующие функции:"
        ),
        reply_markup=main_keyboard,
    )
