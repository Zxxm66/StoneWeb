#!/usr/bin/env python3
"""
Stone WebApp Store - Balenciaga-style минимализм
"""

import asyncio
import aiohttp
import aiohttp_jinja2
import jinja2
from aiohttp import web
from pathlib import Path
import sqlite3
import json
import os
import logging
from datetime import datetime
from functools import wraps
import uuid
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
BASE_DIR = Path(__file__).parent
DB_PATH = os.path.join(BASE_DIR, 'data', 'shop.db')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
WEBAPP_DIR = os.path.join(BASE_DIR, 'webapp')


# Создаем необходимые директории
def create_directories():
    """Создает необходимые директории если их нет"""
    directories = [
        TEMPLATES_DIR,
        STATIC_DIR,
        WEBAPP_DIR,
        os.path.join(WEBAPP_DIR, 'css'),
        os.path.join(WEBAPP_DIR, 'js'),
        os.path.join(WEBAPP_DIR, 'components'),
        os.path.join(WEBAPP_DIR, 'images'),
        os.path.dirname(DB_PATH),  # папка data
        os.path.join(BASE_DIR, 'api'),
        os.path.join(STATIC_DIR, 'images'),  # Убедимся что папка images существует
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Папка проверена/создана: {directory}")


# Создаем директории перед запуском
create_directories()

# Убедимся что placeholder изображение существует
placeholder_path = os.path.join(STATIC_DIR, 'images', 'placeholder.jpg')
if not os.path.exists(placeholder_path):
    # Создаем простой placeholder
    import base64

    placeholder_base64 = "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k="
    image_data = base64.b64decode(placeholder_base64)
    with open(placeholder_path, 'wb') as f:
        f.write(image_data)
    logger.info(f"✅ Создан placeholder: {placeholder_path}")

# Убедимся что templates существует
if not os.path.exists(TEMPLATES_DIR):
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    logger.info(f"Создана папка templates: {TEMPLATES_DIR}")

# Создаем базовый design.html если его нет
design_template_path = os.path.join(TEMPLATES_DIR, 'design.html')
if not os.path.exists(design_template_path):
    with open(design_template_path, 'w', encoding='utf-8') as f:
        f.write("""
        <!DOCTYPE html>
        <html>
        <head><title>STONE</title></head>
        <body>
            <h1>STONE Design Page</h1>
            <p>Шаблон загружен успешно!</p>
        </body>
        </html>
        """)
    logger.info(f"Создан базовый шаблон: {design_template_path}")

# Создаем приложение
app = web.Application(client_max_size=20 * 1024 * 1024)

# Настройка Jinja2
env = aiohttp_jinja2.setup(
    app,
    loader=jinja2.FileSystemLoader(TEMPLATES_DIR)
)


# ============== БАЗА ДАННЫХ ==============

def get_db_connection():
    """Создает соединение с БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_store_db():
    """Инициализация БД для магазина"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Таблица веб-виджетов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS web_widgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                widget_type VARCHAR(50) NOT NULL,
                title VARCHAR(255),
                content TEXT,
                config TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                position INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица категорий
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                slug VARCHAR(100) UNIQUE,
                parent_id INTEGER DEFAULT NULL,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица товаров
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL,
                slug VARCHAR(255) UNIQUE,
                description TEXT,
                price DECIMAL(10, 2) NOT NULL,
                compare_at_price DECIMAL(10, 2),
                image_url TEXT,
                gallery TEXT,  -- JSON array of images
                category_id INTEGER,
                brand VARCHAR(100),
                sku VARCHAR(100),
                color VARCHAR(50),
                size VARCHAR(50),
                material VARCHAR(100),
                discount_percent INTEGER DEFAULT 0,
                quantity INTEGER DEFAULT 0,
                is_featured BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                views INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories (id)
            )
        """)

        # Таблица карусели
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS carousel_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(255),
                subtitle VARCHAR(255),
                image_url TEXT NOT NULL,
                link_url VARCHAR(500),
                button_text VARCHAR(100),
                is_active BOOLEAN DEFAULT TRUE,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Добавляем тестовые виджеты если таблица пуста
        cursor.execute("SELECT COUNT(*) FROM web_widgets")
        if cursor.fetchone()[0] == 0:
            test_widgets = [
                ('marquee', None, 'STONE | PREMIUM SNEAKERS | BETWEEN 11/20/2025 AND 12/15/2025 MAY BE RETURNED',
                 '{"speed": 30, "color": "#000000", "bgColor": "#ffffff"}', 1, 0),
                ('hero', 'STONE', 'between 11/20/2025 and 12/15/2025 may be returned', '{}', 2, 0),
                ('info', 'INFORMATION #LINDON', 'money model options, four, savings', '{}', 3, 0),
                ('collection', 'New Collection',
                 'Explore our carefully curated selection of premium sneakers. Each pair is designed with meticulous attention to detail and crafted from the finest materials.',
                 '{"buttonText": "VIEW COLLECTION"}', 4, 0)
            ]

            cursor.executemany("""
                INSERT INTO web_widgets (widget_type, title, content, config, position, sort_order)
                VALUES (?, ?, ?, ?, ?, ?)
            """, test_widgets)
            logger.info("✅ Добавлены тестовые виджеты")

        # Добавляем тестовые категории
        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] == 0:
            categories = [
                ('Sneakers', 'sneakers', None),
                ('Boots', 'boots', None),
                ('Sandals', 'sandals', None),
                ('Accessories', 'accessories', None)
            ]

            cursor.executemany("""
                INSERT INTO categories (name, slug, parent_id)
                VALUES (?, ?, ?)
            """, categories)
            logger.info("✅ Добавлены тестовые категории")

        # Добавляем тестовые товары
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            products = [
                ('KPOCCOBKM', 'kpoccobkm-1', 'Premium sneakers with unique design', 120.00, 150.00,
                 '/static/images/placeholder.jpg', '["/static/images/placeholder.jpg"]', 1, 'STONE', 'STN-001', 'Black',
                 '42', 'Leather', 20, 10, True),
                ('KPOCCOBKM Pro', 'kpoccobkm-pro', 'Advanced version with better materials', 140.00, 180.00,
                 '/static/images/placeholder.jpg', '["/static/images/placeholder.jpg"]', 1, 'STONE', 'STN-002', 'White',
                 '40-45', 'Suede', 22, 8, True),
                ('KPOCCOBKM Lite', 'kpoccobkm-lite', 'Lightweight version for everyday wear', 130.00, None,
                 '/static/images/placeholder.jpg', '["/static/images/placeholder.jpg"]', 1, 'STONE', 'STN-003', 'Gray',
                 '39-44', 'Mesh', 0, 15, True),
                ('KPOCCOBKM Ultra', 'kpoccobkm-ultra', 'Ultimate performance sneakers', 150.00, 200.00,
                 '/static/images/placeholder.jpg', '["/static/images/placeholder.jpg"]', 1, 'STONE', 'STN-004',
                 'Black/White', '41-43', 'Leather/Mesh', 25, 5, True)
            ]

            cursor.executemany("""
                INSERT INTO products (name, slug, description, price, compare_at_price, image_url, gallery, category_id, brand, sku, color, size, material, discount_percent, quantity, is_featured)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, products)
            logger.info("✅ Добавлены тестовые товары")

        # Добавляем карусель
        cursor.execute("SELECT COUNT(*) FROM carousel_items")
        if cursor.fetchone()[0] == 0:
            carousel_items = [
                ('New Collection 2024', 'Discover the latest designs', '/static/images/placeholder.jpg', '/catalog',
                 'SHOP NOW'),
                ('Limited Edition', 'Exclusive items available', '/static/images/placeholder.jpg',
                 '/catalog?filter=limited', 'VIEW'),
                ('Summer Sale', 'Up to 50% off selected items', '/static/images/placeholder.jpg',
                 '/catalog?filter=sale', 'SHOP SALE')
            ]

            cursor.executemany("""
                INSERT INTO carousel_items (title, subtitle, image_url, link_url, button_text)
                VALUES (?, ?, ?, ?, ?)
            """, carousel_items)
            logger.info("✅ Добавлены карусельные элементы")

        conn.commit()
        logger.info("✅ База данных магазина инициализирована")

    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        conn.rollback()
    finally:
        conn.close()


# ============== ВИДЖЕТЫ ==============

async def get_web_widgets():
    """Получает активные виджеты для магазина"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT widget_type, title, content, config, position
            FROM web_widgets 
            WHERE is_active = TRUE 
            ORDER BY position, sort_order
        """)

        widgets = []
        for row in cursor.fetchall():
            widget = dict(row)
            if widget.get('config'):
                try:
                    widget['config'] = json.loads(widget['config'])
                except:
                    widget['config'] = {}
            widgets.append(widget)

        return widgets
    except Exception as e:
        logger.error(f"Ошибка получения виджетов: {e}")
        return []
    finally:
        conn.close()


# ============== СТАТИЧЕСКИЕ ФАЙЛЫ ==============

async def serve_static(request):
    """Отдает статические файлы из webapp"""
    filename = request.match_info.get('filename', 'index.html')
    file_path = os.path.join(WEBAPP_DIR, filename)

    # Проверяем существование файла
    if not os.path.exists(file_path):
        # Если файл не найден, пробуем index.html
        if filename.endswith('.html'):
            file_path = os.path.join(WEBAPP_DIR, 'index.html')
        else:
            raise web.HTTPNotFound()

    return web.FileResponse(file_path)


# ============== API ЭНДПОИНТЫ ==============

async def api_products(request):
    """API для получения товаров"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Получаем параметры запроса
        limit = int(request.query.get('limit', 12))
        offset = int(request.query.get('offset', 0))
        category = request.query.get('category')
        featured = request.query.get('featured')

        # Базовый запрос
        query = """
            SELECT p.id, p.name, p.slug, p.description, p.price, p.compare_at_price, 
                   p.image_url, p.gallery, p.brand, p.discount_percent, p.quantity,
                   p.color, p.size, p.material, p.is_featured,
                   c.name as category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.is_active = TRUE AND p.quantity > 0
        """

        params = []

        if category:
            query += " AND c.slug = ?"
            params.append(category)

        if featured and featured.lower() == 'true':
            query += " AND p.is_featured = TRUE"

        query += " ORDER BY p.is_featured DESC, p.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)

        products = []
        for row in cursor.fetchall():
            product = dict(row)

            # Обработка изображений - используем placeholder если нет изображения
            if not product.get('image_url') or product['image_url'] == 'None':
                product['image_url'] = '/static/images/placeholder.jpg'

            # Основное изображение
            product['main_image'] = product.get('image_url', '/static/images/placeholder.jpg')

            # Форматируем цены
            price = float(product.get('price', 0))
            product['price_formatted'] = f"${price:.0f}"

            if product.get('compare_at_price'):
                compare_price = float(product['compare_at_price'])
                product['compare_price_formatted'] = f"${compare_price:.0f}"

                # Рассчитываем скидку
                if compare_price > price:
                    discount = ((compare_price - price) / compare_price) * 100
                    product['discount_percent'] = int(discount)

            products.append(product)

        conn.close()

        return web.json_response({
            'success': True,
            'products': products,
            'total': len(products),
            'limit': limit,
            'offset': offset
        })

    except Exception as e:
        logger.error(f"Ошибка API товаров: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def api_widgets(request):
    """API для получения виджетов"""
    try:
        widgets = await get_web_widgets()
        return web.json_response({
            'success': True,
            'widgets': widgets
        })
    except Exception as e:
        logger.error(f"Ошибка API виджетов: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        })


async def api_categories(request):
    """API для получения категорий"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, slug, parent_id 
            FROM categories 
            ORDER BY sort_order, name
        """)

        categories = []
        for row in cursor.fetchall():
            category = dict(row)
            categories.append(category)

        conn.close()

        return web.json_response({
            'success': True,
            'categories': categories
        })

    except Exception as e:
        logger.error(f"Ошибка API категорий: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        })


async def api_carousel(request):
    """API для получения карусели"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT title, subtitle, image_url, link_url, button_text
            FROM carousel_items 
            WHERE is_active = TRUE 
            ORDER BY sort_order
            LIMIT 5
        """)

        items = []
        for row in cursor.fetchall():
            item = dict(row)
            # Используем placeholder если нет изображения
            if not item.get('image_url') or item['image_url'] == 'None':
                item['image_url'] = '/static/images/placeholder.jpg'
            items.append(item)

        conn.close()

        return web.json_response({
            'success': True,
            'items': items
        })

    except Exception as e:
        logger.error(f"Ошибка API карусели: {e}")
        return web.json_response({
            'success': False,
            'error': str(e)
        })


# ============== ГЛАВНАЯ СТРАНИЦА ==============

async def home_page(request):
    """Главная страница магазина с дизайном Balenciaga"""
    try:
        # Получаем данные для страницы
        conn = get_db_connection()
        cursor = conn.cursor()

        # Виджеты
        cursor.execute("""
            SELECT widget_type, title, content, config
            FROM web_widgets 
            WHERE is_active = TRUE 
            ORDER BY position, sort_order
        """)
        widgets = [dict(row) for row in cursor.fetchall()]

        # Популярные товары
        cursor.execute("""
            SELECT id, name, price, image_url, discount_percent, brand
            FROM products 
            WHERE is_active = TRUE AND quantity > 0
            ORDER BY is_featured DESC, created_at DESC
            LIMIT 4
        """)
        featured_products = []
        for row in cursor.fetchall():
            product = dict(row)
            # Используем placeholder если нет изображения
            if not product.get('image_url') or product['image_url'] == 'None':
                product['image_url'] = '/static/images/placeholder.jpg'
            featured_products.append(product)

        # Карусель
        cursor.execute("""
            SELECT title, subtitle, image_url, link_url, button_text
            FROM carousel_items 
            WHERE is_active = TRUE 
            ORDER BY sort_order
            LIMIT 3
        """)
        carousel_items = []
        for row in cursor.fetchall():
            item = dict(row)
            if not item.get('image_url') or item['image_url'] == 'None':
                item['image_url'] = '/static/images/placeholder.jpg'
            carousel_items.append(item)

        conn.close()

        # Подготавливаем данные
        for widget in widgets:
            if widget.get('config'):
                try:
                    widget['config'] = json.loads(widget['config'])
                except:
                    widget['config'] = {}

        context = {
            'widgets': widgets,
            'featured_products': featured_products,
            'carousel_items': carousel_items,
            'current_year': datetime.now().year,
            'range': range  # добавляем функцию range в контекст
        }

        return aiohttp_jinja2.render_template('design.html', request, context)

    except Exception as e:
        logger.error(f"Ошибка рендеринга главной страницы: {e}")
        return web.Response(
            text=f"""
            <html>
            <body>
                <h1>Ошибка загрузки страницы</h1>
                <p>{str(e)}</p>
                <p>Проверьте логи сервера</p>
            </body>
            </html>
            """,
            content_type='text/html',
            status=500
        )


async def catalog_page(request):
    """Страница каталога"""
    return await serve_static(request)


async def product_page(request):
    """Страница товара"""
    return await serve_static(request)


async def cart_page(request):
    """Страница корзины"""
    return await serve_static(request)


async def checkout_page(request):
    """Страница оформления заказа"""
    return await serve_static(request)


async def design_page(request):
    """Дизайн-страница (старая версия для обратной совместимости)"""
    return await home_page(request)


# ============== СТАТИЧЕСКИЕ ФАЙЛЫ С ОБРАБОТКОЙ ОШИБОК ==============

async def serve_static_file(request):
    """Отдает статические файлы с обработкой ошибок"""
    try:
        # Получаем путь к файлу
        path = request.match_info.get('path', '')
        file_path = os.path.join(STATIC_DIR, path)

        # Проверяем существование файла
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            # Если это изображение, возвращаем placeholder
            if path.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                file_path = os.path.join(STATIC_DIR, 'images', 'placeholder.jpg')
                if not os.path.exists(file_path):
                    raise web.HTTPNotFound()
            else:
                raise web.HTTPNotFound()

        return web.FileResponse(file_path)
    except Exception as e:
        logger.error(f"Ошибка отдачи статического файла: {e}")
        raise web.HTTPNotFound()


# ============== РЕГИСТРАЦИЯ РОУТОВ ==============

def setup_routes():
    # Главная страница (новый дизайн)
    app.router.add_get('/', home_page)

    # Старый маршрут для обратной совместимости
    app.router.add_get('/design', design_page)

    # Основные страницы магазина
    app.router.add_get('/catalog', catalog_page)
    app.router.add_get('/product/{id}', product_page)
    app.router.add_get('/cart', cart_page)
    app.router.add_get('/checkout', checkout_page)

    # Статические файлы из webapp
    app.router.add_get('/webapp/{filename}', serve_static)
    app.router.add_get('/webapp/', serve_static)

    # API эндпоинты
    app.router.add_get('/api/products', api_products)
    app.router.add_get('/api/widgets', api_widgets)
    app.router.add_get('/api/categories', api_categories)
    app.router.add_get('/api/carousel', api_carousel)

    # Health check
    app.router.add_get('/health', lambda r: web.Response(text='OK'))

    # Статические файлы (css, js, images) с обработкой ошибок
    app.router.add_get('/static/{path:.*}', serve_static_file)

    # Редирект для favicon
    app.router.add_get('/favicon.ico', lambda r: web.HTTPFound('/static/images/placeholder.jpg'))


# ============== ЗАПУСК СЕРВЕРА ==============

if __name__ == '__main__':
    # Инициализация БД
    init_store_db()

    # Настройка роутов
    setup_routes()

    # Запуск сервера
    host = os.getenv('STORE_HOST', '0.0.0.0')
    port = int(os.getenv('STORE_PORT', 8000))

    logger.info(f"🚀 Запуск Stone WebApp Store на {host}:{port}")
    logger.info(f"📁 WebApp директория: {WEBAPP_DIR}")
    logger.info(f"🗄️ База данных: {DB_PATH}")
    logger.info(f"🎨 Balenciaga дизайн: http://{host}:{port}/")
    logger.info(f"📱 Telegram WebApp: http://{host}:{port}/webapp/")
    logger.info(f"🛍️ API товаров: http://{host}:{port}/api/products")

    web.run_app(app, host=host, port=port, access_log=logger)