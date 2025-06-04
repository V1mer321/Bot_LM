#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Асинхронный процессор запросов для оптимизации обработки множественных запросов.
Обеспечивает параллельное выполнение задач поиска изображений и другой тяжелой обработки.
"""

import os
import asyncio
import logging
import threading
import concurrent.futures
from typing import List, Callable, Dict, Any, Tuple, Optional, Coroutine, Union
import time
import functools

logger = logging.getLogger(__name__)

class AsyncRequestProcessor:
    """
    Процессор асинхронных запросов для параллельной обработки задач.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls, max_workers=None):
        """
        Получение экземпляра процессора (шаблон Singleton).
        
        Args:
            max_workers: Максимальное количество рабочих потоков 
                         (если None, будет использоваться оптимальное значение)
            
        Returns:
            Экземпляр AsyncRequestProcessor
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(max_workers)
        return cls._instance
    
    def __init__(self, max_workers=None):
        """
        Инициализация процессора запросов.
        
        Args:
            max_workers: Максимальное количество рабочих потоков 
                         (если None, будет использоваться оптимальное значение)
        """
        # Если max_workers не указано, используем оптимальное значение
        # (кол-во процессоров + 4 для I/O операций)
        if max_workers is None:
            import multiprocessing
            max_workers = min(multiprocessing.cpu_count() + 4, 32)  # Максимум 32 потока
        
        self.max_workers = max_workers
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        
        # Для отслеживания активных задач
        self.active_tasks = 0
        self.active_tasks_lock = threading.Lock()
        
        logger.info(f"✅ Асинхронный процессор запросов инициализирован (макс. потоков: {max_workers})")
    
    async def process_in_thread(self, func, *args, **kwargs):
        """
        Выполняет функцию в отдельном потоке, не блокируя основной поток.
        
        Args:
            func: Функция для выполнения
            *args, **kwargs: Аргументы для функции
            
        Returns:
            Результат выполнения функции
        """
        with self.active_tasks_lock:
            self.active_tasks += 1
        
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                self.thread_pool, 
                functools.partial(func, *args, **kwargs)
            )
            return result
        finally:
            with self.active_tasks_lock:
                self.active_tasks -= 1
    
    async def process_multiple(self, func, items, *args, **kwargs):
        """
        Параллельная обработка списка элементов.
        
        Args:
            func: Функция для обработки одного элемента
            items: Список элементов для обработки
            *args, **kwargs: Дополнительные аргументы для функции
            
        Returns:
            Список результатов обработки
        """
        if not items:
            return []
        
        # Создаем список задач
        tasks = []
        for item in items:
            # Создаем отдельные аргументы для каждого элемента
            item_args = list(args)  # Копируем базовые аргументы
            
            # Если первый аргумент функции - это элемент (наиболее частый случай)
            task = self.process_in_thread(func, item, *item_args, **kwargs)
            tasks.append(task)
        
        # Выполняем все задачи параллельно
        results = await asyncio.gather(*tasks)
        return results
    
    def run_async(self, coroutine):
        """
        Запускает асинхронную корутину.
        Проверяет, есть ли уже работающий event loop.
        
        Args:
            coroutine: Корутина для выполнения
            
        Returns:
            Результат выполнения корутины
        """
        try:
            # Проверяем, есть ли уже работающий event loop
            loop = asyncio.get_running_loop()
            # Если есть, создаем задачу и возвращаем future
            task = loop.create_task(coroutine)
            return task
        except RuntimeError:
            # Если нет активного loop, используем asyncio.run
            return asyncio.run(coroutine)
    
    def process_sync(self, func, *args, **kwargs):
        """
        Синхронная обертка для выполнения функции в пуле потоков.
        
        Args:
            func: Функция для выполнения
            *args, **kwargs: Аргументы для функции
            
        Returns:
            Результат выполнения функции
        """
        # Просто выполняем функцию в пуле потоков, но синхронно
        future = self.thread_pool.submit(func, *args, **kwargs)
        return future.result()
    
    def process_multiple_sync(self, func, items, *args, **kwargs):
        """
        Синхронная обертка для параллельной обработки списка элементов.
        
        Args:
            func: Функция для обработки одного элемента
            items: Список элементов для обработки
            *args, **kwargs: Дополнительные аргументы для функции
            
        Returns:
            Список результатов обработки
        """
        try:
            # Проверяем, есть ли уже работающий event loop
            loop = asyncio.get_running_loop()
            # Если есть, то нельзя использовать синхронный запуск
            # Возвращаем задачу, которую нужно будет await'ить
            logger.warning("process_multiple_sync вызван в асинхронном контексте. Используйте process_multiple вместо этого.")
            return self.process_multiple(func, items, *args, **kwargs)
        except RuntimeError:
            # Если нет активного loop, используем асинхронную версию через run_async
            return self.run_async(self.process_multiple(func, items, *args, **kwargs))
    
    def get_stats(self):
        """
        Получение статистики использования процессора.
        
        Returns:
            Словарь со статистикой
        """
        return {
            "max_workers": self.max_workers,
            "active_tasks": self.active_tasks
        }


# Функции-обертки для обратной совместимости с существующим кодом

def get_async_processor(max_workers=None):
    """
    Получение экземпляра асинхронного процессора.
    
    Args:
        max_workers: Максимальное количество рабочих потоков
        
    Returns:
        Экземпляр AsyncRequestProcessor
    """
    return AsyncRequestProcessor.get_instance(max_workers)

async def process_in_thread(func, *args, **kwargs):
    """
    Выполняет функцию в отдельном потоке, не блокируя основной поток.
    
    Args:
        func: Функция для выполнения
        *args, **kwargs: Аргументы для функции
        
    Returns:
        Результат выполнения функции
    """
    processor = get_async_processor()
    return await processor.process_in_thread(func, *args, **kwargs)

async def process_multiple(func, items, *args, **kwargs):
    """
    Параллельная обработка списка элементов.
    
    Args:
        func: Функция для обработки одного элемента
        items: Список элементов для обработки
        *args, **kwargs: Дополнительные аргументы для функции
        
    Returns:
        Список результатов обработки
    """
    processor = get_async_processor()
    return await processor.process_multiple(func, items, *args, **kwargs)

def process_sync(func, *args, **kwargs):
    """
    Синхронная обертка для выполнения функции в пуле потоков.
    
    Args:
        func: Функция для выполнения
        *args, **kwargs: Аргументы для функции
        
    Returns:
        Результат выполнения функции
    """
    processor = get_async_processor()
    return processor.process_sync(func, *args, **kwargs)

def process_multiple_sync(func, items, *args, **kwargs):
    """
    Синхронная обертка для параллельной обработки списка элементов.
    
    Args:
        func: Функция для обработки одного элемента
        items: Список элементов для обработки
        *args, **kwargs: Дополнительные аргументы для функции
        
    Returns:
        Список результатов обработки
    """
    processor = get_async_processor()
    return processor.process_multiple_sync(func, items, *args, **kwargs) 