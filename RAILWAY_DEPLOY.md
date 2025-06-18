# 🚀 Развертывание бота на Railway

## Подготовка проекта

### 1. Файлы созданы для Railway:
- `Dockerfile` - контейнер Docker
- `railway.json` - конфигурация Railway
- `requirements-railway.txt` - оптимизированные зависимости
- `railway_start.py` - упрощенный запуск
- `env.example` - пример переменных окружения

### 2. Настройка GitHub репозитория

```bash
# Добавляем файлы в git
git add .
git commit -m "Подготовка для развертывания на Railway"
git push origin main
```

## Развертывание на Railway

### 1. Создание аккаунта
- Перейдите на [railway.app](https://railway.app)
- Войдите через GitHub аккаунт

### 2. Создание проекта
1. Нажмите "New Project"
2. Выберите "Deploy from GitHub repo"
3. Выберите ваш репозиторий с ботом
4. Railway автоматически обнаружит Dockerfile

### 3. Настройка переменных окружения

В разделе Variables добавьте:

**Обязательные:**
```
BOT_TOKEN=ваш_токен_бота_здесь
```

**Опциональные:**
```
ADMIN_IDS=123456789,987654321
LOG_LEVEL=INFO
DISABLE_ANALYTICS=false
USE_POLLING=true
```

### 4. Развертывание
- Railway автоматически начнет сборку
- Процесс займет 3-5 минут
- Логи сборки будут видны в реальном времени

## Проверка работы

### 1. Логи
- Перейдите в раздел "Deployments"
- Проверьте логи на наличие ошибок
- Должно появиться сообщение "🚀 Запуск бота на Railway..."

### 2. Тестирование бота
- Напишите боту в Telegram
- Проверьте основные команды

## Мониторинг

### Статистика Railway
- CPU/RAM использование
- Логи в реальном времени
- Метрики сети

### Перезапуск
```bash
# Через интерфейс Railway или API
railway service restart
```

## Устранение неполадок

### Частые проблемы:

1. **"BOT_TOKEN not found"**
   - Проверьте переменные окружения
   - Убедитесь что токен корректный

2. **"Memory limit exceeded"**
   - Проверьте `requirements-railway.txt`
   - Убедитесь что тяжелые зависимости исключены

3. **"Build failed"**
   - Проверьте Dockerfile
   - Проверьте логи сборки

### Оптимизация:

1. **Скорость запуска:**
   - Используйте `railway_start.py`
   - Отключите ненужные функции

2. **Потребление памяти:**
   - Мониторьте через Railway Dashboard
   - Оптимизируйте imports

## Ограничения бесплатного плана

- **CPU:** Shared
- **RAM:** 512MB
- **Время работы:** 500 часов/месяц
- **Сеть:** 100GB исходящего трафика

## Альтернативные команды

### Локальный тест Docker образа:
```bash
docker build -t my-bot .
docker run -e BOT_TOKEN=your_token my-bot
```

### Railway CLI:
```bash
npm install -g @railway/cli
railway login
railway deploy
``` 