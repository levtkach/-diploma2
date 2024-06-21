from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)

back_or_cancel_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
back_or_cancel_keyboard.add(KeyboardButton("Назад"), KeyboardButton("Отмена❌"))

cancel_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
cancel_keyboard.add(KeyboardButton("Отмена❌"))

start_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
start_keyboard.add(KeyboardButton("Начать👋"))

cancel_back_confirm_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
cancel_back_confirm_keyboard.add(
    KeyboardButton("Назад"), KeyboardButton("Отмена❌"), KeyboardButton("Подтвердить")
)

cancel_continue_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
cancel_continue_keyboard.add(KeyboardButton("Отмена❌"), KeyboardButton("Пропустить"))

confirm_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
confirm_keyboard.add(KeyboardButton("Отмена❌"), KeyboardButton("Подтвердить"))

admin_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
admin_keyboard.add(
    KeyboardButton("Новый пользователь✅"),
    KeyboardButton("Найти пользователя🔎"),
    KeyboardButton("Удалить пользователя🗑️"),
    KeyboardButton("Новый курс✅"),
    KeyboardButton("Все курсы🔎"),
    KeyboardButton("Удалить курс🗑️"),
    KeyboardButton("Новая группа✅"),
    KeyboardButton("Найти группу🔎"),
    KeyboardButton("Удалить группу🗑️"),
    KeyboardButton("Заменить преподавателя👨🏻‍🏫"),
    KeyboardButton("Добавить учеников в группу➕"),
    KeyboardButton("Убрать учеников из группы➖"),
)

teacher_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
teacher_keyboard.add(
    KeyboardButton("Назначить урок📝"),
    KeyboardButton("Расписание📅"),
    KeyboardButton("Отменить урок🗑️"),
)

student_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
student_keyboard.add(
    KeyboardButton("Ближайший урок📝"),
    KeyboardButton("Расписание📅"),
    KeyboardButton("Домашнее задание📚"),
)
