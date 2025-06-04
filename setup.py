from setuptools import setup, find_packages

setup(
    name="toolbot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "python-telegram-bot>=20.3",
        "torch",
        "onnx",
        "onnxruntime",
        "pillow",
        "opencv-python-headless",
        "numpy",
        "scikit-learn",
        "redis",
        "python-dotenv",
        "psutil",
        "colorama",
        "aiohttp",
        "pyTelegramBotAPI",
    ],
) 