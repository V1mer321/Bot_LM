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
        ["📊 Статистика поиска"],
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