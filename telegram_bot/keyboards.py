import telebot
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from telegram_bot.headers import TEST_PAYMETNS
from telegram_bot.subscriptions import subscriptions

# Данные о биржах
PLATFORMS = {
    "fl": "fl.ru",
    # "freelance": "freelance.ru",
    # "weblancer": "weblancer.net",
    # "freelancehunt": "freelancehunt.com",
    "upwork": "upwork.com",
    # "workspace": "workspace.ru",
    "habr": "freelance.habr.com",
    # "freelancer": "www.freelancer.com",
    # "youdo": "youdo.com",
    "kwork": "kwork.ru"
}


# Блок приветствие

def get_welcome_1_message():
    return """
Привет! 👋
Я — бот, который поможет тебе быстро находить подходящие заказы на биржах фриланса. 🚀

Вот что я умею:
1️⃣ Выбрать биржи: Укажи, с каких бирж ты хочешь получать заказы.
2️⃣ Теги для поиска: Добавь ключевые слова, чтобы находить только интересующие тебя задачи.
3️⃣ Стоп-теги: Исключи нежелательные темы или категории с помощью стоп-слов.
4️⃣ Фильтры по цене: Настрой минимальную и максимальную стоимость заказа.
5️⃣ Дополнительные фильтры: Также предложу другие критерии — я гибкий!

💡 Следуй инструкциям или напиши /help, чтобы узнать больше о возможностях.

Готов искать заказы? Давай начнём! 👇"""


def get_welcome_1_keyboard():
    button = types.InlineKeyboardButton(text="Продолжить", callback_data="welcome")
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def get_welcome_2_message(full_name, user_filters, user_active_subscriptions, user_inactive_subscriptions):
    if len(user_filters) > 0:
        if len(user_active_subscriptions) > 0:
            status = "✅ Бот запущен"
        else:
            status = "⛔ Подписка закончилась. Пиши /buy"
    else:
        status = "⚠️ Необходимо настроить бота"

    active_subs_text = []
    for sub in user_active_subscriptions:
        active_subs_text.append(f"""<blockquote>{sub.name}        
    От: {sub.datetime_operation}
    До: {sub.datetime_expire}</blockquote>""")

    inactive_subs_text = []
    for sub in user_inactive_subscriptions:
        inactive_subs_text.append(f"""<blockquote>{sub.name}        
    От: {sub.datetime_operation}
    До: {sub.datetime_expire}</blockquote>""")

    if len(active_subs_text) > 0 and len(inactive_subs_text) > 0:
        subs_text = f"""📋 Вот список всех ваших UniFreelance подписок: 
    
    {"🟢 Активные подписки:" + ' '.join(active_subs_text) if len(active_subs_text) > 0 else ""}
    {"🔴 Истёкшие подписки:" + ' '.join(inactive_subs_text) if len(inactive_subs_text) > 0 else ""}
    Ключи активных подписок:
    """
    else:
        subs_text = "У вас нет подписок 🥺"

    return f"""
Добро пожаловать, <b>{full_name}</b>!

Статус бота: {status}

Подписка: {subs_text}"""


def get_welcome_2_keyboard(user_filters):
    if len(user_filters) > 0:
        button = types.InlineKeyboardButton(text="✏️ Изменить настройку", callback_data="goto_setup")
        return InlineKeyboardMarkup(inline_keyboard=[[button]])
    else:
        button = types.InlineKeyboardButton(text="🆕 Начать настройку", callback_data="goto_setup")
        return InlineKeyboardMarkup(inline_keyboard=[[button]])


def get_setup_menu_text(user_filters):
    platforms_text = '\n'.join([
        f'<b>{index}</b>. {PLATFORMS[filter_object.platform]}'.strip()
        for
        index, filter_object in enumerate(user_filters, start=1)])
    if len(user_filters) > 0:
        return f"""Ваши подключённые биржи:
{platforms_text}"""
    else:
        return "У вас нет подключённых бирж"


def get_setup_menu_keyboard(user_filters):
    button1 = types.InlineKeyboardButton(text="Добавить/Удалить биржу", callback_data="add_platform")

    platform_buttons = [[types.InlineKeyboardButton(text=f"Настроить {PLATFORMS[filter_object.platform]}",
                                                    callback_data=f"goto_settings_{filter_object.platform}")] for
                        filter_object in user_filters]
    return InlineKeyboardMarkup(inline_keyboard=[*platform_buttons, [button1]])


# Клавиатура настроек платформы
def get_settings_keyboard(platform):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить/Удалить ключевые слова", callback_data=f"add_keywords_{platform}")],
        [InlineKeyboardButton(text="🚫 Добавить/Удалить стоп-слова", callback_data=f"add_stopwords_{platform}")],
        [InlineKeyboardButton(text="💰 Указать диапазон цен", callback_data=f"set_price_{platform}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="goto_setup")]
    ])


def back_to_platform_settings(platform, delete_all_keywords=False, delete_all_stop_keywords=False):
    buttons = []
    if delete_all_keywords:
        buttons.append(
            [InlineKeyboardButton(text="🗑️ Удалить все слова", callback_data=f"delete_all_keywords_{platform}")], )
    if delete_all_stop_keywords:
        buttons.append(
            [InlineKeyboardButton(text="🗑️ Удалить все слова", callback_data=f"delete_all_stop_keywords_{platform}")], )
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"goto_settings_{platform}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Функция для создания клавиатуры
def create_market_keyboard(selected_markets: set) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки для каждой биржи
    for platform in PLATFORMS.keys():
        if platform in selected_markets:
            label = f"✅ {PLATFORMS[platform]}"
            callback_data = f"toggle:{platform}"
        else:
            label = f"❌ {PLATFORMS[platform]}"
            callback_data = f"toggle:{platform}"
        builder.add(InlineKeyboardButton(text=label, callback_data=callback_data))

    builder.add(InlineKeyboardButton(text="Готово", callback_data="navigate:done"))
    builder.adjust(1)
    return builder.as_markup()


def get_new_task_notification(order_dict):
    return f'''
<b>{order_dict['title']}</b>

{order_dict['description'] if len(order_dict['description']) < 400 else order_dict['description'][:400] + '...'}

<b>{order_dict['payment']}</b>

Платформа: <b>{PLATFORMS[order_dict['platform']]}</b>

<a href='{order_dict['direct_url']}'>Подробнее</a>
'''


def def_new_task_notification(message_id, order_url, db_id):
    keyboard = telebot.types.InlineKeyboardMarkup()
    button_translate = telebot.types.InlineKeyboardButton(text="Перевод",
                                                          callback_data=f'translate|{message_id}|{db_id}')
    button_go = telebot.types.InlineKeyboardButton(text="Перейти к заказу", url=order_url)
    keyboard.row(button_translate)
    keyboard.row(button_go)
    return keyboard


# зу9фкнторщц485п37нпе8г345з0ол9гнщ3459уз90шпмггк
# Блок список подписок

def get_subs_message(sale: int = 0):
    return [f"""
Выбирайте удобный план и наслаждайтесь безопасным интернет-серфингом! 🌐

✅ Безопасные платежи через ЮКасса
✅ Гарантия возврата средств в течение 3-х дней после приобретения подписки 

{f'🔖 Ваша скидка: {sale}%' if sale else ''}
📅 Ежемесячные подписки:
""", "🗓️ Годовые подписки (✅ Экономия 20%):"]


def get_subs_keyboard(sale: int = 0):
    testday_1 = types.InlineKeyboardButton(
        text=f"1 устройство (тестовая подписка) - {subscriptions['testday_1']['price'] * (100 - sale) / 100}₽",
        callback_data="testday_1")

    month_1 = types.InlineKeyboardButton(
        text=f"1 устройство - {subscriptions['month_1']['price'] * (100 - sale) / 100}₽",
        callback_data="month_1")
    month_2 = types.InlineKeyboardButton(
        text=f"2 устройство - {subscriptions['month_2']['price'] * (100 - sale) / 100}₽",
        callback_data="month_2")
    month_3 = types.InlineKeyboardButton(
        text=f"3 устройство - {subscriptions['month_3']['price'] * (100 - sale) / 100}₽",
        callback_data="month_3")

    year_1 = types.InlineKeyboardButton(text=f"1 устройство - {subscriptions['year_1']['price'] * (100 - sale) / 100}₽",
                                        callback_data="year_1")
    year_2 = types.InlineKeyboardButton(text=f"2 устройство - {subscriptions['year_2']['price'] * (100 - sale) / 100}₽",
                                        callback_data="year_2")
    year_3 = types.InlineKeyboardButton(text=f"3 устройство - {subscriptions['year_3']['price'] * (100 - sale) / 100}₽",
                                        callback_data="year_3")

    return [
        InlineKeyboardMarkup(inline_keyboard=[[month_1], [month_2], [month_3]]),
        InlineKeyboardMarkup(inline_keyboard=[[year_1], [year_2], [year_3]])
    ] if not TEST_PAYMETNS else [
        InlineKeyboardMarkup(inline_keyboard=[[testday_1]]),
        InlineKeyboardMarkup(inline_keyboard=[])
    ]


# Блок оплаты

def get_pay_message(sale):
    return f"""
🛍️ Отлично! Вот ваша ссылка на оплату: ✨
{f'Ваша скидка: {sale}%' if sale > 0 else ''}"""


def get_pay_keyboard(amount, url):
    button1 = types.InlineKeyboardButton(text=f"Оплатить {amount}₽", url=url)
    return InlineKeyboardMarkup(inline_keyboard=[[button1]])


# Успешная оплата

def get_success_pay_message(config_url):
    return f"""
✅ Супер! Вот ваши данные для VPN подключения: 🌐

<blockquote>{config_url}</blockquote>

Спасибо за выбор Kovanoff VPN 🍀"""


def get_success_pay_keyboard():
    button1 = types.InlineKeyboardButton(text="Инструкция для всех платформ", callback_data="instruction")
    return InlineKeyboardMarkup(inline_keyboard=[[button1]])


# Отмена оплаты

def get_canceled_pay_message():
    return f"""
❌ Упс! оплата не прошла, попробуйте снова:
"""


def get_canceled_pay_keyboard(again_text, again_callback):
    button1 = types.InlineKeyboardButton(text=again_text, callback_data=again_callback)
    return InlineKeyboardMarkup(inline_keyboard=[[button1]])


# Список подписок

def get_empty_subscriptions_message():
    return f"""
❌ У вас нет подписок 🥺
"""


def get_actual_subscriptions_message(active_subs, inactive_subs):
    active_subs_text = []
    for sub in active_subs:
        active_subs_text.append(f"""<blockquote>{subscriptions[sub['subscription']]['name']}        
От: {sub['datetime_operation']}
До: {sub['datetime_expire']}</blockquote>""")

    inactive_subs_text = []
    for sub in inactive_subs:
        inactive_subs_text.append(f"""<blockquote>{subscriptions[sub['subscription']]['name']}        
От: {sub['datetime_operation']}
До: {sub['datetime_expire']}</blockquote>""")

    return f"""
📋 Вот список всех ваших VPN подписок: 🌐

{"🟢 Активные подписки:" + ' '.join(active_subs_text) if len(active_subs_text) > 0 else ""}
{"🔴 Истёкшие подписки:" + ' '.join(inactive_subs_text) if len(inactive_subs_text) > 0 else ""}
Ключи активных подписок:
"""


def get_active_subscriptions_keyboard(active_subs):
    button_list = [
        [types.InlineKeyboardButton(text=f"{subscriptions[sub['subscription']]['name']} До: {sub['datetime_expire']}",
                                    callback_data=f"get_info_{sub['panel_uuid']}")] for sub in active_subs
    ]
    return InlineKeyboardMarkup(inline_keyboard=button_list)


# Подписка окончена/заканчивается

def get_cancel_subsciption():
    return """
⛔ К сожалению ваша подписка закончилась. Поспешите продлить доступ к интернету без ограничений 🚀"""


def get_remind_message(days_before_expr):
    return f"""
❗ Внимание, ваша подписка закончится через {days_before_expr} дня. Поспешите продлить доступ к интернету без ограничений 🚀"""


def get_continue_cancell_message():
    return f"""
⛔ К сожалению ваша подписка закончилась. Продлить её не получиться. Вы всегда можете приобрести новую 🚀"""


def get_cancel_keyboard():
    button1 = types.InlineKeyboardButton(text="Приобрести подписку", callback_data="get_sub")
    return InlineKeyboardMarkup(inline_keyboard=[[button1]])


def get_continue_keyboard(panel_uuid):
    button1 = types.InlineKeyboardButton(text="Продлить подписку", callback_data=f"continue_{panel_uuid}")
    return InlineKeyboardMarkup(inline_keyboard=[[button1]])


# Продление подписки

def get_success_continue_message(exp_date):
    return f"""
Подписка успешно продлена! ✅
Дата окончания подписки: {exp_date}"""


# Пробная подписка
def get_cancel_try_period_message():
    return """
К сожалению воспользоваться пробным периодом можно только 1 раз 😁. Рекомендуем приобрести подписку"""


# Реферал

def get_ref_link_message(link):
    return f"🔗 Ваша реф. ссылка {link}"


def get_sale_limit_message(sale):
    return f"""
По вашей ссылке приобрели подписку. 💲 
Ваша скидка: {sale}% (Максимум.) 🔝"""


def get_sale_increase_message(sale):
    return f"""
По вашей ссылке приобрели подписку. 💲 
Ваша скидка: {sale}% 📈"""


# Технические работы
def get_service_working_message():
    return """
🚧 Внимание! В данный момент проводятся технические работы 🛠️. Наш бот временно недоступен ⏳. Мы прилагаем все усилия, чтобы вернуться как можно скорее! 🔧

Спасибо за ваше терпение и понимание 🙏"""


def get_subs_limit_message(limit):
    return f"""
⚠️ У вас не может быть больше {limit} активных подписок! 🖐️

Пожалуйста, дождитесь окончания одной из текущих подписок, чтобы добавить новую 💳"""


def get_wrong_command_message():
    return """
⚠️️ У вас нет прав, чтобы использовать эту команду!"""
