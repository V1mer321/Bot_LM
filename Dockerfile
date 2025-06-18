# Используем Python 3.11 slim для лучшей производительности
FROM python:3.11-slim

# Устанавливаем системные зависимости (минимальные)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgl1-mesa-glx \
    libglib2.0-0 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем оптимизированные зависимости
COPY requirements-railway.txt requirements.txt

# Устанавливаем Python зависимости с оптимизацией для Railway
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем папки для логов и кэша
RUN mkdir -p logs cache temp

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV DISABLE_GPU=1
ENV USE_SIMPLE_SEARCH=1

# Экспонируем порт для healthcheck
EXPOSE 8000

# Команда запуска с новым скриптом
CMD ["python", "railway_start.py"] 