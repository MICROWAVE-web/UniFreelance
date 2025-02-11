import logging
import os
import platform
import random
import time
import traceback

import requests
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from decouple import config
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from undetected_chromedriver import ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager

orders_url = 'https://www.upwork.com/nx/search/jobs/?q={query}'

isLinux = platform.system() == 'Linux'

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def parse_last_ten():
    if isLinux:
        os.system("pkill chrome")
        # Конфигурация Xvfb
        from pyvirtualdisplay import Display

        # Запускаем виртуальный дисплей
        display = Display(visible=False, size=(1024, 768))
        display.start()
    options = ChromeOptions()
    options.add_argument('--headless')  # Запускать в фоновом режиме
    options.add_argument('--no-sandbox')  # Отключить sandbox
    options.add_argument('--disable-dev-shm-usage')  # Отключить использование /dev/shm
    options.add_argument('start-maximized')  # Открывать в максимизированном окне
    options.add_argument('disable-infobars')  # Отключить уведомления
    options.add_argument('--disable-extensions')  # Отключить расширения
    options.add_argument('--proxy-server="direct://"')  # Без прокси
    options.add_argument('--proxy-bypass-list=*')  # Бypass для всех прокси
    options.add_argument('--disable-gpu')  # Отключить GPU (для серверов)


    # Переход на сайт
    try:
        driver = uc.Chrome(service=ChromeDriverManager().install(), options=options)
    except Exception:
        traceback.print_exc()
        return [], 'error'
    try:
        driver.get(orders_url.format(query=''))
        time.sleep(random.randint(1, 5))
        # Ожидаем, пока нужный элемент полностью загрузится
        try:
            WebDriverWait(driver, 10).until(ec.presence_of_element_located((By.XPATH, "//article")))
        except TimeoutException:
            print("Timed out waiting for page to load")
            return [], 'error'
        html = driver.page_source
        BeautifulSoup(html, 'html.parser')
        # Список для хранения данных
        orders_data = []
        # Перебираем до 10 блоков с номерами
        for i in range(1, 11):
            try:
                # Путь к нужному блоку по XPath
                article_xpath = f"/html/body/div[4]/div/div/div[1]/main/div/div/div/div[2]/div[2]/section/article[{i}]"

                # Ищем блок статьи
                article = driver.find_element(By.XPATH, article_xpath)

                # Извлекаем task_id
                task_id = article.get_attribute("data-ev-job-uid")

                # Извлекаем title
                title_element = article.find_element(By.XPATH, "./div[1]/div[1]/div/div/h2/a")
                title = title_element.text.strip()

                # Извлекаем payment (можно сделать это с помощью XPath или другой логики)
                payment_element = article.find_element(By.XPATH, "./div[2]/ul")
                payment = payment_element.text.strip()

                # Извлекаем description
                description_element = article.find_element(By.XPATH, "./div[2]/div[1]/div/p")
                description = description_element.text.strip()

                # Извлекаем direct_url
                direct_url = title_element.get_attribute("href")

                # Добавляем все данные в список
                print(
                    task_id, title, payment, description, direct_url, platform
                )

            except Exception:
                print(f"Ошибка при обработке блока {i}:")
                traceback.print_exc()
                continue  # Переход к следующему блоку, если возникла ошибка

        return orders_data, 'success'
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
