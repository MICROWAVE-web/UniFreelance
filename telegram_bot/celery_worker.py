import traceback

from celery import Celery
from decouple import config
from telebot import TeleBot
from telegram.error import TelegramError

from telegram_bot.db_engine import collect_filters, get_telegram_id_by_user_id
from telegram_bot.keyboards import get_new_task_notification, def_new_task_notification
from telegram_bot.utilities import check_the_filter_match

# Инициализация Celery
app = Celery('tasks', broker='redis://redis:6379/1')
app.conf.broker_connection_retry_on_startup = True
app.autodiscover_tasks()

# Бот
bot = TeleBot(token=config('API_TOKEN'))


def send_message_sync(user_id, text):
    """Отправка сообщения синхронно через python-telegram-bot."""
    try:
        sent_message = bot.send_message(chat_id=user_id, text=text, parse_mode="html")
        return sent_message
    except TelegramError:
        traceback.print_exc()


def wakeup_admins(message):
    for admin in config('ADMINS').split(','):
        send_message_sync(admin, message)


@app.task
def notify_users(order_dict):
    """
    :param order_dict:
    """
    filters_data = collect_filters()
    for platform, platform_dict in filters_data.items():
        if platform != order_dict["platform"]:
            continue
        for query, user_ids in platform_dict.items():
            for user_id in user_ids:
                telegram_id = get_telegram_id_by_user_id(user_id)
                if check_the_filter_match(telegram_id, order_dict, query):
                    sent_message = send_message_sync(telegram_id, get_new_task_notification(order_dict))
                    if sent_message:
                        bot.edit_message_reply_markup(chat_id=telegram_id, message_id=sent_message.message_id,
                                                      reply_markup=def_new_task_notification(sent_message.message_id,
                                                                                             order_dict["direct_url"],
                                                                                          order_dict["order_db_id"]))
    return True
