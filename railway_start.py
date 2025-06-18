#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Специальный скрипт запуска для Railway
Упрощенная версия без GPU проверок и тяжелых зависимостей
"""

import os
import sys
import logging
from pathlib import Path

def setup_railway_logging():
    """Настройка логирования для Railway"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)  # Только консоль для Railway
        ]
    )
    return logging.getLogger(__name__)

def check_environment():
    """Проверка переменных окружения"""
    required_vars = ['BOT_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Отсутствуют переменные окружения: {', '.join(missing_vars)}")

def main():
    """Главная функция запуска для Railway"""
    logger = setup_railway_logging()
    
    logger.info("🚀 Запуск бота на Railway...")
    logger.info(f"Python версия: {sys.version}")
    logger.info(f"Рабочая директория: {os.getcwd()}")
    
    try:
        # Проверяем переменные окружения
        check_environment()
        logger.info("✅ Переменные окружения проверены")
        
        # Устанавливаем пути для Railway
        os.environ['PYTHONPATH'] = '/app'
        os.environ['CONFIG_PATH'] = 'toolbot/config.py'  # Используем Python конфиг
        
        # Отключаем тяжелые функции для Railway
        os.environ['DISABLE_GPU'] = '1'
        os.environ['DISABLE_HEAVY_ML'] = '1'
        os.environ['USE_SIMPLE_SEARCH'] = '1'
        
        # Импортируем и запускаем бота
        from toolbot.main import main as bot_main
        
        logger.info("🤖 Инициализация бота...")
        bot_main()
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 