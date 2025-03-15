import logging
import os
import platform
import random
import time
import traceback

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from parser.parser_engines.order_object import Order
from parser.utilities import get_http_proxy, wakeup_admins, get_user_agent_1, get_user_agent_2, get_upwork_cookies

orders_url = 'https://www.upwork.com/nx/search/jobs/?q={query}'

print(platform.system())
isLinux = platform.system() == 'Linux'

if isLinux:
    from pyvirtualdisplay import Display


def safe_find_element(driver, by, value, retries=3, delay=2):
    for _ in range(retries):
        try:
            return driver.find_element(by, value)
        except Exception as e:
            print(f"Error finding element: {e}. Retrying...")
            time.sleep(delay)
    return None


def parse_last_ten():
    if isLinux:
        try:
            display = Display(visible=False, size=(1024, 768))
            display.start()
        except Exception:
            logging.error(f"Failed to start virtual display!")
            traceback.print_exc()
            return [], 'error'

    options = uc.ChromeOptions()
    options.add_argument("--window-size=1024, 768")
    options.add_argument(f"--proxy-server={get_http_proxy()}")
    options.add_argument(f"--user-agent={get_user_agent_2()}")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument('--start-maximized')  # Открывать в максимизированном окне
    options.add_argument('--disable-infobars')  # Отключить уведомления
    options.add_argument('--disable-extensions')  # Отключить расширения
    options.add_argument("--auto-open-devtools-for-tabs")
    # options.add_argument('--headless')
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--single-process")
    options.add_argument("--no-zygote")
    # driver_path = ChromeDriverManager().install()
    try:
        driver = uc.Chrome(
            # driver_executable_path=driver_path,
            options=options
        )
    except Exception:
        traceback.print_exc()
        return [], 'error'
    try:
        #cookies = get_upwork_cookies()
        driver.get(orders_url.format(query=''))

        #for c in cookies:
        #    p = {
        #        'name': c,
        #        'value': cookies[c]
        #    }
        #    driver.add_cookie(p)

        driver.get(orders_url.format(query=''))

        time.sleep(random.randint(1, 5))
        # Ожидаем, пока нужный элемент полностью загрузится
        try:
            WebDriverWait(driver, 30).until(ec.presence_of_element_located((By.XPATH, "//article")))
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
                article = safe_find_element(driver, By.XPATH, article_xpath)
                if not article:
                    logging.error("Article not found")
                    continue  # Пропустить блок, если элемент не найден

                # article = driver.find_element(By.XPATH, article_xpath)

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
                order_object = Order(
                    task_id, title, payment, description, direct_url, platform='upwork'
                )

                orders_data.append(order_object)

            except Exception:
                print(f"Ошибка при обработке блока {i}:")
                traceback.print_exc()
                continue  # Переход к следующему блоку, если возникла ошибка

        return orders_data, 'success'
    except Exception:
        print('Unexpected error:')
        traceback.print_exc()

        wakeup_admins(traceback.format_exc())
        return [], 'error'

    finally:

        if isLinux:
            # Остановка виртуального дисплея
            try:
                display.stop()
            except Exception:
                logging.error(f"Failed to stop virtual display!")
                traceback.print_exc()

        # Закрытие окон браузера
        try:
            curr = driver.current_window_handle
            for handle in driver.window_handles:
                driver.switch_to.window(handle)
                if handle != curr:
                    driver.close()
        except Exception:
            pass

        driver.quit()
        del driver

        # Закрытие браузера
        if isLinux:
            try:
                display.stop()
            except Exception:
                print(f"Failed to stop virtual display!")
                traceback.print_exc()


if __name__ == '__main__':
    os.chdir('../../')
    orders, status = parse_last_ten()
    for o in orders:
        print(o)
