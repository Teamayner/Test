import telebot
import random
import os
import re
import sqlite3
import datetime
import requests
import calendar
from datetime import datetime, timedelta
from telebot import types

bot = telebot.TeleBot('8223641342:AAG7XpC29VEcgKZw54bzkcRkKvjLzUyhuXs')
print('Бот работает')
request_counter = 0
user_data = {}
admin_id = 5179669274
photo_types = ['Водительские права', 'Фото СТС', 'Фото машины (спереди)', 'Фото машины (сзади)']
user_progress = {}
last_photo_msg = {}
user_state = {}
user_dates = {}
pending_codes = {}
CODE_REGEX = re.compile(r"\b\d{4}\b")
conn = sqlite3.connect("sqlite.db", check_same_thread=False)
cursor = conn.cursor()
BAD_WORDS = ["хуй", "блядь", "сука", "ебать", "пизда", "мразь", "пидор", "пидорас", "блять", "нахуй", "пиздец", "мудак",
             "сволочь", "гавно", "говно", "гандон", "ебаный"]


def get_random_premium_user():
    cursor.execute("SELECT user_id FROM subsciptions WHERE subscription = 'premium'")
    premium_users = cursor.fetchall()
    if not premium_users:
        return None
    return random.choice(premium_users)[0]


def inline_update_button(photo_type):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Обновить", callback_data=f"update1_{photo_type}"))
    return markup


def contains_bad_words(text: str) -> bool:
    text_lower = text.lower()
    return any(bad in text_lower for bad in BAD_WORDS)


def check_subscription(user_id):
    cursor.execute("SELECT subscription, expire_date, is_active FROM subsciptions WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        return "none", None, False
    sub, expire_date, active = row
    if expire_date:
        expire_date = datetime.strptime(expire_date, "%Y-%m-%d")
        if datetime.now() > expire_date:
            cursor.execute("UPDATE subsciptions SET subscription='none', is_active=0 WHERE user_id=?", (user_id,))
            conn.commit()
            return "none", None, False
    return sub, expire_date, bool(active)


def generate_time_keyboard(user_id):
    sub, expire, active = check_subscription(user_id)
    markup = types.InlineKeyboardMarkup(row_width=4)
    if sub == "basic":
        start, end = 7, 22
    else:
        start, end = 0, 24
    buttons = []
    for hour in range(start, end):
        buttons.append(types.InlineKeyboardButton(text=f"{hour:02d}:00", callback_data=f"time_{hour:02d}:00"))
    markup.add(*buttons)
    return markup


def create_calendar1(year=None, month=None, chat_id=None):
    now = datetime.now()
    today = datetime(now.year, now.month, now.day)
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(f"{calendar.month_name[month]} {year}", callback_data="ignore1"))
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    markup.row(*[types.InlineKeyboardButton(day, callback_data="ignore1") for day in week_days])
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(types.InlineKeyboardButton(" ", callback_data="ignore1"))
            else:
                day_date = datetime(year, month, day)
                date_str = f"{day:02d}.{month:02d}.{year}"

                if day_date < today:
                    row.append(types.InlineKeyboardButton(f"{day}\u00B7", callback_data="ignore1"))
                else:
                    if chat_id in user_dates and date_str in user_dates[chat_id]:
                        row.append(types.InlineKeyboardButton(f"{day}✅", callback_data=f"day1_{year}_{month}_{day}"))
                    else:
                        row.append(types.InlineKeyboardButton(str(day), callback_data=f"day1_{year}_{month}_{day}"))
        markup.row(*row)
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    markup.row(
        types.InlineKeyboardButton("<", callback_data=f"prev1_{prev_year}_{prev_month}"),
        types.InlineKeyboardButton(">", callback_data=f"next1_{next_year}_{next_month}")
    )
    markup.row(types.InlineKeyboardButton("✅ Дальше", callback_data="next_step"))
    return markup


def create_calendar(year=None, month=None):
    now = datetime.now()
    today = datetime(now.year, now.month, now.day)
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    markup = types.InlineKeyboardMarkup()
    row = [
        types.InlineKeyboardButton(
            text=f"{calendar.month_name[month]} {year}", callback_data="ignore"
        )
    ]
    markup.row(*row)
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    markup.row(*[types.InlineKeyboardButton(day, callback_data="ignore") for day in week_days])
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(types.InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                day_date = datetime(year, month, day)
                if day_date < today:
                    row.append(types.InlineKeyboardButton(f"{day}\u00B7", callback_data="ignore"))
                else:
                    row.append(types.InlineKeyboardButton(str(day), callback_data=f"day_{year}_{month}_{day}"))
        markup.row(*row)
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    row = [
        types.InlineKeyboardButton("<", callback_data=f"prev_{prev_year}_{prev_month}"),
        types.InlineKeyboardButton(">", callback_data=f"next_{next_year}_{next_month}")
    ]
    markup.row(*row)
    return markup


def set_subscription(user_id, sub_type):
    expire_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    cursor.execute("UPDATE subsciptions SET subscription=?, expire_date=?, is_active=1 WHERE user_id=?",
                   (sub_type, expire_date, user_id))
    conn.commit()


def register_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO subsciptions (user_id) VALUES (?)", (user_id,))
    conn.commit()


@bot.message_handler(commands=['start'])
def start(message):
    button1 = types.KeyboardButton(text='💼 Заказчик')
    button2 = types.KeyboardButton(text='🤵 Водитель')
    markup1 = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup1.add(button1, button2)
    register_user(message.chat.id)
    bot.send_message(message.chat.id, '🙋‍♂️ Приветствую тебя пользователь! Выбери роль', reply_markup=markup1)


@bot.message_handler(commands=['setbasic'])
def setbasic(self):
    msg = bot.send_message(admin_id, 'Введите user_id, чтобы выдать пользователю базовую подписку')
    bot.register_next_step_handler(msg, user_id3)


def user_id3(message):
    try:
        user_id = int(message.text)
        set_subscription(user_id, "basic")
        bot.send_message(user_id, "Вам выдана базовая подписка на 30 дней!")
        bot.send_message(admin_id, f"Базовая подписка успешно выдана пользователю")
    except ValueError:
        bot.send_message(admin_id, 'id должен состоять из цифр')


@bot.message_handler(commands=['setpremium'])
def setbasic(self):
    msg = bot.send_message(admin_id, 'Введите user_id, чтобы выдать пользователю расширенную подписку')
    bot.register_next_step_handler(msg, user_id4)


def user_id4(message):
    try:
        user_id = int(message.text)
        set_subscription(user_id, "premium")
        bot.send_message(user_id, "Вам выдана премиум подписка на 30 дней!")
        bot.send_message(admin_id, f"Премиум подписка успешно выдана пользователю")
    except ValueError:
        bot.send_message(admin_id, 'id должен состоять из цифр')


@bot.message_handler(commands=['approve'])
def approve(self):
    msg = bot.send_message(admin_id, 'Введите user_id, чтобы разрешить водителю зарегистрироваться')
    bot.register_next_step_handler(msg, user_id1)


def user_id1(message):
    button6 = types.KeyboardButton(text='🚚 Мои перевозки')
    button7 = types.KeyboardButton(text='👨‍🏭 Мой профиль')
    button8 = types.KeyboardButton(text='🚗 Создать маршрут перевозки')
    button9 = types.KeyboardButton(text='📦 Поиск груза')
    button10 = types.KeyboardButton(text='🔔 Подписки')
    button11 = types.KeyboardButton(text='🏷️ Избранное')
    markup2 = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup2.add(button6, button7, button8, button9, button10, button11)
    bot.send_message(message.chat.id, "Ознакомьтесь с меню", reply_markup=markup2)
    user_id = int(message.text)
    cursor.execute("UPDATE drivers SET status='одобрено' WHERE user_id=?", (user_id,))
    cursor.execute("SELECT user_id FROM ids WHERE user_id=?", (user_id,))
    conn.commit()
    bot.send_message(user_id, "Ваша регистрация подтверждена! Теперь вам доступно меню", reply_markup=markup2)
    bot.send_message(admin_id, f"Пользователь {user_id} одобрен")


@bot.message_handler(commands=['reject'])
def reject(self):
    msg = bot.send_message(admin_id, 'Введите user_id, чтобы отклонить водителю зарегистрироваться')
    bot.register_next_step_handler(msg, user_id2)


def user_id2(message):
    try:
        user_id = int(message.text.split()[1])
        cursor.execute("UPDATE drivers SET status='отклонено' WHERE user_id=?", (user_id,))
        conn.commit()
        bot.send_message(user_id, "Ваша заявка отклонена администратором")
        bot.send_message(admin_id, f"Пользователь {user_id} отклонён")
    except:
        bot.send_message(admin_id, 'Ошибка! Введите корректный ID пользователя (число)')


@bot.message_handler(commands=['reject1'])
def reject1(self):
    msg = bot.send_message(admin_id, 'Введите user_id, чтобы отклонить водителю зарегистрироваться')
    bot.register_next_step_handler(msg, user_id5)


def user_id5(message):
    try:
        user_id = int(message.text.split()[1])
        bot.send_message(user_id, "Ваша заявка отклонена администратором")
        bot.send_message(admin_id, f"Пользователь {user_id} отклонён")
    except:
        bot.send_message(admin_id, 'Ошибка! Введите корректный ID пользователя (число)')


@bot.message_handler(commands=['drivers'])
def drivers(message):
    cursor.execute("SELECT * FROM drivers")
    rows2 = cursor.fetchall()
    cursor.execute("SELECT * FROM drivers")
    rows = cursor.fetchall()
    if not rows:
        bot.send_message(message.chat.id, "Заявок пока нет")
        return
    for row in rows2:
        id = row[1]
        FIO = row[2]
        number = row[4]
        text2 = (f"Айди: {id}\n"
                 f"ФИО: {FIO}\n"
                 f"Номер телефона: {number}"
                 )
        bot.send_message(message.chat.id, text2)
    for row in rows:
        photo_type = row[2]
        file_path = row[3]
        try:
            with open(file_path, 'rb') as photo:
                bot.send_photo(message.chat.id, photo=photo, caption=photo_type)
        except Exception as e:
            bot.send_message(message.chat.id, f"Ошибка: не удалось открыть {file_path}\n{e}")


@bot.message_handler(func=lambda message: True)
def text(message):
    global FIO
    button = types.KeyboardButton(text='📩 Создать заявку')
    button2 = types.KeyboardButton(text='👤 Мой профиль')
    button3 = types.KeyboardButton(text='📌 Мои заявки')
    button4 = types.KeyboardButton(text='🚚 Поиск машины')
    button5 = types.KeyboardButton(text='📢 Заказать рекламу')
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(button, button2, button3, button4, button5)

    button6 = types.KeyboardButton(text='🚚 Мои перевозки')
    button7 = types.KeyboardButton(text='👨‍🏭 Мой профиль')
    button8 = types.KeyboardButton(text='🚗 Создать маршрут перевозки')
    button9 = types.KeyboardButton(text='📦 Поиск груза')
    button10 = types.KeyboardButton(text='🔔 Подписки')
    button11 = types.KeyboardButton(text='🏷️ Избранное')
    markup2 = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup2.add(button6, button7, button8, button9, button10, button11)

    user_id = message.chat.id
    cursor.execute("SELECT * FROM user WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    user_id1 = message.chat.id
    cursor.execute("SELECT * FROM drivers WHERE user_id=?", (user_id1,))
    user1 = cursor.fetchone()

    user_id2 = message.chat.id
    cursor.execute("SELECT * FROM drivers WHERE user_id=?", (user_id2,))

    if message.text == '💼 Заказчик':
        if user:
            bot.send_message(message.chat.id, "Ознакомьтесь с данным меню", reply_markup=markup)
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            button = types.KeyboardButton("📱 Отправить контактные данные", request_contact=True)
            markup.add(button)
            user_state[message.chat.id] = "registration1"
            bot.send_message(user_id, "📞 Отправьте ваш номер телефона с помощью кнопки ниже 👇", reply_markup=markup)

    if message.text == '🤵 Водитель':
        if user1:
            cursor.execute("SELECT status FROM drivers WHERE user_id=?", (message.chat.id,))
            row = cursor.fetchone()
            status = row[0]
            if not row:
                bot.send_message(chat_id, "Вы ещё не зарегистрированы. Отправьте /start")
                return
            if status == "одобрено":
                user_data[message.chat.id] = {}
                bot.send_message(message.chat.id, '✅ Добро пожаловать в меню!', reply_markup=markup2)
            elif status == "на проверке":
                bot.send_message(message.chat.id, "🕛 Ваша заявка на проверке. Ждите подтверждения администратора")
            elif status == "отклонен":
                bot.send_message(message.chat.id, "❌ Ваша заявка была отклонена. Обратитесь к администратору")
        else:
            msg = bot.send_message(message.chat.id, '👤 Введите ваше ФИО')
            bot.register_next_step_handler(msg, FIO)

    if message.text == '👤 Мой профиль':
        button = types.KeyboardButton(text='🔄 Повторная регистрация')
        button2 = types.KeyboardButton(text='⬅️ Назад')
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(button, button2)
        cursor.execute("SELECT u.name, u.number FROM user u WHERE u.user_id=?", (message.chat.id,))
        row = cursor.fetchone()
        if row:
            name, number = row
            bot.send_message(message.chat.id, f'Мой профиль:\n\n👤 Ваше имя: {name}\n📞 Ваш номер телефона: {number}',
                             reply_markup=markup)

    if message.text == '⬅️ Назад':
        button = types.KeyboardButton(text='📩 Создать заявку')
        button2 = types.KeyboardButton(text='👤 Мой профиль')
        button3 = types.KeyboardButton(text='📌 Мои заявки')
        button4 = types.KeyboardButton(text='🚚 Поиск машины')
        button5 = types.KeyboardButton(text='📢 Заказать рекламу')
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(button, button2, button3, button4, button5)
        bot.send_message(message.chat.id, 'Ознакомьтесь с данным меню', reply_markup=markup)

    if message.text == '🔄 Повторная регистрация':
        cursor.execute("SELECT user_id FROM user WHERE user_id=?", (message.chat.id,))
        row = cursor.fetchone()
        if not row:
            bot.send_message(message.chat.id, "❌ Такого пользователя не существует")
            return
        cursor.execute("DELETE FROM user WHERE user_id=?", (message.chat.id,))
        conn.commit()
        button1 = types.KeyboardButton(text='💼 Заказчик')
        button2 = types.KeyboardButton(text='🤵 Водитель')
        markup1 = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup1.add(button1, button2)
        bot.send_message(message.chat.id, "❌ Старые данные были удалены")
        bot.send_message(message.chat.id, "🙋‍♂️ Приветствую тебя! Выбери роль", reply_markup=markup1)

    if message.text == '📢 Заказать рекламу':
        button = types.KeyboardButton(text='⬅️ Назад')
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(button)
        bot.send_message(message.chat.id, '📢 Для оформления рекламы свяжитесь с нашими модераторами:\n\n'
                                          '👤 Евгений — @Evgeniy_NUR\n'
                                          '👤 Роман — @ROMANPC01', reply_markup=markup
                         )

    if message.text == '👨‍🏭 Мой профиль':
        cursor.execute("""
            SELECT d.FIO, d.number, d.status, AVG(f.rating), s.subscription
            FROM drivers d
            LEFT JOIN feedback f ON d.user_id = f.user_id
            LEFT JOIN subsciptions s ON d.user_id = s.user_id
            WHERE d.user_id=?
        """, (message.chat.id,))
        row = cursor.fetchone()
        cursor.execute("""
            SELECT photo_type, file_path
            FROM driver_photos
            WHERE user_id=?
            ORDER BY id
        """, (message.chat.id,))
        photos = cursor.fetchall()
        if row:
            FIO, phone_number, status, avg, subscription = row
            avg = round(avg, 1) if avg else "Нет оценок"
            markup2 = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            button2 = types.KeyboardButton(text='⬅️ Вернутся в главное меню')
            markup2.add(button2)
            bot.send_message(message.chat.id, text=f'Профиль {message.from_user.first_name}:\n'
                                                   f'👤 ФИО: {FIO}\n'
                                                   f'🆔 ID профиля: {message.chat.id}\n'
                                                   f'🔔 Подписка: {subscription}\n'
                                                   f'📞 Номер телефона: {phone_number}\n'
                                                   f'⭐ Рейтинг: {avg}\n'
                                                   f'🔰 Статус KYC: {status}'
                             )
            for photo_type, file_path in photos:
                with open(file_path, 'rb') as f:
                    msg = bot.send_photo(message.chat.id, f, caption=photo_type,
                                         reply_markup=inline_update_button(photo_type))
                    if message.chat.id not in last_photo_msg:
                        last_photo_msg[message.chat.id] = {}
                    last_photo_msg[message.chat.id][photo_type] = msg.message_id

    if message.text == '⬅️ Вернутся в главное меню':
        button6 = types.KeyboardButton(text='🚚 Мои перевозки')
        button7 = types.KeyboardButton(text='👨‍🏭 Мой профиль')
        button8 = types.KeyboardButton(text='🚗 Создать маршрут перевозки')
        button9 = types.KeyboardButton(text='📦 Поиск груза')
        button10 = types.KeyboardButton(text='🔔 Подписки')
        button11 = types.KeyboardButton(text='🏷️ Избранное')
        markup2 = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup2.add(button6, button7, button8, button9, button10, button11)
        bot.send_message(message.chat.id, "Ознакомьтесь с данным меню", reply_markup=markup2)

    if message.text == '🏷️ Избранное':
        cursor.execute("SELECT application FROM favorites WHERE user_id=?", (message.chat.id,))
        rows = cursor.fetchall()
        if not rows:
            bot.send_message(message.chat.id, "У вас пока нет избранных записей")
        else:
            favs = "\n".join([row[0] for row in rows])
            bot.send_message(message.chat.id, f"Ваши избранные:\n\n{favs}")

    if message.text == '🚚 Поиск машины':
        sub, expire, active = check_subscription(message.from_user.id)
        cursor.execute("SELECT text FROM routes_2")
        rows = cursor.fetchall()

        cursor.execute("SELECT text FROM routes")
        rows1 = cursor.fetchall()
        if not active:
            bot.send_message(message.chat.id, 'Нету водителей в базе')

        for row in rows:
            text = row[0]
            if sub == "basic":
                bot.send_message(message.chat.id, text)

        for row in rows1:
            text = row[0]
            if sub == "premium":
                bot.send_message(message.chat.id, text)

    if message.text == '📦 Поиск груза':
        sub, expire, active = check_subscription(message.from_user.id)
        if not active:
            bot.send_message(message.chat.id,
                             'Ваши заявки скрыты. Преобретите базовую или расширенную подписку, чтобы вы могли видеть заявки')
        elif sub == "basic":
            cursor.execute("SELECT id, text FROM applications ORDER BY RANDOM() LIMIT 5")
            rows = cursor.fetchall()
            if not rows:
                bot.send_message(message.chat.id, "Пока нет заявок для базовой подписки")
            else:
                for row in rows:
                    application_id, text = row
                    markup = types.InlineKeyboardMarkup(row_width=True)
                    button1 = types.InlineKeyboardButton(text='📩 Откликнуться',
                                                         callback_data=f'respond_{application_id}')
                    button2 = types.InlineKeyboardButton(text='❌ Удалить заявку',
                                                         callback_data=f'delete_{application_id}')
                    button3 = types.InlineKeyboardButton(text='🏷️ Сохранить в избранное',
                                                         callback_data=f'save_fav_{application_id}')
                    button4 = types.InlineKeyboardButton(text='🔄 Обновить', callback_data=f'update_{application_id}')
                    markup.add(button1, button2, button3, button4)
                    bot.send_message(message.chat.id, f'{application_id}. {text}', reply_markup=markup)
        elif sub == "premium":
            cursor.execute("SELECT id, text FROM applications ORDER BY RANDOM() LIMIT 5")
            rows = cursor.fetchall()
            if not rows:
                bot.send_message(message.chat.id, "Пока нет заявок для расширенной подписки")
            else:
                for row in rows:
                    application_id, text = row
                    markup = types.InlineKeyboardMarkup(row_width=True)
                    button1 = types.InlineKeyboardButton(text='📩 Откликнуться',
                                                         callback_data=f'respond_{application_id}')
                    button2 = types.InlineKeyboardButton(text='❌ Удалить заявку',
                                                         callback_data=f'delete_{application_id}')
                    button3 = types.InlineKeyboardButton(text='🏷️ Сохранить в избранное',
                                                         callback_data=f'save_fav_{application_id}')
                    button4 = types.InlineKeyboardButton(text='🔄 Обновить', callback_data=f'update_{application_id}')
                    markup.add(button1, button2, button3, button4)
                    bot.send_message(message.chat.id, f'{application_id}. {text}', reply_markup=markup)

    if message.text == '🚗 Создать маршрут перевозки':
        user_data[message.chat.id] = {}
        cities = [
            'Надым', 'Ноябрьск', 'Тарко-Сале', 'Пангоды',
            'Лимбяяха', 'Салехард', 'Коротчаево',
            'Новый Уренгой', 'Губкинский'
        ]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
        buttons = [types.KeyboardButton(text=city) for city in cities]
        buttons1 = [types.KeyboardButton(text='🏙️ Другой город')]
        markup.add(*buttons, *buttons1)
        markup.add(types.KeyboardButton(text='⬅️ Назад'))
        msg = bot.send_message(message.chat.id, '📍 Откуда', reply_markup=markup)
        bot.register_next_step_handler(msg, route1_handler)

    if message.text == '🚚 Мои перевозки':
        user_id = message.chat.id
        cursor.execute("SELECT id, text FROM routes WHERE user_id=?", (user_id,))
        rows = cursor.fetchall()
        if not rows:
            button = types.InlineKeyboardButton(text='↩️ Вернуться в главное меню', callback_data='Меню_Водителя')
            markup_back = types.InlineKeyboardMarkup(row_width=True)
            markup_back.add(button)
            bot.send_message(user_id, 'У вас нету маршрутов', reply_markup=markup_back)
        else:
            for row in rows:
                app_id, app_text = row
                button = types.InlineKeyboardButton(text='↩️ Вернуться в главное меню', callback_data='Меню_Водителя')
                button2 = types.InlineKeyboardButton(text='❌ Удалить маршрут', callback_data=f'delete12_{app_id}')
                markup_back = types.InlineKeyboardMarkup(row_width=True)
                markup_back.add(button, button2)
                bot.send_message(user_id, f"Заявка #{app_id}\n{app_text}", reply_markup=markup_back)

    if message.text == '🔔 Подписки':
        markup = types.InlineKeyboardMarkup(row_width=True)
        button1 = types.InlineKeyboardButton(text='📗 Базовая', callback_data='Базовая')
        button2 = types.InlineKeyboardButton(text='📕 Расширенная', callback_data='Расширенная')
        markup.add(button1, button2)
        bot.send_message(message.chat.id, 'Выберите тип подписки', reply_markup=markup)

    if message.text == '📩 Создать заявку':
        user_data[message.chat.id] = {}
        now = datetime.now()
        markup = create_calendar(now.year, now.month)
        bot.send_message(message.chat.id, "📅 Выберите дату:", reply_markup=markup)

    if message.text == '📌 Мои заявки':
        user_id = message.chat.id
        cursor.execute("SELECT id, text, status FROM applications WHERE user_id=?", (user_id,))
        rows = cursor.fetchall()
        if not rows:
            markup_back = types.InlineKeyboardMarkup()
            markup_back.add(types.InlineKeyboardButton("↩️ Вернуться в главное меню", callback_data="Меню"))
            bot.send_message(user_id, "У вас нет заявок", reply_markup=markup_back)
        else:
            for row in rows:
                app_id, app_text, status = row
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("❌ Удалить заявку", callback_data=f"delete1_{app_id}"),
                    types.InlineKeyboardButton("↩️ Вернуться в главное меню", callback_data="Меню")
                )
                bot.send_message(user_id, f"Заявка #{app_id}\n{app_text}\nСтатус: {status}", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data == 'Базовая':
        user_state[call.message.chat.id] = "buy"
        bot.send_message(call.message.chat.id, 'Базовая подписка дает следующие функции:\n'
                                               '• Ручной режим с открытыми контактами\n'
                                               '• Автоматический подбор (список заявок, совпадающих с маршрутами)\n'
                                               'Отправьте скриншот подтверждения оплаты')
    if call.data == 'Расширенная':
        user_state[call.message.chat.id] = "buy"
        bot.send_message(call.message.chat.id, 'Расширенная подписка дает следующие функции:\n'
                                               '• Всё из базовой подписки'
                                               '• Автоуведомления о новых подходящих заявках\n'
                                               '• Расширенные фильтры автоподбора (габариты, типы погрузки, ограничения ТС, даты)\n'
                                               'Отправьте скриншот подтверждения оплаты')

    if call.data.startswith("time_"):
        chosen_time = call.data.split("_")[1]
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"✅ Вы выбрали время прибытия: {chosen_time}")
        response2(call.message)

    if call.data.startswith("delete1_"):
        app_id = int(call.data.split("_")[1])
        cursor.execute("SELECT user_id FROM applications WHERE id=?", (app_id,))
        row = cursor.fetchone()
        if not row:
            bot.send_message(call.message.chat.id, "Заявка не найдена")
            return
        cursor.execute("DELETE FROM applications WHERE id=?", (app_id,))
        conn.commit()
        bot.send_message(call.message.chat.id, f"Заявка #{app_id} успешно удалена ✅")

    if call.data == "next_step":
        chat_id = call.message.chat.id
        if chat_id not in user_dates or len(user_dates[chat_id]) < 2:
            bot.answer_callback_query(call.id, text="❌ Нужно выбрать минимум 2 даты!")
            return
        dates_text = ", ".join(user_dates[chat_id])
        user_data[call.message.chat.id]['дата1'] = dates_text
        bot.send_message(chat_id, f"Вы выбрали даты: {dates_text}")
        route3(call.message)

    if call.data.startswith("day_"):
        _, year, month, day = call.data.split("_")
        year, month, day = int(year), int(month), int(day)
        today = datetime.now().date()
        selected_date = datetime(year, month, day).date()
        if selected_date < today:
            bot.answer_callback_query(call.id, text="Нельзя выбрать прошедшую дату!")
            return
        date_str = f"{day:02d}.{month:02d}.{year}"
        user_data[call.message.chat.id]['срок'] = date_str
        bot.send_message(call.message.chat.id, f'Вы выбрали: {date_str}')
        application2(call.message)

    if call.data.startswith("day1_"):
        chat_id = call.message.chat.id
        _, year, month, day = call.data.split("_")
        year, month, day = int(year), int(month), int(day)
        date_str = f"{day:02d}.{month:02d}.{year}"
        if chat_id not in user_dates:
            user_dates[chat_id] = []
        if date_str in user_dates[chat_id]:
            user_dates[chat_id].remove(date_str)
        else:
            user_dates[chat_id].append(date_str)
        markup = create_calendar1(year, month, chat_id=chat_id)
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markup)

    if call.data.startswith("prev_") or call.data.startswith("next_"):
        parts = call.data.split("_")
        if len(parts) == 3:
            _, year, month = parts
            year = int(year)
            month = int(month)
            markup = create_calendar(year, month)
            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )

    if call.data.startswith("prev1_") or call.data.startswith("next1_"):
        _, year, month = call.data.split("_")
        year = int(year)
        month = int(month)
        markup = create_calendar1(year, month, chat_id=call.message.chat.id)
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

    if call.data == "ignore":
        bot.answer_callback_query(call.id, text="Нельзя указать предыдущий день")

    if call.data == "ignore1":
        bot.answer_callback_query(call.id, text="Нельзя указать предыдущий день")

    if call.data.startswith("save_fav_"):
        application_id = call.data.split("save_fav_")[1]
        cursor.execute("SELECT text FROM applications WHERE id=?", (application_id,))
        row = cursor.fetchone()
        if row:
            user_id = call.message.chat.id
            text = row[0]
            cursor.execute("INSERT INTO favorites (user_id, application) VALUES (?, ?)", (user_id, text))
            conn.commit()
            bot.send_message(call.message.chat.id, "Заявка была добавлена в избранное!")

    if call.data.startswith(f"respond_"):
        application_id = int(call.data.split("_")[1])
        driver_id = call.from_user.id
        user_data[driver_id] = {"application_id": application_id}
        msg = bot.send_message(driver_id, "Укажите цену")
        bot.register_next_step_handler(msg, response1)

    if call.data.startswith(f"confirm_"):
        parts = call.data.split("_")
        request_id = parts[1]
        driver_id = int(parts[2])
        data = user_data.get(driver_id, {})
        cursor.execute("""
            SELECT u.user_id, u.name 
            FROM applications a
            JOIN user u ON a.user_id = u.user_id
            WHERE a.id = ?
        """, (request_id,))
        row = cursor.fetchone()
        if not row:
            bot.answer_callback_query(call.id, "Заявка не найдена")
            return
        customer_id, name = row
        markup = types.InlineKeyboardMarkup(row_width=True)
        btn1 = types.InlineKeyboardButton("✅ Принять", callback_data=f"accept_{request_id}_{driver_id}")
        btn2 = types.InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_{request_id}_{driver_id}")
        markup.add(btn1, btn2)
        text = (
            f'Здравствуйте {name}, ваша заявка #{customer_id} была замечена.\n'
            f'Условия от водителя:\n'
            f'Цена: {data.get("цена")}\n'
            f'Время: {data.get("время")}\n'
            f'Комментарий: {data.get("комментарий")}'
        )
        bot.send_message(customer_id, text, reply_markup=markup)
        bot.answer_callback_query(call.id, "Ваш отклик отправлен заказчику")

    if call.data.startswith("delete_"):
        application_id = int(call.data.split("_")[1])
        cursor.execute("SELECT user_id FROM applications WHERE id=?", (application_id,))
        row = cursor.fetchone()
        if not row:
            bot.send_message(call.message.chat.id, "Заявка не найдена")
            return
        customer_id = row[0]
        if customer_id == call.from_user.id:
            bot.send_message(call.message.chat.id, "Вы не можете удалить свою собственную заявку таким образом")
            return
        cursor.execute("DELETE FROM applications WHERE id=?", (application_id,))
        conn.commit()
        bot.send_message(call.message.chat.id, f"Заявка #{application_id} успешно удалена")
        bot.send_message(customer_id, f'Ваша заявка #{application_id} была удалена из-за некорректностей данных')

    if call.data == "delete":
        application_id = int(call.data.split("_")[1])
        cursor.execute("SELECT user_id FROM applications WHERE id=?", (application_id,))
        row = cursor.fetchone()
        if not row:
            bot.send_message(call.message.chat.id, "Заявка не найдена")
            return
        cursor.execute("DELETE FROM applications WHERE id=?", (call.message.chat.id,))
        conn.commit()
        bot.send_message(call.message.chat.id, f"Заявка успешно удалена")

    if call.data.startswith("delete12_"):
        application_id = int(call.data.split("_")[1])
        cursor.execute("SELECT user_id FROM routes WHERE id=?", (application_id,))
        row = cursor.fetchone()
        if not row:
            bot.send_message(call.message.chat.id, "Заявка не найдена")
            return
        cursor.execute("DELETE FROM routes WHERE id=?", (application_id,))
        cursor.execute("DELETE FROM routes_2 WHERE id=?", (application_id,))
        conn.commit()
        bot.send_message(call.message.chat.id, f"Заявка №{application_id} успешно удалена ✅")

    if call.data.startswith("update_"):
        cursor.execute("SELECT id, text FROM applications ORDER BY RANDOM() LIMIT 1")
        row = cursor.fetchone()
        if not row:
            bot.answer_callback_query(call.message.chat.id, "Нет заявок для отображения")
            return
        new_id, new_text = row
        markup = types.InlineKeyboardMarkup(row_width=True)
        button1 = types.InlineKeyboardButton(text='📩 Откликнуться', callback_data=f'respond_{application_id}')
        button2 = types.InlineKeyboardButton(text='❌ Удалить заявку',
                                             callback_data=f'delete_{application_id}')
        button3 = types.InlineKeyboardButton(text='🏷️ Сохранить в избранное',
                                             callback_data=f'save_fav_{application_id}')
        button4 = types.InlineKeyboardButton(text='🔄 Обновить', callback_data=f'update_{application_id}')
        markup.add(button1, button2, button3, button4)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=new_text,
            reply_markup=markup
        )
        bot.answer_callback_query(call.message.chat.id, "Заявка обновлена")

    if call.data.startswith("update1_"):
        user_id = call.message.chat.id
        photo_type = call.data.split("_", 1)[1]
        if photo_type not in photo_types:
            bot.answer_callback_query(call.id, "⚠️ Ошибка: неизвестный тип фото")
            return
        user_state[user_id] = "update"
        user_progress[user_id] = photo_types.index(photo_type)

        bot.send_message(user_id, f"Отправьте новое фото для: {photo_type}")

    if call.data.startswith("accept_"):
        parts = call.data.split("_")
        action = parts[0]
        request_id = parts[1]
        driver_id = int(parts[2])
        requester_id = call.message.chat.id
        button = types.InlineKeyboardButton(text='✅ Подтвердить выполнение заказа',
                                            callback_data=f'yes_{request_id}_{driver_id}')
        markup = types.InlineKeyboardMarkup(row_width=True)
        markup.add(button)
        if action == "accept":
            bot.send_message(driver_id,
                             f"Заказчик подтвердил ваш отклик на заявку #{request_id}. Можете приступать к выполнению заявки",
                             reply_markup=markup)
            bot.send_message(requester_id,
                             f"Отлично! Ожидайте подтверждения от водителя о выполнении заявки #{request_id}")

    if call.data.startswith("decline_"):
        parts = call.data.split("_")
        action = parts[0]
        request_id = parts[1]
        driver_id = int(parts[2])
        requester_id = call.message.chat.id
        if action == "decline":
            bot.send_message(driver_id, f"Заказчик отклонил ваш отклик на заявку #{request_id}")
            bot.send_message(requester_id, f"Вы отклонили отклик водителя на заявку #{request_id}")
            cursor.execute("DELETE FROM applications WHERE user_id=?", (requester_id,))
            conn.commit()

    if call.data.startswith("yes_"):
        parts = call.data.split("_")
        request_id = parts[1]
        driver_id = int(parts[2])
        requester_id = call.message.chat.id
        target_id = call.from_user.id
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        button1 = types.KeyboardButton(text='⭐')
        button2 = types.KeyboardButton(text='⭐⭐')
        button3 = types.KeyboardButton(text='⭐⭐⭐')
        button4 = types.KeyboardButton(text='⭐⭐⭐⭐')
        button5 = types.KeyboardButton(text='⭐⭐⭐⭐⭐')
        markup.add(button1, button2, button3, button4, button5)
        msg = bot.send_message(requester_id,
                               f"Водитель подтвердил выполнение заказа #{request_id}. Оставьте оценку заказа #{request_id}",
                               reply_markup=markup)
        bot.register_next_step_handler(msg, save_rating, target_id)
        cursor.execute("DELETE FROM applications WHERE user_id=?", (requester_id,))
        conn.commit()
        bot.send_message(driver_id, f'Вы подтвердили заказ #{request_id}')

    if call.data == 'Меню':
        button = types.KeyboardButton(text='📩 Создать заявку')
        button2 = types.KeyboardButton(text='👤 Мой профиль')
        button3 = types.KeyboardButton(text='📌 Мои заявки')
        button4 = types.KeyboardButton(text='🚚 Поиск машины')
        button5 = types.KeyboardButton(text='📢 Заказать рекламу')
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(button, button2, button3, button4, button5)
        bot.send_message(call.message.chat.id, "Ознакомьтесь с данным меню", reply_markup=markup)

    if call.data == 'Меню_Водителя':
        button6 = types.KeyboardButton(text='🚚 Мои перевозки')
        button7 = types.KeyboardButton(text='👨‍🏭 Мой профиль')
        button8 = types.KeyboardButton(text='🚗 Создать маршрут перевозки')
        button9 = types.KeyboardButton(text='📦 Поиск груза')
        button10 = types.KeyboardButton(text='🔔 Подписки')
        button11 = types.KeyboardButton(text='🏷️ Избранное')
        markup2 = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup2.add(button6, button7, button8, button9, button10, button11)
        bot.send_message(call.message.chat.id, "Ознакомьтесь с данным меню", reply_markup=markup2)


def save_rating(message, target_id):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, save_rating)
        return
    stars = message.text.strip()
    rating = len(stars)
    cursor.execute("SELECT name FROM user WHERE user_id=?", (message.from_user.id,))
    user = cursor.fetchone()
    username = user[0] if user else "Без имени"
    user_id = message.from_user.id
    cursor.execute("INSERT INTO feedback (user_id, FIO, target_id, rating) VALUES (?, ?, ?, ?)",
                   (user_id, username, target_id, rating))
    conn.commit()
    markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, f"Вы поставили {rating}⭐! Напишите отзыв", reply_markup=markup)
    bot.register_next_step_handler(message, save_comment, user_id, target_id)


def save_comment(message, user_id, target_id):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, save_comment)
        return
    text = message.text
    cursor.execute("SELECT id FROM feedback WHERE user_id=? AND target_id=? AND text IS NULL ORDER BY id DESC LIMIT 1",
                   (user_id, target_id))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE feedback SET text=? WHERE id=?", (text, row[0]))
        conn.commit()
        bot.send_message(message.chat.id, "Спасибо за отзыв!")
    else:
        bot.send_message(message.chat.id, "Ошибка: отзыв не найден")


def FIO(message):
    user_FIO = message.text.strip()
    if contains_bad_words(user_FIO):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, FIO)
        return
    if not all(part.isalpha() for part in user_FIO.split()):
        msg = bot.send_message(message.chat.id, "ФИО должно содержать только буквы")
        bot.register_next_step_handler(msg, FIO)
        return
    cursor.execute("INSERT OR REPLACE INTO drivers (user_id, FIO) VALUES (?, ?)", (message.chat.id, user_FIO))
    conn.commit()
    user_data[message.chat.id] = {'name': user_FIO}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("📱 Отправить контактные данные", request_contact=True)
    markup.add(button)
    user_state[message.chat.id] = "registration"
    bot.send_message(message.chat.id, f'✅ Приятно познакомиться, {user_FIO}! Теперь отправьте контактные данные 📞', reply_markup=markup)


def response1(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, response1)
        return
    sub, expire, active = check_subscription(message.from_user.id)
    markup = generate_time_keyboard(sub)
    user_data[message.chat.id]['цена'] = message.text
    bot.send_message(message.chat.id, '🕛 Укажите время прибытия', reply_markup=markup)


def response2(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, response2)
        return
    user_data[message.chat.id]['время'] = message.text
    msg = bot.send_message(message.chat.id, '💬 Укажите комментарий (необязательно)')
    bot.register_next_step_handler(msg, response3)


def response3(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, response3)
        return
    driver_id = message.chat.id
    user_data[driver_id]['комментарий'] = message.text
    application_id = user_data[driver_id]['application_id']
    markup = types.InlineKeyboardMarkup(row_width=True)
    button = types.InlineKeyboardButton(text='✔️ Подтвердить', callback_data=f"confirm_{application_id}_{driver_id}")
    markup.add(button)
    bot.send_message(message.chat.id, 'Подтвердите отклик', reply_markup=markup)


def route1(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, route1)
        return
    cities = [
        'Надым', 'Ноябрьск', 'Тарко-Сале', 'Пангоды',
        'Лимбяяха', 'Салехард', 'Коротчаево',
        'Новый Уренгой', 'Губкинский'
    ]
    user_data[message.chat.id]['откуда1'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
    buttons = [types.KeyboardButton(text=city) for city in cities]
    buttons1 = [types.KeyboardButton(text='🏙️ Другой город')]
    markup.add(*buttons, *buttons1)
    markup.add(types.KeyboardButton(text='⬅️ Назад'))
    msg = bot.send_message(message.chat.id, '📍 Куда', reply_markup=markup)
    bot.register_next_step_handler(msg, route2_handler)


def route1_handler(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, route1_handler)
        return
    cities = [
        'Надым', 'Ноябрьск', 'Тарко-Сале', 'Пангоды',
        'Лимбяяха', 'Салехард', 'Коротчаево',
        'Новый Уренгой', 'Губкинский'
    ]
    if message.text in cities:
        route1(message)
    elif message.text == '🏙️ Другой город':
        msg = bot.send_message(message.chat.id, '🏙️ Укажите название конкретного города')
        bot.register_next_step_handler(msg, route1)
    elif message.text == '⬅️ Назад':
        button6 = types.KeyboardButton(text='🚚 Мои перевозки')
        button7 = types.KeyboardButton(text='👨‍🏭 Мой профиль')
        button8 = types.KeyboardButton(text='🚗 Создать маршрут перевозки')
        button9 = types.KeyboardButton(text='📦 Поиск груза')
        button10 = types.KeyboardButton(text='🔔 Подписки')
        button11 = types.KeyboardButton(text='🏷️ Избранное')
        markup2 = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup2.add(button6, button7, button8, button9, button10, button11)
        bot.send_message(call.message.chat.id, "Ознакомьтесь с данным меню", reply_markup=markup2)
    else:
        msg = bot.send_message(message.chat.id, "⚠️ Выберите город из списка или нажмите 'Другой город'")
        bot.register_next_step_handler(msg, route1_handler)


def route2_handler(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, route2_handler)
        return
    cities = [
        'Надым', 'Ноябрьск', 'Тарко-Сале', 'Пангоды',
        'Лимбяяха', 'Салехард', 'Коротчаево',
        'Новый Уренгой', 'Губкинский'
    ]
    if message.text in cities:
        route1_1(message)
    elif message.text == '🏙️ Другой город':
        msg = bot.send_message(message.chat.id, '🏙️ Укажите название конкретного города')
        bot.register_next_step_handler(msg, route2)
    else:
        msg = bot.send_message(message.chat.id, "⚠️ Выберите город из списка или нажмите 'Другой город'")
        bot.register_next_step_handler(msg, route2_handler)


def route1_1(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, route1_1)
        return
    user_data[message.chat.id]['куда1'] = message.text
    msg = bot.send_message(message.chat.id, '🏢 2–10 попутных городов')
    bot.register_next_step_handler(msg, route2)


def route2(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, route2)
        return
    user_data[message.chat.id]['город1'] = message.text
    now = datetime.now()
    markup = create_calendar1(now.year, now.month, chat_id=message.chat.id)
    bot.send_message(message.chat.id, '📅 Даты действия (минимум 2), затем нажмите «Дальше»', reply_markup=markup)


def route3(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, route3)
        return
    msg = bot.send_message(message.chat.id, '📦 Допустимые габариты (Д×Ш×В)')
    bot.register_next_step_handler(msg, route3_1)


def route3_1(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, route3)
        return
    user_data[message.chat.id]['габариты1'] = message.text
    msg = bot.send_message(message.chat.id, '⚖️ Вес')
    bot.register_next_step_handler(msg, route4)


def route4(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, route4)
        return
    user_data[message.chat.id]['вес1'] = message.text
    msg = bot.send_message(message.chat.id, '🔄 Поддерживаемые типы погрузки')
    bot.register_next_step_handler(msg, route5)


def route5(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, route5)
        return
    user_data[message.chat.id]['погрузки1'] = message.text
    msg = bot.send_message(message.chat.id, '🚛 Ограничения по ТС')
    bot.register_next_step_handler(msg, route6)


def route6(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, route6)
        return
    user_data[message.chat.id]['ограничения1'] = message.text
    data = user_data[message.chat.id]
    user_id = message.chat.id
    cursor.execute("""
                SELECT d.FIO, d.number, AVG(f.rating)
                FROM drivers d
                LEFT JOIN feedback f ON d.user_id = f.user_id
                WHERE d.user_id=?
            """, (user_id,))
    row = cursor.fetchone()
    FIO, number, avg = row
    text = (f'🚦 Откуда: {data["откуда1"]} ➝ Куда: {data["куда1"]}\n'
            f'🏢 Города: {data["город1"]}\n'
            f'📅 Даты действия: {data["дата1"]}\n'
            f'📦 Габариты (Д×Ш×В): {data["габариты1"]}\n'
            f'⚖️ Вес: {data["вес1"]}\n'
            f'🔄 Типы погрузки: {data["погрузки1"]}\n'
            f'🚛 Ограничения по ТС: {data["ограничения1"]}\n\n'
            f'👨‍✈️ Карточка водителя:\n'
            f'👤 ФИО: {FIO}\n'
            f'⭐ Рейтинг: {avg}\n'
            f'✅ Статус KYC: одобрен')
    text1 = (f'🚦 Откуда: {data["откуда1"]} ➝ Куда: {data["куда1"]}\n'
             f'🎯 Куда: {data["куда1"]}\n'
             f'🏢 Города: {data["город1"]}\n\n'
             f'👨‍✈️ Карточка водителя:\n'
             f'👤 ФИО: {FIO}\n'
             f'⭐ Рейтинг: {avg}\n'
             f'✅ Статус KYC: одобрен')
    cursor.execute("INSERT INTO routes_2 (user_id, text, status) VALUES (?, ?, ?)", (message.chat.id, text1, "новая"))
    cursor.execute("INSERT INTO routes (user_id, text, status) VALUES (?, ?, ?)", (message.chat.id, text, "новая"))
    conn.commit()
    button = types.InlineKeyboardButton(text='↩️ Вернуться в главное меню', callback_data='Меню_Водителя')
    markup1 = types.InlineKeyboardMarkup(row_width=True)
    markup1.add(button)
    bot.send_message(message.chat.id, '✅ Отлично! Вы зарегистрировали маршрут!', reply_markup=markup1)


def application2(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, application2)
        return
    cities = [
        'Надым', 'Ноябрьск', 'Тарко-Сале', 'Пангоды',
        'Лимбяяха', 'Салехард', 'Коротчаево',
        'Новый Уренгой', 'Губкинский'
    ]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
    buttons = [types.KeyboardButton(text=city) for city in cities]
    buttons1 = [types.KeyboardButton(text='🏙️ Другой город')]
    markup.add(*buttons, *buttons1)
    markup.add(types.KeyboardButton(text='⬅️ Назад'))
    msg = bot.send_message(message.chat.id, '📍 Откуда', reply_markup=markup)
    bot.register_next_step_handler(msg, application2_handler)


def application2_handler(message):
    cities = [
        'Надым', 'Ноябрьск', 'Тарко-Сале', 'Пангоды',
        'Лимбяяха', 'Салехард', 'Коротчаево',
        'Новый Уренгой', 'Губкинский'
    ]
    if message.text in cities:
        application2_1(message)
    elif message.text == '🏙️ Другой город':
        msg = bot.send_message(message.chat.id, '🏙️ Укажите название конкретного города')
        bot.register_next_step_handler(msg, application2_1)
    elif message.text == '⬅️ Назад':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(
            types.KeyboardButton(text='📩 Создать заявку'),
            types.KeyboardButton(text='👤 Мой профиль'),
            types.KeyboardButton(text='📌 Мои заявки'),
            types.KeyboardButton(text='🚚 Поиск машины'),
            types.KeyboardButton(text='📢 Заказать рекламу')
        )
        bot.send_message(message.chat.id, 'Ознакомьтесь с меню', reply_markup=markup)
    else:
        msg = bot.send_message(message.chat.id, "⚠️ Выберите город из списка или нажмите 'Другой город'")
        bot.register_next_step_handler(msg, application2_handler)


def application2_1(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(
            message.chat.id,
            "🚫 Недопустимая лексика! Введите корректный текст"
        )
        bot.register_next_step_handler(msg, application2_1)
        return
    user_data.setdefault(message.chat.id, {})
    user_data[message.chat.id]['город1'] = message.text
    msg = bot.send_message(message.chat.id, '🏙️ Отлично! Теперь укажите улицу')
    bot.register_next_step_handler(msg, application2_12)


def application2_12(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, application2_12)
        return

    cities = [
        'Надым', 'Ноябрьск', 'Тарко-Сале', 'Пангоды',
        'Лимбяяха', 'Салехард', 'Коротчаево',
        'Новый Уренгой', 'Губкинский'
    ]

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
    buttons = [types.KeyboardButton(text=city) for city in cities]
    buttons1 = [types.KeyboardButton(text='🏙️ Другой город')]
    markup.add(*buttons, *buttons1)
    markup.add(types.KeyboardButton(text='⬅️ Назад'))
    user_data[message.chat.id]['улица1'] = message.text
    msg = bot.send_message(message.chat.id, '📍 Куда', reply_markup=markup)
    bot.register_next_step_handler(msg, application2_handler1)


def application2_handler1(message):
    cities = [
        'Надым', 'Ноябрьск', 'Тарко-Сале', 'Пангоды',
        'Лимбяяха', 'Салехард', 'Коротчаево',
        'Новый Уренгой', 'Губкинский'
    ]
    if message.text in cities:
        application2_2(message)
    elif message.text == '🏙️ Другой город':
        msg = bot.send_message(message.chat.id, 'Укажите название конкретного города')
        bot.register_next_step_handler(msg, application2_2)
    elif message.text == '⬅️ Назад':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton(text='📩 Создать заявку'),
            types.KeyboardButton(text='👤 Мой профиль'),
            types.KeyboardButton(text='📌 Мои заявки'),
            types.KeyboardButton(text='🚚 Поиск машины'),
            types.KeyboardButton(text='📢 Заказать рекламу')
        )
        bot.send_message(message.chat.id, 'Ознакомьтесь с меню', reply_markup=markup)
    else:
        msg = bot.send_message(message.chat.id, "⚠️ Выберите город из списка или нажмите 'Другой город'")
        bot.register_next_step_handler(msg, application2_handler1)


def application2_2(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, application2_2)
        return
    user_data[message.chat.id]['город2'] = message.text
    msg = bot.send_message(message.chat.id, '🏙️ Отлично! Теперь укажите улицу')
    bot.register_next_step_handler(msg, application3)


def application3(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, application3)
        return
    user_data[message.chat.id]['улица2'] = message.text
    msg = bot.send_message(message.chat.id, '🚪 Тип подъезда (свободный, ограниченный, только задним ходом)')
    bot.register_next_step_handler(msg, application4)


def application4(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, application4)
        return
    user_data[message.chat.id]['подъезд'] = message.text
    msg = bot.send_message(message.chat.id, '📦 Разгрузочно-погрузочная зона (рампа, площадка для разворота)')
    bot.register_next_step_handler(msg, application5)


def application5(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, application5)
        return
    user_data[message.chat.id]['зона'] = message.text
    msg = bot.send_message(message.chat.id, '🚛 Ограничения по ТС (высота, ширина, масса, без ограничений)')
    bot.register_next_step_handler(msg, application6)


def application6(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, application6)
        return
    user_data[message.chat.id]['ТС'] = message.text
    msg = bot.send_message(message.chat.id, '🚧 Ограничения на въезд (например, запрет фур)')
    bot.register_next_step_handler(msg, application7)


def application7(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, application7)
        return
    user_data[message.chat.id]['въезд'] = message.text
    msg = bot.send_message(message.chat.id, '📦 Вес (кг)')
    bot.register_next_step_handler(msg, application7_1)


def application7_1(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, application7_1)
        return
    user_data[message.chat.id]['вес'] = message.text
    msg = bot.send_message(message.chat.id, '📐 Габариты (Д×Ш×В)')
    bot.register_next_step_handler(msg, application7_2)


def application7_2(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, application7_2)
        return
    user_data[message.chat.id]['габариты'] = message.text
    msg = bot.send_message(message.chat.id, '🎯 Количество мест')
    bot.register_next_step_handler(msg, application8)


def application8(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, application8)
        return
    user_data[message.chat.id]['мест'] = message.text
    msg = bot.send_message(message.chat.id, '⚠️ Особые условия (хрупкий, температурный режим, опасный)')
    bot.register_next_step_handler(msg, application9)


def application9(message):
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, application9)
        return
    user_data[message.chat.id]['условия'] = message.text
    msg = bot.send_message(message.chat.id, '📝 Комментарий')
    bot.register_next_step_handler(msg, application10)


def application10(message):
    random_user = get_random_premium_user()
    if contains_bad_words(message.text):
        msg = bot.send_message(message.chat.id, "🚫 Недопустимая лексика! Введите корректный текст")
        bot.register_next_step_handler(msg, application10)
        return
    user_data[message.chat.id]['комментарий'] = message.text
    data = user_data[message.chat.id]
    summary = (f'📋 Заявка на перевозку\n\n'
               f'🏙️ Маршрут: {data["город1"]} {data["улица1"]} → {data["город2"]} {data["улица2"]}\n\n'
               f'🚪 Тип подъезда: {data["подъезд"]}\n'
               f'📦 Зона разгрузки/погрузки: {data["зона"]}\n'
               f'🚛 Ограничения по ТС: {data["ТС"]}\n'
               f'🚧 Ограничения на въезд: {data["въезд"]}\n\n'
               f'⚖️ Вес (кг): {data["вес"]}\n'
               f'📐 Габариты (Д×Ш×В): {data["габариты"]}\n'
               f'🎯 Количество мест: {data["мест"]}\n\n'
               f'⏳ Срок актуальности: {data["срок"]}\n'
               f'⚠️ Особые условия: {data["условия"]}\n'
               f'📝 Комментарий: {data["комментарий"]}')
    cursor.execute("INSERT INTO applications (user_id, text, status) VALUES (?, ?, ?)",
                   (message.chat.id, summary, "новая"))
    conn.commit()
    application_id = cursor.lastrowid
    markup_back = types.InlineKeyboardMarkup()
    markup_back.add(types.InlineKeyboardButton("↩️ Вернуться в главное меню", callback_data="Меню"))
    bot.send_message(message.chat.id, f'✅ Заявка #{application_id} создана', reply_markup=markup_back)
    if random_user:
        bot.send_message(random_user, f"📢 Вам пришла заявка #{application_id}")


@bot.message_handler(content_types=['photo', 'contact'])
def photo(message):
    user_id = message.chat.id

    if user_state.get(user_id) == "registration1":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        button = types.KeyboardButton(text='⬅️ Пропустить')
        markup.add(button)
        phone = message.contact.phone_number
        first_name = message.contact.first_name
        cursor.execute("INSERT INTO user (user_id, name, number) VALUES (?, ?, ?)", (message.chat.id, first_name, phone))
        conn.commit()
        msg = bot.send_message(message.chat.id, f"Спасибо, {first_name}! ✅\nТеперь отправьте своё фото 📷", reply_markup=markup)
        bot.register_next_step_handler(msg, get_photo)

    state = user_state.get(message.chat.id)
    cursor.execute("SELECT status FROM drivers WHERE user_id=?", (user_id,))
    row = cursor.fetchone()

    if user_state.get(user_id) == "registration":
        contact = message.contact
        phone = contact.phone_number
        cursor.execute("UPDATE drivers SET number=? WHERE user_id=?", (phone, message.chat.id))
        conn.commit()
        user_state[message.chat.id] = "register"
        user_progress[message.chat.id] = 0
        bot.send_message(message.chat.id, f'Ваш номер телефона: {phone}. Теперь отправьте {photo_types[0]}:')

    if state == "register":
        if row is None:
            cursor.execute("INSERT INTO drivers (user_id, FIO, number, status) VALUES (?, ?, ?, ?, ?)", (user_id, user_FIO, phone, "на проверке"))
            conn.commit()
        if user_id not in user_progress:
            user_progress[user_id] = 0
        step = user_progress.get(user_id, 0)
        if step >= len(photo_types):
            bot.send_message(user_id, "Вы уже отправили все фото ✅")
            return
        photo_type = photo_types[step]
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_path = f"E:/user_photos/{user_id}_{photo_type}.jpg"
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        cursor.execute(
            "INSERT INTO driver_photos (user_id, photo_type, file_path) VALUES (?, ?, ?)",
            (user_id, photo_type, file_path)
        )
        conn.commit()
        bot.send_message(user_id, f"Фото «{photo_type}» загружено ✅")
        user_progress[user_id] += 1
        if user_progress[user_id] < len(photo_types):
            next_type = photo_types[user_progress[user_id]]
            bot.send_message(user_id, f"Теперь отправьте {next_type}:")
        else:
            bot.send_message(user_id, "Все фото загружены ✅ Ваша заявка отправлена администратору.")
            bot.send_message(admin_id, f"Новая заявка от пользователя {user_id}")
            del user_progress[user_id]

    if state == "buy":
        bot.send_message(message.chat.id, 'Фото оплаты сохранено. Ожидайте подтверждения')

    if state == "update":
        step = user_progress[user_id]
        photo_type = photo_types[step]
        cursor.execute("SELECT file_path FROM driver_photos WHERE user_id=? AND photo_type=?", (user_id, photo_type))
        old_photo = cursor.fetchone()
        if old_photo:
            old_path = old_photo[0]
            if old_path and os.path.exists(old_path):
                os.remove(old_path)
            cursor.execute("DELETE FROM driver_photos WHERE user_id=? AND photo_type=?", (user_id, photo_type))
            conn.commit()
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_path = f"E:/user_photos/{user_id}_{photo_type}.jpg"
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        cursor.execute(
            "INSERT INTO driver_photos (user_id, photo_type, file_path) VALUES (?, ?, ?)",
            (user_id, photo_type, file_path)
        )
        conn.commit()
        markup = inline_update_button(photo_type)
        bot.send_photo(
            user_id,
            message.photo[-1].file_id,
            caption=f"{photo_type} (обновлено)",
            reply_markup=markup
        )
        user_state[user_id] = None


def get_photo(message):
    if message.content_type == 'photo':
        button = types.KeyboardButton(text='📩 Создать заявку')
        button2 = types.KeyboardButton(text='👤 Мой профиль')
        button3 = types.KeyboardButton(text='📌 Мои заявки')
        button4 = types.KeyboardButton(text='🚚 Поиск машины')
        button5 = types.KeyboardButton(text='📢 Заказать рекламу')
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(button, button2, button3, button4, button5)
        bot.send_message(message.chat.id, "Регистрация завершена! Добро пожаловать!", reply_markup=markup)

    if message.text == '⬅️ Пропустить':
        button = types.KeyboardButton(text='📩 Создать заявку')
        button2 = types.KeyboardButton(text='👤 Мой профиль')
        button3 = types.KeyboardButton(text='📌 Мои заявки')
        button4 = types.KeyboardButton(text='🚚 Поиск машины')
        button5 = types.KeyboardButton(text='📢 Заказать рекламу')
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(button, button2, button3, button4, button5)
        bot.send_message(message.chat.id, 'Регистрация завершена! Добро пожаловать в меню!', reply_markup=markup)

bot.polling(non_stop=True)
