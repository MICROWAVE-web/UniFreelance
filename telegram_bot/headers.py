# Токер телеграмм
import logging

import pytz
import redis
from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from celery.utils.log import get_task_logger
from decouple import config

# Логгирвание
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])
logger = get_task_logger(__name__)
handler = logging.StreamHandler()  # Используем вывод в консоль
logger.addHandler(handler)

API_TOKEN = config('API_TOKEN')

# Id администраторов
ADMINS = config('ADMINS').split(',')

# ЮКасса
TEST_PAYMETNS = bool(int(config('TEST_PAYMENTS')))
if TEST_PAYMETNS:
    pass
else:
    pass
# Настройка webhook
BASE_WEBHOOK_URL = f'https://{config("WEBHOOK_DOMAIN")}'
BOT_WEBHOOK_PATH = '/unifreelance/webhook'
PAYMENT_WEBHOOK_PATH = '/unifreelance/payment-webhook'

WEBAPP_HOST = '127.0.0.1'
WEBAPP_PORT = int(config("WEBAPP_PORT"))

WEBHOOK_SSL_CERT = config('WEBHOOK_SSL_CERT')
WEBHOOK_SSL_PRIV = config('WEBHOOK_SSL_PRIV')

# Формат времени
DATETIME_FORMAT = "%Y-%m-%d %H:%M"

# defining the timezone
tz = pytz.timezone('Europe/Moscow')

# Роутер
router = Router()

# Режим программы
mode = config('MODE')

# Настройка конфигурации ЮKassa
# Configuration.account_id = YOOKASSA_SHOP_ID
# Configuration.secret_key = YOOKASSA_SECRET_KEY

# Кое-т для напоминания
K_remind = 0.85

# Лимит активных подписок
ACTIVE_COUNT_SUB_LIMIT = 3

# ___________________________________________________________________________
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

dp = Dispatcher()

# Configure Redis job store
jobstores = {
    'default': RedisJobStore(
        jobs_key='apscheduler.jobs',
        run_times_key='apscheduler.run_times',
        host='redis_service',  # Use the Docker Compose service name
        port=6379
    )
}

scheduler = AsyncIOScheduler(jobstores=jobstores)

r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
