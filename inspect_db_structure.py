#!/usr/bin/env python3
import sqlite3
import json

def inspect_db_structure():
    """Детальное изучение структуры базы данных"""
    try:
        conn = sqlite3.connect('data/unified_products.db')
        cursor = conn.cursor()
        
        # Получаем список таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print('Таблицы в базе данных:')
        for table in tables:
            print(f'- {table[0]}')
        
        print('\n' + '='*60)
        
        # Проверяем структуру основной таблицы products
        print('\nСтруктура таблицы products:')
        cursor.execute('PRAGMA table_info(products)')
        columns = cursor.fetchall()
        for col in columns:
            print(f'  {col[1]} ({col[2]}) - {"NOT NULL" if col[3] else "NULL"} - {"PK" if col[5] else ""}')
        
        # Показываем несколько примеров данных
        print('\nПримеры записей из таблицы products:')
        cursor.execute('SELECT item_id, url, picture FROM products LIMIT 5')
        samples = cursor.fetchall()
        for i, sample in enumerate(samples, 1):
            print(f'\nЗапись #{i}:')
            print(f'  item_id: {sample[0]}')
            print(f'  url: {sample[1]}')
            print(f'  picture: {sample[2][:100]}...' if sample[2] and len(sample[2]) > 100 else f'  picture: {sample[2]}')
            
            # Проверяем есть ли вектор
            cursor.execute('SELECT vector FROM products WHERE item_id = ?', (sample[0],))
            vector_data = cursor.fetchone()[0]
            if vector_data:
                print(f'  vector: [BLOB data - {len(vector_data)} bytes]')
            else:
                print(f'  vector: NULL')
        
        # Подсчитываем статистику
        cursor.execute('SELECT COUNT(*) FROM products')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM products WHERE vector IS NOT NULL')
        with_vectors = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM products WHERE picture IS NOT NULL')
        with_pictures = cursor.fetchone()[0]
        
        print(f'\nСтатистика:')
        print(f'- Всего товаров: {total}')
        print(f'- С векторами: {with_vectors}')
        print(f'- С изображениями: {with_pictures}')
        
        # Проверяем разные домены в URL
        cursor.execute("SELECT DISTINCT SUBSTR(url, 1, INSTR(url, '.ru') + 2) FROM products WHERE url IS NOT NULL LIMIT 10")
        domains = [row[0] for row in cursor.fetchall()]
        print(f'- Домены: {domains}')
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при изучении структуры: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    inspect_db_structure() 