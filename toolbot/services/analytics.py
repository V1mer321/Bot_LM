"""
Модуль для сбора и анализа статистики использования бота.
"""

import logging
import time
import json
import os
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class Analytics:
    """
    Класс для сбора и анализа статистики использования бота.
    """
    
    def __init__(self, storage_path: str = "toolbot/data/analytics.json"):
        """
        Инициализация аналитики.
        
        Args:
            storage_path: Путь к файлу хранения статистики
        """
        self.storage_path = storage_path
        self.stats = {
            "total_requests": 0,
            "start_time": time.time(),
            "users": {},
            "commands": {},
            "photo_searches": {
                "total": 0,
                "success": 0,
                "failures": 0
            },
            "departments": {}
        }
        
        # Загружаем статистику, если файл существует
        self._load_stats()
    
    def _load_stats(self):
        """Загружает статистику из файла, если он существует."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self.stats = json.load(f)
                logger.info(f"Статистика загружена из {self.storage_path}")
            else:
                # Создаем директорию для файла, если она не существует
                os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
                logger.info(f"Файл статистики {self.storage_path} не найден, будет создан новый")
        except Exception as e:
            logger.error(f"Ошибка при загрузке статистики: {e}")
    
    def _save_stats(self):
        """Сохраняет статистику в файл."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении статистики: {e}")
    
    def log_command(self, user_id: int, command: str):
        """
        Логирует использование команды.
        
        Args:
            user_id: ID пользователя
            command: Название команды
        """
        # Обновляем общее количество запросов
        self.stats["total_requests"] += 1
        
        # Обновляем статистику пользователя
        user_id_str = str(user_id)
        if user_id_str not in self.stats["users"]:
            self.stats["users"][user_id_str] = {
                "first_seen": time.time(),
                "requests": 0,
                "commands": {}
            }
        
        self.stats["users"][user_id_str]["requests"] += 1
        
        if command not in self.stats["users"][user_id_str]["commands"]:
            self.stats["users"][user_id_str]["commands"][command] = 0
        
        self.stats["users"][user_id_str]["commands"][command] += 1
        
        # Обновляем общую статистику команд
        if command not in self.stats["commands"]:
            self.stats["commands"][command] = 0
        
        self.stats["commands"][command] += 1
        
        # Сохраняем статистику
        self._save_stats()
    
    def log_photo_search(self, user_id: int, department: str, success: bool):
        """
        Логирует поиск по фото.
        
        Args:
            user_id: ID пользователя
            department: Отдел, в котором выполнялся поиск
            success: Успешность поиска
        """
        # Обновляем общее количество запросов
        self.stats["total_requests"] += 1
        
        # Обновляем статистику поиска по фото
        self.stats["photo_searches"]["total"] += 1
        
        if success:
            self.stats["photo_searches"]["success"] += 1
        else:
            self.stats["photo_searches"]["failures"] += 1
        
        # Обновляем статистику по отделам
        if department not in self.stats["departments"]:
            self.stats["departments"][department] = {
                "total": 0,
                "success": 0,
                "failures": 0
            }
        
        self.stats["departments"][department]["total"] += 1
        
        if success:
            self.stats["departments"][department]["success"] += 1
        else:
            self.stats["departments"][department]["failures"] += 1
        
        # Обновляем статистику пользователя
        user_id_str = str(user_id)
        if user_id_str not in self.stats["users"]:
            self.stats["users"][user_id_str] = {
                "first_seen": time.time(),
                "requests": 0,
                "commands": {}
            }
        
        self.stats["users"][user_id_str]["requests"] += 1
        
        # Сохраняем статистику
        self._save_stats()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает текущую статистику.
        
        Returns:
            Словарь с статистикой
        """
        return self.stats
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Возвращает статистику по пользователю.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь с статистикой пользователя
        """
        user_id_str = str(user_id)
        return self.stats["users"].get(user_id_str, {
            "first_seen": time.time(),
            "requests": 0,
            "commands": {}
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Возвращает сводную статистику.
        
        Returns:
            Словарь со сводной статистикой
        """
        uptime = time.time() - self.stats["start_time"]
        
        return {
            "total_requests": self.stats["total_requests"],
            "uptime_seconds": uptime,
            "uptime_days": uptime / (60 * 60 * 24),
            "unique_users": len(self.stats["users"]),
            "photo_searches": self.stats["photo_searches"],
            "top_commands": sorted(
                [(cmd, count) for cmd, count in self.stats["commands"].items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]  # Топ-5 команд
        } 