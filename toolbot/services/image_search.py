"""
Сервис для поиска и анализа изображений.
"""
import os
import cv2
import uuid
import logging
import numpy as np
import faiss
import traceback
import threading
from PIL import Image, ImageEnhance, ImageFilter
import torch
from transformers import CLIPProcessor, CLIPModel

from toolbot.utils.object_detection import detect_objects_on_image as detect_objects
from toolbot.config import get_similarity_threshold, get_top_n_results, get_image_variation_weights, get_similarity_bonuses
from toolbot.utils.cache_manager import get_cached_search_results, cache_search_results
from toolbot.utils.model_optimizer import optimize_clip_model
from toolbot.utils.brand_recognition import recognize_brand, get_known_brands
from toolbot.utils.image_utils import preprocess_image_for_search
from toolbot.utils.clip_fine_tuner import get_clip_fine_tuner

logger = logging.getLogger(__name__)


class ImageSearchService:
    """
    Сервис для поиска и анализа изображений с использованием модели CLIP.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """
        Получение экземпляра сервиса (шаблон Singleton).
        
        Returns:
            Экземпляр ImageSearchService
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """
        Инициализация сервиса поиска изображений.
        """
        self.clip_model = None
        self.clip_processor = None
        self.faiss_index = None
        self.path_mapping = {}
        self.text_features_cache = {}
        self.fine_tuned_model = None
        self.use_fine_tuned = False
        
    def initialize_model(self, use_fine_tuned=False):
        """
        Инициализирует модели для поиска изображений
        
        Args:
            use_fine_tuned: Использовать ли тонко настроенную модель CLIP (если доступна)
            
        Returns:
            True если инициализация успешна, иначе False
        """
        try:
            logger.info("Инициализация моделей для поиска изображений...")
            
            # Проверяем наличие тонко настроенной модели
            models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "clip_fine_tuned")
            if use_fine_tuned and os.path.exists(models_dir):
                # Используем тонко настроенную модель
                logger.info("Загружаем тонко настроенную модель CLIP...")
                clip_tuner = get_clip_fine_tuner()
                if clip_tuner.load_fine_tuned_model(models_dir):
                    self.clip_model = clip_tuner.model
                    self.clip_processor = clip_tuner.processor
                    self.fine_tuned_model = True
                    self.use_fine_tuned = True
                    logger.info("✓ Тонко настроенная модель CLIP успешно загружена")
                else:
                    logger.warning("Не удалось загрузить тонко настроенную модель, используем стандартную")
                    self.load_standard_clip_model()
            else:
                # Используем стандартную модель
                self.load_standard_clip_model()
            
            logger.info("Модели успешно инициализированы")
            return True
        except Exception as e:
            logger.error(f"Ошибка при инициализации моделей: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def load_standard_clip_model(self):
        """
        Загружает стандартную модель CLIP
        
        Returns:
            True если загрузка успешна, иначе False
        """
        try:
            logger.info("Загружаем стандартную модель CLIP...")
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            
            # Оптимизируем модель для более быстрой работы
            self.clip_model = optimize_clip_model(clip_model, optimization_type='quantization')
            self.fine_tuned_model = False
            self.use_fine_tuned = False
            
            logger.info("✓ Стандартная модель CLIP успешно загружена")
            return True
        except Exception as e:
            logger.error(f"Ошибка при загрузке стандартной модели CLIP: {e}")
            return False
            
    def extract_features(self, image_path):
        """
        Извлекает признаки из изображения с помощью CLIP
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            Вектор признаков или None в случае ошибки
        """
        try:
            # Проверяем инициализацию модели
            if self.clip_model is None or self.clip_processor is None:
                if not self.initialize_model():
                    logger.error("Не удалось инициализировать модели")
                    return None
            
            # Предобработка изображения для улучшения распознавания
            enhanced_image_path = preprocess_image_for_search(image_path)
            
            # Используем улучшенное изображение если доступно, иначе оригинальное
            img_path = enhanced_image_path if enhanced_image_path else image_path
            
            # Загружаем и обрабатываем изображение
            image = Image.open(img_path).convert('RGB')
            inputs = self.clip_processor(images=image, return_tensors="pt")
            
            # Извлекаем признаки
            with torch.no_grad():
                image_features = self.clip_model.get_image_features(**inputs)
                
            # Нормализуем вектор признаков
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            # Преобразуем в numpy массив
            features = image_features.cpu().numpy().astype('float32')
            
            return features.reshape(1, -1)[0]
        except Exception as e:
            logger.error(f"Ошибка при извлечении признаков из {image_path}: {e}")
            logger.error(traceback.format_exc())
            return None
            
    def update_image_index(self, folder_path):
        """
        Обновляет индекс изображений для быстрого поиска
        
        Args:
            folder_path: Путь к папке с изображениями
            
        Returns:
            True если индекс успешно обновлен, иначе False
        """
        try:
            logger.info(f"Обновление индекса изображений из папки: {folder_path}")
            
            # Очищаем текущий маппинг путей
            self.path_mapping = {}
            
            # Собираем все изображения
            image_paths = []
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        image_paths.append(os.path.join(root, file))
            
            logger.info(f"Найдено {len(image_paths)} изображений")
            
            if not image_paths:
                logger.warning("Не найдено изображений для индексации")
                return False
            
            # Извлекаем признаки из всех изображений
            features = []
            paths = []
            
            for i, path in enumerate(image_paths):
                try:
                    # Извлекаем признаки
                    feat = self.extract_features(path)
                    if feat is not None:
                        features.append(feat)
                        paths.append(path)
                        
                        # Логируем прогресс
                        if (i+1) % 100 == 0 or i == len(image_paths) - 1:
                            logger.info(f"Обработано {i+1}/{len(image_paths)} изображений")
                except Exception as e:
                    logger.error(f"Ошибка при обработке {path}: {e}")
            
            if not features:
                logger.error("Не удалось извлечь признаки ни из одного изображения")
                return False
            
            # Создаем индекс FAISS
            dimension = len(features[0])
            index = faiss.IndexFlatIP(dimension)  # Используем скалярное произведение для сравнения нормализованных векторов
            
            # Добавляем признаки в индекс
            features_array = np.array(features).astype('float32')
            index.add(features_array)
            
            # Создаем маппинг индексов в пути файлов
            self.path_mapping = {i: path for i, path in enumerate(paths)}
            
            logger.info(f"Индекс успешно создан: {index.ntotal} векторов, размерность {dimension}")
            
            self.faiss_index = index
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании индекса: {e}")
            logger.error(traceback.format_exc())
            return False
            
    def find_similar_images(self, query_image_path, folder_path=None, top_n=5, similarity_threshold=0.25):
        """
        Поиск похожих изображений с использованием CLIP и коррекцией по типу инструмента и бренду
        
        Args:
            query_image_path: Путь к изображению запроса
            folder_path: Путь к папке с изображениями (если нужно обновить индекс)
            top_n: Количество результатов для возврата
            similarity_threshold: Минимальный порог схожести
            
        Returns:
            Список кортежей (путь_к_изображению, схожесть)
        """
        try:
            # Проверяем инициализацию моделей
            if self.clip_model is None:
                if not self.initialize_model():
                    return []
            
            # Проверяем наличие индекса
            if self.faiss_index is None or self.faiss_index.ntotal == 0:
                logger.error("Индекс CLIP не инициализирован или пуст")
                return []
                    
            # Извлекаем признаки из запроса
            query_features = self.extract_features(query_image_path)
            if query_features is None:
                logger.error("Не удалось извлечь CLIP признаки из изображения запроса")
                return []
            
            # Определяем бренд по изображению и имени файла
            query_brand = detect_brand_by_color(query_image_path)
            logger.info(f"Определенный бренд запроса по цветам: {query_brand}")
            
            filename_brand = detect_brand_from_filename(query_image_path)
            if filename_brand != "Неизвестный" and query_brand is None:
                query_brand = filename_brand
                logger.info(f"Бренд определен по имени файла: {query_brand}")
            
            # Определяем тип инструмента
            tool_type, tool_type_ru, tool_confidence = self.classify_tool_type(query_image_path)
            logger.info(f"Определен тип инструмента: {tool_type_ru} с уверенностью {tool_confidence:.2f}")
            
            # Ищем похожие векторы
            query_features = np.array([query_features]).astype('float32')
            distances, indices = self.faiss_index.search(query_features, min(self.faiss_index.ntotal, top_n * 3))
            
            # Преобразуем расстояния в меры сходства (CLIP возвращает косинусное сходство)
            similarities = distances[0]
            
            # Фильтруем результаты по порогу сходства
            results = []
            for idx, similarity in zip(indices[0], similarities):
                if similarity >= similarity_threshold and idx in self.path_mapping:
                    result_path = self.path_mapping[idx]
                    
                    # Проверяем совпадение бренда и типа инструмента
                    result_brand = detect_brand_from_filename(result_path)
                    
                    # Если совпадают бренды, увеличиваем схожесть
                    if query_brand is not None and result_brand == query_brand:
                        similarity = min(similarity * 1.5, 1.0)  # Увеличиваем схожесть, но не больше 1.0
                    
                    results.append((result_path, float(similarity)))
            
            # Сортируем результаты по схожести
            results.sort(key=lambda x: x[1], reverse=True)
            
            # Возвращаем top_n результатов
            return results[:top_n]
        except Exception as e:
            logger.error(f"Ошибка при поиске похожих изображений: {e}")
            logger.error(traceback.format_exc())
            return []
            
    def classify_tool_type(self, image_path, clip_text_features=None):
        """
        Классифицирует тип инструмента с использованием CLIP
        
        Args:
            image_path: Путь к изображению
            clip_text_features: Предварительно рассчитанные текстовые признаки (опционально)
            
        Returns:
            Кортеж (тип_инструмента_en, тип_инструмента_ru, уверенность)
        """
        try:
            # Инициализируем модель CLIP, если нужно
            if self.clip_model is None or self.clip_processor is None:
                if not self.initialize_model():
                    return "unknown", "Неизвестный инструмент", 0.0
            
            # Словарь типов инструментов
            tool_types = {
                "drill": "Дрель",
                "screwdriver": "Отвертка",
                "hammer": "Молоток",
                "saw": "Пила",
                "angle grinder": "Болгарка",
                "jigsaw": "Лобзик",
                "wrench": "Ключ",
                "pliers": "Плоскогубцы",
                "tape measure": "Рулетка",
                "level": "Уровень",
                "impact driver": "Ударный шуруповерт",
                "circular saw": "Циркулярная пила",
                "miter saw": "Торцовочная пила",
                "router": "Фрезер",
                "sander": "Шлифмашина",
                "nail gun": "Гвоздезабиватель"
            }
            
            # Загружаем изображение
            image = Image.open(image_path).convert('RGB')
            
            # Получаем признаки изображения
            inputs = self.clip_processor(images=image, return_tensors="pt")
            with torch.no_grad():
                image_features = self.clip_model.get_image_features(**inputs)
            
            # Нормализуем вектор признаков
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            # Если текстовые признаки не предоставлены, вычисляем их
            if clip_text_features is None:
                # Проверяем кэш
                if not self.text_features_cache:
                    # Вычисляем текстовые признаки для всех типов инструментов
                    text_inputs = self.clip_processor(
                        text=["a photo of a " + tool_type for tool_type in tool_types.keys()],
                        return_tensors="pt", 
                        padding=True
                    )
                    
                    with torch.no_grad():
                        text_features = self.clip_model.get_text_features(**text_inputs)
                        
                    # Нормализуем
                    text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                    
                    # Сохраняем в кэш
                    self.text_features_cache = text_features
                else:
                    text_features = self.text_features_cache
            else:
                text_features = clip_text_features
            
            # Вычисляем сходство между изображением и каждым типом инструмента
            similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
            
            # Находим наиболее вероятный тип инструмента
            values, indices = similarity[0].topk(1)
            
            # Получаем результат
            idx = indices.item()
            confidence = values.item()
            tool_type_en = list(tool_types.keys())[idx]
            tool_type_ru = tool_types[tool_type_en]
            
            return tool_type_en, tool_type_ru, confidence
        except Exception as e:
            logger.error(f"Ошибка при классификации типа инструмента: {e}")
            logger.error(traceback.format_exc())
            return "unknown", "Неизвестный инструмент", 0.0
            
    def enhance_image_features(self, image_path):
        """
        Улучшает извлечение признаков из изображения с использованием 
        предобработки и расширенного распознавания
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            Кортеж (вектор_признаков, метаданные) или (None, {}) в случае ошибки
        """
        try:
            # Сначала извлекаем основные признаки
            features = self.extract_features(image_path)
            if features is None:
                return None, {}
            
            # Определяем бренд инструмента
            brand_name, brand_confidence = recognize_brand(image_path)
            
            # Определяем тип инструмента
            tool_type, type_confidence = self.classify_tool_type(image_path)
            
            # Собираем метаданные
            metadata = {
                "brand": brand_name,
                "brand_confidence": brand_confidence,
                "tool_type": tool_type,
                "type_confidence": type_confidence
            }
            
            logger.debug(f"Извлечены признаки и метаданные из {image_path}: "
                         f"бренд={brand_name} ({brand_confidence:.2f}), "
                         f"тип={tool_type} ({type_confidence:.2f})")
            
            return features, metadata
        except Exception as e:
            logger.error(f"Ошибка при улучшенном извлечении признаков: {e}")
            return None, {}
    
    def enhanced_image_search(self, query_image_path, top_n=None, similarity_threshold=None, 
                             variation_weights=None, similarity_bonuses=None, enable_variations=True):
        """
        Расширенный поиск изображений с использованием различных вариаций исходного изображения
        и коррекцией по типу инструмента и бренду
        
        Args:
            query_image_path: Путь к изображению запроса
            top_n: Количество результатов для возврата
            similarity_threshold: Минимальный порог схожести
            variation_weights: Кортеж весов для различных вариаций (контраст, резкость, яркость)
            similarity_bonuses: Кортеж бонусов схожести (бренд, тип, бренд+тип)
            enable_variations: Включить ли поиск по вариациям изображения
            
        Returns:
            Список кортежей (путь_к_изображению, схожесть)
        """
        try:
            # Проверяем инициализацию индекса
            if self.faiss_index is None:
                logger.error("Индекс не инициализирован")
                return []
                
            # Проверяем наличие файла запроса
            if not os.path.exists(query_image_path):
                logger.error(f"Файл запроса не существует: {query_image_path}")
                return []
            
            # Устанавливаем значения по умолчанию
            if top_n is None:
                top_n = 5
                
            if similarity_threshold is None:
                similarity_threshold = 0.25
                
            if variation_weights is None:
                variation_weights = (0.7, 0.6, 0.5)  # Веса для контраста, резкости, яркости
                
            if similarity_bonuses is None:
                similarity_bonuses = (0.2, 0.1, 0.3)  # Бонусы для бренда, типа, бренд+тип
            
            # Проверяем кэш для этого запроса
            cache_key = f"{query_image_path}_{top_n}_{similarity_threshold}"
            cached_results = get_cached_search_results(cache_key)
            if cached_results:
                logger.info(f"Найдены кэшированные результаты для {query_image_path}")
                return cached_results
            
            # Базовое изображение запроса
            # Используем улучшенное извлечение признаков
            query_features, query_metadata = self.enhance_image_features(query_image_path)
            
            if query_features is None:
                logger.error(f"Не удалось извлечь признаки из {query_image_path}")
                return []
                
            # Получаем информацию о бренде и типе инструмента на изображении
            query_brand = query_metadata.get("brand", "Неизвестный")
            query_tool_type = query_metadata.get("tool_type", "Неизвестный")
            
            # Словарь для хранения результатов и их оценок
            all_results = {}
            
            # Функция для добавления результатов с весом
            def add_weighted_results(results, weight=1.0):
                for img_path, similarity in results:
                    # Если результат уже есть, обновляем его с максимальной схожестью
                    if img_path in all_results:
                        all_results[img_path] = max(all_results[img_path], similarity * weight)
                    else:
                        all_results[img_path] = similarity * weight
            
            # Поиск по основному изображению
            base_results = self.search_with_features(query_features, top_n * 2)
            add_weighted_results(base_results, 1.0)
            
            # Поиск по вариациям изображения если включен
            if enable_variations:
                # Создаем вариации изображения
                pil_image = Image.open(query_image_path).convert('RGB')
                
                # Вариации с разным контрастом
                contrast_enhancer = ImageEnhance.Contrast(pil_image)
                high_contrast_img = contrast_enhancer.enhance(1.5)
                low_contrast_img = contrast_enhancer.enhance(0.7)
                
                # Вариации с разной резкостью
                sharpness_enhancer = ImageEnhance.Sharpness(pil_image)
                high_sharpness_img = sharpness_enhancer.enhance(1.5)
                low_sharpness_img = sharpness_enhancer.enhance(0.7)
                
                # Вариации с разной яркостью
                brightness_enhancer = ImageEnhance.Brightness(pil_image)
                high_brightness_img = brightness_enhancer.enhance(1.3)
                low_brightness_img = brightness_enhancer.enhance(0.8)
                
                # Сохраняем вариации во временных файлах
                base_dir = os.path.dirname(query_image_path)
                temp_files = []
                
                def save_variation(img, suffix):
                    temp_path = os.path.join(base_dir, f"temp_{uuid.uuid4()}_{suffix}.jpg")
                    img.save(temp_path)
                    temp_files.append(temp_path)
                    return temp_path
                
                # Сохраняем все вариации
                high_contrast_path = save_variation(high_contrast_img, "high_contrast")
                low_contrast_path = save_variation(low_contrast_img, "low_contrast")
                high_sharpness_path = save_variation(high_sharpness_img, "high_sharpness")
                low_sharpness_path = save_variation(low_sharpness_img, "low_sharpness")
                high_brightness_path = save_variation(high_brightness_img, "high_brightness")
                low_brightness_path = save_variation(low_brightness_img, "low_brightness")
                
                # Поиск по вариациям с разными весами
                contrast_weight, sharpness_weight, brightness_weight = variation_weights
                
                # Поиск с высоким контрастом
                high_contrast_features = self.extract_features(high_contrast_path)
                if high_contrast_features is not None:
                    high_contrast_results = self.search_with_features(high_contrast_features, top_n)
                    add_weighted_results(high_contrast_results, contrast_weight)
                
                # Поиск с низким контрастом
                low_contrast_features = self.extract_features(low_contrast_path)
                if low_contrast_features is not None:
                    low_contrast_results = self.search_with_features(low_contrast_features, top_n)
                    add_weighted_results(low_contrast_results, contrast_weight * 0.8)
                
                # Поиск с высокой резкостью
                high_sharpness_features = self.extract_features(high_sharpness_path)
                if high_sharpness_features is not None:
                    high_sharpness_results = self.search_with_features(high_sharpness_features, top_n)
                    add_weighted_results(high_sharpness_results, sharpness_weight)
                
                # Поиск с низкой резкостью
                low_sharpness_features = self.extract_features(low_sharpness_path)
                if low_sharpness_features is not None:
                    low_sharpness_results = self.search_with_features(low_sharpness_features, top_n)
                    add_weighted_results(low_sharpness_results, sharpness_weight * 0.8)
                
                # Поиск с высокой яркостью
                high_brightness_features = self.extract_features(high_brightness_path)
                if high_brightness_features is not None:
                    high_brightness_results = self.search_with_features(high_brightness_features, top_n)
                    add_weighted_results(high_brightness_results, brightness_weight)
                
                # Поиск с низкой яркостью
                low_brightness_features = self.extract_features(low_brightness_path)
                if low_brightness_features is not None:
                    low_brightness_results = self.search_with_features(low_brightness_features, top_n)
                    add_weighted_results(low_brightness_results, brightness_weight * 0.8)
                
                # Удаляем временные файлы
                for temp_file in temp_files:
                    try:
                        os.remove(temp_file)
                    except:
                        pass
            
            # Применяем корректировки схожести на основе бренда и типа инструмента
            brand_bonus, type_bonus, brand_type_bonus = similarity_bonuses
            
            # Корректируем оценки схожести
            final_results = {}
            for img_path, similarity in all_results.items():
                # Получаем метаданные результата
                try:
                    # Извлекаем бренд и тип из пути или имени файла
                    result_brand = recognize_brand(img_path)[0]
                    result_type = self.classify_tool_type(img_path)[0]
                    
                    # Корректируем схожесть
                    adjusted_similarity = similarity
                    
                    # Бонус за совпадение бренда
                    if query_brand != "Неизвестный" and query_brand == result_brand:
                        adjusted_similarity += brand_bonus
                    
                    # Бонус за совпадение типа инструмента
                    if query_tool_type != "Неизвестный" and query_tool_type == result_type:
                        adjusted_similarity += type_bonus
                    
                    # Дополнительный бонус за совпадение и бренда, и типа
                    if (query_brand != "Неизвестный" and query_brand == result_brand and
                        query_tool_type != "Неизвестный" and query_tool_type == result_type):
                        adjusted_similarity += brand_type_bonus
                    
                    # Ограничиваем максимальную схожесть до 1.0
                    adjusted_similarity = min(adjusted_similarity, 1.0)
                    
                    final_results[img_path] = adjusted_similarity
                except:
                    # В случае ошибки используем исходную схожесть
                    final_results[img_path] = similarity
            
            # Сортируем результаты по убыванию схожести
            sorted_results = sorted(final_results.items(), key=lambda x: x[1], reverse=True)
            
            # Фильтруем по порогу схожести
            filtered_results = [(path, sim) for path, sim in sorted_results if sim >= similarity_threshold]
            
            # Ограничиваем количество результатов
            final_results = filtered_results[:top_n]
            
            # Кэшируем результаты
            cache_search_results(cache_key, final_results)
            
            return final_results
            
        except Exception as e:
            logger.error(f"Ошибка при расширенном поиске изображений: {e}")
            logger.error(traceback.format_exc())
            return []
            
    def search_with_features(self, features, top_n=5):
        """
        Поиск похожих изображений по вектору признаков
        
        Args:
            features: Вектор признаков для поиска
            top_n: Количество результатов для возврата
            
        Returns:
            Список кортежей (путь_к_изображению, схожесть)
        """
        try:
            # Проверяем инициализацию индекса
            if self.faiss_index is None:
                logger.error("Индекс не инициализирован")
                return []
            
            # Преобразуем признаки в нужный формат
            query_features = features.reshape(1, -1).astype('float32')
            
            # Выполняем поиск в индексе
            distances, indices = self.faiss_index.search(query_features, min(top_n, self.faiss_index.ntotal))
            
            # Формируем результаты
            results = []
            for i, idx in enumerate(indices[0]):
                if idx != -1:  # -1 означает, что индекс не найден
                    path = self.path_mapping.get(idx)
                    if path:
                        # Конвертируем расстояние в схожесть (расстояние - это скалярное произведение, максимум 1)
                        similarity = float(distances[0][i])
                        results.append((path, similarity))
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при поиске с признаками: {e}")
            return []


# Функции-обертки для обратной совместимости с существующим кодом

def initialize_image_search():
    """
    Инициализирует модели для поиска изображений
    
    Returns:
        True если инициализация успешна, иначе False
    """
    service = ImageSearchService.get_instance()
    return service.initialize_model() and service.clip_model

def update_image_index(folder_path):
    """
    Обновляет индекс изображений для быстрого поиска
    
    Args:
        folder_path: Путь к папке с изображениями
        
    Returns:
        FAISS индекс или None в случае ошибки
    """
    service = ImageSearchService.get_instance()
    success = service.update_image_index(folder_path)
    return service.faiss_index if success else None

def find_similar_images(query_image_path, folder_path=None, top_n=5, similarity_threshold=0.25):
    """
    Поиск похожих изображений с использованием CLIP и коррекцией по типу инструмента и бренду
    
    Args:
        query_image_path: Путь к изображению запроса
        folder_path: Путь к папке с изображениями (если нужно обновить индекс)
        top_n: Количество результатов для возврата
        similarity_threshold: Минимальный порог схожести
        
    Returns:
        Список кортежей (путь_к_изображению, схожесть)
    """
    service = ImageSearchService.get_instance()
    return service.find_similar_images(query_image_path, folder_path, top_n, similarity_threshold)

def classify_tool_type(image_path, clip_text_features=None):
    """
    Классифицирует тип инструмента с использованием CLIP
    
    Args:
        image_path: Путь к изображению
        clip_text_features: Предварительно рассчитанные текстовые признаки (опционально)
        
    Returns:
        Кортеж (тип_инструмента_en, тип_инструмента_ru, уверенность)
    """
    service = ImageSearchService.get_instance()
    return service.classify_tool_type(image_path, clip_text_features)

def enhanced_image_search(query_image_path, top_n=None, similarity_threshold=None):
    """
    Улучшенный поиск похожих изображений с использованием мультимодального подхода.
    
    Args:
        query_image_path: Путь к изображению для поиска
        top_n: Количество результатов для возврата (если None, берется из конфигурации)
        similarity_threshold: Минимальный порог схожести (если None, берется из конфигурации)
        
    Returns:
        Список кортежей (путь_к_изображению, схожесть)
    """
    from toolbot.config import get_similarity_threshold, get_top_n_results, get_image_variation_weights, get_similarity_bonuses
    
    # Используем параметры из конфигурации, если они не указаны явно
    if similarity_threshold is None:
        similarity_threshold = get_similarity_threshold()
    
    if top_n is None:
        top_n = get_top_n_results()
    
    # Получаем веса для различных вариаций изображения
    contrast_weight, sharpness_weight, brightness_weight = get_image_variation_weights()
    
    # Получаем бонусы для коррекции схожести
    brand_bonus, type_bonus, brand_type_bonus = get_similarity_bonuses()
    
    service = ImageSearchService.get_instance()
    return service.enhanced_image_search(
        query_image_path, 
        top_n=top_n, 
        similarity_threshold=similarity_threshold,
        variation_weights=(contrast_weight, sharpness_weight, brightness_weight),
        similarity_bonuses=(brand_bonus, type_bonus, brand_type_bonus)
    )


# Оставляем функции для определения бренда (они не используют состояние)
def detect_brand_from_filename(filename):
    """
    Определяет бренд инструмента по имени файла
    
    Args:
        filename: Имя файла или путь к файлу
        
    Returns:
        Название бренда или "Неизвестный"
    """
    # Получаем только имя файла без пути
    basename = os.path.basename(filename).lower()
    
    # Словарь брендов и их вариаций в названиях файлов
    brands = {
        "Makita": ["makita", "макита"],
        "Bosch": ["bosch", "бош"],
        "DeWalt": ["dewalt", "девольт", "де вольт"],
        "Metabo": ["metabo", "метабо"],
        "Hilti": ["hilti", "хилти"],
        "Festool": ["festool", "фестул"],
        "AEG": ["aeg", "аег"],
        "Hitachi": ["hitachi", "хитачи"],
        "Milwaukee": ["milwaukee", "милуоки"],
        "Ryobi": ["ryobi", "риоби"],
        "Dremel": ["dremel", "дремел"],
        "Interskol": ["интерскол", "интерскол"],
        "Zubr": ["zubr", "зубр"],
        "Patriot": ["patriot", "патриот"],
        "Bort": ["bort", "борт"],
        "Stihl": ["stihl", "штиль"],
        "Kärcher": ["karcher", "керхер", "керхэр"],
    }
    
    # Проверяем наличие бренда в имени файла
    for brand, variations in brands.items():
        for variation in variations:
            if variation in basename:
                return brand
    
    return "Неизвестный"


def detect_brand_by_color(image_path):
    """
    Определяет бренд инструмента по цветовой гамме изображения
    
    Args:
        image_path: Путь к изображению
        
    Returns:
        Название бренда или None если не удалось определить
    """
    try:
        # Загружаем изображение
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Не удалось загрузить изображение для определения бренда: {image_path}")
            return None
        
        # Конвертируем в HSV для лучшего анализа цветов
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Получаем размеры изображения
        height, width = img.shape[:2]
        image_area = height * width
        
        # Определяем маски для разных цветов брендов
        # Makita - синий (расширяем диапазон для лучшего определения)
        lower_makita = np.array([95, 80, 50])
        upper_makita = np.array([135, 255, 255])
        makita_mask = cv2.inRange(hsv, lower_makita, upper_makita)
        makita_pixels = cv2.countNonZero(makita_mask)
        
        # DeWalt - желтый
        lower_dewalt = np.array([20, 100, 100])
        upper_dewalt = np.array([40, 255, 255])
        dewalt_mask = cv2.inRange(hsv, lower_dewalt, upper_dewalt)
        dewalt_pixels = cv2.countNonZero(dewalt_mask)
        
        # Bosch зеленый (для инструментов DIY)
        lower_bosch_green = np.array([50, 100, 50])
        upper_bosch_green = np.array([70, 255, 255])
        bosch_green_mask = cv2.inRange(hsv, lower_bosch_green, upper_bosch_green)
        bosch_green_pixels = cv2.countNonZero(bosch_green_mask)
        
        # Bosch синий (для профессиональных инструментов)
        lower_bosch_blue = np.array([90, 100, 50])
        upper_bosch_blue = np.array([120, 255, 255])
        bosch_blue_mask = cv2.inRange(hsv, lower_bosch_blue, upper_bosch_blue)
        bosch_blue_pixels = cv2.countNonZero(bosch_blue_mask)
        
        # Metabo - зеленый
        lower_metabo = np.array([70, 100, 50])
        upper_metabo = np.array([85, 255, 255])
        metabo_mask = cv2.inRange(hsv, lower_metabo, upper_metabo)
        metabo_pixels = cv2.countNonZero(metabo_mask)
        
        # Вычисляем процент площади каждого цвета
        makita_percent = makita_pixels / image_area
        dewalt_percent = dewalt_pixels / image_area
        bosch_green_percent = bosch_green_pixels / image_area
        bosch_blue_percent = bosch_blue_pixels / image_area
        metabo_percent = metabo_pixels / image_area
        
        # Снижаем порог для определения бренда с 15% до 10%
        threshold = 0.10  # 10% от общей площади изображения
        
        # Логируем проценты цветов для отладки
        logger.debug(f"Проценты цветов: Makita синий: {makita_percent:.2f}, DeWalt желтый: {dewalt_percent:.2f}, " 
                    f"Bosch зеленый: {bosch_green_percent:.2f}, Bosch синий: {bosch_blue_percent:.2f}, "
                    f"Metabo зеленый: {metabo_percent:.2f}")
        
        # Определяем бренд по преобладающему цвету
        # Приоритет Makita увеличен, учитывая, что синий цвет Makita является ключевым идентификатором
        if makita_percent > threshold * 0.8:  # Для Makita снижаем порог еще на 20%
            logger.info(f"Определен бренд Makita с процентом цвета: {makita_percent:.2f}")
            return "Makita"
        elif dewalt_percent > threshold:
            logger.info(f"Определен бренд DeWalt с процентом цвета: {dewalt_percent:.2f}")
            return "DeWalt"
        elif bosch_green_percent > threshold:
            logger.info(f"Определен бренд Bosch (зеленый) с процентом цвета: {bosch_green_percent:.2f}")
            return "Bosch"
        elif bosch_blue_percent > threshold:
            logger.info(f"Определен бренд Bosch (синий) с процентом цвета: {bosch_blue_percent:.2f}")
            return "Bosch"
        elif metabo_percent > threshold:
            logger.info(f"Определен бренд Metabo с процентом цвета: {metabo_percent:.2f}")
            return "Metabo"
        
        # Дополнительная проверка - если больше 5% синего цвета Makita, то это, вероятно, Makita
        if makita_percent > 0.05:
            logger.info(f"Определен бренд Makita (по минимальному порогу) с процентом цвета: {makita_percent:.2f}")
            return "Makita"
        
        return None
    except Exception as e:
        logger.error(f"Ошибка при определении бренда по цвету: {e}")
        return None


def detect_tools_on_image(image_path):
    """
    Обнаруживает инструменты на изображении с использованием детектора объектов
    
    Args:
        image_path: Путь к изображению
        
    Returns:
        Список обнаруженных инструментов в формате [{'bbox': (x1, y1, x2, y2), 'confidence': float, 'class_name': str}]
    """
    try:
        # Используем детектор объектов из модуля object_detection
        return detect_objects(image_path)
    except Exception as e:
        logger.error(f"Ошибка при обнаружении инструментов: {e}")
        logger.error(traceback.format_exc())
        
        # В случае ошибки возвращаем один объект, занимающий все изображение
        img = cv2.imread(image_path)
        if img is not None:
            height, width = img.shape[:2]
            return [
                {
                    'bbox': (0, 0, width, height),
                    'confidence': 1.0,
                    'class_name': 'tool'
                }
            ]
        return [] 