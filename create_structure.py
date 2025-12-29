import os
from pathlib import Path


def create_project_structure():
    """Создает структуру папок проекта"""
    base_dir = Path(__file__).parent

    folders = [
        'data',
        'webapp/css',
        'webapp/js',
        'webapp/components',
        'templates',
        'static',
        'api'
    ]

    for folder in folders:
        folder_path = base_dir / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Создана папка: {folder_path}")

    # Создаем базовые файлы
    files = {
        'webapp/index.html': '<!DOCTYPE html>\n<html>\n<head><title>STONE</title></head>\n<body>\n<h1>Loading...</h1>\n</body>\n</html>',
        'webapp/css/balenciaga.css': '/* Balenciaga стили будут здесь */',
        'webapp/css/animations.css': '/* Анимации будут здесь */',
        'webapp/js/app.js': '// Основной JS файл магазина',
        'webapp/js/telegram.js': '// Telegram WebApp SDK интеграция',
        '.env.example': 'STORE_HOST=0.0.0.0\nSTORE_PORT=8000\nDB_PATH=data/shop.db'
    }

    for file_path, content in files.items():
        file_full_path = base_dir / file_path
        file_full_path.write_text(content, encoding='utf-8')
        print(f"✅ Создан файл: {file_path}")


if __name__ == '__main__':
    create_project_structure()
    print("🎉 Структура проекта создана!")
