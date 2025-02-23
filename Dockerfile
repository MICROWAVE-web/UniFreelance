FROM python:3.9-slim

# Установка зависимостей
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    xvfb \
    fluxbox \
    x11vnc \
    apt-transport-https \
    ca-certificates \
    gnupg

# Добавление репозитория Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list'

# Установка Google Chrome
RUN apt-get update && apt-get install -y google-chrome-stable

# Установка undetected-chromedriver
RUN pip install undetected-chromedriver

# Копирование вашего приложения
COPY . /app
WORKDIR /app

ENV PYTHONPATH=/app
# Установка зависимостей Python
RUN pip install -r requirements.txt

# Установка переменных окружения
ENV DISPLAY=:0

# Запуск Xvfb и Fluxbox
CMD Xvfb :0 -screen 0 1920x1080x24 & fluxbox & x11vnc -passwd password -N -forever -rfbport 5900 & python main.py
