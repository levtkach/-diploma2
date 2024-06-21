from config import dp
from aiogram import types

from config import get_student_ids, SessionLocal, bot
from keyboards import student_keyboard as main_keyboard
from database.models import *


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_student_ids()
    and message.text == "Ближайший урок📝",
)
async def next_lesson(message: types.Message):
    session = SessionLocal()
    student = User.get_user_by_telegram_id(session, str(message.from_user.id))
    next_lesson = Lesson.get_next_lesson_for_student(session, student.id)

    if next_lesson:
        group = Group.get_group_by_id(session, next_lesson.group_id)
        teacher = User.get_user_by_id(session, group.teacher_id)
        text = f"Ближайший урок будет *{next_lesson.datetime.strftime('%d/%m/%Y')}* в *{next_lesson.datetime.strftime('%H:%M')}*.\nГруппа: *{group.name}*\nПреподаватель: *{teacher.name} {teacher.surname}*"

    else:
        text = "Ближайший урок не найден."

    await message.reply(
        parse_mode=types.ParseMode.MARKDOWN,
        reply_markup=main_keyboard,
        text=text,
    )
    session.close()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_student_ids()
    and message.text == "Домашнее задание📚",
)
async def last_lesson(message: types.Message):
    session = SessionLocal()
    student = User.get_user_by_telegram_id(session, str(message.from_user.id))

    last_lesson = Lesson.get_last_completed_lesson_for_student(session, student.id)
    if last_lesson:
        group = Group.get_group_by_id(session, last_lesson.group_id)
        teacher = User.get_user_by_id(session, group.teacher_id)
        text = (
            f"Домашнее задание за *{last_lesson.datetime.strftime('%d/%m/%Y')}* группы *{group.name}*\n"
            + f"\nЗадание:\n_{last_lesson.task}_"
            if last_lesson.task
            else "Домашнего задания нет!"
        )
        if file_id := last_lesson.task_file:
            try:
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=file_id,
                    caption=text,
                    parse_mode=types.ParseMode.MARKDOWN,
                )
            except:
                await bot.send_document(
                    chat_id=message.chat.id,
                    document=file_id,
                    caption=text,
                    parse_mode=types.ParseMode.MARKDOWN,
                )
            return
    else:
        text = "У вас еще не было уроков!"

    await message.reply(
        parse_mode=types.ParseMode.MARKDOWN,
        reply_markup=main_keyboard,
        text=text,
    )
    session.close()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_student_ids()
    and message.text == "Расписание📅",
)
async def month_schedule(message: types.Message):
    session = SessionLocal()
    student = User.get_user_by_telegram_id(session, str(message.from_user.id))
    next_month_lessons = (
        Lesson.get_student_lessons_next_month(session, student.id) or []
    )

    message_text = await Lesson.send_result_message(
        next_month_lessons, ["group_id", "datetime", "teacher"]
    )

    await message.reply(
        parse_mode=types.ParseMode.MARKDOWN,
        reply_markup=main_keyboard,
        text=message_text,
    )
    session.close()
