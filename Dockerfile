# Используем официальный образ Python (полный)
FROM joyzoursky/python-chromedriver:3.9

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем переменные окружения
ENV PYTHONPATH=/app:$PYTHONPATH
ENV DISPLAY=:99

# Копируем зависимости перед проектом для кэширования слоёв
COPY requirements.txt .

# Установка зависимостей системы (включая curl и библиотеки для Google Chrome)
RUN apt-get update && apt-get install -y --no-install-recommends xvfb

RUN apt-get clean

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Команда для запуска (пример)
# CMD ["python", "main.py"]
