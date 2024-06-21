from aiogram import types
from aiogram.types import ReplyKeyboardRemove
from config import dp, SessionLocal, bot, Base, engine, update_ids
from database.models import *
import aiohttp, os
from aiogram.types import InputFile


async def download_file(url, filename):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(filename, "wb") as f:
                    f.write(await response.read())
                return filename
            else:
                return None


@dp.message_handler(
    lambda message: message.chat.type in ["group", "supergroup"],
    commands=["new_chat"],
)
async def new_chat(message: types.Message):
    chat_title = message.chat.title if message.chat.title else None
    session = SessionLocal()
    groups = Group.get_group_by_field(session, "name", chat_title)
    group = groups[0] if groups else None

    if group:
        if not group.chat_id:
            text = "Группа зарегистрирована."
        else:
            text = "Группа зарегистрирована заново."
        chat = await bot.get_chat(message.chat.id)
        group.chat_id = message.chat.id
        course = Course.get_course_by_id(session, group.course_id)

        if course.description and not chat.description:

            await bot.set_chat_description(
                chat_id=message.chat.id, description=course.description
            )

    else:
        text = "Группа не найдена. Убедитесь, что название группы правильное."

    session.commit()
    session.close()
    await message.reply(text, reply_markup=ReplyKeyboardRemove())
