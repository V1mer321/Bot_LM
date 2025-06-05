# 🤖 ToolBot - Интеллектуальный Telegram Бот

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.7+-red.svg)](https://pytorch.org)
[![ONNX](https://img.shields.io/badge/ONNX-Runtime-green.svg)](https://onnxruntime.ai)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)

**ToolBot** - современный Telegram бот с возможностями машинного обучения, визуального поиска и интеллектуального анализа изображений.

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
git clone <repository-url>
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

### Отладка
```bash
# Запуск с подробным логированием
LOG_LEVEL=DEBUG python run_bot.py

# Проверка зависимостей
python -c "import torch, transformers, faiss; print('OK')"
```

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте ветку для новой функции: `git checkout -b feature/amazing-feature`
3. Сделайте commit: `git commit -m 'Add amazing feature'`
4. Push в ветку: `git push origin feature/amazing-feature`
5. Создайте Pull Request

## 📄 Лицензия

Этот проект лицензирован под [MIT License](LICENSE).

## 📞 Поддержка

- **Issues**: [GitHub Issues](../../issues)
- **Documentation**: См. папку `docs/`
- **Community**: [Telegram канал](https://t.me/your_channel)

## 🔧 Последние обновления (v2.0.2)

### ✅ Исправленные проблемы
- **🐛 Критические ошибки форматирования**: Исправлены все ошибки `impossible<bad format char>` в f-строках
- **🔧 Проблемы с отступами**: Устранены `IndentationError` во всех модулях
- **⚡ Стабилизация мониторинга**: Улучшена надежность системы мониторинга производительности
- **🛡️ Обработка ошибок**: Улучшена обработка `None` значений в системе логирования

### 🆕 Новые возможности
- **📊 Расширенный мониторинг**: Добавлены новые метрики и алерты
- **🎯 Улучшенная точность**: Оптимизированы алгоритмы поиска и обработки
- **🔒 Повышенная надежность**: Улучшена система восстановления после сбоев

### 🔧 Технические улучшения
- Исправлено форматирование процентов во всех f-строках (`%` → `%%`)
- Улучшена обработка `strftime()` в f-строках
- Стандартизированы отступы во всех Python файлах
- Оптимизирована система логирования для повышения производительности

---

**Автор**: ToolBot Development Team  
**Версия**: 2.0.2  
**Последнее обновление**: 5 июня 2025
