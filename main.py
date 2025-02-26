from dotenv import load_dotenv
import os
import telebot
from telebot import types
import requests
import json
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="bot.log",
    encoding="utf-8"
)
logger = logging.getLogger(__name__)

load_dotenv()

AMOCRM_DOMAIN = os.getenv('AMOCRM_DOMAIN')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'https://ya.ru')

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def load_tokens():
    try:
        with open('tokens.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return None

def save_tokens(tokens):
    with open('tokens.json', 'w') as file:
        json.dump(tokens, file)

def refresh_tokens():
    tokens = load_tokens()
    if not tokens:
        raise Exception("Токены не найдены. Необходима повторная авторизация.")

    url = f'https://{AMOCRM_DOMAIN}/oauth2/access_token'
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': tokens['refresh_token'],
        'redirect_uri': REDIRECT_URI
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        new_tokens = response.json()
        new_tokens['expires_in'] = time.time() + new_tokens['expires_in']
        save_tokens(new_tokens)
        logger.info("Токены успешно обновлены!")
        return new_tokens
    else:
        logger.error(f"Ошибка при обновлении токенов: {response.status_code}, {response.text}")
        raise Exception("Ошибка при обновлении токенов.")

def get_access_token():
    tokens = load_tokens()
    if not tokens:
        raise Exception("Токены не найдены. Необходима повторная авторизация.")

    if time.time() >= tokens['expires_in']:
        logger.info("Токен истек. Обновление...")
        tokens = refresh_tokens()

    return tokens['access_token']

def add_lead_to_amo_crm(name, phone, age, username):
    access_token = get_access_token()

    url = f'https://{AMOCRM_DOMAIN}/api/v4/leads'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    data = [
        {
            "name": f"Лид от {name}",
            "custom_fields_values": [
                {
                    "field_id": 931725,
                    "values": [{"value": phone}]
                },
                {
                    "field_id": 931775,
                    "values": [{"value": age}]
                },
                {
                    "field_id": 932703,
                    "values": [{"value": username}]
                }
            ]
        }
    ]
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        logger.info(f"Лид успешно создан! ID лида: {response.json()['_embedded']['leads'][0]['id']}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при создании лида: {e}")
        return False

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def main(message):
    file_id = 'AgACAgIAAxkDAAMiZ7hmP7jMxCSWyPuPNUru_PXsmWkAAtHrMRtJ8cBJFJx_lD_HfxABAAMCAAN5AAM2BA'
    bot.send_photo(message.chat.id, file_id)

    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('5-8 лет', callback_data='5-8')
    btn2 = types.InlineKeyboardButton('9-11 лет', callback_data='9-11')
    btn3 = types.InlineKeyboardButton('12-14 лет', callback_data='12-14')
    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)

    response = (
        "<b>В Казани на этой неделе пройдет бесплатный мастер-класс для детей 5-14 лет!</b>\n\n"
        "Ваш ребенок:\n\n"
        "⭐️ Постучит на барабанах, сыграет на гитаре и фортепиано свои первые композиции\n\n"
        "⭐️ Попробует себя в вокале, споет любимую песню под руководством опытного педагога\n\n"
        "✅ Текущий уровень не важен. Для детей возраста 5-14 лет\n\n"
        "✅ Продолжительность – 1,5 часа. Ничего брать с собой не нужно\n\n"
        "Чтобы записаться на бесплатный мастер-класс, укажите возраст вашего ребенка 👇"
    )
    bot.send_message(message.chat.id, response, parse_mode='html', reply_markup=markup)

# Обработчик выбора возраста
@bot.callback_query_handler(func=lambda call: True)
def handle_age(call):
    age = call.data
    bot.answer_callback_query(call.id, f"Вы выбрали: {age}")

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    btn_phone = types.KeyboardButton(text="Отправить номер телефона", request_contact=True)
    markup.add(btn_phone)

    bot.send_message(
        call.message.chat.id,
        "Спасибо! Остался последний шаг😊\n\n"
        "Укажите ваш номер телефона.\n"
        "Наш администратор отправит вам расписание мастер-классов на ближайшую неделю и согласует точное время 🤗",
        reply_markup=markup
    )

    bot.register_next_step_handler(call.message, get_phone, age)

# Обработчик отправки номера телефона
@bot.message_handler(content_types=['contact'])
def get_phone(message, age):
    phone_number = message.contact.phone_number

    # Получаем ник пользователя
    username = message.from_user.username
    if username:
        username = f"@{username}"
    else:
        username = "Не указан"

    markup = types.ReplyKeyboardRemove(selective=False)

    if add_lead_to_amo_crm(message.from_user.first_name, phone_number, age, username):
        bot.send_message(
            message.chat.id,
            "Спасибо!\n\n"
            "Скоро наш администратор свяжется с вами и согласует дату и время мастер-класса!\n\n"
            "Подпишитесь на наш канал в Telegram, чтобы быть в курсе акций и новых предложений: https://t.me/neshkolakidskzn",
            reply_markup=markup
        )
    else:
        bot.send_message(
            message.chat.id,
            "Произошла ошибка при обработке вашей заявки. Пожалуйста, попробуйте позже.",
            reply_markup=markup
        )

if __name__ == "__main__":
    logger.info("Бот запущен")
    bot.infinity_polling()