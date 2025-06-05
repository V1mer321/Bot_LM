#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для проверки доступности GPU и CUDA
"""

import torch
import sys

def check_gpu_availability():
    """Проверяет доступность GPU и CUDA"""
    
    print("🔍 ПРОВЕРКА GPU И CUDA")
    print("="*50)
    
    # Версия PyTorch
    print(f"📦 PyTorch версия: {torch.__version__}")
    
    # Проверка CUDA
    cuda_available = torch.cuda.is_available()
    print(f"⚡ CUDA доступен: {'✅ Да' if cuda_available else '❌ Нет'}")
    
    if cuda_available:
        # Информация о GPU
        gpu_count = torch.cuda.device_count()
        print(f"🎮 Количество GPU: {gpu_count}")
        
        for i in range(gpu_count):
            gpu_name = torch.cuda.get_device_name(i)
            gpu_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
            print(f"  GPU {i}: {gpu_name} ({gpu_memory:.2f} ГБ)")
        
        current_device = torch.cuda.current_device()
        print(f"🎯 Текущее устройство: GPU {current_device}")
        
        # Тест создания тензора на GPU
        try:
            test_tensor = torch.rand(10, 10).cuda()
            print("✅ Тест создания тензора на GPU: успешно")
            del test_tensor
        except Exception as e:
            print(f"❌ Ошибка при создании тензора на GPU: {e}")
    else:
        print("💻 Используется CPU")
        
        # Возможные причины отсутствия CUDA
        print("\n🔧 Возможные причины отсутствия CUDA:")
        print("1. Не установлены драйверы NVIDIA")
        print("2. Установлена CPU-версия PyTorch")
        print("3. Версия CUDA не совместима с PyTorch")
        print("4. Нет NVIDIA GPU на этом компьютере")

def check_nvidia_gpu():
    """Проверяет наличие NVIDIA GPU в системе"""
    try:
        import subprocess
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        if result.returncode == 0:
            print("\n🎮 ИНФОРМАЦИЯ О GPU ИЗ nvidia-smi:")
            print("-" * 50)
            lines = result.stdout.split('\n')
            for line in lines:
                if 'GeForce' in line or 'RTX' in line or 'GTX' in line or 'Tesla' in line:
                    print(f"  {line.strip()}")
            return True
        else:
            print("\n❌ nvidia-smi недоступен (драйверы не установлены или нет NVIDIA GPU)")
            return False
    except FileNotFoundError:
        print("\n❌ nvidia-smi не найден (драйверы NVIDIA не установлены)")
        return False
    except Exception as e:
        print(f"\n❌ Ошибка при проверке nvidia-smi: {e}")
        return False

def suggest_cuda_installation():
    """Предлагает способы установки CUDA версии PyTorch"""
    
    print("\n🛠️ КАК УСТАНОВИТЬ CUDA ВЕРСИЮ PYTORCH:")
    print("="*50)
    
    # Получаем версию CUDA если доступна
    if torch.cuda.is_available():
        cuda_version = torch.version.cuda
        print(f"📦 Версия CUDA в PyTorch: {cuda_version}")
    
    print("\n1️⃣ Переустановить PyTorch с CUDA поддержкой:")
    print("   pip uninstall torch torchvision torchaudio")
    print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
    
    print("\n2️⃣ Или для CUDA 12.1:")
    print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
    
    print("\n3️⃣ Проверить совместимость:")
    print("   - Сайт: https://pytorch.org/get-started/locally/")
    print("   - Выберите свою версию CUDA")
    
    print("\n4️⃣ Установить драйверы NVIDIA (если нужно):")
    print("   - https://www.nvidia.com/Download/index.aspx")

if __name__ == "__main__":
    check_gpu_availability()
    
    has_nvidia = check_nvidia_gpu()
    
    if not torch.cuda.is_available() and has_nvidia:
        suggest_cuda_installation()
    elif not torch.cuda.is_available() and not has_nvidia:
        print("\n💡 В этой системе нет NVIDIA GPU. GPU ускорение недоступно.")
        print("   Приложение будет работать на CPU (медленнее, но стабильно).") 