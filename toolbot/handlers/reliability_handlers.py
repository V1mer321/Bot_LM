#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль с обработчиками команд для мониторинга надежности бота.
"""

import os
import time
import logging
import asyncio
from typing import List, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes

from toolbot.utils.error_handler import ErrorHandler, ErrorSeverity
from toolbot.utils.recovery import RecoveryManager, ComponentState
from toolbot.utils.enhanced_logging import get_logger, LogLevel
from toolbot.config import is_admin  # Используем зашифрованную конфигурацию для админ-проверок

# Получаем логгер для модуля
logger = get_logger(__name__)


async def error_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /error_stats - показывает статистику ошибок.
    
    Args:
        update: Объект обновления
        context: Контекст обработчика
    """
    user_id = update.effective_user.id
    
    # Проверяем, является ли пользователь администратором
    if not await is_admin_async(user_id):
        await update.message.reply_text(
            "❌ У вас нет доступа к этой команде. Только администраторы могут просматривать статистику ошибок."
        )
        return
    
    # Получаем статистику ошибок
    error_handler = ErrorHandler.get_instance()
    stats = error_handler.get_error_stats()
    
    # Форматируем сообщение
    total_errors = stats.get("total_errors", 0)
    error_counts = stats.get("error_counts", {})
    
    if not error_counts:
        await update.message.reply_text(
            "✅ Статистика ошибок\n\n"
            "Ошибок не обнаружено! Система работает стабильно."
        )
        return
    
    # Сортируем ошибки по количеству (от большего к меньшему)
    sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Форматируем сообщение со статистикой
    message = f"📊 Статистика ошибок\n\n"
    message += f"Всего ошибок: {total_errors}\n\n"
    message += "Типы ошибок:\n"
    
    for error_type, count in sorted_errors[:10]:  # Показываем топ-10 ошибок
        percentage = (count / total_errors) * 100
        message += f"• {error_type}: {count} ({percentage:.1f}%)\n"
    
    if len(sorted_errors) > 10:
        message += f"\n... и еще {len(sorted_errors) - 10} типов ошибок"
    
    await update.message.reply_text(message)


async def components_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /components_status - показывает состояние компонентов системы.
    
    Args:
        update: Объект обновления
        context: Контекст обработчика
    """
    user_id = update.effective_user.id
    
    # Получаем состояния компонентов
    recovery_manager = RecoveryManager.get_instance()
    components = recovery_manager.get_component_states()
    
    # Определяем эмодзи для разных состояний
    state_emoji = {
        ComponentState.RUNNING: "✅",
        ComponentState.STARTING: "🔄",
        ComponentState.WARNING: "⚠️",
        ComponentState.ERROR: "❌",
        ComponentState.RECOVERING: "🔧",
        ComponentState.STOPPED: "⏹"
    }
    
    # Формируем сообщение с состояниями компонентов
    if not components:
        await update.message.reply_text(
            "ℹ️ Информация о компонентах\n\n"
            "Нет зарегистрированных компонентов для мониторинга."
        )
        return
    
    message = "📊 Состояние компонентов системы\n\n"
    
    for name, data in components.items():
        state = data.get("state", ComponentState.STOPPED)
        emoji = state_emoji.get(state, "❓")
        last_update = data.get("last_update")
        last_restart = data.get("last_restart")
        restart_count = data.get("restart_count", 0)
        last_error = data.get("last_error")
        
        # Форматируем время обновления
        if last_update:
            time_ago = int(time.time() - last_update)
            if time_ago < 60:
                time_str = f"{time_ago} сек. назад"
            elif time_ago < 3600:
                time_str = f"{time_ago // 60} мин. назад"
            else:
                time_str = f"{time_ago // 3600} час. назад"
        else:
            time_str = "неизвестно"
        
        # Добавляем информацию о компоненте
        message += f"{emoji} <b>{name}</b>: {state.value}\n"
        message += f"   Обновлено: {time_str}\n"
        
        if restart_count > 0:
            message += f"   Перезапусков: {restart_count}\n"
        
        if last_error:
            message += f"   Последняя ошибка: {last_error[:50]}...\n"
        
        message += "\n"
    
    # Отправляем сообщение
    await update.message.reply_text(message, parse_mode="HTML")


async def test_recovery_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /test_recovery - тестирует механизм восстановления.
    Доступен только администраторам.
    
    Args:
        update: Объект обновления
        context: Контекст обработчика
    """
    user_id = update.effective_user.id
    
    # Проверяем, является ли пользователь администратором
    if not await is_admin_async(user_id):
        await update.message.reply_text(
            "❌ У вас нет доступа к этой команде. Только администраторы могут тестировать механизм восстановления."
        )
        return
    
    # Запрашиваем подтверждение
    if not context.args or context.args[0].lower() != "confirm":
        await update.message.reply_text(
            "⚠️ Внимание! Эта команда тестирует механизм восстановления путем симуляции сбоя.\n\n"
            "Для подтверждения выполните команду с параметром 'confirm':\n"
            "/test_recovery confirm"
        )
        return
    
    # Получаем менеджер восстановления
    recovery_manager = RecoveryManager.get_instance()
    
    # Отправляем сообщение о начале теста
    message = await update.message.reply_text(
        "🔄 Начинаю тестирование механизма восстановления...\n"
        "Симулирую сбой компонента 'telegram_bot'..."
    )
    
    # Симулируем сбой
    recovery_manager.set_component_state("telegram_bot", ComponentState.ERROR, 
                                       "Тестовая ошибка для проверки механизма восстановления")
    
    # Ждем несколько секунд
    await asyncio.sleep(3)
    
    # Получаем текущее состояние
    components = recovery_manager.get_component_states()
    bot_state = components.get("telegram_bot", {}).get("state", ComponentState.STOPPED)
    
    # Проверяем результат
    if bot_state == ComponentState.RUNNING:
        status = "✅ Тест успешно пройден! Компонент автоматически восстановлен."
    elif bot_state == ComponentState.RECOVERING:
        status = "⏳ Компонент в процессе восстановления. Механизм восстановления запущен."
    else:
        status = f"❌ Компонент не восстановлен. Текущее состояние: {bot_state.value}"
    
    # Обновляем сообщение с результатом теста
    await message.edit_text(
        f"🧪 Результат тестирования механизма восстановления\n\n"
        f"{status}"
    )
    
    # Устанавливаем нормальное состояние компонента
    recovery_manager.set_component_state("telegram_bot", ComponentState.RUNNING)


async def logs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /logs - показывает последние записи журнала.
    Доступен только администраторам.
    
    Args:
        update: Объект обновления
        context: Контекст обработчика
    """
    user_id = update.effective_user.id
    
    # Проверяем, является ли пользователь администратором
    if not await is_admin_async(user_id):
        await update.message.reply_text(
            "❌ У вас нет доступа к этой команде. Только администраторы могут просматривать журналы."
        )
        return
    
    # Парсим аргументы
    log_type = "main"  # Тип журнала по умолчанию
    lines = 20  # Количество строк по умолчанию
    
    if context.args:
        for arg in context.args:
            if arg in ["main", "error", "recovery", "json"]:
                log_type = arg
            elif arg.isdigit():
                lines = int(arg)
    
    # Определяем путь к файлу журнала
    log_files = {
        "main": os.path.join("logs", "toolbot.log"),
        "error": os.path.join("logs", "errors.log"),
        "recovery": os.path.join("logs", "recovery.log"),
        "json": os.path.join("logs", "toolbot_json.log")
    }
    
    log_file = log_files.get(log_type)
    
    # Проверяем существование файла
    if not log_file or not os.path.exists(log_file):
        await update.message.reply_text(
            f"❌ Файл журнала '{log_type}' не найден."
        )
        return
    
    # Читаем последние строки файла
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            # Эффективное чтение последних строк
            last_lines = read_last_lines(f, lines)
    except Exception as e:
        logger.error(f"Ошибка при чтении файла журнала: {e}")
        await update.message.reply_text(
            f"❌ Ошибка при чтении файла журнала: {e}"
        )
        return
    
    # Форматируем сообщение
    message = f"📋 Последние {len(last_lines)} строк журнала '{log_type}':\n\n"
    
    # Проверяем длину сообщения
    log_content = "\n".join(last_lines)
    if len(message) + len(log_content) > 4000:
        # Если сообщение слишком длинное, отправляем файл
        with open("temp_log.txt", "w", encoding="utf-8") as temp_file:
            temp_file.write(log_content)
        
        with open("temp_log.txt", "rb") as temp_file:
            await update.message.reply_document(
                document=temp_file,
                filename=f"{log_type}_last_{len(last_lines)}_lines.txt",
                caption=f"📋 Последние {len(last_lines)} строк журнала '{log_type}'"
            )
        
        # Удаляем временный файл
        os.remove("temp_log.txt")
    else:
        # Иначе отправляем как текстовое сообщение
        message += f"```\n{log_content}\n```"
        await update.message.reply_text(message, parse_mode="Markdown")


def read_last_lines(file, num_lines: int) -> List[str]:
    """
    Эффективно читает последние строки из файла.
    
    Args:
        file: Объект файла
        num_lines: Количество строк для чтения
        
    Returns:
        Список последних строк
    """
    # Переходим в конец файла
    file.seek(0, os.SEEK_END)
    
    # Позиция в файле
    position = file.tell()
    
    # Список строк
    lines = []
    
    # Читаем строки с конца
    line_count = 0
    while position >= 0 and line_count < num_lines:
        # Переходим на позицию
        file.seek(position)
        
        # Если не в начале файла, пропускаем текущий символ
        if position > 0:
            file.seek(position - 1)
        
        # Читаем символ
        char = file.read(1)
        
        # Если символ перевода строки и позиция не в конце файла,
        # добавляем строку в список
        if char == '\n' and position != file.tell() - 1:
            line = file.readline()
            lines.append(line.rstrip())
            line_count += 1
        
        # Переходим к предыдущему символу
        position -= 1
    
    # Возвращаем список в обратном порядке
    return lines[::-1]


async def is_admin_async(user_id: int) -> bool:
    """
    Асинхронная обертка для проверки прав администратора.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        True, если пользователь администратор, иначе False
    """
    return is_admin(user_id) 