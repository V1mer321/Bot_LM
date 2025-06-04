#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для запуска телеграм-бота ToolBot
С поддержкой параметров командной строки и улучшенным логированием
"""

import os
import sys
import logging
import argparse
from pathlib import Path

def setup_logging(log_file="bot.log", console_level=logging.INFO, file_level=logging.DEBUG):
    """
    Настройка логирования с поддержкой уровней для консоли и файла
    
    Args:
        log_file: Путь к файлу журнала
        console_level: Уровень логирования для консоли
        file_level: Уровень логирования для файла
    """
    # Создаем папку для логов, если она не существует
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Настраиваем базовое логирование
    root_logger = logging.getLogger()
    root_logger.setLevel(min(console_level, file_level))  # Устанавливаем самый детальный уровень
    
    # Форматирование логов
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Вывод в файл
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)
    
    # Вывод в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    
    # Добавляем обработчики к корневому логгеру
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger


def main():
    # Разбор аргументов командной строки
    parser = argparse.ArgumentParser(description="Запуск телеграм-бота ToolBot")
    parser.add_argument(
        "--log", 
        type=str, 
        default="bot.log", 
        help="Путь к файлу журнала"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Включить режим отладки (подробное логирование)"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        help="Путь к файлу конфигурации (по умолчанию config.encrypted)"
    )
    parser.add_argument(
        "--key", 
        type=str, 
        help="Путь к файлу ключа шифрования (по умолчанию key.key)"
    )
    parser.add_argument(
        "--no-analytics", 
        action="store_true", 
        help="Отключить сбор аналитики"
    )
    
    args = parser.parse_args()
    
    # Настраиваем логирование на основе параметров
    console_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logging(args.log, console_level=console_level)
    
    # Устанавливаем переменные окружения для конфигурации
    # os.environ['CONFIG_PATH'] = 'config.py'  # Убираем принудительное использование config.py
    if args.config:
        os.environ['CONFIG_PATH'] = args.config
    if args.key:
        os.environ['KEY_PATH'] = args.key
    if args.no_analytics:
        os.environ['DISABLE_ANALYTICS'] = '1'
    
    # Импортируем после настройки окружения
    from toolbot.main import main as bot_main
    
    # Выводим информацию о запуске
    logger.info("==========================================")
    logger.info("Запуск бота ToolBot")
    if args.debug:
        logger.info("Режим отладки: ВКЛ")
    logger.info(f"Файл журнала: {args.log}")
    if args.config:
        logger.info(f"Файл конфигурации: {args.config}")
    if args.key:
        logger.info(f"Файл ключа: {args.key}")
    if args.no_analytics:
        logger.info("Аналитика: ОТКЛЮЧЕНА")
    logger.info("==========================================")
    
    try:
        bot_main()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        print(f"Произошла критическая ошибка: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 