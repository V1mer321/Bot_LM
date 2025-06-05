"""
ToolBot - основной модуль приложения
"""
import os
import logging
import asyncio
import sys
import traceback
import importlib.util
import torch
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler

# Импортируем модули повышения надежности
from toolbot.utils.enhanced_logging import setup_logging, LogLevel, LogFormat, get_logger
from toolbot.utils.error_handler import ErrorSeverity, error_handler_instance, async_error_handler, error_handler
from toolbot.utils.recovery import RecoveryManager, ComponentState, register_component

# Импортируем модуль совместимости telebot
from toolbot.utils.telebot_compatibility import create_telebot

# Настройка расширенного логирования
setup_logging(
    console_level=LogLevel.INFO,
    file_level=LogLevel.DEBUG,
    console_format=LogFormat.SIMPLE,
    file_format=LogFormat.DETAILED,
    log_dir="logs"
)

# Получаем логгер для модуля
logger = get_logger(__name__)

# Импортируем нужные модули
from toolbot.config import load_config
from toolbot.services.analytics import Analytics

# Импортируем модули технических улучшений
from toolbot.utils.model_optimizer import get_model_optimizer
from toolbot.utils.light_models import get_optimized_detector

# Добавляем путь к корневым обработчикам
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Импортируем обработчики команд
from toolbot.handlers.common import start_handler, help_handler, stop_handler, back_to_menu_handler
from toolbot.handlers.admin import (admin_panel_handler, user_management_handler, add_user_handler,
                                  remove_user_handler, list_users_handler, 
                                  back_to_admin_panel_handler,
                                  feedback_management_handler, feedback_stats_button_handler,
                                  errors_button_handler, suggestions_button_handler,
                                  back_to_feedback_handler, add_admin_handler,
                                  search_statistics_handler, detailed_search_stats_handler,
                                  recent_complaints_handler, user_activity_handler,
                                  active_users_handler, all_users_handler,
                                  search_user_handler, activity_stats_handler,
                                  update_databases_handler)
from toolbot.handlers.contacts import (contacts_handler, stores_handler, maps_handler,
                                     skobyanka_handler, back_to_contacts_handler)
# Используем РЕАЛЬНЫЙ photo_handler который работает с unified_products.db
from handlers.photo_handler import (handle_photo as photo_handler, 
                                  handle_not_my_item_callback, handle_add_comment_callback,
                                  handle_try_another_photo_callback, handle_contact_support_callback,
                                  handle_text_message)
# Используем тестовые обработчики только для навигации  
from toolbot.handlers.photo_handler import photo_search_handler, department_selection_handler, back_to_departments_handler
from toolbot.handlers.text_handler import text_handler
# Импортируем обработчики обратной связи
from toolbot.handlers.feedback_handlers import (report_error_handler, suggest_improvement_handler,
                                                process_error_report, process_improvement_suggestion,
                                                cancel_feedback_handler, view_feedback_stats_handler,
                                                view_errors_handler, view_suggestions_handler,
                                                handle_error_status_callback, handle_suggestion_status_callback,
                                                handle_suggestion_priority_callback, handle_show_full_error_callback,
                                                handle_show_full_suggestion_callback)

# Добавляем обработчики для мониторинга надежности
from toolbot.handlers.reliability_handlers import (
    error_stats_handler, components_status_handler, 
    test_recovery_handler, logs_handler
)

# Импортируем функцию проверки доступа из utils/access.py
from toolbot.utils.access import is_allowed_user

# Проверка доступности ONNX Runtime
def check_onnx_available():
    """Проверяет доступность ONNX Runtime для оптимизации моделей"""
    try:
        import onnxruntime
        logger.info(f"✅ ONNX Runtime доступен (версия {onnxruntime.__version__})")
        
        # Проверяем доступные провайдеры (исполнители)
        providers = onnxruntime.get_available_providers()
        logger.info(f"Доступные провайдеры ONNX: {', '.join(providers)}")
        
        return True
    except ImportError:
        logger.warning("⚠️ ONNX Runtime не установлен. Оптимизация моделей будет ограничена.")
        return False

# Инициализация моделей
@error_handler(severity=ErrorSeverity.MEDIUM)
def initialize_models():
    """Асинхронная инициализация моделей машинного обучения"""
    try:
        logger.info("Начинаем инициализацию оптимизированных моделей...")
        
        # Проверяем наличие GPU
        gpu_available = torch.cuda.is_available()
        if gpu_available:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"✅ Обнаружен GPU: {gpu_name} ({gpu_memory:.2f} ГБ)")
            logger.info("🚀 ML-модели будут работать с GPU ускорением!")
        else:
            logger.info("⚠️ GPU не обнаружен. Будет использован CPU для вычислений.")
            logger.info("💡 Для ускорения установите CUDA версию PyTorch:")
            logger.info("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
            logger.info("   Или запустите: python check_gpu.py для диагностики")
        
        # Проверяем доступность ONNX Runtime
        onnx_available = check_onnx_available()
        
        # Инициализируем легкие модели для обнаружения объектов
        try:
            # Загружаем и оптимизируем модели
            mobilenet_detector = get_optimized_detector("mobilenet")
            logger.info(f"✅ Модель MobileNetV3 успешно инициализирована")
            
            # Инициализация EfficientDet только если доступен ONNX
            if onnx_available:
                efficientdet_detector = get_optimized_detector("efficientdet")
                logger.info(f"✅ Модель EfficientDet-Lite успешно инициализирована")
        except Exception as e:
            logger.error(f"❌ Ошибка при инициализации легких моделей: {e}")
        
        logger.info("✅ Инициализация моделей завершена")
        return True
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при инициализации моделей: {e}")
        return False

def register_handlers(application):
    """Регистрация обработчиков команд телеграм-бота"""
    try:
        # Основные команды
        application.add_handler(CommandHandler("start", start_handler))
        application.add_handler(CommandHandler("help", help_handler))
        application.add_handler(CommandHandler("stop", stop_handler))
        application.add_handler(CommandHandler("admin", admin_panel_handler))
        
        # Кнопки главного меню
        application.add_handler(MessageHandler(filters.Regex("^❓ Помощь$"), help_handler))
        application.add_handler(MessageHandler(filters.Regex("^📞 Контакты$"), contacts_handler))
        application.add_handler(MessageHandler(filters.Regex("^📸 Поиск по фото$"), photo_search_handler))
        
        # Кнопки навигации
        application.add_handler(MessageHandler(filters.Regex("^🔙 Назад в меню$"), back_to_menu_handler))
        
        # Кнопки раздела контактов
        application.add_handler(MessageHandler(filters.Regex("^🏪 Магазины$"), stores_handler))
        application.add_handler(MessageHandler(filters.Regex("^🗺 Карты$"), maps_handler))
        application.add_handler(MessageHandler(filters.Regex("^🔧 Скобянка$"), skobyanka_handler))
        application.add_handler(MessageHandler(filters.Regex("^🔙 Назад в контакты$"), back_to_contacts_handler))
        
        # Кнопки выбора отдела для поиска по фото
        application.add_handler(MessageHandler(filters.Regex("^🧱 Строительные материалы$|^🪑 Столярные изделия$|^⚡ Электротовары$|^🔨 Инструменты$|^🏠 Напольные покрытия$|^🧱 Плитка$|^🚽 Сантехника$|^🚿 Водоснабжение$|^🌱 Сад$|^🔩 Скобяные изделия$|^🎨 Краски$|^✨ Отделочные материалы$|^💡 Свет$|^📦 Хранение$|^🍳 Кухни$"), department_selection_handler))
        application.add_handler(MessageHandler(filters.Regex("^🔙 Назад к выбору отдела$"), back_to_departments_handler))
        
        # Кнопки админ-панели
        application.add_handler(MessageHandler(filters.Regex("^👥 Управление пользователями$"), user_management_handler))
        application.add_handler(MessageHandler(filters.Regex("^💬 Обратная связь$"), feedback_management_handler))
        application.add_handler(MessageHandler(filters.Regex("^📊 Статистика поиска$"), search_statistics_handler))
        application.add_handler(MessageHandler(filters.Regex("^👀 Активность пользователей$"), user_activity_handler))
        application.add_handler(MessageHandler(filters.Regex("^👑 Добавить администратора$"), add_admin_handler))
        application.add_handler(MessageHandler(filters.Regex("^🔄 Обновить базы$"), update_databases_handler))
        application.add_handler(MessageHandler(filters.Regex("^📋 Список пользователей$"), list_users_handler))
        application.add_handler(MessageHandler(filters.Regex("^➕ Добавить пользователя$"), add_user_handler))
        application.add_handler(MessageHandler(filters.Regex("^➖ Удалить пользователя$"), remove_user_handler))
        application.add_handler(MessageHandler(filters.Regex("^🔙 Назад в админ-панель$"), back_to_admin_panel_handler))
        
        # Кнопки раздела активности пользователей
        application.add_handler(MessageHandler(filters.Regex("^📈 Активные пользователи$"), active_users_handler))
        application.add_handler(MessageHandler(filters.Regex("^📋 Все пользователи$"), all_users_handler))
        application.add_handler(MessageHandler(filters.Regex("^🔍 Поиск по ID$"), search_user_handler))
        application.add_handler(MessageHandler(filters.Regex("^📊 Общая статистика$"), activity_stats_handler))
        
        # Кнопки раздела статистики поиска
        application.add_handler(MessageHandler(filters.Regex("^📋 Детальная статистика$"), detailed_search_stats_handler))
        application.add_handler(MessageHandler(filters.Regex("^🔄 Обновить данные$"), search_statistics_handler))
        application.add_handler(MessageHandler(filters.Regex("^📝 Последние жалобы$"), recent_complaints_handler))
        application.add_handler(MessageHandler(filters.Regex("^📈 Тренды поиска$"), search_statistics_handler))
        
        # Кнопки раздела обратной связи в админ панели
        application.add_handler(MessageHandler(filters.Regex("^📊 Статистика обратной связи$"), feedback_stats_button_handler))
        application.add_handler(MessageHandler(filters.Regex("^🐛 Просмотр ошибок$"), errors_button_handler))
        application.add_handler(MessageHandler(filters.Regex("^💡 Просмотр предложений$"), suggestions_button_handler))
        application.add_handler(MessageHandler(filters.Regex("^🔙 Назад к обратной связи$"), back_to_feedback_handler))
        
        # Кнопки пользовательской обратной связи
        application.add_handler(MessageHandler(filters.Regex("^🐛 Сообщить об ошибке$"), report_error_handler))
        application.add_handler(MessageHandler(filters.Regex("^💡 Предложить улучшение$"), suggest_improvement_handler))
        application.add_handler(MessageHandler(filters.Regex("^❌ Отмена$"), cancel_feedback_handler))
        
        # Callback handlers для управления тикетами
        application.add_handler(CallbackQueryHandler(handle_error_status_callback, pattern=r"^error_status_\d+_"))
        application.add_handler(CallbackQueryHandler(handle_suggestion_status_callback, pattern=r"^suggestion_status_\d+_"))
        application.add_handler(CallbackQueryHandler(handle_suggestion_priority_callback, pattern=r"^suggestion_priority_\d+_"))
        application.add_handler(CallbackQueryHandler(handle_show_full_error_callback, pattern=r"^error_full_\d+$"))
        application.add_handler(CallbackQueryHandler(handle_show_full_suggestion_callback, pattern=r"^suggestion_full_\d+$"))
        
        # Callback handlers для обратной связи по поиску
        application.add_handler(CallbackQueryHandler(handle_not_my_item_callback, pattern=r"^not_my_item_"))
        application.add_handler(CallbackQueryHandler(handle_add_comment_callback, pattern=r"^add_comment_"))
        application.add_handler(CallbackQueryHandler(handle_try_another_photo_callback, pattern=r"^try_another_photo$"))
        application.add_handler(CallbackQueryHandler(handle_contact_support_callback, pattern=r"^contact_support$"))
        
        # Команды для администраторов (обратная связь)
        application.add_handler(CommandHandler("feedback_stats", view_feedback_stats_handler))
        application.add_handler(CommandHandler("view_errors", view_errors_handler))
        application.add_handler(CommandHandler("view_suggestions", view_suggestions_handler))
        
        # Обработчик фотографий (используем toolbot.handlers.photo_handler)
        application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
        
        # Обработчики для мониторинга надежности
        application.add_handler(CommandHandler("error_stats", error_stats_handler))
        application.add_handler(CommandHandler("components_status", components_status_handler))
        application.add_handler(CommandHandler("test_recovery", test_recovery_handler))
        application.add_handler(CommandHandler("logs", logs_handler))
        
        # Обработчик текста (должен быть последним)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        logger.info("✅ Обработчики команд успешно зарегистрированы")
    except Exception as e:
        logger.error(f"❌ Ошибка при регистрации обработчиков: {e}")
        raise


# Функция проверки здоровья телеграм-бота
def check_bot_health():
    """Проверяет работоспособность бота"""
    try:
        # Базовые проверки
        if not os.path.exists("config.encrypted"):
            logger.warning("Файл конфигурации не найден")
            return False
        
        # Проверка подключения к Redis, если используется
        if os.environ.get("ENABLE_REDIS", "false").lower() == "true":
            try:
                import redis
                redis_host = os.environ.get("REDIS_HOST", "localhost") 
                redis_port = int(os.environ.get("REDIS_PORT", 6379))
                r = redis.Redis(host=redis_host, port=redis_port)
                r.ping()
                logger.debug("Соединение с Redis успешно")
            except Exception as e:
                logger.warning(f"Соединение с Redis недоступно: {e}")
        # Redis отключен - работаем без кеширования
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при проверке здоровья бота: {e}")
        return False


# Функция перезапуска телеграм-бота
def restart_bot():
    """Перезапускает телеграм-бота"""
    try:
        logger.info("Выполняется перезапуск телеграм-бота...")
        
        # Если выполняется в Docker, используем другую стратегию
        if os.environ.get("PRODUCTION") == "1":
            logger.info("Обнаружена среда Docker, отправляем сигнал для перезапуска контейнера")
            # В Docker контейнеры обычно перезапускаются автоматически при завершении процесса
            os.kill(os.getpid(), 15)  # SIGTERM
            return True
            
        # Для локального запуска
        return True
    except Exception as e:
        logger.error(f"Ошибка при перезапуске бота: {e}")
        return False


@error_handler(severity=ErrorSeverity.CRITICAL)
def main():
    """Основная функция для запуска бота"""
    try:
        # Пытаемся загрузить конфигурацию - сначала из модуля основного проекта, потом из toolbot
        local_config = None
        
        try:
            # Сначала пробуем загрузить из config.py в корне проекта
            sys.path.insert(0, os.getcwd())
            import config as config_module
            local_config = config_module.load_config()
            logger.info("✅ Конфигурация загружена из локального config.py")
        except (ImportError, AttributeError) as e:
            logger.warning(f"Локальный config.py не найден или некорректен: {e}")
            local_config = None
            
        # Если не удалось загрузить из корня, пробуем из модуля toolbot
        if not local_config:
            # Проверяем наличие шифрованного файла конфигурации,
            # но не останавливаем приложение, если его нет
            if not os.path.exists("config.encrypted"):
                logger.warning("❌ Зашифрованный файл 'config.encrypted' не найден.")
            else:
                # Пытаемся загрузить конфигурацию
                try:
                    config = load_config()
                    if not config:
                        logger.warning("❌ Не удалось загрузить конфигурацию из encrypted файла.")
                except Exception as e:
                    logger.warning(f"❌ Ошибка при загрузке зашифрованной конфигурации: {e}")
                    config = None
        else:
            config = local_config

        # Проверяем, есть ли у нас конфигурация
        if not config:
            logger.error("❌ Программа завершена из-за некорректной или отсутствующей конфигурации.")
            return

        # Получение токена из конфигурации
        token = config.get("telegram_token")
        if not token:
            logger.error("❌ Токен Telegram не найден в конфигурации.")
            return
            
        # Инициализация аналитики
        analytics = Analytics()
        logger.info("✅ Аналитика инициализирована")
        
        # Инициализация моделей для обнаружения объектов
        initialize_models()
        
        # Примечание: Используется UnifiedDatabaseService из handlers/photo_handler.py
        # Старый сервис improved_database_search больше не инициализируется
        logger.info("✅ Используется UnifiedDatabaseService для поиска по изображениям")
        
        # Создаем и настраиваем приложение
        application = Application.builder().token(config["telegram_token"]).build()
        
        # Создаем экземпляр совместимости TeleBot для интеграции с UI компонентами
        telebot_instance = create_telebot(application)
        
        # Сохраняем экземпляр в глобальной переменной для доступа из других модулей
        global _telebot_instance
        _telebot_instance = telebot_instance
        
        # Сохраняем аналитику в контексте бота
        application.bot_data['analytics'] = analytics
        
        # Регистрируем обработчики команд
        register_handlers(application)
        
        # Регистрируем UI обработчики, если модуль доступен
        try:
            from toolbot.handlers.ui_handlers import register_ui_handlers
            register_ui_handlers(telebot_instance)
            logger.info("✅ UI обработчики успешно зарегистрированы")
        except ImportError as e:
            logger.warning(f"Модуль UI обработчиков недоступен: {e}")
        
        # Регистрация компонента для мониторинга и восстановления
        recovery_manager = RecoveryManager.get_instance()
        register_component("telegram_bot", restart_bot, check_bot_health)
        
        # Проверяем запуск в Docker контейнере
        is_docker = os.path.exists("/.dockerenv") or os.environ.get("PRODUCTION") == "1"
        if is_docker:
            logger.info("🐳 Запуск в Docker контейнере")
        
        # Установка состояния компонента в "запускается"
        recovery_manager.set_component_state("telegram_bot", ComponentState.STARTING)
        
        # Запуск сторожевого таймера для мониторинга компонентов
        recovery_manager.start_watchdog(check_interval=60)
        
        # Запуск бота
        logger.info("🤖 Бот запущен...")
        
        # Установка состояния компонента в "работает"
        recovery_manager.set_component_state("telegram_bot", ComponentState.RUNNING)
        
        # Запуск приложения Telegram
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка при запуске бота: {e}")
        logger.critical(traceback.format_exc())
        
        # Устанавливаем состояние компонента в ошибку
        try:
            recovery_manager = RecoveryManager.get_instance()
            recovery_manager.set_component_state("telegram_bot", ComponentState.ERROR, 
                                               f"Критическая ошибка: {str(e)}")
        except:
            pass
        
        # Пробрасываем исключение дальше
        raise


# Глобальная переменная для хранения экземпляра telebot
_telebot_instance = None

def get_telebot_instance():
    """Получает экземпляр TeleBot для использования в UI компонентах"""
    global _telebot_instance
    return _telebot_instance


if __name__ == '__main__':
    try:
        logger.info("Запуск приложения...")
        main()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.critical(f"Необработанное исключение: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1) 