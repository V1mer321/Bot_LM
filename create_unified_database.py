import pandas as pd
import json
import ast
import sqlite3
import requests
from PIL import Image
import torch
import clip
import numpy as np
from io import BytesIO
import time
import os
from urllib.parse import urlparse
import hashlib

def setup_clip():
    """Инициализация CLIP модели"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, preprocess = clip.load("ViT-B/32", device=device)
    return model, preprocess, device

def get_image_features(model, preprocess, device, image_url):
    """Извлечение признаков из изображения по URL"""
    try:
        # Загружаем изображение
        response = requests.get(image_url, timeout=10)
        if response.status_code != 200:
            return None
            
        image = Image.open(BytesIO(response.content)).convert('RGB')
        image_input = preprocess(image).unsqueeze(0).to(device)
        
        with torch.no_grad():
            features = model.encode_image(image_input)
            # Нормализуем вектор
            features = features / features.norm(dim=-1, keepdim=True)
            
        return features.cpu().numpy().flatten()
    
    except Exception as e:
        print(f"Ошибка при обработке изображения {image_url}: {e}")
        return None

def parse_picture_data(picture_str):
    """Парсинг строки с изображениями и возврат первого URL"""
    try:
        if not picture_str or picture_str == '':
            return None
            
        # Пробуем разные варианты парсинга
        if picture_str.startswith('['):
            # JSON массив
            pictures = json.loads(picture_str)
            if pictures and len(pictures) > 0:
                return pictures[0]
        else:
            # Простая строка URL
            return picture_str.strip('"')
            
    except Exception as e:
        print(f"Ошибка парсинга изображения: {e}")
        return None

def create_unified_database():
    """Создание единой БД из двух файлов"""
    print("Настройка CLIP модели...")
    model, preprocess, device = setup_clip()
    
    # Создаем новую БД
    conn = sqlite3.connect('data/unified_products.db')
    cursor = conn.cursor()
    
    # Создаем таблицу
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            item_id TEXT PRIMARY KEY,
            url TEXT,
            picture TEXT,
            vector BLOB
        )
    ''')
    
    print("Обработка файла new.csv...")
    
    # Обрабатываем new.csv
    try:
        df_new = pd.read_csv('data/new.csv', sep=';', encoding='cp1251')
        print(f"Загружено {len(df_new)} записей из new.csv")
        for index, row in df_new.iterrows():
            try:
                item_id = str(row['item_id']) if 'item_id' in row and pd.notna(row['item_id']) else None
                url = row['url'] if 'url' in row and pd.notna(row['url']) else None
                picture_str = row['picture'] if 'picture' in row and pd.notna(row['picture']) else None
                if not item_id or not url or not picture_str:
                    continue
                picture_url = parse_picture_data(picture_str)
                if not picture_url:
                    continue
                print(f"Обработка товара {item_id} ({index+1}/{len(df_new)}) из new.csv...")
                vector = get_image_features(model, preprocess, device, picture_url)
                if vector is not None:
                    vector_blob = vector.tobytes()
                    cursor.execute('''
                        INSERT OR REPLACE INTO products (item_id, url, picture, vector)
                        VALUES (?, ?, ?, ?)
                    ''', (item_id, url, picture_url, vector_blob))
                if index % 10 == 0:
                    conn.commit()
            except Exception as e:
                print(f"Ошибка при обработке записи {index} из new.csv: {e}")
                continue
        conn.commit()
    except Exception as e:
        print(f"Ошибка при чтении new.csv: {e}")

    print("Обработка файла items_v2_202505221136.csv...")
    try:
        chunk_size = 100
        chunk_count = 0
        for chunk in pd.read_csv('data/items_v2_202505221136.csv',
                                chunksize=chunk_size,
                                encoding='cp1251',
                                on_bad_lines='skip',
                                sep=';'):
            print(f"Загружено {len(chunk)} записей из items_v2_202505221136.csv (часть {chunk_count+1})")
            for index, row in chunk.iterrows():
                try:
                    item_id = str(row['item_id']) if 'item_id' in row and pd.notna(row['item_id']) else None
                    url = row['url'] if 'url' in row and pd.notna(row['url']) else None
                    picture_str = row['picture'] if 'picture' in row and pd.notna(row['picture']) else None
                    if not item_id or not url or not picture_str:
                        continue
                    picture_url = parse_picture_data(picture_str)
                    if not picture_url:
                        continue
                    print(f"Обработка товара {item_id} из items_v2...")
                    vector = get_image_features(model, preprocess, device, picture_url)
                    if vector is not None:
                        vector_blob = vector.tobytes()
                        cursor.execute('''
                            INSERT OR REPLACE INTO products (item_id, url, picture, vector)
                            VALUES (?, ?, ?, ?)
                        ''', (item_id, url, picture_url, vector_blob))
                except Exception as e:
                    print(f"Ошибка при обработке записи из items_v2: {e}")
                    continue
            chunk_count += 1
            conn.commit()
            print(f"Обработано частей: {chunk_count}")
    except Exception as e:
        print(f"Ошибка при чтении items_v2: {e}")
    
    # Сохраняем и закрываем
    conn.commit()
    
    # Статистика
    cursor.execute('SELECT COUNT(*) FROM products')
    total_count = cursor.fetchone()[0]
    print(f"Создана единая БД с {total_count} товарами")
    
    conn.close()
    print("БД создана: data/unified_products.db")

if __name__ == "__main__":
    create_unified_database() 