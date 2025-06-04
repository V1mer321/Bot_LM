import sqlite3
import numpy as np
import torch
from PIL import Image, ImageEnhance, ImageOps
import requests
from io import BytesIO
import cv2

class UnifiedDatabaseService:
    def __init__(self, db_path='data/unified_products.db'):
        self.db_path = db_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Ленивая инициализация - модель загружается только при первом использовании
        self.model = None
        self.preprocess = None
        # Порог схожести для фильтрации результатов - понижен для лучшего поиска
        self.similarity_threshold = 0.2  # Понижен с 0.3 до 0.2
        
    def _ensure_model_loaded(self):
        """Ленивая инициализация CLIP модели"""
        if self.model is None:
            try:
                import clip
                self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)
            except Exception as e:
                raise Exception(f"Ошибка при загрузке CLIP модели: {e}")
        
    def enhance_image(self, image):
        """Улучшение качества изображения перед обработкой"""
        try:
            # Конвертируем в RGB если нужно
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Нормализуем размер (CLIP лучше работает с определённым размером)
            image = ImageOps.fit(image, (224, 224), Image.Resampling.LANCZOS)
            
            # Улучшаем контрастность
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
            
            # Улучшаем чёткость
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)
            
            return image
        except Exception as e:
            print(f"Ошибка при улучшении изображения: {e}")
            return image
        
    def get_image_features(self, image_path_or_url):
        """Извлечение признаков из изображения с улучшенной обработкой"""
        try:
            # Ленивая инициализация модели
            self._ensure_model_loaded()
            
            if image_path_or_url.startswith(('http://', 'https://')):
                # URL изображения
                response = requests.get(image_path_or_url, timeout=15)
                if response.status_code != 200:
                    return None
                image = Image.open(BytesIO(response.content))
            else:
                # Локальный файл
                image = Image.open(image_path_or_url)
            
            # Улучшаем изображение
            image = self.enhance_image(image)
            
            # Обрабатываем CLIP дважды для стабильности
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            
            features_list = []
            # Делаем несколько проходов для стабильности
            for _ in range(3):
                with torch.no_grad():
                    features = self.model.encode_image(image_input)
                    # Нормализуем вектор для корректного косинусного сходства
                    features = features / features.norm(dim=-1, keepdim=True)
                    features_list.append(features.cpu().numpy().flatten())
            
            # Берем средний вектор для большей стабильности
            avg_features = np.mean(features_list, axis=0)
            # Повторно нормализуем
            avg_features = avg_features / np.linalg.norm(avg_features)
                
            return avg_features
            
        except Exception as e:
            print(f"Ошибка при обработке изображения: {e}")
            return None
    
    def cosine_similarity(self, vec1, vec2):
        """Вычисление косинусного сходства между двумя векторами"""
        return np.dot(vec1, vec2)
    
    def search_similar_products(self, image_path_or_url, top_k=5, min_similarity=None):
        """Поиск похожих товаров по изображению с улучшенной точностью"""
        query_vector = self.get_image_features(image_path_or_url)
        if query_vector is None:
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем все товары с ФИКСИРОВАННЫМ порядком для стабильности
        cursor.execute('SELECT item_id, url, picture, vector FROM products ORDER BY item_id')
        rows = cursor.fetchall()
        
        similarities = []
        
        # Понижаем минимальный порог схожести для лучшего поиска
        threshold = min_similarity if min_similarity is not None else 0.1  # Понижен с 0.3 до 0.1
        
        for row in rows:
            item_id, url, picture, vector_blob = row
            
            # Восстанавливаем вектор из БД
            db_vector = np.frombuffer(vector_blob, dtype=np.float32)
            
            # Вычисляем косинусное сходство
            similarity = self.cosine_similarity(query_vector, db_vector)
            
            # Фильтруем по порогу схожести
            if similarity >= threshold:
                similarities.append({
                    'item_id': item_id,
                    'url': url,
                    'picture': picture,
                    'similarity': float(similarity)
                })
        
        # Сортируем по убыванию схожести (стабильная сортировка)
        similarities.sort(key=lambda x: (-x['similarity'], x['item_id']))
        
        conn.close()
        return similarities[:top_k]
    
    def search_with_multiple_thresholds(self, image_path_or_url, top_k=5):
        """Поиск с несколькими порогами для лучшего качества результатов"""
        # Еще больше понижаем пороги для максимального поиска
        thresholds = [0.5, 0.4, 0.3, 0.25, 0.2, 0.15, 0.1]  # Добавлены очень низкие пороги
        
        for threshold in thresholds:
            results = self.search_similar_products(image_path_or_url, top_k=top_k*2, min_similarity=threshold)
            if len(results) >= top_k:
                # Дополнительная фильтрация: убираем результаты с очень низкой схожестью
                filtered_results = [r for r in results if r['similarity'] >= 0.2]  # Понижен с 0.3 до 0.2
                if len(filtered_results) >= top_k:
                    return filtered_results[:top_k]
                return results[:top_k]
        
        # Если ничего не нашли с высокими порогами, пробуем с самым низким
        return self.search_similar_products(image_path_or_url, top_k=top_k, min_similarity=0.05)  # Очень низкий порог
    
    def get_product_by_id(self, item_id):
        """Получение товара по ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT item_id, url, picture FROM products WHERE item_id = ?', (item_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return {
                'item_id': row[0],
                'url': row[1],
                'picture': row[2]
            }
        return None
    
    def get_database_stats(self):
        """Получение статистики БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM products')
        total_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM products WHERE vector IS NOT NULL')
        with_vectors = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_products': total_count,
            'products_with_vectors': with_vectors
        }
    
    def search_with_stability_check(self, image_path_or_url, top_k=5):
        """Поиск с проверкой стабильности результатов"""
        # Делаем поиск несколько раз
        all_results = []
        
        for attempt in range(3):
            results = self.search_with_multiple_thresholds(image_path_or_url, top_k=top_k)
            if results:
                all_results.append(results)
        
        if not all_results:
            return []
        
        # Находим товары, которые стабильно появляются в результатах
        stable_items = {}
        for results in all_results:
            for item in results:
                item_id = item['item_id']
                if item_id not in stable_items:
                    stable_items[item_id] = {
                        'count': 0,
                        'similarities': [],
                        'item': item
                    }
                stable_items[item_id]['count'] += 1
                stable_items[item_id]['similarities'].append(item['similarity'])
        
        # Еще больше снижаем требования для стабильности
        stable_results = []
        for item_id, data in stable_items.items():
            if data['count'] >= 1:  # Появляется как минимум в 1 из 3 поисков
                # Берем среднюю схожесть
                avg_similarity = np.mean(data['similarities'])
                if avg_similarity >= 0.2:  # Понижен порог с 0.35 до 0.2 для максимального поиска
                    item = data['item'].copy()
                    item['similarity'] = avg_similarity
                    item['stability'] = data['count'] / len(all_results)
                    stable_results.append(item)
        
        # Сортируем по средней схожести
        stable_results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return stable_results[:top_k]
    
    def aggressive_search(self, image_path_or_url, top_k=10):
        """Максимально агрессивный поиск - возвращает результаты с любой схожестью"""
        query_vector = self.get_image_features(image_path_or_url)
        if query_vector is None:
            print("Не удалось извлечь признаки из изображения")
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем все товары
        cursor.execute('SELECT item_id, url, picture, vector FROM products ORDER BY item_id')
        rows = cursor.fetchall()
        
        similarities = []
        
        for row in rows:
            item_id, url, picture, vector_blob = row
            
            # Восстанавливаем вектор из БД
            db_vector = np.frombuffer(vector_blob, dtype=np.float32)
            
            # Вычисляем косинусное сходство
            similarity = self.cosine_similarity(query_vector, db_vector)
            
            # Добавляем ВСЕ результаты без фильтрации
            similarities.append({
                'item_id': item_id,
                'url': url,
                'picture': picture,
                'similarity': float(similarity)
            })
        
        # Сортируем по убыванию схожести
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        conn.close()
        
        # Выводим диагностику лучших результатов
        print(f"Агрессивный поиск нашел {len(similarities)} товаров")
        if similarities:
            print(f"Лучшая схожесть: {similarities[0]['similarity']:.4f}")
            print(f"Топ-5 схожестей: {[r['similarity'] for r in similarities[:5]]}")
        
        return similarities[:top_k] 