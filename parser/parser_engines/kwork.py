import os
import random
import time
import traceback

import requests
import undetected_chromedriver as uc
from webdriver_manager.chrome import ChromeDriverManager

from .order_object import Order

orders_url = 'https://kwork.ru/projects?keyword={query}'
detail_url = 'https://kwork.ru/projects/'


def parse_last_ten():
    # Для Kwork proxy не требуется
    options = uc.ChromeOptions()
    # options.add_argument(f"--proxy-server={get_http_proxy()}")
    options.add_argument('--headless')
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver_path = ChromeDriverManager(driver_version='131.0.6778.204').install()

    driver = uc.Chrome(
        use_subprocess=False,
        options=options
    )

    try:

        driver.get(orders_url.format(query=''))
        time.sleep(random.randint(1, 5))

        # Подождем, чтобы страница успела полностью загрузиться
        time.sleep(2)

        # Выполним JavaScript, чтобы получить объект window.stateData
        state_data = driver.execute_script("return window.stateData;")["wantsListData"]["wants"]

        orders_data = []

        for order in state_data[:10]:
            task_id = str(order["id"])
            title = order["name"]
            payment = f'Желаемый  бюджет до {order["priceLimit"]}, допустимый до {order["possiblePriceLimit"]}'
            description = order["description"]
            direct_url = detail_url + str(order["id"])

            additional_files = [file["url"] for file in order["files"]]

            order_object = Order(
                task_id, title, payment, description, direct_url, additional_files, platform='kwork'
            )
            orders_data.append(order_object)

        # Закрытие окон браузера
        try:
            curr = driver.current_window_handle
            for handle in driver.window_handles:
                driver.switch_to.window(handle)
                if handle != curr:
                    driver.close()
        except Exception:
            pass

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
    orders, status = parse_last_ten()
    for o in orders:
        print(o)
