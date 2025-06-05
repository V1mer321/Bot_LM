#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт миграции Excel файлов в SQLite
Переводит skobyanka.xlsx и table_2.xlsx в таблицы БД
"""

import pandas as pd
import sqlite3
import os
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database_connection(db_path="data/excel_data.db"):
    """Создание подключения к SQLite базе данных"""
    try:
        conn = sqlite3.connect(db_path)
        logger.info(f"✅ Подключение к БД {db_path} успешно")
        return conn
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")
        raise

def migrate_skobyanka_to_db(conn):
    """Миграция файла skobyanka.xlsx в таблицу skobyanka_products"""
    
    excel_file = "data/skobyanka.xlsx"
    if not os.path.exists(excel_file):
        logger.error(f"❌ Файл {excel_file} не найден")
        return False
    
    try:
        # Читаем Excel файл
        df = pd.read_excel(excel_file)
        logger.info(f"📊 Загружен файл skobyanka.xlsx: {len(df)} строк")
        
        # Очистка данных - убираем строки с пустыми значениями
        df_clean = df.dropna(subset=['Артикул', 'Наименование'])
        logger.info(f"🧹 После очистки: {len(df_clean)} строк")
        
        # Создаем таблицу
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS skobyanka_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_code TEXT NOT NULL,
            name TEXT NOT NULL,
            quantity_kg REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        cursor = conn.cursor()
        cursor.execute(create_table_sql)
        
        # Создаем индексы для быстрого поиска
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skobyanka_article ON skobyanka_products(article_code);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skobyanka_name ON skobyanka_products(name);")
        
        # Очищаем таблицу перед загрузкой
        cursor.execute("DELETE FROM skobyanka_products")
        
        # Загружаем данные
        for _, row in df_clean.iterrows():
            cursor.execute("""
                INSERT INTO skobyanka_products (article_code, name, quantity_kg)
                VALUES (?, ?, ?)
            """, (
                str(row['Артикул']).replace('.0', '') if pd.notna(row['Артикул']) else None,
                str(row['Наименование']) if pd.notna(row['Наименование']) else None,
                float(row['Количество в кг']) if pd.notna(row['Количество в кг']) else None
            ))
        
        conn.commit()
        
        # Проверяем результат
        cursor.execute("SELECT COUNT(*) FROM skobyanka_products")
        count = cursor.fetchone()[0]
        logger.info(f"✅ Таблица skobyanka_products создана: {count} записей")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при миграции skobyanka: {e}")
        conn.rollback()
        return False

def migrate_table2_to_db(conn):
    """Миграция файла table_2.xlsx в таблицу stores"""
    
    excel_file = "data/table_2.xlsx"
    if not os.path.exists(excel_file):
        logger.error(f"❌ Файл {excel_file} не найден")
        return False
    
    try:
        # Читаем Excel файл
        df = pd.read_excel(excel_file)
        logger.info(f"📊 Загружен файл table_2.xlsx: {len(df)} строк")
        
        # Очистка данных - убираем строки с пустыми значениями
        df_clean = df.dropna(subset=['Код', 'Наименование'])
        logger.info(f"🧹 После очистки: {len(df_clean)} строк")
        
        # Создаем таблицу
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            department TEXT,
            phone_numbers TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        cursor = conn.cursor()
        cursor.execute(create_table_sql)
        
        # Создаем индексы для быстрого поиска
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stores_code ON stores(code);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stores_name ON stores(name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stores_department ON stores(department);")
        
        # Очищаем таблицу перед загрузкой
        cursor.execute("DELETE FROM stores")
        
        # Загружаем данные
        for _, row in df_clean.iterrows():
            cursor.execute("""
                INSERT INTO stores (code, name, department, phone_numbers)
                VALUES (?, ?, ?, ?)
            """, (
                str(row['Код']) if pd.notna(row['Код']) else None,
                str(row['Наименование']) if pd.notna(row['Наименование']) else None,
                str(row['Отдел']) if pd.notna(row['Отдел']) else None,
                str(row['Номера']) if pd.notna(row['Номера']) else None
            ))
        
        conn.commit()
        
        # Проверяем результат
        cursor.execute("SELECT COUNT(*) FROM stores")
        count = cursor.fetchone()[0]
        logger.info(f"✅ Таблица stores создана: {count} записей")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при миграции table_2: {e}")
        conn.rollback()
        return False

def create_search_functions(conn):
    """Создание вспомогательных функций для поиска"""
    
    cursor = conn.cursor()
    
    # Создаем view для удобного поиска по скобянке
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS skobyanka_search AS
        SELECT 
            id,
            article_code,
            name,
            quantity_kg,
            CASE 
                WHEN quantity_kg > 0 THEN 'В наличии'
                ELSE 'Нет в наличии'
            END as availability_status
        FROM skobyanka_products
        ORDER BY name;
    """)
    
    # Создаем view для удобного поиска по магазинам
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS stores_search AS
        SELECT 
            id,
            code,
            name,
            department,
            phone_numbers,
            CASE 
                WHEN phone_numbers IS NOT NULL AND phone_numbers != '' THEN 'Есть телефон'
                ELSE 'Нет телефона'
            END as contact_status
        FROM stores
        ORDER BY name;
    """)
    
    conn.commit()
    logger.info("✅ Создана views для поиска")

def verify_migration(conn):
    """Проверка результатов миграции"""
    
    cursor = conn.cursor()
    
    # Проверяем таблицу skobyanka_products
    cursor.execute("SELECT COUNT(*) FROM skobyanka_products")
    skobyanka_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT name FROM skobyanka_products LIMIT 3")
    skobyanka_samples = cursor.fetchall()
    
    # Проверяем таблицу stores
    cursor.execute("SELECT COUNT(*) FROM stores")
    stores_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT name FROM stores LIMIT 3")
    stores_samples = cursor.fetchall()
    
    print("\n" + "="*50)
    print("📊 РЕЗУЛЬТАТЫ МИГРАЦИИ:")
    print("="*50)
    print(f"🔧 Скобяные изделия: {skobyanka_count} записей")
    print("   Примеры товаров:")
    for sample in skobyanka_samples:
        print(f"   - {sample[0]}")
    
    print(f"\n🏪 Магазины/отделы: {stores_count} записей")
    print("   Примеры магазинов:")
    for sample in stores_samples:
        print(f"   - {sample[0]}")
    
    return skobyanka_count > 0 and stores_count > 0

def main():
    """Основная функция миграции"""
    
    print("🚀 Начинаем миграцию Excel файлов в SQLite")
    print("="*50)
    
    # Создаем подключение к БД
    conn = create_database_connection()
    
    try:
        # Миграция файла skobyanka.xlsx
        print("\n1. Миграция файла skobyanka.xlsx...")
        skobyanka_success = migrate_skobyanka_to_db(conn)
        
        # Миграция файла table_2.xlsx
        print("\n2. Миграция файла table_2.xlsx...")
        table2_success = migrate_table2_to_db(conn)
        
        # Создание вспомогательных функций
        print("\n3. Создание индексов и views...")
        create_search_functions(conn)
        
        # Проверка результатов
        print("\n4. Проверка миграции...")
        success = verify_migration(conn)
        
        if success and skobyanka_success and table2_success:
            print("\n🎉 Миграция завершена успешно!")
            print("\n📋 Следующие шаги:")
            print("1. Обновите код поиска для работы с новыми таблицами")
            print("2. Протестируйте поиск по скобяным изделиям")
            print("3. Протестируйте поиск по магазинам")
            print(f"4. База данных сохранена в: data/excel_data.db")
        else:
            print("\n❌ Миграция завершилась с ошибками")
            
    finally:
        conn.close()

if __name__ == "__main__":
    main() 