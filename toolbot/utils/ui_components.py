#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль с компонентами пользовательского интерфейса для телеграм-бота.
Содержит классы для создания интерактивных кнопок, пошаговых мастеров и индикаторов прогресса.
"""

import logging
import time
import json
from typing import List, Dict, Callable, Any, Optional, Union
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

logger = logging.getLogger(__name__)


class InteractiveButtons:
    """
    Класс для создания и управления интерактивными кнопками в сообщениях бота.
    """
    
    @staticmethod
    def create_button_layout(buttons: List[Dict[str, str]], row_width: int = 2) -> InlineKeyboardMarkup:
        """
        Создает разметку с кнопками для сообщения.
        
        Args:
            buttons: Список словарей с параметрами кнопок {'text': 'Текст кнопки', 'callback_data': 'callback_data'}
            row_width: Количество кнопок в одной строке
            
        Returns:
            Разметка с кнопками для сообщения
        """
        markup = InlineKeyboardMarkup(row_width=row_width)
        
        # Создаем кнопки из переданных данных
        button_objects = []
        for button in buttons:
            if 'url' in button:
                button_objects.append(InlineKeyboardButton(
                    text=button['text'], 
                    url=button['url']
                ))
            else:
                button_objects.append(InlineKeyboardButton(
                    text=button['text'], 
                    callback_data=button['callback_data']
                ))
        
        # Разбиваем на строки по row_width кнопок
        for i in range(0, len(button_objects), row_width):
            markup.add(*button_objects[i:i+row_width])
            
        return markup
    
    @staticmethod
    def create_quick_actions(actions: List[Dict[str, str]]) -> InlineKeyboardMarkup:
        """
        Создает панель быстрых действий для популярных функций.
        
        Args:
            actions: Список словарей с параметрами кнопок действий
            
        Returns:
            Разметка с кнопками быстрых действий
        """
        return InteractiveButtons.create_button_layout(actions, row_width=2)
    
    @staticmethod
    def create_pagination(current_page: int, total_pages: int, 
                         callback_prefix: str) -> InlineKeyboardMarkup:
        """
        Создает кнопки для пагинации результатов.
        
        Args:
            current_page: Текущая страница
            total_pages: Общее количество страниц
            callback_prefix: Префикс для callback_data
            
        Returns:
            Разметка с кнопками пагинации
        """
        markup = InlineKeyboardMarkup(row_width=5)
        buttons = []
        
        # Кнопка "Назад"
        if current_page > 1:
            buttons.append(InlineKeyboardButton(
                text="◀️",
                callback_data=f"{callback_prefix}_page_{current_page-1}"
            ))
        
        # Номер текущей страницы
        buttons.append(InlineKeyboardButton(
            text=f"{current_page}/{total_pages}",
            callback_data=f"page_info"
        ))
        
        # Кнопка "Вперед"
        if current_page < total_pages:
            buttons.append(InlineKeyboardButton(
                text="▶️",
                callback_data=f"{callback_prefix}_page_{current_page+1}"
            ))
        
        markup.add(*buttons)
        
        return markup


class StepByStepWizard:
    """
    Класс для создания пошаговых мастеров, упрощающих сложные процессы.
    """
    
    def __init__(self, bot, steps: List[Dict[str, Any]], user_id: int, 
                initial_message_text: str, on_complete: Callable = None):
        """
        Инициализация мастера.
        
        Args:
            bot: Экземпляр бота для отправки сообщений
            steps: Список шагов мастера
            user_id: ID пользователя
            initial_message_text: Начальный текст сообщения
            on_complete: Функция, вызываемая по завершении всех шагов
        """
        self.bot = bot
        self.steps = steps
        self.user_id = user_id
        self.current_step = 0
        self.user_data = {}
        self.on_complete = on_complete
        self.message_id = None
        self.initial_message_text = initial_message_text
    
    def start(self) -> None:
        """
        Запускает мастер с первого шага.
        """
        if not self.steps:
            logger.error("Не определены шаги для мастера")
            return
        
        # Отправляем начальное сообщение с описанием мастера
        message = self.bot.send_message(
            self.user_id, 
            self.initial_message_text,
            reply_markup=self._create_step_markup(self.current_step),
            parse_mode='HTML'
        )
        self.message_id = message.message_id
        
    def _create_step_markup(self, step_index: int) -> InlineKeyboardMarkup:
        """
        Создает разметку для текущего шага.
        
        Args:
            step_index: Индекс текущего шага
            
        Returns:
            Разметка с кнопками для текущего шага
        """
        step = self.steps[step_index]
        buttons = step.get('buttons', [])
        
        # Добавляем кнопки навигации
        navigation = []
        if step_index > 0:
            navigation.append({
                'text': '◀️ Назад',
                'callback_data': f"wizard_prev_{id(self)}"
            })
        
        if step_index < len(self.steps) - 1:
            navigation.append({
                'text': 'Далее ▶️',
                'callback_data': f"wizard_next_{id(self)}"
            })
        else:
            navigation.append({
                'text': '✅ Завершить',
                'callback_data': f"wizard_complete_{id(self)}"
            })
        
        # Добавляем кнопку отмены
        navigation.append({
            'text': '❌ Отмена',
            'callback_data': f"wizard_cancel_{id(self)}"
        })
        
        # Создаем разметку с кнопками шага и навигацией
        markup = InlineKeyboardMarkup(row_width=2)
        
        # Добавляем кнопки шага
        for i in range(0, len(buttons), 2):
            row_buttons = []
            for button in buttons[i:i+2]:
                row_buttons.append(
                    InlineKeyboardButton(
                        text=button['text'],
                        callback_data=button['callback_data']
                    )
                )
            markup.add(*row_buttons)
        
        # Добавляем кнопки навигации
        nav_buttons = []
        for button in navigation:
            nav_buttons.append(
                InlineKeyboardButton(
                    text=button['text'],
                    callback_data=button['callback_data']
                )
            )
        
        # Добавляем кнопки навигации в одну или две строки
        if len(nav_buttons) <= 2:
            markup.add(*nav_buttons)
        else:
            markup.add(*nav_buttons[:2])
            markup.add(*nav_buttons[2:])
        
        return markup
    
    def process_step_input(self, callback_query: CallbackQuery) -> None:
        """
        Обрабатывает ввод пользователя на текущем шаге.
        
        Args:
            callback_query: Объект callback запроса
        """
        callback_data = callback_query.data
        
        # Проверяем, что это команда для нашего мастера
        if not any(prefix in callback_data for prefix in 
                  [f"wizard_next_{id(self)}", f"wizard_prev_{id(self)}", 
                   f"wizard_complete_{id(self)}", f"wizard_cancel_{id(self)}"]):
            # Обрабатываем ввод пользователя для текущего шага
            current_step = self.steps[self.current_step]
            if 'process_input' in current_step and callable(current_step['process_input']):
                # Вызываем обработчик ввода для текущего шага
                current_step['process_input'](callback_query, self.user_data)
            
            # Обновляем сообщение с учетом ввода пользователя
            self._update_message()
            return
        
        # Обрабатываем команды навигации
        if f"wizard_next_{id(self)}" in callback_data:
            self._go_to_next_step()
        elif f"wizard_prev_{id(self)}" in callback_data:
            self._go_to_prev_step()
        elif f"wizard_complete_{id(self)}" in callback_data:
            self._complete_wizard()
        elif f"wizard_cancel_{id(self)}" in callback_data:
            self._cancel_wizard()
    
    def _go_to_next_step(self) -> None:
        """
        Переходит к следующему шагу мастера.
        """
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self._update_message()
    
    def _go_to_prev_step(self) -> None:
        """
        Переходит к предыдущему шагу мастера.
        """
        if self.current_step > 0:
            self.current_step -= 1
            self._update_message()
    
    def _update_message(self) -> None:
        """
        Обновляет сообщение с текущим шагом.
        """
        if not self.message_id:
            return
        
        current_step = self.steps[self.current_step]
        
        # Получаем текст для шага
        if 'get_text' in current_step and callable(current_step['get_text']):
            text = current_step['get_text'](self.user_data)
        else:
            text = current_step.get('text', 'Шаг без описания')
        
        # Добавляем индикатор прогресса
        progress_text = f"<b>Шаг {self.current_step + 1} из {len(self.steps)}</b>\n\n"
        
        # Обновляем сообщение
        try:
            self.bot.edit_message_text(
                chat_id=self.user_id,
                message_id=self.message_id,
                text=progress_text + text,
                reply_markup=self._create_step_markup(self.current_step),
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении сообщения мастера: {e}")
    
    def _complete_wizard(self) -> None:
        """
        Завершает мастер и вызывает колбэк завершения.
        """
        try:
            # Обновляем сообщение с информацией о завершении
            self.bot.edit_message_text(
                chat_id=self.user_id,
                message_id=self.message_id,
                text="✅ <b>Мастер завершен</b>\n\nСпасибо за предоставленную информацию!",
                parse_mode='HTML'
            )
            
            # Вызываем функцию завершения, если она определена
            if self.on_complete and callable(self.on_complete):
                self.on_complete(self.user_data)
        except Exception as e:
            logger.error(f"Ошибка при завершении мастера: {e}")
    
    def _cancel_wizard(self) -> None:
        """
        Отменяет мастер.
        """
        try:
            # Обновляем сообщение с информацией об отмене
            self.bot.edit_message_text(
                chat_id=self.user_id,
                message_id=self.message_id,
                text="❌ <b>Мастер отменен</b>\n\nВы можете запустить его снова, когда будете готовы.",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Ошибка при отмене мастера: {e}")


class ProgressIndicator:
    """
    Класс для отображения индикаторов прогресса в длительных операциях.
    """
    
    def __init__(self, bot, chat_id: int, operation_name: str = "Операция"):
        """
        Инициализация индикатора прогресса.
        
        Args:
            bot: Экземпляр бота для отправки сообщений
            chat_id: ID чата для отправки индикатора
            operation_name: Название операции
        """
        self.bot = bot
        self.chat_id = chat_id
        self.operation_name = operation_name
        self.message_id = None
        self.start_time = None
        self.is_completed = False
    
    def start(self, initial_percent: int = 0) -> None:
        """
        Запускает индикатор прогресса.
        
        Args:
            initial_percent: Начальный процент выполнения
        """
        self.start_time = time.time()
        message = self.bot.send_message(
            self.chat_id,
            self._get_progress_text(initial_percent),
            parse_mode='HTML'
        )
        self.message_id = message.message_id
    
    def update(self, percent: int, status_text: str = "") -> None:
        """
        Обновляет индикатор прогресса.
        
        Args:
            percent: Процент выполнения (0-100)
            status_text: Дополнительный текст статуса
        """
        if self.is_completed or not self.message_id:
            return
        
        # Убеждаемся, что процент в допустимом диапазоне
        percent = max(0, min(100, percent))
        
        try:
            self.bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.message_id,
                text=self._get_progress_text(percent, status_text),
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении индикатора прогресса: {e}")
    
    def complete(self, final_text: str = "Операция завершена") -> None:
        """
        Завершает индикатор прогресса.
        
        Args:
            final_text: Текст завершения
        """
        if self.is_completed or not self.message_id:
            return
        
        elapsed_time = time.time() - self.start_time
        self.is_completed = True
        
        # Форматируем время выполнения
        if elapsed_time < 60:
            time_str = f"{elapsed_time:.1f} сек."
        else:
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            time_str = f"{minutes} мин. {seconds} сек."
        
        try:
            self.bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.message_id,
                text=f"✅ <b>{final_text}</b>\n\n⏱ Время выполнения: {time_str}",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Ошибка при завершении индикатора прогресса: {e}")
    
    def _get_progress_text(self, percent: int, status_text: str = "") -> str:
        """
        Формирует текст с индикатором прогресса.
        
        Args:
            percent: Процент выполнения (0-100)
            status_text: Дополнительный текст статуса
            
        Returns:
            Отформатированный текст с индикатором прогресса
        """
        # Определяем количество заполненных и пустых блоков
        total_blocks = 10
        filled_blocks = int(percent / 100 * total_blocks)
        empty_blocks = total_blocks - filled_blocks
        
        # Создаем индикатор прогресса
        progress_bar = "🟩" * filled_blocks + "⬜️" * empty_blocks
        
        # Форматируем текст индикатора
        text = f"<b>{self.operation_name}: {percent}%</b>\n\n{progress_bar}\n\n"
        
        # Добавляем дополнительный текст статуса, если есть
        if status_text:
            text += f"{status_text}\n\n"
        
        # Добавляем время выполнения
        if self.start_time:
            elapsed_time = time.time() - self.start_time
            if elapsed_time < 60:
                text += f"⏱ Выполняется: {elapsed_time:.1f} сек."
            else:
                minutes = int(elapsed_time // 60)
                seconds = int(elapsed_time % 60)
                text += f"⏱ Выполняется: {minutes} мин. {seconds} сек."
        
        return text


# Примеры использования

def create_tool_selection_buttons(tool_types: List[str]) -> InlineKeyboardMarkup:
    """
    Создает кнопки для выбора типа инструмента.
    
    Args:
        tool_types: Список типов инструментов
        
    Returns:
        Разметка с кнопками выбора типа инструмента
    """
    buttons = []
    for tool_type in tool_types:
        buttons.append({
            'text': tool_type.replace('_', ' ').capitalize(),
            'callback_data': f"select_tool_{tool_type}"
        })
    
    return InteractiveButtons.create_button_layout(buttons, row_width=2)

def create_brand_selection_buttons(brands: List[str]) -> InlineKeyboardMarkup:
    """
    Создает кнопки для выбора бренда инструмента.
    
    Args:
        brands: Список брендов
        
    Returns:
        Разметка с кнопками выбора бренда
    """
    buttons = []
    for brand in brands:
        buttons.append({
            'text': brand,
            'callback_data': f"select_brand_{brand}"
        })
    
    return InteractiveButtons.create_button_layout(buttons, row_width=2)

def create_quick_action_buttons() -> InlineKeyboardMarkup:
    """
    Создает кнопки быстрых действий для главного меню.
    
    Returns:
        Разметка с кнопками быстрых действий
    """
    actions = [
        {'text': '🔍 Поиск по фото', 'callback_data': 'quick_search_photo'},
        {'text': '📋 Каталог', 'callback_data': 'quick_catalog'},
        {'text': '🔧 Подобрать инструмент', 'callback_data': 'quick_tool_wizard'},
        {'text': '📊 Сравнение моделей', 'callback_data': 'quick_compare'},
        {'text': '💼 Заказы клиентов', 'callback_data': 'quick_orders'},
        {'text': '❓ Помощь', 'callback_data': 'quick_help'}
    ]
    
    return InteractiveButtons.create_quick_actions(actions) 