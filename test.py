import logging
import os
import platform
import random
import time
import traceback

import requests
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from undetected_chromedriver import ChromeOptions
# from webdriver_manager.chrome import ChromeDriverManager

orders_url = 'https://www.upwork.com/nx/search/jobs/?q={query}'

isLinux = platform.system() == 'Linux'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def parse_last_ten():
    if isLinux:
        os.system("pkill chrome")
        # Конфигурация Xvfb
        from pyvirtualdisplay import Display

        # Запускаем виртуальный дисплей
        display = Display(visible=False, size=(1024, 768))
        display.start()
    options = ChromeOptions()
    # options.add_argument('--headless')  # Запускать в фоновом режиме
    options.add_argument('--no-sandbox')  # Отключить sandbox
    options.add_argument('--disable-dev-shm-usage')  # Отключить использование /dev/shm
    options.add_argument('start-maximized')  # Открывать в максимизированном окне
    options.add_argument('disable-infobars')  # Отключить уведомления
    options.add_argument('--disable-extensions')  # Отключить расширения
    options.add_argument('--proxy-server="direct://"')  # Без прокси
    options.add_argument('--proxy-bypass-list=*')  # Бypass для всех прокси\
    options.add_argument("--remote-debugging-port=9230")
    options.add_argument('--disable-gpu')  # Отключить GPU (для серверов)

    # Переход на сайт
    driver = uc.Chrome(options=options)
    try:
        driver.get(orders_url.format(query=''))
        time.sleep(random.randint(1, 5))
        print(driver.page_source)

    except requests.ConnectionError:
        print('Request Error:')
        traceback.print_exc()
        return [], 'error'
    except requests.exceptions.RequestException:
        print('Request Error:')
        traceback.print_exc()
        return [], 'error'
    except Exception:
        print('Unexpected error:')
        traceback.print_exc()
        return [], 'error'
    finally:

        if isLinux:
            # Остановка виртуального дисплея
            display.stop()

        # Закрытие окон браузера
        try:
            curr = driver.current_window_handle
            for handle in driver.window_handles:
                driver.switch_to.window(handle)
                if handle != curr:
                    driver.close()
        except Exception:
            pass

        # Закрытие браузера
        driver.quit()


if __name__ == '__main__':
    os.chdir('../../')
    print(orders_url)
    print("https://ipv4.myexternalip.com/raw/")
    url = input("Введите адрес: ")
    orders, status = parse_last_ten()
    for o in orders:
        print(o)
