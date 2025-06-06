import sqlite3
import json
import logging
import os
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from PIL import Image
import torch

logger = logging.getLogger(__name__)

class TrainingDataService:
    """Сервис для управления обучающими данными и дообучения моделей"""
    
    def __init__(self, db_path='data/search_stats.db'):
        self.db_path = db_path
        self.temp_dir = 'temp/training_images'
        os.makedirs(self.temp_dir, exist_ok=True)
        self._init_training_tables()
    
    def _init_training_tables(self):
        """Инициализация таблиц для обучающих данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Таблица обучающих примеров
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS training_examples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    photo_file_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    feedback_type TEXT NOT NULL, -- 'correct', 'incorrect', 'new_item'
                    target_item_id TEXT,  -- ID товара из unified_products.db
                    similarity_score REAL,
                    user_comment TEXT,
                    image_path TEXT,  -- локальный путь к изображению
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_used_for_training BOOLEAN DEFAULT FALSE,
                    quality_rating INTEGER DEFAULT 5  -- от 1 до 5
                )
            ''')
            
            # Таблица истории дообучения
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_training_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_version TEXT NOT NULL,
                    training_examples_count INTEGER NOT NULL,
                    positive_examples INTEGER NOT NULL,
                    negative_examples INTEGER NOT NULL,
                    accuracy_before REAL,
                    accuracy_after REAL,
                    training_duration_seconds INTEGER,
                    training_parameters TEXT,  -- JSON с параметрами обучения
                    training_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT FALSE,
                    notes TEXT
                )
            ''')
            
            # Таблица аннотированных изображений для новых товаров
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS new_product_annotations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    photo_file_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    product_name TEXT,
                    product_category TEXT,
                    product_description TEXT,
                    image_path TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    admin_approved BOOLEAN DEFAULT FALSE,
                    admin_id INTEGER,
                    approval_date DATETIME,
                    added_to_catalog BOOLEAN DEFAULT FALSE
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Таблицы для обучающих данных инициализированы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при инициализации таблиц обучения: {e}")
    
    def add_training_example(self, photo_file_id: str, user_id: int, username: str,
                           feedback_type: str, target_item_id: str = None,
                           similarity_score: float = None, user_comment: str = None,
                           image_path: str = None, quality_rating: int = 5) -> int:
        """
        Добавление обучающего примера
        
        Args:
            photo_file_id: ID фото в Telegram
            user_id: ID пользователя
            username: Имя пользователя
            feedback_type: Тип обратной связи (correct/incorrect/new_item)
            target_item_id: ID целевого товара
            similarity_score: Оценка схожести
            user_comment: Комментарий пользователя
            image_path: Путь к сохраненному изображению
            quality_rating: Оценка качества примера (1-5)
            
        Returns:
            ID созданной записи
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO training_examples 
                (photo_file_id, user_id, username, feedback_type, target_item_id, 
                 similarity_score, user_comment, image_path, quality_rating)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (photo_file_id, user_id, username, feedback_type, target_item_id,
                  similarity_score, user_comment, image_path, quality_rating))
            
            example_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Добавлен обучающий пример #{example_id} от пользователя {user_id}")
            return example_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении обучающего примера: {e}")
            return 0
    
    def add_new_product_annotation(self, photo_file_id: str, user_id: int, username: str,
                                 product_name: str, product_category: str = None,
                                 product_description: str = None, image_path: str = None) -> int:
        """Добавление аннотации для нового товара"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO new_product_annotations 
                (photo_file_id, user_id, username, product_name, product_category, 
                 product_description, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (photo_file_id, user_id, username, product_name, product_category,
                  product_description, image_path))
            
            annotation_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Добавлена аннотация нового товара #{annotation_id}")
            return annotation_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении аннотации: {e}")
            return 0
    
    def get_training_examples(self, feedback_type: str = None, 
                            is_used: bool = None, limit: int = 100) -> List[Dict]:
        """Получение обучающих примеров"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT id, photo_file_id, user_id, username, feedback_type, 
                       target_item_id, similarity_score, user_comment, image_path,
                       created_at, is_used_for_training, quality_rating
                FROM training_examples
            '''
            params = []
            
            conditions = []
            if feedback_type:
                conditions.append("feedback_type = ?")
                params.append(feedback_type)
            
            if is_used is not None:
                conditions.append("is_used_for_training = ?")
                params.append(is_used)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            columns = ['id', 'photo_file_id', 'user_id', 'username', 'feedback_type',
                      'target_item_id', 'similarity_score', 'user_comment', 'image_path',
                      'created_at', 'is_used_for_training', 'quality_rating']
            
            examples = [dict(zip(columns, row)) for row in rows]
            
            conn.close()
            return examples
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении обучающих примеров: {e}")
            return []
    
    def get_training_statistics(self) -> Dict:
        """Получение статистики обучающих данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Общее количество примеров
            cursor.execute('SELECT COUNT(*) FROM training_examples')
            total_examples = cursor.fetchone()[0]
            
            # По типам обратной связи
            cursor.execute('''
                SELECT feedback_type, COUNT(*) 
                FROM training_examples 
                GROUP BY feedback_type
            ''')
            by_feedback_type = dict(cursor.fetchall())
            
            # Использованные для обучения
            cursor.execute('SELECT COUNT(*) FROM training_examples WHERE is_used_for_training = 1')
            used_for_training = cursor.fetchone()[0]
            
            # Новые товары
            cursor.execute('SELECT COUNT(*) FROM new_product_annotations')
            new_products = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM new_product_annotations WHERE admin_approved = 1')
            approved_products = cursor.fetchone()[0]
            
            # История обучения
            cursor.execute('SELECT COUNT(*) FROM model_training_history')
            training_sessions = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT model_version, accuracy_after, training_date 
                FROM model_training_history 
                WHERE is_active = 1
                ORDER BY training_date DESC 
                LIMIT 1
            ''')
            current_model = cursor.fetchone()
            
            conn.close()
            
            return {
                'total_examples': total_examples,
                'by_feedback_type': by_feedback_type,
                'used_for_training': used_for_training,
                'unused_examples': total_examples - used_for_training,
                'new_products_annotations': new_products,
                'approved_new_products': approved_products,
                'training_sessions': training_sessions,
                'current_model': {
                    'version': current_model[0] if current_model else None,
                    'accuracy': current_model[1] if current_model else None,
                    'date': current_model[2] if current_model else None
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении статистики: {e}")
            return {}
    
    def mark_examples_as_used(self, example_ids: List[int]) -> bool:
        """Отметить примеры как использованные для обучения"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            placeholders = ','.join(['?'] * len(example_ids))
            cursor.execute(f'''
                UPDATE training_examples 
                SET is_used_for_training = 1 
                WHERE id IN ({placeholders})
            ''', example_ids)
            
            updated_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Отмечено {updated_count} примеров как использованных")
            return updated_count > 0
            
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении статуса примеров: {e}")
            return False
    
    def log_training_session(self, model_version: str, examples_count: int,
                           positive_count: int, negative_count: int,
                           accuracy_before: float = None, accuracy_after: float = None,
                           duration_seconds: int = None, parameters: Dict = None,
                           notes: str = None) -> int:
        """Логирование сессии дообучения"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Деактивируем предыдущие модели
            cursor.execute('UPDATE model_training_history SET is_active = 0')
            
            # Добавляем новую сессию
            parameters_json = json.dumps(parameters) if parameters else None
            
            cursor.execute('''
                INSERT INTO model_training_history 
                (model_version, training_examples_count, positive_examples, negative_examples,
                 accuracy_before, accuracy_after, training_duration_seconds, training_parameters,
                 is_active, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            ''', (model_version, examples_count, positive_count, negative_count,
                  accuracy_before, accuracy_after, duration_seconds, parameters_json, notes))
            
            session_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Записана сессия дообучения #{session_id} для модели {model_version}")
            return session_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка при записи сессии обучения: {e}")
            return 0
    
    def get_pending_new_products(self, limit: int = 50) -> List[Dict]:
        """Получение неодобренных новых товаров"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, photo_file_id, user_id, username, product_name, 
                       product_category, product_description, image_path, created_at
                FROM new_product_annotations 
                WHERE admin_approved = 0 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            columns = ['id', 'photo_file_id', 'user_id', 'username', 'product_name',
                      'product_category', 'product_description', 'image_path', 'created_at']
            
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении неодобренных товаров: {e}")
            return []
    
    def approve_new_product(self, annotation_id: int, admin_id: int = None) -> bool:
        """Одобрение нового товара администратором"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE new_product_annotations 
                SET admin_approved = 1, admin_id = ?, approval_date = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (admin_id, annotation_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if success:
                logger.info(f"✅ Товар #{annotation_id} одобрен администратором {admin_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Ошибка при одобрении товара: {e}")
            return False
    
    def log_model_backup(self, metadata: Dict) -> int:
        """
        Логирование информации о резервной копии модели
        
        Args:
            metadata: Метаданные резервной копии
            
        Returns:
            ID записи о резервной копии или 0 при ошибке
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Создание таблицы для резервных копий если её нет
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_id TEXT NOT NULL UNIQUE,
                    model_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    backup_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata TEXT  -- JSON с дополнительными данными
                )
            ''')
            
            cursor.execute('''
                INSERT OR REPLACE INTO model_backups 
                (backup_id, model_path, file_size, backup_type, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                metadata['backup_id'],
                metadata['model_path'],
                metadata['file_size'],
                metadata['backup_type'],
                metadata['created_at'],
                json.dumps(metadata)
            ))
            
            backup_record_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Информация о резервной копии сохранена: {metadata['backup_id']}")
            return backup_record_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка при логировании резервной копии: {e}")
            return 0


# Глобальный экземпляр сервиса
_training_service = None

def get_training_service() -> TrainingDataService:
    """Получение экземпляра сервиса обучающих данных"""
    global _training_service
    if _training_service is None:
        _training_service = TrainingDataService()
    return _training_service 