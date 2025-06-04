"""
Утилиты для работы с файлами.
"""
import os
import logging
import shutil
import uuid
from typing import List, Optional

logger = logging.getLogger(__name__)

class TempFileManager:
    """
    Менеджер контекста для безопасной работы с временными файлами.
    Автоматически удаляет все зарегистрированные файлы при выходе из контекста.
    """
    
    def __init__(self, base_temp_dir: str = "temp"):
        """
        Инициализация менеджера временных файлов.
        
        Args:
            base_temp_dir: Базовая директория для временных файлов
        """
        self.temp_files = []
        self.base_temp_dir = base_temp_dir
        
    def __enter__(self):
        """
        Создает временную директорию при входе в контекст.
        """
        os.makedirs(self.base_temp_dir, exist_ok=True)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Удаляет все временные файлы при выходе из контекста.
        """
        self.cleanup()
    
    def register_file(self, file_path: str) -> str:
        """
        Регистрирует файл для последующего удаления.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Тот же путь к файлу для удобства цепочки вызовов
        """
        self.temp_files.append(file_path)
        return file_path
    
    def create_temp_path(self, filename: str) -> str:
        """
        Создает путь к временному файлу.
        
        Args:
            filename: Имя файла
            
        Returns:
            Полный путь к временному файлу
        """
        path = os.path.join(self.base_temp_dir, filename)
        self.register_file(path)
        return path
    
    def get_temp_file_path(self, base_name: str, extension: str = "") -> str:
        """
        Создает путь к временному файлу с уникальным именем.
        
        Args:
            base_name: Базовое имя файла
            extension: Расширение файла (без точки)
            
        Returns:
            Полный путь к временному файлу
        """
        # Создаем уникальное имя файла
        unique_name = f"{base_name}_{uuid.uuid4().hex}"
        if extension:
            unique_name = f"{unique_name}.{extension}"
            
        # Создаем полный путь
        temp_path = os.path.join(self.base_temp_dir, unique_name)
        
        # Регистрируем файл для последующего удаления
        self.register_file(temp_path)
        
        return temp_path
    
    def get_temp_dir(self) -> str:
        """
        Возвращает путь к временной директории.
        
        Returns:
            Путь к временной директории
        """
        os.makedirs(self.base_temp_dir, exist_ok=True)
        return self.base_temp_dir
    
    def cleanup(self):
        """
        Удаляет все зарегистрированные временные файлы.
        """
        errors = []
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Удален временный файл: {file_path}")
            except Exception as e:
                errors.append((file_path, str(e)))
                logger.error(f"Ошибка при удалении временного файла {file_path}: {e}")
        
        # Очищаем список после обработки
        self.temp_files = []
        
        if errors:
            logger.warning(f"Не удалось удалить {len(errors)} временных файлов")
    
    def check_disk_space(self, min_required_mb: int = 100) -> bool:
        """
        Проверяет наличие свободного места на диске.
        
        Args:
            min_required_mb: Минимальное количество требуемых мегабайт
            
        Returns:
            True если достаточно места, False в противном случае
        """
        try:
            # Получаем путь к временной директории
            temp_dir = os.path.abspath(self.base_temp_dir)
            
            # Проверяем свободное место
            stat = shutil.disk_usage(temp_dir)
            free_mb = stat.free / (1024 * 1024)  # Преобразуем в мегабайты
            
            if free_mb < min_required_mb:
                logger.warning(f"Недостаточно свободного места: {free_mb:.2f} МБ. Требуется минимум {min_required_mb} МБ")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при проверке свободного места: {e}")
            return False  # В случае ошибки возвращаем False для безопасности 