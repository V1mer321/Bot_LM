#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для работы с лёгкими моделями обнаружения объектов.
Предоставляет интерфейс для использования оптимизированных моделей детекции
с низкой латентностью, таких как MobileNetV3, EfficientDet-Lite и т.д.
"""

import os
import logging
import time
import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Any, Tuple, Optional, Union
from pathlib import Path
import onnxruntime as ort
import cv2
from functools import lru_cache

from toolbot.utils.enhanced_logging import get_logger
from toolbot.utils.model_optimizer import get_model_optimizer
from toolbot.utils.cache_manager import get_search_cache

# Получаем логгер для модуля
logger = get_logger(__name__)

# Пути к предварительно обученным моделям
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "optimized")
MOBILENET_MODEL_PATH = os.path.join(MODELS_DIR, "mobilenet_v3_small.onnx")
EFFICIENTDET_MODEL_PATH = os.path.join(MODELS_DIR, "efficientdet_lite0.onnx")


class LightDetectionModel:
    """
    Базовый класс для лёгких моделей обнаружения объектов.
    """
    
    def __init__(self, model_path: str = None, use_onnx: bool = True, 
                 use_cuda: bool = None, confidence_threshold: float = 0.5):
        """
        Инициализация лёгкой модели обнаружения объектов.
        
        Args:
            model_path: Путь к файлу модели (если None, используется модель по умолчанию)
            use_onnx: Использовать ONNX Runtime для инференса
            use_cuda: Использовать CUDA если доступна (если None, определяется автоматически)
            confidence_threshold: Порог уверенности для детекции объектов
        """
        self.model_path = model_path
        self.use_onnx = use_onnx
        self.confidence_threshold = confidence_threshold
        
        # Определяем устройство для вычислений
        if use_cuda is None:
            self.use_cuda = torch.cuda.is_available()
        else:
            self.use_cuda = use_cuda and torch.cuda.is_available()
        
        self.device = torch.device('cuda' if self.use_cuda else 'cpu')
        
        # Кэш-менеджер для кэширования результатов
        self.cache_manager = get_search_cache()
        
        # Загружаем модель
        self.model = None
        self.model_name = "unknown"
        self.input_shape = (224, 224)
        self.initialized = False
        
        logger.info(f"Инициализирована лёгкая модель детекции. CUDA: {self.use_cuda}, ONNX: {self.use_onnx}")
    
    def initialize(self):
        """
        Загрузка и инициализация модели.
        Должна быть переопределена в дочерних классах.
        """
        raise NotImplementedError("Метод должен быть переопределен в дочернем классе")
    
    def preprocess_image(self, image):
        """
        Предобработка изображения для модели.
        
        Args:
            image: Изображение для обработки (numpy array)
            
        Returns:
            Предобработанное изображение
        """
        # Базовая предобработка - изменение размера и нормализация
        if isinstance(image, str) and os.path.exists(image):
            # Если передан путь к файлу, загружаем изображение
            image = cv2.imread(image)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Изменяем размер изображения для модели
        resized = cv2.resize(image, self.input_shape)
        
        # Нормализация [0-255] -> [0-1]
        normalized = resized / 255.0
        
        # Преобразование формата для модели
        if self.use_onnx:
            # Для ONNX: (B, H, W, C) и dtype=float32
            preprocessed = np.expand_dims(normalized, axis=0).astype(np.float32)
        else:
            # Для PyTorch: (B, C, H, W) и tensor
            transposed = normalized.transpose(2, 0, 1)  # (H, W, C) -> (C, H, W)
            preprocessed = np.expand_dims(transposed, axis=0).astype(np.float32)
            preprocessed = torch.from_numpy(preprocessed).to(self.device)
        
        return preprocessed
    
    def postprocess_output(self, output, original_image_shape):
        """
        Постобработка выхода модели.
        Должна быть переопределена в дочерних классах.
        
        Args:
            output: Выход модели
            original_image_shape: Форма исходного изображения
            
        Returns:
            Список обнаруженных объектов
        """
        raise NotImplementedError("Метод должен быть переопределен в дочернем классе")
    
    @lru_cache(maxsize=100)
    def detect_from_file(self, image_path):
        """
        Обнаружение объектов на изображении из файла с кэшированием.
        
        Args:
            image_path: Путь к файлу изображения
            
        Returns:
            Список обнаруженных объектов
        """
        # Проверяем кэш
        cache_key = f"detect_{self.model_name}_{image_path}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            logger.debug(f"Результат детекции получен из кэша для {image_path}")
            return cached_result
        
        # Загружаем изображение
        try:
            image = cv2.imread(image_path)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        except Exception as e:
            logger.error(f"Ошибка при чтении изображения {image_path}: {e}")
            return []
        
        # Запускаем обнаружение
        result = self.detect(image)
        
        # Кэшируем результат
        self.cache_manager.set(cache_key, result, expire=3600)  # Кэш на 1 час
        
        return result
    
    def detect(self, image):
        """
        Обнаружение объектов на изображении.
        
        Args:
            image: Изображение (numpy array RGB формата)
            
        Returns:
            Список обнаруженных объектов
        """
        if not self.initialized:
            self.initialize()
        
        # Сохраняем форму исходного изображения
        original_shape = image.shape[:2]  # (height, width)
        
        # Предобработка изображения
        preprocessed = self.preprocess_image(image)
        
        # Инференс
        start_time = time.time()
        
        try:
            if self.use_onnx:
                # Для ONNX Runtime
                input_name = self.model.get_inputs()[0].name
                output = self.model.run(None, {input_name: preprocessed})
            else:
                # Для PyTorch
                with torch.no_grad():
                    output = self.model(preprocessed)
        except Exception as e:
            logger.error(f"Ошибка при инференсе модели {self.model_name}: {e}")
            return []
        
        inference_time = (time.time() - start_time) * 1000  # в миллисекундах
        logger.debug(f"Время инференса {self.model_name}: {inference_time:.2f} мс")
        
        # Постобработка результата
        detections = self.postprocess_output(output, original_shape)
        
        return detections


class MobileNetDetector(LightDetectionModel):
    """
    Класс для обнаружения объектов с использованием MobileNetV3.
    """
    
    def __init__(self, model_path: str = None, **kwargs):
        """
        Инициализация детектора на основе MobileNetV3.
        
        Args:
            model_path: Путь к файлу модели (если None, используется модель по умолчанию)
            **kwargs: Дополнительные аргументы для базового класса
        """
        super().__init__(model_path, **kwargs)
        self.model_name = "MobileNetV3"
        self.input_shape = (224, 224)
        
        # Классы COCO для MobileNetV3
        self.classes = [
            'инструмент', 'отвертка', 'молоток', 'пила', 'дрель', 'шуруповерт', 
            'гаечный ключ', 'плоскогубцы', 'рубанок', 'степлер', 'ножницы', 
            'уровень', 'рулетка', 'шлифмашина', 'фрезер', 'электролобзик'
        ]
    
    def initialize(self):
        """Загрузка и инициализация модели MobileNetV3"""
        try:
            model_path = self.model_path or MOBILENET_MODEL_PATH
            
            # Создаем директорию для моделей, если она не существует
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            
            if self.use_onnx:
                # Проверяем наличие файла модели ONNX
                if not os.path.exists(model_path):
                    logger.error(f"Файл модели ONNX не найден: {model_path}")
                    # Здесь можно добавить автоматическую загрузку модели при необходимости
                    raise FileNotFoundError(f"Файл модели не найден: {model_path}")
                
                # Создаем сессию ONNX Runtime
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if self.use_cuda else ['CPUExecutionProvider']
                self.model = ort.InferenceSession(model_path, providers=providers)
                logger.info(f"✅ Модель {self.model_name} загружена с использованием ONNX Runtime")
            else:
                # Загрузка модели PyTorch
                self.model = torch.hub.load('pytorch/vision:v0.10.0', 'mobilenet_v3_small', pretrained=True)
                self.model.eval()
                
                # Оптимизация модели
                optimizer = get_model_optimizer()
                self.model = optimizer.optimize_clip_model(self.model, 'quantization')
                
                logger.info(f"✅ Модель {self.model_name} загружена с использованием PyTorch")
            
            self.initialized = True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при инициализации модели {self.model_name}: {e}")
            raise
    
    def postprocess_output(self, output, original_image_shape):
        """
        Постобработка выхода модели MobileNetV3.
        
        Args:
            output: Выход модели
            original_image_shape: Форма исходного изображения (height, width)
            
        Returns:
            Список обнаруженных объектов
        """
        # Для MobileNetV3 (классификация):
        # - output это логиты классов для ONNX или тензор для PyTorch
        
        if self.use_onnx:
            # Для ONNX вывод обычно является списком массивов
            logits = output[0]  # Первый выход - логиты классов
        else:
            # Для PyTorch вывод - тензор
            logits = output.cpu().numpy()
        
        # Применяем softmax для получения вероятностей
        scores = self._softmax(logits)
        
        # Находим класс с максимальной вероятностью
        max_score_idx = np.argmax(scores, axis=1)[0]
        max_score = scores[0, max_score_idx]
        
        # Проверяем порог уверенности
        if max_score < self.confidence_threshold:
            return []
        
        # Формируем результат
        class_name = self.classes[max_score_idx] if max_score_idx < len(self.classes) else "unknown"
        
        # Для классификации возвращаем один объект на всё изображение
        result = [{
            'label': class_name,
            'confidence': float(max_score),
            'bbox': [0, 0, original_image_shape[1], original_image_shape[0]]  # [x, y, width, height]
        }]
        
        return result
    
    def _softmax(self, x):
        """
        Применение softmax к массиву.
        
        Args:
            x: Массив логитов
            
        Returns:
            Массив вероятностей
        """
        # Вычитаем максимум для численной стабильности
        e_x = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e_x / np.sum(e_x, axis=1, keepdims=True)


class EfficientDetLiteDetector(LightDetectionModel):
    """
    Класс для обнаружения объектов с использованием EfficientDet-Lite.
    """
    
    def __init__(self, model_path: str = None, **kwargs):
        """
        Инициализация детектора на основе EfficientDet-Lite.
        
        Args:
            model_path: Путь к файлу модели (если None, используется модель по умолчанию)
            **kwargs: Дополнительные аргументы для базового класса
        """
        super().__init__(model_path, **kwargs)
        self.model_name = "EfficientDet-Lite0"
        self.input_shape = (320, 320)
        
        # Классы COCO для EfficientDet
        self.classes = [
            'инструмент', 'отвертка', 'молоток', 'пила', 'дрель', 'шуруповерт', 
            'гаечный ключ', 'плоскогубцы', 'рубанок', 'степлер', 'ножницы', 
            'уровень', 'рулетка', 'шлифмашина', 'фрезер', 'электролобзик'
        ]
    
    def initialize(self):
        """Загрузка и инициализация модели EfficientDet-Lite"""
        try:
            model_path = self.model_path or EFFICIENTDET_MODEL_PATH
            
            # Создаем директорию для моделей, если она не существует
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            
            if self.use_onnx:
                # Проверяем наличие файла модели ONNX
                if not os.path.exists(model_path):
                    logger.error(f"Файл модели ONNX не найден: {model_path}")
                    raise FileNotFoundError(f"Файл модели не найден: {model_path}")
                
                # Создаем сессию ONNX Runtime с оптимальными настройками
                sess_options = ort.SessionOptions()
                sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if self.use_cuda else ['CPUExecutionProvider']
                self.model = ort.InferenceSession(model_path, sess_options=sess_options, providers=providers)
                logger.info(f"✅ Модель {self.model_name} загружена с использованием ONNX Runtime")
            else:
                # В данной реализации поддерживается только ONNX
                logger.error(f"Модель {self.model_name} поддерживается только в формате ONNX")
                raise NotImplementedError(f"Модель {self.model_name} поддерживается только в формате ONNX")
            
            self.initialized = True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при инициализации модели {self.model_name}: {e}")
            raise
    
    def preprocess_image(self, image):
        """
        Предобработка изображения для модели EfficientDet-Lite.
        
        Args:
            image: Изображение для обработки (numpy array)
            
        Returns:
            Предобработанное изображение
        """
        # Загружаем изображение, если передан путь
        if isinstance(image, str) and os.path.exists(image):
            image = cv2.imread(image)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Сохраняем исходные размеры
        height, width = image.shape[:2]
        
        # Изменяем размер изображения
        resized = cv2.resize(image, self.input_shape)
        
        # Нормализация значений пикселей
        normalized = resized / 255.0
        
        # Преобразование в формат, требуемый моделью
        input_tensor = np.expand_dims(normalized, axis=0).astype(np.float32)
        
        return input_tensor
    
    def postprocess_output(self, output, original_image_shape):
        """
        Постобработка выхода модели EfficientDet-Lite.
        
        Args:
            output: Выход модели
            original_image_shape: Форма исходного изображения (height, width)
            
        Returns:
            Список обнаруженных объектов
        """
        # Распаковываем выход модели
        # Для EfficientDet-Lite в ONNX формате:
        # - output[0]: детекции (batch_size, num_detections)
        # - output[1]: scores (batch_size, num_detections)
        # - output[2]: classes (batch_size, num_detections)
        # - output[3]: boxes (batch_size, num_detections, 4)
        
        num_detections = int(output[0][0])
        detection_boxes = output[1][0][:num_detections]  # [y1, x1, y2, x2] в нормализованных координатах [0, 1]
        detection_scores = output[2][0][:num_detections]
        detection_classes = output[3][0][:num_detections].astype(np.int32)
        
        # Фильтрация по порогу уверенности
        valid_indices = np.where(detection_scores >= self.confidence_threshold)[0]
        
        # Преобразование результатов
        results = []
        
        for i in valid_indices:
            # Получаем координаты в пикселях
            y1, x1, y2, x2 = detection_boxes[i]
            
            # Преобразуем координаты из нормализованных [0, 1] в пиксели
            x1_pixel = int(x1 * original_image_shape[1])
            y1_pixel = int(y1 * original_image_shape[0])
            x2_pixel = int(x2 * original_image_shape[1])
            y2_pixel = int(y2 * original_image_shape[0])
            
            # Ширина и высота прямоугольника
            width = x2_pixel - x1_pixel
            height = y2_pixel - y1_pixel
            
            # Получаем метку класса
            class_id = detection_classes[i]
            class_name = self.classes[class_id] if class_id < len(self.classes) else "unknown"
            
            # Формируем результат
            result = {
                'label': class_name,
                'confidence': float(detection_scores[i]),
                'bbox': [x1_pixel, y1_pixel, width, height]  # [x, y, width, height]
            }
            
            results.append(result)
        
        return results


# Создаем глобальные экземпляры детекторов
_mobilenet_detector = None
_efficientdet_detector = None

def get_mobilenet_detector():
    """
    Получение экземпляра детектора MobileNetV3.
    
    Returns:
        Экземпляр MobileNetDetector
    """
    global _mobilenet_detector
    if _mobilenet_detector is None:
        _mobilenet_detector = MobileNetDetector()
    return _mobilenet_detector

def get_efficientdet_detector():
    """
    Получение экземпляра детектора EfficientDet-Lite.
    
    Returns:
        Экземпляр EfficientDetLiteDetector
    """
    global _efficientdet_detector
    if _efficientdet_detector is None:
        _efficientdet_detector = EfficientDetLiteDetector()
    return _efficientdet_detector

def get_optimized_detector(model_type="mobilenet"):
    """
    Получение оптимизированного детектора заданного типа.
    
    Args:
        model_type: Тип модели ('mobilenet' или 'efficientdet')
        
    Returns:
        Экземпляр детектора
    """
    if model_type.lower() == "mobilenet":
        return get_mobilenet_detector()
    elif model_type.lower() == "efficientdet":
        return get_efficientdet_detector()
    else:
        logger.warning(f"Неизвестный тип модели: {model_type}, используется MobileNet")
        return get_mobilenet_detector() 