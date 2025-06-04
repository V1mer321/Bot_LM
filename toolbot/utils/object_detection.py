"""
Модуль для обнаружения объектов на изображениях.
"""
import os
import cv2
import logging
import numpy as np
from typing import List, Dict, Tuple, Union, Optional

logger = logging.getLogger(__name__)

class ObjectDetector:
    """
    Класс для обнаружения объектов на изображениях с использованием каскадных классификаторов
    или других доступных методов OpenCV.
    """
    
    def __init__(self):
        """
        Инициализация детектора объектов.
        """
        self.cascade_detector = None
        self.initialize_detector()
    
    def initialize_detector(self):
        """
        Инициализация каскадного детектора объектов.
        
        Можно заменить на более продвинутые методы, такие как YOLO или SSD.
        """
        try:
            # Используем каскадный детектор для обнаружения объектов
            # Для обнаружения инструментов можно использовать детектор общего назначения
            # А потом фильтровать результаты
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            
            # Проверяем существование файла
            if not os.path.exists(cascade_path):
                logger.error(f"Файл каскада не найден: {cascade_path}")
                return
                
            self.cascade_detector = cv2.CascadeClassifier(cascade_path)
            logger.info("Каскадный детектор инициализирован успешно")
        except Exception as e:
            logger.error(f"Ошибка при инициализации детектора: {e}")
    
    def detect_objects(self, image_path: str, min_size: Tuple[int, int] = (30, 30)) -> List[Dict]:
        """
        Обнаружение объектов на изображении.
        
        Args:
            image_path: Путь к изображению
            min_size: Минимальный размер объекта (ширина, высота)
            
        Returns:
            Список обнаруженных объектов в формате [{'bbox': (x1, y1, x2, y2), 'confidence': float, 'class_name': str}]
        """
        try:
            # Загружаем изображение
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Не удалось загрузить изображение: {image_path}")
                return []
                
            # Размеры изображения
            height, width = image.shape[:2]
            
            # Получаем прямоугольник, охватывающий все изображение
            full_image_bbox = (0, 0, width, height)
            
            # Проверяем инициализацию детектора
            if self.cascade_detector is None:
                logger.warning("Детектор не инициализирован, возвращаем все изображение")
                return [{'bbox': full_image_bbox, 'confidence': 1.0, 'class_name': 'unknown'}]
            
            # Применяем алгоритмы предобработки
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            
            # Обнаруживаем объекты
            objects = self.cascade_detector.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=min_size
            )
            
            results = []
            
            # Если объекты найдены
            if len(objects) > 0:
                for (x, y, w, h) in objects:
                    # Расширяем bbox для захвата большей части объекта
                    x1 = max(0, x - int(w * 0.1))
                    y1 = max(0, y - int(h * 0.1))
                    x2 = min(width, x + w + int(w * 0.1))
                    y2 = min(height, y + h + int(h * 0.1))
                    
                    # Добавляем результат
                    results.append({
                        'bbox': (x1, y1, x2, y2),
                        'confidence': 0.8,  # Примерная уверенность
                        'class_name': 'tool'  # Пока используем общее название
                    })
            
            # Если не найдено объектов, возвращаем все изображение
            if not results:
                results.append({
                    'bbox': full_image_bbox,
                    'confidence': 1.0,
                    'class_name': 'unknown'
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при обнаружении объектов: {e}")
            return []
            
    def detect_objects_with_contours(self, image_path: str) -> List[Dict]:
        """
        Обнаружение объектов на изображении с использованием контуров.
        Эта реализация лучше подходит для инструментов, которые обычно имеют четкие контуры.
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            Список обнаруженных объектов
        """
        try:
            # Загружаем изображение
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Не удалось загрузить изображение: {image_path}")
                return []
                
            # Размеры изображения
            height, width = image.shape[:2]
            
            # Преобразуем в оттенки серого
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Применяем размытие по Гауссу для уменьшения шума
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Применяем адаптивную бинаризацию
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY_INV, 11, 2
            )
            
            # Находим контуры
            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            
            # Фильтруем контуры по размеру
            min_contour_area = (width * height) * 0.01  # 1% от размера изображения
            significant_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_contour_area]
            
            results = []
            
            # Если нашли значимые контуры
            if significant_contours:
                # Сортируем по площади (от большего к меньшему)
                significant_contours.sort(key=cv2.contourArea, reverse=True)
                
                # Берем только топ-3 контура
                top_contours = significant_contours[:3]
                
                for i, contour in enumerate(top_contours):
                    # Получаем ограничивающий прямоугольник
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Расширяем область
                    x1 = max(0, x - int(w * 0.1))
                    y1 = max(0, y - int(h * 0.1))
                    x2 = min(width, x + w + int(w * 0.1))
                    y2 = min(height, y + h + int(h * 0.1))
                    
                    # Вычисляем уверенность на основе нормализованной площади
                    contour_area = cv2.contourArea(contour)
                    max_area = width * height
                    confidence = min(contour_area / max_area * 10, 1.0)  # Нелинейное масштабирование
                    
                    results.append({
                        'bbox': (x1, y1, x2, y2),
                        'confidence': confidence,
                        'class_name': 'tool'
                    })
            
            # Если не нашли контуров, возвращаем все изображение
            if not results:
                results.append({
                    'bbox': (0, 0, width, height),
                    'confidence': 1.0,
                    'class_name': 'unknown'
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при обнаружении объектов через контуры: {e}")
            return []


# Синглтон-экземпляр детектора
_detector_instance = None

def get_detector():
    """
    Получение экземпляра детектора объектов.
    
    Returns:
        Экземпляр ObjectDetector
    """
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = ObjectDetector()
    return _detector_instance


def detect_objects_on_image(image_path: str) -> List[Dict]:
    """
    Обнаружение объектов на изображении (обертка для использования без создания экземпляра).
    
    Args:
        image_path: Путь к изображению
        
    Returns:
        Список обнаруженных объектов
    """
    detector = get_detector()
    # Используем детектор контуров как более подходящий для инструментов
    return detector.detect_objects_with_contours(image_path) 