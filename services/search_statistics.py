"""
Сервис для сбора статистики поиска по изображениям
"""
import sqlite3
import logging
import json
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class SearchStatisticsService:
    """Сервис для сбора и анализа статистики поиска"""
    
    def __init__(self, db_path='data/search_stats.db'):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Инициализация базы данных статистики"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Таблица для статистики неудачных поисков
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS failed_searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    photo_file_id TEXT NOT NULL,
                    search_results TEXT,  -- JSON с результатами поиска
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    feedback_type TEXT DEFAULT 'not_my_product',  -- тип обратной связи
                    user_comment TEXT  -- комментарий пользователя если есть
                )
            ''')
            
            # Таблица для общей статистики поисков
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    photo_file_id TEXT NOT NULL,
                    results_count INTEGER NOT NULL,
                    best_similarity REAL,
                    search_method TEXT,  -- метод поиска: stable, threshold, aggressive
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    was_successful BOOLEAN DEFAULT 1  -- был ли поиск успешным
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("База данных статистики поиска инициализирована")
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации БД статистики: {e}")
    
    def log_search_session(self, user_id: int, username: str, photo_file_id: str, 
                          results: List[Dict], search_method: str) -> int:
        """
        Логирование сессии поиска
        
        Args:
            user_id: ID пользователя
            username: Имя пользователя
            photo_file_id: ID фото в Telegram
            results: Результаты поиска
            search_method: Метод поиска
            
        Returns:
            ID созданной записи
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            results_count = len(results) if results else 0
            best_similarity = max([r.get('similarity', 0) for r in results]) if results else 0
            
            cursor.execute('''
                INSERT INTO search_sessions 
                (user_id, username, photo_file_id, results_count, best_similarity, search_method, was_successful)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, photo_file_id, results_count, best_similarity, search_method, results_count > 0))
            
            session_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return session_id
            
        except Exception as e:
            logger.error(f"Ошибка при логировании сессии поиска: {e}")
            return 0
    
    def log_failed_search(self, user_id: int, username: str, photo_file_id: str, 
                         search_results: List[Dict], feedback_type: str = 'not_my_product',
                         user_comment: str = None) -> bool:
        """
        Логирование неудачного поиска
        
        Args:
            user_id: ID пользователя
            username: Имя пользователя  
            photo_file_id: ID фото в Telegram
            search_results: Результаты поиска, которые не подошли
            feedback_type: Тип обратной связи
            user_comment: Комментарий пользователя
            
        Returns:
            True если успешно записано
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Сериализуем результаты поиска в JSON
            results_json = json.dumps(search_results, ensure_ascii=False)
            
            cursor.execute('''
                INSERT INTO failed_searches 
                (user_id, username, photo_file_id, search_results, feedback_type, user_comment)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, username, photo_file_id, results_json, feedback_type, user_comment))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Записан неудачный поиск от пользователя {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при записи неудачного поиска: {e}")
            return False
    
    def get_failed_searches_stats(self) -> Dict:
        """Получение статистики неудачных поисков"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Общее количество неудачных поисков
            cursor.execute('SELECT COUNT(*) FROM failed_searches')
            total_failed = cursor.fetchone()[0]
            
            # По дням за последнюю неделю
            cursor.execute('''
                SELECT DATE(timestamp) as date, COUNT(*) as count
                FROM failed_searches 
                WHERE timestamp >= datetime('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            ''')
            daily_stats = cursor.fetchall()
            
            # Топ пользователей с неудачными поисками
            cursor.execute('''
                SELECT user_id, username, COUNT(*) as failed_count
                FROM failed_searches
                GROUP BY user_id, username
                ORDER BY failed_count DESC
                LIMIT 10
            ''')
            top_users = cursor.fetchall()
            
            conn.close()
            
            return {
                'total_failed_searches': total_failed,
                'daily_stats': dict(daily_stats),
                'top_users_with_failures': [
                    {'user_id': row[0], 'username': row[1], 'failed_count': row[2]}
                    for row in top_users
                ]
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return {}
    
    def get_search_success_rate(self) -> Dict:
        """Получение общей статистики успешности поисков"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Общая статистика поисков
            cursor.execute('SELECT COUNT(*) FROM search_sessions')
            total_searches = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM search_sessions WHERE was_successful = 1')
            successful_searches = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM failed_searches')
            user_reported_failures = cursor.fetchone()[0]
            
            # Средняя схожесть по успешным поискам
            cursor.execute('SELECT AVG(best_similarity) FROM search_sessions WHERE was_successful = 1')
            avg_similarity = cursor.fetchone()[0] or 0
            
            success_rate = (successful_searches / total_searches * 100) if total_searches > 0 else 0
            
            conn.close()
            
            return {
                'total_searches': total_searches,
                'successful_searches': successful_searches,
                'user_reported_failures': user_reported_failures,
                'success_rate_percent': round(success_rate, 2),
                'average_similarity': round(avg_similarity, 4)
            }
            
        except Exception as e:
            logger.error(f"Ошибка при расчете успешности: {e}")
            return {}
    
    def get_recent_failed_searches(self, limit: int = 10) -> List[Dict]:
        """Получение последних неудачных поисков для админов"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, username, photo_file_id, search_results, 
                       feedback_type, user_comment, timestamp
                FROM failed_searches
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            result = []
            for row in rows:
                try:
                    search_results = json.loads(row[3]) if row[3] else []
                except:
                    search_results = []
                
                result.append({
                    'user_id': row[0],
                    'username': row[1],
                    'photo_file_id': row[2],
                    'search_results': search_results,
                    'feedback_type': row[4],
                    'user_comment': row[5],
                    'timestamp': row[6]
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении последних неудачных поисков: {e}")
            return []

# Глобальный экземпляр сервиса
_stats_service = None

def get_stats_service():
    """Получение экземпляра сервиса статистики"""
    global _stats_service
    if _stats_service is None:
        _stats_service = SearchStatisticsService()
    return _stats_service 