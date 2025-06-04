#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для управления пользовательским интерфейсом бота.
Координирует работу различных UI-компонентов и предоставляет единый интерфейс
для создания интерактивных элементов, мастеров и прогресс-индикаторов.
"""

import logging
import json
import os
from typing import List, Dict, Any, Optional, Callable, Union
from telebot import TeleBot
from telebot.types import Message, CallbackQuery

from toolbot.utils.ui_components import (
    InteractiveButtons, 
    StepByStepWizard, 
    ProgressIndicator,
    create_quick_action_buttons,
    create_tool_selection_buttons,
    create_brand_selection_buttons
)
from toolbot.utils.brand_recognition import get_known_brands
from toolbot.data.tool_categories import get_tool_categories

logger = logging.getLogger(__name__)

class UIManager:
    """
    Класс для управления пользовательским интерфейсом бота.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls, bot=None):
        """
        Получение экземпляра менеджера UI (синглтон).
        
        Args:
            bot: Экземпляр телеграм-бота (только при первом вызове)
            
        Returns:
            Экземпляр UIManager
        """
        if cls._instance is None:
            if bot is None:
                raise ValueError("При первой инициализации UIManager требуется экземпляр бота")
            cls._instance = cls(bot)
        return cls._instance
    
    def __init__(self, bot: TeleBot):
        """
        Инициализация менеджера UI.
        
        Args:
            bot: Экземпляр телеграм-бота
        """
        self.bot = bot
        self.active_wizards = {}  # Словарь активных мастеров по ID пользователя
        self.progress_indicators = {}  # Словарь индикаторов прогресса по ID чата
        
    def send_main_menu(self, chat_id: int, message_text: str = "Выберите действие:") -> None:
        """
        Отправляет главное меню с быстрыми действиями.
        
        Args:
            chat_id: ID чата для отправки меню
            message_text: Текст сообщения
        """
        markup = create_quick_action_buttons()
        self.bot.send_message(chat_id, message_text, reply_markup=markup, parse_mode='HTML')
    
    def send_tool_selection(self, chat_id: int, message_text: str = "Выберите тип инструмента:") -> None:
        """
        Отправляет меню выбора типа инструмента.
        
        Args:
            chat_id: ID чата для отправки меню
            message_text: Текст сообщения
        """
        tool_categories = get_tool_categories()
        markup = create_tool_selection_buttons(list(tool_categories.keys()))
        self.bot.send_message(chat_id, message_text, reply_markup=markup, parse_mode='HTML')
    
    def send_brand_selection(self, chat_id: int, message_text: str = "Выберите бренд:") -> None:
        """
        Отправляет меню выбора бренда инструмента.
        
        Args:
            chat_id: ID чата для отправки меню
            message_text: Текст сообщения
        """
        brands = get_known_brands()
        markup = create_brand_selection_buttons(brands)
        self.bot.send_message(chat_id, message_text, reply_markup=markup, parse_mode='HTML')
    
    def create_wizard(self, user_id: int, wizard_type: str, 
                     initial_message: str, on_complete: Callable = None) -> None:
        """
        Создает и запускает пошаговый мастер указанного типа.
        
        Args:
            user_id: ID пользователя
            wizard_type: Тип мастера ('tool_selection', 'order', 'comparison')
            initial_message: Начальное сообщение мастера
            on_complete: Функция, вызываемая при завершении мастера
        """
        steps = self._get_wizard_steps(wizard_type)
        if not steps:
            logger.error(f"Неизвестный тип мастера: {wizard_type}")
            return
        
        # Создаем мастер
        wizard = StepByStepWizard(
            bot=self.bot,
            steps=steps,
            user_id=user_id,
            initial_message_text=initial_message,
            on_complete=on_complete
        )
        
        # Сохраняем мастер в словаре активных мастеров
        self.active_wizards[user_id] = wizard
        
        # Запускаем мастер
        wizard.start()
    
    def _get_wizard_steps(self, wizard_type: str) -> List[Dict[str, Any]]:
        """
        Возвращает шаги для указанного типа мастера.
        
        Args:
            wizard_type: Тип мастера
            
        Returns:
            Список шагов мастера
        """
        if wizard_type == 'tool_selection':
            return self._get_tool_selection_wizard_steps()
        elif wizard_type == 'order':
            return self._get_order_wizard_steps()
        elif wizard_type == 'comparison':
            return self._get_comparison_wizard_steps()
        else:
            return []
    
    def _get_tool_selection_wizard_steps(self) -> List[Dict[str, Any]]:
        """
        Возвращает шаги для мастера подбора инструмента.
        
        Returns:
            Список шагов мастера
        """
        steps = [
            # Шаг 1: Выбор типа работ
            {
                'text': "Для каких работ вам нужен инструмент?",
                'buttons': [
                    {'text': '🏠 Бытовые работы', 'callback_data': 'wizard_work_home'},
                    {'text': '🔨 Профессиональные', 'callback_data': 'wizard_work_pro'},
                    {'text': '🏗️ Промышленные', 'callback_data': 'wizard_work_industrial'},
                    {'text': '🌳 Садовые работы', 'callback_data': 'wizard_work_garden'}
                ],
                'process_input': lambda query, data: data.update({'work_type': query.data.replace('wizard_work_', '')})
            },
            # Шаг 2: Выбор типа инструмента
            {
                'text': "Какой тип инструмента вас интересует?",
                'get_text': lambda data: self._get_tool_type_text(data),
                'buttons': [
                    {'text': '🔌 Электроинструмент', 'callback_data': 'wizard_tool_electric'},
                    {'text': '🔋 Аккумуляторный', 'callback_data': 'wizard_tool_cordless'},
                    {'text': '⚙️ Ручной инструмент', 'callback_data': 'wizard_tool_hand'},
                    {'text': '🔧 Измерительный', 'callback_data': 'wizard_tool_measuring'}
                ],
                'process_input': lambda query, data: data.update({'tool_type': query.data.replace('wizard_tool_', '')})
            },
            # Шаг 3: Выбор бренда
            {
                'text': "Предпочитаемый бренд инструмента:",
                'get_text': lambda data: self._get_brand_text(data),
                'buttons': [
                    {'text': 'Makita', 'callback_data': 'wizard_brand_Makita'},
                    {'text': 'Bosch', 'callback_data': 'wizard_brand_Bosch'},
                    {'text': 'DeWalt', 'callback_data': 'wizard_brand_DeWalt'},
                    {'text': 'Milwaukee', 'callback_data': 'wizard_brand_Milwaukee'},
                    {'text': 'Интерскол', 'callback_data': 'wizard_brand_Интерскол'},
                    {'text': 'Любой бренд', 'callback_data': 'wizard_brand_any'}
                ],
                'process_input': lambda query, data: data.update({'brand': query.data.replace('wizard_brand_', '')})
            },
            # Шаг 4: Выбор ценового диапазона
            {
                'text': "Выберите ценовой диапазон:",
                'get_text': lambda data: self._get_price_text(data),
                'buttons': [
                    {'text': '💰 Эконом (до 5000₽)', 'callback_data': 'wizard_price_low'},
                    {'text': '💰💰 Средний (5000-15000₽)', 'callback_data': 'wizard_price_medium'},
                    {'text': '💰💰💰 Премиум (от 15000₽)', 'callback_data': 'wizard_price_high'},
                    {'text': '🔄 Любая цена', 'callback_data': 'wizard_price_any'}
                ],
                'process_input': lambda query, data: data.update({'price_range': query.data.replace('wizard_price_', '')})
            },
            # Шаг 5: Подтверждение выбора
            {
                'text': "Проверьте выбранные параметры:",
                'get_text': lambda data: self._get_confirmation_text(data),
                'buttons': [
                    {'text': '✅ Всё верно', 'callback_data': 'wizard_confirm_yes'},
                    {'text': '🔄 Изменить параметры', 'callback_data': 'wizard_confirm_no'}
                ],
                'process_input': lambda query, data: data.update({'confirmed': query.data == 'wizard_confirm_yes'})
            }
        ]
        return steps
    
    def _get_order_wizard_steps(self) -> List[Dict[str, Any]]:
        """
        Возвращает шаги для мастера создания заказа.
        
        Returns:
            Список шагов мастера
        """
        # Здесь будут шаги для мастера создания заказа
        # Пример шагов для мастера заказа инструмента
        steps = [
            # Шаг 1: Выбор типа заказа
            {
                'text': "Выберите тип заказа:",
                'buttons': [
                    {'text': '🛒 Заказ товара', 'callback_data': 'wizard_order_product'},
                    {'text': '🔄 Обмен/возврат', 'callback_data': 'wizard_order_exchange'},
                    {'text': '🛠️ Сервисное обслуживание', 'callback_data': 'wizard_order_service'}
                ],
                'process_input': lambda query, data: data.update({'order_type': query.data.replace('wizard_order_', '')})
            },
            # Шаг 2: Информация о клиенте
            {
                'text': "Введите информацию о клиенте или выберите из существующих:",
                'get_text': lambda data: "Введите информацию о клиенте или выберите из существующих:",
                'buttons': [
                    {'text': '👤 Новый клиент', 'callback_data': 'wizard_client_new'},
                    {'text': '🔍 Поиск клиента по номеру', 'callback_data': 'wizard_client_search'}
                ],
                'process_input': lambda query, data: data.update({'client_action': query.data.replace('wizard_client_', '')})
            },
            # Шаг 3: Выбор инструментов
            {
                'text': "Выберите инструменты для заказа:",
                'get_text': lambda data: "Выберите инструменты для заказа:",
                'buttons': [
                    {'text': '🔎 Поиск по каталогу', 'callback_data': 'wizard_add_catalog'},
                    {'text': '📷 Поиск по фото', 'callback_data': 'wizard_add_photo'},
                    {'text': '📋 Ввод по артикулу', 'callback_data': 'wizard_add_article'}
                ],
                'process_input': lambda query, data: data.update({'add_method': query.data.replace('wizard_add_', '')})
            },
            # Шаг 4: Выбор способа оплаты
            {
                'text': "Выберите способ оплаты:",
                'get_text': lambda data: "Выберите способ оплаты:",
                'buttons': [
                    {'text': '💵 Наличными', 'callback_data': 'wizard_payment_cash'},
                    {'text': '💳 Картой', 'callback_data': 'wizard_payment_card'},
                    {'text': '🏦 Банковский перевод', 'callback_data': 'wizard_payment_transfer'},
                    {'text': '📃 Счет юр. лицу', 'callback_data': 'wizard_payment_invoice'}
                ],
                'process_input': lambda query, data: data.update({'payment_method': query.data.replace('wizard_payment_', '')})
            },
            # Шаг 5: Подтверждение заказа
            {
                'text': "Проверьте данные заказа:",
                'get_text': lambda data: self._get_order_confirmation_text(data),
                'buttons': [
                    {'text': '✅ Подтвердить заказ', 'callback_data': 'wizard_order_confirm'},
                    {'text': '🔄 Изменить детали', 'callback_data': 'wizard_order_edit'}
                ],
                'process_input': lambda query, data: data.update({'order_confirmed': query.data == 'wizard_order_confirm'})
            }
        ]
        return steps
    
    def _get_comparison_wizard_steps(self) -> List[Dict[str, Any]]:
        """
        Возвращает шаги для мастера сравнения инструментов.
        
        Returns:
            Список шагов мастера
        """
        # Здесь будут шаги для мастера сравнения инструментов
        steps = [
            # Шаг 1: Выбор категории инструментов для сравнения
            {
                'text': "Выберите категорию инструментов для сравнения:",
                'buttons': [
                    {'text': '🔌 Дрели', 'callback_data': 'wizard_compare_drills'},
                    {'text': '🔌 Перфораторы', 'callback_data': 'wizard_compare_hammers'},
                    {'text': '🔌 Шуруповерты', 'callback_data': 'wizard_compare_screwdrivers'},
                    {'text': '🔌 Болгарки', 'callback_data': 'wizard_compare_grinders'},
                    {'text': '🔌 Пилы', 'callback_data': 'wizard_compare_saws'}
                ],
                'process_input': lambda query, data: data.update({'compare_category': query.data.replace('wizard_compare_', '')})
            },
            # Шаг 2: Выбор первого инструмента
            {
                'text': "Выберите первый инструмент для сравнения:",
                'get_text': lambda data: f"Выберите первый инструмент для сравнения из категории {data.get('compare_category', 'инструменты')}:",
                'buttons': [
                    {'text': '🔍 Поиск по названию', 'callback_data': 'wizard_first_search'},
                    {'text': '📷 Выбор по фото', 'callback_data': 'wizard_first_photo'},
                    {'text': '📋 Выбор из каталога', 'callback_data': 'wizard_first_catalog'}
                ],
                'process_input': lambda query, data: data.update({'first_tool_method': query.data.replace('wizard_first_', '')})
            },
            # Шаг 3: Выбор второго инструмента
            {
                'text': "Выберите второй инструмент для сравнения:",
                'get_text': lambda data: f"Выберите второй инструмент для сравнения из категории {data.get('compare_category', 'инструменты')}:",
                'buttons': [
                    {'text': '🔍 Поиск по названию', 'callback_data': 'wizard_second_search'},
                    {'text': '📷 Выбор по фото', 'callback_data': 'wizard_second_photo'},
                    {'text': '📋 Выбор из каталога', 'callback_data': 'wizard_second_catalog'}
                ],
                'process_input': lambda query, data: data.update({'second_tool_method': query.data.replace('wizard_second_', '')})
            },
            # Шаг 4: Параметры сравнения
            {
                'text': "Выберите параметры для сравнения:",
                'get_text': lambda data: "Выберите параметры для сравнения инструментов:",
                'buttons': [
                    {'text': '⚡ Мощность', 'callback_data': 'wizard_param_power'},
                    {'text': '⚙️ Функционал', 'callback_data': 'wizard_param_features'},
                    {'text': '💰 Цена', 'callback_data': 'wizard_param_price'},
                    {'text': '🔋 Аккумулятор', 'callback_data': 'wizard_param_battery'},
                    {'text': '🔄 Все параметры', 'callback_data': 'wizard_param_all'}
                ],
                'process_input': lambda query, data: self._process_comparison_params(query, data)
            },
            # Шаг 5: Формат сравнения
            {
                'text': "Выберите формат сравнения:",
                'get_text': lambda data: "Выберите формат сравнения инструментов:",
                'buttons': [
                    {'text': '📊 Таблица', 'callback_data': 'wizard_format_table'},
                    {'text': '📝 Текстовый отчет', 'callback_data': 'wizard_format_text'},
                    {'text': '📊 Графики', 'callback_data': 'wizard_format_charts'}
                ],
                'process_input': lambda query, data: data.update({'comparison_format': query.data.replace('wizard_format_', '')})
            }
        ]
        return steps
    
    def _process_comparison_params(self, query: CallbackQuery, data: Dict[str, Any]) -> None:
        """
        Обрабатывает выбор параметров для сравнения.
        
        Args:
            query: Объект callback запроса
            data: Словарь данных мастера
        """
        param = query.data.replace('wizard_param_', '')
        
        if 'comparison_params' not in data:
            data['comparison_params'] = []
        
        if param == 'all':
            data['comparison_params'] = ['power', 'features', 'price', 'battery']
        else:
            if param not in data['comparison_params']:
                data['comparison_params'].append(param)
    
    def _get_tool_type_text(self, data: Dict[str, Any]) -> str:
        """
        Формирует текст для шага выбора типа инструмента.
        
        Args:
            data: Словарь данных мастера
            
        Returns:
            Текст для шага выбора типа инструмента
        """
        work_type = data.get('work_type', '')
        
        intro_text = "Какой тип инструмента вас интересует?"
        
        if work_type == 'home':
            return f"{intro_text}\n\nДля бытовых работ рекомендуются инструменты средней мощности и надежности, подходящие для периодического использования."
        elif work_type == 'pro':
            return f"{intro_text}\n\nДля профессиональных работ рекомендуются надежные инструменты повышенной мощности с длительным сроком службы."
        elif work_type == 'industrial':
            return f"{intro_text}\n\nДля промышленных работ рекомендуются инструменты промышленного класса с максимальной производительностью и ресурсом."
        elif work_type == 'garden':
            return f"{intro_text}\n\nДля садовых работ рекомендуются специализированные садовые инструменты с защитой от влаги и загрязнений."
        else:
            return intro_text
    
    def _get_brand_text(self, data: Dict[str, Any]) -> str:
        """
        Формирует текст для шага выбора бренда.
        
        Args:
            data: Словарь данных мастера
            
        Returns:
            Текст для шага выбора бренда
        """
        tool_type = data.get('tool_type', '')
        work_type = data.get('work_type', '')
        
        base_text = "Предпочитаемый бренд инструмента:"
        
        brand_recommendations = {
            'electric': {
                'home': ["Bosch (зеленая линия)", "Интерскол", "Makita"],
                'pro': ["Bosch (синяя линия)", "Makita", "DeWalt", "Milwaukee"],
                'industrial': ["Hilti", "Milwaukee", "Metabo", "Makita"],
                'garden': ["Bosch", "Makita", "Stihl", "Patriot"]
            },
            'cordless': {
                'home': ["Bosch (зеленая линия)", "Makita", "AEG"],
                'pro': ["Makita", "DeWalt", "Milwaukee", "Bosch (синяя линия)"],
                'industrial': ["Milwaukee", "DeWalt", "Hilti"],
                'garden': ["Bosch", "Ryobi", "Makita"]
            },
            'hand': {
                'home': ["Зубр", "Stayer", "Kraftool"],
                'pro': ["Stanley", "Зубр Pro", "Knipex"],
                'industrial': ["Knipex", "Gedore", "Stanley"],
                'garden': ["Fiskars", "Gardena", "Зубр"]
            },
            'measuring': {
                'home': ["Bosch", "ADA", "Зубр"],
                'pro': ["Bosch", "ADA", "Leica", "CONDTROL"],
                'industrial': ["Leica", "Hilti", "CONDTROL"],
                'garden': ["ADA", "Bosch", "CONDTROL"]
            }
        }
        
        if tool_type in brand_recommendations and work_type in brand_recommendations[tool_type]:
            recommendations = brand_recommendations[tool_type][work_type]
            recommendation_text = ", ".join(recommendations)
            return f"{base_text}\n\nДля выбранного типа работ и инструмента рекомендуем: {recommendation_text}"
        
        return base_text
    
    def _get_price_text(self, data: Dict[str, Any]) -> str:
        """
        Формирует текст для шага выбора ценового диапазона.
        
        Args:
            data: Словарь данных мастера
            
        Returns:
            Текст для шага выбора ценового диапазона
        """
        tool_type = data.get('tool_type', '')
        brand = data.get('brand', '')
        
        base_text = "Выберите ценовой диапазон:"
        
        price_recommendations = {
            'electric': {
                'Makita': "medium",
                'Bosch': "medium",
                'DeWalt': "high",
                'Milwaukee': "high",
                'Интерскол': "low"
            },
            'cordless': {
                'Makita': "high",
                'Bosch': "medium",
                'DeWalt': "high",
                'Milwaukee': "high",
                'Интерскол': "medium"
            }
        }
        
        if tool_type in price_recommendations and brand in price_recommendations[tool_type]:
            recommended_range = price_recommendations[tool_type][brand]
            
            range_texts = {
                'low': "эконом (до 5000₽)",
                'medium': "средний (5000-15000₽)",
                'high': "премиум (от 15000₽)"
            }
            
            recommendation = range_texts.get(recommended_range, "")
            
            if recommendation:
                return f"{base_text}\n\nДля бренда {brand} в категории {tool_type} рекомендуемый ценовой диапазон: {recommendation}"
        
        return base_text
    
    def _get_confirmation_text(self, data: Dict[str, Any]) -> str:
        """
        Формирует текст для шага подтверждения выбора.
        
        Args:
            data: Словарь данных мастера
            
        Returns:
            Текст для шага подтверждения выбора
        """
        # Получаем данные из мастера
        work_type_map = {
            'home': 'Бытовые работы',
            'pro': 'Профессиональные работы',
            'industrial': 'Промышленные работы',
            'garden': 'Садовые работы'
        }
        
        tool_type_map = {
            'electric': 'Электроинструмент',
            'cordless': 'Аккумуляторный инструмент',
            'hand': 'Ручной инструмент',
            'measuring': 'Измерительный инструмент'
        }
        
        price_range_map = {
            'low': 'Эконом (до 5000₽)',
            'medium': 'Средний (5000-15000₽)',
            'high': 'Премиум (от 15000₽)',
            'any': 'Любая цена'
        }
        
        work_type = work_type_map.get(data.get('work_type', ''), 'Не указано')
        tool_type = tool_type_map.get(data.get('tool_type', ''), 'Не указано')
        brand = data.get('brand', 'Любой')
        price_range = price_range_map.get(data.get('price_range', ''), 'Не указано')
        
        # Формируем текст
        text = (
            "Проверьте выбранные параметры:\n\n"
            f"🏠 <b>Тип работ:</b> {work_type}\n"
            f"🔨 <b>Тип инструмента:</b> {tool_type}\n"
            f"🏭 <b>Бренд:</b> {brand}\n"
            f"💰 <b>Ценовой диапазон:</b> {price_range}\n\n"
            "Всё верно? Если нет, нажмите 'Изменить параметры'."
        )
        
        return text
    
    def _get_order_confirmation_text(self, data: Dict[str, Any]) -> str:
        """
        Формирует текст для шага подтверждения заказа.
        
        Args:
            data: Словарь данных мастера заказа
            
        Returns:
            Текст для шага подтверждения заказа
        """
        order_type_map = {
            'product': 'Заказ товара',
            'exchange': 'Обмен/возврат',
            'service': 'Сервисное обслуживание'
        }
        
        payment_method_map = {
            'cash': 'Наличными',
            'card': 'Картой',
            'transfer': 'Банковский перевод',
            'invoice': 'Счет юр. лицу'
        }
        
        order_type = order_type_map.get(data.get('order_type', ''), 'Не указано')
        client_action = data.get('client_action', 'Не указано')
        payment_method = payment_method_map.get(data.get('payment_method', ''), 'Не указано')
        
        # Формируем текст
        text = (
            "Проверьте данные заказа:\n\n"
            f"📝 <b>Тип заказа:</b> {order_type}\n"
            f"👤 <b>Клиент:</b> {client_action}\n"
            f"💳 <b>Способ оплаты:</b> {payment_method}\n\n"
            "Всё верно? Если нет, нажмите 'Изменить детали'."
        )
        
        return text
    
    def process_callback(self, callback_query: CallbackQuery) -> bool:
        """
        Обрабатывает callback-запросы для UI-компонентов.
        
        Args:
            callback_query: Объект callback-запроса
            
        Returns:
            True, если запрос был обработан, иначе False
        """
        # Проверяем, есть ли активный мастер для этого пользователя
        user_id = callback_query.from_user.id
        callback_data = callback_query.data
        
        # Обработка callback для быстрых действий
        if callback_data.startswith('quick_'):
            self._process_quick_action(callback_query)
            return True
        
        # Проверяем, есть ли активный мастер
        if user_id in self.active_wizards:
            # Передаем callback в мастер
            self.active_wizards[user_id].process_step_input(callback_query)
            
            # Если в callback есть "wizard_complete", то удаляем мастер
            if f"wizard_complete_{id(self.active_wizards[user_id])}" in callback_data or \
               f"wizard_cancel_{id(self.active_wizards[user_id])}" in callback_data:
                del self.active_wizards[user_id]
            
            return True
        
        return False
    
    def _process_quick_action(self, callback_query: CallbackQuery) -> None:
        """
        Обрабатывает callback для быстрых действий.
        
        Args:
            callback_query: Объект callback-запроса
        """
        user_id = callback_query.from_user.id
        callback_data = callback_query.data
        
        # Удаляем префикс 'quick_'
        action = callback_data.replace('quick_', '')
        
        # Обрабатываем разные действия
        if action == 'search_photo':
            self.bot.answer_callback_query(
                callback_query.id,
                "Отправьте фото инструмента для поиска",
                show_alert=True
            )
        elif action == 'catalog':
            # Отправляем меню каталога
            self.send_tool_selection(user_id, "Каталог инструментов. Выберите категорию:")
        elif action == 'tool_wizard':
            # Запускаем мастер подбора инструмента
            self.create_wizard(
                user_id,
                'tool_selection',
                "🧙‍♂️ <b>Мастер подбора инструмента</b>\n\nЯ помогу вам выбрать подходящий инструмент для ваших задач. Давайте начнем с определения типа работ."
            )
        elif action == 'compare':
            # Запускаем мастер сравнения
            self.create_wizard(
                user_id,
                'comparison',
                "📊 <b>Мастер сравнения инструментов</b>\n\nЯ помогу вам сравнить характеристики разных инструментов. Давайте выберем категорию для сравнения."
            )
        elif action == 'orders':
            # Запускаем мастер заказов
            self.create_wizard(
                user_id,
                'order',
                "💼 <b>Управление заказами клиентов</b>\n\nЯ помогу вам создать новый заказ или найти существующий. Выберите тип операции."
            )
        elif action == 'help':
            # Отправляем справку
            help_text = (
                "🔍 <b>Справка по использованию бота</b>\n\n"
                "• Для поиска инструмента по фото используйте команду /search или кнопку 'Поиск по фото'\n"
                "• Для выбора инструмента с помощью мастера используйте команду /wizard или кнопку 'Подобрать инструмент'\n"
                "• Для просмотра каталога используйте команду /catalog или кнопку 'Каталог'\n"
                "• Для сравнения инструментов используйте команду /compare или кнопку 'Сравнение моделей'\n"
                "• Для работы с заказами используйте команду /orders или кнопку 'Заказы клиентов'\n\n"
                "При возникновении проблем обратитесь к администратору."
            )
            self.bot.send_message(user_id, help_text, parse_mode='HTML')
    
    def start_progress(self, chat_id: int, operation_name: str = "Операция") -> ProgressIndicator:
        """
        Создает и запускает индикатор прогресса.
        
        Args:
            chat_id: ID чата
            operation_name: Название операции
            
        Returns:
            Созданный индикатор прогресса
        """
        # Создаем индикатор прогресса
        indicator = ProgressIndicator(self.bot, chat_id, operation_name)
        
        # Сохраняем в словаре
        self.progress_indicators[chat_id] = indicator
        
        # Запускаем индикатор
        indicator.start()
        
        return indicator
    
    def update_progress(self, chat_id: int, percent: int, status_text: str = "") -> None:
        """
        Обновляет индикатор прогресса.
        
        Args:
            chat_id: ID чата
            percent: Процент выполнения (0-100)
            status_text: Дополнительный текст статуса
        """
        if chat_id in self.progress_indicators:
            self.progress_indicators[chat_id].update(percent, status_text)
    
    def complete_progress(self, chat_id: int, final_text: str = "Операция завершена") -> None:
        """
        Завершает индикатор прогресса.
        
        Args:
            chat_id: ID чата
            final_text: Текст завершения
        """
        if chat_id in self.progress_indicators:
            self.progress_indicators[chat_id].complete(final_text)
            del self.progress_indicators[chat_id]


# Функция для получения экземпляра менеджера UI
def get_ui_manager(bot=None):
    """
    Получение экземпляра менеджера UI.
    
    Args:
        bot: Экземпляр телеграм-бота (только при первом вызове)
        
    Returns:
        Экземпляр UIManager
    """
    return UIManager.get_instance(bot) 