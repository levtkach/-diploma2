from aiogram.utils import executor

from config import dp
import middleware.group_check


from handlers import chat, public, admin, student, teacher, all_roles


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
