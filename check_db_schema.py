#!/usr/bin/env python3
import sqlite3

def check_unified_db():
    """Проверка схемы unified_products.db"""
    try:
        conn = sqlite3.connect('data/unified_products.db')
        cursor = conn.cursor()
        
        print("=== UNIFIED_PRODUCTS.DB ===")
        
        # Список таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Таблицы: {[t[0] for t in tables]}")
        
        # Проверяем таблицу products
        cursor.execute("PRAGMA table_info(products)")
        cols = cursor.fetchall()
        print("\nКолонки таблицы 'products':")
        for col in cols:
            print(f"  {col[1]} ({col[2]})")
        
        conn.close()
        
    except Exception as e:
        print(f"Ошибка при проверке unified_products.db: {e}")

if __name__ == "__main__":
    check_unified_db() 