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


from config import (
    dp,
    get_admin_ids,
    SessionLocal,
    bot,
    Base,
    engine,
    update_ids
)
from keyboards import (
    back_or_cancel_keyboard,
    cancel_keyboard,
    cancel_back_confirm_keyboard,
    confirm_keyboard,
)
from keyboards import admin_keyboard as main_keyboard
from database.models import *


"""СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ"""


class UserCreationStates(StatesGroup):
    EnterName = State()
    EnterSurname = State()
    EnterPhone = State()
    ChooseRole = State()
    Confirm = State()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids()
    and message.text == "Новый пользователь✅"
)
async def new_user(message: types.Message):
    await message.reply(
        "Давайте начнем процесс создания нового пользователя. \nВведите имя:",
        reply_markup=cancel_keyboard,
    )
    await UserCreationStates.EnterName.set()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=UserCreationStates.EnterName,
)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["name"] = message.text

    await message.reply("Введите фамилию:", reply_markup=back_or_cancel_keyboard)
    await UserCreationStates.EnterSurname.set()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=UserCreationStates.EnterSurname,
)
async def process_surname(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["surname"] = message.text

    await message.reply("Введите номер телефона:", reply_markup=back_or_cancel_keyboard)
    await UserCreationStates.EnterPhone.set()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=UserCreationStates.EnterPhone,
)
async def process_phone(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["phone"] = message.text

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("Администратор", callback_data="role_admin"),
        InlineKeyboardButton("Учитель", callback_data="role_teacher"),
        InlineKeyboardButton("Ученик", callback_data="role_student"),
    )

    await message.reply("Выберите роль:", reply_markup=keyboard)
    await UserCreationStates.ChooseRole.set()


@dp.callback_query_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=UserCreationStates.ChooseRole,
)
async def process_role(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data:
        role = callback_query.data.split("_")[1]
        async with state.proxy() as data:
            data["role"] = role

        roles_dict = {
            "admin": "администратор",
            "teacher": "учитель",
            "student": "ученик",
        }
        await callback_query.message.reply(
            f"Спасибо! Вы ввели следующие данные: \n*Имя* - _{data['name']}_\n*Фамилия* - _{data['surname']}_\n*Номер телефона* - _{data['phone']}_\n*Роль* - _{roles_dict.get(data['role'], "роль не выбрана")}_\n\nПодтвердите данные.",
            parse_mode=types.ParseMode.MARKDOWN,
            reply_markup=cancel_back_confirm_keyboard,
        )
        user_data = await state.get_data()
        await UserCreationStates.Confirm.set()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=UserCreationStates.Confirm,
)
async def process_confirm(message: types.Message, state: FSMContext):
    if message.text == "Подтвердить":
        session = SessionLocal()
        async with state.proxy() as data:
            user = User.create_user(
                session,
                name=data["name"],
                surname=data["surname"],
                phone=data["phone"],
                is_admin=data["role"] == "admin",
                is_teacher=data["role"] == "teacher",
            )
            await message.reply(
                f"Пользователь _{user.name} {user.surname}_ создан. \nAPI-ключ: `{user.api_key}`",
                parse_mode=types.ParseMode.MARKDOWN,
                reply_markup=main_keyboard,
            )
        session.close()
        await state.finish()
    else:
        await message.reply(
            f'Я вас не понимаю. Нажмите кнопку "Подтвердить", чтобы подтвердить данные, "Назад", чтобы вернуться назад или "Отмена❌", чтобы отменить операцию.',
        )


"""НАЙТИ ПОЛЬЗОВАТЕЛЯ"""


class UserSearchStates(StatesGroup):
    SearchParam = State()
    SearchData = State()
    SearchResult = State()
    SearchActivity = State()


search_attrs = {
    "Имя": "name",
    "Фамилия": "surname",
    "Номер телефона": "phone",
    "Роль": "role",
    "Ключ": "api_key",
}

param_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
param_keyboard.add(
    *[KeyboardButton(name) for name in list(search_attrs.keys()) + ["Отмена❌"]]
)


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids()
    and message.text == "Найти пользователя🔎"
)
async def new_user(message: types.Message):
    await message.reply("Укажите параметр поиска:", reply_markup=param_keyboard)
    await UserSearchStates.SearchParam.set()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=UserSearchStates.SearchParam,
)
async def process_search_param(message: types.Message, state: FSMContext):
    if message.text in search_attrs.keys():
        param_readable = message.text

        async with state.proxy() as data:
            data["search_key"] = search_attrs.get(param_readable)

        if "Роль" in param_readable:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("Администратор", callback_data="admin"),
                InlineKeyboardButton("Учитель", callback_data="teacher"),
                InlineKeyboardButton("Ученик", callback_data="student"),
            )
            await message.reply(
                f"Выберите одну из ролей ниже.",
                reply_markup=back_or_cancel_keyboard,
            )
            await message.reply(
                f"Доступные роли:",
                reply_markup=keyboard,
                parse_mode=types.ParseMode.MARKDOWN,
            )
        else:
            await message.reply(
                f"Введите значение _{param_readable}_:",
                reply_markup=back_or_cancel_keyboard,
                parse_mode=types.ParseMode.MARKDOWN,
            )
        await UserSearchStates.SearchData.set()
    else:
        await message.reply(
            "Я вас не понимаю. Доступные параметры поиска показаны на клавиатуре.",
            reply_markup=param_keyboard,
        )
        await UserSearchStates.SearchParam.set()
        return


@dp.callback_query_handler(
    lambda callback_query: str(callback_query.from_user.id) in get_admin_ids(),
    state=UserSearchStates.SearchData,
)
@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=UserSearchStates.SearchData,
)
async def process_search_data(message, state: FSMContext):
    async with state.proxy() as data:
        search_key = data["search_key"]
        result = data.get("result", None)

    session = SessionLocal()

    if message_data := getattr(message, "data", None):
        message = message.message
        if message_data in ("admin", "teacher", "student") and search_key == "role":
            role = message_data
            if not result:
                result = User.get_users_by_role(role=role, session=session)
        elif message_data == "cancel":
            await state.finish()
            await message.reply("Отменено", reply_markup=main_keyboard)
            return
        elif message_data == "left":
            async with state.proxy() as data:
                result_position = data.get("result_position", 0)
                result_position -= 10
                data["result_position"] = max(0, result_position)
        elif message_data == "right":
            async with state.proxy() as data:
                result_position = data.get("result_position", 0)
                if len(result) > result_position + 10:
                    result_position += 10
                data["result_position"] = result_position
    else:
        search_data = message.text
        if not result:
            result = User.get_users_by_field(
                field=search_key, value=search_data, session=session
            )

    session.close()

    async with state.proxy() as data:
        data["result"] = result
        result_position = data.get("result_position", 0)

    keyboard = None

    if len(result) > 10:
        show_result = result[result_position : result_position + 10]
        message_text = await User.send_result_message(show_result)
        keyboard = InlineKeyboardMarkup()
        buttons = []

        if result_position > 0:
            buttons.append(InlineKeyboardButton("◀", callback_data="left"))

        if len(result) - len(show_result) > result_position:
            buttons.append(InlineKeyboardButton("▶", callback_data="right"))

        buttons.append(InlineKeyboardButton("❌", callback_data="cancel"))
        keyboard.add(*buttons)
    else:
        message_text = await User.send_result_message(result)
        keyboard = back_or_cancel_keyboard

    if "id" in message.text:
        if message_text != message.text:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.message_id,
                text=message_text,
                parse_mode=types.ParseMode.MARKDOWN,
                reply_markup=keyboard or ReplyKeyboardRemove(),
            )
    else:
        await bot.send_message(
            chat_id=message.chat.id,
            text=message_text,
            parse_mode=types.ParseMode.MARKDOWN,
            reply_markup=keyboard or ReplyKeyboardRemove(),
        )


"""УДАЛИТЬ ПОЛЬЗОВАТЕЛЯ"""


class UserDeleteStates(StatesGroup):
    DeleteParam = State()
    DeleteConfirm = State()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids()
    and message.text == "Удалить пользователя🗑️"
)
async def delete_user(message: types.Message):
    await message.reply(
        "Укажите id пользователей через пробел", reply_markup=cancel_keyboard
    )
    await UserDeleteStates.DeleteParam.set()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=UserDeleteStates.DeleteParam,
)
async def delete_param(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["user_ids"] = message.text

    session = SessionLocal()
    result = User.get_users_by_ids(user_ids=message.text, session=session)
    session.close()
    if result:
        answer_text = await User.send_result_message(
            result=result, fields=["id", "name", "surname", "role"], with_header=False
        )
        await bot.send_message(
            chat_id=message.chat.id,
            text="Будут удалены пользователи:\n\n"
            + answer_text
            + "\nПодтвердите удаление",
            reply_markup=confirm_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )

        await UserDeleteStates.DeleteConfirm.set()
    else:
        await message.reply("Пользователь не найден", reply_markup=main_keyboard)
        await state.finish()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=UserDeleteStates.DeleteConfirm,
)
async def confirm_delete_user(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        user_ids = data.get("user_ids", "")

    if message.text == "Подтвердить":
        session = SessionLocal()
        result = User.delete_users_by_ids(session=session, user_ids=user_ids)
        session.close()
        
        if not result:
            await message.reply("Пользователи не удалены", reply_markup=main_keyboard)
            await state.finish()
            return
        user_ids = [str(user.id) for user in result]
        for user_id in user_ids: 
            update_ids(user_id)

        await message.reply("Пользователи удалены", reply_markup=main_keyboard)
        await state.finish()
    else:
        await message.reply(
            "Выберите команду на клавиатуре.", reply_markup=confirm_keyboard
        )


"""СОЗДАТЬ КУРС"""


class CourseCreationStates(StatesGroup):
    EnterTitle = State()
    EnterDescription = State()
    EnterIcon = State()
    Confirm = State()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids()
    and message.text == "Новый курс✅"
)
async def create_course(message: types.Message):
    await message.reply(
        "Давайте начнем процесс создания учебного курса. \nВведите название:",
        reply_markup=cancel_keyboard,
    )
    await CourseCreationStates.EnterTitle.set()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=CourseCreationStates.EnterTitle,
)
async def group_title(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["title"] = message.text

    await message.reply(
        "Спасибо. \nТеперь описание курса:",
        reply_markup=back_or_cancel_keyboard,
    )
    await CourseCreationStates.EnterDescription.set()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=CourseCreationStates.EnterDescription,
)
async def group_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["description"] = message.text

    await message.reply(
        "Отлично! \nТеперь пришлите картинку, которая будет использована в качестве иконки курса:",
        reply_markup=back_or_cancel_keyboard,
    )
    await CourseCreationStates.EnterIcon.set()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=CourseCreationStates.EnterIcon,
)
@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    content_types=[types.ContentType.PHOTO],
    state=CourseCreationStates.EnterIcon,
)
async def group_photo(message: types.Message, state: FSMContext):
    if message.photo:
        async with state.proxy() as data:
            data["icon"] = message.photo[-1].file_id
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=data["icon"],
            caption=f"Спасибо! Вы ввели следующие данные: \n*Название* - _{data['title']}_\n*Описание:*\n_{data['description']}_\n*Иконка:*",
            parse_mode=types.ParseMode.MARKDOWN,
            reply_markup=cancel_back_confirm_keyboard,
        )
        await CourseCreationStates.Confirm.set()
    else:
        await message.reply(
            "Мне кажется, вы не прислали фото.",
            reply_markup=back_or_cancel_keyboard,
        )


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=CourseCreationStates.Confirm,
)
async def group_confirm(message: types.Message, state: FSMContext):
    if message.text == "Подтвердить":
        course = None
        async with state.proxy() as data:
            session = SessionLocal()
            course = Course.create_course(
                title=data["title"],
                description=data["description"],
                icon=data["icon"],
                session=session,
            )
            session.close()
        await message.reply(
            "Курс создан" if course else "Что-то пошло не так",
            reply_markup=main_keyboard,
        )
        await state.finish()
    else:
        await message.reply(
            "Выберите команду на клавиатуре.", reply_markup=cancel_back_confirm_keyboard
        )


"""УДАЛИТЬ КУРС"""


class CourseDeleteStates(StatesGroup):
    EnterSearchParam = State()
    Confirm = State()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids()
    and message.text == "Удалить курс🗑️"
)
async def delete_course(message: types.Message):
    session = SessionLocal()
    result = Course.get_courses(session)
    session.close()
    result_text = await Course.send_result_message(result)
    if result:
        result_text = "Какой курс вы хотите удалить? (id или название)\n" + result_text
    await message.reply(
        result_text,
        reply_markup=cancel_keyboard,
        parse_mode=types.ParseMode.MARKDOWN,
    )
    await CourseDeleteStates.EnterSearchParam.set()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=CourseDeleteStates.EnterSearchParam,
)
async def course_delete_search(message: types.Message, state: FSMContext):
    field = "id" if message.text.isdigit() else "title"
    session = SessionLocal()
    result = Course.get_courses_by_field(
        session=session, field=field, value=message.text
    )
    session.close()

    if result:
        course = result[-1]
        
        await message.reply(
            f"Будет удален курс: _{course.title}_. Подтвердите удаление.",
            reply_markup=cancel_back_confirm_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )

        async with state.proxy() as data:
            data["course"] = course

        await CourseDeleteStates.Confirm.set()
    else:
        await message.reply(
            "Курс не найден. Попробуйте ещё раз.",
            reply_markup=back_or_cancel_keyboard,
        )


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=CourseDeleteStates.Confirm,
)
async def delete_course_confirm(message: types.Message, state: FSMContext):
    if message.text == "Подтвердить":
        async with state.proxy() as data:
            course = data["course"]

        session = SessionLocal()
        course = Course.delete_course_by_id(session=session, course_id=course.id)
        session.close()

        if course and type(course) == list and course[-1].__class__ == Group:
            message_text = await Group.send_result_message(
                course, fields=["id", "name"]
            )
            await message.reply(
                "Курс не может быть удален, поскольку назначен группам. \n"
                + message_text,
                reply_markup=main_keyboard,
                parse_mode=types.ParseMode.MARKDOWN,
            )

            await state.finish()
            return

        if not course:
            await message.reply(
                "Курс не удален. Попробуйте ещё раз.",
                reply_markup=back_or_cancel_keyboard,
            )
            return

        await message.reply(
            f"Удален курс _{course.title}_.",
            reply_markup=main_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )

        await state.finish()
    else:
        await message.reply(
            "Воспользуйтесь клавиатурой.", reply_markup=cancel_back_confirm_keyboard
        )


"""ВСЕ КУРСЫ"""


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids()
    and message.text == "Все курсы🔎"
)
async def show_courses(message: types.Message):
    session = SessionLocal()
    result = Course.get_courses(session)
    session.close()
    result = await Course.send_result_message(result, with_header=False)
    await message.reply(
        text=result,
        reply_markup=main_keyboard,
        parse_mode=types.ParseMode.MARKDOWN,
    )


"""СОЗДАТЬ ГРУППУ"""


class GroupCreationStates(StatesGroup):
    EnterCourse = State()
    EnterTeacher = State()
    Confirm = State()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids()
    and message.text == "Новая группа✅"
)
async def create_group(message: types.Message):
    await message.reply(
        "Давайте начнем процесс создания учебной группы. \nУкажите курс (название или id):",
        reply_markup=cancel_keyboard,
    )
    session = SessionLocal()
    result = Course.get_courses(session)
    session.close()
    result = await Course.send_result_message(result)
    await message.reply(
        text="Доступные курсы: \n" + result,
        reply_markup=back_or_cancel_keyboard,
        parse_mode=types.ParseMode.MARKDOWN,
    )
    await GroupCreationStates.EnterCourse.set()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=GroupCreationStates.EnterCourse,
)
async def create_group_course(message: types.Message, state: FSMContext):
    field = "id" if message.text.isdigit() else "title"
    session = SessionLocal()
    result = Course.get_courses_by_field(
        session=session, field=field, value=message.text
    )
    session.close()

    if result:
        group = result[-1]
        await message.reply(
            f"Будет создана группа: _{group.title}_\nВыберите преподавателя: (id или фамилия)",
            reply_markup=cancel_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )

        session = SessionLocal()
        teachers = User.get_teachers(session)
        session.close()

        teachers = await User.send_result_message(
            teachers, fields=["id", "name", "surname"]
        )
        await message.reply(
            text="Доступные препователи: \n" + teachers,
            reply_markup=back_or_cancel_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )

        async with state.proxy() as data:
            data["group"] = group

        await GroupCreationStates.EnterTeacher.set()
    else:
        await message.reply(
            "Курс не найден. Попробуйте ещё раз.",
            reply_markup=back_or_cancel_keyboard,
        )


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=GroupCreationStates.EnterTeacher,
)
async def create_group_teacher(message: types.Message, state: FSMContext):
    field = "id" if message.text.isdigit() else "surname"
    session = SessionLocal()
    result = User.get_users_by_field(session=session, field=field, value=message.text)
    session.close()

    if result:
        teacher = result[-1]

        if not teacher.is_teacher:
            await message.reply(
                "Пользователь не является преподавателем. Попробуйте ещё раз.",
                reply_markup=back_or_cancel_keyboard,
            )
            return

        async with state.proxy() as data:
            group = data["group"]

        await message.reply(
            f"Будет создана группа: _{group.title}_\nПреподаватель: _{teacher.name} {teacher.surname}_\nПодтвердите создание группы.",
            reply_markup=cancel_back_confirm_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )

        async with state.proxy() as data:
            data["teacher"] = teacher

        await GroupCreationStates.Confirm.set()
    else:
        await message.reply(
            "Пользователь не найден. Попробуйте ещё раз.",
            reply_markup=back_or_cancel_keyboard,
        )


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=GroupCreationStates.Confirm,
)
async def create_group_confirm(message: types.Message, state: FSMContext):
    if message.text == "Подтвердить":
        async with state.proxy() as data:
            group = data["group"]
            teacher = data["teacher"]

        session = SessionLocal()
        group = Group.create_group(session, group.id, teacher.id)
        session.close()

        if not group:
            await message.reply(
                "Группа не создана. Попробуйте ещё раз.",
                reply_markup=back_or_cancel_keyboard,
            )
            return

        await message.reply(
            f"Группа создана: {group.name}. Преподаватель: {teacher.name} {teacher.surname}",
            reply_markup=main_keyboard,
        )

        await state.finish()
    else:
        await message.reply(
            "Воспользуйтесь клавиатурой.", reply_markup=cancel_back_confirm_keyboard
        )


"""НАЙТИ ГРУППУ"""


class GroupSearchStates(StatesGroup):
    EnterName = State()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids()
    and message.text == "Найти группу🔎"
)
async def search_group(message: types.Message):
    session = SessionLocal()
    result = Course.get_courses(session)
    session.close()

    if not result:
        await message.reply(
            "Групп нет.",
            reply_markup=main_keyboard,
        )
        return

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        *[
            InlineKeyboardButton(course.title, callback_data=course.id)
            for course in result
        ],
        InlineKeyboardButton("❌", callback_data="cancel"),
    )

    await message.reply(
        "Выберите курс:",
        reply_markup=keyboard,
    )

    await GroupSearchStates.EnterName.set()


@dp.callback_query_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=GroupSearchStates.EnterName,
)
async def create_group_course(callback_query: types.CallbackQuery, state: FSMContext):
    session = SessionLocal()

    value = callback_query.data

    if value == "cancel":
        await state.finish()
        await bot.send_message(
            callback_query.message.chat.id, "Отменено", reply_markup=main_keyboard
        )
        return

    course = Course.get_course_by_id(session=session, course_id=int(value))
    groups = Group.get_group_by_field(session, "course_id", course.id)

    session.close()

    if groups:
        full_rows = []

        for group in groups:
            teacher = User.get_user_by_id(session, group.teacher_id)
            students = GroupUserLnk.get_students_of_group(session, group.id)
            student_message = await User.send_result_message(
                students,
                with_header=False,
                fields=["id", "name", "surname", "phone", "key"],
            )
            full_rows.append(
                f"*{group.name}*\n*Преподаватель:* _{teacher.name}_ {teacher.surname}"
                + "\n*Ученики группы:*\n"
                + student_message
                + "\n"
            )

        await bot.send_message(
            callback_query.message.chat.id,
            "\n".join(full_rows),
            reply_markup=main_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )
        await state.finish()

    else:
        await bot.send_message(
            callback_query.message.chat.id,  # Отправляем сообщение в чат, где была нажата кнопка
            "Ничего не найдено. Попробуйте ещё раз.",
            reply_markup=cancel_keyboard,
        )


"""УДАЛИТЬ ГРУППУ"""


class GroupDeleteStates(StatesGroup):
    EnterName = State()
    Confirm = State()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids()
    and message.text == "Удалить группу🗑️"
)
async def delete_group(message: types.Message):
    session = SessionLocal()
    groups = Group.get_groups(session)
    session.close()

    message_text = await Group.send_result_message(groups, with_header=False)

    await message.reply(
        "Укажите группу: (id или название).\nДоступные группы: \n" + message_text,
        reply_markup=cancel_keyboard,
        parse_mode=types.ParseMode.MARKDOWN,
    )
    await GroupDeleteStates.EnterName.set()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=GroupDeleteStates.EnterName,
)
async def delete_group_name(message: types.Message, state: FSMContext):
    field = "id" if message.text.isdigit() else "name"
    session = SessionLocal()
    result = Group.get_group_by_field(session=session, field=field, value=message.text)
    session.close()

    if result:
        group = result[-1]

        await message.reply(
            f"Будет удалена группа: _{group.name}_.\nПодтвердите действие.",
            reply_markup=cancel_back_confirm_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )

        async with state.proxy() as data:
            data["group"] = group

        await GroupDeleteStates.Confirm.set()
    else:
        await message.reply(
            "Группа не найдена. Попробуйте ещё раз.",
            reply_markup=cancel_keyboard,
        )


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=GroupDeleteStates.Confirm,
)
async def delete_group_confirm(message: types.Message, state: FSMContext):
    if message.text == "Подтвердить":
        async with state.proxy() as data:
            group = data["group"]

        session = SessionLocal()
        is_deleted = Group.delete_group_by_id(session, group.id)
        session.close()

        if is_deleted:
            await message.reply(
                f"Группа удалена: _{group.name}_",
                reply_markup=main_keyboard,
                parse_mode=types.ParseMode.MARKDOWN,
            )
        else:
            await message.reply(
                "Ничего не удалено. Попробуйте ещё раз.",
                reply_markup=main_keyboard,
            )

        await state.finish()
    else:
        await message.reply(
            "Воспользуйтесь клавиатурой.", reply_markup=cancel_back_confirm_keyboard
        )


"""ДОБАВИТЬ УЧЕНИКА В ГРУППУ"""


class SendStudentToGropupStates(StatesGroup):
    EnterGroup = State()
    EnterStudents = State()
    Confirm = State()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids()
    and message.text == "Добавить учеников в группу➕"
)
async def send_student_to_group(message: types.Message):
    session = SessionLocal()
    groups = Group.get_groups(session)
    session.close()

    message_text = await Group.send_result_message(
        groups, with_header=False, fields=["id", "name", "teacher"]
    )

    await message.reply(
        "Укажите группу: (id или название).\nДоступные группы: \n" + message_text,
        reply_markup=cancel_keyboard,
        parse_mode=types.ParseMode.MARKDOWN,
    )
    await SendStudentToGropupStates.EnterGroup.set()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=SendStudentToGropupStates.EnterGroup,
)
async def send_student_to_group_name(message: types.Message, state: FSMContext):
    field = "id" if message.text.isdigit() else "name"
    session = SessionLocal()
    result = Group.get_group_by_field(session=session, field=field, value=message.text)
    session.close()

    if result:
        group = result[-1]

        await message.reply(
            f"Будут добавлены ученики в группу: _{group.name}_.\nВведите id учеников через пробел.",
            reply_markup=back_or_cancel_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )

        async with state.proxy() as data:
            data["group"] = group

        await SendStudentToGropupStates.EnterStudents.set()
    else:
        await message.reply(
            "Группа не найдена. Попробуйте ещё раз.",
            reply_markup=cancel_keyboard,
        )


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=SendStudentToGropupStates.EnterStudents,
)
async def send_student_to_group_students(message: types.Message, state: FSMContext):
    session = SessionLocal()
    users = User.get_students_by_ids(session=session, ids=message.text)
    session.close()

    if users:
        async with state.proxy() as data:
            data["users"] = users

        message_text = await User.send_result_message(
            users, fields=["id", "name", "surname"], with_header=False
        )

        await message.reply(
            f"Будут добавлены следующие ученики:\n{message_text}"
            + "\nПодтвердите действие.",
            reply_markup=cancel_back_confirm_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )

        await SendStudentToGropupStates.Confirm.set()
    else:
        await message.reply(
            "Ничего не найдено. Попробуйте ещё раз.",
            reply_markup=cancel_keyboard,
        )


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=SendStudentToGropupStates.Confirm,
)
async def send_student_to_group_confirm(message: types.Message, state: FSMContext):
    if message.text == "Подтвердить":
        async with state.proxy() as data:
            group = data["group"]
            users = data["users"]

        session = SessionLocal()
        linked_users = GroupUserLnk.create_links_for_users(
            session=session, user_ids=users, group_id=group.id
        )
        session.close()

        if linked_users:
            await message.reply(
                f"Ученики были добавлены в группу: _{group.name}_.",
                reply_markup=main_keyboard,
                parse_mode=types.ParseMode.MARKDOWN,
            )
        else:
            await message.reply(
                "Ничего не добавлено. Попробуйте ещё раз.",
                reply_markup=main_keyboard,
            )

        await state.finish()
    else:
        await message.reply(
            "Воспользуйтесь клавиатурой.", reply_markup=cancel_back_confirm_keyboard
        )


"""УБРАТЬ УЧЕНИКОВ ИЗ ГРУППЫ"""


class RemoveStudentFromGropupStates(StatesGroup):
    EnterGroup = State()
    EnterStudents = State()
    Confirm = State()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids()
    and message.text == "Убрать учеников из группы➖"
)
async def remove_student_from_group(message: types.Message):
    session = SessionLocal()
    groups = Group.get_groups(session)
    session.close()

    message_text = await Group.send_result_message(
        groups, with_header=False, fields=["id", "name", "teacher"]
    )

    await message.reply(
        "Укажите группу: (id или название).\nДоступные группы: \n" + message_text,
        reply_markup=cancel_keyboard,
        parse_mode=types.ParseMode.MARKDOWN,
    )
    await RemoveStudentFromGropupStates.EnterGroup.set()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=RemoveStudentFromGropupStates.EnterGroup,
)
async def remove_student_from_group_group(message: types.Message, state: FSMContext):
    field = "id" if message.text.isdigit() else "name"
    session = SessionLocal()
    result = Group.get_group_by_field(session=session, field=field, value=message.text)

    if result:
        group = result[-1]
        students = GroupUserLnk.get_students_of_group(
            session=session, group_id=group.id
        )

        message_text = await User.send_result_message(
            students, fields=["id", "name", "surname"], with_header=False
        )
        await message.reply(
            f"Ученики будут *убраны* из группы: _{group.name}_.\nВведите id учеников через пробел.\nДоступные ученики: \n"
            + message_text
            + "\n\n_Ученики покинут группу, но останутся в системе! Чтобы удалить ученика насовсем воспользуйтесь кнопкой Удалить пользователя_",
            reply_markup=back_or_cancel_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )

        async with state.proxy() as data:
            data["group"] = group

        await RemoveStudentFromGropupStates.EnterStudents.set()
    else:
        await message.reply(
            "Группа не найдена. Попробуйте ещё раз.",
            reply_markup=cancel_keyboard,
        )
    session.close()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=RemoveStudentFromGropupStates.EnterStudents,
)
async def remove_student_from_group_students(message: types.Message, state: FSMContext):
    session = SessionLocal()
    users = User.get_students_by_ids(session=session, ids=message.text)
    session.close()

    if users:
        async with state.proxy() as data:
            data["users"] = users

        message_text = await User.send_result_message(
            users, fields=["id", "name", "surname"], with_header=False
        )

        await message.reply(
            f"Из группы будут убраны следующие ученики:\n{message_text}"
            + "\nПодтвердите действие.",
            reply_markup=cancel_back_confirm_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )

        await RemoveStudentFromGropupStates.Confirm.set()
    else:
        await message.reply(
            "Ученики не найдены. Попробуйте ещё раз.",
            reply_markup=cancel_keyboard,
        )


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=RemoveStudentFromGropupStates.Confirm,
)
async def remove_student_from_group_confirm(message: types.Message, state: FSMContext):
    if message.text == "Подтвердить":
        async with state.proxy() as data:
            group = data["group"]
            users = data["users"]

        session = SessionLocal()
        deleted_users = GroupUserLnk.delete_by_users(session=session, users=users)
        session.close()

        if deleted_users:
            await message.reply(
                f"Ученики были удалены из группы: _{group.name}_.",
                reply_markup=main_keyboard,
                parse_mode=types.ParseMode.MARKDOWN,
            )
        else:
            await message.reply(
                "Ничего не добавлено. Попробуйте ещё раз.",
                reply_markup=main_keyboard,
            )

        await state.finish()
    else:
        await message.reply(
            "Воспользуйтесь клавиатурой.", reply_markup=cancel_back_confirm_keyboard
        )


"""ЗАМЕНИТЬ ПРЕПОДАВАТЕЛЯ"""


class UpdateTeacherStates(StatesGroup):
    EnterGroup = State()
    EnterTeacher = State()
    Confirm = State()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids()
    and message.text == "Заменить преподавателя👨🏻‍🏫"
)
async def update_teacher(message: types.Message):
    session = SessionLocal()
    groups = Group.get_groups(session)
    session.close()

    message_text = await Group.send_result_message(
        groups, with_header=False, fields=["id", "name", "teacher"]
    )

    await message.reply(
        "Укажите группу: (id или название).\nДоступные группы: \n" + message_text,
        reply_markup=cancel_keyboard,
        parse_mode=types.ParseMode.MARKDOWN,
    )
    await UpdateTeacherStates.EnterGroup.set()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=UpdateTeacherStates.EnterGroup,
)
async def update_teacher_group(message: types.Message, state: FSMContext):
    field = "id" if message.text.isdigit() else "name"
    session = SessionLocal()
    result = Group.get_group_by_field(session=session, field=field, value=message.text)
    session.close()

    if result:
        group = result[-1]

        session = SessionLocal()
        teachers = User.get_teachers(session=session)
        session.close()

        message_text = await User.send_result_message(
            teachers, with_header=False, fields=["id", "name", "surname"]
        )

        await message.reply(
            f"Будет заменен преподаватель в группе: _{group.name}_.\nУкажите нового преподавателя(id или фамилия).\nДоступные преподаватели: \n"
            + message_text,
            reply_markup=back_or_cancel_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )

        async with state.proxy() as data:
            data["group"] = group

        await UpdateTeacherStates.EnterTeacher.set()
    else:
        await message.reply(
            "Группа не найдена. Попробуйте ещё раз.",
            reply_markup=cancel_keyboard,
        )


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=UpdateTeacherStates.EnterTeacher,
)
async def update_teacher_teacher(message: types.Message, state: FSMContext):
    feild = "id" if message.text.isdigit() else "surname"

    session = SessionLocal()
    teacher = User.get_teacher_by_field(
        session=session, field=feild, value=message.text
    )

    if feild:
        async with state.proxy() as data:
            group = data["group"]
            data["teacher"] = teacher

        old_teacher = User.get_user_by_id(session=session, user_id=group.teacher_id)

        if old_teacher.id == teacher.id:
            session.close()
            await message.reply(
                "Преподаватель не менялся. Попробуйте ещё раз.",
                reply_markup=back_or_cancel_keyboard,
            )
            return

        await message.reply(
            f"В группе _{group.name}_ будет заменен преподаватель _{old_teacher.name} {old_teacher.surname}_ на _{teacher.name} {teacher.surname}_"
            + "\nПодтвердите действие.",
            reply_markup=cancel_back_confirm_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )

        await UpdateTeacherStates.Confirm.set()
    else:
        await message.reply(
            "Преподаватель не найден. Попробуйте ещё раз.",
            reply_markup=cancel_keyboard,
        )
    session.close()


@dp.message_handler(
    lambda message: str(message.from_user.id) in get_admin_ids(),
    state=UpdateTeacherStates.Confirm,
)
async def update_teacher_confirm(message: types.Message, state: FSMContext):
    if message.text == "Подтвердить":
        async with state.proxy() as data:
            group = data["group"]
            teacher = data["teacher"]

        session = SessionLocal()
        group.teacher = teacher
        session.close()

        await message.reply(
            f"Преподаватель заменен.",
            reply_markup=main_keyboard,
            parse_mode=types.ParseMode.MARKDOWN,
        )

        await state.finish()
    else:
        await message.reply(
            "Воспользуйтесь клавиатурой.", reply_markup=cancel_back_confirm_keyboard
        )
