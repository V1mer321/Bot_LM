#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль с обработчиками для компонентов пользовательского интерфейса.
Содержит функции-обработчики для кнопок, мастеров и индикаторов прогресса.
"""

import logging
import time
import os
from typing import Dict, Any, List, Optional, Callable, Union

from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup

from toolbot.services.ui_manager import get_ui_manager
from toolbot.utils.brand_recognition import get_known_brands
from toolbot.data.tool_categories import get_tool_categories, get_categories_list
from toolbot.services.image_search import enhanced_image_search

logger = logging.getLogger(__name__)


def register_ui_handlers(bot: TeleBot):
    """
    Регистрирует обработчики для компонентов пользовательского интерфейса.
    
    Args:
        bot: Экземпляр Telegram бота
    """
    # Инициализируем менеджер UI
    ui_manager = get_ui_manager(bot)
    
    # Обработчик для команды /menu
    @bot.message_handler(commands=["menu"])
    def handle_menu_command(message: Message):
        """
        Обработчик команды /menu, отправляет главное меню с быстрыми действиями.
        
        Args:
            message: Объект сообщения
        """
        ui_manager.send_main_menu(message.chat.id, "Главное меню бота B2B Лемана про:")
    
    # Обработчик для команды /catalog
    @bot.message_handler(commands=["catalog"])
    def handle_catalog_command(message: Message):
        """
        Обработчик команды /catalog, отправляет меню выбора категории инструмента.
        
        Args:
            message: Объект сообщения
        """
        ui_manager.send_tool_selection(message.chat.id, "Каталог инструментов. Выберите категорию:")
    
    # Обработчик для команды /brands
    @bot.message_handler(commands=["brands"])
    def handle_brands_command(message: Message):
        """
        Обработчик команды /brands, отправляет меню выбора бренда.
        
        Args:
            message: Объект сообщения
        """
        ui_manager.send_brand_selection(message.chat.id, "Выберите бренд инструмента:")
    
    # Обработчик для команды /wizard
    @bot.message_handler(commands=["wizard"])
    def handle_wizard_command(message: Message):
        """
        Обработчик команды /wizard, запускает мастер подбора инструмента.
        
        Args:
            message: Объект сообщения
        """
        ui_manager.create_wizard(
            message.chat.id,
            'tool_selection',
            "🧙‍♂️ <b>Мастер подбора инструмента</b>\n\nЯ помогу вам выбрать подходящий инструмент для ваших задач. Давайте начнем с определения типа работ.",
            on_complete=lambda data: handle_wizard_complete(message.chat.id, data)
        )
    
    # Обработчик для команды /compare
    @bot.message_handler(commands=["compare"])
    def handle_compare_command(message: Message):
        """
        Обработчик команды /compare, запускает мастер сравнения инструментов.
        
        Args:
            message: Объект сообщения
        """
        ui_manager.create_wizard(
            message.chat.id,
            'comparison',
            "📊 <b>Мастер сравнения инструментов</b>\n\nЯ помогу вам сравнить характеристики разных инструментов. Давайте выберем категорию для сравнения.",
            on_complete=lambda data: handle_comparison_complete(message.chat.id, data)
        )
    
    # Обработчик для команды /orders
    @bot.message_handler(commands=["orders"])
    def handle_orders_command(message: Message):
        """
        Обработчик команды /orders, запускает мастер управления заказами.
        
        Args:
            message: Объект сообщения
        """
        ui_manager.create_wizard(
            message.chat.id,
            'order',
            "💼 <b>Управление заказами клиентов</b>\n\nЯ помогу вам создать новый заказ или найти существующий. Выберите тип операции.",
            on_complete=lambda data: handle_order_complete(message.chat.id, data)
        )
    
    # Обработчик для запроса фото (поиск инструмента по фото)
    @bot.message_handler(content_types=["photo"])
    def handle_photo_message(message: Message):
        """
        Обработчик сообщений с фото, выполняет поиск похожих инструментов.
        
        Args:
            message: Объект сообщения
        """
        # Получаем файл
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Создаем временный файл
        file_name = f"temp_{message.chat.id}_{int(time.time())}.jpg"
        file_path = os.path.join(os.path.dirname(__file__), "..", "temp", file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Сохраняем файл
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        # Отправляем сообщение о начале поиска
        bot.send_message(message.chat.id, "🔍 <b>Начинаю поиск похожих инструментов...</b>", parse_mode='HTML')
        
        # Запускаем индикатор прогресса
        progress = ui_manager.start_progress(message.chat.id, "Поиск инструментов")
        
        try:
            # Обновляем прогресс
            ui_manager.update_progress(message.chat.id, 20, "Анализ изображения...")
            
            # Выполняем поиск похожих инструментов (имитация длительной операции)
            time.sleep(1)  # Задержка для демонстрации прогресса
            ui_manager.update_progress(message.chat.id, 40, "Извлечение признаков...")
            
            time.sleep(1)  # Задержка для демонстрации прогресса
            ui_manager.update_progress(message.chat.id, 60, "Поиск в базе данных...")
            
            # Выполняем реальный поиск
            results = enhanced_image_search(file_path, top_n=5)
            
            time.sleep(1)  # Задержка для демонстрации прогресса
            ui_manager.update_progress(message.chat.id, 80, "Форматирование результатов...")
            
            # Завершаем индикатор прогресса
            ui_manager.complete_progress(message.chat.id, "Поиск завершен")
            
            # Отправляем результаты
            if results:
                bot.send_message(message.chat.id, 
                                "<b>Результаты поиска:</b>\n\nНайдены похожие инструменты. Вот наиболее подходящие варианты:", 
                                parse_mode='HTML')
                
                # Отправляем каждый результат
                for i, (img_path, similarity) in enumerate(results, 1):
                    # Получаем имя файла для отображения
                    file_name = os.path.basename(img_path)
                    
                    # Форматируем схожесть в проценты
                    similarity_percent = round(similarity * 100)
                    
                    # Отправляем изображение с подписью
                    with open(img_path, 'rb') as img_file:
                        bot.send_photo(
                            message.chat.id,
                            img_file,
                            caption=f"<b>Вариант {i}</b>\nСхожесть: {similarity_percent}%\nФайл: {file_name}",
                            parse_mode='HTML'
                        )
                
                # Отправляем сообщение с действиями после поиска
                quick_actions = [
                    {'text': '🔍 Новый поиск', 'callback_data': 'quick_search_photo'},
                    {'text': '📋 В каталог', 'callback_data': 'quick_catalog'},
                    {'text': '🧙‍♂️ Мастер подбора', 'callback_data': 'quick_tool_wizard'}
                ]
                markup = create_post_search_markup(quick_actions)
                bot.send_message(
                    message.chat.id,
                    "Выберите дальнейшее действие:",
                    reply_markup=markup
                )
            else:
                bot.send_message(message.chat.id, 
                                "😔 <b>Не найдено похожих инструментов</b>\n\nПопробуйте другое изображение или уточните запрос.", 
                                parse_mode='HTML')
        except Exception as e:
            logger.error(f"Ошибка при поиске: {e}")
            ui_manager.complete_progress(message.chat.id, "Поиск прерван из-за ошибки")
            bot.send_message(message.chat.id, 
                            "❌ <b>Произошла ошибка при поиске</b>\n\nПожалуйста, попробуйте еще раз позже.", 
                            parse_mode='HTML')
        finally:
            # Удаляем временный файл
            try:
                os.remove(file_path)
            except:
                pass
    
    # Обработчик для всех callback-запросов от кнопок
    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call: CallbackQuery):
        """
        Обработчик всех callback-запросов от кнопок.
        
        Args:
            call: Объект callback-запроса
        """
        # Пытаемся обработать запрос с помощью UI менеджера
        if ui_manager.process_callback(call):
            # Если запрос был обработан UI менеджером, отвечаем на callback
            bot.answer_callback_query(call.id)
            return
        
        # Обработка callback для выбора категории инструмента
        if call.data.startswith("select_tool_"):
            tool_type = call.data.replace("select_tool_", "")
            categories = get_tool_categories()
            tool_description = categories.get(tool_type, "Инструмент")
            
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                f"<b>{tool_type.replace('_', ' ').capitalize()}</b>\n\n{tool_description}",
                parse_mode='HTML'
            )
            return
        
        # Обработка callback для выбора бренда
        if call.data.startswith("select_brand_"):
            brand = call.data.replace("select_brand_", "")
            
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                f"<b>Выбран бренд: {brand}</b>\n\nВы можете просмотреть инструменты этого бренда в каталоге или начать подбор через мастер.",
                parse_mode='HTML'
            )
            return
        
        # Если callback не был обработан, просто отвечаем на него
        bot.answer_callback_query(call.id)


def handle_wizard_complete(chat_id: int, data: Dict[str, Any]):
    """
    Обработчик завершения мастера подбора инструмента.
    
    Args:
        chat_id: ID чата
        data: Данные, собранные мастером
    """
    ui_manager = get_ui_manager()
    
    # Проверяем, был ли мастер завершен успешно
    if data.get('confirmed', False):
        # Имитация поиска подходящих инструментов
        ui_manager.bot.send_message(
            chat_id,
            "🔍 <b>Выполняю подбор инструментов по заданным параметрам...</b>",
            parse_mode='HTML'
        )
        
        # Запускаем индикатор прогресса
        progress = ui_manager.start_progress(chat_id, "Подбор инструментов")
        
        try:
            # Имитация длительной операции с обновлением прогресса
            ui_manager.update_progress(chat_id, 25, "Анализ параметров...")
            time.sleep(1)
            
            ui_manager.update_progress(chat_id, 50, "Поиск в базе данных...")
            time.sleep(1)
            
            ui_manager.update_progress(chat_id, 75, "Формирование результатов...")
            time.sleep(1)
            
            # Завершаем индикатор прогресса
            ui_manager.complete_progress(chat_id, "Подбор завершен")
            
            # Отправляем результаты
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
            
            # Получаем параметры из данных мастера
            work_type = work_type_map.get(data.get('work_type', ''), 'Не указано')
            tool_type = tool_type_map.get(data.get('tool_type', ''), 'Не указано')
            brand = data.get('brand', 'Любой')
            price_range = data.get('price_range', '')
            
            # Формируем сообщение с результатами
            message_text = (
                "✅ <b>Результаты подбора инструмента</b>\n\n"
                f"На основе выбранных параметров:\n"
                f"• Тип работ: {work_type}\n"
                f"• Тип инструмента: {tool_type}\n"
                f"• Бренд: {brand}\n\n"
                f"Мы подобрали для вас следующие варианты:"
            )
            
            ui_manager.bot.send_message(chat_id, message_text, parse_mode='HTML')
            
            # Имитация отправки нескольких вариантов инструментов
            # В реальном приложении здесь будет запрос к базе данных и отправка результатов
            for i in range(1, 4):
                ui_manager.bot.send_message(
                    chat_id,
                    f"<b>Вариант {i}</b>\n\n"
                    f"• Модель: {brand} XR-{1000+i*100}\n"
                    f"• Тип: {tool_type}\n"
                    f"• Цена: {5000 + i*3000} ₽\n"
                    f"• Рейтинг: {'⭐' * (i+2)}\n",
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"Ошибка при подборе инструмента: {e}")
            ui_manager.complete_progress(chat_id, "Подбор прерван из-за ошибки")
            ui_manager.bot.send_message(
                chat_id,
                "❌ <b>Произошла ошибка при подборе инструмента</b>\n\nПожалуйста, попробуйте еще раз позже.",
                parse_mode='HTML'
            )


def handle_comparison_complete(chat_id: int, data: Dict[str, Any]):
    """
    Обработчик завершения мастера сравнения инструментов.
    
    Args:
        chat_id: ID чата
        data: Данные, собранные мастером
    """
    ui_manager = get_ui_manager()
    
    # Проверяем параметры сравнения
    category = data.get('compare_category', '')
    comparison_format = data.get('comparison_format', 'table')
    
    message_text = (
        "📊 <b>Результаты сравнения инструментов</b>\n\n"
        f"Категория: {category}\n"
        f"Формат сравнения: {comparison_format}\n\n"
    )
    
    ui_manager.bot.send_message(chat_id, message_text, parse_mode='HTML')
    
    # Имитация отправки результатов сравнения
    # В реальном приложении здесь будет запрос к базе данных и форматирование результатов
    if comparison_format == 'table':
        # Имитация таблицы в текстовом формате
        table = (
            "<b>Таблица сравнения</b>\n\n"
            "<pre>+------------+---------+---------+\n"
            "| Параметр   | Модель1 | Модель2 |\n"
            "+------------+---------+---------+\n"
            "| Мощность   | 800 Вт  | 1200 Вт |\n"
            "| Вес        | 2.5 кг  | 3.2 кг  |\n"
            "| Батарея    | 2.0 Ач  | 4.0 Ач  |\n"
            "| Цена       | 8000 ₽  | 12000 ₽ |\n"
            "+------------+---------+---------+</pre>"
        )
        ui_manager.bot.send_message(chat_id, table, parse_mode='HTML')
    elif comparison_format == 'text':
        # Имитация текстового сравнения
        text = (
            "<b>Текстовое сравнение</b>\n\n"
            "📱 <b>Модель 1</b>\n"
            "• Мощность: 800 Вт\n"
            "• Вес: 2.5 кг\n"
            "• Батарея: 2.0 Ач\n"
            "• Цена: 8000 ₽\n\n"
            "📲 <b>Модель 2</b>\n"
            "• Мощность: 1200 Вт\n"
            "• Вес: 3.2 кг\n"
            "• Батарея: 4.0 Ач\n"
            "• Цена: 12000 ₽\n\n"
            "🏆 <b>Вывод:</b> Модель 2 мощнее, но тяжелее и дороже. Модель 1 легче и доступнее."
        )
        ui_manager.bot.send_message(chat_id, text, parse_mode='HTML')
    else:
        # Имитация сравнения в виде графиков
        ui_manager.bot.send_message(
            chat_id,
            "📊 <b>Графики сравнения</b>\n\n"
            "К сожалению, в текстовом интерфейсе невозможно отобразить графики. "
            "В реальном приложении здесь были бы графики сравнения параметров моделей.",
            parse_mode='HTML'
        )


def handle_order_complete(chat_id: int, data: Dict[str, Any]):
    """
    Обработчик завершения мастера создания заказа.
    
    Args:
        chat_id: ID чата
        data: Данные, собранные мастером
    """
    ui_manager = get_ui_manager()
    
    # Проверяем, подтвержден ли заказ
    if data.get('order_confirmed', False):
        # Имитация создания заказа
        order_id = int(time.time())
        
        # Формируем сообщение с результатами
        message_text = (
            "✅ <b>Заказ успешно создан</b>\n\n"
            f"Номер заказа: <code>{order_id}</code>\n"
            f"Тип заказа: {data.get('order_type', '')}\n"
            f"Способ оплаты: {data.get('payment_method', '')}\n\n"
            f"Статус заказа можно отслеживать в личном кабинете или в разделе 'Заказы'."
        )
        
        ui_manager.bot.send_message(chat_id, message_text, parse_mode='HTML')
    else:
        ui_manager.bot.send_message(
            chat_id,
            "❌ <b>Заказ не был подтвержден</b>\n\n"
            "Вы можете создать заказ позже, выбрав соответствующий пункт в меню.",
            parse_mode='HTML'
        )


def create_post_search_markup(actions: List[Dict[str, str]]) -> InlineKeyboardMarkup:
    """
    Создает разметку с кнопками для действий после поиска.
    
    Args:
        actions: Список словарей с параметрами кнопок действий
        
    Returns:
        Разметка с кнопками действий
    """
    from toolbot.utils.ui_components import InteractiveButtons
    return InteractiveButtons.create_button_layout(actions, row_width=2) 