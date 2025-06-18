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
    handle_text_message, photo_search_handler, department_selection_handler,
    back_to_departments_handler
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
    from telegram import ReplyKeyboardMarkup
    
    # ИСПРАВЛЕНИЕ: Добавляем главное меню с кнопкой поиска по фото
    keyboard = [
        ["📸 Поиск по фото"],
        ["📊 Статистика БД", "ℹ️ Помощь"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_message = """
🤖 Привет! Я бот для поиска товаров по фотографии!

📸 Нажмите "Поиск по фото", выберите отдел и отправьте фотографию товара - я найду похожие позиции в каталоге.

🔍 Функции:
• Поиск по изображению с высокой точностью
• Фильтрация по отделам для лучших результатов
• Отображение процента схожести
• Быстрый доступ к товарам

💡 Сначала выберите отдел, затем отправьте фото!
"""
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

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
4. ✅ Оцените результаты с помощью кнопок
5. 🔗 Перейдите на страницу товара или выберите отдел

🎯 После каждого поиска используйте кнопки:
• ✅ Правильно - если найден нужный товар
• ❌ Неточно - если результат не подходит
• ➕ Добавить товар - предложить новый товар в каталог

🏪 Отделы товаров:
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

📋 Команды:
/start - Начать работу
/help - Показать справку
/stats - Статистика базы данных

🧠 Ваши оценки помогают улучшать поиск:
• Бот запоминает ваши предпочтения
• Качество поиска постоянно улучшается
• Каталог товаров расширяется благодаря вашим предложениям
• Чем больше оценок - тем точнее результаты!"""
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
        
        # ИСПРАВЛЕНИЕ: Добавляем обработчики для выбора отделов
        # Обработчик кнопки "📸 Поиск по фото"
        application.add_handler(MessageHandler(filters.Text("📸 Поиск по фото"), photo_search_handler))
        
        # Обработчики выбора отделов (должны быть ПЕРЕД общим обработчиком текста)
        application.add_handler(MessageHandler(filters.Text("🔍 Поиск по всем отделам"), department_selection_handler))
        application.add_handler(MessageHandler(filters.Text("🛠️ ИНСТРУМЕНТЫ"), department_selection_handler))
        application.add_handler(MessageHandler(filters.Text("🎨 КРАСКИ"), department_selection_handler))
        application.add_handler(MessageHandler(filters.Text("🚰 САНТЕХНИКА"), department_selection_handler))
        application.add_handler(MessageHandler(filters.Text("🧱 СТРОЙМАТЕРИАЛЫ"), department_selection_handler))
        application.add_handler(MessageHandler(filters.Text("🏠 НАПОЛЬНЫЕ ПОКРЫТИЯ"), department_selection_handler))
        application.add_handler(MessageHandler(filters.Text("🌿 САД"), department_selection_handler))
        application.add_handler(MessageHandler(filters.Text("💡 СВЕТ"), department_selection_handler))
        application.add_handler(MessageHandler(filters.Text("⚡ ЭЛЕКТРОТОВАРЫ"), department_selection_handler))
        application.add_handler(MessageHandler(filters.Text("🏠 ОТДЕЛОЧНЫЕ МАТЕРИАЛЫ"), department_selection_handler))
        application.add_handler(MessageHandler(filters.Text("🚿 ВОДОСНАБЖЕНИЕ"), department_selection_handler))
        application.add_handler(MessageHandler(filters.Text("🔩 СКОБЯНЫЕ ИЗДЕЛИЯ"), department_selection_handler))
        application.add_handler(MessageHandler(filters.Text("🗄️ ХРАНЕНИЕ"), department_selection_handler))
        application.add_handler(MessageHandler(filters.Text("🏠 СТОЛЯРНЫЕ ИЗДЕЛИЯ"), department_selection_handler))
        application.add_handler(MessageHandler(filters.Text("🍽️ КУХНИ"), department_selection_handler))
        application.add_handler(MessageHandler(filters.Text("🏢 ПЛИТКА"), department_selection_handler))
        
        # Обработчики возврата к выбору отдела
        application.add_handler(MessageHandler(filters.Text("🔙 Назад к выбору отдела"), back_to_departments_handler))
        application.add_handler(MessageHandler(filters.Text("🔙 Назад в меню"), start))
        
        # Обработчики кнопок главного меню
        application.add_handler(MessageHandler(filters.Text("📊 Статистика БД"), stats_command))
        application.add_handler(MessageHandler(filters.Text("ℹ️ Помощь"), help_command))
        
        # Обработчик остальных текстовых сообщений (должен быть ПОСЛЕДНИМ)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        # Обработчик callback-запросов (для кнопок)
        def create_callback_handler():
            async def callback_router(update: Update, context):
                query = update.callback_query
                logger.info(f"🔍 Получен callback: {query.data} от пользователя {query.from_user.id}")
                
                if query.data.startswith("correct_"):
                    logger.info("➡️ Направляем в handle_correct_feedback")
                    await handle_correct_feedback(update, context)
                elif query.data.startswith("incorrect_"):
                    logger.info("➡️ Направляем в handle_incorrect_feedback")
                    await handle_incorrect_feedback(update, context)
                elif query.data.startswith("new_item_"):
                    logger.info("➡️ Направляем в handle_new_item_request")
                    await handle_new_item_request(update, context)
                elif query.data.startswith("specify_correct_"):
                    logger.info("➡️ Направляем в handle_specify_correct_item")
                    await handle_specify_correct_item(update, context)
                elif query.data.startswith("search_dept_"):
                    logger.info("➡️ Направляем в handle_department_selection (поиск по отделу)")
                    await handle_department_selection(update, context)
                elif query.data.startswith("admin_") or query.data.startswith("fill_product_data_") or query.data.startswith("reject_product_"):
                    logger.info("➡️ Направляем в handle_admin_callback")
                    await handle_admin_callback(update, context)
                else:
                    logger.info("➡️ Направляем в handle_department_selection")
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