import os
import traceback

import requests
from bs4 import BeautifulSoup
from utilities import get_habr_cookies, get_headers

from .order_object import Order

orders_url = 'https://freelance.habr.com/tasks'


def parse_last_ten():
    try:

        response = requests.get(orders_url, cookies=get_habr_cookies(), headers=get_headers(), timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")

        orders = soup.select(".task-card__wrapper")  # Селектор для заказа

        orders_data = []
        for order_element in orders[:10]:
            task_id = order_element.select_one(".task-card__link")["href"].replace("/tasks/", "")
            title = order_element.select_one(".task-card__heading").text.strip()
            payment = order_element.select_one(".task-card__price").text.replace('₽', '₽ ').strip()
            description = order_element.select_one(".task-card__description").text.strip()
            direct_url = orders_url + order_element.select_one(".task-card__link")["href"].replace("tasks/", "")

            order_object = Order(
                task_id, title, payment, description, direct_url, platform='habr'
            )
            orders_data.append(order_object)

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


def test_print_cookie():
    print(get_habr_cookies())


if __name__ == '__main__':
    os.chdir('../../')
    test_print_cookie()
    # orders, status = parse_last_ten()
    # for o in orders:
    #    print(o)
