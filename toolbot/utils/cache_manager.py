#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Система кэширования для оптимизации обработки запросов.
Предоставляет функционал для сохранения и извлечения результатов поиска,
что позволяет избежать повторной обработки одинаковых запросов.
"""

import os
import time
import pickle
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import threading

logger = logging.getLogger(__name__)

class SearchCache:
    """
    Система кэширования результатов поиска изображений.
    Использует в памяти LRU-кэш и персистентное хранение на диске.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls, cache_dir="cache", max_memory_items=100, max_disk_items=1000, ttl=86400):
        """
        Получение экземпляра кэша (шаблон Singleton).
        
        Args:
            cache_dir: Директория для хранения файлов кэша
            max_memory_items: Максимальное количество элементов в памяти
            max_disk_items: Максимальное количество элементов на диске
            ttl: Время жизни элементов кэша в секундах (по умолчанию 24 часа)
            
        Returns:
            Экземпляр SearchCache
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(cache_dir, max_memory_items, max_disk_items, ttl)
        return cls._instance

    def __init__(self, cache_dir="cache", max_memory_items=100, max_disk_items=1000, ttl=86400):
        """
        Инициализация кэш-менеджера.
        
        Args:
            cache_dir: Директория для хранения файлов кэша
            max_memory_items: Максимальное количество элементов в памяти
            max_disk_items: Максимальное количество элементов на диске
            ttl: Время жизни элементов кэша в секундах (по умолчанию 24 часа)
        """
        self.cache_dir = cache_dir
        self.max_memory_items = max_memory_items
        self.max_disk_items = max_disk_items
        self.ttl = ttl
        
        # Кэш в памяти: {ключ: (время_последнего_доступа, данные)}
        self.memory_cache: Dict[str, Tuple[float, Any]] = {}
        
        # Создаем директорию кэша если не существует
        os.makedirs(cache_dir, exist_ok=True)
        
        # Загружаем метаданные кэша с диска
        self.metadata_path = os.path.join(cache_dir, "cache_metadata.pkl")
        self.load_metadata()
        
        logger.info(f"✅ Система кэширования инициализирована (TTL: {ttl}s, макс.элементов: {max_memory_items} в памяти, {max_disk_items} на диске)")

    def load_metadata(self):
        """Загрузка метаданных кэша с диска"""
        # Метаданные: {ключ: (время_создания, время_последнего_доступа, имя_файла)}
        self.metadata: Dict[str, Tuple[float, float, str]] = {}
        
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, 'rb') as f:
                    self.metadata = pickle.load(f)
                logger.debug(f"Загружены метаданные кэша: {len(self.metadata)} записей")
                
                # Очищаем просроченные элементы
                self._cleanup_expired()
            except Exception as e:
                logger.error(f"Ошибка при загрузке метаданных кэша: {e}")
                self.metadata = {}
    
    def save_metadata(self):
        """Сохранение метаданных кэша на диск"""
        try:
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)
            logger.debug(f"Сохранены метаданные кэша: {len(self.metadata)} записей")
        except Exception as e:
            logger.error(f"Ошибка при сохранении метаданных кэша: {e}")
    
    def _generate_key(self, image_path: str, params: Dict) -> str:
        """
        Генерирует уникальный ключ для запроса.
        
        Args:
            image_path: Путь к изображению
            params: Параметры поиска
            
        Returns:
            Уникальный ключ для запроса
        """
        # Получаем хеш содержимого файла
        try:
            with open(image_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Ошибка при генерации хеша файла {image_path}: {e}")
            # Если не удалось получить хеш содержимого, используем имя файла
            file_hash = hashlib.md5(image_path.encode()).hexdigest()
        
        # Сериализуем параметры запроса
        params_str = str(sorted(params.items()))
        
        # Объединяем хеш файла и параметры запроса
        key_str = f"{file_hash}_{params_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, image_path: str, params: Dict) -> Optional[List[Tuple[str, float]]]:
        """
        Получение результатов поиска из кэша.
        
        Args:
            image_path: Путь к изображению
            params: Параметры поиска
            
        Returns:
            Список найденных изображений и уровней схожести,
            или None если результат не найден в кэше
        """
        key = self._generate_key(image_path, params)
        current_time = time.time()
        
        # Проверяем кэш в памяти
        if key in self.memory_cache:
            last_access, data = self.memory_cache[key]
            # Обновляем время последнего доступа
            self.memory_cache[key] = (current_time, data)
            
            # Обновляем метаданные на диске
            if key in self.metadata:
                created_time, _, file_path = self.metadata[key]
                self.metadata[key] = (created_time, current_time, file_path)
                self.save_metadata()
                
            logger.debug(f"✓ Результат найден в памяти для ключа {key[:8]}...")
            return data
        
        # Проверяем кэш на диске
        if key in self.metadata:
            created_time, last_access_time, file_path = self.metadata[key]
            
            # Проверяем срок действия
            if current_time - created_time > self.ttl:
                # Удаляем просроченный элемент
                logger.debug(f"Удален просроченный элемент кэша: {key[:8]}...")
                self._remove_from_disk(key)
                return None
            
            # Загружаем данные с диска
            try:
                cache_file = os.path.join(self.cache_dir, file_path)
                if os.path.exists(cache_file):
                    with open(cache_file, 'rb') as f:
                        data = pickle.load(f)
                    
                    # Добавляем в память для быстрого доступа
                    self._add_to_memory(key, data)
                    
                    # Обновляем время последнего доступа в метаданных
                    self.metadata[key] = (created_time, current_time, file_path)
                    self.save_metadata()
                    
                    logger.debug(f"✓ Результат загружен с диска для ключа {key[:8]}...")
                    return data
                else:
                    # Файл не найден, удаляем запись из метаданных
                    logger.warning(f"Файл кэша не найден: {cache_file}")
                    del self.metadata[key]
                    self.save_metadata()
            except Exception as e:
                logger.error(f"Ошибка при загрузке кэша с диска: {e}")
                # Удаляем повреждённую запись
                self._remove_from_disk(key)
        
        return None
    
    def set(self, image_path: str, params: Dict, results: List[Tuple[str, float]]) -> None:
        """
        Сохранение результатов поиска в кэш.
        
        Args:
            image_path: Путь к изображению
            params: Параметры поиска
            results: Результаты поиска (список кортежей путь-схожесть)
        """
        key = self._generate_key(image_path, params)
        current_time = time.time()
        
        # Добавляем в память
        self._add_to_memory(key, results)
        
        # Сохраняем на диск
        try:
            # Генерируем имя файла
            file_name = f"{key}.pkl"
            file_path = os.path.join(self.cache_dir, file_name)
            
            # Записываем данные
            with open(file_path, 'wb') as f:
                pickle.dump(results, f)
            
            # Обновляем метаданные
            self.metadata[key] = (current_time, current_time, file_name)
            
            # Выполняем очистку диска если превышен лимит
            if len(self.metadata) > self.max_disk_items:
                self._cleanup_disk()
                
            # Сохраняем обновленные метаданные
            self.save_metadata()
            
            logger.debug(f"✓ Результат сохранен в кэш для ключа {key[:8]}...")
        except Exception as e:
            logger.error(f"Ошибка при сохранении кэша на диск: {e}")
    
    def invalidate(self, image_path: str = None) -> None:
        """
        Инвалидация кэша для конкретного изображения или всего кэша.
        
        Args:
            image_path: Путь к изображению для инвалидации 
                        (если None, инвалидируется весь кэш)
        """
        if image_path is None:
            # Очищаем весь кэш
            self.memory_cache.clear()
            
            # Удаляем все файлы кэша на диске
            for key, (_, _, file_name) in self.metadata.items():
                file_path = os.path.join(self.cache_dir, file_name)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.error(f"Ошибка при удалении файла кэша {file_path}: {e}")
            
            # Очищаем метаданные
            self.metadata.clear()
            self.save_metadata()
            
            logger.info("Весь кэш поиска очищен")
        else:
            # Формируем префикс ключа для данного изображения
            try:
                with open(image_path, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
            except Exception:
                file_hash = hashlib.md5(image_path.encode()).hexdigest()
            
            # Удаляем все записи, начинающиеся с этого хеша
            keys_to_remove = []
            
            # Находим все ключи для этого изображения
            for key in list(self.memory_cache.keys()):
                if key.startswith(file_hash):
                    keys_to_remove.append(key)
                    del self.memory_cache[key]
            
            for key in list(self.metadata.keys()):
                if key.startswith(file_hash):
                    keys_to_remove.append(key)
                    self._remove_from_disk(key)
            
            if keys_to_remove:
                logger.info(f"Очищен кэш для изображения {os.path.basename(image_path)} ({len(keys_to_remove)} записей)")
    
    def _add_to_memory(self, key: str, data: Any) -> None:
        """
        Добавление данных в память.
        
        Args:
            key: Ключ кэша
            data: Данные для сохранения
        """
        current_time = time.time()
        
        # Если превышен лимит элементов в памяти, удаляем самый старый
        if len(self.memory_cache) >= self.max_memory_items:
            oldest_key = min(self.memory_cache.keys(), key=lambda k: self.memory_cache[k][0])
            del self.memory_cache[oldest_key]
            logger.debug(f"Удален самый старый элемент из памяти: {oldest_key[:8]}...")
        
        # Добавляем новый элемент
        self.memory_cache[key] = (current_time, data)
    
    def _remove_from_disk(self, key: str) -> None:
        """
        Удаление элемента с диска.
        
        Args:
            key: Ключ кэша для удаления
        """
        if key in self.metadata:
            _, _, file_name = self.metadata[key]
            file_path = os.path.join(self.cache_dir, file_name)
            
            # Удаляем файл
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.error(f"Ошибка при удалении файла кэша {file_path}: {e}")
            
            # Удаляем из метаданных
            del self.metadata[key]
    
    def _cleanup_expired(self) -> None:
        """Очистка просроченных элементов кэша"""
        current_time = time.time()
        expired_keys = []
        
        # Находим просроченные элементы
        for key, (created_time, _, _) in self.metadata.items():
            if current_time - created_time > self.ttl:
                expired_keys.append(key)
        
        # Удаляем просроченные элементы
        for key in expired_keys:
            self._remove_from_disk(key)
        
        if expired_keys:
            logger.info(f"Очищены просроченные элементы кэша: {len(expired_keys)} записей")
            self.save_metadata()
    
    def _cleanup_disk(self) -> None:
        """Очистка диска при превышении лимита элементов"""
        # Сортируем элементы по времени последнего доступа (от старых к новым)
        sorted_items = sorted(self.metadata.items(), key=lambda x: x[1][1])
        
        # Определяем количество элементов для удаления
        items_to_remove = max(len(sorted_items) - self.max_disk_items, 
                             len(sorted_items) // 4)  # Удаляем минимум 25% при очистке
        
        # Удаляем старые элементы
        for i in range(items_to_remove):
            key, _ = sorted_items[i]
            self._remove_from_disk(key)
        
        logger.info(f"Выполнена очистка кэша на диске: удалено {items_to_remove} записей")
        self.save_metadata()
    
    def get_stats(self) -> Dict:
        """
        Получение статистики использования кэша.
        
        Returns:
            Словарь со статистикой кэша
        """
        return {
            "memory_items": len(self.memory_cache),
            "disk_items": len(self.metadata),
            "memory_limit": self.max_memory_items,
            "disk_limit": self.max_disk_items,
            "ttl": self.ttl,
            "cache_dir": self.cache_dir
        }


# Функции-обертки для обратной совместимости с существующим кодом

def get_search_cache(cache_dir="cache", max_memory_items=100, max_disk_items=1000, ttl=86400):
    """
    Получение экземпляра кэша поиска.
    
    Args:
        cache_dir: Директория для хранения файлов кэша
        max_memory_items: Максимальное количество элементов в памяти
        max_disk_items: Максимальное количество элементов на диске
        ttl: Время жизни элементов кэша в секундах (по умолчанию 24 часа)
        
    Returns:
        Экземпляр SearchCache
    """
    return SearchCache.get_instance(cache_dir, max_memory_items, max_disk_items, ttl)

def get_cached_search_results(image_path, params):
    """
    Получение кэшированных результатов поиска.
    
    Args:
        image_path: Путь к изображению
        params: Параметры поиска
        
    Returns:
        Результаты поиска или None если не найдены в кэше
    """
    cache = get_search_cache()
    return cache.get(image_path, params)

def cache_search_results(image_path, params, results):
    """
    Сохранение результатов поиска в кэш.
    
    Args:
        image_path: Путь к изображению
        params: Параметры поиска
        results: Результаты поиска
    """
    cache = get_search_cache()
    cache.set(image_path, params, results)

def invalidate_cache(image_path=None):
    """
    Инвалидация кэша для конкретного изображения или всего кэша.
    
    Args:
        image_path: Путь к изображению для инвалидации
                    (если None, инвалидируется весь кэш)
    """
    cache = get_search_cache()
    cache.invalidate(image_path)

def get_cache_stats():
    """
    Получение статистики использования кэша.
    
    Returns:
        Словарь со статистикой кэша
    """
    cache = get_search_cache()
    return cache.get_stats() 