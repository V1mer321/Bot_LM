#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для распознавания брендов строительных инструментов по цветовым характеристикам.
Содержит расширенную базу данных цветовых шаблонов для различных производителей.
"""

import logging
import cv2
import numpy as np
import os
from collections import Counter
from typing import Dict, List, Tuple, Optional, Union

logger = logging.getLogger(__name__)

# Расширенная база цветовых шаблонов для брендов
# Каждый бренд представлен словарем {имя_цвета: (нижний_HSV, верхний_HSV, вес)}
BRAND_COLOR_TEMPLATES = {
    "Makita": {
        "primary_blue": (np.array([95, 100, 50]), np.array([135, 255, 255]), 1.0),
        "secondary_black": (np.array([0, 0, 0]), np.array([180, 30, 60]), 0.5),
        "logo_white": (np.array([0, 0, 200]), np.array([180, 30, 255]), 0.3),
        "accent_teal": (np.array([85, 80, 50]), np.array([100, 255, 255]), 0.7),
    },
    "DeWalt": {
        "primary_yellow": (np.array([20, 100, 100]), np.array([40, 255, 255]), 1.0),
        "secondary_black": (np.array([0, 0, 0]), np.array([180, 30, 60]), 0.6),
        "logo_black": (np.array([0, 0, 0]), np.array([180, 30, 60]), 0.5),
        "accent_gray": (np.array([0, 0, 80]), np.array([180, 15, 150]), 0.3),
    },
    "Bosch": {
        # Профессиональные инструменты (синие)
        "pro_blue": (np.array([90, 120, 60]), np.array([120, 255, 255]), 1.0),
        # Для дома и сада (зеленые)
        "home_green": (np.array([50, 100, 50]), np.array([70, 255, 255]), 1.0),
        "secondary_black": (np.array([0, 0, 0]), np.array([180, 30, 60]), 0.5),
        "logo_white": (np.array([0, 0, 200]), np.array([180, 30, 255]), 0.3),
        "accent_red": (np.array([0, 100, 100]), np.array([10, 255, 255]), 0.4),
    },
    "Milwaukee": {
        "primary_red": (np.array([0, 120, 70]), np.array([10, 255, 255]), 1.0),
        "secondary_red": (np.array([175, 120, 70]), np.array([180, 255, 255]), 1.0), # Красный в конце спектра HSV
        "secondary_gray": (np.array([0, 0, 100]), np.array([180, 30, 180]), 0.5),
        "logo_white": (np.array([0, 0, 200]), np.array([180, 30, 255]), 0.3),
    },
    "Metabo": {
        "primary_green": (np.array([65, 100, 50]), np.array([85, 255, 255]), 1.0),
        "secondary_black": (np.array([0, 0, 0]), np.array([180, 30, 60]), 0.6),
        "logo_white": (np.array([0, 0, 200]), np.array([180, 30, 255]), 0.3),
    },
    "AEG": {
        "primary_red": (np.array([0, 120, 100]), np.array([10, 255, 255]), 1.0),
        "secondary_red": (np.array([175, 120, 100]), np.array([180, 255, 255]), 1.0),
        "secondary_black": (np.array([0, 0, 0]), np.array([180, 30, 60]), 0.7),
        "logo_white": (np.array([0, 0, 200]), np.array([180, 30, 255]), 0.3),
    },
    "Hilti": {
        "primary_red": (np.array([0, 150, 100]), np.array([10, 255, 255]), 1.0),
        "secondary_red": (np.array([175, 150, 100]), np.array([180, 255, 255]), 1.0),
        "logo_white": (np.array([0, 0, 200]), np.array([180, 30, 255]), 0.4),
    },
    "Festool": {
        "primary_green": (np.array([60, 50, 50]), np.array([80, 255, 255]), 1.0),
        "secondary_green": (np.array([70, 50, 50]), np.array([90, 255, 255]), 0.8),
        "logo_white": (np.array([0, 0, 200]), np.array([180, 30, 255]), 0.4),
    },
    "Hitachi": {
        "primary_green": (np.array([75, 80, 50]), np.array([95, 255, 255]), 1.0),
        "secondary_black": (np.array([0, 0, 0]), np.array([180, 30, 60]), 0.6),
        "logo_white": (np.array([0, 0, 200]), np.array([180, 30, 255]), 0.4),
    },
    "Ryobi": {
        "primary_green": (np.array([45, 100, 50]), np.array([65, 255, 255]), 1.0), # Более желтоватый зеленый
        "secondary_gray": (np.array([0, 0, 100]), np.array([180, 30, 180]), 0.5),
        "accent_black": (np.array([0, 0, 0]), np.array([180, 30, 60]), 0.3),
    },
    "Dremel": {
        "primary_blue": (np.array([85, 80, 50]), np.array([115, 255, 255]), 1.0),
        "secondary_gray": (np.array([0, 0, 100]), np.array([180, 30, 180]), 0.6),
        "accent_black": (np.array([0, 0, 0]), np.array([180, 30, 80]), 0.5),
    },
    "Интерскол": {
        "primary_red": (np.array([0, 120, 100]), np.array([10, 255, 255]), 1.0),
        "secondary_red": (np.array([175, 120, 100]), np.array([180, 255, 255]), 1.0),
        "secondary_gray": (np.array([0, 0, 100]), np.array([180, 30, 180]), 0.5),
        "accent_black": (np.array([0, 0, 0]), np.array([180, 30, 60]), 0.3),
    },
    "Зубр": {
        "primary_red": (np.array([0, 120, 100]), np.array([10, 255, 255]), 1.0),
        "secondary_red": (np.array([175, 120, 100]), np.array([180, 255, 255]), 1.0),
        "secondary_blue": (np.array([100, 50, 50]), np.array([130, 255, 255]), 0.6),
        "accent_black": (np.array([0, 0, 0]), np.array([180, 30, 60]), 0.3),
    },
    "Patriot": {
        "primary_red": (np.array([0, 100, 100]), np.array([10, 255, 255]), 1.0),
        "secondary_red": (np.array([175, 100, 100]), np.array([180, 255, 255]), 1.0),
        "secondary_blue": (np.array([100, 50, 50]), np.array([130, 255, 255]), 0.7),
        "accent_black": (np.array([0, 0, 0]), np.array([180, 30, 60]), 0.4),
    },
    "Bort": {
        "primary_green": (np.array([40, 80, 50]), np.array([70, 255, 255]), 0.8),
        "secondary_black": (np.array([0, 0, 0]), np.array([180, 30, 60]), 0.6),
        "accent_gray": (np.array([0, 0, 100]), np.array([180, 30, 180]), 0.4),
    },
    "Stihl": {
        "primary_orange": (np.array([10, 150, 100]), np.array([25, 255, 255]), 1.0),
        "secondary_gray": (np.array([0, 0, 100]), np.array([180, 30, 180]), 0.5),
        "accent_black": (np.array([0, 0, 0]), np.array([180, 30, 60]), 0.3),
    },
    "Karcher": {
        "primary_yellow": (np.array([25, 150, 100]), np.array([35, 255, 255]), 1.0),
        "secondary_black": (np.array([0, 0, 0]), np.array([180, 30, 60]), 0.7),
        "accent_gray": (np.array([0, 0, 100]), np.array([180, 30, 180]), 0.4),
    },
    "Flex": {
        "primary_red": (np.array([0, 120, 100]), np.array([10, 255, 255]), 1.0),
        "secondary_red": (np.array([175, 120, 100]), np.array([180, 255, 255]), 1.0),
        "secondary_black": (np.array([0, 0, 0]), np.array([180, 30, 60]), 0.7),
    },
    "Skil": {
        "primary_red": (np.array([0, 120, 100]), np.array([10, 255, 255]), 1.0),
        "secondary_red": (np.array([175, 120, 100]), np.array([180, 255, 255]), 1.0),
        "secondary_black": (np.array([0, 0, 0]), np.array([180, 30, 60]), 0.6),
        "accent_gray": (np.array([0, 0, 100]), np.array([180, 30, 180]), 0.4),
    },
    "Einhell": {
        "primary_red": (np.array([0, 120, 100]), np.array([10, 255, 255]), 1.0),
        "secondary_red": (np.array([175, 120, 100]), np.array([180, 255, 255]), 1.0),
        "secondary_black": (np.array([0, 0, 0]), np.array([180, 30, 60]), 0.6),
    }
}

class BrandRecognizer:
    """
    Класс для распознавания брендов строительных инструментов.
    """
    
    def __init__(self, brand_templates=None):
        """
        Инициализация распознавателя брендов.
        
        Args:
            brand_templates: Словарь шаблонов брендов или None для использования стандартного
        """
        self.brand_templates = brand_templates or BRAND_COLOR_TEMPLATES
        logger.info(f"Инициализирован распознаватель брендов с {len(self.brand_templates)} шаблонами")
    
    def recognize_brand_by_color(self, image_path: str, min_confidence: float = 0.35) -> Tuple[Optional[str], float]:
        """
        Распознает бренд инструмента по цветовой гамме изображения.
        
        Args:
            image_path: Путь к изображению
            min_confidence: Минимальный уровень уверенности для распознавания
            
        Returns:
            Кортеж (название_бренда, уверенность) или (None, 0.0) если бренд не определен
        """
        try:
            # Загружаем изображение
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"Не удалось загрузить изображение: {image_path}")
                return None, 0.0
            
            # Конвертируем в HSV для лучшего анализа цветов
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            # Получаем размеры изображения
            height, width = img.shape[:2]
            image_area = height * width
            
            # Словарь для хранения оценок брендов
            brand_scores = {}
            
            # Для каждого бренда вычисляем его оценку
            for brand, color_dict in self.brand_templates.items():
                # Общая оценка бренда
                brand_score = 0.0
                
                # Перебираем все цвета бренда
                for color_name, (lower_hsv, upper_hsv, weight) in color_dict.items():
                    # Создаем маску для текущего цвета
                    color_mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
                    
                    # Подсчитываем количество пикселей данного цвета
                    color_pixels = cv2.countNonZero(color_mask)
                    
                    # Вычисляем долю пикселей данного цвета от общей площади
                    color_percent = color_pixels / image_area
                    
                    # Добавляем к оценке бренда с учетом веса цвета
                    # Используем логарифмическую шкалу для уменьшения влияния очень больших областей
                    if color_percent > 0:
                        brand_score += (np.log1p(color_percent * 100) * weight)
                    
                    logger.debug(f"Бренд {brand}, цвет {color_name}: {color_percent:.4f} * {weight} = {color_percent * weight:.4f}")
                
                # Нормализуем оценку бренда (максимальная возможная оценка зависит от суммы весов)
                total_weight = sum(weight for _, _, weight in color_dict.values())
                if total_weight > 0:
                    brand_score = brand_score / (np.log1p(100) * total_weight)
                
                brand_scores[brand] = brand_score
                logger.debug(f"Общая оценка бренда {brand}: {brand_score:.4f}")
            
            # Находим бренд с максимальной оценкой
            if brand_scores:
                best_brand = max(brand_scores.items(), key=lambda x: x[1])
                brand_name, confidence = best_brand
                
                # Проверяем, превышает ли уверенность минимальный порог
                if confidence >= min_confidence:
                    logger.info(f"Распознан бренд {brand_name} с уверенностью {confidence:.4f}")
                    return brand_name, confidence
                else:
                    logger.info(f"Бренд не определен. Лучший кандидат {brand_name} с уверенностью {confidence:.4f} ниже порога {min_confidence}")
            
            return None, 0.0
        
        except Exception as e:
            logger.error(f"Ошибка при распознавании бренда: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None, 0.0
    
    def recognize_brand_from_filename(self, filename: str) -> str:
        """
        Определяет бренд инструмента по имени файла.
        
        Args:
            filename: Имя файла или путь к файлу
            
        Returns:
            Название бренда или "Неизвестный"
        """
        # Получаем только имя файла без пути
        basename = os.path.basename(filename).lower()
        
        # Словарь брендов и их вариаций в названиях файлов
        brands_variations = {
            "Makita": ["makita", "макита", "макитта"],
            "Bosch": ["bosch", "бош", "бошь", "бошь"],
            "DeWalt": ["dewalt", "девольт", "де вольт", "dewolt"],
            "Metabo": ["metabo", "метабо"],
            "Hilti": ["hilti", "хилти"],
            "Festool": ["festool", "фестул", "festtool"],
            "AEG": ["aeg", "аег", "аегь"],
            "Hitachi": ["hitachi", "хитачи", "хитачь"],
            "Milwaukee": ["milwaukee", "милуоки", "милвоки", "милвауки", "милуаке"],
            "Ryobi": ["ryobi", "риоби", "риобай", "ryob"],
            "Dremel": ["dremel", "дремел", "дремель"],
            "Интерскол": ["интерскол", "interscol", "интерскл"],
            "Зубр": ["zubr", "зубр", "zubp", "зубрь"],
            "Patriot": ["patriot", "патриот", "патриотт"],
            "Bort": ["bort", "борт", "борть"],
            "Stihl": ["stihl", "штиль", "стиль", "стил"],
            "Karcher": ["karcher", "керхер", "керхэр", "кёрхер", "карчер"],
            "Flex": ["flex", "флекс"],
            "Skil": ["skil", "скил", "скиль"],
            "Einhell": ["einhell", "айнхел", "айнхель", "einhel"],
        }
        
        # Проверяем наличие бренда в имени файла
        for brand, variations in brands_variations.items():
            for variation in variations:
                if variation in basename:
                    return brand
        
        return "Неизвестный"
    
    def enhance_recognition_with_filename(self, image_path: str, min_confidence: float = 0.35) -> Tuple[str, float]:
        """
        Комбинированное распознавание бренда по цвету и имени файла.
        
        Args:
            image_path: Путь к изображению
            min_confidence: Минимальный уровень уверенности для распознавания по цвету
            
        Returns:
            Кортеж (название_бренда, уверенность)
        """
        # Сначала пытаемся распознать по цвету с высокой уверенностью
        brand_by_color, confidence = self.recognize_brand_by_color(image_path, min_confidence)
        
        # Если бренд распознан по цвету с высокой уверенностью, возвращаем его
        if brand_by_color is not None and confidence >= min_confidence:
            return brand_by_color, confidence
        
        # Иначе проверяем имя файла
        brand_by_name = self.recognize_brand_from_filename(image_path)
        
        # Если бренд определен по имени файла
        if brand_by_name != "Неизвестный":
            # Если был также определен по цвету, но с низкой уверенностью
            if brand_by_color is not None:
                # Если бренды совпадают, повышаем уверенность
                if brand_by_color == brand_by_name:
                    return brand_by_name, max(confidence + 0.3, 0.9)  # Повышаем уверенность, но не более 0.9
                # Если бренды не совпадают, предпочитаем имя файла с умеренной уверенностью
                else:
                    return brand_by_name, 0.7
            # Если по цвету не определен, возвращаем бренд из имени файла с умеренной уверенностью
            else:
                return brand_by_name, 0.7
        
        # Если бренд не определен ни по цвету, ни по имени файла
        if brand_by_color is not None:
            # Возвращаем бренд по цвету с исходной низкой уверенностью
            return brand_by_color, confidence
        
        # Если бренд вообще не определен
        return "Неизвестный", 0.0


# Создаем глобальный экземпляр распознавателя
_brand_recognizer = None

def get_brand_recognizer() -> BrandRecognizer:
    """
    Получение экземпляра распознавателя брендов.
    
    Returns:
        Экземпляр BrandRecognizer
    """
    global _brand_recognizer
    if _brand_recognizer is None:
        _brand_recognizer = BrandRecognizer()
    return _brand_recognizer


def recognize_brand(image_path: str) -> Tuple[str, float]:
    """
    Распознавание бренда инструмента по изображению.
    
    Args:
        image_path: Путь к изображению
        
    Returns:
        Кортеж (название_бренда, уверенность)
    """
    recognizer = get_brand_recognizer()
    return recognizer.enhance_recognition_with_filename(image_path)


def get_known_brands() -> List[str]:
    """
    Получение списка известных брендов.
    
    Returns:
        Список названий брендов
    """
    return list(BRAND_COLOR_TEMPLATES.keys()) 