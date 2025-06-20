# Добавление названий товаров в систему поиска

## Проделанные изменения

### 1. Расширение базы данных
- ✅ Добавлена колонка `product_name` в таблицу `products`
- ✅ Загружены названия товаров из 4-й колонки CSV файла
- ✅ Обновлено 6445 из 6447 товаров (99.97% покрытие)

### 2. Обновление сервиса поиска
**Файл:** `services/department_search_service.py`
- ✅ Все SQL запросы обновлены для выборки `product_name`
- ✅ Результаты поиска теперь включают названия товаров
- ✅ Текстовый поиск теперь работает и по URL и по названию товара

### 3. Обновление интерфейса бота
**Файл:** `handlers/photo_handler.py`
- ✅ Результаты поиска показывают название товара
- ✅ Формат: `📦 Название: {название товара}`
- ✅ Название отображается между артикулом и отделом

### 4. Настройка main.py
**Файл:** `toolbot/main.py` уже правильно настроен:
- ✅ Импортирует обработчики из корневого `handlers/photo_handler.py`
- ✅ Регистрирует все необходимые обработчики
- ✅ Поддерживает выбор отделов и поиск по фото

## Структура базы данных (обновленная)

```sql
CREATE TABLE products (
    item_id TEXT PRIMARY KEY,
    url TEXT,
    picture TEXT,
    vector BLOB,
    department TEXT,          -- добавлено ранее
    product_name TEXT         -- добавлено сейчас
);
```

## Примеры названий товаров

- `10337184`: КЛЕЙ МОМЕНТ КРИСТАЛЛ 30 МЛ (КРАСКИ)
- `11348600`: УГОЛЬНИК ПП D32 90ГР. (ВОДОСНАБЖЕНИЕ)
- `83237447`: ЛАК LUXENS НА АЛКИД.ОСНОВЕ. ГЛЯНЕЦ 520МЛ (КРАСКИ)

## Запуск бота

Бот запускается через:
```bash
python run_bot.py
```

Который автоматически использует правильно настроенный `toolbot/main.py`.

## Как это работает

1. **Поиск по фото:**
   - Пользователь загружает фото
   - Выбирает отдел или "все отделы" 
   - Получает результаты с названиями товаров

2. **Отображение результатов:**
   ```
   ✅ Результат 1 - Отличное совпадение
   📊 Схожесть: 85%
   🏷️ Артикул: 83237447
   📦 Название: ЛАК LUXENS НА АЛКИД.ОСНОВЕ. ГЛЯНЕЦ 520МЛ
   🏪 Отдел: КРАСКИ
   🌐 Ссылка: [ссылка на товар]
   ```

## Результат

Теперь пользователи видят:
- ✅ Артикул товара
- ✅ **Название товара** (новое!)
- ✅ Отдел товара
- ✅ Прямую ссылку на товар
- ✅ Процент схожести

Это значительно улучшает пользовательский опыт, так как теперь не нужно переходить по ссылке, чтобы узнать, что за товар найден. 