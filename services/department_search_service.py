import sqlite3
import numpy as np
import torch
from PIL import Image, ImageEnhance, ImageOps
import requests
from io import BytesIO

class DepartmentSearchService:
    def __init__(self, db_path='data/unified_products.db'):
        self.db_path = db_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Ленивая инициализация - модель загружается только при первом использовании
        self.model = None
        self.preprocess = None
        # Порог схожести для фильтрации результатов
        self.similarity_threshold = 0.2
        
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
    
    def get_available_departments(self):
        """Получение списка доступных отделов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT department 
            FROM products 
            WHERE department IS NOT NULL AND department != 'nan'
            ORDER BY department
        """)
        departments = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return departments
    
    def search_by_department_and_image(self, image_path_or_url, department=None, top_k=5, min_similarity=None):
        """Поиск похожих товаров по изображению с фильтрацией по отделу"""
        query_vector = self.get_image_features(image_path_or_url)
        if query_vector is None:
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Формируем SQL запрос с учетом фильтра по отделу
        if department and department.upper() != 'ВСЕ':
            cursor.execute("""
                SELECT item_id, url, picture, vector, department, product_name 
                FROM products 
                WHERE department = ? AND vector IS NOT NULL
                ORDER BY item_id
            """, (department.upper(),))
        else:
            cursor.execute("""
                SELECT item_id, url, picture, vector, department, product_name 
                FROM products 
                WHERE vector IS NOT NULL
                ORDER BY item_id
            """)
        
        rows = cursor.fetchall()
        
        similarities = []
        
        # Понижаем минимальный порог схожести для лучшего поиска
        threshold = min_similarity if min_similarity is not None else 0.1
        
        for row in rows:
            item_id, url, picture, vector_blob, dept, product_name = row
            
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
                    'department': dept,
                    'product_name': product_name,
                    'similarity': float(similarity)
                })
        
        # Сортируем по убыванию схожести
        similarities.sort(key=lambda x: (-x['similarity'], x['item_id']))
        
        conn.close()
        return similarities[:top_k]
    
    def search_with_multiple_thresholds_by_department(self, image_path_or_url, department=None, top_k=5):
        """Поиск с несколькими порогами для лучшего качества результатов с фильтром по отделу"""
        thresholds = [0.5, 0.4, 0.3, 0.25, 0.2, 0.15, 0.1]
        
        for threshold in thresholds:
            results = self.search_by_department_and_image(
                image_path_or_url, 
                department=department, 
                top_k=top_k*2, 
                min_similarity=threshold
            )
            if len(results) >= top_k:
                # Дополнительная фильтрация: убираем результаты с очень низкой схожестью
                filtered_results = [r for r in results if r['similarity'] >= 0.2]
                if len(filtered_results) >= top_k:
                    return filtered_results[:top_k]
                return results[:top_k]
        
        # Если ничего не нашли с высокими порогами, пробуем с самым низким
        return self.search_by_department_and_image(
            image_path_or_url, 
            department=department, 
            top_k=top_k, 
            min_similarity=0.05
        )
    
    def get_department_stats(self):
        """Получение статистики по отделам"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT department, COUNT(*) as count
            FROM products 
            WHERE department IS NOT NULL AND department != 'nan'
            GROUP BY department
            ORDER BY count DESC
        """)
        
        stats = {}
        for row in cursor.fetchall():
            stats[row[0]] = row[1]
        
        conn.close()
        return stats
    
    def search_text_by_department(self, search_text, department=None, top_k=10):
        """Текстовый поиск по отделу (по URL товара и названию)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        search_pattern = f"%{search_text.lower()}%"
        
        if department and department.upper() != 'ВСЕ':
            cursor.execute("""
                SELECT item_id, url, picture, department, product_name
                FROM products 
                WHERE department = ? AND (LOWER(url) LIKE ? OR LOWER(product_name) LIKE ?)
                ORDER BY item_id
                LIMIT ?
            """, (department.upper(), search_pattern, search_pattern, top_k))
        else:
            cursor.execute("""
                SELECT item_id, url, picture, department, product_name
                FROM products 
                WHERE LOWER(url) LIKE ? OR LOWER(product_name) LIKE ?
                ORDER BY item_id
                LIMIT ?
            """, (search_pattern, search_pattern, top_k))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'item_id': row[0],
                'url': row[1],
                'picture': row[2],
                'department': row[3],
                'product_name': row[4]
            })
        
        conn.close()
        return results 