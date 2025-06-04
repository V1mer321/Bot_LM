"""
Обработчики для системы обратной связи
"""
import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler

# Добавляем путь к корневым сервисам
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from services.feedback_database import get_feedback_service
from toolbot.utils.access import is_allowed_user
from toolbot.config import is_admin

logger = logging.getLogger(__name__)

async def report_error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик кнопки 'Сообщить об ошибке'
    """
    user_id = update.effective_user.id
    
    if not is_allowed_user(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return
    
    # Устанавливаем состояние ожидания сообщения об ошибке
    context.user_data["state"] = "awaiting_error_report"
    
    # Создаем клавиатуру для отмены
    keyboard = [["❌ Отмена"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🐛 **Сообщить об ошибке**\n\n"
        "Опишите проблему, с которой вы столкнулись:\n\n"
        "📝 **Что включить в описание:**\n"
        "• Что вы пытались сделать\n"
        "• Что произошло вместо ожидаемого\n"
        "• При каких условиях возникла ошибка\n"
        "• Скриншоты (если возможно)\n\n"
        "💡 Чем подробнее описание, тем быстрее мы сможем решить проблему!",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def suggest_improvement_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик кнопки 'Предложить улучшение'
    """
    user_id = update.effective_user.id
    
    if not is_allowed_user(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return
    
    # Устанавливаем состояние ожидания предложения
    context.user_data["state"] = "awaiting_improvement_suggestion"
    
    # Создаем клавиатуру для отмены
    keyboard = [["❌ Отмена"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "💡 **Предложить улучшение**\n\n"
        "Поделитесь своими идеями по улучшению бота:\n\n"
        "🎯 **Что можно предложить:**\n"
        "• Новые функции и возможности\n"
        "• Улучшения интерфейса\n"
        "• Оптимизации работы поиска\n"
        "• Дополнительные разделы\n"
        "• Улучшения удобства использования\n\n"
        "🚀 Ваши идеи помогают нам делать бота лучше!",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def process_error_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает сообщение об ошибке от пользователя
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or f"User_{user_id}"
    message = update.message.text
    
    if not is_allowed_user(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return
    
    try:
        # Сохраняем сообщение об ошибке в БД
        feedback_service = get_feedback_service()
        report_id = feedback_service.add_error_report(user_id, username, message)
        
        # Сбрасываем состояние
        context.user_data["state"] = None
        
        # Возвращаемся к главному меню
        keyboard = [
            ["📞 Контакты", "📸 Поиск по фото"],
            ["❓ Помощь"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"✅ **Сообщение об ошибке получено**\n\n"
            f"🎫 Номер обращения: **#{report_id}**\n\n"
            f"📋 Ваше сообщение передано администраторам и будет рассмотрено в ближайшее время.\n\n"
            f"💬 При необходимости с вами свяжутся для уточнения деталей.\n\n"
            f"🙏 Спасибо за то, что помогаете улучшать работу бота!",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # Уведомляем администраторов
        await notify_admins_about_feedback(context, 'error', report_id, username, message)
        
        # Логируем
        analytics = context.bot_data.get('analytics')
        if analytics:
            analytics.log_command("error_report", user_id)
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении сообщения об ошибке: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при отправке сообщения. Попробуйте позже."
        )

async def process_improvement_suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает предложение по улучшению от пользователя
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or f"User_{user_id}"
    message = update.message.text
    
    if not is_allowed_user(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return
    
    try:
        # Сохраняем предложение в БД
        feedback_service = get_feedback_service()
        suggestion_id = feedback_service.add_improvement_suggestion(user_id, username, message)
        
        # Сбрасываем состояние
        context.user_data["state"] = None
        
        # Возвращаемся к главному меню
        keyboard = [
            ["📞 Контакты", "📸 Поиск по фото"],
            ["❓ Помощь"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"✅ **Предложение принято**\n\n"
            f"🎫 Номер предложения: **#{suggestion_id}**\n\n"
            f"💡 Ваша идея принята к рассмотрению! Мы обязательно изучим ваше предложение.\n\n"
            f"🚀 Если предложение будет реализовано, мы вас обязательно уведомим.\n\n"
            f"🙏 Спасибо за активное участие в развитии бота!",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # Уведомляем администраторов
        await notify_admins_about_feedback(context, 'suggestion', suggestion_id, username, message)
        
        # Логируем
        analytics = context.bot_data.get('analytics')
        if analytics:
            analytics.log_command("improvement_suggestion", user_id)
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении предложения: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при отправке предложения. Попробуйте позже."
        )

async def cancel_feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик отмены ввода обратной связи
    """
    # Сбрасываем состояние
    context.user_data["state"] = None
    
    # Возвращаемся к главному меню
    keyboard = [
        ["📞 Контакты", "📸 Поиск по фото"],
        ["❓ Помощь"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "❌ Отменено. Возвращаемся в главное меню.",
        reply_markup=reply_markup
    )

async def notify_admins_about_feedback(context: ContextTypes.DEFAULT_TYPE, feedback_type: str, 
                                     feedback_id: int, username: str, message: str) -> None:
    """
    Уведомляет администраторов о новой обратной связи
    """
    try:
        # Импортируем конфигурацию для получения списка админов
        from toolbot.config import get_admin_ids
        admin_ids = get_admin_ids()
        
        # Экранируем HTML символы
        safe_username = username.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        safe_message = message[:500].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        if len(message) > 500:
            safe_message += '...'
        
        if feedback_type == 'error':
            emoji = "🐛"
            title = "Новое сообщение об ошибке"
            notification = (
                f"{emoji} <b>{title}</b>\n\n"
                f"🎫 <b>Номер:</b> #{feedback_id}\n"
                f"👤 <b>От:</b> @{safe_username}\n"
                f"📝 <b>Сообщение:</b>\n{safe_message}\n\n"
                f"📋 Используйте админ-панель для просмотра всех обращений."
            )
        else:  # suggestion
            emoji = "💡"
            title = "Новое предложение по улучшению"
            notification = (
                f"{emoji} <b>{title}</b>\n\n"
                f"🎫 <b>Номер:</b> #{feedback_id}\n"
                f"👤 <b>От:</b> @{safe_username}\n"
                f"📝 <b>Предложение:</b>\n{safe_message}\n\n"
                f"📋 Используйте админ-панель для просмотра всех предложений."
            )
        
        # Отправляем уведомления всем администраторам
        for admin_id in admin_ids:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=notification,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление админу {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомлений админам: {e}")

async def view_feedback_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает статистику обратной связи (только для админов)
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Эта команда доступна только администраторам")
        return
    
    try:
        feedback_service = get_feedback_service()
        stats = feedback_service.get_statistics()
        
        stats_text = (
            "<b>📊 Статистика обратной связи</b>\n\n"
            
            "<b>🐛 Сообщения об ошибках:</b>\n"
            f"• Всего: {stats['total_errors']}\n"
            f"• Новых: {stats['new_errors']}\n"
            f"• Решено: {stats['resolved_errors']}\n\n"
            
            "<b>💡 Предложения по улучшению:</b>\n"
            f"• Всего: {stats['total_suggestions']}\n"
            f"• Новых: {stats['new_suggestions']}\n"
            f"• Реализовано: {stats['implemented_suggestions']}\n\n"
            
            "📋 Используйте кнопки ниже для просмотра деталей."
        )
        
        await update.message.reply_text(
            stats_text,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await update.message.reply_text("❌ Ошибка при получении статистики")

async def view_errors_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает последние сообщения об ошибках (только для админов)
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Эта команда доступна только администраторам")
        return
    
    try:
        feedback_service = get_feedback_service()
        errors = feedback_service.get_error_reports(limit=5)  # Уменьшаем количество для лучшего отображения
        
        if not errors:
            await update.message.reply_text("📋 Нет сообщений об ошибках")
            return
        
        await update.message.reply_text("<b>🐛 Последние сообщения об ошибках:</b>", parse_mode='HTML')
        
        for error in errors:
            status_emoji = "🟢" if error['status'] == 'решено' else "🔴" if error['status'] == 'новый' else "🟡"
            
            # Экранируем HTML символы
            username = error['username'] or 'Unknown'
            message_preview = error['message'][:200]  # Увеличиваем превью
            if len(error['message']) > 200:
                message_preview += '...'
            
            # Экранируем HTML символы
            username = username.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            message_preview = message_preview.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            status = error['status'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            text = (
                f"{status_emoji} <b>Ошибка #{error['id']}</b>\n"
                f"👤 От: @{username}\n"
                f"📅 {error['timestamp']}\n"
                f"🏷️ Статус: {status}\n\n"
                f"📝 <b>Сообщение:</b>\n{message_preview}"
            )
            
            # Создаем инлайн кнопки для управления
            keyboard = []
            
            # Кнопки для изменения статуса (только если не решено)
            if error['status'] != 'решено':
                status_buttons = []
                if error['status'] != 'в работе':
                    status_buttons.append(InlineKeyboardButton("🟡 В работе", callback_data=f"error_status_{error['id']}_в_работе"))
                status_buttons.append(InlineKeyboardButton("🟢 Решено", callback_data=f"error_status_{error['id']}_решено"))
                keyboard.append(status_buttons)
            
            # Кнопка показать полное сообщение
            keyboard.append([InlineKeyboardButton("📖 Полное сообщение", callback_data=f"error_full_{error['id']}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        
    except Exception as e:
        logger.error(f"Ошибка при получении сообщений об ошибках: {e}")
        await update.message.reply_text("❌ Ошибка при получении данных")

async def view_suggestions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает последние предложения по улучшению (только для админов)
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Эта команда доступна только администраторам")
        return
    
    try:
        feedback_service = get_feedback_service()
        suggestions = feedback_service.get_improvement_suggestions(limit=5)  # Уменьшаем количество
        
        if not suggestions:
            await update.message.reply_text("📋 Нет предложений по улучшению")
            return
        
        await update.message.reply_text("<b>💡 Последние предложения по улучшению:</b>", parse_mode='HTML')
        
        for suggestion in suggestions:
            status_emoji = "🟢" if suggestion['status'] == 'реализовано' else "🔴" if suggestion['status'] == 'новый' else "🟡"
            priority_emoji = "🔥" if suggestion['priority'] == 'критический' else "⚠️" if suggestion['priority'] == 'высокий' else "⭐" if suggestion['priority'] == 'средний' else "📝"
            
            # Экранируем HTML символы
            username = suggestion['username'] or 'Unknown'
            message_preview = suggestion['message'][:200]  # Увеличиваем превью
            if len(suggestion['message']) > 200:
                message_preview += '...'
            
            # Экранируем HTML символы
            username = username.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            message_preview = message_preview.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            status = suggestion['status'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            priority = suggestion['priority'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            text = (
                f"{status_emoji} <b>Предложение #{suggestion['id']}</b> {priority_emoji}\n"
                f"👤 От: @{username}\n"
                f"📅 {suggestion['timestamp']}\n"
                f"🏷️ Статус: {status} | Приоритет: {priority}\n\n"
                f"💡 <b>Предложение:</b>\n{message_preview}"
            )
            
            # Создаем инлайн кнопки для управления
            keyboard = []
            
            # Кнопки для изменения статуса (только если не реализовано)
            if suggestion['status'] != 'реализовано':
                status_buttons = []
                if suggestion['status'] != 'в работе':
                    status_buttons.append(InlineKeyboardButton("🟡 В работе", callback_data=f"suggestion_status_{suggestion['id']}_в_работе"))
                status_buttons.append(InlineKeyboardButton("🟢 Реализовано", callback_data=f"suggestion_status_{suggestion['id']}_реализовано"))
                keyboard.append(status_buttons)
            
            # Кнопки для изменения приоритета
            priority_buttons = []
            if suggestion['priority'] != 'критический':
                priority_buttons.append(InlineKeyboardButton("🔥 Критический", callback_data=f"suggestion_priority_{suggestion['id']}_критический"))
            if suggestion['priority'] != 'высокий':
                priority_buttons.append(InlineKeyboardButton("⚠️ Высокий", callback_data=f"suggestion_priority_{suggestion['id']}_высокий"))
            if suggestion['priority'] != 'средний':
                priority_buttons.append(InlineKeyboardButton("⭐ Средний", callback_data=f"suggestion_priority_{suggestion['id']}_средний"))
            if suggestion['priority'] != 'обычный':
                priority_buttons.append(InlineKeyboardButton("📝 Обычный", callback_data=f"suggestion_priority_{suggestion['id']}_обычный"))
            
            # Разбиваем кнопки приоритета по 2 в ряд
            if priority_buttons:
                for i in range(0, len(priority_buttons), 2):
                    keyboard.append(priority_buttons[i:i+2])
            
            # Кнопка показать полное сообщение
            keyboard.append([InlineKeyboardButton("📖 Полное предложение", callback_data=f"suggestion_full_{suggestion['id']}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        
    except Exception as e:
        logger.error(f"Ошибка при получении предложений: {e}")
        await update.message.reply_text("❌ Ошибка при получении данных")

# Обработчики инлайн кнопок для управления тикетами

async def handle_error_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик изменения статуса ошибки"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔ Доступ запрещен")
        return
    
    try:
        # Разбираем callback_data: "error_status_{id}_{status}"
        _, _, error_id, status = query.data.split('_', 3)
        error_id = int(error_id)
        
        feedback_service = get_feedback_service()
        success = feedback_service.update_error_status(error_id, status, query.from_user.id)
        
        if success:
            status_emoji = "🟢" if status == 'решено' else "🟡"
            await query.edit_message_text(
                f"✅ <b>Статус ошибки #{error_id} изменен</b>\n\n"
                f"{status_emoji} Новый статус: <b>{status}</b>\n"
                f"👤 Изменено: @{query.from_user.username}\n"
                f"📅 {query.message.date.strftime('%Y-%m-%d %H:%M')}",
                parse_mode='HTML'
            )
            
            # Уведомляем пользователя об изменении статуса
            error_details = feedback_service.get_error_by_id(error_id)
            if error_details:
                try:
                    await context.bot.send_message(
                        chat_id=error_details['user_id'],
                        text=f"📢 <b>Обновление по вашему обращению #{error_id}</b>\n\n"
                             f"{status_emoji} Статус изменен на: <b>{status}</b>\n\n"
                             f"Спасибо за ваше обращение!",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.warning(f"Не удалось уведомить пользователя {error_details['user_id']}: {e}")
        else:
            await query.edit_message_text("❌ Ошибка при изменении статуса")
            
    except Exception as e:
        logger.error(f"Ошибка при обработке изменения статуса ошибки: {e}")
        await query.edit_message_text("❌ Ошибка обработки")

async def handle_suggestion_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик изменения статуса предложения"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔ Доступ запрещен")
        return
    
    try:
        # Разбираем callback_data: "suggestion_status_{id}_{status}"
        _, _, suggestion_id, status = query.data.split('_', 3)
        suggestion_id = int(suggestion_id)
        
        feedback_service = get_feedback_service()
        success = feedback_service.update_suggestion_status(suggestion_id, status, query.from_user.id)
        
        if success:
            status_emoji = "🟢" if status == 'реализовано' else "🟡"
            await query.edit_message_text(
                f"✅ <b>Статус предложения #{suggestion_id} изменен</b>\n\n"
                f"{status_emoji} Новый статус: <b>{status}</b>\n"
                f"👤 Изменено: @{query.from_user.username}\n"
                f"📅 {query.message.date.strftime('%Y-%m-%d %H:%M')}",
                parse_mode='HTML'
            )
            
            # Уведомляем пользователя об изменении статуса
            suggestion_details = feedback_service.get_suggestion_by_id(suggestion_id)
            if suggestion_details:
                try:
                    await context.bot.send_message(
                        chat_id=suggestion_details['user_id'],
                        text=f"📢 <b>Обновление по вашему предложению #{suggestion_id}</b>\n\n"
                             f"{status_emoji} Статус изменен на: <b>{status}</b>\n\n"
                             f"Спасибо за ваше предложение!",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.warning(f"Не удалось уведомить пользователя {suggestion_details['user_id']}: {e}")
        else:
            await query.edit_message_text("❌ Ошибка при изменении статуса")
            
    except Exception as e:
        logger.error(f"Ошибка при обработке изменения статуса предложения: {e}")
        await query.edit_message_text("❌ Ошибка обработки")

async def handle_suggestion_priority_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик изменения приоритета предложения"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔ Доступ запрещен")
        return
    
    try:
        # Разбираем callback_data: "suggestion_priority_{id}_{priority}"
        _, _, suggestion_id, priority = query.data.split('_', 3)
        suggestion_id = int(suggestion_id)
        
        feedback_service = get_feedback_service()
        success = feedback_service.update_suggestion_priority(suggestion_id, priority, query.from_user.id)
        
        if success:
            priority_emoji = "🔥" if priority == 'критический' else "⚠️" if priority == 'высокий' else "⭐" if priority == 'средний' else "📝"
            await query.edit_message_text(
                f"✅ <b>Приоритет предложения #{suggestion_id} изменен</b>\n\n"
                f"{priority_emoji} Новый приоритет: <b>{priority}</b>\n"
                f"👤 Изменено: @{query.from_user.username}\n"
                f"📅 {query.message.date.strftime('%Y-%m-%d %H:%M')}",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text("❌ Ошибка при изменении приоритета")
            
    except Exception as e:
        logger.error(f"Ошибка при обработке изменения приоритета: {e}")
        await query.edit_message_text("❌ Ошибка обработки")

async def handle_show_full_error_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик показа полного текста ошибки"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔ Доступ запрещен")
        return
    
    try:
        # Разбираем callback_data: "error_full_{id}"
        _, _, error_id = query.data.split('_', 2)
        error_id = int(error_id)
        
        feedback_service = get_feedback_service()
        error_details = feedback_service.get_error_by_id(error_id)
        
        if error_details:
            # Экранируем HTML символы
            username = error_details['username'] or 'Unknown'
            message = error_details['message']
            
            username = username.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            message = message.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            status_emoji = "🟢" if error_details['status'] == 'решено' else "🔴" if error_details['status'] == 'новый' else "🟡"
            
            full_text = (
                f"🐛 <b>Полное сообщение об ошибке #{error_id}</b>\n\n"
                f"👤 От: @{username}\n"
                f"📅 {error_details['timestamp']}\n"
                f"{status_emoji} Статус: {error_details['status']}\n\n"
                f"📝 <b>Полное сообщение:</b>\n{message}"
            )
            
            # Кнопка возврата
            keyboard = [[InlineKeyboardButton("🔙 Назад к списку", callback_data="back_to_errors_list")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                full_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text("❌ Сообщение не найдено")
            
    except Exception as e:
        logger.error(f"Ошибка при показе полного сообщения об ошибке: {e}")
        await query.edit_message_text("❌ Ошибка обработки")

async def handle_show_full_suggestion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик показа полного текста предложения"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔ Доступ запрещен")
        return
    
    try:
        # Разбираем callback_data: "suggestion_full_{id}"
        _, _, suggestion_id = query.data.split('_', 2)
        suggestion_id = int(suggestion_id)
        
        feedback_service = get_feedback_service()
        suggestion_details = feedback_service.get_suggestion_by_id(suggestion_id)
        
        if suggestion_details:
            # Экранируем HTML символы
            username = suggestion_details['username'] or 'Unknown'
            message = suggestion_details['message']
            
            username = username.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            message = message.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            status_emoji = "🟢" if suggestion_details['status'] == 'реализовано' else "🔴" if suggestion_details['status'] == 'новый' else "🟡"
            priority_emoji = "🔥" if suggestion_details['priority'] == 'критический' else "⚠️" if suggestion_details['priority'] == 'высокий' else "⭐" if suggestion_details['priority'] == 'средний' else "📝"
            
            full_text = (
                f"💡 <b>Полное предложение #{suggestion_id}</b> {priority_emoji}\n\n"
                f"👤 От: @{username}\n"
                f"📅 {suggestion_details['timestamp']}\n"
                f"{status_emoji} Статус: {suggestion_details['status']}\n"
                f"🎯 Приоритет: {suggestion_details['priority']}\n\n"
                f"📝 <b>Полное предложение:</b>\n{message}"
            )
            
            # Кнопка возврата
            keyboard = [[InlineKeyboardButton("🔙 Назад к списку", callback_data="back_to_suggestions_list")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                full_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text("❌ Предложение не найдено")
            
    except Exception as e:
        logger.error(f"Ошибка при показе полного предложения: {e}")
        await query.edit_message_text("❌ Ошибка обработки") 