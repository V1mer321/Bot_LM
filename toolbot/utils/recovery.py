#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для восстановления после сбоев и автоматического перезапуска приложения.
Реализует стратегии восстановления и механизмы мониторинга состояния компонентов.
"""

import os
import sys
import time
import signal
import logging
import subprocess
import threading
import traceback
import json
import psutil
from typing import List, Dict, Any, Optional, Callable, Union, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Перечисление для стратегий восстановления"""
    RESTART_COMPONENT = "RESTART_COMPONENT"  # Перезапуск отдельного компонента
    RESTART_APPLICATION = "RESTART_APPLICATION"  # Полный перезапуск приложения
    RESTORE_CHECKPOINT = "RESTORE_CHECKPOINT"  # Восстановление из контрольной точки
    FALLBACK_MODE = "FALLBACK_MODE"  # Переход в безопасный режим работы


class ComponentState(Enum):
    """Перечисление для состояний компонентов"""
    STARTING = "STARTING"  # Компонент запускается
    RUNNING = "RUNNING"    # Компонент работает нормально
    WARNING = "WARNING"    # Компонент работает с предупреждениями
    ERROR = "ERROR"        # Компонент в состоянии ошибки
    RECOVERING = "RECOVERING"  # Компонент восстанавливается
    STOPPED = "STOPPED"    # Компонент остановлен


class RecoveryManager:
    """
    Менеджер восстановления для обеспечения стабильной работы приложения.
    Выполняет мониторинг состояния компонентов и применяет соответствующие стратегии восстановления.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """
        Получение экземпляра менеджера восстановления (шаблон Singleton).
        
        Returns:
            Экземпляр RecoveryManager
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Инициализация менеджера восстановления"""
        self.components = {}  # Словарь для хранения состояния компонентов
        self.restart_count = 0  # Счетчик перезапусков
        self.startup_time = time.time()  # Время запуска
        self.max_restarts = 5  # Максимальное количество перезапусков
        self.restart_window = 3600  # Окно времени для подсчета перезапусков (1 час)
        self.recovery_log_path = os.path.join("logs", "recovery.log")
        self.state_file_path = os.path.join("logs", "component_states.json")
        self.watchdog_thread = None
        self.is_running = False
        
        # Создаем директорию для логов, если она не существует
        os.makedirs(os.path.dirname(self.recovery_log_path), exist_ok=True)
        
        # Словарь обработчиков для разных компонентов
        self.recovery_handlers = {}
        
        # Загружаем предыдущие состояния компонентов
        self._load_component_states()
        
        # Устанавливаем обработчики сигналов для корректного завершения
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        """
        Обрабатывает сигналы завершения для корректного завершения работы.
        
        Args:
            signum: Номер сигнала
            frame: Текущий фрейм выполнения
        """
        logger.info(f"Получен сигнал {signum}, завершение работы...")
        self.stop()
        # Продолжаем стандартную обработку сигнала
        sys.exit(0)
    
    def _load_component_states(self):
        """Загружает предыдущие состояния компонентов из файла"""
        try:
            if os.path.exists(self.state_file_path):
                try:
                    with open(self.state_file_path, 'r', encoding='utf-8') as f:
                        states = json.load(f)
                        # Конвертируем строковые состояния в перечисления
                        for component, state_data in states.items():
                            if "state" in state_data:
                                try:
                                    state_data["state"] = ComponentState(state_data["state"])
                                except ValueError:
                                    state_data["state"] = ComponentState.STOPPED
                            self.components[component] = state_data
                        logger.info(f"Загружены состояния {len(self.components)} компонентов")
                except json.JSONDecodeError as je:
                    logger.warning(f"Файл состояний компонентов поврежден, создаем новый: {je}")
                    # Удаляем поврежденный файл
                    try:
                        os.remove(self.state_file_path)
                    except Exception:
                        pass
                    # Создаем пустой словарь состояний
                    self.components = {}
        except Exception as e:
            logger.error(f"Ошибка при загрузке состояний компонентов: {e}")
            # Не позволяем ошибке блокировать запуск
            self.components = {}
    
    def _save_component_states(self):
        """Сохраняет текущие состояния компонентов в файл"""
        try:
            # Конвертируем перечисления в строки для сериализации
            serializable_states = {}
            for component, state_data in self.components.items():
                serializable_states[component] = {}
                for key, value in state_data.items():
                    # Пропускаем функции, которые нельзя сериализовать
                    if callable(value):
                        continue
                    # Преобразуем перечисления в строки
                    if isinstance(value, ComponentState):
                        serializable_states[component][key] = value.value
                    else:
                        serializable_states[component][key] = value
            
            with open(self.state_file_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_states, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении состояний компонентов: {e}")
    
    def register_component(self, component_name: str, restart_func: Optional[Callable] = None,
                         health_check_func: Optional[Callable[[], bool]] = None):
        """
        Регистрирует компонент для мониторинга и восстановления.
        
        Args:
            component_name: Имя компонента
            restart_func: Функция для перезапуска компонента
            health_check_func: Функция для проверки состояния компонента
        """
        self.components[component_name] = {
            "state": ComponentState.STOPPED,
            "restart_func": restart_func,
            "health_check_func": health_check_func,
            "last_restart": None,
            "restart_count": 0,
            "last_error": None
        }
        logger.info(f"Зарегистрирован компонент для мониторинга: {component_name}")
    
    def set_component_state(self, component_name: str, state: ComponentState, 
                          error_message: Optional[str] = None):
        """
        Устанавливает состояние компонента.
        
        Args:
            component_name: Имя компонента
            state: Новое состояние
            error_message: Сообщение об ошибке (если применимо)
        """
        if component_name not in self.components:
            logger.warning(f"Попытка установить состояние для незарегистрированного компонента: {component_name}")
            return
        
        prev_state = self.components[component_name].get("state")
        self.components[component_name]["state"] = state
        self.components[component_name]["last_update"] = time.time()
        
        if error_message:
            self.components[component_name]["last_error"] = error_message
        
        # Логируем изменение состояния
        logger.info(f"Состояние компонента {component_name} изменено: {prev_state} -> {state}")
        
        # Если компонент перешел в состояние ошибки, пытаемся восстановить
        if state == ComponentState.ERROR and prev_state != ComponentState.ERROR:
            self._try_recover_component(component_name)
        
        # Сохраняем обновленные состояния
        self._save_component_states()
    
    def _try_recover_component(self, component_name: str):
        """
        Пытается восстановить компонент, применяя стратегию восстановления.
        
        Args:
            component_name: Имя компонента для восстановления
        """
        if component_name not in self.components:
            logger.warning(f"Попытка восстановить незарегистрированный компонент: {component_name}")
            return False
        
        component = self.components[component_name]
        
        # Проверяем, не превышено ли максимальное количество перезапусков
        current_time = time.time()
        if component.get("restart_count", 0) >= self.max_restarts:
            if current_time - self.startup_time <= self.restart_window:
                logger.error(f"Достигнуто максимальное количество перезапусков для {component_name}. Переход в безопасный режим.")
                self.set_component_state(component_name, ComponentState.WARNING, 
                                       "Превышено максимальное количество перезапусков")
                # Применяем стратегию FALLBACK_MODE
                self._apply_recovery_strategy(component_name, RecoveryStrategy.FALLBACK_MODE)
                return False
            else:
                # Сбрасываем счетчик перезапусков, если прошло достаточно времени
                component["restart_count"] = 0
        
        # Обновляем состояние и счетчик перезапусков
        self.set_component_state(component_name, ComponentState.RECOVERING)
        component["restart_count"] = component.get("restart_count", 0) + 1
        component["last_restart"] = current_time
        
        # Логируем попытку восстановления
        logger.info(f"Попытка восстановления компонента {component_name}. Перезапуск #{component['restart_count']}")
        
        # Попытка восстановления с помощью зарегистрированной функции перезапуска
        restart_func = component.get("restart_func")
        if restart_func and callable(restart_func):
            try:
                restart_func()
                self.set_component_state(component_name, ComponentState.RUNNING)
                logger.info(f"Компонент {component_name} успешно перезапущен")
                return True
            except Exception as e:
                error_msg = f"Ошибка при перезапуске компонента {component_name}: {str(e)}"
                logger.error(error_msg)
                self.set_component_state(component_name, ComponentState.ERROR, error_msg)
                return False
        else:
            # Если функция перезапуска не определена, применяем стратегию RESTART_APPLICATION
            logger.warning(f"Функция перезапуска не определена для {component_name}. Применяется стратегия полного перезапуска.")
            return self._apply_recovery_strategy(component_name, RecoveryStrategy.RESTART_APPLICATION)
    
    def _apply_recovery_strategy(self, component_name: str, strategy: RecoveryStrategy) -> bool:
        """
        Применяет указанную стратегию восстановления к компоненту.
        
        Args:
            component_name: Имя компонента
            strategy: Стратегия восстановления
            
        Returns:
            True, если стратегия успешно применена, иначе False
        """
        logger.info(f"Применение стратегии восстановления {strategy.value} для компонента {component_name}")
        
        # Записываем событие восстановления в лог
        recovery_event = {
            "timestamp": time.time(),
            "component": component_name,
            "strategy": strategy.value,
            "error": self.components[component_name].get("last_error")
        }
        
        try:
            with open(self.recovery_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(recovery_event) + "\n")
        except Exception as e:
            logger.error(f"Ошибка при записи события восстановления: {e}")
        
        # Применяем выбранную стратегию
        if strategy == RecoveryStrategy.RESTART_COMPONENT:
            # Эта стратегия уже применена в _try_recover_component
            return True
            
        elif strategy == RecoveryStrategy.RESTART_APPLICATION:
            # Полный перезапуск приложения
            self.restart_application()
            return True
            
        elif strategy == RecoveryStrategy.RESTORE_CHECKPOINT:
            # Восстановление из контрольной точки
            # В данной реализации просто перезапускаем компонент
            return self._try_recover_component(component_name)
            
        elif strategy == RecoveryStrategy.FALLBACK_MODE:
            # Переход в безопасный режим работы
            logger.warning(f"Компонент {component_name} переведен в безопасный режим работы")
            self.set_component_state(component_name, ComponentState.WARNING, 
                                   "Компонент работает в безопасном режиме")
            return True
            
        else:
            logger.error(f"Неизвестная стратегия восстановления: {strategy}")
            return False
    
    def restart_application(self):
        """
        Выполняет полный перезапуск приложения.
        """
        logger.warning("Выполняется полный перезапуск приложения...")
        
        # Сохраняем текущие состояния компонентов перед перезапуском
        self._save_component_states()
        
        # Получаем команду и аргументы для перезапуска
        args = sys.argv[:]
        
        # Логируем команду перезапуска
        logger.info(f"Команда перезапуска: {sys.executable} {' '.join(args)}")
        
        # Запускаем новый процесс
        try:
            subprocess.Popen([sys.executable] + args)
            logger.info("Новый процесс запущен, завершение текущего процесса...")
            
            # Даем новому процессу время на запуск
            time.sleep(1)
            
            # Завершаем текущий процесс
            os._exit(0)
        except Exception as e:
            logger.error(f"Ошибка при перезапуске приложения: {e}")
            return False
    
    def check_component_health(self, component_name: str) -> bool:
        """
        Проверяет состояние здоровья компонента.
        
        Args:
            component_name: Имя компонента для проверки
            
        Returns:
            True, если компонент здоров, иначе False
        """
        if component_name not in self.components:
            logger.warning(f"Попытка проверить здоровье незарегистрированного компонента: {component_name}")
            return False
        
        component = self.components[component_name]
        
        # Если компонент в состоянии ошибки или восстановления, считаем его нездоровым
        if component["state"] in [ComponentState.ERROR, ComponentState.RECOVERING]:
            return False
        
        # Вызываем функцию проверки здоровья, если она определена
        health_check_func = component.get("health_check_func")
        if health_check_func and callable(health_check_func):
            try:
                is_healthy = health_check_func()
                if not is_healthy and component["state"] != ComponentState.ERROR:
                    self.set_component_state(component_name, ComponentState.ERROR, 
                                           "Проверка здоровья не пройдена")
                elif is_healthy and component["state"] != ComponentState.RUNNING:
                    self.set_component_state(component_name, ComponentState.RUNNING)
                return is_healthy
            except Exception as e:
                error_msg = f"Ошибка при проверке здоровья компонента {component_name}: {str(e)}"
                logger.error(error_msg)
                self.set_component_state(component_name, ComponentState.ERROR, error_msg)
                return False
        
        # Если функция проверки не определена, считаем компонент здоровым
        return component["state"] == ComponentState.RUNNING
    
    def start_watchdog(self, check_interval: int = 60):
        """
        Запускает поток сторожевого таймера для мониторинга компонентов.
        
        Args:
            check_interval: Интервал проверки в секундах
        """
        if self.watchdog_thread and self.watchdog_thread.is_alive():
            logger.warning("Сторожевой таймер уже запущен")
            return
        
        self.is_running = True
        self.watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            args=(check_interval,),
            daemon=True,
            name="RecoveryWatchdog"
        )
        self.watchdog_thread.start()
        logger.info(f"Сторожевой таймер запущен с интервалом {check_interval} сек.")
    
    def _watchdog_loop(self, check_interval: int):
        """
        Основной цикл сторожевого таймера.
        
        Args:
            check_interval: Интервал проверки в секундах
        """
        while self.is_running:
            try:
                # Проверяем состояние всех компонентов
                for component_name in list(self.components.keys()):
                    if self.components[component_name]["state"] != ComponentState.STOPPED:
                        self.check_component_health(component_name)
                
                # Проверяем общее состояние приложения
                self._check_system_resources()
                
                # Сохраняем текущие состояния
                self._save_component_states()
            except Exception as e:
                logger.error(f"Ошибка в цикле сторожевого таймера: {e}")
            
            # Пауза между проверками
            time.sleep(check_interval)
    
    def _check_system_resources(self):
        """
        Проверяет системные ресурсы и логирует предупреждения при их нехватке.
        """
        try:
            # Проверка памяти
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                logger.warning(f"Критический уровень использования памяти: {memory.percent}%%")
            
            # Проверка CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                logger.warning(f"Критический уровень использования CPU: {cpu_percent}%%")
            
            # Проверка диска (используем правильный путь для Windows)
            import platform
            if platform.system() == "Windows":
                disk_path = "C:\\"
            else:
                disk_path = "/"
            
            disk = psutil.disk_usage(disk_path)
            if disk.percent > 90:
                logger.warning(f"Критический уровень использования диска: {disk.percent}%%")
        except Exception as e:
            logger.error(f"Ошибка при проверке системных ресурсов: {e}")
    
    def stop(self):
        """
        Останавливает менеджер восстановления и его сторожевой таймер.
        """
        logger.info("Остановка менеджера восстановления...")
        self.is_running = False
        
        # Ожидаем завершения потока сторожевого таймера
        if self.watchdog_thread and self.watchdog_thread.is_alive():
            self.watchdog_thread.join(timeout=5)
        
        # Сохраняем состояния компонентов
        self._save_component_states()
        logger.info("Менеджер восстановления остановлен")
    
    def get_component_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Возвращает текущие состояния всех компонентов.
        
        Returns:
            Словарь с состояниями компонентов
        """
        # Копируем для безопасного доступа
        return {k: v.copy() for k, v in self.components.items()}


# Удобные функции для работы с менеджером восстановления
def register_component(component_name: str, restart_func=None, health_check_func=None):
    """Регистрирует компонент для мониторинга и восстановления"""
    RecoveryManager.get_instance().register_component(component_name, restart_func, health_check_func)


def set_component_state(component_name: str, state: ComponentState, error_message: str = None):
    """Устанавливает состояние компонента"""
    RecoveryManager.get_instance().set_component_state(component_name, state, error_message)


def start_watchdog(check_interval: int = 60):
    """Запускает сторожевой таймер для мониторинга компонентов"""
    RecoveryManager.get_instance().start_watchdog(check_interval)


def stop_recovery_manager():
    """Останавливает менеджер восстановления"""
    RecoveryManager.get_instance().stop()


def restart_application():
    """Выполняет полный перезапуск приложения"""
    RecoveryManager.get_instance().restart_application()


# Инициализируем менеджер восстановления при импорте модуля
recovery_manager = RecoveryManager.get_instance() 