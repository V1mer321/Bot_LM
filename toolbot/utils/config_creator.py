#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для создания и шифрования конфигурационного файла бота.
"""

import os
import json
import logging
import argparse
from pathlib import Path
from cryptography.fernet import Fernet

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def generate_and_save_key(key_path="key.key"):
    """
    Генерация и сохранение ключа шифрования
    
    Args:
        key_path: Путь для сохранения ключа
        
    Returns:
        Сгенерированный ключ
    """
    try:
        key = Fernet.generate_key()
        with open(key_path, "wb") as key_file:
            key_file.write(key)
        logger.info(f"✅ Ключ шифрования успешно создан и сохранен в {key_path}")
        return key
    except Exception as e:
        logger.error(f"❌ Ошибка при создании ключа: {e}")
        return None


def load_key(key_path="key.key"):
    """
    Загрузка ключа шифрования
    
    Args:
        key_path: Путь к файлу ключа
        
    Returns:
        Загруженный ключ или None в случае ошибки
    """
    try:
        if not os.path.exists(key_path):
            logger.error(f"❌ Файл ключа не найден: {key_path}")
            return None
            
        with open(key_path, "rb") as key_file:
            key = key_file.read()
        logger.info(f"✅ Ключ шифрования успешно загружен из {key_path}")
        return key
    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке ключа: {e}")
        return None


def encrypt_config(config_data, key=None, key_path="key.key", output_path="config.encrypted"):
    """
    Шифрование и сохранение конфигурации
    
    Args:
        config_data: Данные конфигурации для шифрования
        key: Ключ шифрования (если None, загружается из файла)
        key_path: Путь к файлу ключа
        output_path: Путь для сохранения зашифрованного файла
        
    Returns:
        True в случае успеха, False в случае ошибки
    """
    try:
        # Если ключ не передан, загружаем его из файла
        if key is None:
            key = load_key(key_path)
            if key is None:
                logger.info("🔑 Создаю новый ключ шифрования...")
                key = generate_and_save_key(key_path)
                if key is None:
                    return False
        
        f = Fernet(key)
        encrypted_data = f.encrypt(json.dumps(config_data).encode())
        
        with open(output_path, "wb") as config_file:
            config_file.write(encrypted_data)
            
        logger.info(f"✅ Конфигурация успешно создана и зашифрована в {output_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при шифровании конфигурации: {e}")
        return False


def create_default_config():
    """
    Создание конфигурации по умолчанию
    
    Returns:
        Словарь с конфигурацией по умолчанию
    """
    # Создаем базовый шаблон конфигурации
    config_data = {
        "telegram_token": "TELEGRAM_BOT_TOKEN",
        "photos_folder": "data/instruments",
        "admin_ids": [123456789],  # ID администраторов
        "whitelist": [123456789],  # ID разрешенных пользователей
        
        # Параметры поиска изображений
        "similarity_threshold": 0.25,
        "top_n_results": 5,
        "contrast_weight": 0.8,
        "sharpness_weight": 0.8,
        "brightness_weight": 0.7,
        "brand_bonus": 2.0,
        "type_bonus": 1.5,
        "brand_type_bonus": 2.5,
        
        # Пути к справочным таблицам и файлам
        "data_files": {
            "table_2": "data/table_2.xlsx",
            "table_3": "data/table_3.xlsx",
            "les_ega_pdf": "data/les_ega.pdf",
            "skobyanka_table": "data/skobyanka.xlsx"
        }
    }
    
    return config_data


def main():
    # Разбор аргументов командной строки
    parser = argparse.ArgumentParser(description="Создание и шифрование конфигурации бота")
    parser.add_argument(
        "--token", 
        type=str, 
        help="Токен Telegram бота"
    )
    parser.add_argument(
        "--photos", 
        type=str, 
        help="Путь к директории с изображениями"
    )
    parser.add_argument(
        "--admins", 
        type=str, 
        help="Список ID администраторов, разделенных запятыми"
    )
    parser.add_argument(
        "--whitelist", 
        type=str, 
        help="Список ID разрешенных пользователей, разделенных запятыми"
    )
    parser.add_argument(
        "--key", 
        type=str, 
        default="key.key", 
        help="Путь к файлу ключа"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="config.encrypted", 
        help="Путь к выходному файлу конфигурации"
    )
    
    args = parser.parse_args()
    
    print("🔧 Создание конфигурации для ToolBot...")
    
    # Создаем базовую конфигурацию
    config = create_default_config()
    
    # Обновляем конфигурацию из аргументов командной строки
    if args.token:
        config["telegram_token"] = args.token
        
    if args.photos:
        config["photos_folder"] = args.photos
        
    if args.admins:
        try:
            admin_ids = [int(x.strip()) for x in args.admins.split(',')]
            config["admin_ids"] = admin_ids
        except ValueError:
            logger.error("❌ Некорректный формат ID администраторов")
            
    if args.whitelist:
        try:
            whitelist = [int(x.strip()) for x in args.whitelist.split(',')]
            config["whitelist"] = whitelist
        except ValueError:
            logger.error("❌ Некорректный формат ID пользователей в белом списке")
    
    # Шифруем и сохраняем конфигурацию
    if encrypt_config(config, key_path=args.key, output_path=args.output):
        print(f"✅ Конфигурация успешно создана и сохранена в {args.output}")
    else:
        print("❌ Ошибка при создании конфигурации")


if __name__ == "__main__":
    main() 