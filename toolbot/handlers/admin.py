"""
Обработчики команд для административной панели телеграм-бота.
"""
import logging
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
        ["👑 Добавить администратора"],
        ["🔄 Обновить базы"],
        ["🔙 Назад в меню"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "*🛠️ Панель администратора*\n\n"
        "Выберите действие:\n"
        "• 👥 Управление пользователями - добавление/удаление пользователей\n"
        "• 💬 Обратная связь - просмотр ошибок и предложений\n"
        "• 📊 Статистика поиска - анализ эффективности поиска\n"
        "• 👀 Активность пользователей - мониторинг входов и действий\n"
        "• 👑 Добавить администратора - назначение нового админа\n"
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
    
    # Обработка ввода ID пользователя для добавления
    if state == 'awaiting_new_user_id':
        try:
            new_user_id = int(text.strip())
            
            if add_user_to_whitelist(new_user_id):
                await update.message.reply_text(f"✅ Пользователь с ID {new_user_id} успешно добавлен.")
            else:
                await update.message.reply_text("❌ Не удалось добавить пользователя. Проверьте логи.")
                
            # Сбрасываем состояние
            context.user_data.pop('state', None)
            return True
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID. Пожалуйста, введите числовой ID.")
            return True
    
    # Обработка ввода ID пользователя для удаления
    elif state == 'awaiting_remove_user_id':
        try:
            user_id_to_remove = int(text.strip())
            
            if remove_user_from_whitelist(user_id_to_remove):
                await update.message.reply_text(f"✅ Пользователь с ID {user_id_to_remove} успешно удален.")
            else:
                await update.message.reply_text("❌ Не удалось удалить пользователя. Проверьте логи.")
                
            # Сбрасываем состояние
            context.user_data.pop('state', None)
            return True
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID. Пожалуйста, введите числовой ID.")
            return True
    
    # Обработка ввода ID пользователя для назначения администратором
    elif state == 'awaiting_new_admin_id':
        try:
            new_admin_id = int(text.strip())
            
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
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID. Пожалуйста, введите числовой ID.")
            return True
    
    # Обработка поиска пользователя по ID
    elif state == 'awaiting_user_search_id':
        try:
            search_user_id = int(text.strip())
            
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
            
            message = f"*🔍 Информация о пользователе {search_user_id}*\n\n"
            message += f"📊 *Статус:* {status}\n"
            message += f"👤 *Первый вход:* {first_seen_str}\n"
            message += f"⏰ *Последний вход:* {last_seen_str}\n"
            message += f"📞 *Всего запросов:* {total_requests}\n\n"
            
            # Топ команд пользователя
            if commands:
                message += "*🔝 Популярные команды:*\n"
                sorted_commands = sorted(commands.items(), key=lambda x: x[1], reverse=True)
                for cmd, count in sorted_commands[:5]:
                    message += f"• `{cmd}` - {count}x\n"
                message += "\n"
            
            # Последняя активность
            if activity_log:
                message += "*📝 Последняя активность:*\n"
                for activity in activity_log[-5:]:  # Последние 5 записей
                    timestamp = activity.get('timestamp', 0)
                    activity_type = activity.get('type', 'unknown')
                    details = activity.get('details', '')
                    
                    activity_dt = datetime.datetime.fromtimestamp(timestamp)
                    activity_str = activity_dt.strftime("%d.%m %H:%M")
                    
                    # Сокращаем детали для отображения
                    short_details = details[:30] + "..." if len(details) > 30 else details
                    
                    message += f"• {activity_str} - {activity_type}: {short_details}\n"
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )
                
            # Сбрасываем состояние
            context.user_data.pop('state', None)
            return True
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID. Пожалуйста, введите числовой ID.")
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
        message += f"• Процент успеха: {success_stats.get('success_rate_percent', 0)}%\n"
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
                message += f"   Успешность: {success_rate:.1f}%\n"
        
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
                
                status_info += f"✅ *SQLite база:* {count:,} товаров\n"
                status_info += f"   Размер: {file_size:.1f} МБ\n"
                status_info += f"   Обновлена: {mod_time.strftime('%d.%m.%Y %H:%M')}\n\n"
                
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
            
            status_info += f"✅ *TXT экспорт:* {lines:,} товаров\n"
            status_info += f"   Размер: {file_size:.1f} МБ\n"
            status_info += f"   Обновлен: {mod_time.strftime('%d.%m.%Y %H:%M')}\n\n"
        else:
            status_info += f"❌ *TXT экспорт:* Файл не найден\n\n"
        
        # Проверяем CSV экспорт
        if os.path.exists(csv_path):
            file_size = os.path.getsize(csv_path) / (1024 * 1024)  # МБ
            mod_time = datetime.fromtimestamp(os.path.getmtime(csv_path))
            
            status_info += f"✅ *CSV экспорт:* доступен\n"
            status_info += f"   Размер: {file_size:.1f} МБ\n"
            status_info += f"   Обновлен: {mod_time.strftime('%d.%m.%Y %H:%M')}\n\n"
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