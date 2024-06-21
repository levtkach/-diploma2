import random
import string
from datetime import datetime, timedelta
from sqlalchemy import (
    Column,
    Integer,
    String,
    BigInteger,
    Boolean,
    Text,
    ForeignKey,
    DateTime,
    and_,
)
from sqlalchemy.orm import relationship
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import Base, engine, SessionLocal


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    telegram_id = Column(String, index=True)
    api_key = Column(String, index=True)
    name = Column(String)
    surname = Column(String)
    phone = Column(String)
    is_admin = Column(Boolean, default=False)
    is_teacher = Column(Boolean, default=False)

    def __init__(self, name, surname, phone, is_admin, is_teacher):
        self.name = name
        self.surname = surname
        self.phone = phone
        self.is_admin = is_admin
        self.is_teacher = is_teacher

    @staticmethod
    def get_user_by_telegram_id(session, telegram_id):
        return session.query(User).filter(User.telegram_id == str(telegram_id)).first()

    @staticmethod
    def create_user(
        session,
        name,
        surname: str,
        phone: str = "отсутствует",
        is_admin: bool = False,
        is_teacher: bool = False,
    ):
        user = User(
            name=name,
            surname=surname,
            phone=phone,
            is_admin=is_admin,
            is_teacher=is_teacher,
        )
        user.api_key = User.generate_api_key(session)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    @staticmethod
    def get_user_by_api_key(session, api_key: str):
        return session.query(User).filter(User.api_key == str(api_key)).first()

    @staticmethod
    def generate_api_key(session):
        while True:
            key = "key:" + "".join(
                random.choices(string.ascii_letters + string.digits, k=16)
            )
            if not session.query(User).filter(User.api_key == key).first():
                return key

    def assign_api_key(self, session):
        self.api_key = self.generate_api_key(session)
        session.commit()

    @staticmethod
    def get_users_by_field(session, field: str, value: str):

        if not hasattr(User, field):
            return None

        return (
            session.query(User)
            .filter(getattr(User, field) == value)
            .order_by(User.id)
            .all()
        )

    @staticmethod
    def get_users_by_role(session, role: str):
        if role == "admin":
            return session.query(User).filter(User.is_admin == True).all()
        elif role == "teacher":
            return session.query(User).filter(User.is_teacher == True).all()
        elif role == "student":
            return (
                session.query(User)
                .filter(User.is_admin == False, User.is_teacher == False)
                .all()
            )
        else:
            return []

    @staticmethod
    def get_students_by_ids(session, ids: str):
        ids = [id for id in ids.split() if id.isdigit()]
        users = (
            session.query(User)
            .filter(User.id.in_(ids), User.is_admin == False, User.is_teacher == False)
            .all()
        )

        return users

    @staticmethod
    def delete_users_by_ids(session, user_ids: str):
        ids = [id for id in user_ids.split() if id.isdigit()]

        users_to_delete = session.query(User).filter(User.id.in_(ids)).all()
        if users_to_delete:
            for user in users_to_delete:
                session.delete(user)
            session.commit()
        return users_to_delete

    @staticmethod
    def get_users_by_ids(session, user_ids: str):
        ids = [id for id in user_ids.split() if id.isdigit()]
        users = session.query(User).filter(User.id.in_(ids)).all()

        return users

    @staticmethod
    def get_user_by_id(session, user_id: int):
        users = session.query(User).filter(User.id == user_id).first()

        return users

    @staticmethod
    def get_teachers(session):
        return session.query(User).filter(User.is_teacher == True).all()

    @staticmethod
    def get_teacher_by_field(session, field: str, value: str):

        if not hasattr(User, field):
            return None

        return (
            session.query(User)
            .filter(getattr(User, field) == value, User.is_teacher == True)
            .first()
        )

    async def send_result_message(
        result,
        fields=["id", "name", "surname", "phone", "key", "role"],
        with_header=True,
    ):
        if not result:
            return "Пользователи не найдены."

        field_names = {
            "id": "id",
            "name": "Имя",
            "surname": "Фамилия",
            "phone": "Номер",
            "key": "Ключ",
            "role": "Роль",
        }
        field_names = {
            key: value for key, value in field_names.items() if key in fields
        }

        header = " | ".join(
            [f"*{field_names[field]}*" for field in fields if field in field_names]
        )

        separator = " | ".join(["────" * len(fields)])

        rows = []
        for user in result:
            roles = []
            if user.is_admin:
                roles.append("Администратор")
            if user.is_teacher:
                roles.append("Учитель")
            if not roles:
                roles.append("Ученик")
            roles = ", ".join(roles)

            row = [
                f"`{user.id}`" if "id" in fields else "",
                user.name if "name" in fields else "",
                user.surname if "surname" in fields else "",
                user.phone if "phone" in fields else "",
                f"`{user.api_key}`" if "key" in fields else "",
                roles if "role" in fields else "",
            ]
            row = " | ".join(r for r in row if r)
            rows.append(row)

        header = f"{header}\n{separator}\n"
        if not with_header:
            header = ""
        message = header + "\n".join(rows)

        return message


class Course(Base):
    __tablename__ = "courses"

    id = Column(BigInteger, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    icon = Column(String)

    def __init__(self, title, description, icon):
        self.title = title
        self.description = description
        self.icon = icon

    @staticmethod
    def get_course_by_id(session, course_id):
        return session.query(Course).filter(Course.id == course_id).first()

    @staticmethod
    def create_course(session, title, description, icon):
        course = Course(
            title=title,
            description=description,
            icon=icon,
        )
        session.add(course)
        session.commit()
        session.refresh(course)
        return course

    @staticmethod
    def get_course_by_title(session, title):
        return session.query(Course).filter(Course.title == title).first()

    @staticmethod
    def get_courses_by_field(session, field: str, value: str):
        if not hasattr(Course, field):
            return None

        return session.query(Course).filter(getattr(Course, field) == value).all()

    @staticmethod
    def delete_course_by_id(session, course_id):
        course_to_delete = session.query(Course).filter(Course.id == course_id).first()

        return_data = None
        if course_to_delete:

            if groups := (
                session.query(Group)
                .filter(Group.course_id == course_to_delete.id)
                .all()
            ):
                return groups

            return_data = {"id": course_to_delete.id, "title": course_to_delete.title}
            session.delete(course_to_delete)
            session.commit()
        return return_data

    @staticmethod
    def get_courses(session):
        return session.query(Course).all()

    @staticmethod
    def delete_course_by_title(session, title):
        courses_to_delete = session.query(Course).filter(Course.title == title).all()
        if courses_to_delete:
            for course in courses_to_delete:
                session.delete(course)
            session.commit()
        return courses_to_delete

    async def send_result_message(result, with_header=True):
        if not result:
            return "Курс не найден."

        field_names = {
            "id": "id",
            "titile": "Название",
        }

        header = " | ".join([f"*{field}*" for field in field_names.values()])

        separator = " | ".join(["────" * len(field_names)])

        rows = []
        for course in result:
            row = [
                f"`{course.id}`",
                f"`{course.title}`",
            ]
            row = " | ".join(r for r in row if r)
            rows.append(row)

        header = f"{header}\n{separator}\n"
        if not with_header:
            header = ""
        message = header + "\n".join(rows)

        return message


class Group(Base):
    __tablename__ = "groups"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    teacher_id = Column(BigInteger, ForeignKey("users.id"))
    course_id = Column(BigInteger, ForeignKey("courses.id"))
    chat_id = Column(BigInteger, nullable=True)

    teacher = relationship("User", foreign_keys=[teacher_id])
    course = relationship("Course", foreign_keys=[course_id])

    def __init__(self, name, teacher_id, course_id, chat_id=None):
        self.name = name
        self.teacher_id = teacher_id
        self.course_id = course_id
        self.chat_id = chat_id

    @staticmethod
    def create_group(session, course_id, teacher_id):
        from datetime import datetime

        current_year = str(datetime.now().year)[-2:]

        course = Course.get_course_by_id(session, course_id)
        if not course:
            return None

        existing_groups_count = (
            session.query(Group).filter(Group.course_id == course.id).count()
        )

        group_name = f"{course.title}{current_year}{existing_groups_count + 1}"

        teacher = User.get_user_by_id(session, teacher_id)

        if not teacher or not teacher.is_teacher:
            return None

        group = Group(name=group_name, teacher_id=teacher_id, course_id=course.id)
        session.add(group)
        session.commit()
        session.refresh(group)

        return group

    @staticmethod
    def get_group_by_id(session, group_id):
        return session.query(Group).filter(Group.id == group_id).first()

    @staticmethod
    def get_group_by_name(session, group_name):
        return session.query(Group).filter(Group.name == group_name).first()

    @staticmethod
    def delete_group_by_id(session, group_id):
        group_to_delete = session.query(Group).filter(Group.id == group_id).first()
        return_data = None
        if group_to_delete:
            GroupUserLnk.delete_by_group_id(session, group_to_delete.id)
            return_data = {"id": group_to_delete.id, "name": group_to_delete.name}
            session.delete(group_to_delete)
            session.commit()
        return return_data

    @staticmethod
    def get_group_by_field(session, field, value):
        if not hasattr(Group, field):
            return None

        return session.query(Group).filter(getattr(Group, field) == value).all()

    @staticmethod
    def get_groups(session):
        return session.query(Group).all()

    async def send_result_message(
        result, fields=["id", "name", "course", "teacher"], with_header=True
    ):
        if not result:
            return "Группа не найдена."

        field_names = {
            "id": "id",
            "name": "Название",
            "course": "Курс",
            "teacher": "Преподаватель",
        }

        field_names = {
            key: value for key, value in field_names.items() if key in fields
        }

        header = " | ".join(
            [f"*{field_names[field]}*" for field in fields if field in field_names]
        )

        separator = " | ".join(["────" * len(fields)])

        rows = []
        for group in result:
            session = SessionLocal()
            course = Course.get_course_by_id(session, group.course_id).title
            teacher = User.get_user_by_id(session, group.teacher_id)
            teacher_name = f"{teacher.name} {teacher.surname}" if teacher else ""
            session.close()
            row = [
                f"`{group.id}`" if "id" in fields else "",
                group.name if "name" in fields else "",
                course if "course" in fields else "",
                teacher_name if "teacher" in fields else "",
            ]
            row = " | ".join(r for r in row if r)
            rows.append(row)

        header = f"{header}\n{separator}\n"
        if not with_header:
            header = ""
        message = header + "\n".join(rows)

        return message

    async def send_groups_inline_keyboard(groups):
        if not groups:
            return None

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            *[
                InlineKeyboardButton(group.name, callback_data=str(group.id))
                for group in groups
            ]
        )
        return keyboard


class GroupUserLnk(Base):
    __tablename__ = "group_user_link"

    id = Column(BigInteger, primary_key=True, index=True)
    group_id = Column(BigInteger, ForeignKey("groups.id"))
    user_id = Column(BigInteger, ForeignKey("users.id"))

    group = relationship("Group", foreign_keys=[group_id])
    user = relationship("User", foreign_keys=[user_id])

    def __init__(self, group_id, user_id):
        self.group_id = group_id
        self.user_id = user_id

    @staticmethod
    def create(session, group, user):
        if user.is_admin or user.is_teacher:
            return None

        link = GroupUserLnk(group_id=group.id, user_id=user.id)
        session.add(link)
        session.commit()

        return link

    @staticmethod
    def get_students_of_group(session, group_id):
        students = (
            session.query(User)
            .join(GroupUserLnk, User.id == GroupUserLnk.user_id)
            .filter(
                GroupUserLnk.group_id == group_id,
                User.is_teacher == False,
                User.is_admin == False,
            )
            .all()
        )

        return students

    @staticmethod
    def get_groups_of_user(session, user_id):
        groups = (
            session.query(Group)
            .join(GroupUserLnk, Group.id == GroupUserLnk.group_id)
            .filter(GroupUserLnk.user_id == user_id)
            .all()
        )

        return groups

    @staticmethod
    def delete_by_group_id(session, group_id):
        session.query(GroupUserLnk).filter(GroupUserLnk.group_id == group_id).delete()
        session.commit()

    @staticmethod
    def delete_by_users(session, users):
        user_ids = [user.id for user in users]
        users = (
            session.query(GroupUserLnk)
            .filter(GroupUserLnk.user_id.in_(user_ids))
            .delete()
        )
        session.commit()
        return users

    @staticmethod
    def create_links_for_users(session, user_ids, group_id: int):
        linked_users = []

        for user in user_ids:
            if not user.is_admin and not user.is_teacher:
                link = GroupUserLnk(group_id=group_id, user_id=user.id)
                session.add(link)
                linked_users.append(user)

        session.commit()
        return linked_users


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(BigInteger, primary_key=True, index=True)
    group_id = Column(BigInteger, ForeignKey("groups.id"), nullable=False)
    datetime = Column(DateTime, nullable=False)
    task = Column(Text, nullable=True)
    task_file = Column(String, nullable=True)

    group = relationship("Group", back_populates="lessons")

    def __init__(self, group_id, datetime, task=None, task_file=None):
        self.group_id = group_id
        self.datetime = datetime
        self.task = task
        self.task_file = task_file

    @staticmethod
    def create_lesson(session, group_id, datetime, task=None, task_file=None):
        lesson = Lesson(
            group_id=group_id, datetime=datetime, task=task, task_file=task_file
        )
        session.add(lesson)
        session.commit()
        session.refresh(lesson)
        return lesson

    @staticmethod
    def get_lesson_by_id(session, lesson_id):
        return session.query(Lesson).filter(Lesson.id == lesson_id).first()

    @staticmethod
    def get_lessons_by_group(session, group_id):
        return session.query(Lesson).filter(Lesson.group_id == group_id).all()

    @staticmethod
    def delete_lesson_by_id(session, lesson_id):
        lesson_to_delete = session.query(Lesson).filter(Lesson.id == lesson_id).first()
        if lesson_to_delete:
            session.delete(lesson_to_delete)
            session.commit()
        return lesson_to_delete

    def get_lessons_in_time_range(session, time_start, teacher_id):
        return (
            session.query(Lesson)
            .join(Group)
            .filter(
                Lesson.datetime.between(
                    time_start - timedelta(hours=1.49),
                    time_start + timedelta(hours=1.49),
                ),
                Group.teacher_id == teacher_id,
            )
            .all()
        )

    @staticmethod
    def get_lessons_by_teacher_and_date(session, teacher_id, date):
        return (
            session.query(Lesson)
            .join(Group)
            .filter(
                Group.teacher_id == teacher_id,
                Lesson.datetime >= date,
                Lesson.datetime < date + timedelta(days=1),
            )
            .order_by(Lesson.datetime)
            .all()
        )

    @staticmethod
    def get_student_lessons_next_month(session, student_id):
        from datetime import datetime

        current_date = datetime.now()
        next_month_date = current_date + timedelta(days=30)

        lessons = (
            session.query(Lesson)
            .join(Group)
            .join(
                GroupUserLnk,
                and_(
                    Group.id == GroupUserLnk.group_id,
                    GroupUserLnk.user_id == student_id,
                ),
            )
            .filter(Lesson.datetime >= current_date, Lesson.datetime < next_month_date)
            .order_by(Lesson.datetime)
            .all()
        )

        return lessons

    @staticmethod
    def get_next_lesson_for_student(session, student_id):
        from datetime import datetime

        current_date = datetime.now()

        next_lesson = (
            session.query(Lesson)
            .join(Group)
            .join(
                GroupUserLnk,
                and_(
                    Group.id == GroupUserLnk.group_id,
                    GroupUserLnk.user_id == student_id,
                ),
            )
            .filter(Lesson.datetime >= current_date)
            .order_by(Lesson.datetime)
            .first()
        )

        return next_lesson

    @staticmethod
    def get_last_completed_lesson_for_student(session, student_id):
        from datetime import datetime

        current_date = datetime.now()

        last_lesson = (
            session.query(Lesson)
            .join(Group)
            .join(
                GroupUserLnk,
                and_(
                    Group.id == GroupUserLnk.group_id,
                    GroupUserLnk.user_id == student_id,
                ),
            )
            .filter(Lesson.datetime < current_date)
            .order_by(Lesson.datetime.desc())
            .first()
        )

        return last_lesson

    async def send_result_message(
        result,
        fields=["id", "group_id", "datetime", "teacher", "task", "task_file"],
        with_header=True,
    ):
        if not result:
            return "Уроки не найдены."

        field_names = {
            "id": "id",
            "group_id": "Группа",
            "datetime": "Дата и время",
            "teacher": "Преподаватель",
            "task": "Задание",
            "task_file": "Файл задания",
        }

        field_names = {
            key: value for key, value in field_names.items() if key in fields
        }

        header = " | ".join(
            [f"*{field_names[field]}*" for field in fields if field in field_names]
        )

        separator = " | ".join(["────" * len(fields)])

        rows = []
        for lesson in result:
            session = SessionLocal()
            group = session.query(Group).filter(Group.id == lesson.group_id).first()

            group_name = group.name
            tacher = User.get_user_by_id(session, group.teacher_id)
            teacher_name = f"{tacher.name} {tacher.surname}"
            session.close()
            row = [
                f"`{lesson.id}`" if "id" in fields else "",
                f"`{group_name}`" if "group_id" in fields else "",
                (
                    lesson.datetime.strftime("%d/%m/%Y %H:%M")
                    if "datetime" in fields
                    else ""
                ),
                (teacher_name if "teacher" in fields else ""),
                lesson.task if "task" in fields else "",
                lesson.task_file if "task_file" in fields else "",
            ]
            row = " | ".join(r for r in row if r)
            rows.append(row)

        header = f"{header}\n{separator}\n"
        if not with_header:
            header = ""
        message = header + "\n".join(rows)

        return message

    async def send_lessons_inline_keyboard(lessons):
        if not lessons:
            return None
        session = SessionLocal()
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            *[
                InlineKeyboardButton(
                    f"{session.query(Group).filter(Group.id == lesson.group_id).first().name} {lesson.datetime.strftime('%H:%M')}",
                    callback_data=str(lesson.id),
                )
                for lesson in lessons
            ]
        )

        session.close()
        return keyboard


Group.lessons = relationship("Lesson", order_by=Lesson.id, back_populates="group")
Base.metadata.create_all(engine)
