"""
Модуль для работы с конфигурацией бота.
Обеспечивает загрузку и шифрование конфигурационных данных.
"""
import json
import logging
import os
import threading
from typing import Dict, List, Any, Optional, Tuple
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла если он существует
load_dotenv()

# Настройка логирования
logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Менеджер конфигурации для работы с настройками бота.
    Поддерживает шифрование, кэширование и переменные окружения.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    # Значения параметров по умолчанию
    DEFAULT_SIMILARITY_THRESHOLD = 0.25
    DEFAULT_TOP_N_RESULTS = 5
    DEFAULT_CONTRAST_WEIGHT = 0.8
    DEFAULT_SHARPNESS_WEIGHT = 0.8
    DEFAULT_BRIGHTNESS_WEIGHT = 0.7
    DEFAULT_BRAND_BONUS = 2.0
    DEFAULT_TYPE_BONUS = 1.5
    DEFAULT_BRAND_TYPE_BONUS = 2.5
    
    @classmethod
    def get_instance(cls):
        """
        Получение экземпляра менеджера конфигурации (шаблон Singleton).
        
        Returns:
            Экземпляр ConfigManager
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """
        Инициализация менеджера конфигурации.
        """
        self.config = None
        self.config_path = os.environ.get('CONFIG_PATH', 'config.encrypted')
        self.key_path = os.environ.get('KEY_PATH', 'key.key')
        self.fernet = None
        self.load_key()
    
    def load_key(self) -> bool:
        """
        Загрузка ключа шифрования
        
        Returns:
            True если ключ успешно загружен, иначе False
        """
        try:
            # Проверяем наличие ключа в переменных окружения
            env_key = os.environ.get('ENCRYPTION_KEY')
            if env_key:
                key = env_key.encode()
                self.fernet = Fernet(key)
                logger.info("Ключ шифрования загружен из переменных окружения")
                return True
                
            # Если нет в переменных окружения, пытаемся загрузить из файла
            if os.path.exists(self.key_path):
                with open(self.key_path, "rb") as key_file:
                    key = key_file.read()
                self.fernet = Fernet(key)
                logger.info("Ключ шифрования загружен из файла")
                return True
            else:
                logger.error(f"Файл ключа шифрования не найден: {self.key_path}")
                return False
        except Exception as e:
            logger.error(f"Ошибка при загрузке ключа шифрования: {e}")
            return False
    
    def generate_key(self) -> Optional[bytes]:
        """
        Генерация нового ключа шифрования
        
        Returns:
            Ключ шифрования или None в случае ошибки
        """
        try:
            key = Fernet.generate_key()
            # Сохраняем ключ в файл
            with open(self.key_path, "wb") as key_file:
                key_file.write(key)
            
            self.fernet = Fernet(key)
            logger.info("Новый ключ шифрования сгенерирован и сохранен")
            return key
        except Exception as e:
            logger.error(f"Ошибка при генерации ключа шифрования: {e}")
            return None
    
    def encrypt_config(self, config_data: Dict) -> bool:
        """
        Шифрование и сохранение конфигурации
        
        Args:
            config_data: Данные конфигурации для шифрования
            
        Returns:
            True если конфигурация успешно зашифрована, иначе False
        """
        if not self.fernet:
            logger.error("Невозможно зашифровать конфигурацию: отсутствует ключ")
            return False
            
        try:
            encrypted_data = self.fernet.encrypt(json.dumps(config_data).encode())
            
            with open(self.config_path, "wb") as config_file:
                config_file.write(encrypted_data)
                
            # Обновляем кэш
            self.config = config_data
                
            logger.info("Конфигурация успешно зашифрована и сохранена")
            return True
        except Exception as e:
            logger.error(f"Ошибка при шифровании конфигурации: {e}")
            return False
    
    def load_config(self, force_reload: bool = False) -> Optional[Dict]:
        """
        Загружает конфигурацию из зашифрованного файла или переменных окружения
        
        Args:
            force_reload: Принудительная перезагрузка конфигурации из файла
            
        Returns:
            Данные конфигурации или None в случае ошибки
        """
        # Если конфигурация уже загружена и не требуется перезагрузка
        if self.config is not None and not force_reload:
            return self.config
            
        try:
            # Если нет ключа шифрования
            if not self.fernet:
                if not self.load_key():
                    logger.error("Не удалось загрузить ключ шифрования")
                    return None
            
            # Проверяем наличие файла конфигурации
            if not os.path.exists(self.config_path):
                logger.error(f"Файл конфигурации не найден: {self.config_path}")
                return None
                
            # Читаем зашифрованные данные
            with open(self.config_path, "rb") as config_file:
                encrypted_data = config_file.read()

            # Расшифровываем данные
            decrypted_data = self.fernet.decrypt(encrypted_data)
            config = json.loads(decrypted_data.decode())
            
            # Добавляем приоритетные значения из переменных окружения
            config = self._override_from_env(config)

            logger.info("✅ Конфигурация успешно загружена")
            
            # Сохраняем в кэш
            self.config = config
            
            return config
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке конфигурации: {e}")
            return None
    
    def _override_from_env(self, config: Dict) -> Dict:
        """
        Переопределяет значения конфигурации из переменных окружения
        
        Args:
            config: Текущая конфигурация
            
        Returns:
            Обновленная конфигурация
        """
        # Список переменных окружения для проверки
        env_vars = {
            'TELEGRAM_TOKEN': 'telegram_token',
            'PHOTOS_FOLDER': 'photos_folder',
            'ADMIN_IDS': 'admin_ids',
            'SIMILARITY_THRESHOLD': 'similarity_threshold',
            'TOP_N_RESULTS': 'top_n_results',
            'CONTRAST_WEIGHT': 'contrast_weight',
            'SHARPNESS_WEIGHT': 'sharpness_weight',
            'BRIGHTNESS_WEIGHT': 'brightness_weight',
            'BRAND_BONUS': 'brand_bonus',
            'TYPE_BONUS': 'type_bonus',
            'BRAND_TYPE_BONUS': 'brand_type_bonus'
        }
        
        # Проверяем и обновляем значения из переменных окружения
        for env_name, config_name in env_vars.items():
            env_value = os.environ.get(env_name)
            if env_value:
                # Для списков (как admin_ids)
                if config_name == 'admin_ids' and env_value:
                    try:
                        admin_ids = [int(x.strip()) for x in env_value.split(',')]
                        config[config_name] = admin_ids
                    except:
                        logger.warning(f"Не удалось преобразовать {env_name} в список")
                # Для числовых значений
                elif config_name in ['similarity_threshold', 'top_n_results', 
                                     'contrast_weight', 'sharpness_weight', 
                                     'brightness_weight', 'brand_bonus', 
                                     'type_bonus', 'brand_type_bonus'] and env_value:
                    try:
                        if config_name == 'top_n_results':
                            config[config_name] = int(env_value)
                        else:
                            config[config_name] = float(env_value)
                    except:
                        logger.warning(f"Не удалось преобразовать {env_name} в число")
                # Для строк
                else:
                    config[config_name] = env_value
                    
                logger.info(f"Значение {config_name} загружено из переменной окружения")
        
        return config
    
    def is_allowed_user(self, user_id: int) -> bool:
        """
        Проверяет, есть ли пользователь в белом списке
        
        Args:
            user_id: ID пользователя для проверки
            
        Returns:
            True если пользователь разрешен, иначе False
        """
        # ЗАКОММЕНТИРОВАНО: Проверка доступа отключена - все пользователи могут использовать бота
        # config = self.load_config()
        # if not config:
        #     return False
        #     
        # whitelist = config.get('whitelist', [])
        # 
        # # Проверяем также, является ли пользователь администратором
        # admin_ids = config.get('admin_ids', [])
        # 
        # return user_id in whitelist or user_id in admin_ids
        
        # Разрешаем доступ всем пользователям
        return True
    
    def is_admin(self, user_id: int) -> bool:
        """
        Проверяет, является ли пользователь администратором
        
        Args:
            user_id: ID пользователя для проверки
            
        Returns:
            True если пользователь админ, иначе False
        """
        config = self.load_config()
        if not config:
            return False
            
        # Проверяем все возможные ключи для администраторов
        admin_ids = config.get('admin_ids', [])
        admin_users = config.get('admin_users', [])
        admins = config.get('admins', [])
        
        # Объединяем все списки для проверки
        all_admins = set(admin_ids + admin_users + admins)
        
        # Логируем результат проверки (в режиме отладки)
        logger.debug(f"Проверка админ-доступа в ConfigManager: user_id={user_id}, admin_ids={admin_ids}, admin_users={admin_users}, admins={admins}")
        
        return user_id in all_admins
    
    def add_user_to_whitelist(self, user_id: int) -> bool:
        """
        Добавляет пользователя в белый список
        
        Args:
            user_id: ID пользователя для добавления
            
        Returns:
            True если пользователь успешно добавлен, иначе False
        """
        config = self.load_config()
        if not config:
            return False
            
        whitelist = config.get('whitelist', [])
        if user_id in whitelist:
            logger.info(f"Пользователь {user_id} уже в белом списке")
            return True
            
        whitelist.append(user_id)
        config['whitelist'] = whitelist
        
        return self.encrypt_config(config)
    
    def remove_user_from_whitelist(self, user_id: int) -> bool:
        """
        Удаляет пользователя из белого списка
        
        Args:
            user_id: ID пользователя для удаления
            
        Returns:
            True если пользователь успешно удален, иначе False
        """
        config = self.load_config()
        if not config:
            return False
            
        whitelist = config.get('whitelist', [])
        if user_id not in whitelist:
            logger.info(f"Пользователь {user_id} не найден в белом списке")
            return True
            
        whitelist.remove(user_id)
        config['whitelist'] = whitelist
        
        return self.encrypt_config(config)
    
    def add_admin(self, user_id: int) -> bool:
        """
        Добавляет пользователя в список администраторов
        
        Args:
            user_id: ID пользователя для добавления в админы
            
        Returns:
            True если пользователь успешно добавлен в админы, иначе False
        """
        config = self.load_config()
        if not config:
            return False
            
        admins = config.get('admins', [])
        whitelist = config.get('whitelist', [])
        
        # Проверяем, не является ли уже администратором
        if user_id in admins:
            logger.info(f"Пользователь {user_id} уже является администратором")
            return True
        
        # Добавляем в список администраторов
        admins.append(user_id)
        config['admins'] = admins
        
        # Также добавляем в whitelist, если его там нет
        if user_id not in whitelist:
            whitelist.append(user_id)
            config['whitelist'] = whitelist
            logger.info(f"Пользователь {user_id} также добавлен в whitelist")
        
        return self.encrypt_config(config)
    
    def get_similarity_threshold(self) -> float:
        """
        Возвращает порог схожести для поиска изображений
        
        Returns:
            Порог схожести (от 0 до 1)
        """
        config = self.load_config()
        if not config:
            return self.DEFAULT_SIMILARITY_THRESHOLD
            
        return config.get('similarity_threshold', self.DEFAULT_SIMILARITY_THRESHOLD)
    
    def get_top_n_results(self) -> int:
        """
        Возвращает количество результатов для показа
        
        Returns:
            Количество результатов
        """
        config = self.load_config()
        if not config:
            return self.DEFAULT_TOP_N_RESULTS
            
        return config.get('top_n_results', self.DEFAULT_TOP_N_RESULTS)
    
    def get_image_variation_weights(self) -> Tuple[float, float, float]:
        """
        Возвращает веса для различных вариаций изображения при поиске
        
        Returns:
            Кортеж (вес_контраста, вес_резкости, вес_яркости)
        """
        config = self.load_config()
        if not config:
            return (
                self.DEFAULT_CONTRAST_WEIGHT,
                self.DEFAULT_SHARPNESS_WEIGHT,
                self.DEFAULT_BRIGHTNESS_WEIGHT
            )
            
        contrast_weight = config.get('contrast_weight', self.DEFAULT_CONTRAST_WEIGHT)
        sharpness_weight = config.get('sharpness_weight', self.DEFAULT_SHARPNESS_WEIGHT)
        brightness_weight = config.get('brightness_weight', self.DEFAULT_BRIGHTNESS_WEIGHT)
        
        return (contrast_weight, sharpness_weight, brightness_weight)
    
    def get_similarity_bonuses(self) -> Tuple[float, float, float]:
        """
        Возвращает бонусы для коррекции схожести при совпадении характеристик
        
        Returns:
            Кортеж (бонус_бренда, бонус_типа, бонус_бренда_и_типа)
        """
        config = self.load_config()
        if not config:
            return (
                self.DEFAULT_BRAND_BONUS,
                self.DEFAULT_TYPE_BONUS,
                self.DEFAULT_BRAND_TYPE_BONUS
            )
            
        brand_bonus = config.get('brand_bonus', self.DEFAULT_BRAND_BONUS)
        type_bonus = config.get('type_bonus', self.DEFAULT_TYPE_BONUS)
        brand_type_bonus = config.get('brand_type_bonus', self.DEFAULT_BRAND_TYPE_BONUS)
        
        return (brand_bonus, type_bonus, brand_type_bonus)


# Для обратной совместимости с существующим кодом
_config_manager = None


def _get_config_manager():
    """
    Получает экземпляр менеджера конфигурации
    
    Returns:
        Экземпляр ConfigManager
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager.get_instance()
    return _config_manager


def generate_and_save_key():
    """Генерация и сохранение ключа шифрования"""
    return _get_config_manager().generate_key()


def load_key():
    """Загрузка ключа шифрования"""
    return _get_config_manager().load_key()


def encrypt_config(config_data):
    """Шифрование и сохранение конфигурации"""
    return _get_config_manager().encrypt_config(config_data)


def load_config(encrypted_file=None):
    """Загружает конфигурацию из зашифрованного файла"""
    cm = _get_config_manager()
    if encrypted_file:
        cm.config_path = encrypted_file
    return cm.load_config()


def is_allowed_user(user_id):
    """Проверяет, есть ли пользователь в белом списке"""
    # ЗАКОММЕНТИРОВАНО: Проверка доступа отключена - все пользователи могут использовать бота
    # return _get_config_manager().is_allowed_user(user_id)
    
    # Разрешаем доступ всем пользователям
    return True


def is_admin(user_id):
    """Проверяет, является ли пользователь администратором"""
    return _get_config_manager().is_admin(user_id)


def add_user_to_whitelist(user_id):
    """Добавляет пользователя в белый список"""
    return _get_config_manager().add_user_to_whitelist(user_id)


def remove_user_from_whitelist(user_id):
    """Удаляет пользователя из белого списка"""
    return _get_config_manager().remove_user_from_whitelist(user_id)


def add_admin(user_id):
    """Добавляет пользователя в список администраторов"""
    return _get_config_manager().add_admin(user_id)


def get_similarity_threshold():
    """Возвращает порог схожести для поиска изображений"""
    return _get_config_manager().get_similarity_threshold()


def get_top_n_results():
    """Возвращает количество результатов для показа"""
    return _get_config_manager().get_top_n_results()


def get_image_variation_weights():
    """Возвращает веса для различных вариаций изображения"""
    return _get_config_manager().get_image_variation_weights()


def get_similarity_bonuses():
    """Возвращает бонусы для коррекции схожести"""
    return _get_config_manager().get_similarity_bonuses()


def get_admin_ids():
    """Возвращает список ID администраторов"""
    manager = _get_config_manager()
    config = manager.load_config()
    if config:
        return config.get('admins', [])
    return []