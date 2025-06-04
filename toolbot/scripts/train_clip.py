#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для тонкой настройки модели CLIP на данных строительных инструментов.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Добавляем родительскую директорию в sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from toolbot.utils.clip_fine_tuner import fine_tune_clip_model

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(script_dir, 'clip_training.log'))
    ]
)

logger = logging.getLogger(__name__)


def parse_args():
    """
    Парсинг аргументов командной строки.
    
    Returns:
        Объект с аргументами
    """
    parser = argparse.ArgumentParser(description='Тонкая настройка модели CLIP на данных строительных инструментов')
    
    parser.add_argument('--data-dir', type=str, required=True,
                        help='Директория с изображениями для обучения (структура: папки с названиями категорий)')
    
    parser.add_argument('--categories-file', type=str, default=os.path.join(parent_dir, 'data', 'tool_categories.json'),
                        help='Путь к файлу с категориями инструментов')
    
    parser.add_argument('--epochs', type=int, default=3,
                        help='Количество эпох обучения')
    
    parser.add_argument('--learning-rate', type=float, default=5e-6,
                        help='Скорость обучения')
    
    parser.add_argument('--output-dir', type=str, 
                        default=os.path.join(parent_dir, 'models', 'clip_fine_tuned'),
                        help='Директория для сохранения настроенной модели')
    
    return parser.parse_args()


def main():
    """
    Основная функция для запуска тонкой настройки модели CLIP.
    """
    args = parse_args()
    
    # Проверяем существование директории с данными
    if not os.path.exists(args.data_dir):
        logger.error(f"Директория с данными не существует: {args.data_dir}")
        return 1
    
    # Проверяем существование файла категорий
    if not os.path.exists(args.categories_file):
        logger.warning(f"Файл категорий не существует: {args.categories_file}")
        logger.warning("Будут использованы названия директорий как категории")
    
    # Создаем директорию для выходных данных, если её нет
    os.makedirs(args.output_dir, exist_ok=True)
    
    logger.info(f"Запуск тонкой настройки модели CLIP")
    logger.info(f"Параметры:")
    logger.info(f"  - Директория с данными: {args.data_dir}")
    logger.info(f"  - Файл категорий: {args.categories_file}")
    logger.info(f"  - Количество эпох: {args.epochs}")
    logger.info(f"  - Скорость обучения: {args.learning_rate}")
    logger.info(f"  - Директория для сохранения: {args.output_dir}")
    
    # Запускаем тонкую настройку
    try:
        result_path = fine_tune_clip_model(
            image_dir=args.data_dir,
            categories_file=args.categories_file,
            epochs=args.epochs,
            learning_rate=args.learning_rate
        )
        
        if result_path:
            logger.info(f"Тонкая настройка успешно завершена")
            logger.info(f"Модель сохранена в {result_path}")
            return 0
        else:
            logger.error("Ошибка при тонкой настройке модели")
            return 1
    except Exception as e:
        logger.error(f"Исключение при тонкой настройке модели: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main()) 