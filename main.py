#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from handlers.photo_handler import handle_photo, handle_department_selection, get_database_stats
from services.unified_database_search import UnifiedDatabaseService

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = "7655889200:AAGuXvXkz7Rk4zULnGj5gQxGtOGGH2eKZvU"

async def start(update: Update, context):
    """Обработчик команды /start"""
    welcome_message = """
🤖 Привет! Я бот для поиска товаров по фотографии!

📸 Отправьте мне фотографию товара, и я найду похожие позиции в нашем каталоге.

🔍 Функции:
• Поиск по изображению с высокой точностью
• Отображение процента схожести
• Быстрый доступ к товарам
• Распределение по отделам

💡 Просто отправьте фото и получите результаты!
"""
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context):
    """Обработчик команды /help"""
    help_text = """
🔍 **Как пользоваться ботом:**

1. 📸 Отправьте фотографию товара
2. ⏳ Дождитесь результатов поиска
3. 📊 Просмотрите найденные товары с процентом схожести
4. 🔗 Перейдите на страницу товара или выберите отдел

**Отделы товаров:**
• 🧱 Строительные материалы
• 🪑 Столярные изделия
• ⚡ Электрика
• 🔧 Сантехника  
• 🎨 Краски и лаки
• 🔩 Крепёж и метизы
• 🚪 Двери, окна
• 🏠 Кровля
• 🛠️ Инструмент
• 🧽 Хозтовары

**Команды:**
/start - Начать работу
/help - Показать справку
/stats - Статистика базы данных
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context):
    """Статистика базы данных"""
    try:
        stats = await get_database_stats()
        
        stats_text = f"""
📊 **Статистика базы данных:**

📦 Всего товаров: {stats['total_products']}
🖼️ Товаров с изображениями: {stats['products_with_vectors']}
⚡ Готовность к поиску: {(stats['products_with_vectors']/stats['total_products']*100):.1f}%

🔍 База данных обновлена для максимальной точности поиска
"""
        await update.message.reply_text(stats_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await update.message.reply_text("❌ Ошибка при получении статистики базы данных")

async def handle_text(update: Update, context):
    """Обработчик текстовых сообщений"""
    await update.message.reply_text(
        "📸 Отправьте мне фотографию товара для поиска похожих позиций!\n"
        "Или используйте /help для получения справки."
    )

def main():
    """Основная функция запуска бота"""
    try:
        # Проверяем наличие единой БД
        if not os.path.exists('data/unified_products.db'):
            print("❌ Единая база данных не найдена!")
            print("Запустите create_unified_database.py для создания БД")
            return
        
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("stats", stats_command))
        
        # Обработчик фотографий
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        
        # Обработчик текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        # Обработчик callback-запросов (для кнопок)
        application.add_handler(CallbackQueryHandler(handle_department_selection))
        
        # Проверяем подключение к unified database service
        try:
            unified_service = UnifiedDatabaseService()
            stats = unified_service.get_database_stats()
            print(f"✅ Подключение к единой БД успешно!")
            print(f"📦 Товаров в БД: {stats['total_products']}")
            print(f"🖼️ С векторами: {stats['products_with_vectors']}")
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            return
        
        print("🚀 Бот запущен с единой базой данных!")
        print("📊 Точность поиска повышена благодаря обновленным векторам")
        
        # Запускаем бота
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"❌ Критическая ошибка при запуске: {e}")

if __name__ == '__main__':
    main() 