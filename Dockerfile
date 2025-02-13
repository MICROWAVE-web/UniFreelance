# Используем официальный образ Python (полный)
FROM python:3.13

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем переменные окружения
ENV PYTHONPATH=/app:$PYTHONPATH
ENV DISPLAY=:99

# Копируем зависимости перед проектом для кэширования слоёв
COPY requirements.txt .

# Установка зависимостей системы (включая curl и библиотеки для Google Chrome)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    unzip \
    x11vnc \
    xvfb \
    curl \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libvulkan1 \
    libxcomposite1 \
    libxkbcommon0 \
    xdg-utils && \
    rm -rf /var/lib/apt/lists/*

# Добавляем репозиторий Google Chrome и устанавливаем его
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | \
    gpg --no-default-keyring --keyring gnupg-ring:/etc/apt/trusted.gpg.d/google.gpg --import; \
    chmod 644 /etc/apt/trusted.gpg.d/google.gpg; \
    echo "deb http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Устанавливаем Google Chrome
RUN curl -LO https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем Flower
RUN pip install flower

# Копируем весь проект
COPY . .

# Команда для запуска (пример)
# CMD ["python", "main.py"]
