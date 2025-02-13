import logging
import os
import platform
import random
import time
import traceback

import requests
import undetected_chromedriver as uc
from undetected_chromedriver import ChromeOptions

from parser.utilities import get_http_proxy

# from webdriver_manager.chrome import ChromeDriverManager


isLinux = platform.system() == 'Linux'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def parse_last_ten(url):
    if isLinux:
        os.system("pkill chrome")
        # Конфигурация Xvfb
        from pyvirtualdisplay import Display

        # Запускаем виртуальный дисплей
        display = Display(visible=False, size=(1024, 768))
        display.start()
    options = ChromeOptions()
    custom_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

    # set a custom user agent in the browser option

    options.add_argument(f'--user-agent={custom_user_agent}')

    # options.add_argument('--headless')  # Запускать в фоновом режиме
    options.add_argument('--no-sandbox')  # Отключить sandbox
    options.add_argument('--disable-dev-shm-usage')  # Отключить использование /dev/shm
    options.add_argument('--start-maximized')  # Открывать в максимизированном окне
    options.add_argument('--disable-infobars')  # Отключить уведомления
    options.add_argument('--disable-extensions')  # Отключить расширения
    # options.add_argument('--proxy-server="direct://"')  # Без прокси
    # options.add_argument('--proxy-bypass-list=*')  # Бypass для всех прокси\
    options.add_argument("--remote-debugging-port=9230")
    options.add_argument('--disable-gpu')  # Отключить GPU (для серверов)
    options.add_argument(f"--proxy-server={get_http_proxy()}")
    print(f"--proxy-server={get_http_proxy()}")

    # Переход на сайт
    driver = uc.Chrome(options=options)
    try:
        driver.get(url.format(query=''))
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
    # print(orders_url)
    # print("https://ipv4.myexternalip.com/raw/")
    url = 'https://www.upwork.com/nx/search/jobs/?q={query}'
    # url = "https://httpbin.io/ip"
    orders, status = parse_last_ten(url)
    for o in orders:
        print(o)
