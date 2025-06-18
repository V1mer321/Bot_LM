import logging
from datetime import datetime
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
        
        products_text = f"➕ <b>Новые товары для рассмотрения ({len(pending_products)}):</b>\n\n"
        
        for i, product in enumerate(pending_products[:5], 1):
            # Экранируем HTML символы
            product_name = str(product['product_name']).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            category = str(product.get('product_category', 'Не указана')).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            description = str(product.get('product_description', 'Не указано')).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            username = str(product.get('username', 'Аноним')).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            products_text += f"""<b>{i}. {product_name}</b>
📂 Категория: {category}
📋 Описание: {description}
👤 От пользователя: {username} (ID: {product['user_id']})
📅 Дата: {product['created_at']}
🔗 ID аннотации: #{product['id']}

"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Одобрить товары", callback_data="admin_approve_products")],
            [InlineKeyboardButton("❌ Отклонить товары", callback_data="admin_reject_products")],
            [InlineKeyboardButton("📋 Подробный просмотр", callback_data="admin_detailed_products")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(products_text, parse_mode='HTML', reply_markup=reply_markup)
        
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
    
    logger.info(f"🔑 Admin callback получен: {query.data} от {user_id}")
    
    if not is_admin(user_id):
        logger.warning(f"❌ Пользователь {user_id} не является админом")
        await query.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    logger.info(f"✅ Админ {user_id} подтвержден, обрабатываем {query.data}")
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
        
        elif query.data == "admin_detailed_products":
            await manage_new_products(query, context)
        
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
            
        elif query.data.startswith("fill_product_data_"):
            # Начинаем пошаговое заполнение данных товара
            annotation_id = int(query.data.replace("fill_product_data_", ""))
            await start_product_data_filling(query, context, annotation_id)
            
        elif query.data.startswith("reject_product_"):
            # Отклоняем товар
            annotation_id = int(query.data.replace("reject_product_", ""))
            await reject_single_product(query, context, annotation_id)
        
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
        
        products_text = f"➕ <b>Новые товары для рассмотрения ({len(pending_products)}):</b>\n\n"
        
        for i, product in enumerate(pending_products[:3], 1):
            # Экранируем HTML-символы в названии товара
            product_name = str(product['product_name']).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            username = str(product.get('username', 'Аноним')).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            category = str(product.get('product_category', 'Не указана')).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            products_text += f"""<b>{i}. {product_name}</b>
📂 Категория: {category}
👤 От: {username}
📅 {product['created_at']}

"""
        
        keyboard = []
        
        # Добавляем кнопки для каждого товара
        for product in pending_products[:3]:
            keyboard.append([
                InlineKeyboardButton(f"📝 Заполнить #{product['id']}", 
                                   callback_data=f"fill_product_data_{product['id']}"),
                InlineKeyboardButton(f"❌ Отклонить #{product['id']}", 
                                   callback_data=f"reject_product_{product['id']}")
            ])
        
        keyboard.extend([
            [InlineKeyboardButton("✅ Одобрить все готовые", callback_data="admin_approve_products")],
            [InlineKeyboardButton("🔄 Обновить список", callback_data="admin_manage_new_products")]
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(products_text, parse_mode='HTML', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка при управлении товарами: {e}")
        error_msg = f"❌ Ошибка при получении новых товаров:\n\n{str(e)}\n\n"
        error_msg += "🔍 Проверьте:\n"
        error_msg += "• Существует ли база данных\n"
        error_msg += "• Создана ли таблица new_product_annotations\n"
        error_msg += "• Добавлены ли товары для рассмотрения"
        await query.edit_message_text(error_msg)

async def approve_new_products(query, context):
    """Одобрение новых товаров с автоматическим добавлением в каталог"""
    try:
        training_service = get_training_service()
        pending_products = training_service.get_pending_new_products(limit=10)
        
        if not pending_products:
            await query.edit_message_text("✅ Нет товаров для одобрения")
            return
        
        # Показываем процесс обработки
        await query.edit_message_text(
            f"⏳ Обрабатываю {len(pending_products)} товаров...\n\n"
            "• Одобрение заявок\n"
            "• Добавление в каталог\n"
            "• Генерация векторов для поиска\n\n"
            "Пожалуйста, подождите..."
        )
        
        approved_count = 0
        catalog_added_count = 0
        
        for i, product in enumerate(pending_products, 1):
            # Обновляем прогресс
            await query.edit_message_text(
                f"⏳ Обрабатываю товар {i}/{len(pending_products)}: {product['product_name'][:30]}...\n\n"
                f"✅ Одобрено: {approved_count}\n"
                f"📦 Добавлено в каталог: {catalog_added_count}"
            )
            
            # Одобряем товар
            success = training_service.approve_new_product(
                annotation_id=product['id'],
                admin_id=query.from_user.id
            )
            
            if success:
                approved_count += 1
                
                # Добавляем в каталог с генерацией векторов
                catalog_success = await add_approved_product_to_catalog(product['id'])
                
                if catalog_success:
                    catalog_added_count += 1
                    logger.info(f"✅ Товар #{product['id']} добавлен в каталог: {product['product_name']}")
                else:
                    logger.error(f"❌ Не удалось добавить товар #{product['id']} в каталог")
        
        # Финальный результат
        result_text = f"""<b>✅ Обработка завершена!</b>

<b>📊 Статистика:</b>
• Товаров обработано: {len(pending_products)}
• Одобрено заявок: {approved_count}
• Добавлено в каталог: {catalog_added_count}

<b>📦 Обработанные товары:</b>
"""
        
        for i, product in enumerate(pending_products[:approved_count], 1):
            status = "📦✅" if i <= catalog_added_count else "⚠️📝"
            # Экранируем название товара
            product_name = str(product['product_name']).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            result_text += f"{status} {i}. {product_name}\n"
        
        admin_name = str(query.from_user.first_name).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        result_text += f"""

<b>👨‍💼 Администратор:</b> {admin_name}
<b>📅 Дата обработки:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}

🔍 Товары с векторами готовы для поиска!
⚠️ Товары без векторов требуют ручной проверки.
"""
        
        keyboard = [
            [InlineKeyboardButton("📊 Обновить статистику", callback_data="admin_refresh_training_stats")],
            [InlineKeyboardButton("➕ Новые товары", callback_data="admin_manage_new_products")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(result_text, parse_mode='HTML', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка при одобрении товаров: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при обработке товаров:\n\n{str(e)}\n\n"
            "🔄 Попробуйте повторить операцию позже."
        )

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

# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С ТОВАРАМИ ====================

async def save_extended_product_data(annotation_id: int, product_data: dict):
    """Сохранение расширенных данных товара"""
    try:
        import sqlite3
        import json
        
        db_path = 'data/search_stats.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Создаем таблицу для расширенных данных товаров, если её нет
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS extended_product_data (
                annotation_id INTEGER PRIMARY KEY,
                item_id TEXT,
                url TEXT,
                picture_url TEXT,
                additional_data TEXT,
                FOREIGN KEY (annotation_id) REFERENCES new_product_annotations (id)
            )
        ''')
        
        # Сохраняем данные
        additional_data = json.dumps({
            'created_via': 'admin_step_by_step_form',
            'version': '2.1.0'
        })
        
        cursor.execute('''
            INSERT OR REPLACE INTO extended_product_data 
            (annotation_id, item_id, url, picture_url, additional_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (annotation_id, product_data['item_id'], product_data['url'],
              product_data['picture_url'], additional_data))
        
        conn.commit()
        conn.close()
        
        logger.info(f"💾 Расширенные данные товара сохранены для заявки #{annotation_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении расширенных данных: {e}")

async def add_approved_product_to_catalog(annotation_id: int):
    """Добавление одобренного товара в основной каталог с генерацией векторов"""
    try:
        import sqlite3
        import json
        import requests
        from datetime import datetime
        import numpy as np
        
        # Получаем данные товара
        db_path = 'data/search_stats.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем основные данные
        cursor.execute('''
            SELECT npa.product_name, npa.product_description, npa.image_path,
                   epd.item_id, epd.url, epd.picture_url
            FROM new_product_annotations npa
            LEFT JOIN extended_product_data epd ON npa.id = epd.annotation_id
            WHERE npa.id = ? AND npa.admin_approved = 1
        ''', (annotation_id,))
        
        row = cursor.fetchone()
        if not row:
            logger.error(f"❌ Товар #{annotation_id} не найден или не одобрен")
            return False
            
        product_name, description, image_path, item_id, url, picture_url = row
        conn.close()
        
        # Генерируем векторы через CLIP
        from handlers.photo_handler import generate_product_vectors
        vectors = await generate_product_vectors(picture_url or image_path, product_name, description)
        if not vectors:
            logger.error(f"❌ Не удалось сгенерировать векторы для товара #{annotation_id}")
            return False
            
        # Добавляем в основную БД
        unified_db_path = 'data/unified_products.db'
        conn = sqlite3.connect(unified_db_path)
        cursor = conn.cursor()
        
        # Подготавливаем данные
        timestamp = datetime.now().isoformat()
        
        # Генерируем уникальный item_id для новых товаров если не указан
        if not item_id:
            import uuid
            item_id = f"USER_{annotation_id}_{uuid.uuid4().hex[:8]}"
        
        cursor.execute('''
            INSERT OR REPLACE INTO products 
            (item_id, url, picture, vector)
            VALUES (?, ?, ?, ?)
        ''', (item_id, url, picture_url, vectors))
        
        product_row_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        # Обновляем статус в аннотациях
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE new_product_annotations 
            SET added_to_catalog = 1 
            WHERE id = ?
        ''', (annotation_id,))
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Товар #{annotation_id} успешно добавлен в каталог с ID {product_row_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при добавлении товара в каталог: {e}")
        return False

# ==================== ПОШАГОВОЕ ЗАПОЛНЕНИЕ ДАННЫХ ТОВАРА ====================

async def handle_admin_product_step(update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str):
    """Пошаговая обработка заполнения данных товара админом"""
    try:
        product_data = context.user_data['admin_adding_product']
        current_step = product_data['step']
        annotation_id = product_data['annotation_id']
        
        if current_step == 'item_id':
            # Шаг 1: Получили ЛМ товара
            product_data['data']['item_id'] = user_input.strip()
            product_data['step'] = 'url'
            
            await update.message.reply_text(
                "✅ ЛМ товара сохранён!\n\n"
                "📝 *Шаг 2/5:* Введите ссылку на товар\n\n"
                "💡 Пример: `https://lmpro.ru/catalog/item/12345`\n\n"
                "✍️ Вставьте URL товара:",
                parse_mode='Markdown'
            )
            
        elif current_step == 'url':
            # Шаг 2: Получили URL
            product_data['data']['url'] = user_input.strip()
            product_data['step'] = 'picture_url'
            
            await update.message.reply_text(
                "✅ Ссылка на товар сохранена!\n\n"
                "📝 *Шаг 3/5:* Введите ссылку на фотографию\n\n"
                "💡 Пример: `https://lmpro.ru/images/product/abc123.jpg`\n\n"
                "✍️ Вставьте URL фотографии:",
                parse_mode='Markdown'
            )
            
        elif current_step == 'picture_url':
            # Шаг 3: Получили ссылку на фото
            product_data['data']['picture_url'] = user_input.strip()
            product_data['step'] = 'name'
            
            await update.message.reply_text(
                "✅ Ссылка на фотографию сохранена!\n\n"
                "📝 *Шаг 4/5:* Введите название товара\n\n"
                "💡 Пример: `Дрель ударная Makita HP2050H 720Вт`\n\n"
                "✍️ Напишите полное название:",
                parse_mode='Markdown'
            )
            
        elif current_step == 'name':
            # Шаг 4: Получили название
            product_data['data']['name'] = user_input.strip()
            product_data['step'] = 'description'
            
            await update.message.reply_text(
                "✅ Название товара сохранено!\n\n"
                "📝 *Шаг 5/5:* Введите описание товара\n\n"
                "💡 Пример: `Электроинструмент для сверления отверстий в различных материалах. Мощность 720 Вт, функция удара, максимальный диаметр сверления 20мм.`\n\n"
                "✍️ Напишите подробное описание:",
                parse_mode='Markdown'
            )
            
        elif current_step == 'description':
            # Шаг 5: Финальный шаг - получили описание
            product_data['data']['description'] = user_input.strip()
            
            # Собираем все данные и создаем товар
            await finalize_admin_product(update, context, annotation_id, product_data['data'])
            
        else:
            await update.message.reply_text(
                "❌ Неизвестный шаг. Начните процесс заново."
            )
            del context.user_data['admin_adding_product']
            
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке шага добавления товара: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка. Попробуйте начать заново."
        )
        if 'admin_adding_product' in context.user_data:
            del context.user_data['admin_adding_product']

async def finalize_admin_product(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               annotation_id: int, product_data: dict):
    """Финализация добавления товара админом"""
    try:
        from services.training_data_service import get_training_service
        training_service = get_training_service()
        
        # Обновляем название и описание в аннотации
        training_service.update_product_annotation(
            annotation_id=annotation_id,
            product_name=product_data['name'],
            product_description=product_data['description']
        )
        
        # Сохраняем расширенные данные
        await save_extended_product_data(annotation_id, product_data)
        
        # Автоматически одобряем и добавляем в каталог
        training_service.approve_new_product(
            annotation_id=annotation_id,
            admin_id=update.effective_user.id
        )
        
        # Добавляем в основной каталог
        success = await add_approved_product_to_catalog(annotation_id)
        
        if success:
            # Экранируем данные для безопасного отображения
            safe_item_id = str(product_data.get('item_id', 'Не указано')).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
            safe_url = str(product_data.get('url', 'Не указано')).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
            safe_picture_url = str(product_data.get('picture_url', 'Не указано')).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
            safe_name = str(product_data.get('name', 'Не указано')).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
            safe_description = str(product_data.get('description', 'Не указано')).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
            
            # Показываем резюме
            summary = (
                "✅ *Товар успешно добавлен в каталог!*\n\n"
                f"📝 *ID заявки:* #{annotation_id}\n"
                f"🏷️ *ЛМ товара:* `{safe_item_id}`\n"
                f"🔗 *URL товара:* {safe_url}\n"
                f"🖼️ *URL фото:* {safe_picture_url}\n"
                f"📦 *Название:* {safe_name}\n"
                f"📄 *Описание:* {safe_description}\n\n"
                "🎯 *Товар сразу доступен для поиска!*\n"
                "✅ Векторы сгенерированы\n"
                "✅ Добавлен в основной каталог\n\n"
                "🙏 Спасибо за пополнение каталога!"
            )
            
            await update.message.reply_text(summary, parse_mode='Markdown')
            logger.info(f"✅ Админ добавил товар #{annotation_id}: {product_data['name']}")
        else:
            await update.message.reply_text(
                f"⚠️ Данные товара #{annotation_id} сохранены, но не удалось добавить в каталог.\n\n"
                "🔄 Попробуйте использовать команду одобрения товаров."
            )
        
        # Очищаем состояние
        del context.user_data['admin_adding_product']
        
    except Exception as e:
        logger.error(f"❌ Ошибка при финализации товара админом: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при сохранении товара.\n\n"
            "🔄 Попробуйте еще раз."
        )
        if 'admin_adding_product' in context.user_data:
            del context.user_data['admin_adding_product'] 

async def start_product_data_filling(query, context, annotation_id: int):
    """Начало пошагового заполнения данных товара"""
    try:
        from services.training_data_service import get_training_service
        training_service = get_training_service()
        
        # Получаем информацию о товаре
        product_info = training_service.get_product_annotation(annotation_id)
        if not product_info or product_info['admin_approved'] != 0:
            await query.edit_message_text(
                f"❌ Товар #{annotation_id} не найден или уже обработан"
            )
            return
        
        ann_id = product_info['id']
        user_id = product_info['user_id'] 
        username = product_info['username']
        product_name = product_info['product_name']
        product_description = product_info['product_description']
        image_path = product_info['image_path']
        created_at = product_info['created_at']
        
        # Экранируем данные для безопасного отображения
        safe_username = str(username or user_id).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
        safe_description = str(product_description or 'Не указано').replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
        safe_image_path = str(image_path or 'Не указано').replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
        
        # Показываем информацию от пользователя и начинаем заполнение
        user_info = (
            f"📝 *Заполнение данных товара #{ann_id}*\n\n"
            f"👤 *От пользователя:* {safe_username}\n"
            f"📦 *Описание пользователя:* {safe_description}\n"
            f"📅 *Дата:* {created_at}\n\n"
            f"🖼️ *Фото пользователя сохранено:* {safe_image_path}\n\n"
            f"📝 *Шаг 1/5:* Введите ЛМ товара \\(артикул\\)\n\n"
            f"💡 Пример: `ЛМ-12345` или `ABC-789`\n\n"
            f"✍️ Напишите артикул товара:"
        )
        
        # Сохраняем состояние для админа
        context.user_data['admin_adding_product'] = {
            'annotation_id': annotation_id,
            'step': 'item_id',
            'data': {}
        }
        
        await query.edit_message_text(user_info, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Ошибка при начале заполнения товара: {e}")
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")

async def reject_single_product(query, context, annotation_id: int):
    """Отклонение одного товара"""
    try:
        from services.training_data_service import get_training_service
        training_service = get_training_service()
        
        # Помечаем как отклоненный
        training_service.reject_product_annotation(
            annotation_id=annotation_id,
            admin_id=query.from_user.id
        )
        
        await query.edit_message_text(
            f"❌ Товар #{annotation_id} отклонен\n\n"
            f"📝 Заявка помечена как отклоненная и не будет добавлена в каталог.\n\n"
            f"👨‍💼 Администратор: {query.from_user.first_name}\n"
            f"📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        logger.info(f"❌ Админ {query.from_user.id} отклонил товар #{annotation_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при отклонении товара: {e}")
        await query.edit_message_text(f"❌ Ошибка: {str(e)}") 