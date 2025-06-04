# Dockerfile для ToolBot
# Многоэтапная сборка для оптимизации размера образа

# Stage 1: Базовый образ с Python и основными зависимостями
FROM python:3.10-slim AS base

# Установка необходимых системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Создание и установка рабочей директории
WORKDIR /app

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Образ для моделей и инференса
FROM base AS models

# Установка дополнительных системных зависимостей для ONNX Runtime и других библиотек ML
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Установка ONNX Runtime и другие зависимости для машинного обучения
RUN pip install --no-cache-dir onnxruntime-gpu torch torchvision

# Создание директории для моделей
RUN mkdir -p /app/toolbot/models/optimized

# Скрипт для загрузки моделей при первом запуске
COPY toolbot/docker/download_models.sh /app/
RUN chmod +x /app/download_models.sh
RUN /app/download_models.sh

# Stage 3: Финальный образ для приложения
FROM base AS final

# Копирование оптимизированных моделей из предыдущего этапа
COPY --from=models /app/toolbot/models /app/toolbot/models

# Копирование кода приложения
COPY . /app/

# Установка переменных окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PRODUCTION=1

# Создание не-root пользователя для запуска приложения
RUN useradd -m tooluser
RUN chown -R tooluser:tooluser /app
USER tooluser

# Добавление метаданных контейнера
LABEL maintainer="Lemana Pro Team"
LABEL version="1.0"
LABEL description="Lemana Pro ToolBot for B2B department"

# Проверка здоровья контейнера
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys, socket; \
                  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); \
                  s.connect(('localhost', 8000)); \
                  s.close(); \
                  sys.exit(0)"

# Запуск приложения
CMD ["python", "toolbot/main.py"]

# Определяем порты, если есть
EXPOSE 8000 