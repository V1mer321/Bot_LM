"""
Модуль для real-time мониторинга системы и активности пользователей
"""
import asyncio
import psutil
import time
from datetime import datetime, timedelta
import json
import threading
from collections import defaultdict, deque
from typing import Dict, List, Optional, Any
import logging

# Импорт GPUtil с обработкой ошибок для IDE
try:
    import GPUtil  # type: ignore # noqa: F401
    GPU_AVAILABLE = True
except ImportError as e:
    GPU_AVAILABLE = False
    # Не показываем warning при первом импорте, только при использовании

# Импорт PyTorch с обработкой ошибок
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError as e:
    TORCH_AVAILABLE = False

logger = logging.getLogger(__name__)


class SystemMonitor:
    """Мониторинг системных ресурсов в реальном времени"""
    
    def __init__(self):
        self.start_time = time.time()
        self.metrics_history = deque(maxlen=1440)  # 24 часа по минутам
        self.is_running = False
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Запуск мониторинга в отдельном потоке"""
        if not self.is_running:
            self.is_running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("🔍 Мониторинг системы запущен")
    
    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        logger.info("⏹️ Мониторинг системы остановлен")
    
    def _monitor_loop(self):
        """Основной цикл мониторинга"""
        while self.is_running:
            try:
                metrics = self.collect_system_metrics()
                self.metrics_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'metrics': metrics
                })
                time.sleep(5)  # Обновление каждые 5 секунд
            except Exception as e:
                logger.error(f"Ошибка в мониторинге: {e}")
                time.sleep(10)
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Сбор текущих метрик системы"""
        metrics = {}
        
        # CPU метрики
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()
        metrics['cpu'] = {
            'usage_percent': cpu_percent,
            'frequency_mhz': cpu_freq.current if cpu_freq else None,
            'cores_logical': psutil.cpu_count(),
            'cores_physical': psutil.cpu_count(logical=False)
        }
        
        # Память
        memory = psutil.virtual_memory()
        metrics['memory'] = {
            'total_gb': round(memory.total / (1024**3), 2),
            'used_gb': round(memory.used / (1024**3), 2),
            'available_gb': round(memory.available / (1024**3), 2),
            'usage_percent': memory.percent
        }
        
        # Диск
        disk = psutil.disk_usage('/')
        metrics['disk'] = {
            'total_gb': round(disk.total / (1024**3), 2),
            'used_gb': round(disk.used / (1024**3), 2),
            'free_gb': round(disk.free / (1024**3), 2),
            'usage_percent': round((disk.used / disk.total) * 100, 1)
        }
        
        # Сеть
        network = psutil.net_io_counters()
        metrics['network'] = {
            'bytes_sent': network.bytes_sent,
            'bytes_recv': network.bytes_recv,
            'packets_sent': network.packets_sent,
            'packets_recv': network.packets_recv
        }
        
        # GPU метрики (если доступно)
        if GPU_AVAILABLE:
            metrics['gpu'] = self._get_gpu_metrics()
        elif TORCH_AVAILABLE and torch.cuda.is_available():
            metrics['gpu'] = self._get_torch_gpu_metrics()
        else:
            metrics['gpu'] = None
            
        return metrics
    
    def _get_gpu_metrics(self) -> Optional[Dict]:
        """Получение GPU метрик через GPUtil"""
        try:
            if not GPU_AVAILABLE:
                return None
                
            # Локальный импорт для избежания ошибок IDE
            import GPUtil  # type: ignore
            
            gpus = GPUtil.getGPUs()
            if not gpus:
                return None
                
            gpu = gpus[0]  # Берем первую GPU
            return {
                'name': gpu.name,
                'temperature_c': gpu.temperature,
                'usage_percent': round(gpu.load * 100, 1),
                'memory_total_mb': gpu.memoryTotal,
                'memory_used_mb': gpu.memoryUsed,
                'memory_free_mb': gpu.memoryFree,
                'memory_usage_percent': round((gpu.memoryUsed / gpu.memoryTotal) * 100, 1)
            }
        except Exception as e:
            logger.error(f"Ошибка получения GPU метрик: {e}")
            return None
    
    def _get_torch_gpu_metrics(self) -> Optional[Dict]:
        """Получение GPU метрик через PyTorch"""
        try:
            if not torch.cuda.is_available():
                return None
                
            device = torch.cuda.current_device()
            props = torch.cuda.get_device_properties(device)
            
            memory_reserved = torch.cuda.memory_reserved(device)
            memory_allocated = torch.cuda.memory_allocated(device)
            memory_total = props.total_memory
            
            return {
                'name': props.name,
                'memory_total_mb': round(memory_total / (1024**2), 1),
                'memory_allocated_mb': round(memory_allocated / (1024**2), 1),
                'memory_reserved_mb': round(memory_reserved / (1024**2), 1),
                'memory_usage_percent': round((memory_allocated / memory_total) * 100, 1),
                'compute_capability': f"{props.major}.{props.minor}"
            }
        except Exception as e:
            logger.error(f"Ошибка получения PyTorch GPU метрик: {e}")
            return None
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Получение текущих метрик"""
        return self.collect_system_metrics()
    
    def get_metrics_history(self, minutes: int = 60) -> List[Dict]:
        """Получение истории метрик за последние N минут"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        filtered_metrics = []
        for entry in self.metrics_history:
            entry_time = datetime.fromisoformat(entry['timestamp'])
            if entry_time >= cutoff_time:
                filtered_metrics.append(entry)
                
        return filtered_metrics


class UserActivityMonitor:
    """Мониторинг активности пользователей"""
    
    def __init__(self):
        self.active_users = {}  # user_id -> last_activity_time
        self.user_sessions = defaultdict(list)  # user_id -> [session_data]
        self.hourly_stats = defaultdict(int)  # hour -> user_count
        self.daily_stats = defaultdict(int)  # date -> user_count
        self.request_queue = deque(maxlen=1000)  # Очередь запросов
        
    def log_user_activity(self, user_id: int, activity_type: str, additional_data: Dict = None):
        """Логирование активности пользователя"""
        now = datetime.now()
        
        # Обновляем активного пользователя
        self.active_users[user_id] = {
            'last_activity': now,
            'activity_type': activity_type,
            'additional_data': additional_data or {}
        }
        
        # Логируем сессию
        session_data = {
            'timestamp': now.isoformat(),
            'activity_type': activity_type,
            'additional_data': additional_data or {}
        }
        self.user_sessions[user_id].append(session_data)
        
        # Обновляем статистику
        hour_key = now.strftime('%Y-%m-%d %H')
        date_key = now.strftime('%Y-%m-%d')
        self.hourly_stats[hour_key] += 1
        self.daily_stats[date_key] += 1
        
        # Добавляем в очередь запросов
        self.request_queue.append({
            'timestamp': now.isoformat(),
            'user_id': user_id,
            'activity_type': activity_type
        })
    
    def get_active_users(self, minutes: int = 30) -> Dict[int, Dict]:
        """Получение активных пользователей за последние N минут"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        active = {}
        for user_id, user_data in self.active_users.items():
            if user_data['last_activity'] >= cutoff_time:
                active[user_id] = {
                    'last_activity': user_data['last_activity'].isoformat(),
                    'activity_type': user_data['activity_type'],
                    'minutes_ago': int((datetime.now() - user_data['last_activity']).total_seconds() / 60)
                }
                
        return active
    
    def get_request_queue_status(self) -> Dict[str, Any]:
        """Статус очереди запросов"""
        now = datetime.now()
        recent_requests = [
            req for req in self.request_queue 
            if (now - datetime.fromisoformat(req['timestamp'])).seconds < 300  # 5 минут
        ]
        
        return {
            'total_in_queue': len(self.request_queue),
            'recent_5min': len(recent_requests),
            'avg_per_minute': len(recent_requests) / 5 if recent_requests else 0
        }
    
    def get_activity_statistics(self) -> Dict[str, Any]:
        """Получение статистики активности"""
        now = datetime.now()
        
        # Активность за последний час
        hour_ago = now - timedelta(hours=1)
        hour_key = hour_ago.strftime('%Y-%m-%d %H')
        requests_last_hour = self.hourly_stats.get(hour_key, 0)
        
        # Активность за сегодня
        today_key = now.strftime('%Y-%m-%d')
        requests_today = self.daily_stats.get(today_key, 0)
        
        # Новые пользователи за сегодня
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        new_users_today = len([
            user_id for user_id, sessions in self.user_sessions.items()
            if sessions and datetime.fromisoformat(sessions[0]['timestamp']) >= today_start
        ])
        
        return {
            'active_now': len(self.get_active_users(30)),
            'requests_last_hour': requests_last_hour,
            'requests_today': requests_today,
            'new_users_today': new_users_today,
            'total_registered_users': len(self.user_sessions),
            'queue_status': self.get_request_queue_status()
        }


class PerformanceMonitor:
    """Мониторинг производительности бота"""
    
    def __init__(self):
        self.response_times = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        self.success_counts = defaultdict(int)
        self.model_performance = defaultdict(list)
        
    def log_response_time(self, operation: str, response_time_ms: float, success: bool = True):
        """Логирование времени ответа"""
        now = datetime.now()
        
        self.response_times.append({
            'timestamp': now.isoformat(),
            'operation': operation,
            'response_time_ms': response_time_ms,
            'success': success
        })
        
        if success:
            self.success_counts[operation] += 1
        else:
            self.error_counts[operation] += 1
            
    def log_model_performance(self, model_name: str, inference_time_ms: float, accuracy: float = None):
        """Логирование производительности модели"""
        self.model_performance[model_name].append({
            'timestamp': datetime.now().isoformat(),
            'inference_time_ms': inference_time_ms,
            'accuracy': accuracy
        })
        
        # Оставляем только последние 100 записей для каждой модели
        if len(self.model_performance[model_name]) > 100:
            self.model_performance[model_name] = self.model_performance[model_name][-100:]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Получение статистики производительности"""
        if not self.response_times:
            return {'no_data': True}
            
        # Средние времена ответа за последние 100 запросов
        recent_times = list(self.response_times)[-100:]
        avg_response_time = sum(rt['response_time_ms'] for rt in recent_times) / len(recent_times)
        
        # Процент успешных запросов
        total_success = sum(self.success_counts.values())
        total_errors = sum(self.error_counts.values())
        total_requests = total_success + total_errors
        success_rate = (total_success / total_requests * 100) if total_requests > 0 else 0
        
        # Статистика по моделям
        model_stats = {}
        for model_name, performances in self.model_performance.items():
            if performances:
                recent_perfs = performances[-20:]  # Последние 20 запусков
                avg_inference = sum(p['inference_time_ms'] for p in recent_perfs) / len(recent_perfs)
                model_stats[model_name] = {
                    'avg_inference_ms': round(avg_inference, 1),
                    'total_runs': len(performances)
                }
        
        return {
            'avg_response_time_ms': round(avg_response_time, 1),
            'success_rate_percent': round(success_rate, 1),
            'total_requests': total_requests,
            'total_errors': total_errors,
            'model_stats': model_stats
        }


class RealTimeMonitoring:
    """Центральный класс для real-time мониторинга"""
    
    def __init__(self):
        self.system_monitor = SystemMonitor()
        self.user_activity_monitor = UserActivityMonitor()
        self.performance_monitor = PerformanceMonitor()
        self.alerts = []
        self.alert_thresholds = {
            'cpu_usage': 90,
            'memory_usage': 85,
            'gpu_usage': 95,
            'gpu_temperature': 80,
            'response_time_ms': 1000,
            'error_rate_percent': 10
        }
    
    def start(self):
        """Запуск всех мониторов"""
        self.system_monitor.start_monitoring()
        logger.info("🚀 Real-time мониторинг запущен")
    
    def stop(self):
        """Остановка всех мониторов"""
        self.system_monitor.stop_monitoring()
        logger.info("⏹️ Real-time мониторинг остановлен")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Получение данных для дашборда"""
        system_metrics = self.system_monitor.get_current_metrics()
        activity_stats = self.user_activity_monitor.get_activity_statistics()
        performance_stats = self.performance_monitor.get_performance_stats()
        active_users = self.user_activity_monitor.get_active_users()
        
        # Проверка алертов
        alerts = self._check_alerts(system_metrics, performance_stats)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'system': system_metrics,
            'activity': activity_stats,
            'performance': performance_stats,
            'active_users': active_users,
            'alerts': alerts,
            'uptime_seconds': int(time.time() - self.system_monitor.start_time)
        }
    
    def _check_alerts(self, system_metrics: Dict, performance_stats: Dict) -> List[Dict]:
        """Проверка превышения пороговых значений"""
        alerts = []
        
        # Проверка CPU
        if system_metrics.get('cpu', {}).get('usage_percent', 0) > self.alert_thresholds['cpu_usage']:
            cpu_usage = system_metrics['cpu']['usage_percent']
            alerts.append({
                'type': 'warning',
                'message': f"Высокая загрузка CPU: {cpu_usage:.1f}%%",
                'timestamp': datetime.now().isoformat()
            })
        
        # Проверка памяти
        if system_metrics.get('memory', {}).get('usage_percent', 0) > self.alert_thresholds['memory_usage']:
            mem_usage = system_metrics['memory']['usage_percent']
            alerts.append({
                'type': 'warning',
                'message': f"Высокое потребление RAM: {mem_usage:.1f}%%",
                'timestamp': datetime.now().isoformat()
            })
        
        # Проверка GPU
        gpu_data = system_metrics.get('gpu')
        if gpu_data:
            if gpu_data.get('usage_percent', 0) > self.alert_thresholds['gpu_usage']:
                gpu_usage = gpu_data['usage_percent']
                alerts.append({
                    'type': 'warning',
                    'message': f"Высокая загрузка GPU: {gpu_usage:.1f}%%",
                    'timestamp': datetime.now().isoformat()
                })
            
            if gpu_data.get('temperature_c', 0) > self.alert_thresholds['gpu_temperature']:
                gpu_temp = gpu_data['temperature_c']
                alerts.append({
                    'type': 'critical',
                    'message': f"Перегрев GPU: {gpu_temp}°C",
                    'timestamp': datetime.now().isoformat()
                })
        
        # Проверка производительности
        if not performance_stats.get('no_data'):
            if performance_stats.get('avg_response_time_ms', 0) > self.alert_thresholds['response_time_ms']:
                response_time = performance_stats['avg_response_time_ms']
                alerts.append({
                    'type': 'warning',
                    'message': f"Медленный ответ: {response_time:.0f}ms",
                    'timestamp': datetime.now().isoformat()
                })
            
            error_rate = 100 - performance_stats.get('success_rate_percent', 100)
            if error_rate > self.alert_thresholds['error_rate_percent']:
                alerts.append({
                    'type': 'critical',
                    'message': f"Высокий уровень ошибок: {error_rate:.1f}%%",
                    'timestamp': datetime.now().isoformat()
                })
        
        return alerts
    
    # Методы для логирования активности (используются в других частях бота)
    def log_user_activity(self, user_id: int, activity_type: str, additional_data: Dict = None):
        """Публичный метод для логирования активности пользователя"""
        self.user_activity_monitor.log_user_activity(user_id, activity_type, additional_data)
    
    def log_response_time(self, operation: str, response_time_ms: float, success: bool = True):
        """Публичный метод для логирования времени ответа"""
        self.performance_monitor.log_response_time(operation, response_time_ms, success)
    
    def log_model_performance(self, model_name: str, inference_time_ms: float, accuracy: float = None):
        """Публичный метод для логирования производительности модели"""
        self.performance_monitor.log_model_performance(model_name, inference_time_ms, accuracy)


# Глобальный экземпляр мониторинга
monitoring = RealTimeMonitoring() 