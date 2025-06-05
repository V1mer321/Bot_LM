#!/usr/bin/env python3
import sqlite3

def check_sqlite_db():
    """Проверка SQLite базы перед миграцией"""
    try:
        conn = sqlite3.connect('data/unified_products.db')
        cursor = conn.cursor()
        
        # Общая статистика
        cursor.execute('SELECT COUNT(*) FROM products')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM products WHERE vector IS NOT NULL')
        with_vectors = cursor.fetchone()[0]
        
        print("✅ SQLite база готова к миграции:")
        print(f"📦 Всего товаров: {total}")
        print(f"🔮 С векторами: {with_vectors}")
        print(f"📊 Процент готовности: {(with_vectors/total*100):.1f}%")
        
        # Примеры данных
        cursor.execute('SELECT item_id, url FROM products WHERE vector IS NOT NULL LIMIT 3')
        samples = cursor.fetchall()
        print(f"📄 Примеры товаров: {samples}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке SQLite: {e}")
        return False

if __name__ == '__main__':
    check_sqlite_db() 