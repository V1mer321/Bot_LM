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


def check_gpu_status():
    """Проверяет и выводит информацию о GPU"""
    try:
        import torch
        
        print("=" * 60)
        print("🔍 ПРОВЕРКА GPU СТАТУСА")
        print("=" * 60)
        
        print(f"📦 PyTorch версия: {torch.__version__}")
        
        cuda_available = torch.cuda.is_available()
        print(f"⚡ CUDA доступен: {'✅ ДА' if cuda_available else '❌ НЕТ'}")
        
        if cuda_available:
            gpu_count = torch.cuda.device_count()
            print(f"🎮 Количество GPU: {gpu_count}")
            
            for i in range(gpu_count):
                gpu_name = torch.cuda.get_device_name(i)
                props = torch.cuda.get_device_properties(i)
                memory_gb = props.total_memory / (1024**3)
                print(f"  GPU {i}: {gpu_name} ({memory_gb:.2f} ГБ)")
            
            current_device = torch.cuda.current_device()
            print(f"🎯 Текущее устройство: GPU {current_device}")
            
            # Тест создания тензора
            try:
                test_tensor = torch.tensor([1.0, 2.0, 3.0]).cuda()
                print("✅ Тест создания тензора на GPU: УСПЕШНО")
                print("🚀 Бот будет работать с GPU ускорением!")
            except Exception as e:
                print(f"❌ Тест создания тензора на GPU: ОШИБКА - {e}")
                cuda_available = False
        else:
            print("💡 Для активации GPU выполните:")
            print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
            print("⚠️  Бот будет работать на CPU (медленнее)")
        
        print("=" * 60)
        return cuda_available
        
    except ImportError:
        print("❌ PyTorch не установлен!")
        return False


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
    parser.add_argument(
        "--skip-gpu-check", 
        action="store_true", 
        help="Пропустить проверку GPU"
    )
    
    args = parser.parse_args()
    
    # Настраиваем логирование на основе параметров
    console_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logging(args.log, console_level=console_level)
    
    # Проверка GPU статуса (если не отключена)
    if not args.skip_gpu_check:
        gpu_available = check_gpu_status()
        if not args.debug:  # Пауза только если не debug режим
            input("Нажмите Enter для продолжения...")
    
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