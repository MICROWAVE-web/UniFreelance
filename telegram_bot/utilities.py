import json
import re

from telegram_bot.headers import r


def matches_order_to_parameters(order, parameters):
    """
    Функция для проверки соответствия заказа параметрам.

    :param order: Словарь с информацией о заказе.
    :param parameters: Словарь с параметрами для фильтрации.

    :return: True, если заказ соответствует всем параметрам, иначе False.
    """
    # 1. Проверка ключевых слов
    if parameters.get("keywords"):
        if not any(
                keyword.lower() in order["title"].lower() or keyword.lower() in order["description"].lower() for keyword
                in parameters["keywords"]):
            return False

    # 2. Проверка запрещенных ключевых слов
    if parameters.get("stopkeywords"):
        if any(stopkeyword.lower() in order["title"].lower() or stopkeyword.lower() in order["description"].lower() for
               stopkeyword in parameters["stopkeywords"]):
            return False

    # 4. Проверка указанной стоимости
    if parameters.get("have_price"):
        if bool(re.search(r'\d', order["payment"])) is False:
            return False

    # 4. Проверка диапазона цен
    if parameters.get("minprice") and parameters.get("maxprice"):
        numbers = re.findall(r'\d+', order["payment"])
        # Преобразуем найденные числа в целые числа
        if not all([int(parameters["minprice"]) <= int(num) <= int(parameters["maxprice"]) for num in numbers]):
            return False

    return True


def check_the_filter_match(telegram_id, order_dict, filter_query):
    paused_user = r.get(telegram_id)
    if paused_user:
        return False

    json_query = safe_json_loads(filter_query)
    if matches_order_to_parameters(order_dict, json_query):
        return True
    return False


def safe_json_loads(text):
    if not text.strip():  # Проверяем, что строка не пустая
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Логируем или обрабатываем ошибку, если необходимо
        print("Ошибка при декодировании JSON.")
        return {}
