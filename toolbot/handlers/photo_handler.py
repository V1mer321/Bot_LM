"""
Обработчики для работы с фотографиями и визуального поиска
"""
import os
import logging
import traceback
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
import asyncio

from toolbot.utils.access import is_allowed_user
from toolbot.config import is_admin  # Используем зашифрованную конфигурацию для админ-проверок
from toolbot.utils.image_utils import preprocess_image_for_search, extract_tool_by_bbox
from toolbot.utils.file_utils import TempFileManager
from toolbot.utils.rate_limiter import check_rate_limit
from toolbot.utils.async_processor import process_multiple
from config import load_config

logger = logging.getLogger(__name__)

# Ленивая инициализация сервиса поиска изображений
_image_search_initialized = False

def get_image_search_functions():
    """Получение функций поиска изображений с ленивой инициализацией"""
    global _image_search_initialized
    
    if not _image_search_initialized:
        try:
            # Импортируем только при первом использовании
            from toolbot.services.image_search import (
                initialize_image_search, update_image_index, find_similar_images, 
                enhanced_image_search, classify_tool_type, detect_brand_by_color,
                detect_brand_from_filename, detect_tools_on_image
            )
            
            # Инициализируем сервис
            logger.info("Ленивая инициализация сервиса поиска изображений...")
            success = initialize_image_search()
            if success:
                logger.info("✓ Сервис поиска изображений успешно инициализирован")
                _image_search_initialized = True
            else:
                logger.warning("⚠ Инициализация сервиса не удалась")
                
            # Возвращаем функции
            return {
                'initialize_image_search': initialize_image_search,
                'update_image_index': update_image_index,
                'find_similar_images': find_similar_images,
                'enhanced_image_search': enhanced_image_search,
                'classify_tool_type': classify_tool_type,
                'detect_brand_by_color': detect_brand_by_color,
                'detect_brand_from_filename': detect_brand_from_filename,
                'detect_tools_on_image': detect_tools_on_image
            }
        except Exception as e:
            logger.error(f"Ошибка при ленивой инициализации: {str(e)}")
            logger.debug(traceback.format_exc())
            return None
    else:
        # Если уже инициализирован, просто импортируем функции
        from toolbot.services.image_search import (
            initialize_image_search, update_image_index, find_similar_images, 
            enhanced_image_search, classify_tool_type, detect_brand_by_color,
            detect_brand_from_filename, detect_tools_on_image
        )
        
        return {
            'initialize_image_search': initialize_image_search,
            'update_image_index': update_image_index,
            'find_similar_images': find_similar_images,
            'enhanced_image_search': enhanced_image_search,
            'classify_tool_type': classify_tool_type,
            'detect_brand_by_color': detect_brand_by_color,
            'detect_brand_from_filename': detect_brand_from_filename,
            'detect_tools_on_image': detect_tools_on_image
        }

async def photo_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик для запуска поиска по фото
    """
    user_id = update.effective_user.id
    
    if not is_allowed_user(user_id):
        from toolbot.handlers.common import show_error_message
        await show_error_message(update, "access_denied")
        return
    
    # Проверяем ограничение скорости
    is_allowed, wait_time = check_rate_limit(user_id, "general")
    if not is_allowed:
        wait_time_rounded = round(wait_time, 1)
        await update.message.reply_text(
            f"⏱ Вы отправляете слишком много запросов.\n"
            f"Пожалуйста, подождите {wait_time_rounded} секунд перед следующим запросом."
        )
        return
    
    # Логируем использование команды
    analytics = context.bot_data.get('analytics')
    if analytics:
        analytics.log_command("photo_search", user_id)
    
    # Отключаем предыдущий режим ожидания фото, если был активен
    context.user_data["state"] = 'selecting_department'
    
    # Создаем клавиатуру для выбора отдела
    keyboard = [
        ["🧱 Строительные материалы", "🪑 Столярные изделия"],
        ["⚡ Электротовары", "🔨 Инструменты"],
        ["🏠 Напольные покрытия", "🧱 Плитка"],
        ["🚽 Сантехника", "🚿 Водоснабжение"],
        ["🌱 Сад", "🔩 Скобяные изделия"],
        ["🎨 Краски", "✨ Отделочные материалы"],
        ["💡 Свет", "📦 Хранение"],
        ["🍳 Кухни"],
        ["🔙 Назад в меню"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Отправляем сообщение с инструкцией и клавиатурой выбора отдела
    await update.message.reply_text(
        "📸 *Поиск по фото*\n\n"
        "Сначала выберите отдел, в котором хотите искать товар:\n"
        "• 🧱 Строительные материалы - цемент, гипс, штукатурка и т.д.\n"
        "• 🪑 Столярные изделия - деревообработка, фанера и т.д.\n"
        "• ⚡ Электротовары - розетки, провода, выключатели и т.д.\n"
        "• 🔨 Инструменты - все виды инструментов\n"
        "• 🏠 Напольные покрытия - ламинат, паркет, линолеум и т.д.\n"
        "• 🧱 Плитка - керамическая, керамогранит и т.д.\n"
        "• 🚽 Сантехника - унитазы, раковины, ванны и т.д.\n"
        "• 🚿 Водоснабжение - трубы, краны, фитинги и т.д.\n"
        "• 🌱 Сад - товары для сада и огорода\n"
        "• 🔩 Скобяные изделия - метизы, крепежи, фурнитура и т.д.\n"
        "• 🎨 Краски - краски, эмали, лаки и т.д.\n"
        "• ✨ Отделочные материалы - обои, декоративная штукатурка и т.д.\n"
        "• 💡 Свет - лампы, светильники и т.д.\n"
        "• 📦 Хранение - полки, ящики, стеллажи и т.д.\n"
        "• 🍳 Кухни - кухонная мебель и аксессуары\n\n"
        "💡 Выбор отдела поможет получить более точные результаты",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def department_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик выбора отдела для поиска по фото
    """
    user_id = update.effective_user.id
    
    if not is_allowed_user(user_id):
        from toolbot.handlers.common import show_error_message
        await show_error_message(update, "access_denied")
        return
    
    # Проверяем ограничение скорости
    is_allowed, wait_time = check_rate_limit(user_id, "general")
    if not is_allowed:
        wait_time_rounded = round(wait_time, 1)
        await update.message.reply_text(
            f"⏱ Вы отправляете слишком много запросов.\n"
            f"Пожалуйста, подождите {wait_time_rounded} секунд перед следующим запросом."
        )
        return
    
    selected_department = update.message.text
    
    # Сохраняем выбранный отдел в контексте пользователя
    context.user_data["selected_department"] = selected_department
    
    # Включаем режим ожидания фотографии
    context.user_data["state"] = "awaiting_photo"
    
    # Получаем эмодзи отдела
    department_emoji = selected_department.split()[0]
    
    # Создаем клавиатуру для отмены
    keyboard = [["🔙 Назад к выбору отдела"], ["🔙 Назад в меню"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Логируем использование команды с указанием отдела
    analytics = context.bot_data.get('analytics')
    if analytics:
        analytics.log_command(f"photo_search_{selected_department}", user_id)
    
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


async def back_to_departments_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик возврата к выбору отдела"""
    # Сбрасываем текущие состояния
    context.user_data["state"] = None
    
    # Вызываем обработчик поиска по фото для показа меню отделов
    await photo_search_handler(update, context)


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик для обработки фотографий с обнаружением нескольких инструментов
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or "пользователь"
    
    # Логируем получение фото от пользователя
    analytics = context.bot_data.get('analytics')
    if analytics:
        analytics.log_user_activity(user_id, "photo_received", f"Пользователь @{username} отправил фото для поиска")
    
    if not is_allowed_user(user_id):
        from toolbot.handlers.common import show_error_message
        await show_error_message(update, "access_denied")
        return
    
    # Проверяем, находится ли пользователь в состоянии ожидания фотографии
    if context.user_data.get('state') != 'awaiting_photo':
        await update.message.reply_text(
            "❓ Я не ожидаю фотографию. Сначала выберите опцию 'Поиск по фото' в главном меню, "
            "затем выберите отдел и после этого отправьте фотографию."
        )
        return
    
    # Проверяем ограничение скорости для фото запросов
    # Для администраторов ограничений нет
    if not is_admin(user_id):
        is_allowed, wait_time = check_rate_limit(user_id, "photo")
        if not is_allowed:
            wait_time_rounded = round(wait_time, 1)
            await update.message.reply_text(
                f"⏱ Между запросами на поиск по фото должно пройти некоторое время.\n"
                f"Пожалуйста, подождите {wait_time_rounded} секунд перед отправкой следующего фото."
            )
            return
    
    # Получаем выбранный отдел (если есть)
    selected_department = context.user_data.get("selected_department", "")
    department_emoji = selected_department.split()[0] if selected_department else "📸"

    # Отправляем сообщение о начале обработки
    processing_message = await update.message.reply_text(
        f"{department_emoji} Начинаю обработку фотографии...\n"
        "Это может занять некоторое время."
    )

    # Используем менеджер контекста для временных файлов
    with TempFileManager() as temp_manager:
        try:
            # Проверяем доступное место на диске
            if not temp_manager.check_disk_space(min_required_mb=50):
                await processing_message.edit_text(
                    "❌ Недостаточно места на диске для обработки изображений.\n"
                    "Пожалуйста, обратитесь к администратору."
                )
                return
                
            # После получения фотографии отключаем режим
            context.user_data["state"] = None

            # Загружаем конфигурацию
            config = load_config()
            photos_folder = config.get("photos_folder")
            
            # Проверка наличия папки для фотографий
            if not photos_folder:
                logger.error("Ошибка: не указана папка для фотографий в конфигурации")
                await processing_message.edit_text(
                    "❌ Ошибка конфигурации: не указана папка для фотографий.\n"
                    "Пожалуйста, обратитесь к администратору."
                )
                return
                
            # Проверка существования папки и создание, если не существует
            if not os.path.exists(photos_folder):
                try:
                    os.makedirs(photos_folder, exist_ok=True)
                    logger.info(f"Создана папка для фотографий: {photos_folder}")
                except Exception as e:
                    logger.error(f"Не удалось создать папку для фотографий: {e}")
                    await processing_message.edit_text(
                        "❌ Ошибка: не удалось создать папку для фотографий.\n"
                        "Пожалуйста, обратитесь к администратору."
                    )
                    return
                    
            # Получаем информацию о фото
            photo = update.message.photo[-1]  # Берем самую большую версию фото
            file_id = photo.file_id
            
            # Получаем файл от Telegram и сохраняем его во временную директорию
            photo_file = await context.bot.get_file(file_id)
            
            # Сохраняем фото во временный файл с уникальным именем
            temp_photo_path = temp_manager.get_temp_file_path(file_id, "jpg")
            await photo_file.download_to_drive(temp_photo_path)
            
            logger.info(f"Фото сохранено во временный файл: {temp_photo_path}")
            
            # Обновляем статус обработки
            await processing_message.edit_text(
                f"{department_emoji} Фото получено, выполняю предварительную обработку..."
            )
            
            # Улучшаем изображение для поиска с обработкой исключений
            try:
                enhanced_image_path = preprocess_image_for_search(temp_photo_path)
                if enhanced_image_path:
                    logger.info(f"Создано улучшенное изображение: {enhanced_image_path}")
                    search_image_path = enhanced_image_path
                else:
                    logger.warning("Не удалось создать улучшенное изображение, используем оригинал")
                    search_image_path = temp_photo_path
            except Exception as e:
                logger.error(f"Ошибка при предварительной обработке изображения: {e}")
                search_image_path = temp_photo_path  # Используем оригинал при ошибке
                
            # Обновляем статус обработки
            await processing_message.edit_text(
                f"{department_emoji} Выполняю поиск совпадений..."
            )
            
            # Инициализируем модели и индекс, если необходимо
            image_search_functions = get_image_search_functions()
            
            if not image_search_functions:
                logger.error("Не удалось инициализировать модели поиска")
                await processing_message.edit_text(
                    "❌ Не удалось инициализировать модели поиска.\n"
                    "Пожалуйста, попробуйте позже или обратитесь к администратору."
                )
                return
            
            # Обновляем индекс поиска
            try:
                update_index_result = image_search_functions['update_image_index'](photos_folder)
                if not update_index_result:
                    logger.warning("Обновление индекса вернуло пустой результат, возможны проблемы с поиском")
            except Exception as e:
                logger.error(f"Ошибка при обновлении индекса: {e}")
                # Продолжаем выполнение, так как индекс может уже быть создан
            
            # Получаем информацию об объектах на изображении с обработкой исключений
            try:
                detected_objects = image_search_functions['detect_tools_on_image'](search_image_path)
                
                # Логируем количество найденных объектов
                if detected_objects:
                    logger.info(f"Обнаружено {len(detected_objects)} инструментов на изображении")
                else:
                    logger.warning("Не обнаружено инструментов на изображении")
            except Exception as e:
                logger.error(f"Ошибка при обнаружении объектов: {e}")
                detected_objects = None  # Используем None при ошибке
                
            # Если найдены объекты, обрабатываем каждый отдельно
            if detected_objects and len(detected_objects) > 1:
                # Обновляем статус
                await processing_message.edit_text(
                    f"{department_emoji} Обнаружено {len(detected_objects)} инструментов! Анализирую каждый..."
                )
                
                # Функция для обработки отдельного объекта
                def process_single_object(obj_info, img_path, temp_mgr, photos_dir):
                    try:
                        # Получаем информацию об объекте
                        bbox = obj_info.get("bbox")
                        tool_type = obj_info.get("tool_type", "unknown")
                        tool_type_ru = obj_info.get("tool_type_ru", "Неизвестный инструмент")
                        confidence = obj_info.get("confidence", 0.0)
                        
                        # Извлекаем объект из изображения
                        crop_path = extract_tool_by_bbox(img_path, bbox, temp_mgr)
                        if not crop_path:
                            logger.error(f"Не удалось извлечь объект с bbox {bbox}")
                            return None
                            
                        # Улучшаем изображение объекта для поиска
                        enhanced_object_path = preprocess_image_for_search(crop_path)
                        search_object_path = enhanced_object_path if enhanced_object_path else crop_path
                        
                        # Ищем похожие изображения для этого объекта
                        results = image_search_functions['find_similar_images'](search_object_path, top_n=3)
                        
                        if not results:
                            logger.warning(f"Не найдено результатов для объекта {tool_type}")
                            return None
                        
                        # Определяем бренд
                        brand = image_search_functions['detect_brand_by_color'](search_object_path)
                        if not brand:
                            brand = image_search_functions['detect_brand_from_filename'](search_object_path)
                            if brand == "Неизвестный":
                                brand = None
                        
                        return {
                            'image_path': search_object_path,
                            'results': results[:3],  # Берем только топ-3 результата
                            'tool_type': tool_type_ru,
                            'brand': brand,
                            'confidence': confidence
                        }
                    except Exception as e:
                        logger.error(f"Ошибка при обработке объекта: {e}")
                        return None
                
                # Параллельно обрабатываем все объекты с обработкой ошибок
                try:
                    object_results = await process_multiple(
                        process_single_object, 
                        detected_objects, 
                        search_image_path, 
                        temp_manager, 
                        photos_folder
                    )
                    
                    # Фильтруем None результаты
                    object_results = [r for r in object_results if r is not None]
                except Exception as e:
                    logger.error(f"Ошибка при параллельной обработке объектов: {e}")
                    object_results = []
                
                if not object_results:
                    await processing_message.edit_text(
                        "❌ Не удалось обработать обнаруженные объекты.\n"
                        "Пожалуйста, попробуйте снова с другим изображением."
                    )
                    return
                
                # Сортируем результаты по уверенности
                object_results.sort(key=lambda x: x['confidence'], reverse=True)
                
                # Создаем результирующее сообщение
                result_message = f"{department_emoji} Результаты поиска:\n\n"
                for i, obj_result in enumerate(object_results):
                    tool_type = obj_result['tool_type']
                    brand = obj_result['brand'] if obj_result['brand'] else "Неизвестный"
                    confidence = obj_result['confidence'] * 100
                    
                    result_message += f"🔹 Объект #{i+1}: {tool_type}\n"
                    result_message += f"  • Бренд: {brand}\n"
                    result_message += f"  • Уверенность: {confidence:.1f}%\n"
                    
                    # Для каждого объекта добавляем топ результаты
                    if obj_result['results']:
                        result_message += "  • Похожие товары:\n"
                        for j, (img_path, similarity) in enumerate(obj_result['results'][:3]):
                            file_name = os.path.basename(img_path)
                            similarity_percent = round(similarity * 100)
                            result_message += f"    - {file_name} ({similarity_percent}%)\n"
                    
                    result_message += "\n"
                
                # Обновляем сообщение с результатами
                await processing_message.edit_text(result_message)
                
                # Отправляем изображения самых похожих товаров для каждого объекта
                for i, obj_result in enumerate(object_results):
                    if obj_result['results']:
                        try:
                            top_match_path = obj_result['results'][0][0]
                            caption = f"Объект #{i+1}: Лучшее совпадение"
                            await update.message.reply_photo(
                                photo=open(top_match_path, 'rb'),
                                caption=caption
                            )
                        except Exception as e:
                            logger.error(f"Ошибка при отправке изображения: {e}")
                
            else:
                # Если найден только один объект или объекты не обнаружены
                # используем улучшенный поиск для всего изображения
                
                # Ищем похожие изображения
                logger.info(f"Использую улучшенное изображение для поиска: {search_image_path}")
                
                # Обновляем статус обработки
                await processing_message.edit_text(
                    f"{department_emoji} Запускаю расширенный поиск изображений..."
                )
                
                # Ищем похожие изображения с обработкой ошибок
                try:
                    results = image_search_functions['enhanced_image_search'](search_image_path)
                except Exception as e:
                    logger.error(f"Ошибка при выполнении расширенного поиска: {e}")
                    results = []
                
                if not results:
                    await processing_message.edit_text(
                        "❌ Не найдено похожих изображений.\n"
                        "Попробуйте другую фотографию или измените угол съемки."
                    )
                    return
                    
                # Формируем сообщение с результатами
                result_message = f"{department_emoji} Результаты поиска:\n\n"
                result_message += f"Найдено {len(results)} похожих изображений:\n\n"
                
                for i, (img_path, similarity) in enumerate(results[:5]):
                    file_name = os.path.basename(img_path)
                    similarity_percent = round(similarity * 100)
                    result_message += f"{i+1}. {file_name} - Совпадение: {similarity_percent}%\n"
                
                # Обновляем сообщение с результатами
                await processing_message.edit_text(result_message)
                
                # Отправляем изображения топ-3 результатов
                for i, (img_path, similarity) in enumerate(results[:3]):
                    try:
                        file_name = os.path.basename(img_path)
                        similarity_percent = round(similarity * 100)
                        caption = f"Совпадение #{i+1}: {similarity_percent}% - {file_name}"
                        
                        await update.message.reply_photo(
                            photo=open(img_path, 'rb'),
                            caption=caption
                        )
                    except Exception as e:
                        logger.error(f"Ошибка при отправке изображения результата: {e}")
                
            # Логируем успешный поиск
            analytics = context.bot_data.get('analytics')
            if analytics:
                analytics.log_photo_search(user_id, selected_department, bool(results))
                
        except Exception as e:
            logger.error(f"Ошибка при обработке фото: {e}")
            logger.error(traceback.format_exc())
            
            await processing_message.edit_text(
                "❌ Произошла ошибка при обработке фотографии.\n"
                "Пожалуйста, попробуйте позже или обратитесь к администратору."
            )
            
            # Логируем ошибку
            analytics = context.bot_data.get('analytics')
            if analytics:
                analytics.log_error("photo_handler", str(e), user_id) 