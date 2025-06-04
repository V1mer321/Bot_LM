#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для улучшенной обработки исключений и ошибок в приложении.
Предоставляет механизмы для сбора, анализа и обработки различных типов ошибок.
"""

import sys
import logging
import traceback
import functools
import os
import datetime
import json
import inspect
from typing import Callable, Dict, Any, Optional, List, Type, Union
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Перечисление для уровней серьезности ошибок"""
    LOW = "LOW"           # Незначительные ошибки, не влияющие на работу приложения
    MEDIUM = "MEDIUM"     # Ошибки, которые могут повлиять на некоторые функции
    HIGH = "HIGH"         # Серьезные ошибки, нарушающие работу важных компонентов
    CRITICAL = "CRITICAL" # Критические ошибки, требующие немедленного вмешательства


class ErrorHandler:
    """
    Класс для централизованной обработки ошибок в приложении.
    Включает механизмы логирования, сохранения стека вызовов и отправки уведомлений.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """
        Получение экземпляра обработчика ошибок (шаблон Singleton).
        
        Returns:
            Экземпляр ErrorHandler
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Инициализация обработчика ошибок"""
        self.error_log_path = os.path.join("logs", "errors.log")
        self.error_stats_path = os.path.join("logs", "error_stats.json")
        self.error_handlers = {}  # Словарь обработчиков для разных типов исключений
        self.error_counts = {}    # Счетчик ошибок по типам
        self.total_errors = 0     # Общее количество ошибок
        
        # Создаем директорию для логов, если она не существует
        os.makedirs(os.path.dirname(self.error_log_path), exist_ok=True)
        
        # Загружаем статистику ошибок, если файл существует
        self._load_error_stats()
        
        # Устанавливаем глобальный обработчик необработанных исключений
        sys.excepthook = self.global_exception_handler
    
    def _load_error_stats(self):
        """Загружает статистику ошибок из файла"""
        try:
            if os.path.exists(self.error_stats_path):
                with open(self.error_stats_path, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                    self.error_counts = stats.get("error_counts", {})
                    self.total_errors = stats.get("total_errors", 0)
                    logger.info(f"Загружена статистика ошибок: {self.total_errors} всего ошибок")
        except Exception as e:
            logger.error(f"Ошибка при загрузке статистики ошибок: {e}")
    
    def _save_error_stats(self):
        """Сохраняет статистику ошибок в файл"""
        try:
            stats = {
                "error_counts": self.error_counts,
                "total_errors": self.total_errors,
                "last_updated": datetime.datetime.now().isoformat()
            }
            with open(self.error_stats_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении статистики ошибок: {e}")
    
    def register_handler(self, exception_type: Type[Exception], handler: Callable[[Exception], None]):
        """
        Регистрирует обработчик для указанного типа исключения.
        
        Args:
            exception_type: Тип исключения
            handler: Функция-обработчик, принимающая исключение
        """
        self.error_handlers[exception_type] = handler
        logger.debug(f"Зарегистрирован обработчик для {exception_type.__name__}")
    
    def handle_error(self, e: Exception, context: Dict[str, Any] = None, 
                     severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> bool:
        """
        Обрабатывает возникшее исключение.
        
        Args:
            e: Исключение для обработки
            context: Контекст выполнения, в котором произошла ошибка
            severity: Уровень серьезности ошибки
            
        Returns:
            True, если ошибка была успешно обработана, иначе False
        """
        error_type = type(e).__name__
        
        # Обновляем статистику ошибок
        self.total_errors += 1
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Формируем контекст, если он не был предоставлен
        if context is None:
            context = {}
        
        # Добавляем информацию о стеке вызовов
        tb = traceback.format_exc()
        
        # Базовое форматирование сообщения об ошибке
        error_message = f"[{severity.value}] {error_type}: {str(e)}"
        
        # Дополнительная информация из контекста
        context_info = "\n".join([f"{k}: {v}" for k, v in context.items()])
        
        # Полное сообщение для логирования
        full_message = f"""
{'-' * 50}
Время: {datetime.datetime.now().isoformat()}
{error_message}
{'-' * 50}
Контекст:
{context_info}
{'-' * 50}
Стек вызовов:
{tb}
{'-' * 50}
"""
        
        # Логируем ошибку
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(error_message, exc_info=True)
        elif severity == ErrorSeverity.HIGH:
            logger.error(error_message, exc_info=True)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(error_message, exc_info=True)
        else:
            logger.info(error_message)
        
        # Записываем полную информацию в файл журнала ошибок
        try:
            with open(self.error_log_path, 'a', encoding='utf-8') as f:
                f.write(full_message)
        except Exception as log_error:
            logger.error(f"Не удалось записать ошибку в журнал: {log_error}")
        
        # Вызываем специальный обработчик для данного типа исключения, если он есть
        for exc_type, handler in self.error_handlers.items():
            if isinstance(e, exc_type):
                try:
                    handler(e)
                except Exception as handler_error:
                    logger.error(f"Ошибка в обработчике исключений: {handler_error}")
        
        # Сохраняем статистику
        self._save_error_stats()
        
        return True
    
    def global_exception_handler(self, exc_type, exc_value, exc_traceback):
        """
        Глобальный обработчик необработанных исключений.
        
        Args:
            exc_type: Тип исключения
            exc_value: Значение исключения
            exc_traceback: Трассировка исключения
        """
        if issubclass(exc_type, KeyboardInterrupt):
            # Стандартная обработка для прерывания с клавиатуры
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical("Необработанное исключение", exc_info=(exc_type, exc_value, exc_traceback))
        
        # Получаем контекст
        frame = None
        try:
            frame = inspect.trace()[-1][0]
            context = {
                "function": frame.f_code.co_name,
                "module": frame.f_globals.get('__name__', 'unknown'),
                "file": frame.f_code.co_filename
            }
        except Exception:
            context = {}
        finally:
            if frame:
                del frame  # Избегаем циклических ссылок
        
        # Обрабатываем ошибку
        self.handle_error(exc_value, context, ErrorSeverity.CRITICAL)
    
    def get_error_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику ошибок.
        
        Returns:
            Словарь со статистикой ошибок
        """
        return {
            "total_errors": self.total_errors,
            "error_counts": self.error_counts,
            "last_updated": datetime.datetime.now().isoformat()
        }
    
    def clear_error_stats(self):
        """Очищает статистику ошибок"""
        self.error_counts = {}
        self.total_errors = 0
        self._save_error_stats()
        logger.info("Статистика ошибок очищена")


def error_handler(severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """
    Декоратор для обработки исключений в функциях.
    
    Args:
        severity: Уровень серьезности ошибки
        
    Returns:
        Декорированная функция
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = ErrorHandler.get_instance()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    "function": func.__name__,
                    "module": func.__module__,
                    "args": str(args),
                    "kwargs": str(kwargs)
                }
                handler.handle_error(e, context, severity)
                # Пробрасываем исключение дальше
                raise
        return wrapper
    return decorator


def async_error_handler(severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """
    Декоратор для обработки исключений в асинхронных функциях.
    
    Args:
        severity: Уровень серьезности ошибки
        
    Returns:
        Декорированная асинхронная функция
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            handler = ErrorHandler.get_instance()
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = {
                    "function": func.__name__,
                    "module": func.__module__,
                    "args": str(args),
                    "kwargs": str(kwargs)
                }
                handler.handle_error(e, context, severity)
                # Пробрасываем исключение дальше
                raise
        return wrapper
    return decorator


# Удобные функции для обработки ошибок разного уровня серьезности
def handle_low_error(e: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
    """Обрабатывает незначительную ошибку"""
    return ErrorHandler.get_instance().handle_error(e, context, ErrorSeverity.LOW)


def handle_medium_error(e: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
    """Обрабатывает ошибку среднего уровня серьезности"""
    return ErrorHandler.get_instance().handle_error(e, context, ErrorSeverity.MEDIUM)


def handle_high_error(e: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
    """Обрабатывает серьезную ошибку"""
    return ErrorHandler.get_instance().handle_error(e, context, ErrorSeverity.HIGH)


def handle_critical_error(e: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
    """Обрабатывает критическую ошибку"""
    return ErrorHandler.get_instance().handle_error(e, context, ErrorSeverity.CRITICAL)


# Инициализируем обработчик ошибок при импорте модуля
error_handler_instance = ErrorHandler.get_instance() 