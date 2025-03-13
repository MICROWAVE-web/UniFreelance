# UniFreelance

UniFreelance - это парсер фриланс-заказов с различных платформ. Позволяет собирать и анализировать заказы, а также работать с базой данных.


Удобный телеграм бот с настройкой подборки для каждой биржи реализуется фильтрами, которые задаёт пользователь

## Функциональность

- Сбор заказов с фриланс-платформ
- Обработка данных с использованием Celery
- Сохранение данных в базу
- Возможность развертывания через Docker

## Используемые технологии

- **Python 3.8+**
- **Celery** - для фоновых задач
- **PostgreSQL / SQLite** - база данных
- **Docker** - контейнеризация
- **BeautifulSoup** - парсинг данных
- **Aiogram & pyTelegramBotAPI** - Телеграмм бот
- 
## Установка

1. Клонируйте репозиторий:

   ```bash
   git clone https://github.com/yourusername/UniFreelance.git
   cd UniFreelance
   ```

2. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```

## Запуск

### Без Docker

```bash
python parser/run_parser.py
```

### С Docker

```bash
docker-compose up --build
```

## Файлы проекта

- `run_parser.py` - основной файл парсинга
- `celery_worker.py` - обработка задач Celery
- `db_engine.py` - работа с базой данных
- `utilities.py` - вспомогательные утилиты
- `Dockerfile` - контейнеризация
- `docker-compose.yml` - запуск через Docker

## Требования

- Python 3.8+
- Docker (если используется контейнеризация)
- PostgreSQL (если используется в качестве базы)
