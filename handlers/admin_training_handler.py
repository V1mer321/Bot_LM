import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.training_data_service import get_training_service
from services.model_training_service import get_model_training_service

logger = logging.getLogger(__name__)

# ID администраторов (можно вынести в config)
ADMIN_USER_IDS = [2093834331]  # ID администратора из логов

def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    # Пытаемся использовать проверку из основной системы бота
    try:
        from toolbot.utils.access import is_allowed_user
        from toolbot.config import load_config
        
        config = load_config()
        if config:
            admin_ids = config.get('admin_users', []) or config.get('admin_ids', []) or config.get('admins', [])
            if user_id in admin_ids:
                return True
    except Exception as e:
        logger.warning(f"Не удалось проверить права через основную систему: {e}")
    
    # Fallback на локальный список
    return user_id in ADMIN_USER_IDS

async def admin_training_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /admin_training_stats - статистика обучающих данных"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав администратора")
        return
    
    try:
        training_service = get_training_service()
        stats = training_service.get_training_statistics()
        
        stats_text = f"""
🧠 **Статистика дообучения моделей:**

📊 **Обучающие примеры:**
• Всего примеров: {stats.get('total_examples', 0)}
• Использованные: {stats.get('used_for_training', 0)}
• Неиспользованные: {stats.get('unused_examples', 0)}

📋 **По типам обратной связи:**
"""
        
        feedback_types = stats.get('by_feedback_type', {})
        for feedback_type, count in feedback_types.items():
            emoji = "✅" if feedback_type == "correct" else "❌" if feedback_type == "incorrect" else "➕"
            stats_text += f"• {emoji} {feedback_type}: {count}\n"
        
        stats_text += f"""

🆕 **Новые товары:**
• Аннотаций: {stats.get('new_products_annotations', 0)}
• Одобренных: {stats.get('approved_new_products', 0)}

🎯 **Сессии обучения:**
• Всего сессий: {stats.get('training_sessions', 0)}

🤖 **Текущая модель:**
• Версия: {stats.get('current_model', {}).get('version', 'Не установлена')}
• Точность: {stats.get('current_model', {}).get('accuracy', 'Н/Д')}
• Дата: {stats.get('current_model', {}).get('date', 'Н/Д')}
"""
        
        # Кнопки управления
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить статистику", callback_data="admin_refresh_training_stats")],
            [InlineKeyboardButton("📝 Просмотреть примеры", callback_data="admin_view_examples")],
            [InlineKeyboardButton("🚀 Запустить дообучение", callback_data="admin_start_training")],
            [InlineKeyboardButton("➕ Управление новыми товарами", callback_data="admin_manage_new_products")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(stats_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики обучения: {e}")
        await update.message.reply_text("❌ Ошибка при получении статистики")

async def admin_start_training_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /admin_start_training - запуск дообучения"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав администратора")
        return
    
    try:
        training_service = get_model_training_service()
        
        # Получаем рекомендации
        recommendations = training_service.get_training_recommendations()
        
        if not recommendations.get('should_train', False):
            reasons_text = "\n".join([f"• {reason}" for reason in recommendations.get('reasons', [])])
            await update.message.reply_text(
                f"ℹ️ Дообучение пока не рекомендуется:\n\n{reasons_text}\n\n"
                f"Накопите больше обучающих примеров для лучшего результата."
            )
            return
        
        # Подтверждение запуска обучения
        reasons_text = "\n".join([f"• {reason}" for reason in recommendations.get('reasons', [])])
        
        keyboard = [
            [InlineKeyboardButton("✅ Запустить дообучение", callback_data="admin_confirm_training")],
            [InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel_training")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🚀 **Готов к запуску дообучения!**\n\n"
            f"📊 Рекомендации:\n{reasons_text}\n\n"
            f"⚠️ Процесс может занять несколько минут.\n"
            f"🔄 Бот будет недоступен во время обучения.\n\n"
            f"Подтвердить запуск?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Ошибка при подготовке к дообучению: {e}")
        await update.message.reply_text("❌ Ошибка при подготовке к дообучению")

async def admin_view_examples_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /admin_view_examples - просмотр обучающих примеров"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав администратора")
        return
    
    try:
        training_service = get_training_service()
        
        # Получаем примеры разных типов
        correct_examples = training_service.get_training_examples(feedback_type='correct', limit=5)
        incorrect_examples = training_service.get_training_examples(feedback_type='incorrect', limit=5)
        unused_examples = training_service.get_training_examples(is_used=False, limit=10)
        
        examples_text = f"""
📝 **Обучающие примеры:**

✅ **Правильные примеры ({len(correct_examples)}):**
"""
        
        for ex in correct_examples[:3]:
            examples_text += f"• ID: {ex['id']}, Товар: {ex.get('target_item_id', 'Н/Д')}, Схожесть: {ex.get('similarity_score', 0):.3f}\n"
        
        examples_text += f"""

❌ **Неправильные примеры ({len(incorrect_examples)}):**
"""
        
        for ex in incorrect_examples[:3]:
            examples_text += f"• ID: {ex['id']}, Товар: {ex.get('target_item_id', 'Н/Д')}, Схожесть: {ex.get('similarity_score', 0):.3f}\n"
        
        examples_text += f"""

🆕 **Неиспользованные примеры ({len(unused_examples)}):**
"""
        
        for ex in unused_examples[:5]:
            feedback_emoji = "✅" if ex['feedback_type'] == 'correct' else "❌"
            examples_text += f"• {feedback_emoji} ID: {ex['id']}, Тип: {ex['feedback_type']}\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_refresh_training_stats")],
            [InlineKeyboardButton("🔄 Обновить список", callback_data="admin_refresh_examples")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(examples_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка при просмотре примеров: {e}")
        await update.message.reply_text("❌ Ошибка при получении примеров")

async def admin_manage_new_products_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /admin_new_products - управление новыми товарами"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав администратора")
        return
    
    try:
        training_service = get_training_service()
        pending_products = training_service.get_pending_new_products(limit=10)
        
        if not pending_products:
            await update.message.reply_text(
                "✅ Нет новых товаров для рассмотрения\n\n"
                "📝 Все поступившие заявки уже обработаны."
            )
            return
        
        products_text = f"➕ **Новые товары для рассмотрения ({len(pending_products)}):**\n\n"
        
        for i, product in enumerate(pending_products[:5], 1):
            products_text += f"""
**{i}. {product['product_name']}**
📂 Категория: {product.get('product_category', 'Не указана')}
📋 Описание: {product.get('product_description', 'Не указано')}
👤 От пользователя: {product.get('username', 'Аноним')} (ID: {product['user_id']})
📅 Дата: {product['created_at']}
🔗 ID аннотации: #{product['id']}

"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Одобрить товары", callback_data="admin_approve_products")],
            [InlineKeyboardButton("❌ Отклонить товары", callback_data="admin_reject_products")],
            [InlineKeyboardButton("📋 Подробный просмотр", callback_data="admin_detailed_products")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(products_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка при управлении новыми товарами: {e}")
        await update.message.reply_text("❌ Ошибка при получении новых товаров")

async def admin_model_backups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /admin_model_backups - управление резервными копиями моделей"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав администратора")
        return
    
    try:
        model_service = get_model_training_service()
        backups = model_service.list_model_backups()
        
        if not backups:
            backups_text = """💾 Управление резервными копиями моделей

📁 Резервные копии не найдены

Резервные копии создаются автоматически:
• Перед каждым дообучением
• При восстановлении из резервной копии
• Можно создать вручную для текущей модели"""
        else:
            backups_text = f"""💾 Управление резервными копиями моделей

📁 Найдено резервных копий: {len(backups)}

"""
            
            for i, backup in enumerate(backups[:10], 1):  # Показываем первые 10
                size_mb = backup['file_size'] / (1024 * 1024)
                backup_type = backup['backup_type']
                
                emoji = "🔄" if backup_type == "manual" else "⚡" if backup_type == "auto" else "🔙"
                
                backups_text += f"""{emoji} {i}. {backup['backup_id']}
   📅 {backup['created_at'][:19]}
   💾 {size_mb:.1f} MB ({backup_type})

"""
        
        keyboard = [
            [InlineKeyboardButton("💾 Создать резервную копию", callback_data="admin_create_backup")],
            [InlineKeyboardButton("📋 Список всех копий", callback_data="admin_list_backups")],
            [InlineKeyboardButton("🔄 Восстановить из копии", callback_data="admin_restore_backup")],
            [InlineKeyboardButton("🗑️ Очистить старые копии", callback_data="admin_cleanup_backups")],
            [InlineKeyboardButton("📊 К статистике", callback_data="admin_refresh_training_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(backups_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка при получении резервных копий: {e}")
        await update.message.reply_text("❌ Ошибка при работе с резервными копиями")

# ================= CALLBACK ОБРАБОТЧИКИ =================

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-кнопок администратора"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    await query.answer()
    
    try:
        if query.data == "admin_refresh_training_stats":
            await refresh_training_stats(query, context)
        
        elif query.data == "admin_view_examples":
            await view_training_examples(query, context)
        
        elif query.data == "admin_start_training":
            await start_training_process(query, context)
        
        elif query.data == "admin_confirm_training":
            await confirm_training_start(query, context)
        
        elif query.data == "admin_cancel_training":
            await query.edit_message_text("❌ Дообучение отменено")
        
        elif query.data == "admin_manage_new_products":
            await manage_new_products(query, context)
        
        elif query.data == "admin_approve_products":
            await approve_new_products(query, context)
        
        elif query.data == "admin_refresh_examples":
            await view_training_examples(query, context)
        
        # Обработчики резервных копий
        elif query.data == "admin_create_backup":
            await create_model_backup(query, context)
        
        elif query.data == "admin_list_backups":
            await list_model_backups(query, context)
        
        elif query.data == "admin_restore_backup":
            await restore_backup_menu(query, context)
        
        elif query.data == "admin_cleanup_backups":
            await cleanup_old_backups(query, context)
        
        elif query.data.startswith("admin_restore_"):
            # Обработка восстановления конкретной резервной копии
            backup_id = query.data.replace("admin_restore_", "")
            await restore_specific_backup(query, context, backup_id)
        
        else:
            await query.edit_message_text("❓ Неизвестная команда")
            
    except Exception as e:
        logger.error(f"Ошибка в admin callback: {e}")
        await query.edit_message_text("❌ Произошла ошибка при обработке команды")

async def confirm_training_start(query, context):
    """Подтверждение и запуск дообучения"""
    await query.edit_message_text("🚀 Запуск дообучения...\n\n⏳ Пожалуйста, подождите...")
    
    try:
        training_service = get_model_training_service()
        
        # Подготавливаем данные
        train_data, val_data = training_service.prepare_training_data(min_examples=10)
        
        if not train_data:
            await query.edit_message_text(
                "❌ Недостаточно обучающих данных для запуска дообучения.\n\n"
                "📊 Накопите больше примеров и попробуйте снова."
            )
            return
        
        # Запускаем дообучение
        result = training_service.fine_tune_model(train_data, val_data)
        
        if result.get('success'):
            success_text = f"""
✅ **Дообучение завершено успешно!**

🤖 Модель: {result.get('model_version')}
📊 Использовано примеров: {result.get('examples_used')}
⏱️ Время обучения: {result.get('training_duration')} сек
📈 Точность до: {result.get('accuracy_before', 'Н/Д'):.3f}
📈 Точность после: {result.get('accuracy_after', 'Н/Д'):.3f}

🎯 Модель обновлена и готова к использованию!
"""
            await query.edit_message_text(success_text, parse_mode='Markdown')
        else:
            error_text = f"❌ Ошибка при дообучении:\n\n{result.get('error', 'Неизвестная ошибка')}"
            await query.edit_message_text(error_text)
            
    except Exception as e:
        logger.error(f"Ошибка при дообучении: {e}")
        await query.edit_message_text(f"❌ Критическая ошибка при дообучении:\n\n{str(e)}")

async def refresh_training_stats(query, context):
    """Обновление статистики обучения"""
    training_service = get_training_service()
    stats = training_service.get_training_statistics()
    
    # Аналогично admin_training_stats_command, но через edit_message
    stats_text = f"""
🧠 **Статистика дообучения (обновлено):**

📊 Всего примеров: {stats.get('total_examples', 0)}
📈 Неиспользованные: {stats.get('unused_examples', 0)}
🆕 Новых товаров: {stats.get('new_products_annotations', 0)}
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_refresh_training_stats")],
        [InlineKeyboardButton("🚀 Запустить дообучение", callback_data="admin_start_training")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup)

async def view_training_examples(query, context):
    """Просмотр обучающих примеров через callback"""
    try:
        training_service = get_training_service()
        
        # Получаем примеры разных типов
        correct_examples = training_service.get_training_examples(feedback_type='correct', limit=5)
        incorrect_examples = training_service.get_training_examples(feedback_type='incorrect', limit=5)
        unused_examples = training_service.get_training_examples(is_used=False, limit=10)
        
        examples_text = f"""
📝 **Обучающие примеры (обновлено):**

✅ **Правильные примеры ({len(correct_examples)}):**
"""
        
        for ex in correct_examples[:3]:
            examples_text += f"• ID: {ex['id']}, Товар: {ex.get('target_item_id', 'Н/Д')}, Схожесть: {ex.get('similarity_score', 0):.3f}\n"
        
        examples_text += f"""

❌ **Неправильные примеры ({len(incorrect_examples)}):**
"""
        
        for ex in incorrect_examples[:3]:
            examples_text += f"• ID: {ex['id']}, Товар: {ex.get('target_item_id', 'Н/Д')}, Схожесть: {ex.get('similarity_score', 0):.3f}\n"
        
        examples_text += f"""

🆕 **Неиспользованные примеры ({len(unused_examples)}):**
"""
        
        for ex in unused_examples[:5]:
            feedback_emoji = "✅" if ex['feedback_type'] == 'correct' else "❌"
            examples_text += f"• {feedback_emoji} ID: {ex['id']}, Тип: {ex['feedback_type']}\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_refresh_training_stats")],
            [InlineKeyboardButton("🔄 Обновить список", callback_data="admin_refresh_examples")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(examples_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка при просмотре примеров: {e}")
        await query.edit_message_text("❌ Ошибка при получении примеров")

async def start_training_process(query, context):
    """Запуск процесса дообучения через callback"""
    try:
        training_service = get_training_service()
        stats = training_service.get_training_statistics()
        
        total_examples = stats.get('total_examples', 0)
        unused_examples = stats.get('unused_examples', 0)
        
        if total_examples < 10:
            await query.edit_message_text(
                f"❌ Недостаточно обучающих данных для дообучения!\n\n"
                f"📊 Есть примеров: {total_examples}\n"
                f"🎯 Нужно минимум: 10\n\n"
                f"📈 Накопите больше пользовательской обратной связи и попробуйте снова."
            )
            return
        
        confirmation_text = f"""
🤖 **Подтверждение дообучения модели**

📊 **Данные для обучения:**
• Всего примеров: {total_examples}
• Неиспользованных: {unused_examples}

⚠️ **Внимание:**
• Процесс займет 5-15 минут
• Бот будет недоступен во время обучения
• Рекомендуется делать резервную копию

🚀 Начать дообучение?
"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Да, запустить", callback_data="admin_confirm_training")],
            [InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel_training")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(confirmation_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка при подготовке дообучения: {e}")
        await query.edit_message_text("❌ Ошибка при подготовке дообучения")

async def manage_new_products(query, context):
    """Управление новыми товарами через callback"""
    try:
        training_service = get_training_service()
        pending_products = training_service.get_pending_new_products(limit=10)
        
        if not pending_products:
            await query.edit_message_text(
                "✅ Нет новых товаров для рассмотрения\n\n"
                "📝 Все поступившие заявки уже обработаны."
            )
            return
        
        products_text = f"➕ **Новые товары для рассмотрения ({len(pending_products)}):**\n\n"
        
        for i, product in enumerate(pending_products[:3], 1):
            products_text += f"""
**{i}. {product['product_name']}**
📂 Категория: {product.get('product_category', 'Не указана')}
👤 От: {product.get('username', 'Аноним')}
📅 {product['created_at']}

"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Одобрить товары", callback_data="admin_approve_products")],
            [InlineKeyboardButton("❌ Отклонить товары", callback_data="admin_reject_products")],
            [InlineKeyboardButton("🔄 Обновить список", callback_data="admin_manage_new_products")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(products_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка при управлении товарами: {e}")
        await query.edit_message_text("❌ Ошибка при получении товаров")

async def approve_new_products(query, context):
    """Одобрение новых товаров"""
    try:
        training_service = get_training_service()
        pending_products = training_service.get_pending_new_products(limit=5)
        
        if not pending_products:
            await query.edit_message_text("✅ Нет товаров для одобрения")
            return
        
        approved_count = 0
        for product in pending_products:
            # Здесь можно добавить логику одобрения товара
            # Например, обновить статус в БД
            try:
                training_service.approve_new_product(product['id'])
                approved_count += 1
            except Exception as e:
                logger.error(f"Ошибка одобрения товара {product['id']}: {e}")
        
        result_text = f"""
✅ **Товары одобрены!**

📦 Одобрено товаров: {approved_count}
📧 Пользователи получат уведомления
🔄 Товары будут добавлены в каталог

🎯 Рекомендуется запустить переиндексацию каталога.
"""
        
        await query.edit_message_text(result_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка при одобрении товаров: {e}")
        await query.edit_message_text("❌ Ошибка при одобрении товаров")

async def create_model_backup(query, context):
    """Создание резервной копии модели"""
    await query.edit_message_text("💾 Создание резервной копии...\n\n⏳ Пожалуйста, подождите...")
    
    try:
        model_service = get_model_training_service()
        result = model_service.create_model_backup()
        
        if result.get('success'):
            size_mb = result.get('size', 0) / (1024 * 1024)
            success_text = f"""✅ Резервная копия создана успешно!

💾 ID резервной копии: {result.get('backup_id')}
📅 Дата создания: {result.get('created_at', '')[:19]}
📊 Размер файла: {size_mb:.1f} MB
📁 Путь: models/backups/

Резервная копия сохранена и готова к использованию."""
            
            keyboard = [
                [InlineKeyboardButton("📋 Список резервных копий", callback_data="admin_list_backups")],
                [InlineKeyboardButton("📊 К статистике", callback_data="admin_refresh_training_stats")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(success_text, reply_markup=reply_markup)
        else:
            error_text = f"❌ Ошибка при создании резервной копии:\n\n{result.get('error', 'Неизвестная ошибка')}"
            await query.edit_message_text(error_text)
            
    except Exception as e:
        logger.error(f"Ошибка при создании резервной копии: {e}")
        await query.edit_message_text(f"❌ Ошибка при создании резервной копии:\n\n{str(e)}")

async def list_model_backups(query, context):
    """Подробный список резервных копий"""
    try:
        model_service = get_model_training_service()
        backups = model_service.list_model_backups()
        
        if not backups:
            await query.edit_message_text(
                "📁 Резервные копии не найдены\n\n"
                "Создайте первую резервную копию текущей модели."
            )
            return
        
        backups_text = f"📋 Все резервные копии ({len(backups)}):\n\n"
        
        for i, backup in enumerate(backups, 1):
            size_mb = backup['file_size'] / (1024 * 1024)
            backup_type = backup['backup_type']
            
            emoji = "🔄" if backup_type == "manual" else "⚡" if backup_type == "auto" else "🔙"
            
            backups_text += f"""{emoji} {i}. {backup['backup_id']}
📅 {backup['created_at'][:19]}
💾 {size_mb:.1f} MB
🏷️ Тип: {backup_type}
📁 {backup['model_type']}

"""
        
        keyboard = [
            [InlineKeyboardButton("💾 Создать новую копию", callback_data="admin_create_backup")],
            [InlineKeyboardButton("🔄 Восстановить", callback_data="admin_restore_backup")],
            [InlineKeyboardButton("🗑️ Очистить старые", callback_data="admin_cleanup_backups")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(backups_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка копий: {e}")
        await query.edit_message_text("❌ Ошибка при получении списка резервных копий")

async def restore_backup_menu(query, context):
    """Меню выбора резервной копии для восстановления"""
    try:
        model_service = get_model_training_service()
        backups = model_service.list_model_backups()
        
        if not backups:
            await query.edit_message_text("📁 Нет доступных резервных копий для восстановления")
            return
        
        restore_text = "🔄 Выберите резервную копию для восстановления:\n\n"
        
        keyboard = []
        for backup in backups[:10]:  # Показываем только первые 10
            size_mb = backup['file_size'] / (1024 * 1024)
            button_text = f"{backup['backup_id'][:20]}... ({size_mb:.1f}MB)"
            callback_data = f"admin_restore_{backup['backup_id']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="admin_list_backups")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        restore_text += "⚠️ ВНИМАНИЕ: Текущая модель будет заменена!\nАвтоматически создастся резервная копия текущей модели."
        
        await query.edit_message_text(restore_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка при подготовке меню восстановления: {e}")
        await query.edit_message_text("❌ Ошибка при подготовке восстановления")

async def restore_specific_backup(query, context, backup_id: str):
    """Восстановление конкретной резервной копии"""
    await query.edit_message_text(f"🔄 Восстановление из резервной копии...\n\n⏳ ID: {backup_id}")
    
    try:
        model_service = get_model_training_service()
        result = model_service.restore_model_from_backup(backup_id)
        
        if result.get('success'):
            success_text = f"""✅ Модель успешно восстановлена!

🔄 Восстановлена копия: {backup_id}
📅 Время восстановления: {result.get('restored_at', '')[:19]}
💾 Создана резервная копия текущей модели

Модель готова к использованию."""
            
            keyboard = [
                [InlineKeyboardButton("📋 Список копий", callback_data="admin_list_backups")],
                [InlineKeyboardButton("📊 К статистике", callback_data="admin_refresh_training_stats")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(success_text, reply_markup=reply_markup)
        else:
            error_text = f"❌ Ошибка при восстановлении:\n\n{result.get('error', 'Неизвестная ошибка')}"
            await query.edit_message_text(error_text)
            
    except Exception as e:
        logger.error(f"Ошибка при восстановлении: {e}")
        await query.edit_message_text(f"❌ Ошибка при восстановлении:\n\n{str(e)}")

async def cleanup_old_backups(query, context):
    """Очистка старых резервных копий"""
    await query.edit_message_text("🗑️ Очистка старых резервных копий...\n\n⏳ Пожалуйста, подождите...")
    
    try:
        model_service = get_model_training_service()
        result = model_service.cleanup_old_backups(keep_count=10)  # Оставляем 10 последних
        
        if result.get('success'):
            cleanup_text = f"""✅ Очистка завершена!

🗑️ Удалено копий: {result.get('deleted_count', 0)}
💾 Сохранено копий: {result.get('kept_count', 0)}

{result.get('message', '')}"""
            
            keyboard = [
                [InlineKeyboardButton("📋 Обновить список", callback_data="admin_list_backups")],
                [InlineKeyboardButton("📊 К статистике", callback_data="admin_refresh_training_stats")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(cleanup_text, reply_markup=reply_markup)
        else:
            error_text = f"❌ Ошибка при очистке:\n\n{result.get('error', 'Неизвестная ошибка')}"
            await query.edit_message_text(error_text)
            
    except Exception as e:
        logger.error(f"Ошибка при очистке: {e}")
        await query.edit_message_text(f"❌ Ошибка при очистке:\n\n{str(e)}") 