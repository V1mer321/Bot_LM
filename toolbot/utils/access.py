"""
Модуль для проверки доступа пользователя (whitelist/admin) с поддержкой разных форматов конфигурации.
"""
import logging

logger = logging.getLogger(__name__)

def is_allowed_user(user_id: int) -> bool:
    """
    Проверяет, разрешен ли пользователь (работает с config.py и toolbot.config).
    Args:
        user_id: ID пользователя
    Returns:
        True если пользователь разрешен, иначе False
    """
    # ЗАКОММЕНТИРОВАНО: Проверка доступа отключена - все пользователи могут использовать бота
    # try:
    #     import config as local_config_module
    #     local_config = local_config_module.load_config()
    #     allowed_users = local_config.get("allowed_users", [])
    #     admin_users = local_config.get("admin_users", [])
    #     admin_ids = local_config.get("admin_ids", [])
    #     logger.debug(f"Проверка доступа для пользователя {user_id}: allowed_users={allowed_users}, admin_users={admin_users}, admin_ids={admin_ids}")
    #     if user_id in allowed_users or user_id in admin_users or user_id in admin_ids:
    #         return True
    # except Exception as e:
    #     logger.error(f"Ошибка при проверке локальной конфигурации: {e}")
    #     pass
    # 
    # try:
    #     from toolbot.config import is_allowed_user as toolbot_is_allowed_user
    #     result = toolbot_is_allowed_user(user_id)
    #     logger.debug(f"Результат проверки доступа в toolbot.config: {result}")
    #     return result
    # except Exception as e:
    #     logger.error(f"Ошибка при проверке toolbot.config: {e}")
    #     return False
    
    # Разрешаем доступ всем пользователям
    logger.debug(f"Доступ для пользователя {user_id} разрешен (проверки отключены)")
    return True

def is_admin(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь администратором (работает с config.py и toolbot.config).
    Args:
        user_id: ID пользователя
    Returns:
        True если пользователь администратор, иначе False
    """
    try:
        import config as local_config_module
        local_config = local_config_module.load_config()
        admin_users = local_config.get("admin_users", [])
        admin_ids = local_config.get("admin_ids", [])
        logger.debug(f"Проверка админ-доступа для пользователя {user_id}: admin_users={admin_users}, admin_ids={admin_ids}")
        if user_id in admin_users or user_id in admin_ids:
            return True
    except Exception as e:
        logger.error(f"Ошибка при проверке локальной конфигурации (админ): {e}")
        pass
    
    try:
        from toolbot.config import is_admin as toolbot_is_admin
        result = toolbot_is_admin(user_id)
        logger.debug(f"Результат проверки админ-доступа в toolbot.config: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при проверке toolbot.config (админ): {e}")
        return False 