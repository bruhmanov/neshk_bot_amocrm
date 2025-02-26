import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
import config
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="bot.log",
    encoding="utf-8"
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(config.TELEGRAM_BOT_TOKEN)

def authorize_google_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(config.GOOGLE_SHEETS_CREDENTIALS, scope)
    client = gspread.authorize(creds)
    return client

def add_data_to_google_sheets(name, phone, age, username):
    try:
        client = authorize_google_sheets()
        sheet = client.open(config.GOOGLE_SHEETS_NAME).worksheet("Лист1")

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        age_with_years = f"{age} лет"

        if username.startswith("@"):
            username = username[1:]

        if phone.startswith("+"):
            phone = phone[1:]

        response = sheet.append_row([current_time, name, username, phone, age_with_years])

        logger.info(f"Ответ от Google Sheets API: {response}")

        if response:
            logger.info(f"Данные успешно добавлены в Google Sheets: {current_time}, {name}, {username}, {phone}, {age_with_years}")
            return True
        else:
            logger.error("Ошибка: Пустой ответ от Google Sheets API")
            return False

    except gspread.exceptions.APIError as e:
        logger.error(f"Ошибка при добавлении данных в Google Sheets: {e}")
        return False
    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
        return False

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

def get_phone(message, age):
    phone_number = None

    if message.contact:
        phone_number = message.contact.phone_number
    elif message.text:
        phone_number = message.text

    if not phone_number:
        bot.send_message(
            message.chat.id,
            "Пожалуйста, укажите номер телефона.",
            reply_markup=types.ReplyKeyboardRemove(selective=False)
        )
        bot.register_next_step_handler(message, get_phone, age)
        return

    username = message.from_user.username
    if username:
        username = username
    else:
        username = "Не указан"

    if add_data_to_google_sheets(message.from_user.first_name, phone_number, age, username):
        bot.send_message(
            message.chat.id,
            "Спасибо!\n\n"
            "Скоро наш администратор свяжется с вами и согласует дату и время мастер-класса!\n\n"
            "Подпишитесь на наш канал в Telegram, чтобы быть в курсе акций и новых предложений: https://t.me/neshkolakidskzn",
            reply_markup=types.ReplyKeyboardRemove(selective=False)
        )
    else:
        bot.send_message(
            message.chat.id,
            "Произошла ошибка при обработке вашей заявки. Пожалуйста, попробуйте позже.",
            reply_markup=types.ReplyKeyboardRemove(selective=False)
        )

if __name__ == "__main__":
    logger.info("Бот запущен")
    bot.infinity_polling()