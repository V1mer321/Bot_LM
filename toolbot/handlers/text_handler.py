"""
Обработчики текстовых сообщений для телеграм-бота.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from toolbot.config import is_allowed_user, is_admin  # Используем зашифрованную конфигурацию (безопасно)
from toolbot.handlers.admin import process_admin_text_input
from toolbot.services.data_service import search_in_colors, search_in_stores, search_in_skobyanka
from services.text_logging_service import get_text_logging_service

logger = logging.getLogger(__name__)


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик текстовых сообщений
    
    Args:
        update: Объект Update от телеграма
        context: Контекст бота
    """
    user_id = update.effective_user.id
    text = update.message.text
    username = update.effective_user.username or "пользователь"
    first_name = update.effective_user.first_name or ""
    last_name = update.effective_user.last_name or ""
    chat_id = update.effective_chat.id
    
    # Получаем состояние пользователя
    user_state = context.user_data.get('state', 'none')
    
    # Определяем тип сообщения
    message_type = 'text'
    if text.startswith('/'):
        message_type = 'command'
    elif user_state and 'admin' in user_state:
        message_type = 'admin_input'
    elif user_state and 'search' in user_state:
        message_type = 'search_query'
    elif user_state and 'feedback' in user_state:
        message_type = 'feedback'
    elif user_state and 'broadcast' in user_state:
        message_type = 'broadcast_input'
    
    # Логируем в SQLite базу (ПОЛНЫЙ ТЕКСТ)
    try:
        text_logger = get_text_logging_service()
        text_logger.log_text_message(
            user_id=user_id,
            message_text=text,
            username=username,
            first_name=first_name,
            last_name=last_name,
            chat_id=chat_id,
            message_type=message_type,
            is_admin=is_admin(user_id),
            user_state=user_state
        )
    except Exception as e:
        logger.error(f"❌ Ошибка при логировании текста в SQLite: {e}")
    
    # Логируем текстовое сообщение от пользователя в аналитику (кроме чувствительных данных)
    analytics = context.bot_data.get('analytics')
    if analytics:
        # Логируем только первые 50 символов для безопасности в аналитику
        text_preview = text[:50] + "..." if len(text) > 50 else text
        analytics.log_user_activity(user_id, "text_message", f"@{username}: {text_preview}")
    
    # Сначала пытаемся обработать административные запросы (ПЕРЕД проверкой доступа)
    # Это позволяет админам добавлять пользователей
    if await process_admin_text_input(update, context):
        return
    
    # Проверяем, есть ли пользователь в белом списке
    if not is_allowed_user(user_id):
        from toolbot.handlers.common import show_error_message
        await show_error_message(update, "access_denied")
        return
    
    # Проверяем текущее состояние пользователя
    state = context.user_data.get('state')
    
    # Обработка состояний обратной связи
    if state == 'awaiting_error_report':
        # Обрабатываем сообщение об ошибке
        from toolbot.handlers.feedback_handlers import process_error_report
        await process_error_report(update, context)
        return
    elif state == 'awaiting_improvement_suggestion':
        # Обрабатываем предложение по улучшению
        from toolbot.handlers.feedback_handlers import process_improvement_suggestion
        await process_improvement_suggestion(update, context)
        return
    
    # Логируем использование текстового поиска (только если не обратная связь)
    analytics = context.bot_data.get('analytics')
    if analytics:
        analytics.log_command("text_search", user_id)
    
    # Обработка по состояниям поиска
    if state == 'searching_colors':
        await process_colors_search(update, context, text)
    elif state == 'searching_stores':
        await process_stores_search(update, context, text)
    elif state == 'searching_skobyanka':
        await process_skobyanka_search(update, context, text)
    else:
        # Неизвестное состояние, показываем сообщение об ошибке
        await update.message.reply_text(
            "❓ Не понимаю вашего запроса. Пожалуйста, используйте меню для навигации."
        )


async def process_colors_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
    """
    Обработчик поиска по цветам
    
    Args:
        update: Объект Update от телеграма
        context: Контекст бота
        query: Поисковый запрос
    """
    results = await search_in_colors(query)
    
    if results:
        # Отправляем найденные результаты
        for i, result in enumerate(results[:10]):  # Ограничиваем до 10 результатов
            await update.message.reply_text(
                result,
                parse_mode='Markdown'
            )
            
        if len(results) > 10:
            await update.message.reply_text(
                f"🔍 Найдено ещё {len(results) - 10} результатов. Уточните запрос для более конкретных результатов."
            )
    else:
        await update.message.reply_text(
            "❌ Ничего не найдено. Попробуйте другой запрос."
        )


async def process_stores_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
    """
    Обработчик поиска по магазинам
    
    Args:
        update: Объект Update от телеграма
        context: Контекст бота
        query: Поисковый запрос
    """
    results = await search_in_stores(query)
    
    if results:
        await update.message.reply_text(
            f"*🏪 Результаты поиска по запросу:* '{query}'\n",
            parse_mode='Markdown'
        )
        
        # Отправляем найденные результаты
        for i, result in enumerate(results[:10]):  # Ограничиваем до 10 результатов
            await update.message.reply_text(
                result,
                parse_mode='Markdown'
            )
            
        if len(results) > 10:
            await update.message.reply_text(
                f"🔍 Найдено ещё {len(results) - 10} результатов. Уточните запрос для более точных результатов."
            )
    else:
        await update.message.reply_text(
            "❌ Ничего не найдено по вашему запросу. Попробуйте изменить поисковый запрос."
        )


async def process_skobyanka_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
    """
    Обработчик поиска по скобянке
    
    Args:
        update: Объект Update от телеграма
        context: Контекст бота
        query: Поисковый запрос
    """
    results = await search_in_skobyanka(query)
    
    if results:
        await update.message.reply_text(
            f"*🔧 Результаты поиска в скобянке по запросу:* '{query}'\n",
            parse_mode='Markdown'
        )
        
        # Отправляем найденные результаты
        for i, result in enumerate(results[:10]):  # Ограничиваем до 10 результатов
            await update.message.reply_text(
                result,
                parse_mode='Markdown'
            )
            
        if len(results) > 10:
            await update.message.reply_text(
                f"🔍 Найдено ещё {len(results) - 10} результатов. Уточните запрос для более точных результатов."
            )
    else:
        await update.message.reply_text(
            "❌ Ничего не найдено по вашему запросу. Попробуйте изменить поисковый запрос."
        ) 