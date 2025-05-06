#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Запуск бота с улучшенным локальным поиском вместо Cloudinary
Использует существующие библиотеки без дополнительных зависимостей
"""

import os
import sys
import logging
import shutil
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Импортируем наш модуль улучшенного локального поиска
from enhanced_local_search import patch_bot_module, update_enhanced_index, initialize_enhanced_search

# Проверяем наличие необходимых компонентов
try:
    import torch
    import cv2
    import faiss
    from PIL import Image
    logger.info("✅ Все необходимые компоненты найдены")
except ImportError as e:
    logger.error(f"❌ Отсутствует компонент: {e}")
    print("Для работы улучшенного поиска необходимы следующие библиотеки:")
    print("- PyTorch (torch)")
    print("- OpenCV (cv2)")
    print("- FAISS (faiss-cpu)")
    print("- PIL (pillow)")
    sys.exit(1)

# Директория для образцов изображений
SAMPLES_DIR = "sample_images"

def setup_sample_images():
    """Настройка каталога с образцами изображений"""
    # Создаем директорию если не существует
    if not os.path.exists(SAMPLES_DIR):
        os.makedirs(SAMPLES_DIR)
        logger.info(f"✅ Создана директория {SAMPLES_DIR}")
    
    # Создаем поддиректории для разных брендов
    brands = ["Makita", "Oasis", "DeWalt", "Bosch", "Milwaukee", "Интерскол", "Dexter"]
    for brand in brands:
        brand_dir = os.path.join(SAMPLES_DIR, brand)
        if not os.path.exists(brand_dir):
            os.makedirs(brand_dir)
            logger.info(f"✅ Создана директория для бренда {brand}")
    
    # Проверяем, есть ли фото в базе
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        image_files.extend(list(Path(SAMPLES_DIR).glob(f'**/{ext}')))
    
    logger.info(f"В каталоге образцов найдено {len(image_files)} изображений")
    
    # Проверяем наличие photos_folder в конфигурации
    from Bot_ebet import load_config
    config = load_config()
    photos_folder = config.get("photos_folder")
    
    if photos_folder and os.path.exists(photos_folder):
        logger.info(f"Найдена основная директория с фото: {photos_folder}")
        
        # Предлагаем скопировать изображения
        if len(image_files) == 0:
            logger.info("Копирую образцы из основной директории...")
            
            # Определяем, какие поддиректории в photos_folder нужно скопировать
            base_folders = []
            for item in os.listdir(photos_folder):
                item_path = os.path.join(photos_folder, item)
                if os.path.isdir(item_path):
                    base_folders.append(item)
            
            # Если директория структурирована, копируем изображения из неё
            if base_folders:
                for folder in base_folders:
                    src_dir = os.path.join(photos_folder, folder)
                    dest_dir = os.path.join(SAMPLES_DIR, folder)
                    
                    # Копируем до 20 файлов из каждой директории
                    copied = 0
                    for ext in ['*.jpg', '*.jpeg', '*.png']:
                        for file in Path(src_dir).glob(ext):
                            if copied >= 20:
                                break
                            
                            dest_file = os.path.join(dest_dir, file.name)
                            try:
                                if not os.path.exists(dest_dir):
                                    os.makedirs(dest_dir)
                                shutil.copy2(file, dest_file)
                                copied += 1
                            except Exception as e:
                                logger.error(f"Ошибка при копировании {file}: {e}")
                    
                    logger.info(f"Скопировано {copied} изображений из {folder}")
            
            # Проверяем снова количество файлов
            image_files = []
            for ext in ['*.jpg', '*.jpeg', '*.png']:
                image_files.extend(list(Path(SAMPLES_DIR).glob(f'**/{ext}')))
            
            logger.info(f"Теперь в каталоге образцов {len(image_files)} изображений")
    
    return len(image_files) > 0

if __name__ == "__main__":
    print("🤖 Запуск бота с улучшенным локальным поиском...")
    
    # Настраиваем каталог с образцами
    print("📁 Настройка каталога с образцами...")
    samples_ready = setup_sample_images()
    
    if not samples_ready:
        print("⚠️ В каталоге образцов нет изображений! Поиск будет работать некорректно.")
        print(f"Добавьте изображения в директорию {SAMPLES_DIR} и его поддиректории.")
        print("Продолжаем запуск...")
    
    # Инициализируем улучшенный поиск
    print("🔍 Инициализация улучшенного поиска...")
    if initialize_enhanced_search():
        print("✅ Улучшенный поиск инициализирован")
    else:
        print("❌ Не удалось инициализировать улучшенный поиск")
        sys.exit(1)
    
    # Индексируем изображения
    print(f"🔄 Индексация изображений из {SAMPLES_DIR}...")
    if update_enhanced_index(SAMPLES_DIR):
        print("✅ Индекс изображений успешно обновлен")
    else:
        print("⚠️ Проблема при обновлении индекса, продолжаем с текущим состоянием")
    
    # Патчим основной модуль бота
    print("🔧 Замена Cloudinary на улучшенный локальный поиск...")
    if patch_bot_module():
        print("✅ Модуль бота успешно настроен")
    else:
        print("❌ Не удалось настроить модуль бота")
        sys.exit(1)
    
    # Запускаем бота
    print("🚀 Запуск бота...")
    from Bot_ebet import main
    main() 