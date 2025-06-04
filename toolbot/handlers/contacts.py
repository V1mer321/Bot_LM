"""
Обработчики команд для раздела контактов телеграм-бота.
"""
import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from toolbot.utils.access import is_allowed_user

logger = logging.getLogger(__name__)


async def contacts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик для раздела контактов
    """
    user_id = update.effective_user.id
    
    if not is_allowed_user(user_id):
        from toolbot.handlers.common import show_error_message
        await show_error_message(update, "access_denied")
        return
    
    # Логируем использование команды
    analytics = context.bot_data.get('analytics')
    if analytics:
        analytics.log_command("contacts", user_id)
    
    # Создаем клавиатуру для раздела контактов
    keyboard = [
        ["🏪 Магазины"],
        ["🗺 Карты", "🔧 Скобянка"],
        ["🔙 Назад в меню"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Отправляем сообщение с меню
    await update.message.reply_text(
        "*📞 Контакты и информация*\n\n"
        "Выберите нужный раздел:\n"
        "• 🏪 Магазины - адреса и телефоны магазинов\n"
        "• 🗺 Карты - расположение объектов на карте\n"
        "• 🔧 Скобянка - каталог скобяных изделий\n\n"
        "💡 _Используйте кнопки для навигации_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def back_to_contacts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик возврата в раздел контактов
    """
    await contacts_handler(update, context)


async def stores_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик для раздела магазинов
    """
    user_id = update.effective_user.id
    
    if not is_allowed_user(user_id):
        from toolbot.handlers.common import show_error_message
        await show_error_message(update, "access_denied")
        return
    
    # Логируем использование команды
    analytics = context.bot_data.get('analytics')
    if analytics:
        analytics.log_command("stores", user_id)
    
    # Создаем клавиатуру только для возврата
    keyboard = [["🔙 Назад в контакты"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Устанавливаем состояние поиска магазинов
    context.user_data['state'] = 'searching_stores'
    
    # Отправляем сообщение с инструкцией по поиску
    await update.message.reply_text(
        "*🏪 Поиск по таблице*\n\n"
        "Введите наименование или отдел для поиска.\n"
        "Поиск выполняется по частичному совпадению текста.\n\n"
        "💡 _Пример: исп_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def maps_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик для раздела карт
    """
    user_id = update.effective_user.id
    
    if not is_allowed_user(user_id):
        from toolbot.handlers.common import show_error_message
        await show_error_message(update, "access_denied")
        return
    
    # Логируем использование команды
    analytics = context.bot_data.get('analytics')
    if analytics:
        analytics.log_command("maps", user_id)
    
    # Создаем клавиатуру для возврата
    keyboard = [["🔙 Назад в контакты"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Отправляем сообщение
    await update.message.reply_text(
        "*🗺 Карты*\n\n"
        "В разработке. Скоро здесь появятся интерактивные карты с расположением магазинов и складов.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def skobyanka_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик для раздела скобянки
    """
    user_id = update.effective_user.id
    
    if not is_allowed_user(user_id):
        from toolbot.handlers.common import show_error_message
        await show_error_message(update, "access_denied")
        return
    
    # Логируем использование команды
    analytics = context.bot_data.get('analytics')
    if analytics:
        analytics.log_command("skobyanka", user_id)
    
    # Устанавливаем состояние поиска скобянки
    context.user_data['state'] = 'searching_skobyanka'
    
    # Создаем клавиатуру для возврата
    keyboard = [["🔙 Назад в контакты"], ["🔙 Назад в меню"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Отправляем сообщение
    await update.message.reply_text(
        "*🔧 Каталог скобяных изделий*\n\n"
        "Введите поисковый запрос для поиска в каталоге скобяных изделий.\n"
        "Поиск выполняется по частичному совпадению текста.\n"
        "Можно искать по:\n"
        "• Наименованию\n"
        "• Артикулу\n"
        "• Размеру\n"
        "• Другим параметрам\n\n"
        "💡 _Пример: винт 5_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    ) 