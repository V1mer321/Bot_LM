import os
import logging
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Ленивая инициализация сервиса поиска (инициализируется только при первом использовании)
_unified_db_service = None

def get_unified_db_service():
    """Получение экземпляра сервиса с ленивой инициализацией"""
    global _unified_db_service
    if _unified_db_service is None:
        try:
            logger.info("Ленивая инициализация UnifiedDatabaseService...")
            from services.unified_database_search import UnifiedDatabaseService
            _unified_db_service = UnifiedDatabaseService()
            logger.info("✓ UnifiedDatabaseService успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка при инициализации UnifiedDatabaseService: {e}")
            raise
    return _unified_db_service

def get_stats_service():
    """Получение экземпляра сервиса статистики"""
    try:
        from services.search_statistics import get_stats_service
        return get_stats_service()
    except Exception as e:
        logger.error(f"Ошибка при инициализации сервиса статистики: {e}")
        return None

def get_short_id(photo_file_id):
    """Создает короткий хеш из photo_file_id для использования в callback_data"""
    return hashlib.md5(photo_file_id.encode()).hexdigest()[:8]

def safe_callback_data(data):
    """Создает безопасный callback_data с проверкой длины"""
    if len(data.encode('utf-8')) > 64:
        logger.warning(f"Callback data слишком длинный: {len(data)} символов, обрезаем")
        return data[:60] + "..."
    return data

# Определение отделов
DEPARTMENTS = [
    "🧱 Строительные материалы",
    "🪑 Столярные изделия", 
    "⚡ Электрика",
    "🔧 Сантехника",
    "🎨 Краски и лаки",
    "🔩 Крепёж и метизы",
    "🚪 Двери, окна",
    "🏠 Кровля",
    "🛠️ Инструмент",
    "🧽 Хозтовары"
]

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фотографий от пользователей"""
    import time
    start_time = time.time()
    
    try:
        # Логируем активность пользователя в мониторинге
        try:
            from toolbot.services.monitoring import monitoring
            user_id = update.effective_user.id
            monitoring.log_user_activity(user_id, 'photo_search', {
                'file_id': update.message.photo[-1].file_id[:20] + '...'  # Короткий ID для логов
            })
        except Exception as e:
            logger.warning(f"Ошибка логирования активности: {e}")
        
        photo = update.message.photo[-1]  # Берем фото наибольшего размера
        file = await context.bot.get_file(photo.file_id)
        
        # Создаем директорию для временных файлов
        os.makedirs('temp', exist_ok=True)
        
        # Скачиваем фото
        photo_path = f'temp/{photo.file_id}.jpg'
        await file.download_to_drive(photo_path)
        
        # Отправляем сообщение о начале поиска
        loading_message = await update.message.reply_text("🔍 Анализирую изображение и ищу похожие товары...")
        
        # Ищем похожие товары с проверкой стабильности результатов
        unified_db_service = get_unified_db_service()
        search_method = "stable"
        similar_products = unified_db_service.search_with_stability_check(photo_path, top_k=5)
        
        # Если стабильный поиск не дал результатов, пробуем обычный поиск с пониженными порогами
        if not similar_products:
            logger.info("Стабильный поиск не дал результатов, пробуем обычный поиск...")
            search_method = "threshold"
            similar_products = unified_db_service.search_with_multiple_thresholds(photo_path, top_k=5)
        
        # Если и обычный поиск не дал результатов, пробуем агрессивный поиск
        if not similar_products:
            logger.info("Обычный поиск не дал результатов, пробуем агрессивный поиск...")
            search_method = "aggressive"
            similar_products = unified_db_service.aggressive_search(photo_path, top_k=5)
            
            # Если агрессивный поиск дал результаты, добавляем предупреждение о низкой точности
            if similar_products:
                await update.message.reply_text(
                    "⚠️ *Внимание:* найдены результаты с низкой схожестью.\n"
                    "Возможно, эти товары не совсем соответствуют вашему запросу."
                )
        
        # Логируем сессию поиска
        stats_service = get_stats_service()
        if stats_service:
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name
            session_id = stats_service.log_search_session(
                user_id=user_id,
                username=username,
                photo_file_id=photo.file_id,
                results=similar_products or [],
                search_method=search_method
            )
            
            # Сохраняем контекст поиска для кнопки "Это не мой товар"
            # Используем короткий ID для callback_data, но сохраняем полный контекст
            short_id = get_short_id(photo.file_id)
            context.user_data[f'search_session_{short_id}'] = {
                'session_id': session_id,
                'user_id': user_id,
                'username': username,
                'photo_file_id': photo.file_id,  # Полный file_id для логирования
                'results': similar_products or [],
                'search_method': search_method
            }
        
        # Выводим диагностику в логи
        if similar_products:
            similarities = [p['similarity'] for p in similar_products]
            logger.info(f"Найдено {len(similar_products)} товаров, схожести: {similarities}")
        else:
            logger.warning("Ни один метод поиска не дал результатов!")
            
            # Проверяем статистику БД для диагностики
            stats = unified_db_service.get_database_stats()
            logger.info(f"Статистика БД: {stats}")
        
        # Удаляем временный файл
        if os.path.exists(photo_path):
            os.remove(photo_path)
        
        # Удаляем сообщение о загрузке
        await loading_message.delete()
        
        if not similar_products:
            await update.message.reply_text(
                "😔 К сожалению, не удалось найти достаточно похожие товары.\n\n"
                "🎯 Для лучших результатов:\n"
                "• Убедитесь, что фото содержит строительный товар\n"
                "• Сделайте фото более чётким и крупным\n"
                "• Уберите лишние объекты из кадра\n"
                "• Улучшите освещение\n"
                "• Сфотографируйте товар с разных ракурсов\n\n"
                "💡 Бот ищет только среди строительных материалов, инструментов и товаров для дома.\n\n"
                "🐛 Если проблема повторяется, воспользуйтесь функцией 'Сообщить о баге' в результатах поиска"
            )
            return
        
        # Проверяем качество результатов (пороги понижены для лучшего поиска)
        best_similarity = similar_products[0]['similarity']
        if best_similarity < 0.3:  # Понижен с 0.5 до 0.3
            quality_warning = "\n⚠️ Результаты с низкой схожестью - возможно, товар не из нашего каталога"
        elif best_similarity < 0.5:  # Понижен с 0.7 до 0.5
            quality_warning = "\n📝 Результаты с умеренной схожестью"
        else:
            quality_warning = "\n✅ Найдены очень похожие товары!"
        
        await update.message.reply_text(
            f"🎯 Найдено {len(similar_products)} стабильных результатов{quality_warning}"
        )
        
        # Отправляем результаты
        await send_search_results(update, context, similar_products, get_short_id(photo.file_id))
        
        # Логируем производительность
        try:
            from toolbot.services.monitoring import monitoring
            response_time = (time.time() - start_time) * 1000  # В миллисекундах
            monitoring.log_response_time('photo_search', response_time, success=True)
            monitoring.log_model_performance('image_search', response_time, accuracy=best_similarity if similar_products else 0)
        except Exception as e:
            logger.warning(f"Ошибка логирования производительности: {e}")
        
    except Exception as e:
        # Логируем ошибку в мониторинге
        try:
            from toolbot.services.monitoring import monitoring
            response_time = (time.time() - start_time) * 1000
            monitoring.log_response_time('photo_search', response_time, success=False)
        except:
            pass
            
        logger.error(f"Ошибка при обработке фото: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке изображения.")

async def send_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE, products, short_id):
    """Отправка результатов поиска с улучшенной информацией"""
    try:
        for i, product in enumerate(products, 1):
            # Конвертируем similarity в проценты
            similarity_percent = int(product['similarity'] * 100)
            
            # Получаем стабильность если есть
            stability = product.get('stability', 1.0)
            stability_percent = int(stability * 100)
            
            # Определяем качество совпадения (понижены пороги)
            if similarity_percent >= 70:  # Понижен с 80
                quality_emoji = "🎯"
                quality_text = "Превосходное совпадение"
            elif similarity_percent >= 50:  # Понижен с 65
                quality_emoji = "✅"
                quality_text = "Отличное совпадение"
            elif similarity_percent >= 35:  # Понижен с 50
                quality_emoji = "📝"
                quality_text = "Хорошее совпадение"
            elif similarity_percent >= 20:  # Понижен с 35
                quality_emoji = "🔍"
                quality_text = "Умеренное совпадение"
            else:
                quality_emoji = "❓"
                quality_text = "Возможное совпадение"
            
            caption = (
                f"{quality_emoji} Результат {i} - {quality_text}\n"
                f"📊 Схожесть: {similarity_percent}% (стабильность: {stability_percent}%)\n"
                f"🏷️ Артикул: {product['item_id']}\n"
                f"🌐 Ссылка: {product['url']}"
            )
            
            # Кнопки для взаимодействия
            keyboard = [
                [InlineKeyboardButton("🔗 Открыть товар", url=product['url'])],
                [InlineKeyboardButton("📋 Выбрать отдел", callback_data=safe_callback_data(f"select_dept_{product['item_id']}"))],
                [
                    InlineKeyboardButton("✅ Правильно", callback_data=safe_callback_data(f"correct_{short_id}_{i}_{product['item_id']}")),
                    InlineKeyboardButton("❌ Неправильно", callback_data=safe_callback_data(f"incorrect_{short_id}_{i}_{product['item_id']}"))
                ],
                [InlineKeyboardButton("➕ Добавить новый товар", callback_data=safe_callback_data(f"new_item_{short_id}"))]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем изображение товара
            try:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=product['picture'],
                    caption=caption,
                    reply_markup=reply_markup
                )
            except Exception as e:
                # Если не удается отправить изображение, отправляем текст
                logger.warning(f"Не удалось отправить изображение: {e}")
                await update.message.reply_text(
                    text=caption,
                    reply_markup=reply_markup
                )
                
    except Exception as e:
        logger.error(f"Ошибка при отправке результатов: {e}")
        await update.message.reply_text("❌ Ошибка при отправке результатов поиска.")

async def handle_department_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора отдела"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("select_dept_"):
        item_id = query.data.replace("select_dept_", "")
        
        # Создаем клавиатуру с отделами
        keyboard = []
        for dept in DEPARTMENTS:
            keyboard.append([InlineKeyboardButton(dept, callback_data=f"dept_{dept}_{item_id}")])
        
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_caption(
            caption=f"Выберите отдел для товара {item_id}:",
            reply_markup=reply_markup
        )
    
    elif query.data.startswith("dept_"):
        # Извлекаем данные
        parts = query.data.split("_", 2)
        if len(parts) >= 3:
            dept_name = parts[1]
            item_id = parts[2]
            
            await query.edit_message_caption(
                caption=f"✅ Товар {item_id} добавлен в отдел '{dept_name}'"
            )
    
    elif query.data == "cancel":
        await query.edit_message_caption(
            caption="❌ Выбор отдела отменен"
        )

# Функция для получения статистики БД
async def get_database_stats():
    """Получение статистики базы данных"""
    unified_db_service = get_unified_db_service()
    return unified_db_service.get_database_stats()

async def handle_not_my_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопки 'Это не мой товар'"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Парсим callback_data: not_my_item_{short_id}_{result_index}
        data_parts = query.data.split('_')
        if len(data_parts) >= 4:
            short_id = data_parts[3]  # Короткий ID
            result_index = int(data_parts[4])
            
            # Получаем контекст поиска по короткому ID
            search_key = f'search_session_{short_id}'
            search_context = context.user_data.get(search_key)
            
            if search_context:
                stats_service = get_stats_service()
                if stats_service:
                    # Логируем неудачный поиск
                    stats_service.log_failed_search(
                        user_id=search_context['user_id'],
                        username=search_context['username'],
                        photo_file_id=search_context['photo_file_id'],
                        search_results=search_context['results'],
                        feedback_type='not_my_product'
                    )
                    
                    logger.info(f"Пользователь {search_context['user_id']} отметил результат {result_index} как неподходящий")
                
                # Предлагаем дополнительные действия
                keyboard = [
                    [InlineKeyboardButton("💬 Оставить комментарий", callback_data=f"add_comment_{short_id}")],
                    [InlineKeyboardButton("🔄 Попробовать другое фото", callback_data="try_another_photo")],
                    [InlineKeyboardButton("📞 Связаться с поддержкой", callback_data="contact_support")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_caption(
                    caption="❌ Спасибо за обратную связь!\n\n"
                           "📊 Ваш отзыв поможет нам улучшить качество поиска.\n\n"
                           "Что бы вы хотели сделать дальше?",
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_caption(
                    caption="❌ Спасибо за обратную связь!\n\n"
                           "К сожалению, не удалось найти контекст поиска."
                )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке 'не мой товар': {e}")
        await query.edit_message_caption(
            caption="❌ Спасибо за обратную связь!\n\n"
                   "Произошла ошибка при обработке, но ваш отзыв учтен."
        )

async def handle_add_comment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка добавления комментария"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Парсим callback_data: add_comment_{short_id}
        short_id = query.data.replace('add_comment_', '')
        
        # Сохраняем состояние ожидания комментария
        context.user_data['awaiting_comment_for'] = short_id
        
        await query.edit_message_caption(
            caption="💬 Пожалуйста, напишите комментарий о том, какой товар вы искали.\n\n"
                   "Это поможет нам улучшить качество поиска!"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при запросе комментария: {e}")
        await query.answer("❌ Ошибка при обработке запроса", show_alert=True)

async def handle_try_another_photo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка 'попробовать другое фото'"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_caption(
        caption="📸 Попробуйте сделать новое фото:\n\n"
               "🎯 Советы для лучшего результата:\n"
               "• Хорошее освещение\n"
               "• Четкий фокус на товаре\n"
               "• Убрать лишние объекты из кадра\n"
               "• Сфотографировать с разных ракурсов\n"
               "• Показать этикетку или упаковку\n\n"
               "📤 Просто отправьте новое фото в чат!"
    )

async def handle_contact_support_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка 'связаться с поддержкой'"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_caption(
        caption="📞 Связь с поддержкой:\n\n"
               "🤖 Используйте команду /admin для связи с администратором\n"
               "📝 Или напишите в разделе 'Предложения' через админ-панель\n\n"
               "💡 Опишите, какой именно товар вы искали - это поможет нам улучшить поиск!"
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений (включая комментарии к поиску и описания товаров)"""
    user_text = update.message.text
    
    # Проверяем различные типы ожидаемого ввода
    awaiting_comment_for = context.user_data.get('awaiting_comment_for')
    awaiting_new_product_for = context.user_data.get('awaiting_new_product_for')
    awaiting_correct_item_for = context.user_data.get('awaiting_correct_item_for')
    
    # Обработка комментария к поиску
    if awaiting_comment_for:
        search_key = f'search_session_{awaiting_comment_for}'
        search_context = context.user_data.get(search_key)
        
        if search_context:
            stats_service = get_stats_service()
            if stats_service:
                stats_service.log_failed_search(
                    user_id=search_context['user_id'],
                    username=search_context['username'],
                    photo_file_id=search_context['photo_file_id'],
                    search_results=search_context['results'],
                    feedback_type='not_my_product_with_comment',
                    user_comment=user_text
                )
        
        del context.user_data['awaiting_comment_for']
        
        await update.message.reply_text(
            "✅ Спасибо за подробный комментарий!\n\n"
            "📊 Ваша обратная связь поможет нам улучшить качество поиска.\n"
            "🎯 Попробуйте отправить другое фото для поиска."
        )
        return
    
    # Обработка описания нового товара
    elif awaiting_new_product_for:
        await handle_new_product_description(update, context, awaiting_new_product_for, user_text)
        return
    
    # Обработка указания правильного товара
    elif awaiting_correct_item_for:
        await handle_correct_item_specification(update, context, awaiting_correct_item_for, user_text)
        return
    
    # Если не ожидается комментарий, передаем управление обычному обработчику текста
    try:
        from toolbot.handlers.text_handler import text_handler
        await text_handler(update, context)
    except Exception as e:
        logger.error(f"Ошибка в обработчике текста: {e}")
        await update.message.reply_text(
            "📸 Отправьте фото товара для поиска или используйте /help для получения справки."
        )

# ==================== НОВЫЕ ОБРАБОТЧИКИ ДЛЯ ДООБУЧЕНИЯ ====================

async def handle_correct_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка правильного результата поиска"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Парсим callback_data: correct_{short_id}_{result_index}_{item_id}
        data_parts = query.data.split('_')
        if len(data_parts) >= 4:
            short_id = data_parts[1]
            result_index = int(data_parts[2])
            item_id = data_parts[3]
            
            # Получаем контекст поиска
            search_key = f'search_session_{short_id}'
            search_context = context.user_data.get(search_key)
            
            if search_context:
                # Получаем оригинальное изображение
                photo_file_id = search_context['photo_file_id']
                
                # Сохраняем изображение для обучения
                photo_path = await save_training_image(context, photo_file_id, short_id)
                
                # Получаем similarity_score для данного результата
                results = search_context.get('results', [])
                similarity_score = 0.5
                if result_index-1 < len(results):
                    similarity_score = results[result_index-1].get('similarity', 0.5)
                
                # Добавляем обучающий пример
                from services.training_data_service import get_training_service
                training_service = get_training_service()
                
                example_id = training_service.add_training_example(
                    photo_file_id=photo_file_id,
                    user_id=search_context['user_id'],
                    username=search_context['username'],
                    feedback_type='correct',
                    target_item_id=item_id,
                    similarity_score=similarity_score,
                    image_path=photo_path,
                    quality_rating=5  # Правильный результат = высокое качество
                )
                
                if example_id:
                    logger.info(f"✅ Добавлен положительный пример обучения #{example_id}")
                    
                    await query.edit_message_caption(
                        caption="✅ Спасибо! Ваша оценка поможет улучшить точность поиска.\n\n"
                               "🎯 Этот пример будет использован для дообучения модели.\n"
                               f"📝 ID обучающего примера: #{example_id}",
                        reply_markup=None
                    )
                else:
                    await query.edit_message_caption(
                        caption="✅ Спасибо за обратную связь!\n\n"
                               "❌ Не удалось сохранить пример для обучения.",
                        reply_markup=None
                    )
            else:
                await query.edit_message_caption(
                    caption="✅ Спасибо за обратную связь!",
                    reply_markup=None
                )
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке правильного результата: {e}")
        await query.edit_message_caption(
            caption="✅ Спасибо за обратную связь!",
            reply_markup=None
        )

async def handle_incorrect_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка неправильного результата поиска"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Парсим callback_data: incorrect_{short_id}_{result_index}_{item_id}
        data_parts = query.data.split('_')
        if len(data_parts) >= 4:
            short_id = data_parts[1]
            result_index = int(data_parts[2])
            item_id = data_parts[3]
            
            # Получаем контекст поиска
            search_key = f'search_session_{short_id}'
            search_context = context.user_data.get(search_key)
            
            if search_context:
                # Получаем оригинальное изображение
                photo_file_id = search_context['photo_file_id']
                
                # Сохраняем изображение для обучения
                photo_path = await save_training_image(context, photo_file_id, short_id)
                
                # Получаем similarity_score для данного результата
                results = search_context.get('results', [])
                similarity_score = 0.5
                if result_index-1 < len(results):
                    similarity_score = results[result_index-1].get('similarity', 0.5)
                
                # Добавляем отрицательный обучающий пример
                from services.training_data_service import get_training_service
                training_service = get_training_service()
                
                example_id = training_service.add_training_example(
                    photo_file_id=photo_file_id,
                    user_id=search_context['user_id'],
                    username=search_context['username'],
                    feedback_type='incorrect',
                    target_item_id=item_id,
                    similarity_score=similarity_score,
                    image_path=photo_path,
                    quality_rating=2  # Неправильный результат = низкое качество
                )
                
                if example_id:
                    logger.info(f"❌ Добавлен отрицательный пример обучения #{example_id}")
                    
                    # Предлагаем указать правильный товар
                    keyboard = [
                        [InlineKeyboardButton("➕ Указать правильный товар", callback_data=f"specify_correct_{short_id}")],
                        [InlineKeyboardButton("🔄 Попробовать другое фото", callback_data="try_another_photo")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_caption(
                        caption="❌ Понятно, этот результат не подходит.\n\n"
                               "🎯 Ваш отзыв поможет улучшить точность поиска.\n"
                               f"📝 ID обучающего примера: #{example_id}\n\n"
                               "💡 Хотите указать правильный товар?",
                        reply_markup=reply_markup
                    )
                else:
                    await query.edit_message_caption(
                        caption="❌ Спасибо за обратную связь!\n\n"
                               "❌ Не удалось сохранить пример для обучения.",
                        reply_markup=None
                    )
            else:
                await query.edit_message_caption(
                    caption="❌ Спасибо за обратную связь!",
                    reply_markup=None
                )
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке неправильного результата: {e}")
        await query.edit_message_caption(
            caption="❌ Спасибо за обратную связь!",
            reply_markup=None
        )

async def handle_new_item_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка запроса на добавление нового товара"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Парсим callback_data: new_item_{short_id}
        short_id = query.data.replace('new_item_', '')
        
        # Сохраняем состояние ожидания описания нового товара
        context.user_data['awaiting_new_product_for'] = short_id
        
        await query.edit_message_caption(
            caption="➕ Добавление нового товара в каталог\n\n"
                   "📝 Пожалуйста, опишите товар:\n"
                   "• Название\n"
                   "• Категория (если знаете)\n"
                   "• Краткое описание\n\n"
                   "💡 Пример: 'Дрель ударная, электроинструмент, 850W'\n\n"
                   "✍️ Напишите описание одним сообщением:",
            reply_markup=None
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запросе нового товара: {e}")
        await query.answer("❌ Ошибка при обработке запроса", show_alert=True)

async def handle_specify_correct_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка указания правильного товара"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Парсим callback_data: specify_correct_{short_id}
        short_id = query.data.replace('specify_correct_', '')
        
        # Сохраняем состояние ожидания указания правильного товара
        context.user_data['awaiting_correct_item_for'] = short_id
        
        await query.edit_message_caption(
            caption="🎯 Укажите правильный товар\n\n"
                   "📝 Напишите:\n"
                   "• Артикул товара (если знаете)\n"
                   "• Или название и описание\n\n"
                   "💡 Пример: 'Артикул: ABC123' или 'Саморезы 4x50 оцинкованные'\n\n"
                   "✍️ Напишите информацию о товаре:",
            reply_markup=None
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запросе правильного товара: {e}")
        await query.answer("❌ Ошибка при обработке запроса", show_alert=True)

async def save_training_image(context, photo_file_id: str, short_id: str) -> str:
    """Сохранение изображения для обучения"""
    try:
        import os
        from datetime import datetime
        
        # Создаем директорию для обучающих изображений
        training_dir = 'temp/training_images'
        os.makedirs(training_dir, exist_ok=True)
        
        # Генерируем уникальное имя файла
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'training_{short_id}_{timestamp}.jpg'
        file_path = os.path.join(training_dir, filename)
        
        # Скачиваем изображение
        file = await context.bot.get_file(photo_file_id)
        await file.download_to_drive(file_path)
        
        logger.info(f"💾 Изображение сохранено для обучения: {file_path}")
        return file_path
        
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении изображения для обучения: {e}")
        return ""

async def handle_new_product_description(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                       short_id: str, description: str):
    """Обработка описания нового товара"""
    try:
        # Получаем контекст поиска
        search_key = f'search_session_{short_id}'
        search_context = context.user_data.get(search_key)
        
        if search_context:
            photo_file_id = search_context['photo_file_id']
            
            # Сохраняем изображение для аннотации
            photo_path = await save_training_image(context, photo_file_id, short_id)
            
            # Парсим описание товара
            parts = description.split(',')
            product_name = parts[0].strip() if parts else description
            product_category = parts[1].strip() if len(parts) > 1 else ""
            product_description = parts[2].strip() if len(parts) > 2 else description
            
            # Добавляем аннотацию нового товара
            from services.training_data_service import get_training_service
            training_service = get_training_service()
            
            annotation_id = training_service.add_new_product_annotation(
                photo_file_id=photo_file_id,
                user_id=search_context['user_id'],
                username=search_context['username'],
                product_name=product_name,
                product_category=product_category,
                product_description=product_description,
                image_path=photo_path
            )
            
            if annotation_id:
                logger.info(f"➕ Добавлена аннотация нового товара #{annotation_id}")
                
                await update.message.reply_text(
                    f"✅ Спасибо! Ваш новый товар добавлен на рассмотрение.\n\n"
                    f"📝 ID аннотации: #{annotation_id}\n"
                    f"🏷️ Название: {product_name}\n"
                    f"📂 Категория: {product_category or 'Не указана'}\n"
                    f"📋 Описание: {product_description}\n\n"
                    f"👨‍💼 Администратор рассмотрит заявку и добавит товар в каталог.\n"
                    f"📧 Вы получите уведомление о результате."
                )
            else:
                await update.message.reply_text(
                    "❌ Не удалось сохранить аннотацию товара.\n\n"
                    "🔄 Попробуйте еще раз или обратитесь к администратору."
                )
        else:
            await update.message.reply_text(
                "❌ Не удалось найти контекст поиска.\n\n"
                "🔄 Попробуйте сделать новый поиск."
            )
        
        # Очищаем состояние
        del context.user_data['awaiting_new_product_for']
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке описания нового товара: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке описания товара.\n\n"
            "🔄 Попробуйте еще раз."
        )
        if 'awaiting_new_product_for' in context.user_data:
            del context.user_data['awaiting_new_product_for']

async def handle_correct_item_specification(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                          short_id: str, specification: str):
    """Обработка указания правильного товара"""
    try:
        # Получаем контекст поиска
        search_key = f'search_session_{short_id}'
        search_context = context.user_data.get(search_key)
        
        if search_context:
            photo_file_id = search_context['photo_file_id']
            
            # Сохраняем изображение для обучения
            photo_path = await save_training_image(context, photo_file_id, short_id)
            
            # Добавляем правильный обучающий пример
            from services.training_data_service import get_training_service
            training_service = get_training_service()
            
            # Пытаемся извлечь артикул из описания
            target_item_id = None
            if specification.lower().startswith('артикул'):
                parts = specification.split(':', 1)
                if len(parts) > 1:
                    target_item_id = parts[1].strip()
            
            example_id = training_service.add_training_example(
                photo_file_id=photo_file_id,
                user_id=search_context['user_id'],
                username=search_context['username'],
                feedback_type='correct',
                target_item_id=target_item_id,
                similarity_score=1.0,  # Максимальная схожесть для правильного указания
                user_comment=specification,
                image_path=photo_path,
                quality_rating=5
            )
            
            if example_id:
                logger.info(f"🎯 Добавлен правильный пример обучения #{example_id}")
                
                await update.message.reply_text(
                    f"✅ Отлично! Правильный товар добавлен в обучающие данные.\n\n"
                    f"📝 ID примера: #{example_id}\n"
                    f"🎯 Указание: {specification}\n"
                    f"🏷️ Артикул: {target_item_id or 'Не указан'}\n\n"
                    f"🧠 Эта информация поможет улучшить точность поиска.\n"
                    f"🙏 Спасибо за помощь в обучении системы!"
                )
            else:
                await update.message.reply_text(
                    "❌ Не удалось сохранить обучающий пример.\n\n"
                    "🔄 Попробуйте еще раз или обратитесь к администратору."
                )
        else:
            await update.message.reply_text(
                "❌ Не удалось найти контекст поиска.\n\n"
                "🔄 Попробуйте сделать новый поиск."
            )
        
        # Очищаем состояние
        del context.user_data['awaiting_correct_item_for']
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке указания правильного товара: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке указания товара.\n\n"
            "🔄 Попробуйте еще раз."
        )
        if 'awaiting_correct_item_for' in context.user_data:
            del context.user_data['awaiting_correct_item_for']