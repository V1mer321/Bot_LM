"""
Сервис для управления базой данных обратной связи
"""
import sqlite3
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class FeedbackDatabaseService:
    """Сервис для работы с базой данных обратной связи"""
    
    def __init__(self, db_path='data/feedback.db'):
        self.db_path = db_path
        self.ensure_database_exists()
    
    def ensure_database_exists(self):
        """Создает базу данных и таблицы если их нет"""
        # Создаем директорию если не существует
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        # Создаем таблицы
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица сообщений об ошибках
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS error_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    message TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'новый',
                    admin_response TEXT,
                    admin_id INTEGER,
                    response_timestamp DATETIME
                )
            ''')
            
            # Таблица предложений по улучшению
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS improvement_suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    message TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'новый',
                    admin_response TEXT,
                    admin_id INTEGER,
                    response_timestamp DATETIME,
                    priority TEXT DEFAULT 'обычный'
                )
            ''')
            
            # Таблица общих сообщений (если понадобится)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS general_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    feedback_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'новый',
                    admin_response TEXT,
                    admin_id INTEGER,
                    response_timestamp DATETIME
                )
            ''')
            
            conn.commit()
            logger.info("✅ База данных обратной связи готова к работе")
    
    def add_error_report(self, user_id: int, username: str, message: str) -> int:
        """Добавляет сообщение об ошибке"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO error_reports (user_id, username, message) 
                VALUES (?, ?, ?)
            ''', (user_id, username, message))
            conn.commit()
            report_id = cursor.lastrowid
            logger.info(f"📋 Новое сообщение об ошибке #{report_id} от пользователя {user_id}")
            return report_id
    
    def add_improvement_suggestion(self, user_id: int, username: str, message: str, priority: str = 'обычный') -> int:
        """Добавляет предложение по улучшению"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO improvement_suggestions (user_id, username, message, priority) 
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, message, priority))
            conn.commit()
            suggestion_id = cursor.lastrowid
            logger.info(f"💡 Новое предложение #{suggestion_id} от пользователя {user_id}")
            return suggestion_id
    
    def get_error_reports(self, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Получает сообщения об ошибках"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if status:
                cursor.execute('''
                    SELECT id, user_id, username, message, timestamp, status, admin_response
                    FROM error_reports 
                    WHERE status = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (status, limit))
            else:
                cursor.execute('''
                    SELECT id, user_id, username, message, timestamp, status, admin_response
                    FROM error_reports 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
            
            columns = ['id', 'user_id', 'username', 'message', 'timestamp', 'status', 'admin_response']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_improvement_suggestions(self, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Получает предложения по улучшению"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if status:
                cursor.execute('''
                    SELECT id, user_id, username, message, timestamp, status, priority, admin_response
                    FROM improvement_suggestions 
                    WHERE status = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (status, limit))
            else:
                cursor.execute('''
                    SELECT id, user_id, username, message, timestamp, status, priority, admin_response
                    FROM improvement_suggestions 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
            
            columns = ['id', 'user_id', 'username', 'message', 'timestamp', 'status', 'priority', 'admin_response']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def update_status(self, table: str, item_id: int, status: str, admin_id: int, admin_response: str = None) -> bool:
        """Обновляет статус сообщения"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if admin_response:
                cursor.execute(f'''
                    UPDATE {table} 
                    SET status = ?, admin_id = ?, admin_response = ?, response_timestamp = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, admin_id, admin_response, item_id))
            else:
                cursor.execute(f'''
                    UPDATE {table} 
                    SET status = ?, admin_id = ?
                    WHERE id = ?
                ''', (status, admin_id, item_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def update_error_status(self, error_id: int, status: str, admin_id: int, admin_response: str = None) -> bool:
        """Обновляет статус сообщения об ошибке"""
        return self.update_status('error_reports', error_id, status, admin_id, admin_response)
    
    def update_suggestion_status(self, suggestion_id: int, status: str, admin_id: int, admin_response: str = None) -> bool:
        """Обновляет статус предложения"""
        return self.update_status('improvement_suggestions', suggestion_id, status, admin_id, admin_response)
    
    def update_suggestion_priority(self, suggestion_id: int, priority: str, admin_id: int) -> bool:
        """Обновляет приоритет предложения"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE improvement_suggestions 
                SET priority = ?, admin_id = ?
                WHERE id = ?
            ''', (priority, admin_id, suggestion_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_error_by_id(self, error_id: int) -> Optional[Dict]:
        """Получает сообщение об ошибке по ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, user_id, username, message, timestamp, status, admin_response
                FROM error_reports 
                WHERE id = ?
            ''', (error_id,))
            
            result = cursor.fetchone()
            if result:
                columns = ['id', 'user_id', 'username', 'message', 'timestamp', 'status', 'admin_response']
                return dict(zip(columns, result))
            return None
    
    def get_suggestion_by_id(self, suggestion_id: int) -> Optional[Dict]:
        """Получает предложение по ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, user_id, username, message, timestamp, status, priority, admin_response
                FROM improvement_suggestions 
                WHERE id = ?
            ''', (suggestion_id,))
            
            result = cursor.fetchone()
            if result:
                columns = ['id', 'user_id', 'username', 'message', 'timestamp', 'status', 'priority', 'admin_response']
                return dict(zip(columns, result))
            return None
    
    def get_statistics(self) -> Dict:
        """Получает статистику обратной связи"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Статистика сообщений об ошибках
            cursor.execute('SELECT COUNT(*) FROM error_reports')
            total_errors = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM error_reports WHERE status = "новый"')
            new_errors = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM error_reports WHERE status = "решено"')
            resolved_errors = cursor.fetchone()[0]
            
            # Статистика предложений
            cursor.execute('SELECT COUNT(*) FROM improvement_suggestions')
            total_suggestions = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM improvement_suggestions WHERE status = "новый"')
            new_suggestions = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM improvement_suggestions WHERE status = "реализовано"')
            implemented_suggestions = cursor.fetchone()[0]
            
            return {
                'total_errors': total_errors,
                'new_errors': new_errors,
                'resolved_errors': resolved_errors,
                'total_suggestions': total_suggestions,
                'new_suggestions': new_suggestions,
                'implemented_suggestions': implemented_suggestions
            }
    
    def search_feedback(self, query: str, feedback_type: str = None) -> List[Dict]:
        """Поиск в сообщениях обратной связи"""
        results = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Поиск в ошибках
            if not feedback_type or feedback_type == 'errors':
                cursor.execute('''
                    SELECT 'error' as type, id, user_id, username, message, timestamp, status
                    FROM error_reports 
                    WHERE message LIKE ? OR username LIKE ?
                    ORDER BY timestamp DESC
                ''', (f'%{query}%', f'%{query}%'))
                
                columns = ['type', 'id', 'user_id', 'username', 'message', 'timestamp', 'status']
                results.extend([dict(zip(columns, row)) for row in cursor.fetchall()])
            
            # Поиск в предложениях
            if not feedback_type or feedback_type == 'suggestions':
                cursor.execute('''
                    SELECT 'suggestion' as type, id, user_id, username, message, timestamp, status
                    FROM improvement_suggestions 
                    WHERE message LIKE ? OR username LIKE ?
                    ORDER BY timestamp DESC
                ''', (f'%{query}%', f'%{query}%'))
                
                columns = ['type', 'id', 'user_id', 'username', 'message', 'timestamp', 'status']
                results.extend([dict(zip(columns, row)) for row in cursor.fetchall()])
        
        return results


# Глобальный экземпляр сервиса
_feedback_service = None

def get_feedback_service() -> FeedbackDatabaseService:
    """Получение экземпляра сервиса обратной связи"""
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = FeedbackDatabaseService()
    return _feedback_service 