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
import re
import os
import logging
import urllib.parse
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
DB_PATH = os.path.join(BASE_DIR, 'data', 'shop (2).db')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
WEBAPP_DIR = os.path.join(BASE_DIR, 'webapp')


def create_directories():
    directories = [
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


def ensure_columns(conn, table_name, columns):
    """Add missing columns to a table if they do not exist."""
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    existing = {row[1] for row in cur.fetchall()}
    for name, ddl in columns.items():
        if name not in existing:
            try:
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {name} {ddl}")
                conn.commit()  # Commit immediately after each ALTER
                logger.info(f"Added column {name} to {table_name}")
            except sqlite3.OperationalError as e:
                logger.warning(f"Could not add column {name} to {table_name}: {e}")


def slugify(value):
    """Make a simple URL slug from a string."""
    if not value:
        return None
    slug = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
    return slug or None


def migrate_schema(conn):
    """Ensure legacy databases have the columns expected by current queries."""
    ensure_columns(conn, 'products', {
        'slug': 'TEXT',
        'description': 'TEXT',
        'compare_at_price': 'DECIMAL(10, 2)',
        'gallery': 'TEXT',
        'color': 'VARCHAR(50)',
        'size': 'VARCHAR(50)',
        'material': 'VARCHAR(100)',
        'is_featured': 'BOOLEAN DEFAULT FALSE',
        'views': 'INTEGER DEFAULT 0',
        'is_active': 'BOOLEAN DEFAULT TRUE',
        'created_at': 'TIMESTAMP',
        'updated_at': 'TIMESTAMP'
    })

    ensure_columns(conn, 'categories', {
        'slug': 'VARCHAR(100)',
        'sort_order': 'INTEGER DEFAULT 0',
        'created_at': 'TIMESTAMP'
    })

    ensure_columns(conn, 'web_widgets', {
        'is_active': 'BOOLEAN DEFAULT TRUE',
        'position': 'INTEGER DEFAULT 0',
        'sort_order': 'INTEGER DEFAULT 0',
        'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
        'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
    })

    ensure_columns(conn, 'carousel_items', {
        'is_active': 'BOOLEAN DEFAULT TRUE',
        'sort_order': 'INTEGER DEFAULT 0',
        'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
    })

    cur = conn.cursor()
    cur.execute("UPDATE products SET is_active = 1 WHERE is_active IS NULL")
    cur.execute("UPDATE products SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    cur.execute("UPDATE products SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
    cur.execute("SELECT id, name FROM products WHERE slug IS NULL OR slug = ''")
    for pid, name in cur.fetchall():
        slug = slugify(name) or f"product-{pid}"
        cur.execute("UPDATE products SET slug = ? WHERE id = ?", (slug, pid))

    cur.execute("UPDATE categories SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    cur.execute("SELECT id, name FROM categories WHERE slug IS NULL OR slug = ''")
    for cid, name in cur.fetchall():
        slug = slugify(name) or f"category-{cid}"
        cur.execute("UPDATE categories SET slug = ? WHERE id = ?", (slug, cid))

    cur.execute("UPDATE web_widgets SET is_active = 1 WHERE is_active IS NULL")
    cur.execute("UPDATE web_widgets SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    cur.execute("UPDATE web_widgets SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")

    cur.execute("UPDATE carousel_items SET is_active = 1 WHERE is_active IS NULL")
    cur.execute("UPDATE carousel_items SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")

    conn.commit()


def normalize_image(raw):
    """Return a single usable image URL from legacy or list storage."""
    placeholder = '/static/images/placeholder.jpg'
    if not raw or raw == 'None':
        return placeholder
    if isinstance(raw, str) and raw.strip().startswith('['):
        try:
            data = json.loads(raw)
            if isinstance(data, list) and data:
                return data[0]
        except Exception:
            return placeholder
    return raw


def get_cart_count(request):
    """Return cart item count from a cookie if present."""
    for key in ('cart', 'cart_items'):
        raw = request.cookies.get(key)
        if not raw:
            continue
        try:
            decoded = urllib.parse.unquote(raw)
            data = json.loads(decoded)
            if isinstance(data, list):
                total = 0
                for item in data:
                    qty = item.get('quantity') if isinstance(item, dict) else 1
                    try:
                        total += int(qty)
                    except Exception:
                        total += 1
                return total
        except Exception:
            continue
    return 0


def parse_sizes(size_value):
    """Split size strings into list of tokens/ranges for display."""
    if not size_value:
        return []
    text = str(size_value).replace(',', '.')
    tokens = []
    for part in re.split(r'[/;\\s]+', text):
        if not part:
            continue
        if '-' in part:
            try:
                start_s, end_s = part.split('-', 1)
                start_f = float(start_s)
                end_f = float(end_s)
                step = 0.5 if (start_f % 1 or end_f % 1) else 1
                cur = start_f
                while cur <= end_f + 1e-9:
                    tokens.append(f"{cur}".rstrip('0').rstrip('.') if '.' in f"{cur}" else str(int(cur)))
                    cur = round(cur + step, 2)
                continue
            except Exception:
                pass
        tokens.append(part)
    seen = set()
    result = []
    for t in tokens:
        t_norm = t
        if t_norm not in seen:
            seen.add(t_norm)
            result.append(t_norm)
    try:
        result.sort(key=lambda x: float(str(x).replace(',', '.')))
    except Exception:
        pass
    return result


def list_carousel_images():
    """Return list of image URLs from static/images/carousel."""
    images_dir = os.path.join(STATIC_DIR, 'images', 'carousel')
    urls = []
    if not os.path.isdir(images_dir):
        return urls
    for fname in sorted(os.listdir(images_dir)):
        if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
            urls.append(f'/static/images/carousel/{fname}')
    return urls


def parse_cart_cookie(request):
    """Parse cart cookie into list of {'product_id','quantity'}."""
    raw = request.cookies.get('cart') or request.cookies.get('cart_items')
    if not raw:
        return []
    try:
        decoded = urllib.parse.unquote(raw)
        data = json.loads(decoded)
        if isinstance(data, list):
            items = []
            for entry in data:
                if isinstance(entry, dict) and entry.get('product_id'):
                    try:
                        pid = int(entry['product_id'])
                    except Exception:
                        continue
                    qty = entry.get('quantity', 1)
                    try:
                        qty = int(qty)
                    except Exception:
                        qty = 1
                    items.append({
                        'product_id': pid,
                        'quantity': max(qty, 1),
                        'size': entry.get('size')
                    })
            return items
    except Exception:
        return []
    return []


def format_product_row(row):
    """Normalize product dict with formatted price fields."""
    product = dict(row)
    raw_size = product.get('size_value') or product.get('size')
    if raw_size:
        product['size'] = raw_size
    product['image_url'] = normalize_image(product.get('image_url'))
    price = float(product.get('price', 0) or 0)
    product['price_formatted'] = f"{price:,.0f} RUB".replace(',', ' ')
    if product.get('compare_at_price'):
        compare_price = float(product['compare_at_price'] or 0)
        product['compare_price_formatted'] = f"{compare_price:,.0f} RUB".replace(',', ' ')
        if compare_price > price:
            discount = ((compare_price - price) / compare_price) * 100
            product['discount_percent'] = int(discount)
    return product


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

        migrate_schema(conn)

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

        return 
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
            product = format_product_row(row)
            product['main_image'] = product['image_url']
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
            SELECT p.id, p.name, p.price, p.compare_at_price, p.image_url, p.discount_percent,
                   p.brand, p.color, p.slug, p.size, p.size_id, s.value AS size_value
            FROM products p
            LEFT JOIN sizes s ON p.size_id = s.id
            WHERE p.is_active = TRUE AND p.quantity > 0
            ORDER BY p.is_featured DESC, p.created_at DESC
            LIMIT 4
        """)
        featured_products = []
        for row in cursor.fetchall():
            product = format_product_row(row)
            featured_products.append(product)

        # Карусель: берем файлы из static/images/carousel, fallback к БД
        carousel_items = [{'image_url': url} for url in list_carousel_images()]
        if not carousel_items:
            cursor.execute("""
                SELECT image_url
                FROM carousel_items
                WHERE is_active = TRUE
                ORDER BY sort_order
                LIMIT 3
            """)
            for row in cursor.fetchall():
                item = dict(row)
                item['image_url'] = normalize_image(item.get('image_url'))
                carousel_items.append(item)

        # Категории
        cursor.execute("""
            SELECT id, name, slug, parent_id
            FROM categories
            ORDER BY sort_order, name
        """)
        category_rows = [dict(row) for row in cursor.fetchall()]

        categories = [c for c in category_rows if not c.get('parent_id')]
        subcategories = {}
        for row in category_rows:
            pid = row.get('parent_id')
            if pid:
                subcategories.setdefault(pid, []).append(row)

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
            'categories': categories,
            'subcategories': subcategories,
            'bag_count': get_cart_count(request),
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
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, slug, parent_id, sort_order
            FROM categories
            ORDER BY sort_order, name
        """)
        category_rows = [dict(row) for row in cursor.fetchall()]
        categories = [c for c in category_rows if not c.get('parent_id')]
        subcategories = {}
        for row in category_rows:
            pid = row.get('parent_id')
            if pid:
                subcategories.setdefault(pid, []).append(row)

        category_slug = request.query.get('category')
        brand = request.query.get('brand')
        color = request.query.get('color')
        price_min = request.query.get('price_min')
        price_max = request.query.get('price_max')
        size = request.query.get('size')

        current_category = next((c for c in category_rows if c['slug'] == category_slug), None) if category_slug else None
        current_category_id = current_category['id'] if current_category else None
        # For UI we still need parent to highlight subcats
        current_parent_id = current_category['parent_id'] if current_category and current_category.get('parent_id') else None

        if category_slug:
            logger.info(f"📌 Filter by category: {category_slug} -> ID: {current_category_id}")

        def collect_descendants(rows, root_id):
            ids = []
            if not root_id:
                return ids
            queue = [root_id]
            while queue:
                cid = queue.pop(0)
                if cid in ids:
                    continue
                ids.append(cid)
                for r in rows:
                    if r.get('parent_id') == cid:
                        queue.append(r['id'])
            return ids

        # For filtering, use the selected category (which will include descendants if it has children)
        root_category_id = current_category_id if current_category else None
        allowed_ids = collect_descendants(category_rows, root_category_id)

        if allowed_ids and category_slug:
            logger.info(f"✓ Category filter IDs: {allowed_ids}")

        query = """
            SELECT p.id, p.name, p.price, p.compare_at_price, p.image_url, 
                   p.discount_percent, p.brand, p.color, p.slug,
                   p.size, p.size_id, s.value AS size_value
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN sizes s ON p.size_id = s.id
            WHERE p.is_active = TRUE AND p.quantity > 0
        """
        params = []

        if category_slug and allowed_ids:
            placeholders = ",".join("?" * len(allowed_ids))
            query += f" AND p.category_id IN ({placeholders})"
            params.extend(allowed_ids)
        elif not category_slug:
            allowed_ids = None

        if brand:
            query += " AND LOWER(p.brand) = LOWER(?)"
            params.append(brand)

        if color:
            query += " AND LOWER(p.color) = LOWER(?)"
            params.append(color)

        if price_min:
            try:
                params.append(float(price_min))
                query += " AND p.price >= ?"
            except ValueError:
                pass

        if price_max:
            try:
                params.append(float(price_max))
                query += " AND p.price <= ?"
            except ValueError:
                pass

        query += " ORDER BY p.is_featured DESC, p.created_at DESC"

        cursor.execute(query, params)
        merged = {}
        size_token = size.lower() if size else None
        for row in cursor.fetchall():
            product = format_product_row(row)
            sizes_list = parse_sizes(product.get('size'))
            if size_token:
                has_size = any(str(s).lower() == size_token for s in sizes_list)
                if not has_size:
                    continue
            key = product.get('slug') or product['id']
            if key in merged:
                existing = merged[key]
                for s in sizes_list:
                    if s not in existing['sizes_display']:
                        existing['sizes_display'].append(s)
            else:
                product['sizes_display'] = sizes_list
                merged[key] = product
        products = list(merged.values())

        if category_slug:
            logger.info(f"📦 Found {len(products)} products in category {category_slug}")

        available_brands = []
        available_sizes = []
        available_colors = []
        filter_ids = allowed_ids if allowed_ids else None

        # Get available filters
        if filter_ids:
            placeholders = ",".join("?" * len(filter_ids))
            cursor.execute(f"""
                SELECT DISTINCT brand FROM products
                WHERE is_active = TRUE AND quantity > 0 AND brand IS NOT NULL AND brand != ''
                AND category_id IN ({placeholders})
            """, filter_ids)
            available_brands = [row[0] for row in cursor.fetchall()]

            cursor.execute(f"""
                SELECT DISTINCT COALESCE(s.value, p.size) AS size_value
                FROM products p
                LEFT JOIN sizes s ON p.size_id = s.id
                WHERE p.is_active = TRUE AND p.quantity > 0
                  AND COALESCE(s.value, p.size) IS NOT NULL AND COALESCE(s.value, p.size) != ''
                  AND p.category_id IN ({placeholders})
            """, filter_ids)
            sizes_raw = [row[0] for row in cursor.fetchall()]
            sizes_tokens = []
            for s in sizes_raw:
                sizes_tokens.extend(parse_sizes(s))
            available_sizes = sorted({t for t in sizes_tokens})

            cursor.execute(f"""
                SELECT DISTINCT color FROM products
                WHERE is_active = TRUE AND quantity > 0 AND color IS NOT NULL AND color != ''
                AND category_id IN ({placeholders})
            """, filter_ids)
            available_colors = [row[0] for row in cursor.fetchall()]
        else:
            # If no category selected, get filters from ALL active products
            cursor.execute("""
                SELECT DISTINCT brand FROM products
                WHERE is_active = TRUE AND quantity > 0 AND brand IS NOT NULL AND brand != ''
            """)
            available_brands = [row[0] for row in cursor.fetchall()]

            cursor.execute("""
                SELECT DISTINCT COALESCE(s.value, p.size) AS size_value
                FROM products p
                LEFT JOIN sizes s ON p.size_id = s.id
                WHERE p.is_active = TRUE AND p.quantity > 0
                  AND COALESCE(s.value, p.size) IS NOT NULL AND COALESCE(s.value, p.size) != ''
            """)
            sizes_raw = [row[0] for row in cursor.fetchall()]
            sizes_tokens = []
            for s in sizes_raw:
                sizes_tokens.extend(parse_sizes(s))
            available_sizes = sorted({t for t in sizes_tokens})

            cursor.execute("""
                SELECT DISTINCT color FROM products
                WHERE is_active = TRUE AND quantity > 0 AND color IS NOT NULL AND color != ''
            """)
            available_colors = [row[0] for row in cursor.fetchall()]

        active_filters = []
        if category_slug:
            category_name = next((c['name'] for c in category_rows if c['slug'] == category_slug), category_slug)
            active_filters.append({'label': 'Категория', 'value': category_name})
        if brand:
            active_filters.append({'label': 'Бренд', 'value': brand})
        if color:
            active_filters.append({'label': 'Цвет', 'value': color})
        if size:
            active_filters.append({'label': 'Размер', 'value': size})
        if price_min:
            active_filters.append({'label': 'Мин. цена', 'value': price_min})
        if price_max:
            active_filters.append({'label': 'Макс. цена', 'value': price_max})

        conn.close()

        context = {
            'products': products,
            'categories': categories,
            'product_count': len(products),
            'current_category': category_slug,
            'current_category_id': current_category_id,
            'current_parent_id': current_parent_id,
            'subcategories': subcategories,
            'active_filters': active_filters,
            'available_brands': available_brands,
            'available_sizes': available_sizes,
            'available_colors': available_colors,
            'current_brand': brand,
            'current_size': size,
            'current_color': color,
            'bag_count': get_cart_count(request),
            'current_year': datetime.now().year
        }

        return aiohttp_jinja2.render_template('catalog.html', request, context)
    except Exception as e:
        logger.error(f"Ошибка каталога: {e}")
        raise

categories = [
    {
        'id': 1,
        'name': 'Одежда',
        'slug': 'odezhda',
        'has_subcategories': True
    },
    {
        'id': 2,
        'name': 'Кроссовки',
        'slug': 'krossovki',
        'has_subcategories': False
    },
    {
        'id': 3,
        'name': 'Аксессуары',
        'slug': 'aksessuary',
        'has_subcategories': True
    }
]

subcategories = {
    1: [  # Для категории "Одежда" (ID: 1)
        {'id': 101, 'name': 'Футболки', 'slug': 'futbolki'},
        {'id': 102, 'name': 'Штаны', 'slug': 'shtany'},
        {'id': 103, 'name': 'Куртки', 'slug': 'kurtki'},
        {'id': 104, 'name': 'Шорты', 'slug': 'shorty'},
        {'id': 105, 'name': 'Кофты', 'slug': 'kofty'}
    ],
    3: [  # Для категории "Аксессуары" (ID: 3)
        {'id': 301, 'name': 'Сумки', 'slug': 'sumki'},
        {'id': 302, 'name': 'Очки', 'slug': 'ochki'},
        {'id': 303, 'name': 'Кепки и шапки', 'slug': 'kepki-shapki'},
        {'id': 304, 'name': 'Носки', 'slug': 'noski'},
        {'id': 305, 'name': 'Коллекционное', 'slug': 'kollektsionnoe'},
        {'id': 306, 'name': 'Другое', 'slug': 'drugoe'}
    ]
}
async def product_page(request):
    """Страница товара"""
    try:
        pid = request.match_info.get('id')
        conn = get_db_connection()
        cursor = conn.cursor()

        product = None
        if pid and str(pid).isdigit():
            cursor.execute("""
                SELECT p.id, p.name, p.price, p.compare_at_price, p.image_url, p.gallery, p.description,
                       p.discount_percent, p.brand, p.color, p.size, p.material, p.slug, p.quantity,
                       p.size_id, s.value AS size_value
                FROM products p
                LEFT JOIN sizes s ON p.size_id = s.id
                WHERE p.id = ?
            """, (int(pid),))
            row = cursor.fetchone()
            if row:
                product = format_product_row(row)
        if product is None and pid:
            cursor.execute("""
                SELECT p.id, p.name, p.price, p.compare_at_price, p.image_url, p.gallery, p.description,
                       p.discount_percent, p.brand, p.color, p.size, p.material, p.slug, p.quantity,
                       p.size_id, s.value AS size_value
                FROM products p
                LEFT JOIN sizes s ON p.size_id = s.id
                WHERE p.slug = ?
            """, (pid,))
            row = cursor.fetchone()
            if row:
                product = format_product_row(row)

        if not product:
            raise web.HTTPNotFound()

        product['sizes_display'] = parse_sizes(product.get('size'))
        gallery = []
        if product.get('gallery'):
            try:
                data = json.loads(product['gallery'])
                if isinstance(data, list):
                    gallery = data
            except Exception:
                gallery = []
        if product.get('image_url'):
            gallery = [product['image_url']] + [g for g in gallery if g != product['image_url']]

        context = {
            'product': product,
            'gallery': gallery,
            'bag_count': get_cart_count(request),
            'current_year': datetime.now().year
        }
        conn.close()
        return aiohttp_jinja2.render_template('product.html', request, context)
    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка страницы товара: {e}")
        raise web.HTTPNotFound()


async def cart_page(request):
    """Страница корзины"""
    try:
        items = parse_cart_cookie(request)
        cart_products = []
        if items:
            ids = [i['product_id'] for i in items]
            placeholders = ",".join("?" * len(ids))
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT p.id, p.name, p.price, p.compare_at_price, p.image_url, p.size, p.brand, p.slug,
                       p.size_id, s.value AS size_value
                FROM products p
                LEFT JOIN sizes s ON p.size_id = s.id
                WHERE p.id IN ({placeholders})
            """, ids)
            rows = cursor.fetchall()
            product_map = {row['id']: format_product_row(row) for row in rows}
            for p in product_map.values():
                p['sizes_display'] = parse_sizes(p.get('size'))
            for it in items:
                prod = product_map.get(it['product_id'])
                if prod:
                    prod = dict(prod)
                    prod['quantity'] = it['quantity']
                    prod['cart_size'] = it.get('size') or (prod.get('sizes_display') or [None])[0]
                    cart_products.append(prod)
            conn.close()

        total = sum((float(p.get('price', 0)) * p.get('quantity', 1)) for p in cart_products)
        total_formatted = f"{total:,.0f} RUB".replace(',', ' ')

        context = {
            'cart_products': cart_products,
            'total_formatted': total_formatted,
            'bag_count': get_cart_count(request),
            'current_year': datetime.now().year
        }
        return aiohttp_jinja2.render_template('cart.html', request, context)
    except Exception as e:
        logger.error(f"Ошибка корзины: {e}")
        raise web.HTTPNotFound()


async def checkout_page(request):
    """Страница оформления заказа"""
    return await serve_static(request)


async def gift_page(request):
    """Страница покупки подарочного сертификата"""
    context = {
        'current_year': datetime.now().year,
        'bag_count': get_cart_count(request)
    }
    return aiohttp_jinja2.render_template('gift.html', request, context)


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
    app.router.add_get('/gift', gift_page)

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
