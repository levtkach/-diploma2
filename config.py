import os
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware


from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

student_ids = set()
admin_ids = set()
teacher_ids = set()

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

Base = declarative_base()
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_admin_ids():
    return admin_ids


def get_teacher_ids():
    return teacher_ids


def get_student_ids():
    return student_ids


def get_all_ids():
    return admin_ids | teacher_ids | student_ids


def update_ids(id):
    global student_ids, admin_ids, teacher_ids
    if id in student_ids:
        student_ids.remove(id)
    if id in admin_ids:
        admin_ids.remove(id)
    if id in teacher_ids:
        teacher_ids.remove(id)


def add_id(telegram_id, type):
    global student_ids, admin_ids, teacher_ids
    if type == "admin":
        admin_ids.add(telegram_id)
    if type == "teacher":
        teacher_ids.add(telegram_id)
    if type == "student":
        student_ids.add(telegram_id)
