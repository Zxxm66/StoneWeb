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
        
        # Добавляем тестовые виджеты если таблица пуста
        cursor.execute("SELECT COUNT(*) FROM web_widgets")
        if cursor.fetchone()[0] == 0:
            test_widgets = [
                ('marquee', None, 'STONE | PREMIUM SNEAKERS | BETWEEN 11/20/2025 AND 12/15/2025 MAY BE RETURNED', '{"speed": 20, "color": "#ffffff", "bgColor": "#000000"}', 1, 0),
                ('hero', 'STONE', 'between 11/20/2025 and 12/15/2025 may be returned', '{}', 2, 0),
                ('info', 'INFORMATION #LINDON', 'money model options, four, savings', '{}', 3, 0),
                ('collection', 'New Collection', 'Explore our carefully curated selection of premium sneakers. Each pair is designed with meticulous attention to detail and crafted from the finest materials.', '{}', 4, 0)
            ]
            
            cursor.executemany("""
                INSERT INTO web_widgets (widget_type, title, content, config, position, sort_order)
                VALUES (?, ?, ?, ?, ?, ?)
            """, test_widgets)
            logger.info("✅ Добавлены тестовые виджеты")
        
        conn.commit()
        logger.info("✅ База данных магазина инициализирована")
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        conn.rollback()
    finally:
        conn.close()