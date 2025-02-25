import json
import logging
import os
import traceback

import requests
import telebot
from decouple import config
from random_user_agent.params import SoftwareName, OperatingSystem
from random_user_agent.user_agent import UserAgent
from randomheader import RandomHeader

from telegram_bot.headers import ADMINS

bot = telebot.TeleBot(config("API_TOKEN"))


def wakeup_admins(message):
    try:
        for admin in ADMINS:
            bot.send_message(chat_id=admin, text=message)
    except Exception:
        traceback.print_exc()


def check_proxy(proxy):
    try:
        response = requests.get("https://www.google.com", proxies={"http": proxy, "https": proxy}, timeout=10)
        return response.status_code == 200
    except Exception:
        logging.error("Error, while proxy checking!")
        logging.error(traceback.format_exc())
        return False


def get_http_proxy():
    """
    Прокси для запросов заблоченных сайтов
    """
    return config("PROXY")


def get_user_agent():
    """
    Возвращает случайные user-agent
    """
    software_names = [SoftwareName.CHROME.value]
    operating_systems = [OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value]

    user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=100)

    return user_agent_rotator.get_random_user_agent()


def get_habr_cookies():
    """
    Читает cookies из файла и возвращает их в виде словаря.
    """
    with open("parser/util_files/habr_cookies.txt", "r") as file:
        cookies = json.load(file)
    return cookies


def get_upwork_cookies():
    """
    Читает cookies из файла и возвращает их в виде словаря.
    """
    with open("parser/util_files/upwork_cookies.txt", "r") as file:
        cookies = json.load(file)
    return cookies


def get_headers():
    rh = RandomHeader()
    return rh.header()


if __name__ == '__main__':
    print(get_habr_cookies())
