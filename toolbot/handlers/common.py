"""
Общие обработчики команд для телеграм-бота.
"""
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

# Импортируем исправленную функцию из utils/access.py
from toolbot.utils.access import is_allowed_user

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /start - показывает главное меню
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or "пользователь"
    
    # Логируем использование команды
    analytics = context.bot_data.get('analytics')
    if analytics:
        analytics.log_command("start", user_id)
    
    # Проверяем, есть ли пользователь в белом списке
    if not is_allowed_user(user_id):
        await update.message.reply_text(
            f"⛔ <b>Доступ запрещен</b>\n\n"
            f"Ваш ID: <code>{user_id}</code>\n\n"
            f"Для получения доступа обратитесь к администратору.",
            parse_mode='HTML'
        )
        return
    
    # Формируем клавиатуру для главного меню
    keyboard = [
        ["📞 Контакты", "📸 Поиск по фото"],
        ["❓ Помощь"]
    ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Отправляем приветственное сообщение
    await update.message.reply_text(
        f"👋 Добро пожаловать, {username}!\n\n"
        f"Выберите нужный раздел с помощью кнопок меню:\n"
        f"• 📞 Контакты - информация о магазинах\n"
        f"• 📸 Поиск по фото - поиск товаров по изображению\n"
        f"• ❓ Помощь - информация о боте\n\n"
        f"💡 <i>Для начала работы нажмите на кнопку в меню</i>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /help - показывает справочную информацию
    """
    user_id = update.effective_user.id
    
    # Логируем использование команды
    analytics = context.bot_data.get('analytics')
    if analytics:
        analytics.log_command("help", user_id)
    
    # Проверяем, есть ли пользователь в белом списке
    if not is_allowed_user(user_id):
        await show_error_message(update, "access_denied")
        return
    
    # Формируем текст справки
    help_text = (
        "*❓ СПРАВОЧНАЯ ИНФОРМАЦИЯ ПО БОТУ*\n\n"
        "*О БОТЕ:*\n"
        "Данный Telegram-бот разработан для упрощения поиска строительных товаров и инструментов. "
        "С его помощью вы можете найти нужный товар по фото, получить информацию о магазинах, "
        "ознакомиться с каталогом скобяных изделий и многое другое.\n\n"
        
        "*ОСНОВНЫЕ КОМАНДЫ:*\n"
        "• /start - запуск бота и возврат в главное меню\n"
        "• /help - вызов этой справки\n"
        "• /stop - отмена текущей операции\n\n"
        
        "*ОСНОВНЫЕ РАЗДЕЛЫ:*\n"
        "• 📞 *Контакты* - доступ к информации о магазинах, логистике и другим контактным данным\n"
        "• 📸 *Поиск по фото* - поиск товаров с помощью фотографии\n"
        "• ❓ *Помощь* - данная справка\n\n"
        
        "*РАЗДЕЛ КОНТАКТЫ:*\n"
        "• 🏪 *Магазины* - адреса и контакты магазинов\n"
        "• 🗺 *Карты* - расположение объектов на карте\n"
        "• 🔧 *Скобянка* - справочник по скобяным изделиям\n\n"
        
        "*ПОИСК ПО ФОТО:*\n"
        "Эта функция позволяет искать товары, сфотографировав их. Для использования:\n"
        "1. Нажмите кнопку 📸 *Поиск по фото*\n"
        "2. Выберите отдел, в котором нужно искать товар\n"
        "3. Сделайте четкую фотографию товара и отправьте боту\n"
        "4. Дождитесь результатов поиска\n\n"
        
        "*СОВЕТЫ ПО ИСПОЛЬЗОВАНИЮ:*\n"
        "• Для лучшего распознавания делайте фото при хорошем освещении\n"
        "• Старайтесь держать камеру параллельно товару\n"
        "• Избегайте теней и бликов на фотографии\n"
        "• Если не получаете нужные результаты, попробуйте выбрать другой отдел или сделать фото с другого ракурса\n\n"
        
        "*НАВИГАЦИЯ:*\n"
        "• Используйте кнопки на клавиатуре для переходов между разделами\n"
        "• Кнопка 🔙 *Назад в меню* возвращает в главное меню из любого раздела\n"
        "• Команда /stop отменяет текущую операцию\n\n"
        
        "*ОБРАТНАЯ СВЯЗЬ:*\n"
        "• Используйте кнопки ниже для связи с разработчиками\n"
        "• Сообщайте об ошибках для улучшения работы бота\n"
        "• Предлагайте новые функции и улучшения\n\n"
        
        "💡 Мы всегда готовы помочь и улучшить работу бота!"
    )
    
    # Создаем клавиатуру с кнопками обратной связи
    keyboard = [
        ["🐛 Сообщить об ошибке", "💡 Предложить улучшение"],
        ["🔙 Назад в меню"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Показываем справку
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def stop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /stop - отменяет текущую операцию и возвращается в главное меню
    """
    user_id = update.effective_user.id
    
    # Логируем использование команды
    analytics = context.bot_data.get('analytics')
    if analytics:
        analytics.log_command("stop", user_id)
    
    # Сбрасываем все состояния пользователя
    if 'state' in context.user_data:
        del context.user_data['state']
    
    if 'awaiting_photo' in context.user_data:
        context.user_data['awaiting_photo'] = False
    
    # Отправляем сообщение
    await update.message.reply_text(
        "✅ Текущая операция отменена. Возвращаемся в главное меню.",
        reply_markup=ReplyKeyboardMarkup([
            ["📞 Контакты", "📸 Поиск по фото"],
            ["❓ Помощь"]
        ], resize_keyboard=True)
    )


async def back_to_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик возврата в главное меню
    """
    user_id = update.effective_user.id
    
    # Логируем использование команды
    analytics = context.bot_data.get('analytics')
    if analytics:
        analytics.log_command("back_to_menu", user_id)
    
    # Сбрасываем все состояния
    if 'state' in context.user_data:
        del context.user_data['state']
    if 'awaiting_photo' in context.user_data:
        context.user_data['awaiting_photo'] = False
    if 'selected_department' in context.user_data:
        del context.user_data['selected_department']
    
    # Вызываем обработчик команды /start для показа главного меню
    await start_handler(update, context)


async def show_error_message(update: Update, error_type="general"):
    """
    Показывает сообщение об ошибке в зависимости от типа
    
    Args:
        update: Объект Update от телеграма
        error_type: Тип ошибки (access_denied, invalid_command, general)
    """
    error_messages = {
        "access_denied": "⛔ *Доступ запрещен*\n\nВы не имеете доступа к этому боту.\nПожалуйста, обратитесь к администратору.",
        "invalid_command": "❌ *Неизвестная команда*\n\nВведенная команда не распознана.\nИспользуйте меню для навигации.",
        "general": "❌ *Произошла ошибка*\n\nПожалуйста, попробуйте еще раз или обратитесь к администратору."
    }
    
    message = error_messages.get(error_type, error_messages["general"])
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown'
    ) 