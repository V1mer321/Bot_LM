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
    Поиск в базе магазинов по их названию и адресу
    
    Args:
        query: Поисковый запрос
        
    Returns:
        Список строк с результатами поиска
    """
    try:
        config = load_config()
        if not config:
            logger.error("Невозможно загрузить конфигурацию для поиска магазинов")
            return ["❌ Ошибка при загрузке конфигурации"]
            
        # Используем ключ table_2 вместо stores_file
        excel_file = config.get('table_2')
        if not excel_file or not os.path.exists(excel_file):
            # Пробуем использовать абсолютный путь как запасной вариант
            excel_file = "C:\\Users\\PluxuryPC\\PycharmProjects\\PythonProject5\\data\\table_2.xlsx"
            if not os.path.exists(excel_file):
                logger.error(f"Файл с базой магазинов не найден: {excel_file}")
                return ["❌ Файл с базой магазинов не найден"]
        
        # Читаем Excel файл
        df = pd.read_excel(excel_file)
        logger.info(f"Загружена таблица магазинов. Количество строк: {len(df)}")
        logger.info(f"Колонки в таблице: {df.columns.tolist()}")
        
        # Проверяем наличие колонки 'Наименование'
        if 'Наименование' not in df.columns:
            logger.error(f"❌ В таблице отсутствует колонка 'Наименование'")
            return ["❌ Ошибка в структуре таблицы магазинов"]

        # Если запрос пустой, возвращаем первые 15 строк
        if not query.strip():
            results = []
            for _, row in df.head(15).iterrows():
                store_info = [f"🏪 *{row['Наименование']}*"]
                
                for col in df.columns:
                    if col != 'Наименование':
                        value = row[col]
                        if pd.notna(value):  # Проверяем, что значение не NaN
                            formatted_value = format_numeric_value(value)
                            store_info.append(f"• {col}: {formatted_value}")
                
                results.append("\n".join(store_info))
            return results

        # Приводим запрос к нижнему регистру
        query = query.lower().strip()
        logger.info(f"Поисковый запрос для магазинов: {query}")

        # Поиск по всем текстовым колонкам
        matches = df.apply(
            lambda row: any(
                str(value).lower().find(query) != -1 
                for value in row if pd.notna(value) and isinstance(value, str)
            ), 
            axis=1
        )
        
        results_df = df[matches]
        logger.info(f"Найдено совпадений: {len(results_df)}")
        
        if not results_df.empty:
            # Форматируем результаты
            results = []
            for _, row in results_df.iterrows():
                store_info = [f"🏪 *{row['Наименование']}*"]
                
                for col in df.columns:
                    if col != 'Наименование':
                        value = row[col]
                        if pd.notna(value):  # Проверяем, что значение не NaN
                            formatted_value = format_numeric_value(value)
                            if col == 'Отдел':
                                store_info.append(f"📍 Отдел: {formatted_value}")
                            else:
                                store_info.append(f"• {col}: {formatted_value}")
                
                results.append("\n".join(store_info))
            
            return results
        else:
            # Выводим для отладки
            logger.info("Примеры данных из таблицы:")
            logger.info(df['Наименование'].head().to_string())
            return []
                
    except Exception as e:
        logger.error(f"Ошибка при поиске магазинов: {e}")
        import traceback
        logger.error(f"Детали ошибки: {traceback.format_exc()}")
        return ["❌ Произошла ошибка при поиске магазинов"]


async def search_in_skobyanka(query: str) -> list:
    """
    Поиск в базе скобяных изделий
    
    Args:
        query: Поисковый запрос
        
    Returns:
        Список строк с результатами поиска
    """
    try:
        config = load_config()
        if not config:
            logger.error("Невозможно загрузить конфигурацию для поиска скобянки")
            return ["❌ Ошибка при загрузке конфигурации"]
            
        # Использовать имя ключа из конфигурации
        excel_file = config.get('skobyanka_table')
        if not excel_file or not os.path.exists(excel_file):
            # Пробуем использовать абсолютный путь как запасной вариант
            excel_file = "C:\\Users\\PluxuryPC\\PycharmProjects\\PythonProject5\\data\\skobyanka.xlsx"
            if not os.path.exists(excel_file):
                logger.error(f"Файл скобянки не найден: {excel_file}")
                return ["❌ Файл с базой данных не найден"]
            
        # Читаем Excel файл
        df = pd.read_excel(excel_file)
        logger.info(f"Загружена таблица скобянки. Количество строк: {len(df)}")
        logger.info(f"Колонки в таблице: {df.columns.tolist()}")
        
        # Если запрос пустой, возвращаем первые 15 строк
        if not query.strip():
            results = []
            for _, row in df.head(15).iterrows():
                result_parts = []
                
                # Определяем основное название/артикул
                name_column = next((col for col in ['Наименование', 'Товар', 'Артикул'] 
                                    if col in df.columns), df.columns[0])
                result_parts.append(f"🔧 *{row[name_column]}*")
                
                # Добавляем остальные поля
                for col in df.columns:
                    if col != name_column:
                        value = row[col]
                        if pd.notna(value):  # Проверяем, что значение не NaN
                            # Форматируем числовое значение
                            formatted_value = format_numeric_value(value)
                            result_parts.append(f"• {col}: {formatted_value}")
                
                results.append("\n".join(result_parts))
            return results

        # Удаляем пробелы из запроса и приводим к нижнему регистру
        query = query.lower().strip()
        logger.info(f"Поисковый запрос для скобянки: {query}")

        # Поиск по всем колонкам
        matches = df.apply(
            lambda row: any(
                str(value).lower().find(query) != -1 
                for value in row if pd.notna(value)
            ), 
            axis=1
        )
        
        results_df = df[matches]
        logger.info(f"Найдено совпадений: {len(results_df)}")
        
        if not results_df.empty:
            # Форматируем совпадения
            results = []
            for _, row in results_df.iterrows():
                result_parts = []
                
                # Определяем основное название/артикул
                name_column = next((col for col in ['Наименование', 'Товар', 'Артикул'] 
                                    if col in df.columns), df.columns[0])
                result_parts.append(f"🔧 *{row[name_column]}*")
                
                # Добавляем остальные поля
                for col in df.columns:
                    if col != name_column:
                        value = row[col]
                        if pd.notna(value):  # Проверяем, что значение не NaN
                            # Форматируем числовое значение
                            formatted_value = format_numeric_value(value)
                            result_parts.append(f"• {col}: {formatted_value}")
                
                results.append("\n".join(result_parts))
            
            return results[:10]  # Ограничиваем до 10 результатов
        else:
            return []
                
    except Exception as e:
        logger.error(f"Ошибка при поиске скобянки: {e}")
        import traceback
        logger.error(f"Детали ошибки: {traceback.format_exc()}")
        return ["❌ Произошла ошибка при поиске"]