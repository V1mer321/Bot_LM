#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для расширенного логирования в приложении.
Предоставляет настраиваемые форматы логов, обработчики для различных потоков вывода,
сохранение логов в разных форматах и ротацию файлов логов.
"""

import os
import sys
import json
import time
import logging
import logging.handlers
import traceback
import datetime
import atexit
import socket
import threading
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Tuple

# Проверяем наличие colorama для цветного вывода в консоль
try:
    from colorama import init, Fore, Style
    init()  # Инициализация colorama
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False


class LogLevel(Enum):
    """Перечисление для уровней логирования"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LogFormat(Enum):
    """Перечисление для форматов логирования"""
    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"


class LoggingManager:
    """
    Менеджер логирования, предоставляющий расширенные возможности логирования.
    Поддерживает различные форматы, уровни и точки вывода логов.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """
        Получение экземпляра менеджера логирования (шаблон Singleton).
        
        Returns:
            Экземпляр LoggingManager
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Инициализация менеджера логирования"""
        self.base_logger = logging.getLogger()
        
        # Настройки по умолчанию
        self.log_dir = "logs"
        self.log_file = os.path.join(self.log_dir, "toolbot.log")
        self.error_log_file = os.path.join(self.log_dir, "errors.log")
        self.json_log_file = os.path.join(self.log_dir, "toolbot_json.log")
        self.max_size = 10 * 1024 * 1024  # 10 МБ
        self.backup_count = 5
        self.console_format = LogFormat.SIMPLE
        self.file_format = LogFormat.DETAILED
        self.console_level = LogLevel.INFO
        self.file_level = LogLevel.DEBUG
        
        # Инициализируем форматтеры
        self.formatters = self._create_formatters()
        
        # Список обработчиков логов
        self.handlers = {}
        
        # Создаем директорию для логов, если она не существует
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Добавляем обработчик для очистки при завершении
        atexit.register(self.shutdown)
        
        # Метаданные для JSON-логов
        self.metadata = {
            "host": socket.gethostname(),
            "app_name": "toolbot",
            "start_time": datetime.datetime.now().isoformat()
        }
        
        # Идентификаторы потоков и их имена для контекстного логирования
        self.thread_context = {}
        
        # Создаем обработчики логов
        self._setup_handlers()
    
    def _create_formatters(self) -> Dict[str, logging.Formatter]:
        """
        Создает форматтеры для разных форматов логов.
        
        Returns:
            Словарь с форматтерами
        """
        formatters = {}
        
        # Простой формат для консоли
        simple_format = '%(levelname)s - %(message)s'
        formatters[LogFormat.SIMPLE.value] = logging.Formatter(simple_format)
        
        # Подробный формат для файла
        detailed_format = ('%(asctime)s - %(name)s - %(levelname)s - '
                         '%(filename)s:%(lineno)d - %(funcName)s - %(message)s')
        formatters[LogFormat.DETAILED.value] = logging.Formatter(detailed_format)
        
        # JSON формат
        formatters[LogFormat.JSON.value] = self.JsonFormatter()
        
        return formatters
    
    def _setup_handlers(self):
        """Настраивает обработчики логов для разных выходных потоков."""
        # Консольный обработчик
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.console_level.value)
        console_handler.setFormatter(self.formatters[self.console_format.value])
        if COLORAMA_AVAILABLE:
            console_handler = self.ColoredHandler(console_handler)
        self.handlers['console'] = console_handler
        
        # Основной файловый обработчик с ротацией
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=self.max_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.file_level.value)
        file_handler.setFormatter(self.formatters[self.file_format.value])
        self.handlers['file'] = file_handler
        
        # Обработчик только для ошибок
        error_handler = logging.handlers.RotatingFileHandler(
            self.error_log_file,
            maxBytes=self.max_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(LogLevel.ERROR.value)
        error_handler.setFormatter(self.formatters[LogFormat.DETAILED.value])
        self.handlers['error'] = error_handler
        
        # JSON обработчик
        json_handler = logging.handlers.RotatingFileHandler(
            self.json_log_file,
            maxBytes=self.max_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        json_handler.setLevel(self.file_level.value)
        json_handler.setFormatter(self.formatters[LogFormat.JSON.value])
        self.handlers['json'] = json_handler
        
        # Добавляем обработчики к корневому логгеру
        for handler in self.handlers.values():
            self.base_logger.addHandler(handler)
        
        # Устанавливаем базовый уровень логирования
        min_level = min(self.console_level.value, self.file_level.value)
        self.base_logger.setLevel(min_level)
    
    def configure(self, console_level: Optional[LogLevel] = None, 
                file_level: Optional[LogLevel] = None,
                console_format: Optional[LogFormat] = None,
                file_format: Optional[LogFormat] = None,
                log_dir: Optional[str] = None):
        """
        Настраивает менеджер логирования.
        
        Args:
            console_level: Уровень логирования для консоли
            file_level: Уровень логирования для файла
            console_format: Формат логов для консоли
            file_format: Формат логов для файла
            log_dir: Директория для файлов логов
        """
        changes = False
        
        # Обновляем директорию для логов, если указана
        if log_dir:
            self.log_dir = log_dir
            self.log_file = os.path.join(self.log_dir, "toolbot.log")
            self.error_log_file = os.path.join(self.log_dir, "errors.log")
            self.json_log_file = os.path.join(self.log_dir, "toolbot_json.log")
            os.makedirs(self.log_dir, exist_ok=True)
            changes = True
        
        # Обновляем уровни логирования, если указаны
        if console_level:
            self.console_level = console_level
            if 'console' in self.handlers:
                self.handlers['console'].setLevel(console_level.value)
            changes = True
        
        if file_level:
            self.file_level = file_level
            if 'file' in self.handlers:
                self.handlers['file'].setLevel(file_level.value)
            if 'json' in self.handlers:
                self.handlers['json'].setLevel(file_level.value)
            changes = True
        
        # Обновляем форматы логов, если указаны
        if console_format:
            self.console_format = console_format
            if 'console' in self.handlers:
                self.handlers['console'].setFormatter(self.formatters[console_format.value])
            changes = True
        
        if file_format:
            self.file_format = file_format
            if 'file' in self.handlers:
                self.handlers['file'].setFormatter(self.formatters[file_format.value])
            changes = True
        
        # Если были изменения, перенастраиваем логгер
        if changes:
            # Устанавливаем минимальный уровень логирования
            min_level = min(self.console_level.value, self.file_level.value)
            self.base_logger.setLevel(min_level)
            
            self.base_logger.info("Настройки логирования обновлены")
    
    def add_context(self, key: str, value: Any):
        """
        Добавляет контекстную информацию для текущего потока.
        
        Args:
            key: Ключ для контекстной информации
            value: Значение контекстной информации
        """
        thread_id = threading.get_ident()
        if thread_id not in self.thread_context:
            self.thread_context[thread_id] = {}
        self.thread_context[thread_id][key] = value
    
    def get_context(self) -> Dict[str, Any]:
        """
        Возвращает контекстную информацию для текущего потока.
        
        Returns:
            Словарь с контекстной информацией
        """
        thread_id = threading.get_ident()
        return self.thread_context.get(thread_id, {})
    
    def clear_context(self):
        """Очищает контекстную информацию для текущего потока."""
        thread_id = threading.get_ident()
        if thread_id in self.thread_context:
            del self.thread_context[thread_id]
    
    def log_exception(self, exc_info=None, extra: Optional[Dict[str, Any]] = None, 
                    level: LogLevel = LogLevel.ERROR):
        """
        Логирует исключение с подробным контекстом.
        
        Args:
            exc_info: Информация об исключении (по умолчанию текущее)
            extra: Дополнительная информация для логирования
            level: Уровень логирования
        """
        if exc_info is None:
            exc_info = sys.exc_info()
        
        # Получаем трассировку и форматируем её
        if exc_info[0] is not None:
            exc_type, exc_value, exc_traceback = exc_info
            tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            tb_text = ''.join(tb_lines)
            
            # Формируем сообщение
            message = f"Исключение: {exc_type.__name__}: {exc_value}\n{tb_text}"
            
            # Добавляем контекстную информацию
            context = self.get_context()
            if context:
                context_text = "\nКонтекст:\n" + "\n".join([f"{k}: {v}" for k, v in context.items()])
                message += context_text
            
            # Добавляем дополнительную информацию
            if extra:
                extra_text = "\nДополнительно:\n" + "\n".join([f"{k}: {v}" for k, v in extra.items()])
                message += extra_text
            
            # Логируем сообщение
            self.base_logger.log(level.value, message)
    
    def set_thread_name(self, name: str):
        """
        Устанавливает имя для текущего потока.
        
        Args:
            name: Имя потока
        """
        thread = threading.current_thread()
        thread.name = name
        self.add_context("thread_name", name)
    
    def shutdown(self):
        """Корректно завершает работу всех обработчиков логов."""
        for handler in self.handlers.values():
            handler.close()
        
        # Очищаем контекстную информацию
        self.thread_context.clear()
        
        logging.shutdown()
    
    class JsonFormatter(logging.Formatter):
        """Форматтер для вывода логов в формате JSON."""
        
        def format(self, record):
            """
            Форматирует запись лога в JSON.
            
            Args:
                record: Запись лога
                
            Returns:
                Строка JSON с данными лога
            """
            manager = LoggingManager.get_instance()
            
            # Базовые поля
            log_data = {
                "timestamp": datetime.datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "thread": record.thread,
                "thread_name": record.threadName,
                "process": record.process
            }
            
            # Добавляем контекстную информацию
            thread_id = record.thread
            if thread_id in manager.thread_context:
                log_data["context"] = manager.thread_context[thread_id]
            
            # Добавляем метаданные
            log_data.update(manager.metadata)
            
            # Добавляем информацию об исключении, если есть
            if record.exc_info:
                exc_type, exc_value, exc_traceback = record.exc_info
                log_data["exception"] = {
                    "type": exc_type.__name__ if exc_type else "Unknown",
                    "message": str(exc_value) if exc_value else "Unknown",
                    "traceback": traceback.format_exception(exc_type, exc_value, exc_traceback) if exc_type else []
                }
            
            # Добавляем дополнительные поля из kwargs
            if hasattr(record, "extra") and record.extra:
                log_data.update(record.extra)
            
            return json.dumps(log_data, ensure_ascii=False)
    
    class ColoredHandler(logging.Handler):
        """Обработчик для цветного вывода логов в консоль."""
        
        def __init__(self, target_handler):
            """
            Инициализация цветного обработчика.
            
            Args:
                target_handler: Целевой обработчик для проксирования
            """
            super().__init__()
            self.target_handler = target_handler
            # Цветовые коды для разных уровней логирования
            self.colors = {
                logging.DEBUG: Fore.CYAN if COLORAMA_AVAILABLE else "",
                logging.INFO: Fore.GREEN if COLORAMA_AVAILABLE else "",
                logging.WARNING: Fore.YELLOW if COLORAMA_AVAILABLE else "",
                logging.ERROR: Fore.RED if COLORAMA_AVAILABLE else "",
                logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT if COLORAMA_AVAILABLE else ""
            }
        
        def emit(self, record):
            """
            Выводит запись лога с цветовым форматированием.
            
            Args:
                record: Запись лога
            """
            # Запоминаем исходный message
            orig_msg = record.msg
            
            # Добавляем цветовое форматирование, если colorama доступна
            if COLORAMA_AVAILABLE:
                color = self.colors.get(record.levelno, "")
                reset = Style.RESET_ALL
                record.msg = f"{color}{record.msg}{reset}"
            
            # Передаем запись целевому обработчику
            self.target_handler.emit(record)
            
            # Восстанавливаем исходный message
            record.msg = orig_msg
        
        def setFormatter(self, formatter):
            """
            Устанавливает форматтер для целевого обработчика.
            
            Args:
                formatter: Форматтер для установки
            """
            self.target_handler.setFormatter(formatter)
        
        def setLevel(self, level):
            """
            Устанавливает уровень логирования для целевого обработчика.
            
            Args:
                level: Уровень логирования
            """
            self.target_handler.setLevel(level)
            super().setLevel(level)
        
        def close(self):
            """Закрывает целевой обработчик."""
            self.target_handler.close()
            super().close()


def setup_logging(console_level: LogLevel = LogLevel.INFO, 
                 file_level: LogLevel = LogLevel.DEBUG,
                 console_format: LogFormat = LogFormat.SIMPLE,
                 file_format: LogFormat = LogFormat.DETAILED,
                 log_dir: str = "logs"):
    """
    Настраивает систему логирования.
    
    Args:
        console_level: Уровень логирования для консоли
        file_level: Уровень логирования для файла
        console_format: Формат логов для консоли
        file_format: Формат логов для файла
        log_dir: Директория для файлов логов
    """
    manager = LoggingManager.get_instance()
    manager.configure(
        console_level=console_level,
        file_level=file_level,
        console_format=console_format,
        file_format=file_format,
        log_dir=log_dir
    )
    return manager


def get_logger(name: str = None):
    """
    Получает логгер с указанным именем.
    
    Args:
        name: Имя логгера (если None, используется имя модуля вызывающего)
        
    Returns:
        Настроенный логгер
    """
    # Если имя не указано, пытаемся получить имя модуля вызывающего
    if name is None:
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'root')
    
    # Получаем логгер
    logger = logging.getLogger(name)
    
    # Устанавливаем уровень логирования в соответствии с менеджером
    manager = LoggingManager.get_instance()
    min_level = min(manager.console_level.value, manager.file_level.value)
    logger.setLevel(min_level)
    
    return logger


def log_exception(exc_info=None, extra=None, level=LogLevel.ERROR):
    """
    Логирует исключение с подробным контекстом.
    
    Args:
        exc_info: Информация об исключении (по умолчанию текущее)
        extra: Дополнительная информация для логирования
        level: Уровень логирования
    """
    LoggingManager.get_instance().log_exception(exc_info, extra, level)


def add_context(key: str, value: Any):
    """
    Добавляет контекстную информацию для текущего потока.
    
    Args:
        key: Ключ для контекстной информации
        value: Значение контекстной информации
    """
    LoggingManager.get_instance().add_context(key, value)


def clear_context():
    """Очищает контекстную информацию для текущего потока."""
    LoggingManager.get_instance().clear_context()


def set_thread_name(name: str):
    """
    Устанавливает имя для текущего потока.
    
    Args:
        name: Имя потока
    """
    LoggingManager.get_instance().set_thread_name(name)


# Инициализируем менеджер логирования при импорте модуля
logging_manager = LoggingManager.get_instance() 