import contextvars

from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware

from config import SessionLocal, Base, engine, dp, get_all_ids, add_id
from database.models import *


data_var = contextvars.ContextVar("data")


class GroupCheckMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        # self.session = session

    async def on_pre_process_message(self, message: types.Message, data: dict):
        if (
            message.from_user
            and (telegram_id := str(message.from_user.id))
            and not telegram_id in get_all_ids()
        ):
            session = SessionLocal()
            user = User.get_user_by_telegram_id(session, telegram_id)
            session.close()
            user_roles = set()
            if user:
                if user.is_admin:
                    user_roles.add("admin")
                    add_id(telegram_id, "admin")
                if user.is_teacher:
                    user_roles.add("teacher")
                    add_id(telegram_id, "teacher")
                if not user.is_teacher and not user.is_admin:
                    user_roles.add("student")
                    add_id(telegram_id, "student")

            data["user_roles"] = user_roles

        data_var.set(data)
        return


Base.metadata.create_all(bind=engine)
dp.middleware.setup(GroupCheckMiddleware())
