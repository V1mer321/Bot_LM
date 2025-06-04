#!/bin/bash
# Скрипт для загрузки оптимизированных моделей при сборке контейнера

# Создаем директорию для моделей, если она не существует
mkdir -p /app/toolbot/models/optimized

# Функция для загрузки модели с проверкой существования
download_model() {
    local model_url=$1
    local model_path=$2
    local model_name=$(basename "$model_path")
    
    echo "Проверяем $model_name..."
    
    if [ -f "$model_path" ]; then
        echo "Модель $model_name уже существует. Пропускаем загрузку."
    else
        echo "Загружаем $model_name..."
        wget -q --show-progress -O "$model_path" "$model_url"
        
        # Проверяем успешность загрузки
        if [ $? -eq 0 ]; then
            echo "Модель $model_name успешно загружена."
        else
            echo "Ошибка при загрузке модели $model_name."
            # В случае ошибки возвращаем ненулевой код выхода
            return 1
        fi
    fi
    
    return 0
}

# MobileNetV3 Small (ONNX)
MOBILENET_URL="https://github.com/onnx/models/raw/main/vision/classification/mobilenet/model/mobilenetv3-small-1.0.onnx"
MOBILENET_PATH="/app/toolbot/models/optimized/mobilenet_v3_small.onnx"

# EfficientDet-Lite0 (ONNX)
EFFICIENTDET_URL="https://github.com/google/automl/raw/master/efficientdet/lite/efficientdet-lite0.onnx"
EFFICIENTDET_PATH="/app/toolbot/models/optimized/efficientdet_lite0.onnx"

# Загружаем модели
echo "Начинаем загрузку оптимизированных моделей..."

download_model "$MOBILENET_URL" "$MOBILENET_PATH"
if [ $? -ne 0 ]; then
    echo "Не удалось загрузить MobileNetV3. Попытка создания заглушки..."
    # Создаем заглушку для модели (будет заменена при первом запуске)
    echo "PLACEHOLDER_MODEL" > "$MOBILENET_PATH"
fi

download_model "$EFFICIENTDET_URL" "$EFFICIENTDET_PATH"
if [ $? -ne 0 ]; then
    echo "Не удалось загрузить EfficientDet-Lite0. Попытка создания заглушки..."
    # Создаем заглушку для модели (будет заменена при первом запуске)
    echo "PLACEHOLDER_MODEL" > "$EFFICIENTDET_PATH"
fi

echo "Загрузка моделей завершена."

# Создаем файл с информацией о моделях
MODEL_INFO_PATH="/app/toolbot/models/model_info.json"
echo '{
  "models": {
    "mobilenet_v3_small": {
      "path": "/app/toolbot/models/optimized/mobilenet_v3_small.onnx",
      "type": "classification",
      "input_shape": [224, 224],
      "version": "1.0"
    },
    "efficientdet_lite0": {
      "path": "/app/toolbot/models/optimized/efficientdet_lite0.onnx",
      "type": "detection",
      "input_shape": [320, 320],
      "version": "1.0"
    }
  },
  "last_updated": "'$(date -Iseconds)'"
}' > "$MODEL_INFO_PATH"

echo "Информация о моделях сохранена в $MODEL_INFO_PATH"

exit 0 