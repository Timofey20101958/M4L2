from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logic import *
import schedule
import threading
import time
from config import *
from datetime import timedelta

bot = TeleBot(API_TOKEN)

last_sent_prizes = []  
MAX_LAST_PRIZES = 10

def gen_markup(id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton("Получить!", callback_data=id))
    return markup

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):

    prize_id = call.data
    user_id = call.message.chat.id

    img = manager.get_prize_img(prize_id)
    with open(f'img/{img}', 'rb') as photo:
        bot.send_photo(user_id, photo)


def send_message():
    prize_id, img = manager.get_random_prize()[:2]
    manager.mark_prize_used(prize_id)
    hide_img(img)
    
    last_sent_prizes.append({
        'prize_id': prize_id,
        'img_name': img,
        'timestamp': time.time()
    })
    if len(last_sent_prizes) > MAX_LAST_PRIZES:
        last_sent_prizes.pop(0)
    
    for user in manager.get_users():
        with open(f'hidden_img/{img}', 'rb') as photo:
            bot.send_photo(user, photo, reply_markup=gen_markup(id=prize_id))

def shedule_thread():
    schedule.every().minute.do(send_message) # Здесь ты можешь задать периодичность отправки картинок
    while True:
        schedule.run_pending()
        time.sleep(15)

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    if user_id in manager.get_users():
        bot.reply_to(message, "Ты уже зарегестрирован!")
    else:
        manager.add_user(user_id, message.from_user.username)
        bot.reply_to(message, """Привет! Добро пожаловать! 
Тебя успешно зарегистрировали!
Каждый час тебе будут приходить новые картинки и у тебя будет шанс их получить!
Для этого нужно быстрее всех нажать на кнопку 'Получить!'

Только три первых пользователя получат картинку!)""")
        
@bot.message_handler(commands=['rating'])
def handle_rating(message):
    res = get_rating() 
    res = [f'| @{x[0]:<11} | {x[1]:<11}|\n{"_"*26}' for x in res]
    res = '\n'.join(res)
    res = f'|USER_NAME    |COUNT_PRIZE|\n{"_"*26}\n' + res
    bot.send_message(message.chat.id, res)
    
@bot.message_handler(commands=['retry'])
def handle_retry(message):
    user_id = message.chat.id
    now = time.time()
    
    available_prizes = [
        p for p in last_sent_prizes
        if now - p['timestamp'] <= 3600  # Призы за последний час
    ]
    
    if not available_prizes:
        bot.send_message(user_id, "Нет доступных призов для повторной отправки.")
        return
    
    markup = InlineKeyboardMarkup()
    for prize in available_prizes:
        markup.add(InlineKeyboardButton(
            f"Приз от {time.strftime('%H:%M', time.localtime(prize['timestamp']))}",
            callback_data=f"retry_{prize['prize_id']}"
        ))
    bot.send_message(user_id, "Выберите приз для повторной отправки:", reply_markup=markup)   

@bot.callback_query_handler(func=lambda call: call.data.startswith('retry_'))
def retry_callback(call):
    prize_id = call.data.replace('retry_', '')
    user_id = call.message.chat.id
    
    # Ищем изображение по ID приза
    img = manager.get_prize_img(prize_id)
    if img:
        try:
            with open(f'img/{img}', 'rb') as photo:
                bot.send_photo(user_id, photo, caption="Повторная отправка картинки!")
        except FileNotFoundError:
            bot.send_message(user_id, "Изображение не найдено.")
    else:
        bot.send_message(user_id, "Приз не найден.")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):

    prize_id = call.data
    user_id = call.message.chat.id

    if get_winners_count() < 3:
        res = message.add_winner(user_id,prize_id)
        if res:
            img = get_prize_img(prize_id)
            with open(f'img/{img}', 'rb') as photo:
                bot.send_photo(user_id, photo, caption="Поздравляем! Ты получил картинку!")
        else:
            bot.send_message(user_id, 'Ты уже получил картинку!')
    else:
        bot.send_message(user_id, "К сожалению, ты не успел получить картинку! Попробуй в следующий раз!)")

def polling_thread():
    bot.polling(none_stop=True)

if __name__ == '__main__':
    manager = DatabaseManager(DATABASE)
    manager.create_tables()

    polling_thread = threading.Thread(target=polling_thread)
    polling_shedule  = threading.Thread(target=shedule_thread)

    polling_thread.start()
    polling_shedule.start()
  
