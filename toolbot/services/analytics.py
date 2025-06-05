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
                    loaded_stats = json.load(f)
                
                # Проверяем корректность загруженных данных
                if not isinstance(loaded_stats, dict):
                    logger.warning("Некорректный формат файла статистики, используется по умолчанию")
                    return
                
                # Безопасно обновляем статистику
                for key in ["total_requests", "start_time", "commands", "photo_searches", "departments"]:
                    if key in loaded_stats:
                        self.stats[key] = loaded_stats[key]
                
                # Особая обработка пользователей
                if "users" in loaded_stats and isinstance(loaded_stats["users"], dict):
                    for user_id, user_data in loaded_stats["users"].items():
                        if isinstance(user_data, dict):
                            self.stats["users"][user_id] = user_data
                        
                logger.info(f"Статистика загружена из {self.storage_path}")
            else:
                # Создаем директорию для файла, если она не существует
                os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
                logger.info(f"Файл статистики {self.storage_path} не найден, будет создан новый")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Ошибка JSON при загрузке статистики: {e}")
            # При JSON ошибке - пересоздаем файл
            self._save_stats()
        except Exception as e:
            logger.error(f"Неожиданная ошибка при загрузке статистики: {e}")
            # При любой другой ошибке - создаем новый файл
            self._save_stats()
    
    def _save_stats(self):
        """Сохраняет статистику в файл."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении статистики: {e}")
    
    def log_user_activity(self, user_id: int, activity_type: str, details: str = ""):
        """
        Логирует активность пользователя (вход в бота, команды, сообщения).
        
        Args:
            user_id: ID пользователя
            activity_type: Тип активности (start, command, message, photo_search, etc.)
            details: Дополнительные детали
        """
        current_time = time.time()
        user_id_str = str(user_id)
        
        # Инициализируем пользователя если его нет
        if user_id_str not in self.stats["users"]:
            self.stats["users"][user_id_str] = {
                "first_seen": current_time,
                "last_seen": current_time,
                "requests": 0,
                "commands": {},
                "activity_log": []
            }
        
        # Обновляем последнее время активности
        self.stats["users"][user_id_str]["last_seen"] = current_time
        self.stats["users"][user_id_str]["requests"] += 1
        
        # Добавляем запись в лог активности (сохраняем последние 50 записей)
        activity_record = {
            "timestamp": current_time,
            "type": activity_type,
            "details": details
        }
        
        if "activity_log" not in self.stats["users"][user_id_str]:
            self.stats["users"][user_id_str]["activity_log"] = []
            
        self.stats["users"][user_id_str]["activity_log"].append(activity_record)
        
        # Ограничиваем размер лога (последние 50 записей)
        if len(self.stats["users"][user_id_str]["activity_log"]) > 50:
            self.stats["users"][user_id_str]["activity_log"] = self.stats["users"][user_id_str]["activity_log"][-50:]
        
        # Логируем в консоль для отладки
        logger.info(f"Пользователь {user_id}: {activity_type} - {details}")
        
        # Сохраняем статистику
        self._save_stats()

    def log_command(self, command: str, user_id: int):
        """
        Логирует использование команды.
        
        Args:
            command: Название команды
            user_id: ID пользователя
        """
        # Обновляем общее количество запросов
        self.stats["total_requests"] += 1
        
        # Логируем активность пользователя
        self.log_user_activity(user_id, "command", command)
        
        # Обновляем статистику команд пользователя
        user_id_str = str(user_id)
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
    
    def get_recent_users(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Возвращает список пользователей, активных за последние N дней.
        
        Args:
            days: Количество дней для фильтрации
            
        Returns:
            Список пользователей с их активностью
        """
        current_time = time.time()
        cutoff_time = current_time - (days * 24 * 60 * 60)
        
        recent_users = []
        
        for user_id, user_data in self.stats["users"].items():
            last_seen = user_data.get("last_seen", user_data.get("first_seen", 0))
            
            if last_seen >= cutoff_time:
                recent_activity = []
                activity_log = user_data.get("activity_log", [])
                
                # Фильтруем активность за указанный период
                for activity in activity_log:
                    if activity["timestamp"] >= cutoff_time:
                        recent_activity.append(activity)
                
                user_info = {
                    "user_id": int(user_id),
                    "first_seen": user_data.get("first_seen", 0),
                    "last_seen": last_seen,
                    "total_requests": user_data.get("requests", 0),
                    "recent_activity": recent_activity,
                    "commands": user_data.get("commands", {})
                }
                
                recent_users.append(user_info)
        
        # Сортируем по последней активности (самые активные первыми)
        recent_users.sort(key=lambda x: x["last_seen"], reverse=True)
        
        return recent_users

    def get_user_activity_log(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Возвращает лог активности конкретного пользователя.
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество записей
            
        Returns:
            Список последних действий пользователя
        """
        user_id_str = str(user_id)
        
        if user_id_str not in self.stats["users"]:
            return []
        
        activity_log = self.stats["users"][user_id_str].get("activity_log", [])
        
        # Возвращаем последние записи
        return activity_log[-limit:] if activity_log else []

    def get_summary(self) -> Dict[str, Any]:
        """
        Возвращает сводную статистику.
        
        Returns:
            Словарь со сводной статистикой
        """
        uptime = time.time() - self.stats["start_time"]
        
        # Подсчитываем активных пользователей за последние дни
        current_time = time.time()
        day_ago = current_time - (24 * 60 * 60)
        week_ago = current_time - (7 * 24 * 60 * 60)
        
        active_today = 0
        active_week = 0
        
        for user_data in self.stats["users"].values():
            last_seen = user_data.get("last_seen", user_data.get("first_seen", 0))
            
            if last_seen >= day_ago:
                active_today += 1
            if last_seen >= week_ago:
                active_week += 1
        
        return {
            "total_requests": self.stats["total_requests"],
            "uptime_seconds": uptime,
            "uptime_days": uptime / (60 * 60 * 24),
            "unique_users": len(self.stats["users"]),
            "active_today": active_today,
            "active_week": active_week,
            "photo_searches": self.stats["photo_searches"],
            "top_commands": sorted(
                [(cmd, count) for cmd, count in self.stats["commands"].items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]  # Топ-5 команд
        } 