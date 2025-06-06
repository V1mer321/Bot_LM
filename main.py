#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from handlers.photo_handler import (
    handle_photo, handle_department_selection, get_database_stats,
    handle_correct_feedback, handle_incorrect_feedback, 
    handle_new_item_request, handle_specify_correct_item,
    handle_text_message
)
from handlers.admin_training_handler import (
    admin_training_stats_command, admin_start_training_command,
    admin_view_examples_command, admin_manage_new_products_command,
    admin_model_backups_command, handle_admin_callback
)
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

async def admin_help_command(update: Update, context):
    """Обработчик команды /admin_help - справка для администраторов"""
    user_id = update.effective_user.id
    
    # Проверяем права администратора (можно вынести в отдельную функцию)
    from handlers.admin_training_handler import is_admin
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав администратора")
        return
    
    admin_help_text = """🔧 Справка для администраторов

👑 Административные команды:
/admin_help - Эта справка
/admin_training_stats - Статистика дообучения
/admin_start_training - Запуск дообучения модели
/admin_view_examples - Просмотр обучающих примеров
/admin_new_products - Управление новыми товарами
/admin_model_backups - Управление резервными копиями моделей

🧠 Система дообучения:
• Накопите 20+ примеров для начального дообучения
• Рекомендуется 50+ примеров для качественного результата
• Следите за балансом положительных/отрицательных примеров
• Проводите дообучение регулярно (раз в неделю при активном использовании)

📊 Мониторинг:
• Проверяйте статистику обучающих данных
• Отслеживайте точность модели после дообучения
• Одобряйте новые товары от пользователей
• Следите за качеством обучающих примеров

⚠️ Важно:
• Дообучение может занимать несколько минут
• Бот будет недоступен во время обучения
• Сохраняйте резервные копии моделей"""
    
    await update.message.reply_text(admin_help_text)

async def help_command(update: Update, context):
    """Обработчик команды /help"""
    help_text = """🔍 Как пользоваться ботом:

1. 📸 Отправьте фотографию товара
2. ⏳ Дождитесь результатов поиска
3. 📊 Просмотрите найденные товары с процентом схожести
4. 🔗 Перейдите на страницу товара или выберите отдел

Отделы товаров:
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

Команды:
/start - Начать работу
/help - Показать справку
/stats - Статистика базы данных

🧠 Помогайте улучшать поиск:
• ✅/❌ Оценивайте качество найденных товаров
• ➕ Предлагайте новые товары для каталога
• 🎯 Указывайте правильные товары при неточном поиске
• 📝 Оставляйте комментарии для улучшения системы"""
    await update.message.reply_text(help_text)

async def stats_command(update: Update, context):
    """Статистика базы данных"""
    try:
        stats = await get_database_stats()
        
        stats_text = f"""📊 Статистика базы данных:

📦 Всего товаров: {stats['total_products']}
🖼️ Товаров с изображениями: {stats['products_with_vectors']}
⚡ Готовность к поиску: {(stats['products_with_vectors']/stats['total_products']*100):.1f}%

🔍 База данных обновлена для максимальной точности поиска"""
        await update.message.reply_text(stats_text)
        
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
        
        # Административные команды для дообучения
        application.add_handler(CommandHandler("admin_help", admin_help_command))
        application.add_handler(CommandHandler("admin_training_stats", admin_training_stats_command))
        application.add_handler(CommandHandler("admin_start_training", admin_start_training_command))
        application.add_handler(CommandHandler("admin_view_examples", admin_view_examples_command))
        application.add_handler(CommandHandler("admin_new_products", admin_manage_new_products_command))
        application.add_handler(CommandHandler("admin_model_backups", admin_model_backups_command))
        
        # Обработчик фотографий
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        
        # Обработчик текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        # Обработчик callback-запросов (для кнопок)
        def create_callback_handler():
            async def callback_router(update: Update, context):
                query = update.callback_query
                if query.data.startswith("correct_"):
                    await handle_correct_feedback(update, context)
                elif query.data.startswith("incorrect_"):
                    await handle_incorrect_feedback(update, context)
                elif query.data.startswith("new_item_"):
                    await handle_new_item_request(update, context)
                elif query.data.startswith("specify_correct_"):
                    await handle_specify_correct_item(update, context)
                elif query.data.startswith("admin_"):
                    await handle_admin_callback(update, context)
                else:
                    await handle_department_selection(update, context)
            return callback_router
        
        application.add_handler(CallbackQueryHandler(create_callback_handler()))
        
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