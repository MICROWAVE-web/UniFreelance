"""import logging
import traceback

from celery import Celery
from celery.utils.log import get_task_logger
from decouple import config
from telebot import TeleBot
from telegram.error import TelegramError

# Инициализация Celery
app = Celery('tasks', broker='redis://redis:6379/1')
app.conf.broker_connection_retry_on_startup = True
app.autodiscover_tasks()

# Бот
bot = TeleBot(token=config('API_TOKEN'))

# Логгирвание
logger = get_task_logger(__name__)
handler = logging.StreamHandler()  # Используем вывод в консоль
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def send_message_sync(user_id, text):
    try:
        bot.send_message(chat_id=user_id, text=text)
    except TelegramError:
        traceback.print_exc()


def wakeup_admins(message):
    for admin in config('ADMINS').split(','):
        send_message_sync(admin, message)


@app.task
def notify_users(order_object):


    wakeup_admins(f"Order details: {order_object}")

    '''async def _snd_prompt(usr_id):
        await bot.send_message(usr_id)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_snd_prompt(user_id))
    except RuntimeError:
        traceback.print_exc()
        wakeup_admins(f"RuntimeError. Перезапускаю worker")
        os.system("sudo systemctl restart kovanoff_vpn_worker")
    finally:
        loop.close()'''

    return True
"""