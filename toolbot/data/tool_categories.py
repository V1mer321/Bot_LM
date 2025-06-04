#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для работы с категориями инструментов.
Предоставляет функции для загрузки и получения категорий из JSON-файла.
"""

import os
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Путь к файлу с категориями относительно этого модуля
CATEGORIES_FILE = os.path.join(os.path.dirname(__file__), 'tool_categories.json')

# Кэш категорий для избежания повторного чтения файла
_tool_categories_cache = None


def get_tool_categories() -> Dict[str, str]:
    """
    Получает словарь категорий инструментов.
    
    Returns:
        Словарь категорий в формате {код_категории: описание}
    """
    global _tool_categories_cache
    
    # Если категории уже загружены, возвращаем их из кэша
    if _tool_categories_cache is not None:
        return _tool_categories_cache
    
    try:
        # Загружаем категории из файла
        if os.path.exists(CATEGORIES_FILE):
            with open(CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                _tool_categories_cache = json.load(f)
                logger.info(f"Загружены категории инструментов: {len(_tool_categories_cache)} категорий")
                return _tool_categories_cache
        else:
            logger.warning(f"Файл категорий не найден: {CATEGORIES_FILE}")
            # Возвращаем пустой словарь, если файл не найден
            _tool_categories_cache = {}
            return _tool_categories_cache
    except Exception as e:
        logger.error(f"Ошибка при загрузке категорий инструментов: {e}")
        # В случае ошибки возвращаем пустой словарь
        return {}


def get_category_description(category_code: str) -> Optional[str]:
    """
    Получает описание категории по ее коду.
    
    Args:
        category_code: Код категории
        
    Returns:
        Описание категории или None, если категория не найдена
    """
    categories = get_tool_categories()
    return categories.get(category_code)


def get_categories_list() -> List[str]:
    """
    Получает список кодов всех категорий.
    
    Returns:
        Список кодов категорий
    """
    return list(get_tool_categories().keys())


def get_category_by_name(name: str) -> Optional[str]:
    """
    Находит код категории по части названия или описания.
    
    Args:
        name: Часть названия или описания категории
        
    Returns:
        Код найденной категории или None, если категория не найдена
    """
    name = name.lower()
    categories = get_tool_categories()
    
    # Сначала ищем точное совпадение с кодом категории
    if name in categories:
        return name
    
    # Затем ищем в описаниях
    for code, description in categories.items():
        if name in description.lower() or name in code.lower():
            return code
    
    return None


if __name__ == "__main__":
    # Пример использования модуля
    print(f"Всего категорий: {len(get_categories_list())}")
    print(f"Категория 'дрель': {get_category_description('дрель')}")
    print(f"Поиск по названию 'перфоратор': {get_category_by_name('перфоратор')}") 