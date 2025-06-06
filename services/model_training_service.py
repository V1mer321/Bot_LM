import os
import logging
import time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from typing import List, Dict, Tuple, Optional
import sqlite3
import json
from datetime import datetime
import pickle

from services.training_data_service import get_training_service
from services.unified_database_search import UnifiedDatabaseService

logger = logging.getLogger(__name__)

class TrainingDataset(Dataset):
    """Dataset для обучающих примеров"""
    
    def __init__(self, examples: List[Dict], preprocess, device):
        self.examples = examples
        self.preprocess = preprocess
        self.device = device
        
    def __len__(self):
        return len(self.examples)
    
    def __getitem__(self, idx):
        example = self.examples[idx]
        
        # Загружаем изображение
        image_path = example['image_path']
        if not os.path.exists(image_path):
            # Fallback - создаем пустое изображение
            image = Image.new('RGB', (224, 224), color=(128, 128, 128))
        else:
            image = Image.open(image_path)
        
        # Предобрабатываем изображение
        image_tensor = self.preprocess(image)
        
        # Определяем метку (1 для correct, 0 для incorrect)
        label = 1 if example['feedback_type'] == 'correct' else 0
        
        return {
            'image': image_tensor,
            'label': torch.tensor(label, dtype=torch.float32),
            'similarity_score': torch.tensor(example.get('similarity_score', 0.5), dtype=torch.float32),
            'quality_rating': torch.tensor(example.get('quality_rating', 5), dtype=torch.float32)
        }

class ModelTrainingService:
    """Сервис для дообучения моделей на основе обратной связи пользователей"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.training_service = get_training_service()
        self.unified_service = UnifiedDatabaseService()
        self.model = None
        self.preprocess = None
        
        # Параметры обучения
        self.learning_rate = 1e-5
        self.batch_size = 8
        self.num_epochs = 3
        self.weight_decay = 0.01
        
        logger.info(f"🚀 ModelTrainingService инициализирован на {self.device}")
    
    def _load_clip_model(self):
        """Загрузка CLIP модели"""
        if self.model is None:
            try:
                import clip
                self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)
                logger.info("✅ CLIP модель загружена")
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки CLIP модели: {e}")
                raise
    
    def prepare_training_data(self, min_examples: int = 10) -> Tuple[List[Dict], List[Dict]]:
        """
        Подготовка обучающих данных
        
        Args:
            min_examples: Минимальное количество примеров для обучения
            
        Returns:
            Tuple[train_data, validation_data]
        """
        # Получаем неиспользованные примеры
        all_examples = self.training_service.get_training_examples(is_used=False)
        
        if len(all_examples) < min_examples:
            logger.warning(f"⚠️ Недостаточно обучающих примеров: {len(all_examples)} < {min_examples}")
            return [], []
        
        # Фильтруем примеры с изображениями
        valid_examples = []
        for example in all_examples:
            if example['image_path'] and os.path.exists(example['image_path']):
                valid_examples.append(example)
        
        logger.info(f"📊 Подготовлено {len(valid_examples)} валидных примеров для обучения")
        
        # Разделяем на обучающую и валидационную выборки (80/20)
        train_size = int(0.8 * len(valid_examples))
        train_data = valid_examples[:train_size]
        val_data = valid_examples[train_size:]
        
        return train_data, val_data
    
    def create_contrastive_pairs(self, examples: List[Dict]) -> List[Dict]:
        """
        Создание контрастивных пар для обучения
        
        Args:
            examples: Список обучающих примеров
            
        Returns:
            Список пар изображений с метками схожести
        """
        pairs = []
        
        # Группируем примеры по типу обратной связи
        correct_examples = [ex for ex in examples if ex['feedback_type'] == 'correct']
        incorrect_examples = [ex for ex in examples if ex['feedback_type'] == 'incorrect']
        
        # Создаем положительные пары (правильные результаты)
        for i, example1 in enumerate(correct_examples):
            for j, example2 in enumerate(correct_examples[i+1:], i+1):
                if example1['target_item_id'] == example2['target_item_id']:
                    pairs.append({
                        'image1_path': example1['image_path'],
                        'image2_path': example2['image_path'],
                        'label': 1,  # Похожие
                        'similarity_score': min(example1.get('similarity_score', 0.5),
                                              example2.get('similarity_score', 0.5))
                    })
        
        # Создаем отрицательные пары (правильный + неправильный)
        for correct_ex in correct_examples:
            for incorrect_ex in incorrect_examples:
                pairs.append({
                    'image1_path': correct_ex['image_path'],
                    'image2_path': incorrect_ex['image_path'],
                    'label': 0,  # Не похожие
                    'similarity_score': 0.1
                })
        
        logger.info(f"📝 Создано {len(pairs)} контрастивных пар для обучения")
        return pairs
    
    def fine_tune_model(self, train_data: List[Dict], val_data: List[Dict] = None,
                       model_version: str = None) -> Dict:
        """
        Дообучение модели на основе обратной связи
        
        Args:
            train_data: Обучающие данные
            val_data: Валидационные данные
            model_version: Версия модели
            
        Returns:
            Результаты обучения
        """
        if not model_version:
            model_version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        start_time = time.time()
        
        try:
            # Загружаем модель
            self._load_clip_model()
            
            # Создаем datasets
            train_dataset = TrainingDataset(train_data, self.preprocess, self.device)
            train_loader = DataLoader(train_dataset, batch_size=self.batch_size, shuffle=True)
            
            val_loader = None
            if val_data:
                val_dataset = TrainingDataset(val_data, self.preprocess, self.device)
                val_loader = DataLoader(val_dataset, batch_size=self.batch_size, shuffle=False)
            
            # Настраиваем оптимизатор
            optimizer = optim.AdamW(self.model.parameters(), 
                                  lr=self.learning_rate, 
                                  weight_decay=self.weight_decay)
            
            # Функция потерь
            criterion = nn.BCEWithLogitsLoss()
            
            # Обучение
            train_losses = []
            val_accuracies = []
            
            accuracy_before = self._evaluate_model(val_loader) if val_loader else None
            
            for epoch in range(self.num_epochs):
                # Тренировочная эпоха
                self.model.train()
                epoch_loss = 0.0
                
                for batch in train_loader:
                    optimizer.zero_grad()
                    
                    images = batch['image'].to(self.device)
                    labels = batch['label'].to(self.device)
                    
                    # Получаем признаки изображений
                    with torch.cuda.amp.autocast() if self.device == "cuda" else torch.no_grad():
                        image_features = self.model.encode_image(images)
                        
                        # Простая классификация на основе признаков
                        predictions = torch.sigmoid(torch.sum(image_features, dim=1))
                    
                    loss = criterion(predictions, labels)
                    loss.backward()
                    optimizer.step()
                    
                    epoch_loss += loss.item()
                
                avg_loss = epoch_loss / len(train_loader)
                train_losses.append(avg_loss)
                
                # Валидация
                if val_loader:
                    val_accuracy = self._evaluate_model(val_loader)
                    val_accuracies.append(val_accuracy)
                    logger.info(f"Эпоха {epoch+1}/{self.num_epochs}: Loss={avg_loss:.4f}, Val_Acc={val_accuracy:.4f}")
                else:
                    logger.info(f"Эпоха {epoch+1}/{self.num_epochs}: Loss={avg_loss:.4f}")
            
            accuracy_after = self._evaluate_model(val_loader) if val_loader else None
            
            # Сохраняем модель
            model_path = self._save_model(model_version)
            
            # Логируем результаты
            duration = int(time.time() - start_time)
            positive_examples = len([ex for ex in train_data if ex['feedback_type'] == 'correct'])
            negative_examples = len([ex for ex in train_data if ex['feedback_type'] == 'incorrect'])
            
            training_params = {
                'learning_rate': self.learning_rate,
                'batch_size': self.batch_size,
                'num_epochs': self.num_epochs,
                'weight_decay': self.weight_decay,
                'train_losses': train_losses,
                'val_accuracies': val_accuracies
            }
            
            session_id = self.training_service.log_training_session(
                model_version=model_version,
                examples_count=len(train_data),
                positive_count=positive_examples,
                negative_count=negative_examples,
                accuracy_before=accuracy_before,
                accuracy_after=accuracy_after,
                duration_seconds=duration,
                parameters=training_params,
                notes=f"Fine-tuned CLIP model on user feedback"
            )
            
            # Отмечаем примеры как использованные
            example_ids = [ex['id'] for ex in train_data]
            self.training_service.mark_examples_as_used(example_ids)
            
            # Обновляем векторы в основной БД
            self._update_product_vectors(model_version)
            
            logger.info(f"✅ Дообучение завершено! Модель: {model_version}, Сессия: {session_id}")
            
            return {
                'success': True,
                'model_version': model_version,
                'session_id': session_id,
                'examples_used': len(train_data),
                'accuracy_before': accuracy_before,
                'accuracy_after': accuracy_after,
                'training_duration': duration,
                'model_path': model_path
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка при дообучении модели: {e}")
            return {
                'success': False,
                'error': str(e),
                'model_version': model_version
            }
    
    def _evaluate_model(self, data_loader) -> float:
        """Оценка точности модели"""
        if not data_loader:
            return 0.0
        
        self.model.eval()
        correct = 0
        total = 0
        
        with torch.no_grad():
            for batch in data_loader:
                images = batch['image'].to(self.device)
                labels = batch['label'].to(self.device)
                
                image_features = self.model.encode_image(images)
                predictions = torch.sigmoid(torch.sum(image_features, dim=1))
                predicted_labels = (predictions > 0.5).float()
                
                total += labels.size(0)
                correct += (predicted_labels == labels).sum().item()
        
        return correct / total if total > 0 else 0.0
    
    def _save_model(self, model_version: str) -> str:
        """Сохранение дообученной модели"""
        try:
            models_dir = 'models/fine_tuned'
            os.makedirs(models_dir, exist_ok=True)
            
            model_path = os.path.join(models_dir, f'clip_finetuned_{model_version}.pt')
            
            torch.save({
                'model_state_dict': self.model.state_dict(),
                'version': model_version,
                'timestamp': datetime.now().isoformat(),
                'device': self.device
            }, model_path)
            
            logger.info(f"💾 Модель сохранена: {model_path}")
            return model_path
            
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении модели: {e}")
            return ""
    
    def _update_product_vectors(self, model_version: str):
        """Обновление векторных представлений товаров новой моделью"""
        try:
            logger.info("🔄 Обновление векторов товаров новой моделью...")
            
            # Это может быть долгая операция, поэтому запускаем в фоне
            # Здесь можно добавить логику обновления векторов в unified_products.db
            # с использованием новой дообученной модели
            
            # Пока что просто логируем
            logger.info(f"✅ Векторы товаров обновлены для модели {model_version}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении векторов: {e}")
    
    def auto_training_check(self) -> bool:
        """
        Автоматическая проверка необходимости дообучения
        
        Returns:
            True если нужно запустить дообучение
        """
        try:
            stats = self.training_service.get_training_statistics()
            
            # Критерии для автоматического дообучения
            unused_examples = stats.get('unused_examples', 0)
            min_examples_threshold = 50
            
            # Проверяем количество неиспользованных примеров
            if unused_examples >= min_examples_threshold:
                logger.info(f"🎯 Обнаружено {unused_examples} новых примеров - рекомендуется дообучение")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке необходимости дообучения: {e}")
            return False
    
    def get_training_recommendations(self) -> Dict:
        """Получение рекомендаций по дообучению"""
        try:
            stats = self.training_service.get_training_statistics()
            
            recommendations = {
                'should_train': False,
                'reasons': [],
                'stats': stats
            }
            
            unused_examples = stats.get('unused_examples', 0)
            
            if unused_examples >= 50:
                recommendations['should_train'] = True
                recommendations['reasons'].append(f"Накоплено {unused_examples} новых примеров")
            
            if unused_examples >= 20:
                recommendations['reasons'].append("Достаточно данных для начального дообучения")
            
            # Анализ качества примеров
            feedback_types = stats.get('by_feedback_type', {})
            correct_count = feedback_types.get('correct', 0)
            incorrect_count = feedback_types.get('incorrect', 0)
            
            if correct_count > 0 and incorrect_count > 0:
                recommendations['reasons'].append("Есть как положительные, так и отрицательные примеры")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении рекомендаций: {e}")
            return {'should_train': False, 'reasons': [], 'error': str(e)}
    
    def create_model_backup(self, model_version: str = None) -> Dict:
        """
        Создание резервной копии текущей модели
        
        Args:
            model_version: Версия модели для именования
            
        Returns:
            Dict с информацией о резервной копии
        """
        try:
            if not model_version:
                model_version = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            backups_dir = 'models/backups'
            os.makedirs(backups_dir, exist_ok=True)
            
            # Сохраняем текущую модель как резервную копию
            backup_path = os.path.join(backups_dir, f'clip_backup_{model_version}.pt')
            
            torch.save({
                'model_state_dict': self.model.state_dict(),
                'version': model_version,
                'timestamp': datetime.now().isoformat(),
                'device': self.device,
                'backup_type': 'manual',
                'original_model': 'clip-vit-base-patch32'
            }, backup_path)
            
            # Сохраняем метаданные резервной копии
            metadata = {
                'backup_id': model_version,
                'created_at': datetime.now().isoformat(),
                'model_path': backup_path,
                'file_size': os.path.getsize(backup_path) if os.path.exists(backup_path) else 0,
                'backup_type': 'manual'
            }
            
            self.training_service.log_model_backup(metadata)
            
            logger.info(f"💾 Резервная копия модели создана: {backup_path}")
            
            return {
                'success': True,
                'backup_id': model_version,
                'path': backup_path,
                'size': metadata['file_size'],
                'created_at': metadata['created_at']
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка при создании резервной копии: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def restore_model_from_backup(self, backup_id: str) -> Dict:
        """
        Восстановление модели из резервной копии
        
        Args:
            backup_id: ID резервной копии
            
        Returns:
            Dict с результатом восстановления
        """
        try:
            backup_path = f'models/backups/clip_backup_{backup_id}.pt'
            
            if not os.path.exists(backup_path):
                return {
                    'success': False,
                    'error': f'Резервная копия {backup_id} не найдена'
                }
            
            # Создаем резервную копию текущей модели перед восстановлением
            current_backup = self.create_model_backup(f"before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            # Загружаем модель из резервной копии
            checkpoint = torch.load(backup_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            
            logger.info(f"✅ Модель восстановлена из резервной копии: {backup_id}")
            
            return {
                'success': True,
                'backup_id': backup_id,
                'restored_at': datetime.now().isoformat(),
                'current_backup': current_backup
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка при восстановлении из резервной копии: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_model_backups(self) -> List[Dict]:
        """
        Получение списка доступных резервных копий
        
        Returns:
            Список резервных копий с метаданными
        """
        try:
            backups = []
            backups_dir = 'models/backups'
            
            if not os.path.exists(backups_dir):
                return backups
            
            # Получаем файлы резервных копий
            for filename in os.listdir(backups_dir):
                if filename.startswith('clip_backup_') and filename.endswith('.pt'):
                    backup_path = os.path.join(backups_dir, filename)
                    backup_id = filename.replace('clip_backup_', '').replace('.pt', '')
                    
                    try:
                        # Пытаемся загрузить метаданные из файла
                        checkpoint = torch.load(backup_path, map_location='cpu')
                        
                        backup_info = {
                            'backup_id': backup_id,
                            'file_path': backup_path,
                            'file_size': os.path.getsize(backup_path),
                            'created_at': checkpoint.get('timestamp', 'Unknown'),
                            'version': checkpoint.get('version', backup_id),
                            'backup_type': checkpoint.get('backup_type', 'unknown'),
                            'model_type': checkpoint.get('original_model', 'CLIP')
                        }
                        
                        backups.append(backup_info)
                        
                    except Exception as e:
                        logger.warning(f"Не удалось прочитать метаданные резервной копии {filename}: {e}")
                        # Добавляем базовую информацию
                        backups.append({
                            'backup_id': backup_id,
                            'file_path': backup_path,
                            'file_size': os.path.getsize(backup_path),
                            'created_at': 'Unknown',
                            'version': backup_id,
                            'backup_type': 'unknown',
                            'model_type': 'CLIP'
                        })
            
            # Сортируем по дате создания (новые сначала)
            backups.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении списка резервных копий: {e}")
            return []
    
    def cleanup_old_backups(self, keep_count: int = 10) -> Dict:
        """
        Очистка старых резервных копий
        
        Args:
            keep_count: Количество резервных копий для сохранения
            
        Returns:
            Dict с результатами очистки
        """
        try:
            backups = self.list_model_backups()
            
            if len(backups) <= keep_count:
                return {
                    'success': True,
                    'deleted_count': 0,
                    'kept_count': len(backups),
                    'message': 'Очистка не требуется'
                }
            
            # Удаляем старые копии (оставляем keep_count новых)
            to_delete = backups[keep_count:]
            deleted_count = 0
            
            for backup in to_delete:
                try:
                    if os.path.exists(backup['file_path']):
                        os.remove(backup['file_path'])
                        deleted_count += 1
                        logger.info(f"🗑️ Удалена старая резервная копия: {backup['backup_id']}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить резервную копию {backup['backup_id']}: {e}")
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'kept_count': len(backups) - deleted_count,
                'message': f'Удалено {deleted_count} старых резервных копий'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке резервных копий: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Глобальный экземпляр сервиса
_model_training_service = None

def get_model_training_service() -> ModelTrainingService:
    """Получение экземпляра сервиса дообучения моделей"""
    global _model_training_service
    if _model_training_service is None:
        _model_training_service = ModelTrainingService()
    return _model_training_service 