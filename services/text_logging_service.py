"""
Сервис для логирования всех текстовых сообщений пользователей в SQLite
"""
import sqlite3
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class TextLoggingService:
    """Сервис для логирования текстовых сообщений в SQLite"""
    
    def __init__(self, db_path='data/text_messages.db'):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Инициализация базы данных для логирования текстов"""
        try:
            # Создаем директорию если её нет
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Создаем таблицу для текстовых сообщений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS text_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    chat_id INTEGER,
                    message_text TEXT NOT NULL,
                    message_type TEXT DEFAULT 'text',
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_admin BOOLEAN DEFAULT 0,
                    user_state TEXT,
                    message_length INTEGER,
                    has_mentions BOOLEAN DEFAULT 0,
                    has_urls BOOLEAN DEFAULT 0
                )
            ''')
            
            # Создаем индексы для быстрого поиска
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON text_messages(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON text_messages(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_type ON text_messages(message_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_is_admin ON text_messages(is_admin)')
            
            conn.commit()
            conn.close()
            logger.info(f"✅ База данных логирования текстов инициализирована: {self.db_path}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при инициализации БД логирования: {e}")

    def log_text_message(self, user_id: int, message_text: str, username: str = None, 
                        first_name: str = None, last_name: str = None, chat_id: int = None,
                        message_type: str = 'text', is_admin: bool = False, user_state: str = None):
        """
        Логирует текстовое сообщение в базу данных
        
        Args:
            user_id: ID пользователя
            message_text: Текст сообщения
            username: Username пользователя
            first_name: Имя пользователя
            last_name: Фамилия пользователя
            chat_id: ID чата
            message_type: Тип сообщения (text, command, admin_input, search_query, etc.)
            is_admin: Является ли пользователь администратором
            user_state: Текущее состояние пользователя в боте
        """
        try:
            # Анализируем сообщение
            message_length = len(message_text)
            has_mentions = '@' in message_text
            has_urls = any(url in message_text.lower() for url in ['http://', 'https://', 'www.', 't.me/'])
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO text_messages 
                (user_id, username, first_name, last_name, chat_id, message_text, 
                 message_type, is_admin, user_state, message_length, has_mentions, has_urls)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, chat_id, message_text,
                  message_type, is_admin, user_state, message_length, has_mentions, has_urls))
            
            conn.commit()
            conn.close()
            
            # Логируем только первые 100 символов для безопасности
            text_preview = message_text[:100] + "..." if len(message_text) > 100 else message_text
            logger.debug(f"📝 Сохранен текст от {user_id} (@{username}): {text_preview}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при логировании текста от {user_id}: {e}")

    def get_user_messages(self, user_id: int, limit: int = 50) -> list:
        """Получает последние сообщения пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, message_text, message_type, user_state
                FROM text_messages 
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (user_id, limit))
            
            messages = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'timestamp': msg[0],
                    'text': msg[1],
                    'type': msg[2],
                    'state': msg[3]
                }
                for msg in messages
            ]
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении сообщений пользователя {user_id}: {e}")
            return []

    def get_statistics(self) -> dict:
        """Получает статистику логирования"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Общая статистика
            cursor.execute('SELECT COUNT(*) FROM text_messages')
            total_messages = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT user_id) FROM text_messages')
            unique_users = cursor.fetchone()[0]
            
            # Статистика по типам сообщений
            cursor.execute('''
                SELECT message_type, COUNT(*) 
                FROM text_messages 
                GROUP BY message_type 
                ORDER BY COUNT(*) DESC
            ''')
            message_types = dict(cursor.fetchall())
            
            # Статистика по времени (последние 24 часа)
            cursor.execute('''
                SELECT COUNT(*) 
                FROM text_messages 
                WHERE timestamp >= datetime('now', '-24 hours')
            ''')
            messages_24h = cursor.fetchone()[0]
            
            # Топ активных пользователей
            cursor.execute('''
                SELECT user_id, username, COUNT(*) as message_count
                FROM text_messages 
                GROUP BY user_id 
                ORDER BY message_count DESC 
                LIMIT 10
            ''')
            top_users = cursor.fetchall()
            
            conn.close()
            
            return {
                'total_messages': total_messages,
                'unique_users': unique_users,
                'messages_24h': messages_24h,
                'message_types': message_types,
                'top_users': [
                    {
                        'user_id': user[0],
                        'username': user[1],
                        'message_count': user[2]
                    }
                    for user in top_users
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении статистики: {e}")
            return {}

    def search_messages(self, query: str, limit: int = 100) -> list:
        """Поиск сообщений по тексту"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, username, message_text, timestamp, message_type
                FROM text_messages 
                WHERE message_text LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (f'%{query}%', limit))
            
            results = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'user_id': result[0],
                    'username': result[1],
                    'text': result[2],
                    'timestamp': result[3],
                    'type': result[4]
                }
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"❌ Ошибка при поиске сообщений: {e}")
            return []

    def cleanup_old_messages(self, days: int = 30) -> int:
        """Удаляет сообщения старше указанного количества дней"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM text_messages 
                WHERE timestamp < datetime('now', '-{} days')
            '''.format(days))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"🧹 Удалено {deleted_count} старых сообщений (старше {days} дней)")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке старых сообщений: {e}")
            return 0

# Глобальный экземпляр сервиса
text_logger = TextLoggingService()

def get_text_logging_service() -> TextLoggingService:
    """Получить экземпляр сервиса логирования текстов"""
    return text_logger 