#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Оптимизатор моделей машинного обучения.
Предоставляет функции для оптимизации производительности моделей CLIP, ResNet и других.
Включает квантизацию, JIT-компиляцию и другие методы ускорения.
"""

import os
import logging
import torch
import numpy as np
from typing import Dict, Any, Optional, Tuple, List, Union
from pathlib import Path
import time

logger = logging.getLogger(__name__)

class ModelOptimizer:
    """
    Класс для оптимизации моделей машинного обучения.
    Поддерживает квантизацию, JIT-компиляцию и другие методы оптимизации.
    """
    
    # Поддерживаемые типы оптимизации
    OPTIMIZATION_TYPES = {
        'none': 'Без оптимизации',
        'quantization': 'Квантизация (8/16 бит)',
        'jit': 'JIT-компиляция',
        'jit_quantization': 'JIT-компиляция + квантизация',
        'onnx': 'Конвертация в ONNX'
    }
    
    def __init__(self):
        """Инициализация оптимизатора моделей"""
        # Проверяем доступность CUDA
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.cuda_available = torch.cuda.is_available()
        
        # Отслеживаем модели, которые уже оптимизированы
        self.optimized_models = {}
        
        if self.cuda_available:
            logger.info(f"✅ Оптимизатор моделей инициализирован с использованием CUDA")
            logger.info(f"   - GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"   - CUDA версия: {torch.version.cuda}")
            logger.info(f"   - Доступная память: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} ГБ")
        else:
            logger.info(f"✅ Оптимизатор моделей инициализирован с использованием CPU")
    
    def optimize_clip_model(self, model, optimization_type='quantization', optimize_processor=True):
        """
        Оптимизация модели CLIP для более быстрой работы.
        
        Args:
            model: Модель CLIP для оптимизации
            optimization_type: Тип оптимизации ('none', 'quantization', 'jit', 'jit_quantization')
            optimize_processor: Оптимизировать ли также процессор CLIP
            
        Returns:
            Оптимизированная модель CLIP
        """
        if optimization_type not in self.OPTIMIZATION_TYPES:
            logger.warning(f"Неизвестный тип оптимизации: {optimization_type}, используется 'none'")
            optimization_type = 'none'
        
        # Проверяем, была ли модель уже оптимизирована
        model_id = id(model)
        if model_id in self.optimized_models:
            logger.info(f"✓ Модель уже оптимизирована ({self.OPTIMIZATION_TYPES[optimization_type]})")
            return self.optimized_models[model_id]
        
        # Переводим модель в режим оценки
        model.eval()
        
        # Оптимизация в зависимости от выбранного типа
        if optimization_type == 'none':
            # Просто переносим модель на GPU если доступна
            if self.cuda_available:
                model = model.to(self.device)
            
            logger.info("✓ Модель перенесена на оптимальное устройство без дополнительной оптимизации")
        
        elif optimization_type == 'quantization':
            # Квантизация модели
            try:
                # Сначала переносим на GPU если доступна
                if self.cuda_available:
                    model = model.to(self.device)
                
                # Квантизация для CPU
                if not self.cuda_available:
                    # Квантизация до int8 (только для CPU)
                    model_fp32 = model
                    model_int8 = torch.quantization.quantize_dynamic(
                        model_fp32, 
                        {torch.nn.Linear}, 
                        dtype=torch.qint8
                    )
                    model = model_int8
                    logger.info("✓ Модель квантизована до 8 бит (CPU)")
                else:
                    # Для CUDA используем half precision (FP16)
                    model = model.half()
                    logger.info("✓ Модель конвертирована в half precision (FP16) для GPU")
            except Exception as e:
                logger.error(f"Ошибка при квантизации модели: {e}")
                # Возвращаемся к обычной модели
                if self.cuda_available:
                    model = model.to(self.device)
        
        elif optimization_type == 'jit':
            # JIT-компиляция модели
            try:
                # Подготавливаем пример входных данных для трассировки
                example_input = torch.randn(1, 3, 224, 224)
                if self.cuda_available:
                    example_input = example_input.to(self.device)
                    model = model.to(self.device)
                
                # Делаем трассировку модели
                with torch.no_grad():
                    traced_model = torch.jit.trace(model, example_input)
                
                # Оптимизируем трассированную модель
                model = torch.jit.optimize_for_inference(traced_model)
                
                logger.info("✓ Модель JIT-скомпилирована для ускорения вывода")
            except Exception as e:
                logger.error(f"Ошибка при JIT-компиляции модели: {e}")
                # Возвращаемся к обычной модели
                if self.cuda_available:
                    model = model.to(self.device)
        
        elif optimization_type == 'jit_quantization':
            # Комбинация JIT и квантизации
            try:
                # Подготавливаем пример входных данных для трассировки
                example_input = torch.randn(1, 3, 224, 224)
                if self.cuda_available:
                    example_input = example_input.to(self.device)
                    model = model.to(self.device)
                    # Для CUDA используем half precision
                    model = model.half()
                    example_input = example_input.half()
                
                # Делаем трассировку модели
                with torch.no_grad():
                    traced_model = torch.jit.trace(model, example_input)
                
                # Оптимизируем трассированную модель
                model = torch.jit.optimize_for_inference(traced_model)
                
                logger.info("✓ Модель JIT-скомпилирована и квантизована")
            except Exception as e:
                logger.error(f"Ошибка при JIT-компиляции с квантизацией: {e}")
                # Возвращаемся к обычной модели, но с half precision если возможно
                if self.cuda_available:
                    model = model.to(self.device).half()
                else:
                    model = model.to(self.device)
        
        # Добавляем оптимизированную модель в кэш
        self.optimized_models[model_id] = model
        
        return model
    
    def optimize_batch_processing(self, image_paths, batch_size=4):
        """
        Группировка изображений в пакеты для более эффективной обработки.
        
        Args:
            image_paths: Список путей к изображениям
            batch_size: Размер пакета для обработки
            
        Returns:
            Список пакетов изображений
        """
        # Группируем изображения в пакеты
        image_batches = []
        for i in range(0, len(image_paths), batch_size):
            image_batches.append(image_paths[i:i+batch_size])
        
        logger.debug(f"Изображения разбиты на {len(image_batches)} пакетов по {batch_size} шт.")
        return image_batches
    
    def measure_inference_time(self, model, input_data, num_iterations=10):
        """
        Измерение времени вывода модели.
        
        Args:
            model: Модель для измерения
            input_data: Входные данные для модели
            num_iterations: Количество итераций для усреднения
            
        Returns:
            Среднее время вывода в миллисекундах
        """
        # Переводим модель в режим оценки
        model.eval()
        
        # Прогреваем модель
        with torch.no_grad():
            _ = model(input_data)
        
        # Синхронизируем CUDA, если используется
        if self.cuda_available:
            torch.cuda.synchronize()
        
        # Измеряем время
        start_time = time.time()
        with torch.no_grad():
            for _ in range(num_iterations):
                _ = model(input_data)
                # Синхронизируем CUDA, если используется
                if self.cuda_available:
                    torch.cuda.synchronize()
        
        end_time = time.time()
        inference_time = (end_time - start_time) * 1000 / num_iterations  # в миллисекундах
        
        return inference_time


# Создаем глобальный экземпляр оптимизатора
optimizer = None

def get_model_optimizer():
    """
    Получение экземпляра оптимизатора моделей.
    
    Returns:
        Экземпляр ModelOptimizer
    """
    global optimizer
    if optimizer is None:
        optimizer = ModelOptimizer()
    return optimizer

def optimize_clip_model(model, optimization_type='quantization', optimize_processor=True):
    """
    Оптимизация модели CLIP.
    
    Args:
        model: Модель CLIP для оптимизации
        optimization_type: Тип оптимизации
        optimize_processor: Оптимизировать ли также процессор CLIP
        
    Returns:
        Оптимизированная модель CLIP
    """
    opt = get_model_optimizer()
    return opt.optimize_clip_model(model, optimization_type, optimize_processor)

def optimize_batch_processing(image_paths, batch_size=4):
    """
    Группировка изображений в пакеты для более эффективной обработки.
    
    Args:
        image_paths: Список путей к изображениям
        batch_size: Размер пакета для обработки
        
    Returns:
        Список пакетов изображений
    """
    opt = get_model_optimizer()
    return opt.optimize_batch_processing(image_paths, batch_size)

def measure_inference_time(model, input_data, num_iterations=10):
    """
    Измерение времени вывода модели.
    
    Args:
        model: Модель для измерения
        input_data: Входные данные для модели
        num_iterations: Количество итераций для усреднения
        
    Returns:
        Среднее время вывода в миллисекундах
    """
    opt = get_model_optimizer()
    return opt.measure_inference_time(model, input_data, num_iterations) 