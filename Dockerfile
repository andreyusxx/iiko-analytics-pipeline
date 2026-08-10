# Використовуємо легку офіційну версію Python
FROM python:3.11-slim

# Робоча директорія всередині контейнера
WORKDIR /app

# Копіюємо файл залежностей та встановлюємо їх
COPY requirements-bot.txt .
RUN pip install --no-cache-dir -r requirements-bot.txt 

# Копіюємо весь решту коду проєкту
COPY . .

# Команда для запуску бота
CMD ["python", "bot.py"]