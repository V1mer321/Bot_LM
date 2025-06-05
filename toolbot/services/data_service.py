"""
Модуль для работы с данными из файлов и баз данных.
Предоставляет функции поиска в Excel файлах и других источниках данных.
"""
import os
import logging
import pandas as pd
from pathlib import Path

from toolbot.config import load_config

logger = logging.getLogger(__name__)


def format_numeric_value(value):
    """
    Форматирует числовое значение для вывода, удаляя десятичную точку и нули у целых чисел
    
    Args:
        value: Форматируемое значение
        
    Returns:
        Отформатированное значение в виде строки
    """
    try:
        # Если значение - число
        if isinstance(value, (int, float)):
            # Проверяем, является ли число целым (например, 450.0)
            if value.is_integer():
                return str(int(value))  # Конвертируем в целое число без .0
            else:
                return str(value)  # Оставляем как есть для дробных чисел
        # Если это уже строка или другой тип, возвращаем как есть
        return str(value)
    except Exception:
        # В случае ошибки просто возвращаем строковое представление
        return str(value)


async def search_in_colors(query: str) -> list:
    """
    Поиск в базе цветов по колонке 'Цвет'
    
    Args:
        query: Поисковый запрос
        
    Returns:
        Список строк с результатами поиска
    """
    try:
        config = load_config()
        if not config:
            logger.error("Невозможно загрузить конфигурацию для поиска цветов")
            return ["❌ Ошибка при загрузке конфигурации"]
            
        # Используем ключ table_3 вместо colors_file
        colors_file = config.get('table_3')
        if not colors_file or not os.path.exists(colors_file):
            # Пробуем использовать абсолютный путь как запасной вариант
            colors_file = "C:\\Users\\PluxuryPC\\PycharmProjects\\PythonProject5\\data\\table_3.xlsx"
            if not os.path.exists(colors_file):
                logger.error(f"Файл с базой цветов не найден: {colors_file}")
                return ["❌ Файл с базой цветов не найден"]
        
        # Читаем Excel файл
        df = pd.read_excel(colors_file)
        logger.info(f"Загружена таблица цветов. Количество строк: {len(df)}")
        logger.info(f"Колонки в таблице: {df.columns.tolist()}")
        
        # Проверяем наличие колонки 'Цвет'
        if 'Цвет' not in df.columns:
            logger.error("❌ В таблице отсутствует колонка 'Цвет'")
            return ["❌ Ошибка в структуре таблицы"]

        # Удаляем пробелы из запроса и приводим к нижнему регистру
        query = query.lower().strip()
        logger.info(f"Поисковый запрос: {query}")

        # Поиск в колонке 'Цвет'
        mask = df['Цвет'].astype(str).str.lower().str.contains(query, na=False)
        matches = df[mask]
        
        logger.info(f"Найдено совпадений: {len(matches)}")
        
        if not matches.empty:
            # Форматируем совпадения
            results = []
            for _, row in matches.iterrows():
                result_parts = []
                for col in df.columns:
                    value = row[col]
                    if col == 'Цвет':
                        result_parts.append(f"🎨 *{value}*")
                    else:
                        if pd.notna(value):  # Проверяем, что значение не NaN
                            # Форматируем числовое значение
                            formatted_value = format_numeric_value(value)
                            result_parts.append(f"• {col}: {formatted_value}")
                
                results.append("\n".join(result_parts))
            return results
        else:
            # Выводим первые несколько строк для отладки
            logger.info("Примеры данных из таблицы:")
            logger.info(df['Цвет'].head().to_string())
            return ["❌ Ничего не найдено. Попробуйте изменить запрос."]
                
    except Exception as e:
        logger.error(f"Ошибка при поиске цветов: {e}")
        return ["❌ Произошла ошибка при поиске"]


async def search_in_stores(query: str) -> list:
    """
    Поиск в базе магазинов/отделов по названию и отделу (SQLite)
    
    Args:
        query: Поисковый запрос
        
    Returns:
        Список строк с результатами поиска
    """
    try:
        # Путь к базе данных
        db_path = "data/excel_data.db"
        if not os.path.exists(db_path):
            logger.error(f"База данных {db_path} не найдена")
            return ["❌ База данных магазинов не найдена"]
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем все данные из БД
        cursor.execute("""
            SELECT code, name, department, phone_numbers
            FROM stores 
            ORDER BY name
        """)
        
        all_results = cursor.fetchall()
        
        # Если запрос пустой, возвращаем первые 15 магазинов
        if not query.strip():
            results = all_results[:15]
        else:
            # Фильтруем результаты в Python (поиск по 2-й и 3-й колонке)
            query_lower = query.lower()
            filtered_results = []
            
            for row in all_results:
                code, name, dept, phones = row
                name_lower = (name or "").lower()
                dept_lower = (dept or "").lower()
                
                # Проверяем вхождение подстроки в название или отдел
                if query_lower in name_lower or query_lower in dept_lower:
                    # Определяем приоритет: название важнее отдела
                    priority = 1 if query_lower in name_lower else 2
                    filtered_results.append((priority, row))
            
            # Сортируем по приоритету и берем первые 20
            filtered_results.sort(key=lambda x: (x[0], x[1][1]))  # по приоритету, потом по имени
            results = [row for _, row in filtered_results[:20]]
        conn.close()
        
        if results:
            formatted_results = []
            for code, name, dept, phones in results:
                # Основная информация
                store_info = [f"🏪 *{name}*"]
                
                # Код магазина
                if code:
                    store_info.append(f"🏷️ Код: {code}")
                
                # Отдел (это 3-я колонка по которой ищем)
                if dept:
                    store_info.append(f"📍 Отдел: {dept}")
                
                # Телефоны
                if phones:
                    store_info.append(f"📞 Телефоны: {phones}")
                else:
                    store_info.append(f"📞 Телефоны: Не указаны")
                
                formatted_results.append("\n".join(store_info))
            
            logger.info(f"Найдено {len(formatted_results)} магазинов по запросу: '{query}'")
            return formatted_results
        else:
            logger.info(f"Магазины не найдены по запросу: '{query}'")
            return [f"❌ По запросу '{query}' магазины не найдены"]
                
    except Exception as e:
        logger.error(f"Ошибка при поиске магазинов в БД: {e}")
        import traceback
        logger.error(f"Детали ошибки: {traceback.format_exc()}")
        return ["❌ Произошла ошибка при поиске магазинов"]


async def search_in_skobyanka(query: str) -> list:
    """
    Поиск в базе скобяных изделий (SQLite)
    
    Args:
        query: Поисковый запрос
        
    Returns:
        Список строк с результатами поиска
    """
    try:
        # Путь к базе данных
        db_path = "data/excel_data.db"
        if not os.path.exists(db_path):
            logger.error(f"База данных {db_path} не найдена")
            return ["❌ База данных скобяных изделий не найдена"]
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем все данные из БД
        cursor.execute("""
            SELECT article_code, name, quantity_kg
            FROM skobyanka_products 
            ORDER BY name
        """)
        
        all_results = cursor.fetchall()
        
        # Если запрос пустой, возвращаем первые 15 товаров
        if not query.strip():
            results = all_results[:15]
        else:
            # Фильтруем результаты в Python (поиск по артикулу и названию)
            query_lower = query.lower()
            filtered_results = []
            
            for row in all_results:
                article, name, quantity = row
                article_lower = (article or "").lower()
                name_lower = (name or "").lower()
                
                # Проверяем вхождение подстроки в артикул или название
                if query_lower in article_lower or query_lower in name_lower:
                    # Определяем приоритет: артикул важнее названия
                    priority = 1 if query_lower in article_lower else 2
                    filtered_results.append((priority, row))
            
            # Сортируем по приоритету и берем первые 20
            filtered_results.sort(key=lambda x: (x[0], x[1][1]))  # по приоритету, потом по названию
            results = [row for _, row in filtered_results[:20]]
        
        conn.close()
        
        if results:
            formatted_results = []
            for article, name, quantity in results:
                # Основная информация
                product_info = [f"🔧 *{name}*"]
                
                # Артикул
                if article:
                    product_info.append(f"🏷️ Артикул: {article}")
                
                # Количество в кг
                if quantity is not None:
                    if quantity > 0:
                        product_info.append(f"📦 В наличии: {format_numeric_value(quantity)} кг")
                    else:
                        product_info.append(f"❌ Нет в наличии")
                else:
                    product_info.append(f"❓ Количество не указано")
                
                formatted_results.append("\n".join(product_info))
            
            logger.info(f"Найдено {len(formatted_results)} товаров скобянки по запросу: '{query}'")
            return formatted_results
        else:
            logger.info(f"Товары скобянки не найдены по запросу: '{query}'")
            return [f"❌ По запросу '{query}' товары скобянки не найдены"]
                
    except Exception as e:
        logger.error(f"Ошибка при поиске скобянки в БД: {e}")
        import traceback
        logger.error(f"Детали ошибки: {traceback.format_exc()}")
        return ["❌ Произошла ошибка при поиске скобянки"]