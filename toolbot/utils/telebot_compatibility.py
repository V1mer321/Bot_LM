#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для обеспечения совместимости между python-telegram-bot и pyTelegramBotAPI (telebot).
Предоставляет альтернативные классы и функции для совместного использования обеих библиотек.
"""

import logging
import inspect
from typing import Callable, Any, Dict, List, Union, Optional
from telegram import Update, Bot as PTBBot
from telegram.ext import Application, CallbackContext
from telegram.helpers import escape_markdown
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

# Эмуляция класса TeleBot из pyTelegramBotAPI для python-telegram-bot
class TeleBot:
    """
    Класс-адаптер, эмулирующий TeleBot из pyTelegramBotAPI.
    Обеспечивает совместимость с интерфейсом telebot при использовании python-telegram-bot.
    """
    
    def __init__(self, token: str, application: Application = None, bot: PTBBot = None):
        """
        Инициализация адаптера TeleBot.
        
        Args:
            token: Токен Telegram бота
            application: Экземпляр Application из python-telegram-bot (опционально)
            bot: Экземпляр Bot из python-telegram-bot (опционально)
        """
        self.token = token
        self.application = application
        self.bot = bot or (application.bot if application else None)
        self.message_handlers = []
        self.callback_query_handlers = []
        
    async def _async_send_message(self, chat_id: int, text: str, **kwargs) -> Message:
        """
        Асинхронно отправляет сообщение.
        
        Args:
            chat_id: ID чата
            text: Текст сообщения
            **kwargs: Дополнительные аргументы
            
        Returns:
            Объект сообщения
        """
        parse_mode = kwargs.get('parse_mode', None)
        reply_markup = kwargs.get('reply_markup', None)
        
        # Конвертировать разметку клавиатуры из telebot в python-telegram-bot
        ptb_markup = None
        if reply_markup:
            ptb_markup = self._convert_markup_to_ptb(reply_markup)
        
        msg = await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=ptb_markup
        )
        return self._convert_message_to_telebot(msg)
    
    def send_message(self, chat_id: int, text: str, **kwargs) -> Message:
        """
        Отправляет сообщение пользователю.
        
        Args:
            chat_id: ID чата
            text: Текст сообщения
            **kwargs: Дополнительные аргументы
            
        Returns:
            Объект сообщения
        """
        parse_mode = kwargs.get('parse_mode', None)
        reply_markup = kwargs.get('reply_markup', None)
        
        # Конвертировать разметку клавиатуры из telebot в python-telegram-bot
        ptb_markup = None
        if reply_markup:
            ptb_markup = self._convert_markup_to_ptb(reply_markup)
        
        # Используем sync_send из Application или запускаем корутину
        if self.application:
            msg = self.application.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=ptb_markup
            )
            return self._convert_message_to_telebot(msg)
        else:
            import asyncio
            loop = asyncio.get_event_loop()
            msg = loop.run_until_complete(self._async_send_message(chat_id, text, **kwargs))
            return msg
    
    def send_photo(self, chat_id: int, photo, **kwargs) -> Message:
        """
        Отправляет фото пользователю.
        
        Args:
            chat_id: ID чата
            photo: Фото (файловый объект или ID файла)
            **kwargs: Дополнительные аргументы
            
        Returns:
            Объект сообщения
        """
        caption = kwargs.get('caption', None)
        parse_mode = kwargs.get('parse_mode', None)
        reply_markup = kwargs.get('reply_markup', None)
        
        # Конвертировать разметку клавиатуры из telebot в python-telegram-bot
        ptb_markup = None
        if reply_markup:
            ptb_markup = self._convert_markup_to_ptb(reply_markup)
        
        msg = self.bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=caption,
            parse_mode=parse_mode,
            reply_markup=ptb_markup
        )
        return self._convert_message_to_telebot(msg)
    
    def get_file(self, file_id: str) -> Any:
        """
        Получает информацию о файле.
        
        Args:
            file_id: ID файла
            
        Returns:
            Объект с информацией о файле
        """
        file = self.bot.get_file(file_id)
        # Эмулируем интерфейс telebot.types.File
        class TelebotFile:
            def __init__(self, ptb_file):
                self.file_id = ptb_file.file_id
                self.file_path = ptb_file.file_path
                self.file_size = ptb_file.file_size
        
        return TelebotFile(file)
    
    def download_file(self, file_path: str) -> bytes:
        """
        Скачивает файл по ссылке.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Содержимое файла
        """
        return self.bot.get_file(file_path).download_as_bytearray()
    
    def answer_callback_query(self, callback_query_id: str, **kwargs) -> bool:
        """
        Отвечает на callback запрос.
        
        Args:
            callback_query_id: ID callback запроса
            **kwargs: Дополнительные аргументы
            
        Returns:
            True, если запрос обработан
        """
        text = kwargs.get('text', None)
        show_alert = kwargs.get('show_alert', False)
        
        self.bot.answer_callback_query(
            callback_query_id=callback_query_id,
            text=text,
            show_alert=show_alert
        )
        return True
    
    def _convert_message_to_telebot(self, ptb_message) -> Message:
        """
        Конвертирует сообщение из python-telegram-bot в формат telebot.
        
        Args:
            ptb_message: Объект сообщения python-telegram-bot
            
        Returns:
            Объект сообщения в формате telebot
        """
        # Создаем заглушку сообщения telebot
        msg = Message()
        msg.message_id = ptb_message.message_id
        msg.chat = type('Chat', (), {
            'id': ptb_message.chat.id,
            'type': ptb_message.chat.type,
            'title': getattr(ptb_message.chat, 'title', None),
            'username': getattr(ptb_message.chat, 'username', None),
            'first_name': getattr(ptb_message.chat, 'first_name', None),
            'last_name': getattr(ptb_message.chat, 'last_name', None),
        })
        msg.text = getattr(ptb_message, 'text', None)
        msg.content_type = 'text' if hasattr(ptb_message, 'text') else 'unknown'
        return msg
    
    def _convert_markup_to_ptb(self, telebot_markup) -> Any:
        """
        Конвертирует разметку клавиатуры из telebot в python-telegram-bot.
        
        Args:
            telebot_markup: Объект разметки telebot
            
        Returns:
            Объект разметки python-telegram-bot
        """
        from telegram import InlineKeyboardMarkup as PTBInlineKeyboardMarkup
        from telegram import InlineKeyboardButton as PTBInlineKeyboardButton
        
        if isinstance(telebot_markup, InlineKeyboardMarkup):
            ptb_buttons = []
            for row in telebot_markup.keyboard:
                ptb_row = []
                for button in row:
                    if button.url:
                        ptb_row.append(PTBInlineKeyboardButton(
                            text=button.text,
                            url=button.url
                        ))
                    else:
                        ptb_row.append(PTBInlineKeyboardButton(
                            text=button.text,
                            callback_data=button.callback_data
                        ))
                ptb_buttons.append(ptb_row)
            return PTBInlineKeyboardMarkup(ptb_buttons)
        return None

    def message_handler(self, **kwargs):
        """
        Декоратор для обработчиков сообщений.
        
        Args:
            **kwargs: Параметры обработчика (commands, content_types, func)
            
        Returns:
            Декоратор
        """
        def decorator(handler):
            handler_info = {
                'handler': handler,
                'filters': kwargs
            }
            self.message_handlers.append(handler_info)
            return handler
        return decorator
    
    def callback_query_handler(self, **kwargs):
        """
        Декоратор для обработчиков callback запросов.
        
        Args:
            **kwargs: Параметры обработчика (func)
            
        Returns:
            Декоратор
        """
        def decorator(handler):
            handler_info = {
                'handler': handler,
                'filters': kwargs
            }
            self.callback_query_handlers.append(handler_info)
            return handler
        return decorator
    
    def add_handler(self, handler, *args, **kwargs):
        """
        Добавляет обработчик к приложению.
        
        Args:
            handler: Обработчик
            *args: Дополнительные аргументы
            **kwargs: Дополнительные именованные аргументы
        """
        if self.application:
            self.application.add_handler(handler, *args, **kwargs)


# Создаем экземпляр TeleBot для совместимости
def create_telebot(application: Application) -> TeleBot:
    """
    Создает экземпляр TeleBot из Application python-telegram-bot.
    
    Args:
        application: Экземпляр Application из python-telegram-bot
        
    Returns:
        Экземпляр TeleBot
    """
    token = application.bot.token
    return TeleBot(token=token, application=application, bot=application.bot) 