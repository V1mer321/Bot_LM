# 🤖 ToolBot - Интеллектуальный Telegram Бот

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.7+-red.svg)](https://pytorch.org)
[![ONNX](https://img.shields.io/badge/ONNX-Runtime-green.svg)](https://onnxruntime.ai)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)

**ToolBot** - современный Telegram бот с возможностями машинного обучения, визуального поиска и интеллектуального анализа изображений.

## 🚀 Развертывание на Railway

### Быстрый деплой
1. Форкните этот репозиторий
2. Зайдите на [railway.app](https://railway.app)
3. Подключите GitHub репозиторий
4. Добавьте переменную `BOT_TOKEN`
5. Деплой запустится автоматически!

📖 **Подробная инструкция**: [RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md)

## 🚀 Основные возможности

### 🔍 **Визуальный поиск**
- Поиск товаров по изображению с использованием CLIP модели
- Распознавание объектов с помощью YOLO и EfficientDet
- Семантический поиск с векторной базой данных FAISS

### 🛠️ **ML/AI возможности**
- Оптимизированные модели: MobileNetV3, EfficientDet-Lite
- Поддержка ONNX Runtime для быстрого инференса
- Автоматическое кэширование результатов

### 📊 **Аналитика и мониторинг**
- Система логирования и error tracking
- Мониторинг производительности и восстановления
- Аналитика использования бота
- **🕒 Real-time мониторинг** - системный дашборд с метриками CPU, RAM, GPU
- **🚨 Система алертов** - автоматическое уведомление о критических состояниях
- **📈 История метрик** - отслеживание производительности во времени

## 📋 Требования

### Системные требования
- **Python**: 3.13+
- **ОС**: Windows 10/11, Linux, macOS
- **RAM**: минимум 4GB, рекомендуется 8GB+
- **CPU**: поддержка AVX2 для FAISS

### Основные зависимости
```
torch>=2.2.0
transformers>=4.37.0
python-telegram-bot>=20.7
faiss-cpu>=1.7.4
onnxruntime>=1.15.1
ultralytics>=8.0.0
```

## ⚡ Быстрый старт

### 1. Клонирование репозитория
```bash
git clone https://github.com/V1mer321/Bot_LM.git
cd Bot_LM
```

### 2. Создание виртуального окружения
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Настройка конфигурации
Создайте файл `config.py` или `.env` с настройками:
```python
TELEGRAM_BOT_TOKEN = "your_bot_token_here"
ADMIN_USER_ID = your_admin_id
```

### 5. Запуск бота
```bash
python run_bot.py
```

## 🏗️ Архитектура проекта

```
Bot_LM/
├── toolbot/                 # Основной модуль бота
│   ├── handlers/           # Обработчики команд и сообщений
│   ├── services/           # Бизнес-логика и сервисы
│   ├── utils/              # Утилиты и вспомогательные модули
│   └── data/               # Данные и конфигурации
├── services/               # Внешние сервисы
├── handlers/               # Дополнительные обработчики
├── data/                   # Базы данных и индексы
├── logs/                   # Файлы логов
├── cache/                  # Кэшированные данные
└── requirements.txt        # Зависимости Python
```

## 🔧 Настройка для разработки

### PyCharm
1. Откройте проект в PyCharm
2. **File → Settings → Project → Python Interpreter**
3. Выберите интерпретатор: `venv/Scripts/python.exe` (Windows) или `venv/bin/python` (Linux/macOS)

### VS Code/Cursor
1. Откройте проект
2. Выберите интерпретатор Python: `Ctrl+Shift+P` → "Python: Select Interpreter"
3. Выберите из виртуального окружения `venv`

## 📊 Использование

### Основные команды бота
- `/start` - Запуск бота и приветствие
- `/help` - Справка по командам
- `/search` - Поиск по изображению
- `/stats` - Статистика использования
- `/admin` - Административные функции (только для админов)
- `/monitoring` - Real-time системный мониторинг
- `/performance` - Статистика производительности
- `/reliability` - Надежность и состояние компонентов

### Поиск по изображению
1. Отправьте изображение боту
2. Бот автоматически обработает изображение
3. Получите результаты поиска с похожими товарами

## 🛠️ Конфигурация

### Основные настройки (`config.py`)
```python
# Telegram Bot
TELEGRAM_BOT_TOKEN = "your_token"
ADMIN_USER_ID = 123456789

# ML модели
USE_GPU = False
ONNX_PROVIDERS = ["CPUExecutionProvider"]
CACHE_SIZE = 1000

# База данных
DATABASE_PATH = "data/products.db"
SEARCH_INDEX_PATH = "data/faiss_index"
```

### Переменные окружения (`.env`)
```env
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_USER_ID=123456789
DEBUG=False
LOG_LEVEL=INFO
```

## 🔍 Система поиска

### Алгоритм поиска
1. **Предобработка изображения** - изменение размера, нормализация
2. **Извлечение признаков** - CLIP модель для векторизации
3. **Поиск в индексе** - FAISS для быстрого поиска схожих векторов
4. **Постобработка** - фильтрация и ранжирование результатов

### Настройка точности
- `similarity_threshold` - порог схожести (по умолчанию 0.7)
- `top_k` - количество результатов (по умолчанию 5)
- `use_reranking` - переранжирование результатов

## 📈 Мониторинг и логирование

### Системы логирования
- **Основные логи**: `bot.log`
- **Ошибки**: автоматическое отслеживание и уведомления
- **Аналитика**: статистика использования в `data/analytics.json`

### Мониторинг производительности
- Использование памяти и CPU
- Время ответа API
- Скорость обработки изображений

## 🚨 Устранение проблем

### Частые проблемы

#### 1. ModuleNotFoundError: No module named 'torch'
**Решение**: Установите зависимости в правильное виртуальное окружение
```bash
pip install -r requirements.txt
```

#### 2. ONNX Runtime ошибки
**Решение**: Проверьте совместимость версий
```bash
pip install onnxruntime --upgrade
```

#### 3. FAISS ошибки на Windows
**Решение**: Установите Visual C++ Redistributable

#### 4. Telegram API ошибки
**Решение**: Проверьте токен бота и сетевое подключение

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл [LICENSE](LICENSE) для получения дополнительной информации.

## 🤝 Участие в разработке

Приветствуются любые предложения по улучшению! Создавайте issues и pull requests.

## 👥 Авторы

- **V1mer321** - Основной разработчик
- Telegram: [@your_telegram]

## 🙏 Благодарности

- OpenAI за модель CLIP
- Meta за модели FAISS
- Ultralytics за YOLO
- Сообщество Python за отличные библиотеки
