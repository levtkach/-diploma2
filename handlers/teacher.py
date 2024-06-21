from datetime import datetime, timedelta
from aiogram import types

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram_calendar import (
    simple_cal_callback,
    SimpleCalendar,
    dialog_cal_callback,
    DialogCalendar,
    DateDialogCalendar,
)

from config import (
    dp,
    get_teacher_ids,
    SessionLocal,
    bot,
    Base,
    engine,
)
from keyboards import (
    back_or_cancel_keyboard,
    cancel_keyboard,
    cancel_back_confirm_keyboard,
    confirm_keyboard,
    cancel_continue_keyboard,
)
from keyboards import teacher_keyboard as main_keyboard

from database.models import *


async def get_teacher(message: types.Message):
    teacher_telegram_id = str(message.from_user.id)
    session = SessionLocal()
    teacher = (
        session.query(User)
        .filter(User.telegram_id == teacher_telegram_id, User.is_teacher == True)
        .first()
    )
    session.close()
    return teacher


async def not_teacher(message: types.Message):
    await message.reply(
        "Вы не являетесь учителем. \nПожалуйста, свяжитесь с администратором.",
        reply_markup=cancel_keyboard,
    )


"""НАЗНАЧИТЬ УРОК"""


class CourseCreationStates(StatesGroup):
    EnterGroup = State()
    EnterDate = State()
    EnterTask = State()
    EnterTaskFile = State()
    Confirm = State()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_teacher_ids()
    and message.text == "Назначить урок📝",
)
async def create_lesson(message: types.Message):
    teacher = await get_teacher(message)

    if not teacher:
        await not_teacher(message=message)
        return

    session = SessionLocal()
    teacher_groups = session.query(Group).filter(Group.teacher_id == teacher.id).all()
    group_keyboard = await Group.send_groups_inline_keyboard(teacher_groups)
    session.close()

    await message.reply(
        "Давайте назначим урок!",
        reply_markup=cancel_keyboard,
    )
    await bot.send_message(
        message.from_user.id,
        "Выберите группу:",
        reply_markup=group_keyboard,
    )

    await CourseCreationStates.EnterGroup.set()


@dp.callback_query_handler(
    lambda message: str(message.from_user.id) in get_teacher_ids(),
    state=CourseCreationStates.EnterGroup,
)
async def create_lesson_group(callback_query: types.CallbackQuery, state: FSMContext):
    group_id = callback_query.data
    session = SessionLocal()
    group = Group.get_group_by_id(session, group_id)
    session.close()

    if not group:
        await callback_query.answer("Группу не найдена. Попробуйте ещё раз.")
        return

    async with state.proxy() as data:
        data["group"] = group

    await callback_query.message.answer(
        f"Группа: _{group.name}_",
        parse_mode=types.ParseMode.MARKDOWN,
        reply_markup=cancel_keyboard,
    )

    await bot.send_message(
        callback_query.from_user.id,
        "Теперь нужно выбрать дату и время:",
        reply_markup=await DialogCalendar().start_calendar(),
    )
    await CourseCreationStates.EnterDate.set()


@dp.callback_query_handler(
    dialog_cal_callback.filter(), state=CourseCreationStates.EnterDate
)
async def create_lesson_date(
    callback_query: types.CallbackQuery, callback_data: dict, state: FSMContext
):
    selected, date = await DialogCalendar().process_selection(
        callback_query, callback_data
    )
    if selected:

        if date < datetime.now():
            await callback_query.message.answer(
                "Нельзя выбрать прошедшую дату. Попробуйте ещё раз.",
                reply_markup=await DialogCalendar().start_calendar(),
            )
            return

        session = SessionLocal()

        async with state.proxy() as data:
            teacher_id = data["group"].teacher_id

        blocking_lessons = Lesson.get_lessons_in_time_range(
            session, date, teacher_id=teacher_id
        )
        session.close()

        if blocking_lessons:
            await callback_query.message.answer(
                f"У вас есть блокирующий урок в {blocking_lessons[0].datetime.strftime('%d/%m/%Y %H:%M')}. Попробуйте ещё раз.",
                reply_markup=await DialogCalendar().start_calendar(),
            )
            return

        await callback_query.message.answer(
            f"Выбрано: {date.strftime('%d/%m/%Y %H:%M')}\nТеперь запланируйте домашнее задание:",
            reply_markup=cancel_continue_keyboard,
        )

        async with state.proxy() as data:
            data["date"] = date

        await CourseCreationStates.EnterTask.set()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_teacher_ids(),
    state=CourseCreationStates.EnterTask,
)
async def create_lesson_task(message: types.Message, state: FSMContext):
    if message.text.lower() != "пропустить":

        async with state.proxy() as data:
            data["task"] = message.text

        await message.reply(
            f"Задание принято, теперь прикрепите файл к заданию (фото или документ).",
            reply_markup=cancel_continue_keyboard,
        )

        await CourseCreationStates.EnterTaskFile.set()
    else:
        async with state.proxy() as data:
            await message.reply(
                f"Вы запланировали урок в `{data.get('date').strftime('%d/%m/%Y %H:%M')}` у `{data.get('group').name}`.",
                reply_markup=confirm_keyboard,
                parse_mode=types.ParseMode.MARKDOWN,
            )
        await CourseCreationStates.Confirm.set()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_teacher_ids(),
    content_types=types.ContentType.PHOTO,
    state=CourseCreationStates.EnterTaskFile,
)
@dp.message_handler(
    lambda message: str(message.from_user.id) in get_teacher_ids(),
    content_types=types.ContentType.DOCUMENT,
    state=CourseCreationStates.EnterTaskFile,
)
@dp.message_handler(
    lambda message: str(message.from_user.id) in get_teacher_ids(),
    state=CourseCreationStates.EnterTaskFile,
)
async def create_lesson_task_file(message: types.Message, state: FSMContext):
    if message.text and message.text.lower() == "пропустить":
        pass
    elif message.content_type == "photo":
        async with state.proxy() as data:
            data["task_file"] = message.photo[-1].file_id
        await state.update_data(task_file=message.photo[-1].file_id)
    elif message.content_type == "document":
        async with state.proxy() as data:
            data["task_file"] = message.document.file_id
        await state.update_data(task_file=message.document.file_id)

    async with state.proxy() as data:
        task = data.get("task")
        date = data.get("date")
        group = data.get("group")

    if date and group:
        await message.reply(
            (
                f"Хотите запланировать урок в _{date.strftime('%d/%m/%Y %H:%M')}_ у _{group.name}_?"
                + (f"\nЗадание:\n_{task}_" if task else "")
            ),
            reply_markup=confirm_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )
        await CourseCreationStates.Confirm.set()
    else:
        await message.reply("Пожалуйста, сначала укажите дату и группу.")


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_teacher_ids(),
    state=CourseCreationStates.Confirm,
)
async def create_lesson_confirm(message: types.Message, state: FSMContext):
    if message.text == "Подтвердить":
        session = SessionLocal()
        async with state.proxy() as data:
            user = Lesson.create_lesson(
                session,
                group_id=data.get("group").id,
                datetime=data.get("date"),
                task=data.get("task"),
                task_file=data.get("task_file"),
            )
            await message.reply(
                f"Урок назначен!",
                parse_mode=types.ParseMode.MARKDOWN,
                reply_markup=main_keyboard,
            )
        session.close()
        await state.finish()
    else:
        await message.reply(
            f"Я вас не понимаю. Воспользуйтесь клавиатурой.",
        )


"""РАСПИСАНИЕ"""


class FindLessonStates(StatesGroup):
    EnterDate = State()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_teacher_ids()
    and message.text == "Расписание📅",
)
async def find_lesson(message: types.Message):
    teacher = await get_teacher(message)

    if not teacher:
        await not_teacher(message=message)
        return

    session = SessionLocal()

    session.close()

    await message.reply(
        "Давайте найдем ваши уроки!",
        reply_markup=cancel_keyboard,
    )
    await bot.send_message(
        message.from_user.id,
        "Выберите дату:",
        reply_markup=await DateDialogCalendar().start_calendar(),
    )

    await FindLessonStates.EnterDate.set()


@dp.callback_query_handler(
    dialog_cal_callback.filter(), state=FindLessonStates.EnterDate
)
async def find_lesson_callback(
    callback_query: types.CallbackQuery, callback_data: dict, state: FSMContext
):
    selected, date = await DateDialogCalendar().process_selection(
        callback_query, callback_data
    )
    if selected:

        session = SessionLocal()

        teacher_id = User.get_user_by_telegram_id(
            session, callback_query.from_user.id
        ).id

        lessons = Lesson.get_lessons_by_teacher_and_date(
            session=session, teacher_id=teacher_id, date=date
        )

        session.close()
        answer_message = await Lesson.send_result_message(
            lessons, with_header=False, fields=["group_id", "datetime"]
        )
        await callback_query.message.answer(
            f"Ваши уроки на: *{date.strftime('%d/%m/%Y')}*\n" + answer_message,
            reply_markup=main_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )

        async with state.proxy() as data:
            data["date"] = date

        await state.finish()


"""ОТМЕНИТЬ УРОК"""


class RemoveLessonStates(StatesGroup):
    EnterDate = State()
    EnterLesson = State()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_teacher_ids()
    and message.text == "Отменить урок🗑️",
)
async def remove_lesson(message: types.Message):
    teacher = await get_teacher(message)

    if not teacher:
        await not_teacher(message=message)
        return

    await message.reply(
        "Давайте отменим ваши уроки!",
        reply_markup=cancel_keyboard,
    )
    await bot.send_message(
        message.from_user.id,
        "Выберите дату:",
        reply_markup=await DateDialogCalendar().start_calendar(),
    )

    await RemoveLessonStates.EnterDate.set()


@dp.callback_query_handler(
    dialog_cal_callback.filter(), state=RemoveLessonStates.EnterDate
)
async def remove_lesson_callback(
    callback_query: types.CallbackQuery, callback_data: dict, state: FSMContext
):
    selected, date = await DateDialogCalendar().process_selection(
        callback_query, callback_data
    )
    if selected:

        session = SessionLocal()

        teacher_id = User.get_user_by_telegram_id(
            session, callback_query.from_user.id
        ).id

        lessons = Lesson.get_lessons_by_teacher_and_date(
            session=session, teacher_id=teacher_id, date=date
        )

        async with state.proxy() as data:
            data["lessons"] = lessons

        session.close()

        if not lessons:
            await callback_query.message.answer(
                "У вас нет уроков на эту дату.",
                reply_markup=main_keyboard,
            )
            await state.finish()
            return

        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text=f"*{date.strftime('%d/%m/%Y')}*",
            parse_mode=types.ParseMode.MARKDOWN,
        )

        lessons_keyboard = await Lesson.send_lessons_inline_keyboard(lessons)
        await callback_query.message.answer(
            f"Какие уроки вы хотите отменить?",
            reply_markup=lessons_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )

        await RemoveLessonStates.EnterLesson.set()


@dp.callback_query_handler(
    lambda message: str(message.from_user.id) in get_teacher_ids(),
    state=RemoveLessonStates.EnterLesson,
)
async def remove_lesson_lesson(callback_query: types.CallbackQuery, state: FSMContext):
    lesson_id = callback_query.data
    session = SessionLocal()
    lesson = Lesson.delete_lesson_by_id(session, lesson_id)

    await callback_query.answer(lesson.id)

    async with state.proxy() as data:
        lessons = data["lessons"]
        lessons = list(
            filter(lambda anothwer_lesson: anothwer_lesson.id != lesson.id, lessons)
        )
        data["lessons"] = lessons
        lessons_keyboard = await Lesson.send_lessons_inline_keyboard(
            data.get("lessons")
        )

    session.close()

    if not lesson:
        await callback_query.answer("Урок не отменен...")
        return

    if lessons:
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=lessons_keyboard,
            text="Хотите отменить еще один урок?",
        )
    else:
        await bot.delete_message(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
        )
        await bot.send_message(
            callback_query.from_user.id,
            "Все уроки отменены!",
            reply_markup=main_keyboard,
        )

        await state.finish()
