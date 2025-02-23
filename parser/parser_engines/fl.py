import sys
import os

# Добавление корневого каталога проекта в путь поиска
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import time
import traceback

import requests
from bs4 import BeautifulSoup

from parser.parser_engines.order_object import Order
from parser.utilities import get_headers, get_upwork_cookies

rss_url = 'https://www.fl.ru/rss/all.xml'


def sort_item_by_date(item):
    pub_date_string = item.get('pubdate')
    if pub_date_string:
        pub_date_string = pub_date_string.split(', ', 1)[-1].replace(' GMT', '', 1)
        return time.strptime(pub_date_string, "%d %b %Y %H:%M:%S")


def get_payment(item):
    title_string = item.find('title')
    if title_string is not None:
        splitted_title = title_string.text.split('(Бюджет: ')
        if len(splitted_title) == 1:
            return "По договоренности"
        payment = splitted_title[-1].replace(')', '', 1)
        return str(payment)


def get_task_id(item):
    link_string = item.find('link')
    if link_string is not None:
        task_id = link_string.text.split('/projects/')[-1].split('/')[0]
        return str(task_id)


def parse_last_ten():
    try:

        response = requests.get(rss_url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(response.text, 'xml')

        items = soup.findAll('item')

        orders_data = []
        for item in items[:10]:
            title = item.find('title').text
            direct_url = item.find('link').text
            description = item.find('description').text
            # pubdate = item.find('pubDate').text
            task_id = get_task_id(item)
            payment = get_payment(item).replace("&#8381;", "₽")
            order_object = Order(
                task_id, title, payment, description, direct_url, platform='fl'
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
    print(get_upwork_cookies())


if __name__ == '__main__':
    os.chdir('../../')
    orders, status = parse_last_ten()
    for o in orders:
        print(o)
