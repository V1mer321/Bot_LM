#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для автоматической установки GPU версии PyTorch
"""

import subprocess
import sys
import platform

def check_nvidia_gpu():
    """Проверяет наличие NVIDIA GPU"""
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def install_cuda_pytorch():
    """Устанавливает CUDA версию PyTorch"""
    
    print("🚀 УСТАНОВКА GPU ВЕРСИИ PYTORCH")
    print("="*50)
    
    # Проверяем наличие NVIDIA GPU
    if not check_nvidia_gpu():
        print("❌ NVIDIA GPU не обнаружен или драйверы не установлены")
        print("   Установка GPU версии PyTorch невозможна")
        return False
    
    print("✅ NVIDIA GPU обнаружен")
    
    # Показываем варианты CUDA
    print("\n🎯 Выберите версию CUDA:")
    print("1. CUDA 11.8 (рекомендуется для большинства GPU)")
    print("2. CUDA 12.1 (для новых GPU)")
    print("3. Отмена")
    
    while True:
        choice = input("\nВведите номер (1-3): ").strip()
        
        if choice == "1":
            cuda_version = "cu118"
            url = "https://download.pytorch.org/whl/cu118"
            break
        elif choice == "2":
            cuda_version = "cu121"
            url = "https://download.pytorch.org/whl/cu121"
            break
        elif choice == "3":
            print("Установка отменена")
            return False
        else:
            print("❌ Некорректный выбор. Введите 1, 2 или 3")
    
    print(f"\n🔄 Устанавливаю PyTorch с CUDA {cuda_version.replace('cu', '')}...")
    
    try:
        # Удаляем старую версию
        print("1️⃣ Удаляю старую версию PyTorch...")
        subprocess.run([
            sys.executable, "-m", "pip", "uninstall", 
            "torch", "torchvision", "torchaudio", "-y"
        ], check=True)
        
        # Устанавливаем новую версию
        print("2️⃣ Устанавливаю CUDA версию PyTorch...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "torch", "torchvision", "torchaudio", 
            "--index-url", url
        ], check=True)
        
        print("✅ Установка завершена!")
        
        # Проверяем установку
        print("3️⃣ Проверяю установку...")
        result = subprocess.run([
            sys.executable, "-c", 
            "import torch; print(f'CUDA доступен: {torch.cuda.is_available()}')"
        ], capture_output=True, text=True)
        
        if "CUDA доступен: True" in result.stdout:
            print("🎉 GPU ускорение успешно настроено!")
            print("   Перезапустите бота для применения изменений")
            return True
        else:
            print("⚠️ CUDA не активирован. Возможные проблемы:")
            print("   - Несовместимая версия CUDA")
            print("   - Устаревшие драйверы NVIDIA")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при установке: {e}")
        return False

if __name__ == "__main__":
    success = install_cuda_pytorch()
    
    if success:
        print("\n🎯 Следующие шаги:")
        print("1. Перезапустите бота")
        print("2. Проверьте логи - должно появиться сообщение об обнаружении GPU")
        print("3. Запустите python check_gpu.py для дополнительной проверки")
    else:
        print("\n💡 Альтернативы:")
        print("1. Проверьте наличие NVIDIA GPU")
        print("2. Обновите драйверы NVIDIA")
        print("3. Бот продолжит работать на CPU (медленнее, но стабильно)")
    
    input("\nНажмите Enter для выхода...") 