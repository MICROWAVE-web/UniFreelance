import os
import sys

# Добавление корневого каталога проекта в путь поиска
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import random
import time
from datetime import datetime

from decouple import config

from db_engine import create_parser_database
from db_engine import save_to_db  # Импорт функции для сохранения в БД
from parser_engines import fl, kwork, upwork  # Импорт парсеров

# Периодичность парсинга (в минутах)
MIN_INTERVAL = int(config('MIN_INTERVAL'))  # Минимальная периодичность парсинга
MAX_INTERVAL = int(config('MAX_INTERVAL'))  # Максимальная периодичность
RANDOM_INTERVAL = int(config('RANDOM_INTERVAL'))  # Случайное отклонение от интервала


# Функция для добавления случайной задержки
def random_sleep():
    delay = random.randint(MIN_INTERVAL * 60, MAX_INTERVAL * 60) + random.randint(0, RANDOM_INTERVAL * 60)
    print(f"Задержка: {delay} секунд")
    time.sleep(delay)


# Асинхронная функция парсинга
def parse_orders():
    while True:
        if eval(config('CONSOLE_LOG')) == 1:
            print(f"{datetime.now()} - Начинаем парсинг...")

        # Парсинг с разных бирж
        orders_fl, status_fl = fl.parse_last_ten()  # Парсинг с FL
        if orders_fl:
            save_to_db(orders_fl, 'fl')
        # orders_habr, status_habr = habr.parse_last_ten()  # Парсинг с Habr
        # if orders_habr:
        #    save_to_db(orders_habr, 'habr')
        orders_kwork, status_kwork = kwork.parse_last_ten()  # Парсинг с Kwork
        if orders_kwork:
            save_to_db(orders_kwork, 'kwork')
        #orders_upwork, status_upwork = upwork.parse_last_ten()  # Парсинг с Upwork
        #if orders_upwork:
        #    save_to_db(orders_upwork, 'upwork')

        if eval(config('CONSOLE_LOG')) == 1:
            print(f"{datetime.now()} - Парсинг завершен. Ожидаем следующую итерацию.")

        # Задержка перед следующим парсингом
        random_sleep()


# Запуск программы
if __name__ == '__main__':
    # Проверка создания таблиц
    create_parser_database()
    parse_orders()
