from datetime import timedelta

subscriptions = {
    # Подписка для тестирования
    'testday_1': {'name': 'UniFreelance на день (тестовая подписка)', 'price': 20, 'period': timedelta(days=1),
                  'devices': 1},

    # Планы
    'try_period': {'name': 'UniFreelance на день', 'price': 0, 'period': timedelta(days=2),
                   'devices': 1},
    'month': {'name': 'UniFreelance на месяц', 'price': 990, 'period': timedelta(days=31),
                'devices': 1},
    'year': {'name': 'UniFreelance на год', 'price': 9990, 'period': timedelta(days=365),
               'devices': 1},
}