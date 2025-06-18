import os
import logging
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Ленивая инициализация сервиса поиска (инициализируется только при первом использовании)
_unified_db_service = None
_department_search_service = None

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

def get_department_search_service():
    """Получение экземпляра сервиса поиска по отделам"""
    global _department_search_service
    if _department_search_service is None:
        try:
            logger.info("Ленивая инициализация DepartmentSearchService...")
            from services.department_search_service import DepartmentSearchService
            _department_search_service = DepartmentSearchService()
            logger.info("✓ DepartmentSearchService успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка при инициализации DepartmentSearchService: {e}")
            raise
    return _department_search_service

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

# Определение отделов - сопоставляем с реальными отделами из БД
DEPARTMENTS = {
    "🛠️ ИНСТРУМЕНТЫ": "ИНСТРУМЕНТЫ",
    "🎨 КРАСКИ": "КРАСКИ", 
    "🚰 САНТЕХНИКА": "САНТЕХНИКА",
    "🧱 СТРОЙМАТЕРИАЛЫ": "СТРОЙМАТЕРИАЛЫ",
    "🏠 НАПОЛЬНЫЕ ПОКРЫТИЯ": "НАПОЛЬНЫЕ ПОКРЫТИЯ",
    "🌿 САД": "САД",
    "💡 СВЕТ": "СВЕТ",
    "⚡ ЭЛЕКТРОТОВАРЫ": "ЭЛЕКТРОТОВАРЫ",
    "🏠 ОТДЕЛОЧНЫЕ МАТЕРИАЛЫ": "ОТДЕЛОЧНЫЕ МАТЕРИАЛЫ",
    "🚿 ВОДОСНАБЖЕНИЕ": "ВОДОСНАБЖЕНИЕ",
    "🔩 СКОБЯНЫЕ ИЗДЕЛИЯ": "СКОБЯНЫЕ ИЗДЕЛИЯ",
    "🗄️ ХРАНЕНИЕ": "ХРАНЕНИЕ",
    "🏠 СТОЛЯРНЫЕ ИЗДЕЛИЯ": "СТОЛЯРНЫЕ ИЗДЕЛИЯ",
    "🍽️ КУХНИ": "КУХНИ",
    "🏢 ПЛИТКА": "ПЛИТКА"
}

# Обработчики для системы выбора отделов
async def photo_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Поиск по фото' - показывает выбор отделов"""
    # Создаем клавиатуру с отделами и кнопкой "Поиск по всем отделам"
    keyboard = []
    
    # Добавляем кнопку поиска по всем отделам
    keyboard.append(["🔍 Поиск по всем отделам"])
    
    # Добавляем кнопки отделов
    dept_buttons = list(DEPARTMENTS.keys())
    for i in range(0, len(dept_buttons), 2):
        row = []
        for j in range(2):
            if i + j < len(dept_buttons):
                row.append(dept_buttons[i + j])
        keyboard.append(row)
    
    # Добавляем кнопку возврата в меню
    keyboard.append(["🔙 Назад в меню"])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🏪 *Выберите отдел для поиска:*\n\n"
        "• 🛠️ ИНСТРУМЕНТЫ - молотки, отвертки, дрели и т.д.\n"
        "• 🎨 КРАСКИ - эмали, лаки, грунтовки и т.д.\n"
        "• 🚰 САНТЕХНИКА - унитазы, раковины, ванны и т.д.\n"
        "• 🧱 СТРОЙМАТЕРИАЛЫ - кирпич, блоки, цемент и т.д.\n"
        "• 🏠 НАПОЛЬНЫЕ ПОКРЫТИЯ - ламинат, линолеум и т.д.\n"
        "• 🌿 САД - инструменты, удобрения, семена и т.д.\n"
        "• 💡 СВЕТ - лампы, светильники, люстры и т.д.\n"
        "• ⚡ ЭЛЕКТРОТОВАРЫ - кабели, розетки и т.д.\n"
        "• 🏠 ОТДЕЛОЧНЫЕ МАТЕРИАЛЫ - обои, штукатурка и т.д.\n"
        "• 🚿 ВОДОСНАБЖЕНИЕ - трубы, фитинги, краны и т.д.\n"
        "• 🔩 СКОБЯНЫЕ ИЗДЕЛИЯ - гвозди, шурупы, болты и т.д.\n"
        "• 🗄️ ХРАНЕНИЕ - полки, ящики, стеллажи и т.д.\n"
        "• 🏠 СТОЛЯРНЫЕ ИЗДЕЛИЯ - доски, брус, фанера и т.д.\n"
        "• 🍽️ КУХНИ - кухонная мебель и аксессуары\n"
        "• 🏢 ПЛИТКА - керамическая, керамогранит и т.д.\n\n"
        "💡 Выбор отдела поможет получить более точные результаты",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def department_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора отдела для поиска по фото"""
    selected_department = update.message.text
    
    # ИСПРАВЛЕНИЕ: Добавляем логирование выбора отдела
    logger.info(f"🏪 ВЫБОР ОТДЕЛА пользователем {update.effective_user.id}: '{selected_department}'")
    
    # Сохраняем выбранный отдел в контексте пользователя
    context.user_data["selected_department"] = selected_department
    
    # ИСПРАВЛЕНИЕ: Устанавливаем состояние ожидания фото
    context.user_data["state"] = "awaiting_photo"
    
    # ИСПРАВЛЕНИЕ: Проверяем, что отдел сохранился
    saved_department = context.user_data.get("selected_department")
    logger.info(f"✅ СОХРАНЕН отдел в контексте: '{saved_department}'")
    logger.info(f"✅ УСТАНОВЛЕНО состояние: awaiting_photo")
    
    # Получаем эмодзи отдела
    department_emoji = selected_department.split()[0]
    
    # Создаем клавиатуру для возврата
    keyboard = [["🔙 Назад к выбору отдела"], ["🔙 Назад в меню"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"{department_emoji} *Поиск в отделе {selected_department}*\n\n"
        f"Теперь отправьте фотографию товара для поиска.\n\n"
        f"💡 Советы для лучшего результата:\n"
        f"• Фотографируйте в хорошем освещении\n"
        f"• Держите камеру параллельно товару\n"
        f"• Избегайте теней и отражений\n"
        f"• Следите, чтобы товар занимал большую часть кадра",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def back_to_departments_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик возврата к выбору отдела"""
    # Сбрасываем выбранный отдел
    context.user_data.pop('selected_department', None)
    
    # Показываем меню выбора отделов
    await photo_search_handler(update, context)

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

        # Проверяем, выбран ли отдел
        selected_department = context.user_data.get('selected_department')
        if not selected_department:
            await update.message.reply_text(
                "❓ Сначала выберите отдел для поиска!\n\n"
                "📋 Нажмите кнопку '📸 Поиск по фото' в главном меню, "
                "затем выберите отдел и после этого отправьте фотографию."
            )
            return
        
        # Показываем сообщение о начале обработки
        dept_emoji = selected_department.split()[0] if selected_department else "📸"
        processing_msg = await update.message.reply_text(
            f"{dept_emoji} Анализирую изображение для отдела {selected_department}...\n"
            "⏳ Это может занять несколько секунд."
        )
        
        photo = update.message.photo[-1]  # Берем фото наибольшего размера
        file = await context.bot.get_file(photo.file_id)
        
        # Создаем директорию для временных файлов
        os.makedirs('temp', exist_ok=True)
        
        # Скачиваем фото
        photo_path = f'temp/{photo.file_id}.jpg'
        await file.download_to_drive(photo_path)
        
        # Сохраняем путь к фото для дальнейшего использования
        short_id = get_short_id(photo.file_id)
        
        # Определяем отдел для поиска
        if selected_department == "🔍 Поиск по всем отделам":
            department_name = "ВСЕ"
        else:
            # Преобразуем отображаемое название в системное
            department_name = DEPARTMENTS.get(selected_department, "ВСЕ")
            
            # ИСПРАВЛЕНИЕ: Проверяем, найден ли отдел в словаре
            if selected_department not in DEPARTMENTS and selected_department != "🔍 Поиск по всем отделам":
                logger.warning(f"⚠️ ПРОБЛЕМА: Отдел '{selected_department}' не найден в словаре DEPARTMENTS!")
                logger.warning(f"⚠️ Доступные отделы: {list(DEPARTMENTS.keys())}")
                logger.warning(f"⚠️ Поиск будет выполнен по всем отделам по умолчанию")
        
        # Логируем детали выбора отдела
        logger.info(f"🎯 Обрабатываем фото от пользователя {update.effective_user.id}")
        logger.info(f"📂 Выбранный отдел пользователем: '{selected_department}'")
        logger.info(f"🏷️ Системное название отдела: '{department_name}'")
        
        # Выполняем поиск сразу в выбранном отделе
        await perform_department_search(update, context, photo_path, photo.file_id, department_name, short_id, processing_msg)
        
        # Очищаем выбранный отдел после поиска
        context.user_data.pop('selected_department', None)
        
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
            
            # Добавляем информацию об отделе если есть
            department_info = ""
            if 'department' in product and product['department']:
                department_info = f"🏪 Отдел: {product['department']}\n"
            
            # Добавляем название товара если есть
            product_name_info = ""
            if 'product_name' in product and product['product_name'] and product['product_name'] != 'nan':
                product_name_info = f"📦 Название: {product['product_name']}\n"
            
            caption = (
                f"{quality_emoji} Результат {i} - {quality_text}\n"
                f"📊 Схожесть: {similarity_percent}% (стабильность: {stability_percent}%)\n"
                f"🏷️ Артикул: {product['item_id']}\n"
                f"{product_name_info}"
                f"{department_info}"
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
    """Обработка выбора отдела для поиска"""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data.startswith("search_dept_"):
            # Парсим callback_data: search_dept_{department}_{short_id}
            parts = query.data.split("_", 3)
            if len(parts) >= 4:
                department = parts[2]  # отдел
                short_id = parts[3]   # короткий ID фото
                
                # Получаем сохраненные данные о фото
                photo_path = context.user_data.get(f'photo_path_{short_id}')
                photo_file_id = context.user_data.get(f'photo_file_id_{short_id}')
                
                if not photo_path or not photo_file_id:
                    await query.edit_message_text("❌ Ошибка: данные фото не найдены. Попробуйте загрузить фото заново.")
                    return
                
                # Показываем сообщение о начале поиска
                dept_text = "всем отделам" if department == "ВСЕ" else f"отделу '{department}'"
                await query.edit_message_text(f"🔍 Анализирую изображение и ищу похожие товары по {dept_text}...")
                
                # Выполняем поиск с использованием нового сервиса
                await perform_department_search(update, context, photo_path, photo_file_id, department, short_id)
                
            else:
                await query.edit_message_text("❌ Ошибка в данных запроса")
                
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора отдела: {e}")
        await query.edit_message_text("❌ Произошла ошибка при обработке запроса")

async def perform_department_search(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  photo_path: str, photo_file_id: str, department: str, short_id: str, processing_msg=None):
    """Выполняет поиск по отделу"""
    import time
    start_time = time.time()
    
    try:
        # Логируем начало поиска
        logger.info(f"🔍 Начинаем поиск по отделу: '{department}'")
        
        # Получаем сервис поиска по отделам
        dept_search_service = get_department_search_service()
        
        # Определяем отдел для поиска (None для поиска по всем отделам)
        search_department = None if department == "ВСЕ" else department
        logger.info(f"🎯 Отдел для API поиска: {search_department}")
        
        # Выполняем поиск
        similar_products = dept_search_service.search_with_multiple_thresholds_by_department(
            photo_path, 
            department=search_department, 
            top_k=5
        )
        
        # Логируем сессию поиска
        stats_service = get_stats_service()
        if stats_service:
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name
            search_method = f"department_{department}"
            session_id = stats_service.log_search_session(
                user_id=user_id,
                username=username,
                photo_file_id=photo_file_id,
                results=similar_products or [],
                search_method=search_method
            )
            
            # Сохраняем контекст поиска для обратной связи
            context.user_data[f'search_session_{short_id}'] = {
                'session_id': session_id,
                'user_id': user_id,
                'username': username,
                'photo_file_id': photo_file_id,
                'results': similar_products or [],
                'search_method': search_method,
                'department': department
            }
        
        # Удаляем временный файл
        if os.path.exists(photo_path):
            os.remove(photo_path)
            
        # Очищаем временные данные
        context.user_data.pop(f'photo_path_{short_id}', None)
        context.user_data.pop(f'photo_file_id_{short_id}', None)
        
        # Выводим диагностику в логи
        department_for_log = "всем отделам" if department == "ВСЕ" else f"отделе '{department}'"
        
        if similar_products:
            similarities = [p['similarity'] for p in similar_products]
            logger.info(f"Найдено {len(similar_products)} товаров в {department_for_log}, схожести: {similarities}")
        else:
            logger.warning(f"Поиск в {department_for_log} не дал результатов!")
        
        if not similar_products:
            # Получаем статистику по отделам для вывода
            dept_stats = dept_search_service.get_department_stats()
            dept_info = f"\n\n📊 Доступные отделы:\n"
            for dept, count in list(dept_stats.items())[:5]:
                dept_info += f"• {dept}: {count} товаров\n"
            
            # Используем processing_msg если есть, иначе callback_query
            if processing_msg:
                await processing_msg.edit_text(
                    f"😔 К сожалению, не удалось найти похожие товары в отделе '{department}'.\n\n"
                    "🎯 Попробуйте:\n"
                    "• Выбрать другой отдел\n"
                    "• Поиск по всем отделам\n"
                    "• Сделать более четкое фото\n"
                    "• Сфотографировать товар с другого ракурса"
                    + dept_info
                )
            else:
                await update.callback_query.edit_message_text(
                    f"😔 К сожалению, не удалось найти похожие товары в отделе '{department}'.\n\n"
                    "🎯 Попробуйте:\n"
                    "• Поиск по всем отделам\n"
                    "• Выбрать другой отдел\n"
                    "• Сделать более четкое фото\n"
                    "• Сфотографировать товар с другого ракурса"
                    + dept_info
                )
            return
        
        # Проверяем качество результатов
        best_similarity = similar_products[0]['similarity']
        
        # Формируем правильное отображение отдела
        department_display = "всем отделам" if department == "ВСЕ" else f"отделе '{department}'"
        
        if best_similarity < 0.3:
            quality_warning = f"\n⚠️ Результаты с низкой схожестью в {department_display}"
        elif best_similarity < 0.5:
            quality_warning = f"\n📝 Результаты с умеренной схожестью в {department_display}"
        else:
            quality_warning = f"\n✅ Найдены похожие товары в {department_display}!"
        
        # Используем processing_msg если есть, иначе callback_query
        if processing_msg:
            await processing_msg.edit_text(
                f"🎯 Найдено {len(similar_products)} результатов{quality_warning}"
            )
        else:
            await update.callback_query.edit_message_text(
                f"🎯 Найдено {len(similar_products)} результатов{quality_warning}"
            )
        
        # Отправляем результаты
        await send_search_results(update, context, similar_products, short_id)
        
        # Логируем производительность
        try:
            from toolbot.services.monitoring import monitoring
            response_time = (time.time() - start_time) * 1000
            monitoring.log_response_time('department_search', response_time, success=True)
            monitoring.log_model_performance('department_search', response_time, accuracy=best_similarity)
        except Exception as e:
            logger.warning(f"Ошибка логирования производительности: {e}")
            
    except Exception as e:
        logger.error(f"Ошибка при поиске по отделу: {e}")
        await update.callback_query.edit_message_text(
            f"❌ Произошла ошибка при поиске в отделе '{department}'. Попробуйте еще раз."
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
    
    # Проверяем админское пошаговое заполнение данных товара
    if 'admin_adding_product' in context.user_data:
        from handlers.admin_training_handler import handle_admin_product_step
        await handle_admin_product_step(update, context, user_text)
        return
    
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
    
    # ИСПРАВЛЕНИЕ: Проверяем, является ли это сообщение кнопкой отдела
    text = update.message.text
    logger.info(f"🔍 Обрабатываем текстовое сообщение: '{text}'")
    
    # Проверяем, это ли кнопка отдела
    DEPARTMENTS = [
        "🔍 Поиск по всем отделам",
        "🛠️ ИНСТРУМЕНТЫ", "🎨 КРАСКИ", "🚰 САНТЕХНИКА", "🧱 СТРОЙМАТЕРИАЛЫ",
        "🏠 НАПОЛЬНЫЕ ПОКРЫТИЯ", "🌿 САД", "💡 СВЕТ", "⚡ ЭЛЕКТРОТОВАРЫ",
        "🏠 ОТДЕЛОЧНЫЕ МАТЕРИАЛЫ", "🚿 ВОДОСНАБЖЕНИЕ", "🔩 СКОБЯНЫЕ ИЗДЕЛИЯ",
        "🗄️ ХРАНЕНИЕ", "🏠 СТОЛЯРНЫЕ ИЗДЕЛИЯ", "🍽️ КУХНИ", "🏢 ПЛИТКА"
    ]
    
    if text in DEPARTMENTS:
        logger.info(f"✨ Обнаружена кнопка отдела: {text}")
        await department_selection_handler(update, context)
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
        
        # Сохраняем состояние ожидания описания товара
        context.user_data['awaiting_new_product_for'] = short_id
        
        await query.edit_message_caption(
            caption="➕ *Предложение нового товара*\n\n"
                   "📝 Опишите товар, который вы искали:\n\n"
                   "💡 Например:\n"
                   "• `Дрель ударная Makita`\n"
                   "• `Саморезы по дереву 4x50`\n"
                   "• `Краска белая водоэмульсионная`\n\n"
                   "✍️ Напишите название и описание товара:",
            parse_mode='Markdown',
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





async def generate_product_vectors(image_source: str, title: str, description: str):
    """Генерация векторов для товара через CLIP модель"""
    try:
        # Импортируем необходимые модули
        from toolbot.services.image_search import ImageSearchService
        import torch
        import numpy as np
        from PIL import Image
        import requests
        from io import BytesIO
        
        # Инициализируем модель
        search_service = ImageSearchService.get_instance()
        if not search_service.initialize_model():
            logger.error("❌ Не удалось инициализировать модель поиска")
            return None
        
        # Сохраняем изображение во временный файл для обработки
        temp_image_path = None
        if image_source.startswith('http'):
            # Загружаем по URL
            response = requests.get(image_source, timeout=10)
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content)).convert('RGB')
                # Сохраняем во временный файл
                import tempfile
                temp_image_path = tempfile.mktemp(suffix='.jpg')
                image.save(temp_image_path)
            else:
                logger.error(f"❌ Не удалось загрузить изображение по URL: {image_source}")
                return None
        else:
            # Локальный файл
            if os.path.exists(image_source):
                temp_image_path = image_source
            else:
                logger.error(f"❌ Файл не найден: {image_source}")
                return None
        
        if temp_image_path is None:
            logger.error(f"❌ Не удалось подготовить изображение: {image_source}")
            return None
            
        # Генерируем векторы изображения через сервис
        image_vector = search_service.extract_features(temp_image_path)
        if image_vector is None:
            logger.error(f"❌ Не удалось извлечь признаки изображения")
            # Удаляем временный файл если создавали его
            if image_source.startswith('http') and os.path.exists(temp_image_path):
                os.remove(temp_image_path)
            return None
        
        # Генерируем векторы текста через CLIP модель (с ограничением длины)
        text_prompt = f"{title}. {description}"
        
        # CLIP принимает максимум 77 токенов, обрезаем если нужно
        max_length = 75  # Оставляем запас для специальных токенов
        text_inputs = search_service.clip_processor(
            text=[text_prompt], 
            return_tensors="pt", 
            padding=True, 
            truncation=True,
            max_length=max_length
        )
        
        # Переносим тензоры на то же устройство что и модель
        device = next(search_service.clip_model.parameters()).device
        text_inputs = {k: v.to(device) for k, v in text_inputs.items()}
        
        with torch.no_grad():
            text_features = search_service.clip_model.get_text_features(**text_inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            text_vector = text_features.cpu().numpy().astype('float32').reshape(-1)
        
        # Комбинируем векторы (80% изображение, 20% текст)
        combined_vector = 0.8 * image_vector + 0.2 * text_vector
        
        # Нормализуем
        combined_vector = combined_vector / np.linalg.norm(combined_vector)
        
        # Конвертируем в bytes для сохранения в БД
        vector_bytes = combined_vector.astype(np.float32).tobytes()
        
        # Удаляем временный файл если создавали его
        if image_source.startswith('http') and os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        
        logger.info(f"✅ Векторы сгенерированы для товара: {title}")
        return vector_bytes
        
    except Exception as e:
        logger.error(f"❌ Ошибка при генерации векторов: {e}")
        return None