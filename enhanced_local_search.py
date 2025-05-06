#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Улучшенный модуль локального поиска изображений без Cloudinary
Использует существующие компоненты (PyTorch, FAISS, OpenCV) без дополнительных зависимостей
"""

import os
import logging
import numpy as np
import cv2
from pathlib import Path
import pickle
import uuid
import torch
from torchvision import transforms, models
from PIL import Image, ImageEnhance
import faiss
import time

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные для моделей
enhanced_model = None
enhanced_feature_extractor = None
enhanced_faiss_index = None
enhanced_label_encoder = None

def initialize_enhanced_search():
    """Инициализация улучшенного поиска изображений"""
    global enhanced_model, enhanced_feature_extractor, enhanced_faiss_index, enhanced_label_encoder
    
    try:
        # Загружаем предобученную ResNet50 (вместо ResNet18 для лучшего качества)
        enhanced_model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
        # Удаляем последний слой
        enhanced_model = torch.nn.Sequential(*(list(enhanced_model.children())[:-1]))
        enhanced_model.eval()
        
        # Создаем улучшенный преобразователь для изображений
        enhanced_feature_extractor = transforms.Compose([
            transforms.Resize((256, 256)),  # Увеличенное разрешение
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                std=[0.229, 0.224, 0.225])
        ])
        
        # Создаем индекс FAISS
        feature_dim = 2048  # Размерность выхода предпоследнего слоя ResNet50
        enhanced_faiss_index = faiss.IndexFlatL2(feature_dim)
        
        # Загружаем существующий индекс если есть
        if os.path.exists('enhanced_index.pkl'):
            try:
                with open('enhanced_index.pkl', 'rb') as f:
                    saved_data = pickle.load(f)
                    enhanced_faiss_index = saved_data['index']
                    enhanced_label_encoder = saved_data['labels']
                logger.info(f"Загружен существующий индекс с {enhanced_faiss_index.ntotal} изображениями")
            except Exception as e:
                logger.error(f"Ошибка при загрузке индекса: {e}")
                # Создаем новый индекс
                enhanced_faiss_index = faiss.IndexFlatL2(feature_dim)
                enhanced_label_encoder = []
        else:
            enhanced_label_encoder = []
        
        logger.info("✅ Улучшенная модель поиска изображений успешно инициализирована")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации улучшенной модели: {e}")
        import traceback
        logger.error(f"Детали ошибки: {traceback.format_exc()}")
        return False

def enhanced_extract_features(image_path):
    """Улучшенное извлечение признаков из изображения"""
    global enhanced_model, enhanced_feature_extractor
    
    try:
        # Загружаем изображение с помощью OpenCV для предобработки
        cv_img = cv2.imread(str(image_path))
        if cv_img is None:
            logger.error(f"Не удалось загрузить изображение с помощью OpenCV: {image_path}")
            return None
        
        logger.info(f"Извлечение улучшенных признаков из: {os.path.basename(image_path)}")
        
        # Создаем копию для обработки
        enhanced_img = cv_img.copy()
        
        # Преобразуем в RGB для корректной передачи в модель
        enhanced_img = cv2.cvtColor(enhanced_img, cv2.COLOR_BGR2RGB)
        
        # Применяем улучшенную обработку изображения
        # 1. Автоматическая коррекция яркости и контрастности
        gray = cv2.cvtColor(enhanced_img, cv2.COLOR_RGB2GRAY)
        min_val, max_val, _, _ = cv2.minMaxLoc(gray)
        
        # Если изображение слишком темное или слишком светлое - корректируем
        if max_val - min_val < 100:  # Низкий контраст
            enhanced_img = cv2.convertScaleAbs(enhanced_img, alpha=1.5, beta=10)
        
        # 2. Улучшение резкости
        kernel = np.array([[-1,-1,-1], 
                           [-1, 9,-1],
                           [-1,-1,-1]])
        enhanced_img = cv2.filter2D(enhanced_img, -1, kernel)
        
        # 3. Преобразование для дальнейшей обработки через PIL
        pil_img = Image.fromarray(enhanced_img)
        
        # 4. Дополнительные улучшения с помощью PIL
        enhancer = ImageEnhance.Contrast(pil_img)
        pil_img = enhancer.enhance(1.2)
        
        enhancer = ImageEnhance.Sharpness(pil_img)
        pil_img = enhancer.enhance(1.3)
        
        enhancer = ImageEnhance.Color(pil_img)
        pil_img = enhancer.enhance(1.2)
        
        # 5. Извлекаем векторы признаков из базового и улучшенного изображений
        tensor = enhanced_feature_extractor(pil_img).unsqueeze(0)
        
        with torch.no_grad():
            features = enhanced_model(tensor).squeeze().cpu().numpy()
            
            # Нормализуем вектор признаков
            features = features / np.linalg.norm(features)
        
        return features
        
    except Exception as e:
        logger.error(f"❌ Ошибка при извлечении признаков: {e}")
        import traceback
        logger.error(f"Детали ошибки: {traceback.format_exc()}")
        return None

def update_enhanced_index(folder_path):
    """Обновление индекса изображений с улучшенным извлечением признаков"""
    global enhanced_faiss_index, enhanced_label_encoder
    
    try:
        # Проверяем инициализацию
        if enhanced_model is None or enhanced_feature_extractor is None:
            if not initialize_enhanced_search():
                return False
        
        features_list = []
        paths_list = []
        
        # Собираем все изображения, включая подкаталоги
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png']:
            image_files.extend(list(Path(folder_path).glob(f'**/{ext}')))
        
        logger.info(f"Найдено {len(image_files)} изображений для улучшенного индексирования")
        
        # Индексируем изображения
        for idx, img_path in enumerate(image_files):
            if idx % 10 == 0:
                logger.info(f"Обработано {idx}/{len(image_files)} изображений")
                
            features = enhanced_extract_features(str(img_path))
            if features is not None:
                features_list.append(features)
                paths_list.append(str(img_path))
        
        # Обновляем индекс
        if features_list:
            features_array = np.array(features_list).astype('float32')
            
            # Создаем новый индекс
            feature_dim = features_array.shape[1]
            new_index = faiss.IndexFlatL2(feature_dim)
            new_index.add(features_array)
            
            enhanced_faiss_index = new_index
            enhanced_label_encoder = paths_list
            
            # Сохраняем индекс
            with open('enhanced_index.pkl', 'wb') as f:
                pickle.dump({
                    'index': enhanced_faiss_index,
                    'labels': enhanced_label_encoder
                }, f)
            
            logger.info(f"✅ Улучшенный индекс обновлен, добавлено {len(features_list)} изображений")
            return True
        else:
            logger.error("Не удалось извлечь признаки ни из одного изображения")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении улучшенного индекса: {e}")
        import traceback
        logger.error(f"Детали ошибки: {traceback.format_exc()}")
        return False

def enhanced_find_similar_images(query_image_path, top_n=5, similarity_threshold=0.2):
    """Улучшенный поиск похожих изображений"""
    global enhanced_faiss_index, enhanced_label_encoder
    
    try:
        # Проверяем инициализацию
        if enhanced_model is None or enhanced_feature_extractor is None:
            if not initialize_enhanced_search():
                logger.error("Не удалось инициализировать улучшенный поиск")
                return []
        
        # Проверяем наличие индекса
        if enhanced_faiss_index is None or enhanced_faiss_index.ntotal == 0:
            logger.error("Улучшенный индекс не инициализирован или пуст")
            return []
                
        # Извлекаем признаки из запроса
        query_features = enhanced_extract_features(query_image_path)
        if query_features is None:
            logger.error("Не удалось извлечь признаки из запроса")
            return []
        
        # Пытаемся определить бренд запроса для улучшения результатов
        from Bot_ebet import detect_brand_by_color, detect_brand_from_filename
        
        query_brand = detect_brand_by_color(query_image_path)
        logger.info(f"Определенный бренд запроса: {query_brand}")
        
        # Также определяем бренд по имени файла (если возможно)
        filename_brand = detect_brand_from_filename(query_image_path)
        if filename_brand != "Неизвестный" and query_brand is None:
            query_brand = filename_brand
            logger.info(f"Бренд определен по имени файла: {query_brand}")
        
        # Ищем похожие изображения
        query_features = query_features.astype('float32').reshape(1, -1)
        distances, indices = enhanced_faiss_index.search(
            query_features,
            min(top_n * 4, enhanced_faiss_index.ntotal)  # Берем больше результатов для фильтрации
        )
        
        # Подготовка результатов с корректировкой по бренду
        results = []
        processed_brands = set()  # Для отслеживания брендов
        
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(enhanced_label_encoder):
                image_path = enhanced_label_encoder[idx]
                
                # Базовая схожесть
                similarity = 1.0 / (1.0 + dist)
                
                # Определяем бренд найденного изображения
                result_brand = detect_brand_by_color(image_path)
                
                # Если не удалось определить по цвету, пробуем по имени файла
                if result_brand is None:
                    result_brand = detect_brand_from_filename(image_path)
                    if result_brand != "Неизвестный":
                        logger.info(f"Бренд результата определен по имени файла: {result_brand}")
                
                # Корректируем схожесть в зависимости от бренда
                if similarity >= similarity_threshold:
                    # Если у исходного запроса определен бренд
                    brand_adjusted_similarity = similarity
                    
                    if query_brand:
                        if result_brand == query_brand:
                            # Если бренды совпадают - повышаем схожесть
                            brand_adjusted_similarity = similarity * 1.8
                            logger.info(f"Корректировка схожести для совпадающего бренда {query_brand}: {brand_adjusted_similarity:.3f}")
                        elif query_brand == "Makita" and result_brand == "Dexter":
                            # Если запрос Makita, а результат Dexter - снижаем схожесть
                            brand_adjusted_similarity = similarity * 0.3
                        elif query_brand == "Dexter" and result_brand == "Makita":
                            # Если запрос Dexter, а результат Makita - снижаем схожесть
                            brand_adjusted_similarity = similarity * 0.3
                        elif query_brand == "Makita" and result_brand == "Интерскол":
                            # Makita и Интерскол тоже часто путаются
                            brand_adjusted_similarity = similarity * 0.4
                        elif query_brand == "Интерскол" and result_brand == "Makita":
                            brand_adjusted_similarity = similarity * 0.4
                        elif query_brand != result_brand and result_brand is not None:
                            # Разные бренды - снижаем схожесть
                            brand_adjusted_similarity = similarity * 0.6
                    
                    # Ограничиваем значение схожести до 1.0 (100%)
                    brand_adjusted_similarity = min(brand_adjusted_similarity, 1.0)
                    
                    # Применяем разнообразие брендов
                    if result_brand in processed_brands and result_brand is not None:
                        brand_adjusted_similarity *= 0.92
                    
                    # Добавляем в результаты
                    results.append((image_path, brand_adjusted_similarity))
                    
                    # Отмечаем бренд как обработанный
                    if result_brand is not None:
                        processed_brands.add(result_brand)
        
        # Сортируем по скорректированной схожести
        results = sorted(results, key=lambda x: x[1], reverse=True)
        
        # Берем топ-N результатов
        return results[:top_n]
        
    except Exception as e:
        logger.error(f"❌ Ошибка при поиске изображений: {e}")
        import traceback
        logger.error(f"Детали ошибки: {traceback.format_exc()}")
        return []

def patch_bot_module():
    """Полностью заменяет Cloudinary на улучшенный локальный поиск"""
    try:
        import Bot_ebet
        
        # Отключаем Cloudinary
        Bot_ebet.use_cloudinary = False
        
        # Заменяем функцию инициализации Cloudinary
        def mock_initialize_cloudinary():
            logger.info("Cloudinary отключен, используется улучшенный локальный поиск")
            return False
        
        # Заменяем поиск через Cloudinary нашим улучшенным поиском
        def mock_search_cloudinary(image_path, max_results=5, folder=None):
            logger.info("Используем улучшенный локальный поиск вместо Cloudinary")
            return enhanced_find_similar_images(image_path, top_n=max_results)
        
        # Применяем патчи
        Bot_ebet.initialize_cloudinary = mock_initialize_cloudinary
        Bot_ebet.search_similar_images_cloudinary = mock_search_cloudinary
        
        # Инициализируем улучшенный поиск
        if not initialize_enhanced_search():
            logger.warning("⚠️ Не удалось инициализировать улучшенный поиск")
            return False
        
        logger.info("✅ Бот успешно настроен для использования улучшенного локального поиска")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при модификации модуля бота: {e}")
        import traceback
        logger.error(f"Детали ошибки: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    # Тестирование модуля
    print("Инициализация улучшенного поиска...")
    initialize_enhanced_search()
    
    # Индексация тестовой директории
    test_dir = "sample_images"
    if os.path.exists(test_dir):
        print(f"Индексация изображений в {test_dir}...")
        update_enhanced_index(test_dir)
    else:
        print(f"Директория {test_dir} не существует.") 