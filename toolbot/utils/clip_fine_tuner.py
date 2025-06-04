#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для тонкой настройки модели CLIP на специфических данных строительных инструментов.
"""

import os
import logging
import torch
import numpy as np
from pathlib import Path
from PIL import Image
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from transformers import CLIPProcessor, CLIPModel, CLIPTokenizerFast
from sklearn.model_selection import train_test_split
import shutil
import json
import tempfile
from tqdm import tqdm

logger = logging.getLogger(__name__)

class ToolImageDataset(Dataset):
    """
    Датасет для тонкой настройки модели CLIP на изображениях строительных инструментов.
    """
    def __init__(self, image_paths, text_labels, processor):
        """
        Инициализация датасета.
        
        Args:
            image_paths: Список путей к изображениям
            text_labels: Список текстовых описаний/меток для изображений
            processor: Процессор CLIP для предобработки изображений и текста
        """
        self.image_paths = image_paths
        self.text_labels = text_labels
        self.processor = processor
        
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        # Загружаем и предобрабатываем изображение
        image = Image.open(self.image_paths[idx]).convert('RGB')
        text = self.text_labels[idx]
        
        # Предобработка с помощью процессора CLIP
        inputs = self.processor(
            text=[text],
            images=image,
            return_tensors="pt",
            padding=True,
            truncation=True
        )
        
        # Удаляем размерность батча для возврата одного элемента
        inputs = {k: v.squeeze(0) if v.ndim > 1 else v for k, v in inputs.items()}
        
        return inputs


class CLIPFineTuner:
    """
    Класс для тонкой настройки модели CLIP на специфических данных.
    """
    def __init__(self, model_name="openai/clip-vit-base-patch32"):
        """
        Инициализация тюнера.
        
        Args:
            model_name: Название предобученной модели CLIP
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_name = model_name
        self.model = None
        self.processor = None
        self.tokenizer = None
        self.fine_tuned = False
        
        logger.info(f"Инициализация CLIPFineTuner с использованием {self.device}")
        
    def load_model(self):
        """
        Загрузка предобученной модели CLIP.
        
        Returns:
            True если загрузка успешна, иначе False
        """
        try:
            logger.info(f"Загрузка модели {self.model_name}...")
            self.processor = CLIPProcessor.from_pretrained(self.model_name)
            self.model = CLIPModel.from_pretrained(self.model_name)
            self.tokenizer = CLIPTokenizerFast.from_pretrained(self.model_name)
            
            # Перемещаем модель на GPU если доступна
            self.model = self.model.to(self.device)
            
            logger.info(f"Модель CLIP успешно загружена")
            return True
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {e}")
            return False
    
    def prepare_data(self, image_dir, categories_file=None, test_size=0.2):
        """
        Подготовка данных для тонкой настройки.
        
        Args:
            image_dir: Директория с изображениями для обучения
            categories_file: Путь к файлу с категориями инструментов в формате JSON
            test_size: Доля тестовых данных
            
        Returns:
            Кортеж (train_loader, val_loader) или None в случае ошибки
        """
        try:
            # Загружаем категории инструментов
            categories = {}
            if categories_file and os.path.exists(categories_file):
                with open(categories_file, 'r', encoding='utf-8') as f:
                    categories = json.load(f)
            
            # Собираем пути к изображениям и их метки
            image_paths = []
            text_labels = []
            
            for root, _, files in os.walk(image_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        # Получаем путь к файлу
                        img_path = os.path.join(root, file)
                        
                        # Получаем название категории из пути
                        rel_path = os.path.relpath(img_path, image_dir)
                        category = os.path.dirname(rel_path).split(os.sep)[0]
                        
                        # Если категория есть в словаре, используем её описание
                        if category in categories:
                            desc = categories[category]
                        else:
                            # Иначе используем название категории как метку
                            desc = f"изображение {category}"
                        
                        image_paths.append(img_path)
                        text_labels.append(desc)
            
            if not image_paths:
                logger.error(f"Не найдено изображений в директории {image_dir}")
                return None
            
            logger.info(f"Найдено {len(image_paths)} изображений для обучения")
            
            # Разделяем данные на обучающие и валидационные
            train_imgs, val_imgs, train_texts, val_texts = train_test_split(
                image_paths, text_labels, test_size=test_size, random_state=42
            )
            
            # Создаем датасеты
            train_dataset = ToolImageDataset(train_imgs, train_texts, self.processor)
            val_dataset = ToolImageDataset(val_imgs, val_texts, self.processor)
            
            # Создаем загрузчики данных
            train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True)
            val_loader = DataLoader(val_dataset, batch_size=8)
            
            logger.info(f"Данные подготовлены: {len(train_dataset)} обучающих, {len(val_dataset)} валидационных")
            return train_loader, val_loader
            
        except Exception as e:
            logger.error(f"Ошибка при подготовке данных: {e}")
            return None
    
    def fine_tune(self, train_loader, val_loader, epochs=3, learning_rate=5e-6):
        """
        Тонкая настройка модели CLIP.
        
        Args:
            train_loader: Загрузчик обучающих данных
            val_loader: Загрузчик валидационных данных
            epochs: Количество эпох обучения
            learning_rate: Скорость обучения
            
        Returns:
            True если настройка успешна, иначе False
        """
        try:
            if self.model is None and not self.load_model():
                return False
            
            # Подготавливаем оптимизатор
            optimizer = optim.AdamW(self.model.parameters(), lr=learning_rate)
            
            # Функция потерь (используем встроенную в модель CLIP)
            
            logger.info(f"Начинаем тонкую настройку модели на {epochs} эпох")
            
            # Основной цикл обучения
            best_loss = float('inf')
            for epoch in range(epochs):
                # Режим обучения
                self.model.train()
                train_loss = 0.0
                
                # Прогресс-бар для отслеживания обучения
                pbar = tqdm(train_loader, desc=f"Эпоха {epoch+1}/{epochs}")
                
                for batch in pbar:
                    # Перемещаем данные на устройство
                    input_ids = batch.get('input_ids', None)
                    pixel_values = batch.get('pixel_values', None)
                    attention_mask = batch.get('attention_mask', None)
                    
                    if input_ids is not None:
                        input_ids = input_ids.to(self.device)
                    if pixel_values is not None:
                        pixel_values = pixel_values.to(self.device)
                    if attention_mask is not None:
                        attention_mask = attention_mask.to(self.device)
                    
                    # Обнуляем градиенты
                    optimizer.zero_grad()
                    
                    # Прямой проход
                    outputs = self.model(
                        input_ids=input_ids,
                        pixel_values=pixel_values,
                        attention_mask=attention_mask,
                        return_loss=True
                    )
                    
                    loss = outputs.loss
                    
                    # Обратный проход
                    loss.backward()
                    
                    # Обновление весов
                    optimizer.step()
                    
                    # Накапливаем потери
                    train_loss += loss.item()
                    pbar.set_postfix({'loss': loss.item()})
                
                # Средняя потеря за эпоху
                avg_train_loss = train_loss / len(train_loader)
                
                # Валидация
                self.model.eval()
                val_loss = 0.0
                
                with torch.no_grad():
                    for batch in val_loader:
                        input_ids = batch.get('input_ids', None)
                        pixel_values = batch.get('pixel_values', None)
                        attention_mask = batch.get('attention_mask', None)
                        
                        if input_ids is not None:
                            input_ids = input_ids.to(self.device)
                        if pixel_values is not None:
                            pixel_values = pixel_values.to(self.device)
                        if attention_mask is not None:
                            attention_mask = attention_mask.to(self.device)
                        
                        outputs = self.model(
                            input_ids=input_ids,
                            pixel_values=pixel_values,
                            attention_mask=attention_mask,
                            return_loss=True
                        )
                        
                        val_loss += outputs.loss.item()
                
                avg_val_loss = val_loss / len(val_loader)
                
                logger.info(f"Эпоха {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}")
                
                # Сохраняем лучшую модель
                if avg_val_loss < best_loss:
                    best_loss = avg_val_loss
                    self.save_model("best_clip_model")
                    logger.info(f"Сохранена лучшая модель с валидационной потерей {best_loss:.4f}")
            
            self.fine_tuned = True
            logger.info(f"Тонкая настройка модели CLIP завершена. Лучшая потеря: {best_loss:.4f}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при тонкой настройке модели: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def save_model(self, output_dir):
        """
        Сохранение настроенной модели.
        
        Args:
            output_dir: Директория для сохранения модели
            
        Returns:
            Путь к сохраненной модели или None в случае ошибки
        """
        try:
            # Создаем временную директорию
            temp_dir = tempfile.mkdtemp()
            
            # Сохраняем модель и процессор
            self.model.save_pretrained(temp_dir)
            self.processor.save_pretrained(temp_dir)
            
            # Создаем директорию для сохранения если её нет
            os.makedirs(output_dir, exist_ok=True)
            
            # Перемещаем файлы модели
            for item in os.listdir(temp_dir):
                src = os.path.join(temp_dir, item)
                dst = os.path.join(output_dir, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
            
            # Удаляем временную директорию
            shutil.rmtree(temp_dir)
            
            logger.info(f"Модель сохранена в {output_dir}")
            return output_dir
        except Exception as e:
            logger.error(f"Ошибка при сохранении модели: {e}")
            return None
    
    def load_fine_tuned_model(self, model_dir):
        """
        Загрузка ранее настроенной модели.
        
        Args:
            model_dir: Директория с сохраненной моделью
            
        Returns:
            True если загрузка успешна, иначе False
        """
        try:
            logger.info(f"Загрузка настроенной модели из {model_dir}...")
            
            self.processor = CLIPProcessor.from_pretrained(model_dir)
            self.model = CLIPModel.from_pretrained(model_dir)
            
            # Перемещаем модель на GPU если доступна
            self.model = self.model.to(self.device)
            
            self.fine_tuned = True
            logger.info(f"Настроенная модель CLIP успешно загружена")
            return True
        except Exception as e:
            logger.error(f"Ошибка при загрузке настроенной модели: {e}")
            return False


# Функция для получения экземпляра тюнера
def get_clip_fine_tuner():
    """
    Получение экземпляра тюнера CLIP.
    
    Returns:
        Экземпляр CLIPFineTuner
    """
    return CLIPFineTuner()


# Функция для тонкой настройки модели CLIP
def fine_tune_clip_model(image_dir, categories_file=None, epochs=3, learning_rate=5e-6):
    """
    Тонкая настройка модели CLIP на пользовательских данных.
    
    Args:
        image_dir: Директория с изображениями для обучения
        categories_file: Путь к файлу с категориями инструментов
        epochs: Количество эпох обучения
        learning_rate: Скорость обучения
        
    Returns:
        Путь к сохраненной модели или None в случае ошибки
    """
    tuner = get_clip_fine_tuner()
    
    if not tuner.load_model():
        return None
    
    data = tuner.prepare_data(image_dir, categories_file)
    if data is None:
        return None
    
    train_loader, val_loader = data
    
    if not tuner.fine_tune(train_loader, val_loader, epochs, learning_rate):
        return None
    
    # Сохраняем модель в директории моделей
    model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "clip_fine_tuned")
    return tuner.save_model(model_dir) 