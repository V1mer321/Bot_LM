"""
Модуль для работы с конфигурацией.
"""
import os
import json
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Функция для загрузки конфигурации
def load_config():
    """
    Загружает конфигурацию из файла или переменных окружения.
    
    Returns:
        Словарь с конфигурацией
    """
    # В реальной системе здесь будет расшифровка конфигурации
    # Для тестирования используем тестовые данные
    config = {
        "telegram_token": "7128449925:AAGz7uzZJ37Iy0mXoSgrlrRKk7LFcv_Q7W8",  # Токен Telegram
        "allowed_users": [2093834331, 355246766],  # Список разрешенных пользователей
        "admin_users": [2093834331],  # Список администраторов (старый формат)
        "admin_ids": [2093834331],  # Список ID администраторов (для совместимости с toolbot.config)
        "admins": [2093834331],  # Еще один вариант ключа для админов (для совместимости)
        "whitelist": [2093834331, 355246766],  # Белый список пользователей (для совместимости)
        "storage_path": "toolbot/data/",  # Путь к хранилищу данных
        "models_path": "toolbot/models/",  # Путь к моделям
        "use_gpu": False,  # Использовать ли GPU
        "log_level": "INFO",  # Уровень логирования
        "photos_folder": "toolbot/data/photos"
    }
    logger.debug(f"Загружена конфигурация: admin_users={config['admin_users']}, admin_ids={config['admin_ids']}")
    return config

def is_allowed_user(user_id: int) -> bool:
    """
    Проверяет, разрешен ли пользователь.
    
    Args:
        user_id: Идентификатор пользователя
        
    Returns:
        True, если пользователь разрешен, иначе False
    """
    # ЗАКОММЕНТИРОВАНО: Проверка доступа отключена - все пользователи могут использовать бота
    # config = load_config()
    # allowed_users = config.get("allowed_users", [])
    # whitelist = config.get("whitelist", [])
    # admin_users = config.get("admin_users", [])
    # admin_ids = config.get("admin_ids", [])
    # admins = config.get("admins", [])
    
    # # Считаем, что при тестировании все пользователи разрешены
    # if not allowed_users and not whitelist:
    #     return True
    
    # # Проверяем все возможные списки
    # if (user_id in allowed_users or user_id in whitelist or 
    #     user_id in admin_users or user_id in admin_ids or 
    #     user_id in admins):
    #     return True
    
    # return False
    
    # Разрешаем доступ всем пользователям
    return True

def is_admin(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь администратором.
    
    Args:
        user_id: Идентификатор пользователя
        
    Returns:
        True, если пользователь администратор, иначе False
    """
    config = load_config()
    admin_users = config.get("admin_users", [])
    admin_ids = config.get("admin_ids", [])
    admins = config.get("admins", [])
    
    # Проверяем все возможные ключи для админов
    is_admin_result = user_id in admin_users or user_id in admin_ids or user_id in admins
    logger.debug(f"Проверка админ-доступа в config.py: user_id={user_id}, результат={is_admin_result}")
    
    return is_admin_result

# Создаем тестовый файл конфигурации
def create_test_config():
    """
    Создает тестовый файл конфигурации для локального тестирования.
    """
    with open("config.encrypted", "w", encoding="utf-8") as f:
        f.write("TEST CONFIG")
    
    print("Создан тестовый файл конфигурации config.encrypted")

# При импорте модуля создаем тестовую конфигурацию
if not os.path.exists("config.encrypted"):
    create_test_config() 