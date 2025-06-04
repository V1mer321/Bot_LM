"""
Модуль для ограничения частоты запросов к боту.
"""
import time
import threading
import logging
from typing import Dict, Optional, Tuple
from collections import deque

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Класс для ограничения частоты запросов к боту.
    Реализует алгоритм скользящего окна.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """
        Получение экземпляра лимитера (шаблон Singleton).
        
        Returns:
            Экземпляр RateLimiter
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """
        Инициализация ограничителя частоты запросов.
        """
        self.user_requests = {}  # user_id -> deque[timestamp]
        self.photo_requests = {}  # user_id -> timestamp
        
        # Значения по умолчанию
        self.default_limit = 30  # Максимальное количество запросов
        self.default_window = 60  # Окно в секундах (1 минута)
        self.photo_cooldown = 10  # Кулдаун между запросами фото (секунды)
    
    def check_and_add(self, user_id: int, action_type: str = "general") -> Tuple[bool, Optional[float]]:
        """
        Проверяет, не превышен ли лимит запросов и добавляет запрос в историю.
        
        Args:
            user_id: ID пользователя
            action_type: Тип действия ('general', 'photo', 'admin', etc.)
            
        Returns:
            Кортеж (можно_выполнить, время_до_следующего_запроса)
        """
        current_time = time.time()
        
        # Для запросов фото используем отдельный кулдаун
        if action_type == "photo":
            with self._lock:
                last_request = self.photo_requests.get(user_id, 0)
                time_since_last = current_time - last_request
                
                if time_since_last < self.photo_cooldown:
                    remaining = self.photo_cooldown - time_since_last
                    return False, remaining
                
                # Обновляем время последнего запроса
                self.photo_requests[user_id] = current_time
                return True, None
        
        # Для административных действий нет ограничений
        if action_type == "admin":
            return True, None
        
        # Для обычных запросов используем алгоритм скользящего окна
        with self._lock:
            if user_id not in self.user_requests:
                self.user_requests[user_id] = deque()
            
            # Очистка устаревших запросов
            window_start = current_time - self.default_window
            while self.user_requests[user_id] and self.user_requests[user_id][0] < window_start:
                self.user_requests[user_id].popleft()
            
            # Проверка количества запросов в окне
            if len(self.user_requests[user_id]) >= self.default_limit:
                oldest = self.user_requests[user_id][0]
                time_until_available = (oldest + self.default_window) - current_time
                return False, time_until_available
            
            # Добавляем новый запрос
            self.user_requests[user_id].append(current_time)
            return True, None
    
    def set_limits(self, general_limit: int = None, general_window: int = None, photo_cooldown: int = None):
        """
        Устанавливает лимиты для различных типов запросов.
        
        Args:
            general_limit: Общий лимит запросов в окне
            general_window: Размер окна в секундах
            photo_cooldown: Кулдаун между запросами фото
        """
        with self._lock:
            if general_limit is not None:
                self.default_limit = max(1, general_limit)
            
            if general_window is not None:
                self.default_window = max(1, general_window)
            
            if photo_cooldown is not None:
                self.photo_cooldown = max(1, photo_cooldown)
            
            logger.info(f"Установлены новые лимиты: запросов={self.default_limit}, "
                       f"окно={self.default_window}с, фото={self.photo_cooldown}с")
    
    def reset_for_user(self, user_id: int):
        """
        Сбрасывает счетчики запросов для конкретного пользователя.
        
        Args:
            user_id: ID пользователя
        """
        with self._lock:
            if user_id in self.user_requests:
                del self.user_requests[user_id]
            
            if user_id in self.photo_requests:
                del self.photo_requests[user_id]


# Глобальные функции для использования ограничителя

def check_rate_limit(user_id: int, action_type: str = "general") -> Tuple[bool, Optional[float]]:
    """
    Проверяет, не превышен ли лимит запросов для пользователя.
    
    Args:
        user_id: ID пользователя
        action_type: Тип действия
        
    Returns:
        Кортеж (можно_выполнить, время_до_следующего_запроса)
    """
    limiter = RateLimiter.get_instance()
    return limiter.check_and_add(user_id, action_type)


def set_rate_limits(general_limit: int = None, general_window: int = None, photo_cooldown: int = None):
    """
    Устанавливает лимиты для различных типов запросов.
    
    Args:
        general_limit: Общий лимит запросов в окне
        general_window: Размер окна в секундах
        photo_cooldown: Кулдаун между запросами фото
    """
    limiter = RateLimiter.get_instance()
    limiter.set_limits(general_limit, general_window, photo_cooldown)


def reset_rate_limits_for_user(user_id: int):
    """
    Сбрасывает счетчики запросов для конкретного пользователя.
    
    Args:
        user_id: ID пользователя
    """
    limiter = RateLimiter.get_instance()
    limiter.reset_for_user(user_id) 