#!/usr/bin/env python3
"""
Скрипт для экспорта unified_products.db в формат TXT.
Сохраняет всю информацию кроме векторов CLIP (они будут перегенерированы при необходимости).
"""
import sqlite3
import json
import os
from datetime import datetime

def export_to_txt():
    """Экспортирует базу данных в TXT формат"""
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect('data/unified_products.db')
        cursor = conn.cursor()
        
        # Получаем все данные
        cursor.execute('SELECT item_id, url, picture FROM products ORDER BY item_id')
        products = cursor.fetchall()
        
        print(f"📦 Найдено {len(products)} товаров для экспорта")
        
        # Создаем директорию для TXT файлов если её нет
        txt_dir = 'data/txt_export'
        os.makedirs(txt_dir, exist_ok=True)
        
        # Экспорт в простой TXT формат (разделители - табуляция)
        txt_file = os.path.join(txt_dir, 'unified_products.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            # Заголовок
            f.write("# Unified Products Database Export\n")
            f.write(f"# Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total products: {len(products)}\n")
            f.write("# Format: ITEM_ID<TAB>URL<TAB>PICTURE_URL\n")
            f.write("#" + "="*80 + "\n")
            
            # Данные
            for product in products:
                item_id, url, picture = product
                f.write(f"{item_id}\t{url or ''}\t{picture or ''}\n")
        
        print(f"✅ Экспорт в TXT завершен: {txt_file}")
        
        # Экспорт в JSON формат для структурированных данных
        json_file = os.path.join(txt_dir, 'unified_products.json')
        json_data = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "total_products": len(products),
                "format_version": "1.0"
            },
            "products": []
        }
        
        for product in products:
            item_id, url, picture = product
            json_data["products"].append({
                "item_id": item_id,
                "url": url,
                "picture": picture
            })
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Экспорт в JSON завершен: {json_file}")
        
        # Экспорт в CSV формат
        csv_file = os.path.join(txt_dir, 'unified_products.csv')
        with open(csv_file, 'w', encoding='utf-8') as f:
            # Заголовок CSV
            f.write("item_id,url,picture\n")
            
            # Данные (экранируем запятые в URL)
            for product in products:
                item_id, url, picture = product
                # Экранируем кавычки и запятые в CSV
                url_clean = (url or '').replace('"', '""')
                picture_clean = (picture or '').replace('"', '""')
                
                f.write(f'"{item_id}","{url_clean}","{picture_clean}"\n')
        
        print(f"✅ Экспорт в CSV завершен: {csv_file}")
        
        # Создаем простой TXT файл с только ID и URL (для быстрого просмотра)
        simple_txt_file = os.path.join(txt_dir, 'products_simple.txt')
        with open(simple_txt_file, 'w', encoding='utf-8') as f:
            f.write("# Simplified Products List\n")
            f.write("# Format: ITEM_ID - URL\n")
            f.write("#" + "="*50 + "\n")
            
            for product in products:
                item_id, url, picture = product
                f.write(f"{item_id} - {url or 'NO_URL'}\n")
        
        print(f"✅ Упрощенный TXT завершен: {simple_txt_file}")
        
        # Статистика
        print(f"\n📊 Статистика экспорта:")
        print(f"- Всего товаров: {len(products)}")
        
        # Подсчитываем товары с изображениями
        with_pictures = sum(1 for p in products if p[2])
        print(f"- С изображениями: {with_pictures}")
        
        # Подсчитываем товары с URL
        with_urls = sum(1 for p in products if p[1])
        print(f"- С URL: {with_urls}")
        
        # Размеры файлов
        for file_path in [txt_file, json_file, csv_file, simple_txt_file]:
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            print(f"- {os.path.basename(file_path)}: {size_mb:.2f} MB")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при экспорте: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    export_to_txt() 