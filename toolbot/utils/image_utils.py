"""
Утилиты для обработки изображений.
"""
import os
import logging
import uuid
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def preprocess_image_for_search(image_path):
    """
    Расширенная предварительная обработка изображения для улучшения качества распознавания.
    Включает адаптивную коррекцию контраста, удаление шума, улучшение резкости 
    и фокусировку на объекте.
    
    Args:
        image_path: Путь к исходному изображению
        
    Returns:
        Путь к обработанному изображению или None в случае ошибки
    """
    try:
        # Загружаем изображение
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Не удалось загрузить изображение для предобработки: {image_path}")
            return None
            
        # Получаем размеры изображения
        height, width = img.shape[:2]
        
        # Если изображение слишком большое, уменьшаем его для ускорения обработки
        max_dimension = 1024
        if max(height, width) > max_dimension:
            scale = max_dimension / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            logger.info(f"Изображение уменьшено до {new_width}x{new_height}")
        
        # Анализируем изображение для адаптивной обработки
        img_yuv = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)
        y_channel = img_yuv[:,:,0]
        
        # Получаем статистику по яркости изображения
        min_val, max_val, _, _ = cv2.minMaxLoc(y_channel)
        mean_val = np.mean(y_channel)
        std_val = np.std(y_channel)
        
        logger.debug(f"Статистика изображения: мин={min_val}, макс={max_val}, среднее={mean_val:.2f}, стд={std_val:.2f}")
        
        # Проверяем, недоэкспонировано или переэкспонировано изображение
        is_dark = mean_val < 100
        is_bright = mean_val > 180
        is_low_contrast = std_val < 40
        
        # Создаем PIL изображение для дальнейшей обработки
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        
        # Адаптивная коррекция контраста в зависимости от статистики изображения
        if is_low_contrast:
            # Применяем автоматическое выравнивание гистограммы для низкоконтрастных изображений
            logger.info("Применяется автоматическое выравнивание гистограммы для низкоконтрастного изображения")
            img_pil = ImageOps.autocontrast(img_pil, cutoff=2)
        else:
            # Иначе применяем умеренное улучшение контраста
            contrast_enhancer = ImageEnhance.Contrast(img_pil)
            img_pil = contrast_enhancer.enhance(1.25)  # Немного увеличиваем контраст
        
        # Адаптивная коррекция яркости
        brightness_factor = 1.0
        if is_dark:
            brightness_factor = 1.4  # Значительно увеличиваем яркость для темных изображений
            logger.info(f"Темное изображение, увеличиваем яркость на {(brightness_factor-1)*100}%")
        elif is_bright:
            brightness_factor = 0.8  # Слегка уменьшаем яркость для светлых изображений
            logger.info(f"Светлое изображение, уменьшаем яркость на {(1-brightness_factor)*100}%")
        
        brightness_enhancer = ImageEnhance.Brightness(img_pil)
        img_pil = brightness_enhancer.enhance(brightness_factor)
        
        # Удаление шума с помощью билатерального фильтра (сохраняет края)
        # Сначала конвертируем PIL обратно в OpenCV
        img_cv2 = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        img_denoised = cv2.bilateralFilter(img_cv2, 9, 75, 75)
        
        # Повышение резкости уже на денойзенном изображении
        img_rgb = cv2.cvtColor(img_denoised, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        
        # Применяем фильтр повышения резкости
        # Используем умную резкость (UnsharpMask) вместо простой
        img_pil = img_pil.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        
        # Улучшаем насыщенность цветов для лучшего распознавания брендов
        color_enhancer = ImageEnhance.Color(img_pil)
        img_pil = color_enhancer.enhance(1.3)  # Увеличиваем насыщенность на 30%
        
        # Дополнительная обработка для выделения границ объектов
        # Конвертируем PIL в OpenCV для обработки
        img_cv2 = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        
        # Определяем, есть ли коробка на изображении
        if detect_tool_box(img_cv2):
            logger.info("Обнаружена коробка с инструментом, применяем специальную обработку")
            # Если инструмент в коробке, пытаемся выделить сам инструмент
            extracted_tool = extract_tool_from_box(img_cv2)
            if extracted_tool is not None:
                img_cv2 = extracted_tool
        
        # Проверяем, есть ли на изображении текст/стикеры/ценники, которые могут мешать
        text_regions = detect_text_regions(img_cv2)
        if text_regions:
            logger.info(f"Обнаружено {len(text_regions)} текстовых областей, маскируем их")
            img_cv2 = mask_text_regions(img_cv2, text_regions)
            
        # Конвертируем обратно в PIL
        img_rgb = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2RGB)
        img_pil_final = Image.fromarray(img_rgb)
        
        # Создаем новый путь для обработанного изображения
        base_path, ext = os.path.splitext(image_path)
        enhanced_path = f"{base_path}_enhanced{ext}"
        
        # Сохраняем обработанное изображение
        img_pil_final.save(enhanced_path)
        logger.info(f"Создано улучшенное изображение: {enhanced_path}")
        
        return enhanced_path
    except Exception as e:
        logger.error(f"Ошибка при предобработке изображения: {e}")
        import traceback
        logger.error(f"Детали ошибки: {traceback.format_exc()}")
        return None


def detect_text_regions(image):
    """
    Обнаруживает области с текстом на изображении (ценники, стикеры и т.д.)
    
    Args:
        image: Изображение в формате OpenCV
        
    Returns:
        Список прямоугольников с координатами текстовых областей [(x1, y1, x2, y2), ...]
    """
    try:
        # Преобразуем изображение в оттенки серого
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Применяем адаптивное пороговое преобразование для выделения текста
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Применяем морфологические операции для выделения текстовых областей
        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        dilation = cv2.dilate(binary, rect_kernel, iterations=1)
        
        # Находим контуры
        contours, _ = cv2.findContours(dilation, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Фильтруем контуры, оставляя только потенциальные текстовые области
        text_regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            # Фильтруем по пропорциям и размеру (текст обычно шире чем выше)
            if 2 < w/h < 20 and w > 30 and h > 10:
                text_regions.append((x, y, x+w, y+h))
        
        return text_regions
    except Exception as e:
        logger.error(f"Ошибка при обнаружении текстовых областей: {e}")
        return []


def mask_text_regions(image, text_regions):
    """
    Маскирует текстовые области на изображении для улучшения распознавания
    
    Args:
        image: Изображение в формате OpenCV
        text_regions: Список координат текстовых областей [(x1, y1, x2, y2), ...]
        
    Returns:
        Изображение с замаскированными текстовыми областями
    """
    try:
        # Создаем копию изображения
        result = image.copy()
        
        # Для каждой текстовой области
        for x1, y1, x2, y2 in text_regions:
            # Получаем среднее значение цвета вокруг текстовой области
            # для более плавного заполнения
            
            # Расширяем область на 5 пикселей для контекста
            x1_ext = max(0, x1 - 5)
            y1_ext = max(0, y1 - 5)
            x2_ext = min(image.shape[1], x2 + 5)
            y2_ext = min(image.shape[0], y2 + 5)
            
            # Получаем пиксели по периметру
            top_row = image[y1_ext:y1, x1_ext:x2_ext]
            bottom_row = image[y2:y2_ext, x1_ext:x2_ext]
            left_col = image[y1_ext:y2_ext, x1_ext:x1]
            right_col = image[y1_ext:y2_ext, x2:x2_ext]
            
            # Объединяем все пиксели периметра
            perimeter_pixels = np.concatenate(
                [top_row.reshape(-1, 3), bottom_row.reshape(-1, 3), 
                 left_col.reshape(-1, 3), right_col.reshape(-1, 3)]
            )
            
            if perimeter_pixels.size > 0:
                # Вычисляем среднее значение цвета
                avg_color = np.mean(perimeter_pixels, axis=0).astype(np.uint8)
                # Заполняем текстовую область средним цветом
                result[y1:y2, x1:x2] = avg_color
            else:
                # Если не удалось получить периметр, используем размытие
                # Вырезаем область и размываем ее сильным Гауссовым размытием
                roi = result[y1:y2, x1:x2]
                blurred_roi = cv2.GaussianBlur(roi, (21, 21), 0)
                result[y1:y2, x1:x2] = blurred_roi
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при маскировании текстовых областей: {e}")
        return image


def detect_tool_box(image):
    """
    Определяет, находится ли инструмент в коробке
    
    Args:
        image: Изображение в формате OpenCV
        
    Returns:
        True если инструмент в коробке, иначе False
    """
    try:
        # Конвертируем в оттенки серого
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Находим контуры
        _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Если контуров нет, возвращаем False
        if not contours:
            return False
        
        # Получаем размеры изображения
        height, width = image.shape[:2]
        image_area = height * width
        
        # Ищем большие прямоугольные контуры (потенциально коробки)
        for contour in contours:
            area = cv2.contourArea(contour)
            # Если контур занимает значительную часть изображения
            if area > image_area * 0.3:
                # Проверяем прямоугольность контура
                perimeter = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.04 * perimeter, True)
                if len(approx) == 4:  # Прямоугольник
                    return True
        
        # Дополнительно проверяем наличие специфичных цветов для коробок инструментов
        # Многие коробки имеют яркие цвета (Makita - синий, DeWalt - желтый)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Синие коробки (Makita, Bosch, Dexter)
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        blue_pixels = cv2.countNonZero(blue_mask)
        
        # Желтые коробки (DeWalt)
        lower_yellow = np.array([20, 100, 100])
        upper_yellow = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        yellow_pixels = cv2.countNonZero(yellow_mask)
        
        # Проверяем зеленый цвет (Hitachi, некоторые Bosch)
        lower_green = np.array([40, 50, 50])
        upper_green = np.array([80, 255, 255])
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        green_pixels = cv2.countNonZero(green_mask)
        
        # Проверяем красный цвет (Milwaukee, Hilti)
        # Красный цвет в HSV находится на обоих концах спектра, поэтому используем две маски
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        red_pixels = cv2.countNonZero(red_mask)
        
        # Определяем порог для обнаружения коробки (снижаем с 0.2 до 0.15 для лучшего обнаружения)
        color_threshold = image_area * 0.15
        if (blue_pixels > color_threshold or 
            yellow_pixels > color_threshold or 
            green_pixels > color_threshold or 
            red_pixels > color_threshold):
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"Ошибка при определении коробки: {e}")
        return False


def extract_tool_from_box(image):
    """
    Извлекает инструмент из коробки, фокусируясь на самом инструменте
    с использованием улучшенного алгоритма сегментации
    
    Args:
        image: Изображение в формате OpenCV
        
    Returns:
        Изображение с извлеченным инструментом или None в случае ошибки
    """
    try:
        # Размеры изображения
        height, width = image.shape[:2]
        
        # Конвертируем в оттенки серого
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Применяем GrabCut для сегментации инструмента от фона
        # Создаем маску для GrabCut
        mask = np.zeros(image.shape[:2], np.uint8)
        
        # Примерный прямоугольник вокруг центра изображения
        # Сначала берем центральную область как 60% от размера изображения
        rect_width = int(width * 0.6)
        rect_height = int(height * 0.6)
        rect_x = (width - rect_width) // 2
        rect_y = (height - rect_height) // 2
        rect = (rect_x, rect_y, rect_width, rect_height)
        
        # Применяем GrabCut для выделения объекта
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        
        try:
            # Пытаемся применить GrabCut с ограниченным числом итераций для скорости
            cv2.grabCut(image, mask, rect, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_RECT)
        except Exception as e:
            logger.warning(f"Ошибка при применении GrabCut: {e}. Используем альтернативный метод.")
            # Если GrabCut не сработал, используем простое обрезание по центру
            return extract_central_region(image)
        
        # Создаем маску для выделения переднего плана
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        
        # Если маска пустая, используем альтернативный метод
        if np.sum(mask2) < 100:
            logger.warning("GrabCut не выделил объект. Используем альтернативный метод.")
            return extract_central_region(image)
        
        # Применяем маску к изображению
        extracted = image * mask2[:, :, np.newaxis]
        
        # Находим ограничивающий прямоугольник для объекта
        non_zero_points = cv2.findNonZero(mask2)
        if non_zero_points is None or len(non_zero_points) == 0:
            logger.warning("Не удалось найти ненулевые точки в маске. Используем альтернативный метод.")
            return extract_central_region(image)
            
        x, y, w, h = cv2.boundingRect(non_zero_points)
        
        # Вырезаем объект с небольшим отступом
        padding = 20
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(width, x + w + padding)
        y2 = min(height, y + h + padding)
        
        # Вырезаем объект
        roi = image[y1:y2, x1:x2]
        
        # Проверяем, получили ли мы что-то полезное
        if roi.size == 0:
            logger.warning("Не удалось извлечь ROI с помощью GrabCut, возвращаем центральную область")
            return extract_central_region(image)
            
        return roi
        
    except Exception as e:
        logger.error(f"Ошибка при извлечении инструмента из коробки: {e}")
        # В случае любой ошибки возвращаем центральную область
        return extract_central_region(image)


def extract_central_region(image):
    """
    Извлекает центральную область изображения
    
    Args:
        image: Изображение в формате OpenCV
        
    Returns:
        Центральная область изображения
    """
    try:
        # Размеры изображения
        height, width = image.shape[:2]
        
        # Вычисляем центральную область (70%)
        center_x, center_y = width // 2, height // 2
        roi_width = int(width * 0.7)
        roi_height = int(height * 0.7)
        
        # Координаты углов
        x1 = max(0, center_x - roi_width // 2)
        y1 = max(0, center_y - roi_height // 2)
        x2 = min(width, x1 + roi_width)
        y2 = min(height, y1 + roi_height)
        
        # Вырезаем ROI
        roi = image[y1:y2, x1:x2]
        return roi
    except Exception as e:
        logger.error(f"Ошибка при извлечении центральной области: {e}")
        return image


def extract_tool_by_bbox(image_path, bbox, temp_manager=None):
    """
    Извлекает изображение инструмента по координатам ограничивающей рамки
    и улучшает его для лучшего распознавания
    
    Args:
        image_path: Путь к исходному изображению
        bbox: Координаты ограничивающей рамки (x1, y1, x2, y2)
        temp_manager: Менеджер временных файлов (опционально)
        
    Returns:
        Путь к файлу с вырезанным инструментом или None в случае ошибки
    """
    try:
        # Загружаем изображение
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Не удалось загрузить изображение: {image_path}")
            return None
            
        # Извлекаем координаты
        x1, y1, x2, y2 = bbox
        
        # Получаем размеры изображения
        height, width = img.shape[:2]
        
        # Убеждаемся, что координаты в пределах изображения
        x1 = max(0, int(x1))
        y1 = max(0, int(y1))
        x2 = min(width, int(x2))
        y2 = min(height, int(y2))
        
        # Вырезаем область
        tool_img = img[y1:y2, x1:x2]
        
        # Проверяем, не пустая ли область
        if tool_img.size == 0:
            logger.error(f"Вырезанная область имеет нулевой размер: {bbox}")
            return None
            
        # Добавляем небольшое размытие для уменьшения шума
        tool_img = cv2.GaussianBlur(tool_img, (3, 3), 0)
        
        # Улучшаем контраст
        tool_img_rgb = cv2.cvtColor(tool_img, cv2.COLOR_BGR2RGB)
        tool_img_pil = Image.fromarray(tool_img_rgb)
        
        # Улучшаем контраст
        contrast_enhancer = ImageEnhance.Contrast(tool_img_pil)
        tool_img_pil = contrast_enhancer.enhance(1.3)
        
        # Увеличиваем резкость
        tool_img_pil = tool_img_pil.filter(ImageFilter.SHARPEN)
        
        # Конвертируем обратно в OpenCV
        tool_img = cv2.cvtColor(np.array(tool_img_pil), cv2.COLOR_RGB2BGR)
        
        # Определяем путь для сохранения
        if temp_manager:
            # Используем менеджер временных файлов если доступен
            tool_image_path = temp_manager.get_temp_file_path(f"tool_{uuid.uuid4()}", "jpg")
        else:
            # Иначе используем стандартный путь
            base_dir = os.path.dirname(image_path)
            tool_image_path = os.path.join(base_dir, f"tool_{uuid.uuid4()}.jpg")
        
        # Сохраняем изображение инструмента
        cv2.imwrite(tool_image_path, tool_img)
        
        logger.info(f"Извлечено изображение инструмента: {tool_image_path}")
        return tool_image_path
        
    except Exception as e:
        logger.error(f"Ошибка при извлечении инструмента по bbox: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def equalize_image(image):
    """
    Применяет CLAHE (Contrast Limited Adaptive Histogram Equalization)
    для улучшения контраста с сохранением деталей
    
    Args:
        image: Изображение в формате OpenCV
        
    Returns:
        Изображение с улучшенным контрастом
    """
    try:
        # Конвертируем в LAB цветовое пространство
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Создаем CLAHE объект
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        
        # Применяем CLAHE только к L-каналу
        cl = clahe.apply(l)
        
        # Объединяем каналы
        merged = cv2.merge((cl, a, b))
        
        # Конвертируем обратно в BGR
        result = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при эквализации изображения: {e}")
        return image 