"""
Улучшенный сервис для поиска товаров по базе данных items с гибридным подходом
"""
import os
import sqlite3
import logging
import numpy as np
import faiss
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
import tempfile
import requests
from typing import List, Tuple, Optional
import traceback
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

class ImprovedDatabaseImageSearchService:
    """
    Улучшенный сервис для поиска похожих товаров в базе данных items
    """
    
    def __init__(self, db_path: str = "data/items.db"):
        self.db_path = db_path
        self.clip_model = None
        self.clip_processor = None
        self.faiss_index_cosine = None
        self.faiss_index_euclidean = None
        self.item_mapping = {}
        self.vectors_normalized = None
        self.vectors_raw = None
        self.initialized = False
        
    def initialize(self) -> bool:
        """
        Инициализация CLIP модели и загрузка векторов из базы данных
        """
        try:
            # Инициализация CLIP модели
            logger.info("Загружаем CLIP модель...")
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            
            # Проверяем доступность GPU
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.clip_model.to(device)
            logger.info(f"CLIP модель загружена на устройство: {device}")
            
            # Загружаем векторы из базы данных
            self._load_vectors_from_db()
            
            self.initialized = True
            logger.info("✅ ImprovedDatabaseImageSearchService успешно инициализирован")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при инициализации ImprovedDatabaseImageSearchService: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _load_vectors_from_db(self):
        """
        Загружает векторы из базы данных и создает множественные FAISS индексы
        """
        try:
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"База данных не найдена: {self.db_path}")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            logger.info("Загружаем векторы из базы данных...")
            cursor.execute("SELECT item_id, vector FROM items WHERE vector IS NOT NULL")
            rows = cursor.fetchall()
            
            if not rows:
                logger.error("Не найдено товаров с векторами в базе данных")
                return False
            
            logger.info(f"Найдено {len(rows)} товаров с векторами")
            
            # Загружаем векторы
            vectors = []
            item_ids = []
            
            for item_id, vector_blob in rows:
                if vector_blob:
                    vector = np.frombuffer(vector_blob, dtype=np.float32)
                    if len(vector) == 512:
                        vectors.append(vector)
                        item_ids.append(item_id)
                    else:
                        logger.warning(f"Неверная размерность вектора для ЛМ товара {item_id}: {len(vector)}")
            
            if not vectors:
                logger.error("Не найдено векторов правильной размерности")
                return False
            
            # Создаем векторные массивы
            self.vectors_raw = np.array(vectors, dtype=np.float32)
            self.vectors_normalized = self.vectors_raw.copy()
            faiss.normalize_L2(self.vectors_normalized)
            
            dimension = self.vectors_raw.shape[1]
            
            # Создаем индекс для косинусного сходства (нормализованные векторы)
            logger.info("Создаем индекс для косинусного сходства...")
            self.faiss_index_cosine = faiss.IndexFlatIP(dimension)
            self.faiss_index_cosine.add(self.vectors_normalized)
            
            # Создаем индекс для евклидова расстояния (сырые векторы)
            logger.info("Создаем индекс для евклидова расстояния...")
            self.faiss_index_euclidean = faiss.IndexFlatL2(dimension)
            self.faiss_index_euclidean.add(self.vectors_raw)
            
            # Создаем маппинг индексов к ЛМ товара
            self.item_mapping = {i: item_id for i, item_id in enumerate(item_ids)}
            
            logger.info(f"✅ FAISS индексы созданы: {len(vectors)} векторов, размерность {dimension}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке векторов из базы данных: {e}")
            raise
    
    def extract_features_from_image(self, image_path: str) -> Optional[np.ndarray]:
        """
        Извлекает признаки из изображения с помощью CLIP
        """
        try:
            if not self.initialized:
                logger.error("Сервис не инициализирован")
                return None
            
            # Загружаем изображение
            image = Image.open(image_path).convert('RGB')
            
            # Обрабатываем изображение
            inputs = self.clip_processor(images=image, return_tensors="pt")
            
            # Переносим на нужное устройство
            device = next(self.clip_model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            # Извлекаем признаки
            with torch.no_grad():
                image_features = self.clip_model.get_image_features(**inputs)
            
            # Конвертируем в numpy
            features = image_features.cpu().numpy().astype('float32')
            
            return features.reshape(-1)
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении признаков из {image_path}: {e}")
            return None

    def search_similar_items(self, image_path: str, top_k: int = 5) -> List[Tuple[str, str, float]]:
        """
        Ищет похожие товары по изображению используя гибридный подход
        """
        try:
            if not self.initialized:
                logger.error("Сервис не инициализирован")
                return []
            
            # Извлекаем признаки из изображения
            features = self.extract_features_from_image(image_path)
            if features is None:
                return []
            
            # Подготавливаем векторы запроса
            query_raw = features.reshape(1, -1).astype(np.float32)
            query_normalized = query_raw.copy()
            faiss.normalize_L2(query_normalized)
            
            # Метод 1: Косинусное сходство
            similarities_cosine, indices_cosine = self.faiss_index_cosine.search(query_normalized, top_k * 2)
            
            # Метод 2: Евклидово расстояние
            distances_euclidean, indices_euclidean = self.faiss_index_euclidean.search(query_raw, top_k * 2)
            
            # Метод 3: Прямое вычисление косинусного сходства с сырыми векторами
            cosine_similarities = []
            for i, vector in enumerate(self.vectors_raw):
                cos_sim = np.dot(query_raw[0], vector) / (np.linalg.norm(query_raw[0]) * np.linalg.norm(vector))
                cosine_similarities.append((cos_sim, i))
            
            cosine_similarities.sort(key=lambda x: x[0], reverse=True)
            top_cosine_indices = [idx for _, idx in cosine_similarities[:top_k * 2]]
            
            # Объединяем результаты всех методов
            combined_scores = {}
            
            # Добавляем оценки от косинусного сходства (FAISS)
            for rank, (similarity, idx) in enumerate(zip(similarities_cosine[0], indices_cosine[0])):
                if idx != -1 and idx in self.item_mapping:
                    item_id = self.item_mapping[idx]
                    score = similarity * 100
                    rank_bonus = (top_k * 2 - rank) / (top_k * 2) * 10  # Бонус за ранг
                    combined_scores[item_id] = combined_scores.get(item_id, 0) + score + rank_bonus
            
            # Добавляем оценки от евклидова расстояния
            max_distance = max(distances_euclidean[0]) if len(distances_euclidean[0]) > 0 else 1.0
            for rank, (distance, idx) in enumerate(zip(distances_euclidean[0], indices_euclidean[0])):
                if idx != -1 and idx in self.item_mapping:
                    item_id = self.item_mapping[idx]
                    # Конвертируем расстояние в схожесть
                    score = max(0, (1 - distance / max_distance)) * 100
                    rank_bonus = (top_k * 2 - rank) / (top_k * 2) * 10
                    combined_scores[item_id] = combined_scores.get(item_id, 0) + score + rank_bonus
            
            # Добавляем оценки от прямого косинусного сходства
            for rank, idx in enumerate(top_cosine_indices):
                if idx in self.item_mapping:
                    item_id = self.item_mapping[idx]
                    cos_sim, _ = cosine_similarities[rank]
                    score = max(0, cos_sim * 100)
                    rank_bonus = (top_k * 2 - rank) / (top_k * 2) * 10
                    combined_scores[item_id] = combined_scores.get(item_id, 0) + score + rank_bonus
            
            # Сортируем по итоговой оценке
            sorted_results = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Подготавливаем финальные результаты
            results = []
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for item_id, score in sorted_results[:top_k]:
                cursor.execute("SELECT image_url FROM items WHERE item_id = ?", (item_id,))
                row = cursor.fetchone()
                
                if row and row[0]:
                    image_url = row[0]
                    # Нормализуем итоговую оценку к диапазону 0-1
                    normalized_score = min(1.0, max(0.0, score / 200.0))  # Делим на 200, так как у нас 3 метода
                    results.append((item_id, image_url, normalized_score))
                    logger.debug(f"Найден товар ЛМ{item_id} с итоговой оценкой {normalized_score:.3f}")
            
            conn.close()
            logger.info(f"Найдено {len(results)} похожих товаров (гибридный поиск)")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при поиске похожих товаров: {e}")
            return []

# Глобальный экземпляр улучшенного сервиса
_improved_database_search_service = None

def get_improved_database_search_service() -> ImprovedDatabaseImageSearchService:
    """
    Получает глобальный экземпляр улучшенного сервиса поиска
    """
    global _improved_database_search_service
    
    if _improved_database_search_service is None:
        _improved_database_search_service = ImprovedDatabaseImageSearchService()
        
    return _improved_database_search_service

def initialize_improved_database_search() -> bool:
    """
    Инициализирует улучшенный сервис поиска по базе данных
    """
    service = get_improved_database_search_service()
    return service.initialize()

def search_items_by_image_improved(image_path: str, top_k: int = 5) -> List[Tuple[str, str, float]]:
    """
    Ищет товары по изображению используя улучшенный алгоритм
    """
    service = get_improved_database_search_service()
    return service.search_similar_items(image_path, top_k) 