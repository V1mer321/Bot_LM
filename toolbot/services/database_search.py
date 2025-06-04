"""
Сервис для поиска товаров по базе данных items
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

logger = logging.getLogger(__name__)

class DatabaseImageSearchService:
    """
    Сервис для поиска похожих товаров в базе данных items
    """
    
    def __init__(self, db_path: str = "data/items.db"):
        self.db_path = db_path
        self.clip_model = None
        self.clip_processor = None
        self.faiss_index = None
        self.item_mapping = {}  # mapping: faiss_index -> item_id
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
            logger.info("✅ DatabaseImageSearchService успешно инициализирован")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при инициализации DatabaseImageSearchService: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _load_vectors_from_db(self):
        """
        Загружает векторы из базы данных и создает FAISS индекс
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
                    if len(vector) == 512:  # Проверяем размерность
                        vectors.append(vector)
                        item_ids.append(item_id)
                    else:
                        logger.warning(f"Неверная размерность вектора для ЛМ товара {item_id}: {len(vector)}")
            
            if not vectors:
                logger.error("Не найдено векторов правильной размерности")
                return False
            
            # Создаем FAISS индекс
            vectors_array = np.array(vectors, dtype=np.float32)
            
            # НЕ нормализуем векторы из БД, так как они уже в правильном формате
            # Используем косинусное расстояние через IndexFlatIP с ручной нормализацией только запросов
            dimension = vectors_array.shape[1]
            
            # Для косинусного сходства нормализуем ВСЕ векторы одинаково
            logger.info("Нормализуем векторы для косинусного сходства...")
            faiss.normalize_L2(vectors_array)  # Нормализуем векторы из БД
            
            self.faiss_index = faiss.IndexFlatIP(dimension)
            self.faiss_index.add(vectors_array)
            
            # Создаем маппинг индексов FAISS к ЛМ товара
            self.item_mapping = {i: item_id for i, item_id in enumerate(item_ids)}
            
            logger.info(f"✅ FAISS индекс создан: {len(vectors)} векторов, размерность {dimension}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке векторов из базы данных: {e}")
            raise
    
    def extract_features_from_image(self, image_path: str) -> Optional[np.ndarray]:
        """
        Извлекает признаки из изображения с помощью CLIP
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            Вектор признаков или None в случае ошибки
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
            
            # НЕ нормализуем здесь - оставляем как в исходном формате CLIP
            # Нормализация будет происходить только перед поиском
            
            # Конвертируем в numpy
            features = image_features.cpu().numpy().astype('float32')
            
            return features.reshape(-1)
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении признаков из {image_path}: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def search_similar_items(self, image_path: str, top_k: int = 5) -> List[Tuple[str, str, float]]:
        """
        Ищет похожие товары по изображению
        
        Args:
            image_path: Путь к изображению
            top_k: Количество результатов
            
        Returns:
            Список кортежей (лм_товара, image_url, similarity)
        """
        try:
            if not self.initialized:
                logger.error("Сервис не инициализирован")
                return []
            
            # Извлекаем признаки из изображения
            features = self.extract_features_from_image(image_path)
            if features is None:
                return []
            
            # Нормализуем ТОЛЬКО вектор запроса для консистентности с БД
            query_features = features.reshape(1, -1).astype(np.float32)
            faiss.normalize_L2(query_features)
            
            # Выполняем поиск
            similarities, indices = self.faiss_index.search(query_features, top_k)
            
            # Подготавливаем результаты
            results = []
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for idx, (similarity, faiss_idx) in enumerate(zip(similarities[0], indices[0])):
                if faiss_idx != -1 and faiss_idx in self.item_mapping:
                    item_id = self.item_mapping[faiss_idx]
                    
                    # Получаем URL изображения
                    cursor.execute("SELECT image_url FROM items WHERE item_id = ?", (item_id,))
                    row = cursor.fetchone()
                    
                    if row and row[0]:
                        image_url = row[0]
                        # Ограничиваем similarity значениями от 0 до 1
                        clamped_similarity = max(0.0, min(1.0, float(similarity)))
                        results.append((item_id, image_url, clamped_similarity))
                        logger.debug(f"Найден товар ЛМ{item_id} с похожестью {clamped_similarity:.3f}")
            
            conn.close()
            logger.info(f"Найдено {len(results)} похожих товаров")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при поиске похожих товаров: {e}")
            return []
    
    def get_item_info(self, item_id: int) -> Optional[Tuple[str]]:
        """
        Получает информацию о товаре по ID
        
        Args:
            item_id: ID товара
            
        Returns:
            Кортеж с информацией о товаре или None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT image_url FROM items WHERE item_id = ?", (item_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            return row
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о товаре {item_id}: {e}")
            return None

# Глобальный экземпляр сервиса (Singleton)
_database_search_service = None

def get_database_search_service() -> DatabaseImageSearchService:
    """
    Получает глобальный экземпляр сервиса поиска по базе данных
    """
    global _database_search_service
    
    if _database_search_service is None:
        _database_search_service = DatabaseImageSearchService()
        
    return _database_search_service

def initialize_database_search() -> bool:
    """
    Инициализирует сервис поиска по базе данных
    """
    service = get_database_search_service()
    return service.initialize()

def search_items_by_image(image_path: str, top_k: int = 5) -> List[Tuple[str, str, float]]:
    """
    Ищет товары по изображению
    
    Args:
        image_path: Путь к изображению
        top_k: Количество результатов
        
    Returns:
        Список кортежей (лм_товара, image_url, similarity)
    """
    service = get_database_search_service()
    return service.search_similar_items(image_path, top_k) 