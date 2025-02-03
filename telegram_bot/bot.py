import asyncio
import json
import ssl
import time
import traceback
from datetime import date, timedelta, datetime

import redis
from aiogram import F
from aiogram.filters import Command, CommandStart, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.payload import decode_payload
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from apscheduler.triggers.date import DateTrigger
from deep_translator import GoogleTranslator

import telegram_bot
from headers import (bot, dp, scheduler, ADMINS, router, BOT_WEBHOOK_PATH, BASE_WEBHOOK_URL, mode,
                     PAYMENT_WEBHOOK_PATH, WEBAPP_PORT, WEBAPP_HOST, DATETIME_FORMAT, tz, ACTIVE_COUNT_SUB_LIMIT,
                     logging, r, WEBHOOK_SSL_PRIV, WEBHOOK_SSL_CERT)
from keyboards import *
from parser.db_engine import get_task_by_id, create_database
from telegram_bot.db_engine import check_user_exists, get_user_by_telegram_id, get_filters_by_user_id, \
    get_active_subscriptions, get_inactive_subscriptions, delete_filter, add_filter, add_sale_to_user, add_user, \
    get_filter_by_user_id, edit_filter_query_by_user_id
from telegram_bot.utilities import safe_json_loads
from throttle_middleware import ThrottlingMiddleware

# Языки для перевода
LANGUAGES = {
    "🇷🇺 Русский": "ru",
    "🇺🇸 English": "en",
    "🇪🇸 Español": "es",
    "🇩🇪 Deutsch": "de",
    "🇫🇷 Français": "fr"
}


class MarketStates(StatesGroup):
    selecting_platform = State()
    selecting_settings = State()


class FilterSettings(StatesGroup):
    waiting_keywords = State()
    waiting_stopwords = State()
    waiting_price_range = State()


# Маппинг для хранения задач по каждому пользователю
user_tasks = {}


# Задача удаления состояния через 5 минут
async def test_remove_state_after_delay(user_id: int, state: FSMContext, message_id):
    await asyncio.sleep(300)  # 5 минут (300 секунд)
    await state.clear()  # Завершаем состояние
    try:
        if message_id:
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text="Действие прервано",
            )
            await bot.edit_message_reply_markup(chat_id=user_id, message_id=message_id, reply_markup=None)
    except Exception as e:
        pass
    del user_tasks[user_id]  # Удаляем задачу для этого пользователя


# Функция для удаления состояния через 5 минут
def remove_state_after_delay(user_id, state: FSMContext, message_id=None):
    # Отменяем предыдущие задачи, если они есть
    if user_id in user_tasks:
        user_tasks[user_id].cancel()

    # Запускаем задачу для удаления состояния через 5 минут
    task = asyncio.create_task(test_remove_state_after_delay(user_id, state, message_id))
    user_tasks[user_id] = task


# Оповещение для администраторов
async def wakeup_admins(message):
    for admin in ADMINS:
        await bot.send_message(chat_id=admin, text=message)


# Приветствие шаг 1
@router.message(CommandStart())
async def send_welcome_1(message: types.Message, command: CommandObject = None):
    telegram_id = str(message.from_user.id)
    # Приостановка уведомления
    make_pause_notification(telegram_id)

    referral = ""

    # Проверка реферала
    if command and command.args:
        reference = str(decode_payload(command.args))
        if reference != telegram_id:
            referral = reference

    check = check_user_exists(telegram_id)
    if check is None:
        add_user(telegram_id, referral)

    await bot.send_message(telegram_id, text=get_welcome_1_message(), reply_markup=get_welcome_1_keyboard())


# Приветствие шаг 2
@router.callback_query(F.data == 'welcome')
async def send_welcome_2(call: CallbackQuery):
    telegram_id = str(call.from_user.id)
    # Приостановка уведомления
    make_pause_notification(telegram_id)
    full_name = call.from_user.full_name
    message_id = call.message.message_id
    user_object = get_user_by_telegram_id(telegram_id)
    user_filters = get_filters_by_user_id(user_object.id)
    user_active_subscriptions = get_active_subscriptions(user_object.id)
    user_inactive_subscriptions = get_inactive_subscriptions(user_object.id)
    await bot.edit_message_text(chat_id=telegram_id,
                                message_id=message_id,
                                text=get_welcome_2_message(full_name,
                                                           user_filters,
                                                           user_active_subscriptions,
                                                           user_inactive_subscriptions))
    await bot.edit_message_reply_markup(chat_id=telegram_id, message_id=message_id,
                                        reply_markup=get_welcome_2_keyboard(user_filters))


# Открытие общих настроек
@router.callback_query(F.data == 'goto_setup')
async def open_setup(call: CallbackQuery, state: FSMContext):
    telegram_id = str(call.from_user.id)
    # Приостановка уведомления
    make_pause_notification(telegram_id)
    user_object = get_user_by_telegram_id(telegram_id)
    user_filters = get_filters_by_user_id(user_object.id)

    current_state = await state.get_state()
    # Если вернулись, то редачим
    if current_state in [MarketStates.selecting_platform, MarketStates.selecting_settings]:
        state_data = await state.get_data()
        last_message_id = state_data.get("last_message_id")
        await bot.edit_message_text(chat_id=telegram_id, message_id=last_message_id,
                                    text=get_setup_menu_text(user_filters))
        await bot.edit_message_reply_markup(chat_id=telegram_id, message_id=last_message_id,
                                            reply_markup=get_setup_menu_keyboard(user_filters))
        await state.clear()
        await state.update_data(last_message_id=last_message_id)
    else:
        sent_message = await bot.send_message(telegram_id, get_setup_menu_text(user_filters),
                                              reply_markup=get_setup_menu_keyboard(user_filters))

        await state.clear()
        await state.update_data(last_message_id=sent_message.message_id)


# Обработчик добавление биржи
@router.callback_query(F.data == 'add_platform')
async def add_platform(call: CallbackQuery, state: FSMContext):
    telegram_id = str(call.from_user.id)
    # Приостановка уведомления
    make_pause_notification(telegram_id)
    state_data = await state.get_data()
    last_message_id = state_data.get("last_message_id")
    user_object = get_user_by_telegram_id(telegram_id)
    user_filters = get_filters_by_user_id(user_object.id)
    selected_markets = set([filter_object.platform for filter_object in user_filters])
    await state.update_data(selected_markets=selected_markets)
    await state.set_state(MarketStates.selecting_platform)

    # Очистка состояния через 5 минут
    remove_state_after_delay(telegram_id, state, last_message_id)

    await bot.edit_message_text(chat_id=telegram_id, message_id=last_message_id, text="Выберите биржи для уведомлений:")
    await bot.edit_message_reply_markup(chat_id=telegram_id, message_id=last_message_id,
                                        reply_markup=create_market_keyboard(selected_markets=selected_markets))


# Обработчик нажатия кнопок
@router.callback_query(StateFilter(MarketStates.selecting_platform))
async def callback_handler(callback: CallbackQuery, state: FSMContext):
    # Парсим callback_data
    telegram_id = str(callback.from_user.id)
    # Приостановка уведомления
    make_pause_notification(telegram_id)
    user_object = get_user_by_telegram_id(telegram_id)

    data = callback.data.split(":")
    action = data[0]
    value = data[1]

    state_data = await state.get_data()
    selected_markets = state_data.get("selected_markets", set())

    if action == "toggle":
        if value in selected_markets:
            delete_filter(user_object.id, value)
            selected_markets.remove(value)
        else:
            add_filter(user_object.id, value, "")
            selected_markets.add(value)
        await state.update_data(selected_markets=selected_markets)

        # Обновляем клавиатуру
        keyboard = create_market_keyboard(selected_markets)
        await callback.message.edit_reply_markup(reply_markup=keyboard)

    elif action == "navigate":
        if value == "done":
            await open_setup(callback, state)

    await callback.answer()


# Рефералка
async def referral_reward(referral):
    if referral == "":
        return
    telegram_id = referral
    user_object = get_user_by_telegram_id(telegram_id)

    if user_object is not None:
        if user_object.sale >= 30:
            await bot.send_message(telegram_id, get_sale_limit_message(user_object.sale))
        else:
            add_sale_to_user(telegram_id, 5)
            await bot.send_message(telegram_id, get_sale_increase_message(user_object.sale))


# Открытие настроек биржи
@router.callback_query(F.data.startswith("goto_settings_"))
async def open_platform_settings(callback: types.CallbackQuery, state: FSMContext):
    telegram_id = str(callback.from_user.id)
    """Открывает настройки уведомлений для выбранной платформы."""
    platform = callback.data.split("_")[-1]
    await state.set_state(MarketStates.selecting_settings)

    # Очистка состояния через 5 минут
    remove_state_after_delay(telegram_id, state, callback.message.message_id)

    db_user_id = get_user_by_telegram_id(telegram_id).id

    db_filter_object = get_filter_by_user_id(db_user_id, platform)
    filter_query = db_filter_object.query
    json_query = safe_json_loads(filter_query)

    keywords = json_query.get("keywords")
    stopkeywords = json_query.get("stopkeywords")
    minprice = json_query.get("minprice", "Не указана")
    maxprice = json_query.get("maxprice", "Не указана")
    have_price = json_query.get("have_price")

    await callback.message.edit_text(
        f"Настройки уведомлений для {platform}:\n\n"
        "Выберите действие:\n\n"
        f"🔑 <b>Ключевые слова:</b> {', '.join(keywords) if keywords else 'Нет ключевых слов'}\n"
        f"🚫 <b>Ключевые стоп-слова:</b> {', '.join(stopkeywords) if stopkeywords else 'Нет ключевых стоп-слов'}\n"
        f"💰 <b>Минимальная цена:</b> {minprice} валюты\n"
        f"💵 <b>Максимальная цена:</b> {maxprice} валюты\n"
        f"🔍 <b>Наличие цены:</b> {'Да' if have_price else 'Нет'}\n\n"
        "Выберите действие:",
        parse_mode='html',
        reply_markup=get_settings_keyboard(platform)
    )


# Меню настройки ключeвых слов
@router.callback_query(F.data.startswith("add_keywords_"))
async def add_keywords(callback: types.CallbackQuery, state: FSMContext):
    telegram_id = str(callback.from_user.id)
    # Приостановка уведомления
    make_pause_notification(telegram_id)
    """Пользователь добавляет ключевые слова."""
    platform = callback.data.split("_")[-1]
    await state.update_data(platform=platform)
    await state.set_state(FilterSettings.waiting_keywords)

    # Очистка состояния через 5 минут
    remove_state_after_delay(telegram_id, state, callback.message.message_id)

    await callback.message.edit_text(
        "Введите ключевые слова через запятую (,):"
    )
    await callback.message.edit_reply_markup(reply_markup=back_to_platform_settings(platform,
                                                                                    delete_all_keywords=True,
                                                                                    delete_all_stop_keywords=False))


# Удаление всех ключевых слов
@router.callback_query(F.data.startswith("delete_all_keywords_"))
async def delete_all_keywords(callback: types.CallbackQuery, state: FSMContext):
    telegram_id = str(callback.from_user.id)
    # Приостановка уведомления
    make_pause_notification(telegram_id)
    """Пользователь удаляет ключевые слова."""
    platform = callback.data.split("_")[-1]

    # логика сохранения в БД
    db_user_id = get_user_by_telegram_id(telegram_id).id
    db_filter_object = get_filter_by_user_id(db_user_id, platform)
    filter_query = db_filter_object.query
    json_query = safe_json_loads(filter_query)
    json_query["keywords"] = []
    json_query = json.dumps(json_query)
    edit_filter_query_by_user_id(db_user_id, platform, json_query)

    sent_message = await callback.message.answer(
        f"Ключевые слова удалены для {platform}!",
        reply_markup=back_to_platform_settings(platform)
    )
    await state.update_data(last_message_id=sent_message.message_id)


# Сохранение ключевых слов
@router.message(StateFilter(FilterSettings.waiting_keywords))
async def save_keywords(message: types.Message, state: FSMContext):
    telegram_id = str(message.from_user.id)
    """Сохранение ключевых слов в БД (заглушка)"""
    data = await state.get_data()
    platform = data.get("platform")
    keywords = [word.strip() for word in message.text.split(",")]

    # логика сохранения в БД
    db_user_id = get_user_by_telegram_id(telegram_id).id
    db_filter_object = get_filter_by_user_id(db_user_id, platform)
    filter_query = db_filter_object.query
    json_query = safe_json_loads(filter_query)
    if not json_query.get("keywords"):
        json_query["keywords"] = keywords
    else:
        json_query["keywords"] += keywords
    json_query = json.dumps(json_query)
    edit_filter_query_by_user_id(db_user_id, platform, json_query)

    sent_message = await message.answer(
        f"Ключевые слова сохранены для {platform}!",
        reply_markup=back_to_platform_settings(platform)
    )
    await state.update_data(last_message_id=sent_message.message_id)


# Добавление ключевых стоп слов
@router.callback_query(F.data.startswith("add_stopwords_"))
async def add_stopwords(callback: types.CallbackQuery, state: FSMContext):
    telegram_id = str(callback.from_user.id)
    # Приостановка уведомления
    make_pause_notification(telegram_id)
    """Пользователь добавляет стоп-слова."""
    platform = callback.data.split("_")[-1]
    await state.update_data(platform=platform)
    await state.set_state(FilterSettings.waiting_stopwords)

    # Очистка состояния через 5 минут
    remove_state_after_delay(telegram_id, state, callback.message.message_id)

    await callback.message.edit_text(
        "Введите стоп-слова через запятую (,):"
    )
    await callback.message.edit_reply_markup(reply_markup=back_to_platform_settings(platform))


# Удаление всех ключевых слов
@router.callback_query(F.data.startswith("delete_all_stop_keywords_"))
async def delete_all_keywords(callback: types.CallbackQuery, state: FSMContext):
    telegram_id = str(callback.from_user.id)
    # Приостановка уведомления
    make_pause_notification(telegram_id)
    """Пользователь удаляет ключевые слова."""
    platform = callback.data.split("_")[-1]

    # логика сохранения в БД
    db_user_id = get_user_by_telegram_id(telegram_id).id
    db_filter_object = get_filter_by_user_id(db_user_id, platform)
    filter_query = db_filter_object.query
    json_query = safe_json_loads(filter_query)
    json_query["stopkeywords"] = []
    json_query = json.dumps(json_query)
    edit_filter_query_by_user_id(db_user_id, platform, json_query)

    sent_message = await callback.message.answer(
        f"Ключевые стоп-слова удалены для {platform}!",
        reply_markup=back_to_platform_settings(platform)
    )
    await state.update_data(last_message_id=sent_message.message_id)


# Сохранение ключевых стоп слов
@router.message(StateFilter(FilterSettings.waiting_stopwords))
async def save_stopwords(message: types.Message, state: FSMContext):
    telegram_id = str(message.from_user.id)
    """Сохранение стоп-слов в БД (заглушка)"""
    data = await state.get_data()
    platform = data.get("platform")
    stopkeywords = [word.strip() for word in message.text.split(",")]

    # логика сохранения в БД
    db_user_id = get_user_by_telegram_id(telegram_id).id
    db_filter_object = get_filter_by_user_id(db_user_id, platform)
    filter_query = db_filter_object.query
    json_query = safe_json_loads(filter_query)
    if not json_query.get("stopkeywords"):
        json_query["stopkeywords"] = stopkeywords
    else:
        json_query["stopkeywords"] += stopkeywords
    json_query = json.dumps(json_query)
    edit_filter_query_by_user_id(db_user_id, platform, json_query)

    sent_message = await message.answer(
        f"Стоп-слова сохранены для {platform}!",
        reply_markup=back_to_platform_settings(platform)
    )
    await state.update_data(last_message_id=sent_message.message_id)


@router.callback_query(F.data.startswith("set_price_"))
async def set_price_range(callback: types.CallbackQuery, state: FSMContext):
    telegram_id = str(callback.from_user.id)
    # Приостановка уведомления
    make_pause_notification(telegram_id)
    """Пользователь указывает диапазон цен."""
    platform = callback.data.split("_")[-1]
    await state.update_data(platform=platform)
    await state.set_state(FilterSettings.waiting_price_range)

    # Очистка состояния через 5 минут

    await callback.message.edit_text(
        "Введите диапазон цен в валюте платформы: min-max (например, «100-1000»):"
    )
    await callback.message.edit_reply_markup(reply_markup=back_to_platform_settings(platform))


@router.message(StateFilter(FilterSettings.waiting_price_range))
async def save_price_range(message: types.Message, state: FSMContext):
    telegram_id = str(message.from_user.id)
    """Сохранение диапазона цен в БД (заглушка)"""
    data = await state.get_data()
    platform = data.get("platform")
    price_range = message.text.replace(" ", "").strip()

    # Проверка формата
    if not price_range.replace("-", "").isdigit():
        sent_message = await message.answer(
            "Неверный формат! Введите диапазон в формате: min-max (например, «100-1000»)",
            reply_markup=back_to_platform_settings(platform))
        await state.update_data(last_message_id=sent_message.message_id)
        return

    minprice, maxprice = price_range.split("-")

    db_user_id = get_user_by_telegram_id(telegram_id).id
    db_filter_object = get_filter_by_user_id(db_user_id, platform)
    filter_query = db_filter_object.query
    json_query = safe_json_loads(filter_query)
    json_query["minprice"] = minprice
    json_query["maxprice"] = maxprice
    json_query = json.dumps(json_query)
    edit_filter_query_by_user_id(db_user_id, platform, json_query)

    sent_message = await message.answer(
        f"Диапазон цен сохранен для {platform}!",
        reply_markup=back_to_platform_settings(platform)
    )
    await state.update_data(last_message_id=sent_message.message_id)


# Создание реф. ссылок
@router.message(Command('my_ref'))
async def get_ref(message: types.Message):
    telegram_id = str(message.from_user.id)
    user_object = get_user_by_telegram_id(telegram_id)
    if user_object is not None:
        link = await create_start_link(bot, telegram_id, encode=True)
        await bot.send_message(telegram_id, get_ref_link_message(link))
    else:
        await bot.send_message(telegram_id, f"Напиши /start")


@router.callback_query(F.data.startswith("translate|"))
async def show_language_buttons(callback: types.CallbackQuery):
    """Меняет клавиатуру на кнопки выбора языка."""
    message_id = callback.data.split("|")[1]
    order_db_id = callback.data.split("|")[2]

    order_object = get_task_by_id(order_db_id)
    if order_object is None:
        await bot.answer_callback_query(callback.id, text='Извините, действие невозможно.',
                                        show_alert=True)
        return

    order_url = order_object.direct_url

    buttons = [
        [InlineKeyboardButton(text=lang, callback_data=f"lang|{code}|{message_id}|{order_db_id}")]
        for lang, code in LANGUAGES.items()
    ]
    buttons.append([InlineKeyboardButton(text="Перейти к заказу", url=order_url)])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_reply_markup(reply_markup=keyboard)


@router.callback_query(F.data.startswith("lang|"))
async def translate_message(callback: types.CallbackQuery):
    """Переводит текст и заменяет сообщение."""
    _, lang_code, message_id, order_db_id = callback.data.split("|")

    order_object = get_task_by_id(order_db_id)
    if order_object is None:
        await bot.answer_callback_query(callback.id, text='Извините, действие невозможно.',
                                        show_alert=True)
        return

    order_url = order_object.direct_url

    original_text = callback.message.text
    translated_text = GoogleTranslator(source="auto", target=lang_code).translate(original_text)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"translate|{message_id}|{order_db_id}")],
        [InlineKeyboardButton(text="Перейти к заказу", url=order_url)]
    ])

    await callback.message.edit_text(translated_text, reply_markup=keyboard)


# q34phufgq34yf98q34fp98q3u4yf;8uq34fuq;3p48fuq983;04f
# Проверка актуалности подписки:
@router.message(Command('cancel_subs'))
async def get_statistic(message: types.Message):
    def cancel_sub(sub):
        exp_date = datetime.strptime(sub['datetime_expire'], DATETIME_FORMAT).replace(tzinfo=tz)
        now_date = datetime.now(tz) + timedelta(hours=1)
        if exp_date < now_date:
            return True
        return False

    user_id = message.from_user.id
    if str(user_id) not in ADMINS:
        await bot.send_message(user_id, get_wrong_command_message())
        return

    suc_cancel = 0
    fail_cancel = 0
    data = load_users()
    for usr_id, user_info in data.items():
        for subscription in user_info.get("subscriptions", []):
            if subscription["active"] is False:
                continue

            output = cancel_sub(subscription)
            if output is True:
                suc_cancel += 1
            elif output is False:
                fail_cancel += 1

    text = f"""
Отменены: {suc_cancel}
Активны: {fail_cancel}"""
    await bot.send_message(user_id, text)


# Статистика
@router.message(Command('statistic'))
async def get_statistic(message: types.Message):
    user_id = message.from_user.id
    if str(user_id) not in ADMINS:
        await bot.send_message(user_id, get_wrong_command_message())
        return
    # Переменные для подсчета
    total_users = 0
    try_period_users_total = 0
    try_period_users_today = 0
    paid_users_total = 0
    paid_users_today = 0
    empty_users = 0

    # Текущая дата для проверки
    today = date.today()

    # Данные о пользователях
    data = load_users()

    # Проходим по каждому пользователю
    for _, user_info in data.items():
        total_users += 1  # Считаем общего пользователя

        # Проверка на try_period
        if user_info.get("try_period", False):
            try_period_users_total += 1

            # Проверяем, если дата операции совпадает с сегодняшней датой
            for subscription in user_info.get("subscriptions", []):
                if subscription["subscription"] == "try_period":
                    operation_date = datetime.strptime(subscription["datetime_operation"], DATETIME_FORMAT).date()
                    if operation_date == today:
                        try_period_users_today += 1
                        break

        # Проверка на подписки
        if len(user_info.get("subscriptions", [])) > 0:
            paid_users_total_fl = False

            # Проверяем, была ли подписка оформлена сегодня
            for subscription in user_info["subscriptions"]:
                operation_date = datetime.strptime(subscription["datetime_operation"], DATETIME_FORMAT).date()
                if subscription["subscription"] != "try_period":
                    paid_users_total_fl = True
                    if operation_date == today:
                        paid_users_today += 1
                        break
            if paid_users_total_fl:
                paid_users_total += 1

        # Проверка на пустого пользователя
        if len(user_info.get("subscriptions", [])) == 0 and user_info.get("try_period", False) is False:
            empty_users += 1

    text = f"""Общая статистика:
1) Общее количество : {total_users}
2) Количество  с пробной подпиской (всего): {try_period_users_total}
3) Количество  с платной подпиской (всего): {paid_users_total}
4) Количество  с пробной подпиской (за сегодня): {try_period_users_today} 
5) Количество  с платной подпиской (за сегодня): {paid_users_today}
6) Количество пустых: {empty_users}"""

    # Вывод статистики
    await bot.send_message(chat_id=user_id, text=text)


# Эхо
@router.message()
async def send_welcome(message: types.Message, command: CommandObject = None):
    user_id = message.from_user.id

    await bot.send_message(user_id, text=message.text)


# Список доступных подписок
@router.callback_query(F.data == 'get_sub')
async def get_sub(call: CallbackQuery, state: FSMContext):
    user_sale = int(get_user_data(call.from_user.id).get('sale', 0))
    if TEST_PAYMETNS is not True or str(call.from_user.id) in ADMINS:
        await call.message.answer(text=get_subs_message(user_sale)[0], reply_markup=get_subs_keyboard(user_sale)[0])
        await call.message.answer(text=get_subs_message(user_sale)[1], reply_markup=get_subs_keyboard(user_sale)[1])
    else:
        await bot.send_message(call.from_user.id, text=get_service_working_message())
    await state.clear()


# Список доступных подписок
@router.message(Command('buy'))
async def buy_sub(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_sale = int(get_user_data(message.from_user.id).get('sale', 0))
    if TEST_PAYMETNS is not True or str(user_id) in ADMINS:
        await bot.send_message(chat_id=user_id, text=get_subs_message(user_sale)[0],
                               reply_markup=get_subs_keyboard(user_sale)[0])
        await bot.send_message(chat_id=user_id, text=get_subs_message(user_sale)[1],
                               reply_markup=get_subs_keyboard(user_sale)[1])
    else:
        await bot.send_message(user_id, text=get_service_working_message())
    await state.clear()


# Вывод подписок пользователя
@router.message(Command('my_subs'))
async def my_subs(message: types.Message):
    """

    :param message:
    :return:
    """
    user_data = get_user_data(message.from_user.id)
    if user_data is None:
        await bot.send_message(chat_id=message.from_user.id, text=get_empty_subscriptions_message())
    elif len(user_data['subscriptions']) > 0:
        active_subs = []
        inactive_subs = []
        subscriptions = user_data['subscriptions']
        for sub in subscriptions:
            status = sub.get('active')
            if status is True:
                active_subs.append(sub)
            else:
                inactive_subs.append(sub)
        await bot.send_message(chat_id=message.from_user.id,
                               text=get_actual_subscriptions_message(active_subs, inactive_subs),
                               reply_markup=get_active_subscriptions_keyboard(active_subs))
    else:
        await bot.send_message(chat_id=message.from_user.id, text=get_empty_subscriptions_message())


# Получение инфо-ии по конкретной подписке пользователя
@router.callback_query(F.data.startswith("get_info_"))
async def get_info(call: CallbackQuery, state: FSMContext):
    """

    :param call:
    :param state:
    :return:
    """
    try:
        pass
    except Exception:
        await wakeup_admins(f"Ошибка отправки данных пользователю panel_uuid={call.data[9:]} {call.from_user.id=}")
        traceback.print_exc()


# Сохранение данных о подписке
async def save_subscription(user_id, payment, notification, datetime_expire, panel_uuid, try_period=False):
    """
    :param try_period:
    :param user_id:
    :param payment:
    :param notification:
    :param datetime_expire:
    :param panel_uuid:
    :return:
    """
    try:
        user_data = get_user_data(user_id)
        if user_data is None:
            add_user(user_id, {
                'try_period': True if try_period else False,
                'subscriptions': [
                    {
                        'payment_id': notification.object.id if try_period is False else '-',
                        'subscription': payment['subscription'] if try_period is False else 'try_period',
                        'datetime_operation': datetime.now(tz).strftime(DATETIME_FORMAT),
                        'datetime_expire': datetime_expire.strftime(DATETIME_FORMAT),
                        'panel_uuid': panel_uuid,
                        'active': True
                    }
                ],
            })
        else:
            user_data['try_period'] = True if try_period else user_data['try_period']
            user_data['subscriptions'].append(
                {
                    'payment_id': notification.object.id if try_period is False else '-',
                    'subscription': payment['subscription'] if try_period is False else 'try_period',
                    'datetime_operation': datetime.now(tz).strftime(DATETIME_FORMAT),
                    'datetime_expire': datetime_expire.strftime(DATETIME_FORMAT),
                    'panel_uuid': panel_uuid,
                    'active': True
                }
            )
            save_user(user_id, user_data)
    except Exception:
        await wakeup_admins(f"Ошибка сохранения подписки (файл users.json) {user_id=} {panel_uuid=}")
        traceback.print_exc()


# Пробная подписка
@router.callback_query(F.data == "try_period")
async def process_try_period(call: CallbackQuery, state: FSMContext):
    """
    :param call:
    :param state:
    :return:
    """
    try:

        await state.clear()
    except Exception:
        await wakeup_admins(f"Ошибка cоздания триальной подписки {call.from_user.id=}")
        traceback.print_exc()


# Продление подписки
@router.callback_query(F.data.startswith("continue_"))
async def continue_subscribe(call: CallbackQuery, state: FSMContext):
    """

    :param call:
    :param state:
    :return:
    """
    try:
        if TEST_PAYMETNS is True and str(call.from_user.id) not in ADMINS:
            await bot.send_message(call.from_user.id, text=get_service_working_message())
            return

        panel_uuid = call.data[9:45]
        subscription = subscriptions.get(call.data[45:])
        user_id = call.from_user.id
        user_data = get_user_data(user_id)
        if user_data is not None and user_data.get('subscriptions') is not None:
            for sub in user_data['subscriptions']:
                if sub['panel_uuid'] == panel_uuid and sub['active'] is False:
                    await bot.send_message(user_id, text=get_continue_cancell_message(),
                                           reply_markup=get_cancel_keyboard())
                    return

        if subscription:
            fin_price = str(int(subscription['price'] * (100 - int(user_data['sale'])) / 100))
            payment = None

            await call.message.answer(text=get_pay_message(user_data['sale']),
                                      reply_markup=get_pay_keyboard(fin_price, payment.confirmation.confirmation_url))
        else:
            await call.message.answer("Неверная команда. Напишите /start")
        await state.clear()
    except Exception:
        await wakeup_admins(f"Ошибка продления подписки (платёж) {call.from_user.id=}")
        traceback.print_exc()


# Покупка подписки
@router.callback_query(F.data.startswith("month_") | F.data.startswith("year_") | F.data.startswith("testday_"))
async def process_subscribe(call: CallbackQuery, state: FSMContext):
    """

    :param call:
    :param state:
    :return:
    """
    try:
        user_id = call.from_user.id

        if TEST_PAYMETNS is True and str(user_id) not in ADMINS:
            await bot.send_message(user_id, text=get_service_working_message())
            return

        if count_active_subscriptions(user_id) >= ACTIVE_COUNT_SUB_LIMIT:
            await bot.send_message(user_id, text=get_subs_limit_message(ACTIVE_COUNT_SUB_LIMIT))
            return

        subscription = subscriptions.get(call.data)
        if subscription:

            user_data = get_user_data(user_id)

            fin_price = str(int(subscription['price'] * (100 - int(user_data['sale'])) / 100))

            payment = None

            await call.message.answer(text=get_pay_message(user_data['sale']), reply_markup=get_pay_keyboard(fin_price,
                                                                                                             payment.confirmation.confirmation_url))
        else:
            await call.message.answer("Неверная команда. Напишите /start")
        await state.clear()
    except Exception:
        await wakeup_admins(f"Ошибка создания подписки (платёж) {call.from_user.id=}")
        traceback.print_exc()


# Создание нового клиента в 3xui
async def create_new_client(user_id, payment, notification):
    """

    :param user_id:
    :param payment:
    :param notification:
    :return:
    """
    try:
        pass
    except Exception as e:
        await wakeup_admins(f"Ошибка при создании клиента {user_id=} {notification.object.id=}")
        traceback.print_exc()


# Обработчик webhook для платежной системы
async def payment_webhook_handler(request):
    try:
        pass
    except Exception as e:
        traceback.print_exc()
        await wakeup_admins(f"Ошибка обработки webhook: {str(e)}")
        logging.error(f"Error processing payment webhook: {str(e)}")
        return web.Response(status=500)


# Обработчик команды /alert
@router.message(Command("alert"))
async def alert_handler(message: Message):
    # Проверяем, является ли пользователь администратором
    user_id = message.from_user.id
    if str(user_id) not in ADMINS:
        await bot.send_message(user_id, get_wrong_command_message())
        return

    # Получаем текст сообщения из команды
    alert_text = message.text.split(" ", 1)
    if len(alert_text) < 2:
        await message.reply("❗ Используйте команду в формате: /alert <текст>")
        return

    message_text = alert_text[1]

    # Подтверждение начала рассылки
    await message.reply("✅ Начинаю рассылку...")

    # Запускаем массовую рассылку
    success_count, failed_count = await broadcast_message(message_text)

    # Отправляем отчет об успешности рассылки
    await message.reply(f"📢 Рассылка завершена!\n✅ Успешно: {success_count}\n❌ Ошибки: {failed_count}")


# Функция для отправки массового сообщения
async def broadcast_message(message_text: str):
    users = get_users_id()
    success_count = 0
    failed_count = 0

    for user_id in users:
        try:
            await bot.send_message(chat_id=user_id, text=message_text)
            success_count += 1
        except Exception as e:
            print(f"Ошибка при отправке пользователю {user_id}: {e}")
            failed_count += 1

        # Делаем небольшую паузу, чтобы избежать ограничений API Telegram
        await asyncio.sleep(0.05)

    return success_count, failed_count


async def pause_notification(telegram_id):
    """
    Приостанавливает уведомления на 3 минуты
    """
    r.delete(telegram_id)


def make_pause_notification(telegram_id):
    # Создаём задержку на уведомления на 3 минуты для удобства пользователя
    if r.exists(telegram_id):
        jobs = scheduler.get_jobs()
        for job in jobs:
            if job.kwargs["telegram_id"] == telegram_id:
                scheduler.remove_job(job.id)
    else:
        r.set(telegram_id, "1")
    scheduler.add_job(
        pause_notification,
        trigger=DateTrigger(run_date=datetime.now() + timedelta(minutes=3)),
        kwargs={"telegram_id": telegram_id}
    )


async def on_startup(*args, **kwargs) -> None:
    webhook_url = f"{BASE_WEBHOOK_URL}{BOT_WEBHOOK_PATH}"
    webhook_info = await bot.get_webhook_info()
    print(webhook_info)
    if webhook_info.url != webhook_url:
        await bot.set_webhook(
            url=webhook_url,
        )


async def local_startup(*args, **kwargs) -> None:
    await bot.delete_webhook()
    time.sleep(3)
    await dp.start_polling(bot)


async def main():
    # Создание базы данных (если нужно)

    # БД для бота
    telegram_bot.db_engine.create_database()

    # БД для парсера
    create_database()

    # Запуск шедулера
    scheduler.start()

    # Список задач
    tasks = []

    if mode == "local":
        dp.include_router(router)  # Подключаем роутеры
        task_1 = asyncio.create_task(local_startup())  # Локальный режим запуска
        tasks.append(task_1)
    else:
        # Middleware для ограничения
        dp.include_router(router)
        dp.message.middleware(ThrottlingMiddleware(redis.Redis(host='localhost', port=6379, db=1)))

        dp.startup.register(on_startup)

        # Настройка веб-сервера
        app = web.Application()
        # app.router.add_post(PAYMENT_WEBHOOK_PATH, payment_webhook_handler)

        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )
        # Регистрация обработчиков
        webhook_requests_handler.register(app, path=BOT_WEBHOOK_PATH)

        # Настройка вебхуков
        setup_application(app, dp, bot=bot)

        # Generate SSL context
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile=WEBHOOK_SSL_CERT, keyfile=WEBHOOK_SSL_PRIV)

        # Запуск веб-приложения
        return await web._run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)

    # Запуск всех задач параллельно
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
