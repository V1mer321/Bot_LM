"""
Обработчики команд для административной панели телеграм-бота.
"""
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

# Используем зашифрованную конфигурацию (теперь она содержит правильные админ-ID)
from toolbot.config import is_admin, add_user_to_whitelist, remove_user_from_whitelist, load_config, add_admin

logger = logging.getLogger(__name__)


async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик для админ-панели
    """
    user_id = update.effective_user.id
    
    # Проверяем, является ли пользователь администратором (используем зашифрованную конфигурацию)
    if not is_admin(user_id):
        await update.message.reply_text(
            "⛔ *Доступ запрещен*\n"
            "У вас нет прав администратора.",
            parse_mode='Markdown'
        )
        return

    # Логируем использование команды
    analytics = context.bot_data.get('analytics')
    if analytics:
        analytics.log_command("admin_panel", user_id)

    keyboard = [
        ["👥 Управление пользователями", "💬 Обратная связь"],
        ["📊 Статистика поиска", "👀 Активность пользователей"],
        ["🕒 Real-time мониторинг", "👑 Добавить администратора"],
        ["📢 Отправить сообщение всем", "📝 Логи текстов"],
        ["🔄 Обновить базы", "🔙 Назад в меню"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "*🛠️ Панель администратора*\n\n"
        "Выберите действие:\n"
        "• 👥 Управление пользователями - добавление/удаление пользователей\n"
        "• 💬 Обратная связь - просмотр ошибок и предложений\n"
        "• 📊 Статистика поиска - анализ эффективности поиска\n"
        "• 👀 Активность пользователей - мониторинг входов и действий\n"
        "• 🕒 Real-time мониторинг - система в реальном времени\n"
        "• 👑 Добавить администратора - назначение нового админа\n"
        "• 📢 Отправить сообщение всем - массовая рассылка пользователям\n"
        "• 📝 Логи текстов - просмотр текстовых сообщений пользователей\n"
        "• 🔄 Обновить базы - обновление баз данных\n\n"
        "💡 _Используйте кнопки для навигации_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def user_management_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик раздела управления пользователями
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    keyboard = [
        ["➕ Добавить пользователя", "➖ Удалить пользователя"],
        ["📋 Список пользователей"],
        ["🔙 Назад в админ-панель"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "*👥 Управление пользователями*\n\n"
        "Выберите действие:\n"
        "• Добавить пользователя\n"
        "• Удалить пользователя\n"
        "• Просмотреть список пользователей",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def add_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик добавления пользователя
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    # Устанавливаем состояние ожидания ID пользователя
    context.user_data['state'] = 'awaiting_new_user_id'

    await update.message.reply_text(
        "*➕ Добавление пользователя*\n\n"
        "Отправьте ID пользователя, которого хотите добавить.",
        parse_mode='Markdown'
    )


async def remove_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик удаления пользователя
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    # Устанавливаем состояние ожидания ID пользователя для удаления
    context.user_data['state'] = 'awaiting_remove_user_id'

    await update.message.reply_text(
        "*➖ Удаление пользователя*\n\n"
        "Отправьте ID пользователя, которого хотите удалить.",
        parse_mode='Markdown'
    )


async def add_admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик добавления администратора
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    # Устанавливаем состояние ожидания ID пользователя для назначения администратором
    context.user_data['state'] = 'awaiting_new_admin_id'

    await update.message.reply_text(
        "*👑 Добавление администратора*\n\n"
        "Отправьте ID пользователя, которого хотите назначить администратором.\n\n"
        "⚠️ *Внимание:* Администратор получит полный доступ к управлению ботом!",
        parse_mode='Markdown'
    )


async def list_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик для просмотра списка пользователей
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    config_data = load_config()  # Переименовываем чтобы не конфликтовало с модулем config
    whitelist = config_data.get('whitelist', [])
    admins = config_data.get('admins', [])

    if not whitelist:
        await update.message.reply_text("❌ В списке нет пользователей.")
        return

    # Формируем сообщение со списком пользователей
    message = "*👥 Список пользователей*\n\n"
    
    for idx, uid in enumerate(whitelist, 1):
        admin_mark = "👑 " if uid in admins else ""
        message += f"{idx}. {admin_mark}ID: `{uid}`\n"

    message += "\n💡 _Администраторы отмечены значком_ 👑"

    await update.message.reply_text(
        message,
        parse_mode='Markdown'
    )


async def back_to_admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик возврата в админ-панель
    """
    await admin_panel_handler(update, context)


async def process_admin_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Обрабатывает текстовый ввод для административных задач
    
    Args:
        update: Объект Update от телеграма
        context: Контекст бота
        
    Returns:
        True если ввод был обработан, False в противном случае
    """
    user_id = update.effective_user.id
    text = update.message.text
    state = context.user_data.get('state')
    
    if not is_admin(user_id):
        return False
    
    # Обработка ввода ID нового пользователя
    if state == 'awaiting_new_user_id':
        try:
            # Удаляем все нецифровые символы кроме минуса
            clean_text = ''.join(c for c in text.strip() if c.isdigit() or c == '-')
            if not clean_text or clean_text == '-':
                raise ValueError("Пустой ID")
            
            new_user_id = int(clean_text)
            
            if add_user_to_whitelist(new_user_id):
                await update.message.reply_text(f"✅ Пользователь с ID {new_user_id} успешно добавлен.")
            else:
                await update.message.reply_text("❌ Не удалось добавить пользователя. Проверьте логи.")
                
            # Сбрасываем состояние
            context.user_data.pop('state', None)
            return True
        except (ValueError, TypeError):
            await update.message.reply_text("❌ Неверный формат ID. Введите числовой ID (например: 123456789 или -123456789)")
            return True
    
    # Обработка ввода ID пользователя для удаления
    elif state == 'awaiting_remove_user_id':
        try:
            # Удаляем все нецифровые символы кроме минуса
            clean_text = ''.join(c for c in text.strip() if c.isdigit() or c == '-')
            if not clean_text or clean_text == '-':
                raise ValueError("Пустой ID")
            
            user_id_to_remove = int(clean_text)
            
            if remove_user_from_whitelist(user_id_to_remove):
                await update.message.reply_text(f"✅ Пользователь с ID {user_id_to_remove} успешно удален.")
            else:
                await update.message.reply_text("❌ Не удалось удалить пользователя. Проверьте логи.")
                
            # Сбрасываем состояние
            context.user_data.pop('state', None)
            return True
        except (ValueError, TypeError):
            await update.message.reply_text("❌ Неверный формат ID. Введите числовой ID (например: 123456789 или -123456789)")
            return True
    
    # Обработка ввода ID пользователя для назначения администратором
    elif state == 'awaiting_new_admin_id':
        try:
            # Удаляем все нецифровые символы кроме минуса
            clean_text = ''.join(c for c in text.strip() if c.isdigit() or c == '-')
            if not clean_text or clean_text == '-':
                raise ValueError("Пустой ID")
            
            new_admin_id = int(clean_text)
            
            # Проверяем, не является ли пользователь уже администратором
            config_data = load_config()
            current_admins = config_data.get('admins', []) if config_data else []
            
            if new_admin_id in current_admins:
                await update.message.reply_text(f"⚠️ Пользователь с ID {new_admin_id} уже является администратором.")
            elif add_admin(new_admin_id):
                await update.message.reply_text(
                    f"✅ Пользователь с ID {new_admin_id} успешно назначен администратором!\n"
                    f"👑 Теперь у него есть полный доступ к админ-панели."
                )
            else:
                await update.message.reply_text("❌ Не удалось назначить администратора. Проверьте логи.")
                
            # Сбрасываем состояние
            context.user_data.pop('state', None)
            return True
        except (ValueError, TypeError):
            await update.message.reply_text("❌ Неверный формат ID. Введите числовой ID (например: 123456789 или -123456789)")
            return True
    
    # Обработка ввода текста сообщения для рассылки
    elif state == 'awaiting_broadcast_message':
        if text.strip():
            await send_broadcast_message(update, context, text.strip())
            return True
        else:
            await update.message.reply_text("❌ Сообщение не может быть пустым. Попробуйте еще раз:")
            return True
    
    # Обработка подтверждения рассылки
    elif state == 'awaiting_broadcast_confirmation':
        if text == "✅ Да, отправить":
            await execute_broadcast(update, context)
            return True
        elif text == "❌ Отменить":
            # Очищаем состояние
            context.user_data.pop('broadcast_text', None)
            context.user_data.pop('broadcast_users', None)
            context.user_data.pop('state', None)
            
            await update.message.reply_text(
                "❌ Рассылка отменена.",
                reply_markup=ReplyKeyboardMarkup([
                    ["👥 Управление пользователями", "💬 Обратная связь"],
                    ["📊 Статистика поиска", "👀 Активность пользователей"],
                    ["🕒 Real-time мониторинг", "👑 Добавить администратора"],
                    ["📢 Отправить сообщение всем", "📝 Логи текстов"],
                    ["🔄 Обновить базы", "🔙 Назад в меню"]
                ], resize_keyboard=True)
            )
            return True
        else:
            await update.message.reply_text("❓ Пожалуйста, выберите один из вариантов: '✅ Да, отправить' или '❌ Отменить'")
            return True
    
    # Обработка поиска в текстовых логах
    elif state == 'awaiting_text_search_query':
        if text.strip():
            await perform_text_search(update, context, text.strip())
            return True
        else:
            await update.message.reply_text("❌ Поисковый запрос не может быть пустым. Попробуйте еще раз:")
            return True
    
    # Обработка запроса сообщений пользователя
    elif state == 'awaiting_user_messages_id':
        try:
            # Удаляем все нецифровые символы кроме минуса
            clean_text = ''.join(c for c in text.strip() if c.isdigit() or c == '-')
            if not clean_text or clean_text == '-':
                raise ValueError("Пустой ID")
            
            target_user_id = int(clean_text)
            await show_user_messages(update, context, target_user_id)
            return True
        except (ValueError, TypeError):
            await update.message.reply_text("❌ Неверный формат ID. Введите числовой ID (например: 123456789 или -123456789)")
            return True
    
    # Обработка поиска пользователя по ID
    elif state == 'awaiting_user_search_id':
        try:
            # Удаляем все нецифровые символы кроме минуса
            clean_text = ''.join(c for c in text.strip() if c.isdigit() or c == '-')
            if not clean_text or clean_text == '-':
                raise ValueError("Пустой ID")
            
            search_user_id = int(clean_text)
            
            # Получаем аналитику
            analytics = context.bot_data.get('analytics')
            if not analytics:
                await update.message.reply_text("❌ Аналитика недоступна")
                context.user_data.pop('state', None)
                return True
            
            # Получаем информацию о пользователе
            user_stats = analytics.get_user_stats(search_user_id)
            activity_log = analytics.get_user_activity_log(search_user_id, limit=10)
            
            if user_stats.get('requests', 0) == 0:
                await update.message.reply_text(f"❌ Пользователь с ID {search_user_id} не найден в статистике.")
                context.user_data.pop('state', None)
                return True
            
            # Форматируем информацию о пользователе
            import datetime
            import time
            
            first_seen = user_stats.get('first_seen', 0)
            last_seen = user_stats.get('last_seen', first_seen)
            total_requests = user_stats.get('requests', 0)
            commands = user_stats.get('commands', {})
            
            # Форматируем даты
            first_seen_dt = datetime.datetime.fromtimestamp(first_seen)
            last_seen_dt = datetime.datetime.fromtimestamp(last_seen)
            
            first_seen_str = first_seen_dt.strftime("%d.%m.%Y %H:%M")
            last_seen_str = last_seen_dt.strftime("%d.%m.%Y %H:%M")
            
            # Определяем статус активности
            current_time = time.time()
            time_diff = current_time - last_seen
            if time_diff < 3600:  # менее часа
                status = "🟢 В сети"
            elif time_diff < 86400:  # менее дня
                status = "🟡 Был сегодня"
            elif time_diff < 604800:  # менее недели
                status = "🟠 Был на неделе"
            else:
                status = "🔴 Давно не заходил"
            
            message = f"🔍 Информация о пользователе {search_user_id}\n\n"
            message += f"📊 Статус: {status}\n"
            message += f"👤 Первый вход: {first_seen_str}\n"
            message += f"⏰ Последний вход: {last_seen_str}\n"
            message += f"📞 Всего запросов: {total_requests}\n\n"
            
            # Топ команд пользователя
            if commands:
                message += "🔝 Популярные команды:\n"
                sorted_commands = sorted(commands.items(), key=lambda x: x[1], reverse=True)
                for cmd, count in sorted_commands[:5]:
                    cmd_safe = cmd.replace('\\', '\\\\').replace('*', '\\*').replace('_', '\\_').replace('`', '\\`').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
                    message += f"• {cmd_safe} \\- {count}x\n"
                message += "\n"
            
            # Последняя активность
            if activity_log:
                message += "📝 Последняя активность:\n"
                for activity in activity_log[-5:]:  # Последние 5 записей
                    timestamp = activity.get('timestamp', 0)
                    activity_type = activity.get('type', 'unknown')
                    details = activity.get('details', '')
                    
                    activity_dt = datetime.datetime.fromtimestamp(timestamp)
                    activity_str = activity_dt.strftime("%d.%m %H:%M")
                    
                    # Сокращаем детали для отображения
                    short_details = details[:30] + "..." if len(details) > 30 else details
                    details_safe = short_details.replace('\\', '\\\\').replace('*', '\\*').replace('_', '\\_').replace('`', '\\`').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
                    
                    message += f"• {activity_str} \\- {activity_type}: {details_safe}\n"
            
            await update.message.reply_text(
                message,
                parse_mode='MarkdownV2'
            )
                
            # Сбрасываем состояние
            context.user_data.pop('state', None)
            return True
        except (ValueError, TypeError):
            await update.message.reply_text("❌ Неверный формат ID. Введите числовой ID (например: 123456789 или -123456789)")
            return True
        except Exception as e:
            logger.error(f"Ошибка при поиске пользователя: {e}")
            await update.message.reply_text(f"❌ Ошибка при поиске пользователя: {str(e)}")
            context.user_data.pop('state', None)
            return True
    
    return False


async def feedback_management_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик раздела управления обратной связью
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    keyboard = [
        ["📊 Статистика обратной связи"],
        ["🐛 Просмотр ошибок", "💡 Просмотр предложений"],
        ["🔙 Назад в админ-панель"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "*💬 Управление обратной связью*\n\n"
        "Выберите действие:\n"
        "• 📊 Статистика - общая статистика обращений\n"
        "• 🐛 Просмотр ошибок - последние сообщения об ошибках\n"
        "• 💡 Просмотр предложений - предложения по улучшению\n\n"
        "💡 _Используйте кнопки для навигации_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def feedback_stats_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик кнопки статистики обратной связи
    """
    # Импортируем обработчик из feedback_handlers
    from toolbot.handlers.feedback_handlers import view_feedback_stats_handler
    await view_feedback_stats_handler(update, context)
    
    # Добавляем кнопку возврата
    keyboard = [["🔙 Назад к обратной связи"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "📋 _Используйте кнопку ниже для возврата_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def errors_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик кнопки просмотра ошибок
    """
    # Импортируем обработчик из feedback_handlers
    from toolbot.handlers.feedback_handlers import view_errors_handler
    await view_errors_handler(update, context)
    
    # Добавляем кнопку возврата
    keyboard = [["🔙 Назад к обратной связи"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "📋 _Используйте кнопку ниже для возврата_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def suggestions_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик кнопки просмотра предложений
    """
    # Импортируем обработчик из feedback_handlers
    from toolbot.handlers.feedback_handlers import view_suggestions_handler
    await view_suggestions_handler(update, context)
    
    # Добавляем кнопку возврата
    keyboard = [["🔙 Назад к обратной связи"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "📋 _Используйте кнопку ниже для возврата_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def back_to_feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик возврата к управлению обратной связью
    """
    await feedback_management_handler(update, context)


async def search_statistics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик статистики поиска по изображениям
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    try:
        # Импортируем сервис статистики
        from services.search_statistics import get_stats_service
        stats_service = get_stats_service()
        
        # Получаем общую статистику успешности
        success_stats = stats_service.get_search_success_rate()
        
        # Получаем статистику неудачных поисков
        failed_stats = stats_service.get_failed_searches_stats()
        
        # Получаем последние неудачные поиски
        recent_failed = stats_service.get_recent_failed_searches(limit=5)
        
        # Формируем сообщение со статистикой
        message = "*📊 Статистика поиска по изображениям*\n\n"
        
        # Общая статистика
        message += "*🎯 Общая эффективность:*\n"
        message += f"• Всего поисков: {success_stats.get('total_searches', 0)}\n"
        message += f"• Успешных поисков: {success_stats.get('successful_searches', 0)}\n"
        message += f"• Пользователи сообщили о неудачах: {success_stats.get('user_reported_failures', 0)}\n"
        success_rate = success_stats.get('success_rate_percent', 0)
        message += f"• Процент успеха: {success_rate}%%\n"
        message += f"• Средняя схожесть: {success_stats.get('average_similarity', 0):.3f}\n\n"
        
        # Статистика неудачных поисков
        message += "*❌ Анализ неудач:*\n"
        message += f"• Всего жалоб: {failed_stats.get('total_failed_searches', 0)}\n"
        
        # Топ пользователей с неудачами
        top_users = failed_stats.get('top_users_with_failures', [])
        if top_users:
            message += f"• Топ пользователей с неудачами:\n"
            for user in top_users[:3]:
                username = user.get('username', 'Неизвестно')
                message += f"  - {username} (ID: {user['user_id']}): {user['failed_count']} неудач\n"
        
        # Статистика по дням
        daily_stats = failed_stats.get('daily_stats', {})
        if daily_stats:
            message += f"\n• Неудачи за последние дни:\n"
            for date, count in list(daily_stats.items())[:5]:
                message += f"  - {date}: {count} неудач\n"
        
        # Последние неудачные поиски
        if recent_failed:
            message += f"\n*🔍 Последние неудачные поиски:*\n"
            for i, search in enumerate(recent_failed[:3], 1):
                username = search.get('username', 'Неизвестно')
                timestamp = search.get('timestamp', '')[:10]  # Только дата
                feedback = search.get('feedback_type', 'unknown')
                comment = search.get('user_comment', '')
                
                message += f"{i}. {username} ({timestamp})\n"
                if comment:
                    message += f"   💬 \"{comment[:50]}...\"\n"
        
        # Кнопки управления
        keyboard = [
            ["📋 Детальная статистика", "🔄 Обновить данные"],
            ["📝 Последние жалобы", "📈 Тренды поиска"],
            ["🔙 Назад в админ-панель"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики поиска: {e}")
        await update.message.reply_text(
            "❌ Ошибка при получении статистики поиска.\n"
            "Проверьте логи для деталей."
        )


async def detailed_search_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик детальной статистики поиска"""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    try:
        from services.search_statistics import get_stats_service
        stats_service = get_stats_service()
        
        # Получаем подробные данные
        recent_failed = stats_service.get_recent_failed_searches(limit=10)
        
        if not recent_failed:
            await update.message.reply_text("📊 Нет данных о неудачных поисках.")
            return
        
        message = "*📋 Детальная статистика неудачных поисков*\n\n"
        
        for i, search in enumerate(recent_failed, 1):
            username = search.get('username', 'Неизвестно')
            user_id_str = search.get('user_id', 'unknown')
            timestamp = search.get('timestamp', '')[:16]  # Дата и время
            feedback_type = search.get('feedback_type', 'unknown')
            comment = search.get('user_comment', '')
            
            # Анализируем результаты поиска
            results = search.get('search_results', [])
            if results:
                best_similarity = max([r.get('similarity', 0) for r in results])
                results_count = len(results)
            else:
                best_similarity = 0
                results_count = 0
            
            message += f"*{i}. {username}* (ID: {user_id_str})\n"
            message += f"📅 {timestamp}\n"
            message += f"🔍 Результатов: {results_count}, лучшая схожесть: {best_similarity:.3f}\n"
            
            if comment:
                message += f"💬 \"{comment}\"\n"
            
            message += "─" * 30 + "\n"
            
            # Ограничиваем размер сообщения
            if len(message) > 3500:
                message += f"\n... и еще {len(recent_failed) - i} записей"
                break
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении детальной статистики: {e}")
        await update.message.reply_text("❌ Ошибка при получении детальной статистики.")


async def recent_complaints_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик последних жалоб"""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    try:
        from services.search_statistics import get_stats_service
        stats_service = get_stats_service()
        
        # Получаем только жалобы с комментариями
        all_failed = stats_service.get_recent_failed_searches(limit=20)
        complaints_with_comments = [
            search for search in all_failed 
            if search.get('user_comment') and search.get('user_comment').strip()
        ]
        
        if not complaints_with_comments:
            await update.message.reply_text("📝 Нет жалоб с комментариями.")
            return
        
        message = "*📝 Последние жалобы пользователей*\n\n"
        
        for i, search in enumerate(complaints_with_comments[:5], 1):
            username = search.get('username', 'Неизвестно')
            timestamp = search.get('timestamp', '')[:10]
            comment = search.get('user_comment', '')
            
            message += f"*{i}. {username}* ({timestamp})\n"
            message += f"💬 \"{comment}\"\n\n"
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении жалоб: {e}")
        await update.message.reply_text("❌ Ошибка при получении жалоб.")


async def user_activity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик для просмотра активности пользователей
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    keyboard = [
        ["📈 Активные пользователи", "📋 Все пользователи"],
        ["🔍 Поиск по ID", "📊 Общая статистика"],
        ["🔙 Назад в админ-панель"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "*👀 Мониторинг активности пользователей*\n\n"
        "Выберите тип отчета:\n"
        "• 📈 *Активные пользователи* - активность за последние 7 дней\n"
        "• 📋 *Все пользователи* - полный список с базовой информацией\n"
        "• 🔍 *Поиск по ID* - детальная информация о конкретном пользователе\n"
        "• 📊 *Общая статистика* - сводная статистика активности",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def active_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает активных пользователей за последние 7 дней
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return
    
    analytics = context.bot_data.get('analytics')
    if not analytics:
        await update.message.reply_text("❌ Аналитика недоступна")
        return
    
    try:
        import datetime
        
        recent_users = analytics.get_recent_users(days=7)
        
        if not recent_users:
            await update.message.reply_text("📈 Активных пользователей за последние 7 дней не найдено.")
            return
        
        message = "*📈 Активные пользователи (последние 7 дней)*\n\n"
        
        for i, user_data in enumerate(recent_users[:20], 1):  # Топ-20
            try:
                user_id_val = user_data.get("user_id", 0)
                last_seen = user_data.get("last_seen", 0)
                total_requests = user_data.get("total_requests", 0)
                recent_activity = user_data.get("recent_activity", [])
                recent_activity_count = len(recent_activity) if recent_activity else 0
                
                # Безопасно форматируем время последней активности
                try:
                    last_seen_dt = datetime.datetime.fromtimestamp(last_seen)
                    last_seen_str = last_seen_dt.strftime("%d.%m %H:%M")
                except (OSError, ValueError):
                    last_seen_str = "неизвестно"
                
                message += f"{i}. ID: `{user_id_val}`\n"
                message += f"   Последний вход: {last_seen_str}\n"
                message += f"   Всего запросов: {total_requests}\n"
                message += f"   Активность за неделю: {recent_activity_count}\n\n"
            except Exception as e:
                logger.warning(f"Ошибка при обработке пользователя {i}: {e}")
                continue
        
        if len(recent_users) > 20:
            message += f"*...и ещё {len(recent_users) - 20} пользователей*"
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении активных пользователей: {e}")
        import traceback
        logger.error(f"Полная ошибка: {traceback.format_exc()}")
        await update.message.reply_text(
            "❌ Произошла ошибка при получении данных об активности.\n"
            f"Детали: {str(e)}"
        )


async def all_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает всех пользователей с базовой информацией
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return
    
    analytics = context.bot_data.get('analytics')
    if not analytics:
        await update.message.reply_text("❌ Аналитика недоступна")
        return
    
    try:
        import datetime
        import time
        
        stats = analytics.get_stats()
        if not stats:
            await update.message.reply_text("📋 Статистика не найдена.")
            return
            
        users = stats.get("users", {})
        
        if not users:
            await update.message.reply_text("📋 Пользователей в базе данных не найдено.")
            return
        
        # Сортируем пользователей по времени последней активности
        user_list = []
        for user_id_str, user_data in users.items():
            try:
                if not user_data or not isinstance(user_data, dict):
                    continue
                    
                last_seen = user_data.get("last_seen", user_data.get("first_seen", 0))
                first_seen = user_data.get("first_seen", 0)
                
                # Проверяем корректность данных
                if not isinstance(last_seen, (int, float)) or not isinstance(first_seen, (int, float)):
                    continue
                    
                user_list.append({
                    "user_id": int(user_id_str),
                    "last_seen": last_seen,
                    "total_requests": user_data.get("requests", 0),
                    "first_seen": first_seen
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Некорректные данные пользователя {user_id_str}: {e}")
                continue
        
        if not user_list:
            await update.message.reply_text("📋 Корректных данных пользователей не найдено.")
            return
        
        user_list.sort(key=lambda x: x["last_seen"], reverse=True)
        
        message = f"*📋 Все пользователи ({len(user_list)} чел.)*\n\n"
        
        current_time = time.time()
        
        for i, user_data in enumerate(user_list[:30], 1):  # Первые 30
            try:
                user_id_val = user_data["user_id"]
                last_seen = user_data["last_seen"]
                total_requests = user_data["total_requests"]
                first_seen = user_data["first_seen"]
                
                # Определяем статус активности
                time_diff = current_time - last_seen
                if time_diff < 3600:  # менее часа
                    status = "🟢 онлайн"
                elif time_diff < 86400:  # менее дня
                    status = "🟡 сегодня"
                elif time_diff < 604800:  # менее недели
                    status = "🟠 на неделе"
                else:
                    status = "🔴 давно"
                
                # Безопасно форматируем первое появление
                try:
                    first_seen_dt = datetime.datetime.fromtimestamp(first_seen)
                    first_seen_str = first_seen_dt.strftime("%d.%m.%y")
                except (OSError, ValueError):
                    first_seen_str = "неизвестно"
                
                message += f"{i}. ID: `{user_id_val}` {status}\n"
                message += f"   Первый вход: {first_seen_str}\n"
                message += f"   Всего запросов: {total_requests}\n\n"
            except Exception as e:
                logger.warning(f"Ошибка при обработке пользователя {i}: {e}")
                continue
        
        if len(user_list) > 30:
            message += f"*...и ещё {len(user_list) - 30} пользователей*\n\n"
        
        message += "💡 _Для детальной информации используйте 'Поиск по ID'_"
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей: {e}")
        import traceback
        logger.error(f"Полная ошибка: {traceback.format_exc()}")
        await update.message.reply_text(
            "❌ Произошла ошибка при получении списка пользователей.\n"
            f"Детали: {str(e)}"
        )


async def search_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик поиска пользователя по ID
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    # Устанавливаем состояние ожидания ID пользователя
    context.user_data['state'] = 'awaiting_user_search_id'

    await update.message.reply_text(
        "*🔍 Поиск пользователя по ID*\n\n"
        "Отправьте ID пользователя, информацию о котором хотите получить:",
        parse_mode='Markdown'
    )


async def activity_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает общую статистику активности
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return
    
    analytics = context.bot_data.get('analytics')
    if not analytics:
        await update.message.reply_text("❌ Аналитика недоступна")
        return
    
    try:
        import datetime
        
        summary = analytics.get_summary()
        
        if not summary:
            await update.message.reply_text("📊 Данные статистики недоступны.")
            return
        
        uptime_days = summary.get("uptime_days", 0)
        total_requests = summary.get("total_requests", 0)
        unique_users = summary.get("unique_users", 0)
        active_today = summary.get("active_today", 0)
        active_week = summary.get("active_week", 0)
        
        message = "*📊 Общая статистика активности*\n\n"
        message += f"⏱ *Время работы:* {uptime_days:.1f} дней\n"
        message += f"📞 *Всего запросов:* {total_requests}\n"
        message += f"👥 *Уникальных пользователей:* {unique_users}\n"
        message += f"🟢 *Активны сегодня:* {active_today}\n"
        message += f"📅 *Активны за неделю:* {active_week}\n\n"
        
        # Топ команд
        top_commands = summary.get("top_commands", [])
        if top_commands:
            message += "*🔝 Популярные команды:*\n"
            for i, (cmd, count) in enumerate(top_commands[:5], 1):  # Только топ-5
                message += f"{i}. `{cmd}` - {count}x\n"
            message += "\n"
        
        # Статистика поиска по фото
        photo_searches = summary.get("photo_searches", {})
        if photo_searches and isinstance(photo_searches, dict):
            total_photo = photo_searches.get("total", 0)
            success_photo = photo_searches.get("success", 0)
            
            if total_photo > 0:
                success_rate = (success_photo / total_photo) * 100
                message += f"📸 *Поиск по фото:*\n"
                message += f"   Всего поисков: {total_photo}\n"
                message += f"   Успешных: {success_photo}\n"
                message += f"   Успешность: {success_rate:.1f}%%\n"
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении общей статистики: {e}")
        import traceback
        logger.error(f"Полная ошибка: {traceback.format_exc()}")
        await update.message.reply_text(
            "❌ Произошла ошибка при получении статистики.\n"
            f"Детали: {str(e)}"
        )


async def update_databases_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик обновления баз данных
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return
    
    try:
        # Логируем начало обновления
        analytics = context.bot_data.get('analytics')
        if analytics:
            analytics.log_command("update_databases", user_id)
        
        # Отправляем сообщение о начале обновления
        status_message = await update.message.reply_text(
            "🔄 *Начинаю обновление баз данных...*\n\n"
            "⏳ Подождите, это может занять несколько минут.",
            parse_mode='Markdown'
        )
        
        # Проверяем статус текущих баз данных
        import os
        import sqlite3
        from datetime import datetime
        
        db_path = "data/unified_products.db"
        csv_path = "data/txt_export/unified_products.csv"
        txt_path = "data/txt_export/unified_products.txt"
        
        status_info = "📊 *Статус баз данных:*\n\n"
        
                # Проверяем SQLite базу
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM products")
                count = cursor.fetchone()[0]
                
                file_size = os.path.getsize(db_path) / (1024 * 1024)  # МБ
                mod_time = datetime.fromtimestamp(os.path.getmtime(db_path))
                mod_time_str = mod_time.strftime('%d.%m.%Y %H:%M')
                
                status_info += f"✅ *SQLite база:* {count:,} товаров\n"
                status_info += f"   Размер: {file_size:.1f} МБ\n"
                status_info += f"   Обновлена: {mod_time_str}\n\n"
                
                conn.close()
            except Exception as e:
                status_info += f"❌ *SQLite база:* Ошибка - {str(e)}\n\n"
        else:
            status_info += f"❌ *SQLite база:* Файл не найден\n\n"
        
        # Проверяем TXT экспорт
        if os.path.exists(txt_path):
            file_size = os.path.getsize(txt_path) / (1024 * 1024)  # МБ
            mod_time = datetime.fromtimestamp(os.path.getmtime(txt_path))
            
            with open(txt_path, 'r', encoding='utf-8') as f:
                lines = sum(1 for _ in f) - 1  # минус заголовок
            
            mod_time_str = mod_time.strftime('%d.%m.%Y %H:%M')
            status_info += f"✅ *TXT экспорт:* {lines:,} товаров\n"
            status_info += f"   Размер: {file_size:.1f} МБ\n"
            status_info += f"   Обновлен: {mod_time_str}\n\n"
        else:
            status_info += f"❌ *TXT экспорт:* Файл не найден\n\n"
        
        # Проверяем CSV экспорт
        if os.path.exists(csv_path):
            file_size = os.path.getsize(csv_path) / (1024 * 1024)  # МБ
            mod_time = datetime.fromtimestamp(os.path.getmtime(csv_path))
            
            mod_time_str = mod_time.strftime('%d.%m.%Y %H:%M')
            status_info += f"✅ *CSV экспорт:* доступен\n"
            status_info += f"   Размер: {file_size:.1f} МБ\n"
            status_info += f"   Обновлен: {mod_time_str}\n\n"
        else:
            status_info += f"❌ *CSV экспорт:* Файл не найден\n\n"
        
        status_info += "💡 *Примечание:* Основная база данных (SQLite) обновляется автоматически.\n"
        status_info += "TXT и CSV файлы можно пересоздать при необходимости."
        
        # Обновляем сообщение
        await status_message.edit_text(
            status_info,
            parse_mode='Markdown'
        )
        
        # Добавляем кнопки для дополнительных действий
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("🔄 Пересоздать TXT", callback_data="recreate_txt")],
            [InlineKeyboardButton("📊 Проверить целостность", callback_data="check_integrity")],
            [InlineKeyboardButton("🔙 Вернуться в админку", callback_data="back_to_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🛠️ *Дополнительные действия:*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении баз данных: {e}")
        import traceback
        logger.error(f"Полная ошибка: {traceback.format_exc()}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обновлении баз данных.\n"
            f"Детали: {str(e)}"
        )


async def realtime_monitoring_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Главное меню real-time мониторинга
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    keyboard = [
        ["📊 Дашборд системы", "👥 Активные пользователи"],
        ["⚡ Производительность", "🚨 Алерты и уведомления"],
        ["📈 История метрик", "⚙️ Настройки мониторинга"],
        ["🔙 Назад в админ-панель"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "*🕒 Real-time мониторинг*\n\n"
        "Система мониторинга в реальном времени:\n\n"
        "• 📊 Дашборд системы - текущие метрики CPU, GPU, RAM\n"
        "• 👥 Активные пользователи - кто сейчас онлайн\n"
        "• ⚡ Производительность - скорость обработки запросов\n"
        "• 🚨 Алерты - критические состояния системы\n"
        "• 📈 История метрик - графики за последние часы\n"
        "• ⚙️ Настройки - пороговые значения алертов\n\n"
        "💡 _Данные обновляются каждые 5 секунд_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def system_dashboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает системный дашборд в реальном времени
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    try:
        # Импортируем мониторинг
        from toolbot.services.monitoring import monitoring
        
        # Получаем данные дашборда
        dashboard_data = monitoring.get_dashboard_data()
        
        # Формируем сообщение
        current_time = datetime.now()
        uptime_hours = dashboard_data['uptime_seconds'] // 3600
        uptime_minutes = (dashboard_data['uptime_seconds'] % 3600) // 60
        
        message = f"*📊 Системный дашборд* `{current_time.hour:02d}:{current_time.minute:02d}:{current_time.second:02d}`\n\n"
        message += f"⏱ *Время работы:* {uptime_hours}ч {uptime_minutes}м\n\n"
        
        # Системные метрики
        system = dashboard_data['system']
        
        # CPU
        cpu = system.get('cpu', {})
        cpu_usage = cpu.get('usage_percent', 0)
        cpu_emoji = "🔥" if cpu_usage > 80 else "⚡" if cpu_usage > 50 else "✅"
        message += f"{cpu_emoji} *CPU:* {cpu_usage:.1f}%%\n"
        
        if cpu.get('frequency_mhz'):
            message += f"   Частота: {cpu['frequency_mhz']:.0f} MHz\n"
        message += f"   Ядра: {cpu.get('cores_logical', '?')} логических\n\n"
        
        # Память
        memory = system.get('memory', {})
        mem_usage = memory.get('usage_percent', 0)
        mem_emoji = "🔥" if mem_usage > 85 else "⚠️" if mem_usage > 70 else "✅"
        message += f"{mem_emoji} *RAM:* {mem_usage:.1f}%%\n"
        message += f"   Используется: {memory.get('used_gb', 0):.1f} / {memory.get('total_gb', 0):.1f} ГБ\n"
        message += f"   Свободно: {memory.get('available_gb', 0):.1f} ГБ\n\n"
        
        # GPU (если доступно)
        gpu = system.get('gpu')
        if gpu:
            gpu_usage = gpu.get('usage_percent', 0)
            gpu_temp = gpu.get('temperature_c', 0)
            gpu_mem_usage = gpu.get('memory_usage_percent', 0)
            
            gpu_emoji = "🔥" if gpu_temp > 80 or gpu_usage > 90 else "⚡" if gpu_usage > 70 else "✅"
            message += f"{gpu_emoji} *GPU:* {gpu.get('name', 'Unknown')}\n"
            message += f"   Загрузка: {gpu_usage:.1f}%%\n"
            
            if gpu_temp > 0:
                message += f"   Температура: {gpu_temp}°C\n"
                
            if 'memory_total_mb' in gpu:
                total_gb = gpu['memory_total_mb'] / 1024
                used_gb = gpu.get('memory_allocated_mb', gpu.get('memory_used_mb', 0)) / 1024
                message += f"   VRAM: {used_gb:.1f} / {total_gb:.1f} ГБ ({gpu_mem_usage:.1f}%%)\n"
            message += "\n"
        else:
            message += "❌ *GPU:* Не доступен\n\n"
        
        # Диск
        disk = system.get('disk', {})
        disk_usage = disk.get('usage_percent', 0)
        disk_emoji = "🔥" if disk_usage > 90 else "⚠️" if disk_usage > 80 else "✅"
        message += f"{disk_emoji} *Диск:* {disk_usage:.1f}%%\n"
        message += f"   Свободно: {disk.get('free_gb', 0):.1f} / {disk.get('total_gb', 0):.1f} ГБ\n\n"
        
        # Активность пользователей
        activity = dashboard_data['activity']
        message += f"👥 *Активные пользователи:* {activity['active_now']}\n"
        message += f"📞 *Запросов за час:* {activity['requests_last_hour']}\n"
        message += f"🆕 *Новых сегодня:* {activity['new_users_today']}\n\n"
        
        # Производительность
        performance = dashboard_data['performance']
        if not performance.get('no_data'):
            avg_time = performance.get('avg_response_time_ms', 0)
            success_rate = performance.get('success_rate_percent', 0)
            
            perf_emoji = "🔥" if avg_time > 1000 else "⚠️" if avg_time > 500 else "✅"
            message += f"{perf_emoji} *Средний ответ:* {avg_time:.0f}мс\n"
            message += f"✅ *Успешность:* {success_rate:.1f}%%\n"
            message += f"🔢 *Всего запросов:* {performance.get('total_requests', 0)}\n\n"
        
        # Алерты
        alerts = dashboard_data.get('alerts', [])
        if alerts:
            message += "🚨 *Активные алерты:*\n"
            for alert in alerts[:3]:  # Показываем только первые 3
                emoji = "🔥" if alert['type'] == 'critical' else "⚠️"
                message += f"{emoji} {alert['message']}\n"
            if len(alerts) > 3:
                message += f"... и еще {len(alerts) - 3} алертов\n"
        else:
            message += "✅ *Алерты:* Все в норме\n"
        
        # Кнопки для обновления
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_dashboard")],
            [InlineKeyboardButton("📈 История", callback_data="metrics_history"),
             InlineKeyboardButton("🚨 Все алерты", callback_data="all_alerts")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_monitoring")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка в системном дашборде: {e}")
        import traceback
        logger.error(f"Полная ошибка: {traceback.format_exc()}")
        await update.message.reply_text(
            f"❌ Ошибка при получении данных мониторинга:\n{str(e)}"
        )


async def active_users_realtime_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает активных пользователей в реальном времени
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    try:
        from toolbot.services.monitoring import monitoring
        
        # Получаем активных пользователей
        active_users = monitoring.user_activity_monitor.get_active_users(30)
        activity_stats = monitoring.user_activity_monitor.get_activity_statistics()
        queue_status = monitoring.user_activity_monitor.get_request_queue_status()
        
        current_time = datetime.now()
        message = f"*👥 Активные пользователи* `{current_time.hour:02d}:{current_time.minute:02d}:{current_time.second:02d}`\n\n"
        
        # Общая статистика
        message += f"🟢 *Сейчас онлайн:* {len(active_users)} пользователей\n"
        message += f"📊 *Запросов за 5 мин:* {queue_status['recent_5min']}\n"
        message += f"⚡ *Средняя нагрузка:* {queue_status['avg_per_minute']:.1f} req/min\n\n"
        
        if active_users:
            message += "*🔥 Активные пользователи (последние 30 мин):*\n\n"
            
            # Сортируем по времени последней активности
            sorted_users = sorted(
                active_users.items(),
                key=lambda x: x[1]['minutes_ago']
            )
            
            for user_id_active, user_data in sorted_users[:10]:  # Показываем только первые 10
                minutes_ago = user_data['minutes_ago']
                activity_type = user_data['activity_type']
                
                # Эмодзи в зависимости от типа активности
                activity_emoji = {
                    'photo_search': '📸',
                    'text_search': '🔍',
                    'catalog_browse': '📋',
                    'admin_panel': '⚙️',
                    'start': '🚀',
                    'help': '❓'
                }.get(activity_type, '💬')
                
                # Время активности
                if minutes_ago == 0:
                    time_str = "сейчас"
                elif minutes_ago < 5:
                    time_str = f"{minutes_ago}м назад"
                else:
                    time_str = f"{minutes_ago}м назад"
                
                message += f"{activity_emoji} `{user_id_active}` - {time_str}\n"
                message += f"   ↳ {activity_type}\n"
            
            if len(active_users) > 10:
                message += f"\n... и еще {len(active_users) - 10} пользователей\n"
        else:
            message += "😴 *Сейчас никого нет онлайн*\n\n"
        
        # Статистика за сегодня
        message += f"\n📅 *Статистика за сегодня:*\n"
        message += f"• Всего запросов: {activity_stats['requests_today']}\n"
        message += f"• Новых пользователей: {activity_stats['new_users_today']}\n"
        message += f"• Зарегистрировано всего: {activity_stats['total_registered_users']}\n"
        
        # Кнопки
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_active_users")],
            [InlineKeyboardButton("📊 Детальная статистика", callback_data="detailed_activity_stats")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_monitoring")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка в мониторинге активных пользователей: {e}")
        await update.message.reply_text(
            f"❌ Ошибка при получении данных о пользователях:\n{str(e)}"
        )


async def performance_monitoring_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает метрики производительности в реальном времени
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    try:
        from toolbot.services.monitoring import monitoring
        
        performance_stats = monitoring.performance_monitor.get_performance_stats()
        system_metrics = monitoring.system_monitor.get_current_metrics()
        
        current_time = datetime.now()
        message = f"*⚡ Производительность* `{current_time.hour:02d}:{current_time.minute:02d}:{current_time.second:02d}`\n\n"
        
        # Инициализируем переменные значениями по умолчанию
        avg_time = 0
        success_rate = 100
        
        if performance_stats.get('no_data'):
            message += "📊 *Нет данных о производительности*\n\n"
            message += "Данные будут доступны после первых запросов к боту."
        else:
            # Общие метрики производительности
            avg_time = performance_stats.get('avg_response_time_ms', 0)
            success_rate = performance_stats.get('success_rate_percent', 0)
            total_requests = performance_stats.get('total_requests', 0)
            total_errors = performance_stats.get('total_errors', 0)
            
            # Эмодзи в зависимости от производительности
            time_emoji = "🔥" if avg_time > 1000 else "⚠️" if avg_time > 500 else "✅"
            success_emoji = "🔥" if success_rate < 90 else "⚠️" if success_rate < 95 else "✅"
            
            message += f"{time_emoji} *Среднее время ответа:* {avg_time:.1f}мс\n"
            message += f"{success_emoji} *Успешность:* {success_rate:.1f}%%\n"
            message += f"📊 *Всего запросов:* {total_requests:,}\n"
            message += f"❌ *Ошибок:* {total_errors}\n\n"
            
            # Производительность моделей
            model_stats = performance_stats.get('model_stats', {})
            if model_stats:
                message += "*🧠 Производительность моделей:*\n"
                for model_name, stats in model_stats.items():
                    avg_inference = stats['avg_inference_ms']
                    total_runs = stats['total_runs']
                    
                    model_emoji = "🚀" if avg_inference < 100 else "⚡" if avg_inference < 300 else "⚠️"
                    message += f"{model_emoji} {model_name}:\n"
                    message += f"   ↳ {avg_inference:.1f}мс (запусков: {total_runs})\n"
                message += "\n"
        
        # GPU метрики (если доступно)
        gpu_data = system_metrics.get('gpu')
        if gpu_data:
            message += "*🎮 GPU Производительность:*\n"
            message += f"• Модель: {gpu_data.get('name', 'Unknown')}\n"
            
            if 'usage_percent' in gpu_data:
                usage = gpu_data['usage_percent']
                usage_emoji = "🔥" if usage > 90 else "⚡" if usage > 70 else "✅"
                message += f"• Загрузка: {usage_emoji} {usage:.1f}%%\n"
                
            if 'temperature_c' in gpu_data:
                temp = gpu_data['temperature_c']
                temp_emoji = "🔥" if temp > 80 else "⚠️" if temp > 70 else "✅"
                message += f"• Температура: {temp_emoji} {temp}°C\n"
                
            if 'memory_usage_percent' in gpu_data:
                mem_usage = gpu_data['memory_usage_percent']
                mem_emoji = "🔥" if mem_usage > 90 else "⚠️" if mem_usage > 80 else "✅"
                message += f"• VRAM: {mem_emoji} {mem_usage:.1f}%%\n"
            
            message += "\n"
        
        # Тренды производительности (если есть история)
        message += "*📈 Статус системы:*\n"
        
        # CPU
        cpu_usage = system_metrics.get('cpu', {}).get('usage_percent', 0)
        cpu_emoji = "🔥" if cpu_usage > 80 else "⚡" if cpu_usage > 50 else "✅"
        message += f"{cpu_emoji} CPU: {cpu_usage:.1f}%%\n"
        
        # Память
        mem_usage = system_metrics.get('memory', {}).get('usage_percent', 0)
        mem_emoji = "🔥" if mem_usage > 85 else "⚠️" if mem_usage > 70 else "✅"
        message += f"{mem_emoji} RAM: {mem_usage:.1f}%%\n"
        
        # Рекомендации по оптимизации
        recommendations = []
        
        if avg_time > 1000:
            recommendations.append("🔧 Время ответа высокое - проверьте загрузку GPU")
        if success_rate < 95:
            recommendations.append("⚠️ Низкая успешность - проверьте логи ошибок")
        if cpu_usage > 80:
            recommendations.append("🔥 Высокая загрузка CPU - возможно требуется масштабирование")
        if mem_usage > 85:
            recommendations.append("💾 Высокое потребление RAM - проверьте утечки памяти")
            
        if recommendations:
            message += "\n*💡 Рекомендации:*\n"
            for rec in recommendations:
                message += f"• {rec}\n"
        
        # Кнопки
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_performance")],
            [InlineKeyboardButton("📊 Детальные метрики", callback_data="detailed_metrics")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_monitoring")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка в мониторинге производительности: {e}")
        await update.message.reply_text(
            f"❌ Ошибка при получении метрик производительности:\n{str(e)}"
        )


async def back_to_monitoring_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Возврат в главное меню мониторинга
    """
    await realtime_monitoring_handler(update, context)


async def metrics_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает историю метрик системы
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    try:
        from toolbot.services.monitoring import monitoring
        
        # Получаем историю метрик за последний час
        metrics_history = monitoring.system_monitor.get_metrics_history(60)
        
        if not metrics_history:
            await update.message.reply_text(
                "📈 *История метрик*\n\n"
                "Данные недоступны. Система мониторинга запущена недавно.\n"
                "История будет накапливаться в течение работы бота.",
                parse_mode='Markdown'
            )
            return
        
        # Анализируем тренды
        cpu_values = [m['metrics']['cpu']['usage_percent'] for m in metrics_history if 'cpu' in m['metrics']]
        memory_values = [m['metrics']['memory']['usage_percent'] for m in metrics_history if 'memory' in m['metrics']]
        
        message = "*📈 История метрик (последний час)*\n\n"
        
        if cpu_values:
            cpu_avg = sum(cpu_values) / len(cpu_values)
            cpu_max = max(cpu_values)
            cpu_min = min(cpu_values)
            message += f"**💻 CPU:**\n"
            message += f"• Среднее: {cpu_avg:.1f}%%\n"
            message += f"• Максимум: {cpu_max:.1f}%%\n"
            message += f"• Минимум: {cpu_min:.1f}%%\n\n"
        
        if memory_values:
            mem_avg = sum(memory_values) / len(memory_values)
            mem_max = max(memory_values)
            mem_min = min(memory_values)
            message += f"**💾 RAM:**\n"
            message += f"• Среднее: {mem_avg:.1f}%%\n"
            message += f"• Максимум: {mem_max:.1f}%%\n"
            message += f"• Минимум: {mem_min:.1f}%%\n\n"
        
        message += f"📊 Всего записей: {len(metrics_history)}\n"
        message += f"⏰ Период: последние {len(metrics_history) * 5} минут"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка в истории метрик: {e}")
        await update.message.reply_text(
            f"❌ Ошибка при получении истории метрик:\n{str(e)}"
        )


async def alerts_notifications_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает все алерты и уведомления
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    try:
        from toolbot.services.monitoring import monitoring
        
        # Получаем текущие данные для проверки алертов
        dashboard_data = monitoring.get_dashboard_data()
        alerts = dashboard_data.get('alerts', [])
        
        message = "*🚨 Алерты и уведомления*\n\n"
        
        if alerts:
            message += f"**Активные алерты ({len(alerts)}):**\n\n"
            
            for i, alert in enumerate(alerts, 1):
                alert_type = alert['type']
                alert_message = alert['message']
                timestamp = alert['timestamp'][:16]  # Только дата и время
                
                emoji = "🔥" if alert_type == 'critical' else "⚠️"
                message += f"{emoji} **{i}.** {alert_message}\n"
                message += f"   ⏰ {timestamp}\n\n"
        else:
            message += "✅ **Активных алертов нет**\n\n"
            message += "Система работает в штатном режиме."
        
        message += "\n**⚙️ Пороговые значения:**\n"
        message += f"• CPU: > 90%%\n"
        message += f"• RAM: > 85%%\n"
        message += f"• GPU: > 95%%\n"
        message += f"• Температура GPU: > 80°C\n"
        message += f"• Время ответа: > 1000мс\n"
        message += f"• Ошибки: > 10%%"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка в алертах: {e}")
        await update.message.reply_text(
            f"❌ Ошибка при получении алертов:\n{str(e)}"
        )


async def monitoring_settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Настройки системы мониторинга
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    try:
        from toolbot.services.monitoring import monitoring
        
        # Получаем данные дашборда для uptime
        dashboard_data = monitoring.get_dashboard_data()
        thresholds = monitoring.alert_thresholds
        
        message = "*⚙️ Настройки мониторинга*\n\n"
        message += "**🔧 Текущие пороговые значения:**\n\n"
        
        message += f"💻 **CPU Usage:** {thresholds['cpu_usage']}%%\n"
        message += f"💾 **Memory Usage:** {thresholds['memory_usage']}%%\n"
        message += f"🎮 **GPU Usage:** {thresholds['gpu_usage']}%%\n"
        message += f"🌡️ **GPU Temperature:** {thresholds['gpu_temperature']}°C\n"
        message += f"⏱️ **Response Time:** {thresholds['response_time_ms']}мс\n"
        message += f"❌ **Error Rate:** {thresholds['error_rate_percent']}%%\n\n"
        
        message += "**📊 Параметры сбора данных:**\n"
        message += f"• Интервал сбора: 5 секунд\n"
        message += f"• История: 24 часа (1440 записей)\n"
        message += f"• Лимит активных пользователей: 30 минут\n"
        message += f"• Лимит производительности: 1000 записей\n\n"
        
        message += "**🔄 Статус мониторинга:**\n"
        uptime = dashboard_data.get('uptime_seconds', 0)
        uptime_hours = uptime // 3600
        uptime_minutes = (uptime % 3600) // 60
        message += f"• Работает: {uptime_hours}ч {uptime_minutes}м\n"
        # Нужно импортировать для проверки доступности
        try:
            from toolbot.services.monitoring import GPU_AVAILABLE, TORCH_AVAILABLE
        except ImportError:
            GPU_AVAILABLE, TORCH_AVAILABLE = False, False
            
        message += f"• GPU мониторинг: {'✅ Активен' if GPU_AVAILABLE else '❌ Недоступен'}\n"
        message += f"• PyTorch мониторинг: {'✅ Активен' if TORCH_AVAILABLE else '❌ Недоступен'}"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка в настройках мониторинга: {e}")
        await update.message.reply_text(
            f"❌ Ошибка при получении настроек мониторинга:\n{str(e)}"
        ) 


async def broadcast_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик для отправки сообщений всем пользователям
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    # Устанавливаем состояние ожидания текста сообщения
    context.user_data['state'] = 'awaiting_broadcast_message'

    await update.message.reply_text(
        "*📢 Массовая рассылка*\n\n"
        "Отправьте текст сообщения, которое будет разослано всем пользователям бота.\n\n"
        "⚠️ *Внимание:* Сообщение получат все пользователи, которые когда-либо пользовались ботом!\n\n"
        "💡 Поддерживается *Markdown* форматирование:\n"
        "• `*жирный текст*`\n"
        "• `_курсив_`\n"
        "• `` `код` ``\n"
        "• `[ссылка](URL)`\n\n"
        "🚫 Для отмены отправьте команду /admin",
        parse_mode='Markdown'
    )


async def send_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str) -> None:
    """
    Отправляет сообщение всем пользователям
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    try:
        # Получаем аналитику для списка пользователей
        analytics = context.bot_data.get('analytics')
        if not analytics:
            await update.message.reply_text("❌ Система аналитики недоступна")
            return

        stats = analytics.get_stats()
        users = stats.get("users", {})
        
        if not users:
            await update.message.reply_text("❌ Пользователи не найдены")
            return

        # Получаем список уникальных пользователей
        user_ids = [int(uid) for uid in users.keys()]
        total_users = len(user_ids)
        
        # Подтверждение отправки
        confirm_message = (
            f"*📢 Подтверждение массовой рассылки*\n\n"
            f"**Получателей:** {total_users} пользователей\n\n"
            f"**Ваше сообщение:**\n"
            f"```\n{message_text}\n```\n\n"
            f"⚠️ *Вы уверены, что хотите отправить это сообщение всем пользователям?*"
        )
        
        # Сохраняем текст сообщения для подтверждения
        context.user_data['broadcast_text'] = message_text
        context.user_data['broadcast_users'] = user_ids
        context.user_data['state'] = 'awaiting_broadcast_confirmation'
        
        keyboard = [
            ["✅ Да, отправить", "❌ Отменить"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        await update.message.reply_text(
            confirm_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Ошибка при подготовке рассылки: {e}")
        await update.message.reply_text(
            f"❌ Ошибка при подготовке рассылки:\n{str(e)}"
        )


async def execute_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Выполняет массовую рассылку сообщений
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    try:
        broadcast_text = context.user_data.get('broadcast_text')
        user_ids = context.user_data.get('broadcast_users', [])
        
        if not broadcast_text or not user_ids:
            await update.message.reply_text("❌ Данные для рассылки не найдены")
            return

        # Показываем прогресс
        progress_message = await update.message.reply_text(
            f"📤 **Начинаю рассылку...**\n"
            f"Всего получателей: {len(user_ids)}\n"
            f"Отправлено: 0/{len(user_ids)}",
            parse_mode='Markdown'
        )

        # Статистика отправки
        sent_count = 0
        failed_count = 0
        blocked_count = 0
        failed_users = []

        # Отправляем сообщения порциями, чтобы не превысить лимиты Telegram
        import asyncio
        for i, target_user_id in enumerate(user_ids):
            try:
                # Отправляем сообщение пользователю
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=broadcast_text,
                    parse_mode='Markdown'
                )
                sent_count += 1
                
                # Обновляем прогресс каждые 10 сообщений
                if (i + 1) % 10 == 0 or i == len(user_ids) - 1:
                    await progress_message.edit_text(
                        f"📤 **Выполняется рассылка...**\n"
                        f"Всего получателей: {len(user_ids)}\n"
                        f"✅ Отправлено: {sent_count}\n"
                        f"❌ Ошибок: {failed_count}\n"
                        f"🚫 Заблокировали бота: {blocked_count}\n"
                        f"Прогресс: {i+1}/{len(user_ids)} ({((i+1)/len(user_ids)*100):.1f}%)",
                        parse_mode='Markdown'
                    )
                
                # Пауза между сообщениями, чтобы не превысить лимиты
                await asyncio.sleep(0.05)  # 50мс между сообщениями
                
            except Exception as e:
                error_str = str(e).lower()
                if "blocked" in error_str or "bot was blocked" in error_str:
                    blocked_count += 1
                else:
                    failed_count += 1
                    failed_users.append((target_user_id, str(e)))
                
                logger.warning(f"Не удалось отправить сообщение пользователю {target_user_id}: {e}")

        # Финальный отчет
        success_rate = (sent_count / len(user_ids)) * 100
        
        final_report = (
            f"📊 **Рассылка завершена!**\n\n"
            f"**Статистика:**\n"
            f"• Всего пользователей: {len(user_ids)}\n"
            f"• ✅ Успешно отправлено: {sent_count}\n"
            f"• 🚫 Заблокировали бота: {blocked_count}\n"
            f"• ❌ Ошибки отправки: {failed_count}\n"
            f"• 📈 Успешность: {success_rate:.1f}%\n\n"
        )
        
        if failed_users:
            final_report += f"**Пользователи с ошибками:** {len(failed_users)} чел.\n"
            if len(failed_users) <= 5:
                for uid, error in failed_users:
                    final_report += f"• ID {uid}: {error[:50]}...\n"
            else:
                final_report += f"• Первые 5 из {len(failed_users)} ошибок:\n"
                for uid, error in failed_users[:5]:
                    final_report += f"  - ID {uid}: {error[:40]}...\n"
        
        final_report += f"\n⏰ Время выполнения: ~{len(user_ids) * 0.05:.1f} сек."

        await progress_message.edit_text(final_report, parse_mode='Markdown')
        
        # Логируем рассылку
        analytics = context.bot_data.get('analytics')
        if analytics:
            analytics.log_user_activity(user_id, "broadcast_message", 
                                       f"Отправлено {sent_count}/{len(user_ids)} сообщений")

        # Очищаем состояние
        context.user_data.pop('broadcast_text', None)
        context.user_data.pop('broadcast_users', None)
        context.user_data.pop('state', None)

    except Exception as e:
        logger.error(f"Ошибка при выполнении рассылки: {e}")
        await update.message.reply_text(
            f"❌ Критическая ошибка при рассылке:\n{str(e)}"
        )
        # Очищаем состояние при ошибке
        context.user_data.pop('broadcast_text', None)
        context.user_data.pop('broadcast_users', None)
        context.user_data.pop('state', None)


async def text_logs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик для просмотра логов текстовых сообщений
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    keyboard = [
        ["📊 Статистика текстов", "🔍 Поиск в текстах"],
        ["👤 Сообщения пользователя", "📋 Последние сообщения"],
        ["🧹 Очистка старых логов", "📈 Анализ активности"],
        ["🔙 Назад в админ-панель"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "*📝 Логи текстовых сообщений*\n\n"
        "Выберите действие:\n"
        "• 📊 *Статистика текстов* - общая статистика сообщений\n"
        "• 🔍 *Поиск в текстах* - поиск по содержимому сообщений\n"
        "• 👤 *Сообщения пользователя* - история конкретного пользователя\n"
        "• 📋 *Последние сообщения* - недавние текстовые сообщения\n"
        "• 🧹 *Очистка старых логов* - удаление старых записей\n"
        "• 📈 *Анализ активности* - паттерны использования\n\n"
        "💡 _Все текстовые сообщения логируются в SQLite базу_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def text_logs_statistics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает статистику текстовых логов
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    try:
        from services.text_logging_service import get_text_logging_service
        
        text_logger = get_text_logging_service()
        stats = text_logger.get_statistics()
        
        if not stats:
            await update.message.reply_text("❌ Статистика недоступна")
            return

        message = "*📊 Статистика текстовых сообщений*\n\n"
        
        # Основные цифры
        message += f"**Общая статистика:**\n"
        message += f"• Всего сообщений: {stats.get('total_messages', 0)}\n"
        message += f"• Уникальных пользователей: {stats.get('unique_users', 0)}\n"
        message += f"• За последние 24 часа: {stats.get('messages_24h', 0)}\n\n"
        
        # Статистика по типам
        message_types = stats.get('message_types', {})
        if message_types:
            message += f"**По типам сообщений:**\n"
            for msg_type, count in list(message_types.items())[:7]:  # Топ-7
                type_emoji = {
                    'text': '💬',
                    'command': '⚡',
                    'admin_input': '👑',
                    'search_query': '🔍',
                    'feedback': '📝',
                    'broadcast_input': '📢'
                }.get(msg_type, '📄')
                message += f"• {type_emoji} {msg_type}: {count}\n"
            message += "\n"
        
        # Топ активных пользователей
        top_users = stats.get('top_users', [])
        if top_users:
            message += f"**Топ активных пользователей:**\n"
            for i, user in enumerate(top_users[:5], 1):
                username_display = f"@{user['username']}" if user['username'] else f"ID {user['user_id']}"
                message += f"{i}. {username_display}: {user['message_count']} сообщений\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка в статистике текстов: {e}")
        await update.message.reply_text(f"❌ Ошибка при получении статистики:\n{str(e)}")


async def search_in_texts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик поиска в текстовых сообщениях
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    # Устанавливаем состояние ожидания поискового запроса
    context.user_data['state'] = 'awaiting_text_search_query'

    await update.message.reply_text(
        "*🔍 Поиск в текстовых сообщениях*\n\n"
        "Отправьте слово или фразу для поиска в логах текстовых сообщений.\n\n"
        "⚠️ *Внимание:* Поиск производится по ВСЕМ сохраненным сообщениям!\n\n"
        "💡 Примеры запросов:\n"
        "• `товар` - найти сообщения со словом 'товар'\n"
        "• `/start` - найти команды старта\n"
        "• `ошибка` - найти жалобы на ошибки\n\n"
        "🚫 Для отмены отправьте команду /admin",
        parse_mode='Markdown'
    )


async def user_messages_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик просмотра сообщений конкретного пользователя
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    # Устанавливаем состояние ожидания ID пользователя
    context.user_data['state'] = 'awaiting_user_messages_id'

    await update.message.reply_text(
        "*👤 Сообщения пользователя*\n\n"
        "Отправьте ID пользователя, чьи сообщения хотите посмотреть.\n\n"
        "📋 Показываются последние 20 сообщений с временными метками и типами.\n\n"
        "🚫 Для отмены отправьте команду /admin",
        parse_mode='Markdown'
    )


async def recent_messages_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает последние текстовые сообщения
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    try:
        from services.text_logging_service import get_text_logging_service
        import sqlite3
        
        text_logger = get_text_logging_service()
        
        # Получаем последние 20 сообщений
        conn = sqlite3.connect(text_logger.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, username, message_text, timestamp, message_type, is_admin
            FROM text_messages 
            ORDER BY timestamp DESC
            LIMIT 20
        ''')
        
        messages = cursor.fetchall()
        conn.close()
        
        if not messages:
            await update.message.reply_text("📋 Текстовых сообщений пока нет")
            return

        message_text = "📋 Последние текстовые сообщения\n\n"
        
        for i, msg in enumerate(messages, 1):
            user_id_msg, username, text, timestamp, msg_type, is_admin_flag = msg
            
            # Форматируем время
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime("%H:%M")
            except:
                time_str = timestamp[:16]
            
            # Эмодзи для типа сообщения
            type_emoji = {
                'text': '💬',
                'command': '⚡',
                'admin_input': '👑',
                'search_query': '🔍',
                'feedback': '📝',
                'broadcast_input': '📢'
            }.get(msg_type, '📄')
            
            # Безопасное экранирование текста
            text_short = text[:50] + "..." if len(text) > 50 else text
            text_safe = text_short.replace('\\', '\\\\').replace('*', '\\*').replace('_', '\\_').replace('`', '\\`').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
            
            # Отметка админа
            admin_mark = " 👑" if is_admin_flag else ""
            username_display = f"@{username}" if username else f"ID{user_id_msg}"
            
            message_text += f"{i}\\. {type_emoji} {time_str} {username_display}{admin_mark}\n"
            message_text += f"   {text_safe}\n\n"
            
            # Ограничиваем длину сообщения
            if len(message_text) > 3000:
                message_text += f"\\.\\.\\. и ещё {len(messages) - i} сообщений"
                break

        await update.message.reply_text(message_text, parse_mode='MarkdownV2')
        
    except Exception as e:
        logger.error(f"Ошибка при получении последних сообщений: {e}")
        # Отправляем без Markdown при ошибке
        error_msg = f"❌ Ошибка при получении сообщений: {str(e)}"
        await update.message.reply_text(error_msg)


async def cleanup_old_texts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик очистки старых текстовых логов
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    keyboard = [
        ["🗑️ Удалить старше 30 дней", "🗑️ Удалить старше 7 дней"],
        ["📊 Показать размер базы", "🔙 Назад к логам"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "*🧹 Очистка логов текстовых сообщений*\n\n"
        "⚠️ *Внимание:* Удаленные логи восстановить невозможно!\n\n"
        "Выберите период для удаления:\n"
        "• Старше 30 дней - стандартная очистка\n"
        "• Старше 7 дней - агрессивная очистка\n"
        "• Показать размер базы - текущее состояние\n\n"
        "💡 _Рекомендуется регулярно очищать старые логи_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def perform_text_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
    """
    Выполняет поиск в текстовых сообщениях
    """
    try:
        from services.text_logging_service import get_text_logging_service
        
        text_logger = get_text_logging_service()
        results = text_logger.search_messages(query, limit=20)
        
        if not results:
            await update.message.reply_text(f"🔍 По запросу '{query}' ничего не найдено.")
            context.user_data.pop('state', None)
            return

        message_text = f"🔍 Результаты поиска: '{query}'\n\n"
        message_text += f"Найдено: {len(results)} сообщений\n\n"
        
        for i, result in enumerate(results[:15], 1):  # Показываем первые 15
            user_id_res = result['user_id']
            username = result['username']
            text = result['text']
            timestamp = result['timestamp']
            msg_type = result['type']
            
            # Форматируем время
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime("%d.%m %H:%M")
            except:
                time_str = timestamp[:16]
            
            # Подсвечиваем найденный текст (без Markdown)
            if len(text) > 100:
                # Находим позицию искомого текста и показываем контекст
                pos = text.lower().find(query.lower())
                start = max(0, pos - 30)
                end = min(len(text), pos + len(query) + 30)
                context_text = text[start:end]
                if start > 0:
                    context_text = "..." + context_text
                if end < len(text):
                    context_text = context_text + "..."
                display_text = context_text
            else:
                display_text = text
            
            # Безопасное экранирование всех специальных символов
            text_safe = display_text.replace('\\', '\\\\').replace('*', '\\*').replace('_', '\\_').replace('`', '\\`').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
            
            username_display = f"@{username}" if username else f"ID{user_id_res}"
            
            message_text += f"{i}\\. {time_str} {username_display} \\({msg_type}\\)\n"
            message_text += f"   {text_safe}\n\n"
            
            # Ограничиваем длину сообщения
            if len(message_text) > 3000:
                message_text += f"\\.\\.\\. и ещё {len(results) - i} результатов"
                break

        await update.message.reply_text(message_text, parse_mode='MarkdownV2')
        
        # Очищаем состояние
        context.user_data.pop('state', None)
        
    except Exception as e:
        logger.error(f"Ошибка при поиске в текстах: {e}")
        # Отправляем без Markdown при ошибке
        error_msg = f"❌ Ошибка при поиске: {str(e)}"
        await update.message.reply_text(error_msg)
        context.user_data.pop('state', None)


async def show_user_messages(update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id: int) -> None:
    """
    Показывает сообщения конкретного пользователя
    """
    try:
        from services.text_logging_service import get_text_logging_service
        
        text_logger = get_text_logging_service()
        messages = text_logger.get_user_messages(target_user_id, limit=20)
        
        if not messages:
            await update.message.reply_text(f"👤 У пользователя ID {target_user_id} нет текстовых сообщений.")
            context.user_data.pop('state', None)
            return

        message_text = f"👤 Сообщения пользователя ID {target_user_id}\n\n"
        message_text += f"Всего найдено: {len(messages)} сообщений\n\n"
        
        for i, msg in enumerate(messages, 1):
            timestamp = msg['timestamp']
            text = msg['text']
            msg_type = msg['type']
            state = msg['state']
            
            # Форматируем время
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime("%d.%m %H:%M")
            except:
                time_str = timestamp[:16]
            
            # Эмодзи для типа сообщения
            type_emoji = {
                'text': '💬',
                'command': '⚡',
                'admin_input': '👑',
                'search_query': '🔍',
                'feedback': '📝',
                'broadcast_input': '📢'
            }.get(msg_type, '📄')
            
            # Безопасное экранирование текста
            text_short = text[:80] + "..." if len(text) > 80 else text
            # Полное экранирование всех специальных символов Markdown
            text_safe = text_short.replace('\\', '\\\\').replace('*', '\\*').replace('_', '\\_').replace('`', '\\`').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
            
            state_info = f" [{state}]" if state and state != 'none' else ""
            
            message_text += f"{i}\\. {type_emoji} {time_str}{state_info}\n"
            message_text += f"   {text_safe}\n\n"
            
            # Ограничиваем длину сообщения
            if len(message_text) > 3000:
                message_text += f"\\.\\.\\. и ещё {len(messages) - i} сообщений"
                break

        await update.message.reply_text(message_text, parse_mode='MarkdownV2')
        
        # Очищаем состояние
        context.user_data.pop('state', None)
        
    except Exception as e:
        logger.error(f"Ошибка при получении сообщений пользователя {target_user_id}: {e}")
        # Отправляем без Markdown при ошибке
        error_msg = f"❌ Ошибка при получении сообщений: {str(e)}"
        await update.message.reply_text(error_msg)
        context.user_data.pop('state', None)