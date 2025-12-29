// Stone Store - Main Application
class StoneStore {
    constructor() {
        this.cart = this.loadCart();
        this.favorites = this.loadFavorites();
        this.currentPage = window.location.pathname;
        this.init();
    }

    async init() {
        console.log('Stone Store initialized');

        // Initialize Telegram WebApp
        if (window.TelegramApp) {
            await window.TelegramApp.init();
        }

        // Load initial data
        await this.loadInitialData();

        // Setup event listeners
        this.setupEventListeners();

        // Update cart UI
        this.updateCartUI();

        // Setup router
        this.setupRouter();
    }

    async loadInitialData() {
        try {
            // Load products
            const productsResponse = await fetch('/api/products');
            if (productsResponse.ok) {
                const data = await productsResponse.json();
                if (data.success) {
                    this.products = data.products;
                    this.categories = data.categories;
                    this.brands = data.brands;
                    console.log('Products loaded:', this.products.length);
                }
            }

            // Load widgets for home page
            if (this.currentPage === '/' || this.currentPage === '/webapp/') {
                await this.loadHomeWidgets();
            }
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }

    async loadHomeWidgets() {
        try {
            const response = await fetch('/api/widgets');
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.widgets) {
                    this.renderWidgets(data.widgets);
                }
            }
        } catch (error) {
            console.error('Error loading widgets:', error);
        }
    }

    renderWidgets(widgets) {
        const container = document.getElementById('page-content');
        if (!container) return;

        let html = '<div class="home-page">';

        widgets.forEach(widget => {
            html += this.renderWidget(widget);
        });

        html += '</div>';
        container.innerHTML = html;
    }

    renderWidget(widget) {
        const config = widget.config || {};

        switch(widget.widget_type) {
            case 'hero':
                return `
                    <section class="balenciaga-hero fade-in">
                        <div class="hero-content">
                            <h1 class="hero-title balenciaga-heading">
                                ${widget.title || 'STONE'}
                            </h1>
                            <p class="hero-subtitle balenciaga-subheading">
                                ${widget.content || 'PREMIUM SNEAKERS'}
                            </p>
                            <a href="/catalog" class="hero-cta">
                                SHOP COLLECTION
                            </a>
                        </div>
                    </section>
                `;

            case 'marquee':
                return `
                    <div class="marquee-container" style="
                        background: ${config.bgColor || '#000'};
                        color: ${config.color || '#fff'};
                        padding: 16px 0;
                        overflow: hidden;
                        border-top: 1px solid rgba(255,255,255,0.1);
                        border-bottom: 1px solid rgba(255,255,255,0.1);
                    ">
                        <div class="marquee-content" style="
                            display: inline-block;
                            white-space: nowrap;
                            animation: marquee ${config.speed || 20}s linear infinite;
                            font-size: 12px;
                            letter-spacing: 0.2em;
                        ">
                            ${widget.content || ''}
                        </div>
                        <style>
                            @keyframes marquee {
                                0% { transform: translateX(100%); }
                                100% { transform: translateX(-100%); }
                            }
                        </style>
                    </div>
                `;

            case 'collection':
                return `
                    <section class="collection-section p-48 fade-in delay-1">
                        <h2 class="balenciaga-heading text-center mb-24">
                            ${widget.title || 'NEW COLLECTION'}
                        </h2>
                        <p class="text-center text-muted mb-48" style="max-width: 600px; margin: 0 auto;">
                            ${widget.content || 'Explore our carefully curated selection of premium sneakers.'}
                        </p>
                        <div class="product-grid">
                            ${this.renderFeaturedProducts()}
                        </div>
                    </section>
                `;

            default:
                return `
                    <section class="widget p-24 fade-in">
                        <h2>${widget.title || 'Widget'}</h2>
                        <p>${widget.content || ''}</p>
                    </section>
                `;
        }
    }

    renderFeaturedProducts() {
        if (!this.products || this.products.length === 0) {
            return '<p class="text-center text-muted">No products available</p>';
        }

        return this.products.slice(0, 4).map(product => `
            <div class="product-card fade-in" data-id="${product.id}">
                ${product.discount_percent ? `
                    <div class="discount-badge">-${product.discount_percent}%</div>
                ` : ''}
                <div class="product-image">
                    ${product.main_image ? `
                        <img src="${product.main_image}" alt="${product.name}"
                             onerror="this.style.display='none'; this.parentNode.style.background='#1A1A1A'">
                    ` : ''}
                </div>
                <div class="product-info">
                    <div class="product-brand">${product.brand || 'STONE'}</div>
                    <div class="product-name">${product.name}</div>
                    <div class="product-price">
                        ${product.discount_price_formatted ? `
                            <span class="original-price">${product.price_formatted}₽</span>
                            <span>${product.discount_price_formatted}₽</span>
                        ` : `
                            <span>${product.price_formatted}₽</span>
                        `}
                    </div>
                </div>
            </div>
        `).join('');
    }

    // Cart management
    loadCart() {
        try {
            const cart = localStorage.getItem('stone_cart');
            return cart ? JSON.parse(cart) : { items: [], total: 0 };
        } catch (error) {
            console.error('Error loading cart:', error);
            return { items: [], total: 0 };
        }
    }

    saveCart() {
        try {
            localStorage.setItem('stone_cart', JSON.stringify(this.cart));
            this.updateCartUI();

            // Update Telegram button
            if (window.TelegramApp) {
                window.TelegramApp.updateCart(this.cart);
            }
        } catch (error) {
            console.error('Error saving cart:', error);
        }
    }

    addToCart(product, quantity = 1) {
        const existingItem = this.cart.items.find(item => item.id === product.id);

        if (existingItem) {
            existingItem.quantity += quantity;
        } else {
            this.cart.items.push({
                id: product.id,
                name: product.name,
                price: product.discount_price || product.price,
                originalPrice: product.price,
                image: product.main_image,
                quantity: quantity,
                brand: product.brand
            });
        }

        this.calculateCartTotal();
        this.saveCart();

        // Show notification
        this.showNotification(`Added to cart: ${product.name}`);
    }

    removeFromCart(productId) {
        this.cart.items = this.cart.items.filter(item => item.id !== productId);
        this.calculateCartTotal();
        this.saveCart();
    }

    updateQuantity(productId, quantity) {
        const item = this.cart.items.find(item => item.id === productId);
        if (item) {
            item.quantity = Math.max(1, quantity);
            this.calculateCartTotal();
            this.saveCart();
        }
    }

    calculateCartTotal() {
        this.cart.total = this.cart.items.reduce((sum, item) => {
            return sum + (item.price * item.quantity);
        }, 0);
    }

    clearCart() {
        this.cart = { items: [], total: 0 };
        this.saveCart();
    }

    // Favorites
    loadFavorites() {
        try {
            const favs = localStorage.getItem('stone_favorites');
            return favs ? JSON.parse(favs) : [];
        } catch (error) {
            console.error('Error loading favorites:', error);
            return [];
        }
    }

    saveFavorites() {
        try {
            localStorage.setItem('stone_favorites', JSON.stringify(this.favorites));
        } catch (error) {
            console.error('Error saving favorites:', error);
        }
    }

    toggleFavorite(productId) {
        const index = this.favorites.indexOf(productId);
        if (index > -1) {
            this.favorites.splice(index, 1);
        } else {
            this.favorites.push(productId);
        }
        this.saveFavorites();
    }

    isFavorite(productId) {
        return this.favorites.includes(productId);
    }

    // UI Updates
    updateCartUI() {
        const cartCount = this.cart.items.reduce((sum, item) => sum + item.quantity, 0);
        const cartElements = document.querySelectorAll('.cart-count, .nav-cart');

        cartElements.forEach(el => {
            if (el.classList.contains('cart-count')) {
                el.textContent = cartCount;
                el.style.display = cartCount > 0 ? 'inline' : 'none';
            }
        });
    }

    showNotification(message, duration = 3000) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'stone-notification';
        notification.innerHTML = `
            <div style="
                position: fixed;
                bottom: 24px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(20px);
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                z-index: 9999;
                font-size: 14px;
                animation: slideUp 0.3s ease;
            ">
                ${message}
            </div>
        `;

        document.body.appendChild(notification);

        // Remove after duration
        setTimeout(() => {
            notification.style.animation = 'slideDown 0.3s ease';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, duration);

        // Add animation styles
        if (!document.querySelector('#notification-styles')) {
            const style = document.createElement('style');
            style.id = 'notification-styles';
            style.textContent = `
                @keyframes slideUp {
                    from { transform: translate(-50%, 100%); opacity: 0; }
                    to { transform: translate(-50%, 0); opacity: 1; }
                }
                @keyframes slideDown {
                    from { transform: translate(-50%, 0); opacity: 1; }
                    to { transform: translate(-50%, 100%); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
    }

    // Routing
    setupRouter() {
        // Handle internal links
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (link && link.href && link.href.startsWith(window.location.origin)) {
                e.preventDefault();
                const path = new URL(link.href).pathname;
                this.navigateTo(path);
            }
        });

        // Handle browser back/forward
        window.addEventListener('popstate', () => {
            this.navigateTo(window.location.pathname, false);
        });
    }

    async navigateTo(path, pushState = true) {
        this.currentPage = path;

        if (pushState) {
            window.history.pushState({}, '', path);
        }

        // Show loading state
        const content = document.getElementById('page-content');
        if (content) {
            content.innerHTML = `
                <div class="loading-page">
                    <div style="text-align: center; padding: 80px 24px;">
                        <div class="loading-bar" style="width: 200px; margin: 0 auto;"></div>
                    </div>
                </div>
            `;
        }

        // Load page content
        await this.loadPageContent(path);
    }

    async loadPageContent(path) {
        const content = document.getElementById('page-content');
        if (!content) return;

        try {
            // Simple page routing
            if (path === '/' || path === '/webapp/') {
                await this.loadHomePage();
            } else if (path === '/catalog') {
                await this.loadCatalogPage();
            } else if (path === '/cart') {
                await this.loadCartPage();
            } else if (path.startsWith('/product/')) {
                const productId = path.split('/product/')[1];
                await this.loadProductPage(productId);
            } else {
                content.innerHTML = `
                    <div class="page-not-found" style="text-align: center; padding: 80px 24px;">
                        <h1 style="font-size: 48px; margin-bottom: 16px;">404</h1>
                        <p style="opacity: 0.7; margin-bottom: 24px;">Page not found</p>
                        <a href="/" style="color: white; text-decoration: underline;">Go Home</a>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading page:', error);
            content.innerHTML = `
                <div style="text-align: center; padding: 80px 24px; color: #ff3b30;">
                    <p>Error loading page. Please try again.</p>
                </div>
            `;
        }
    }

    async loadHomePage() {
        await this.loadHomeWidgets();
    }

    async loadCatalogPage() {
        const content = document.getElementById('page-content');
        if (!content) return;

        try {
            // Fetch products if not loaded
            if (!this.products) {
                await this.loadInitialData();
            }

            content.innerHTML = `
                <div class="catalog-page">
                    <div style="padding: 48px 24px;">
                        <h1 class="balenciaga-heading" style="font-size: 48px; margin-bottom: 16px;">
                            CATALOG
                        </h1>
                        <p class="text-muted" style="margin-bottom: 48px;">
                            ${this.products ? this.products.length : 0} items available
                        </p>
                        <div class="product-grid">
                            ${this.products ? this.products.map(product => `
                                <div class="product-card" data-id="${product.id}"
                                     onclick="window.stoneStore.navigateTo('/product/${product.id}')">
                                    ${product.discount_percent ? `
                                        <div class="discount-badge">-${product.discount_percent}%</div>
                                    ` : ''}
                                    <div class="product-image">
                                        ${product.main_image ? `
                                            <img src="${product.main_image}" alt="${product.name}">
                                        ` : ''}
                                    </div>
                                    <div class="product-info">
                                        <div class="product-brand">${product.brand || 'STONE'}</div>
                                        <div class="product-name">${product.name}</div>
                                        <div class="product-price">
                                            ${product.discount_price_formatted ? `
                                                <span class="original-price">${product.price_formatted}₽</span>
                                                <span>${product.discount_price_formatted}₽</span>
                                            ` : `
                                                <span>${product.price_formatted}₽</span>
                                            `}
                                        </div>
                                    </div>
                                </div>
                            `).join('') : ''}
                        </div>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Error loading catalog:', error);
            content.innerHTML = '<p>Error loading products</p>';
        }
    }

    async loadCartPage() {
        const content = document.getElementById('page-content');
        if (!content) return;

        if (this.cart.items.length === 0) {
            content.innerHTML = `
                <div style="text-align: center; padding: 80px 24px;">
                    <h1 style="font-size: 48px; margin-bottom: 16px;">CART</h1>
                    <p style="opacity: 0.7; margin-bottom: 24px;">Your cart is empty</p>
                    <a href="/catalog" style="
                        display: inline-block;
                        padding: 12px 24px;
                        background: white;
                        color: black;
                        text-decoration: none;
                        font-weight: 600;
                    ">
                        SHOP NOW
                    </a>
                </div>
            `;
            return;
        }

        content.innerHTML = `
            <div class="cart-page" style="padding: 24px;">
                <h1 style="font-size: 32px; margin-bottom: 24px;">CART</h1>
                <div class="cart-items">
                    ${this.cart.items.map(item => `
                        <div class="cart-item" style="
                            display: flex;
                            gap: 16px;
                            padding: 16px 0;
                            border-bottom: 1px solid rgba(255,255,255,0.1);
                        ">
                            <div style="width: 80px; height: 80px; background: #1A1A1A;">
                                ${item.image ? `<img src="${item.image}" alt="${item.name}" style="width: 100%; height: 100%; object-fit: cover;">` : ''}
                            </div>
                            <div style="flex-grow: 1;">
                                <div style="font-size: 12px; opacity: 0.7; margin-bottom: 4px;">
                                    ${item.brand || 'STONE'}
                                </div>
                                <div style="font-weight: 500; margin-bottom: 8px;">${item.name}</div>
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <button onclick="window.stoneStore.updateQuantity(${item.id}, ${item.quantity - 1})"
                                                style="background: none; border: 1px solid rgba(255,255,255,0.2); color: white; width: 24px; height: 24px; border-radius: 50%;">
                                            -
                                        </button>
                                        <span>${item.quantity}</span>
                                        <button onclick="window.stoneStore.updateQuantity(${item.id}, ${item.quantity + 1})"
                                                style="background: none; border: 1px solid rgba(255,255,255,0.2); color: white; width: 24px; height: 24px; border-radius: 50%;">
                                            +
                                        </button>
                                    </div>
                                    <div style="font-weight: 600;">${(item.price * item.quantity).toLocaleString()}₽</div>
                                </div>
                            </div>
                            <button onclick="window.stoneStore.removeFromCart(${item.id})"
                                    style="background: none; border: none; color: rgba(255,255,255,0.5); font-size: 20px;">
                                ×
                            </button>
                        </div>
                    `).join('')}
                </div>
                <div style="padding: 24px 0; border-top: 1px solid rgba(255,255,255,0.1);">
                    <div style="display: flex; justify-content: space-between; font-size: 18px; font-weight: 600; margin-bottom: 24px;">
                        <span>TOTAL</span>
                        <span>${this.cart.total.toLocaleString()}₽</span>
                    </div>
                    <button onclick="window.stoneStore.checkout()" style="
                        width: 100%;
                        padding: 16px;
                        background: white;
                        color: black;
                        border: none;
                        font-weight: 600;
                        text-transform: uppercase;
                        letter-spacing: 0.1em;
                    ">
                        PROCEED TO CHECKOUT
                    </button>
                </div>
            </div>
        `;
    }

    async loadProductPage(productId) {
        const content = document.getElementById('page-content');
        if (!content) return;

        try {
            // Fetch product details
            const product = this.products?.find(p => p.id == productId);

            if (!product) {
                content.innerHTML = '<p>Product not found</p>';
                return;
            }

            content.innerHTML = `
                <div class="product-page">
                    <div style="max-width: 1200px; margin: 0 auto; padding: 24px;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 48px;">
                            <!-- Product Images -->
                            <div class="product-images">
                                <div style="background: #1A1A1A; height: 500px; margin-bottom: 16px;">
                                    ${product.main_image ? `
                                        <img src="${product.main_image}" alt="${product.name}"
                                             style="width: 100%; height: 100%; object-fit: cover;">
                                    ` : ''}
                                </div>
                            </div>

                            <!-- Product Info -->
                            <div class="product-details">
                                <div style="margin-bottom: 8px; font-size: 12px; letter-spacing: 0.2em; opacity: 0.7;">
                                    ${product.brand || 'STONE'}
                                </div>
                                <h1 style="font-size: 32px; font-weight: 700; margin-bottom: 16px;">
                                    ${product.name}
                                </h1>
                                <div style="margin-bottom: 24px;">
                                    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                                        ${product.discount_price_formatted ? `
                                            <span style="font-size: 24px; font-weight: 600;">
                                                ${product.discount_price_formatted}₽
                                            </span>
                                            <span style="text-decoration: line-through; opacity: 0.5;">
                                                ${product.price_formatted}₽
                                            </span>
                                            <span style="background: #ff3b30; color: white; padding: 2px 8px; font-size: 12px; font-weight: 600;">
                                                -${product.discount_percent}%
                                            </span>
                                        ` : `
                                            <span style="font-size: 24px; font-weight: 600;">
                                                ${product.price_formatted}₽
                                            </span>
                                        `}
                                    </div>

                                    ${product.quantity > 0 ? `
                                        <div style="color: #4CAF50; font-size: 14px; margin-bottom: 16px;">
                                            ✓ In stock (${product.quantity} available)
                                        </div>
                                    ` : `
                                        <div style="color: #ff3b30; font-size: 14px; margin-bottom: 16px;">
                                            ✗ Out of stock
                                        </div>
                                    `}

                                    <div style="margin-bottom: 32px;">
                                        <button onclick="window.stoneStore.addToCart(${JSON.stringify(product).replace(/"/g, '&quot;')})"
                                                style="
                                                    width: 100%;
                                                    padding: 16px;
                                                    background: white;
                                                    color: black;
                                                    border: none;
                                                    font-weight: 600;
                                                    text-transform: uppercase;
                                                    letter-spacing: 0.1em;
                                                    margin-bottom: 12px;
                                                "
                                                ${product.quantity <= 0 ? 'disabled style="opacity: 0.5; cursor: not-allowed;"' : ''}>
                                            ADD TO CART
                                        </button>
                                        <button onclick="window.stoneStore.toggleFavorite(${product.id})"
                                                style="
                                                    width: 100%;
                                                    padding: 16px;
                                                    background: none;
                                                    color: white;
                                                    border: 1px solid rgba(255,255,255,0.2);
                                                    font-weight: 600;
                                                    text-transform: uppercase;
                                                    letter-spacing: 0.1em;
                                                ">
                                            ${this.isFavorite(product.id) ? '♥ REMOVE FROM FAVORITES' : '♡ ADD TO FAVORITES'}
                                        </button>
                                    </div>

                                    <div style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 24px;">
                                        <h3 style="font-size: 14px; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px;">
                                            Description
                                        </h3>
                                        <p style="opacity: 0.7; line-height: 1.6;">
                                            Premium sneakers from our latest collection.
                                            Crafted with attention to detail and using the finest materials.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Error loading product:', error);
            content.innerHTML = '<p>Error loading product details</p>';
        }
    }

    // Checkout
    async checkout() {
        if (this.cart.items.length === 0) {
            this.showNotification('Your cart is empty');
            return;
        }

        try {
            if (window.TelegramApp && window.TelegramApp.isInitialized) {
                // Use Telegram WebApp checkout
                const orderData = {
                    action: 'create_order',
                    cart: this.cart,
                    user: window.TelegramApp.getUserId(),
                    timestamp: Date.now()
                };

                window.TelegramApp.sendData(JSON.stringify(orderData));
                this.showNotification('Processing your order...');
            } else {
                // Fallback to regular checkout
                const response = await fetch('/api/checkout', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        cart: this.cart,
                        user: this.getUserInfo()
                    })
                });

                if (response.ok) {
                    const result = await response.json();
                    if (result.success) {
                        this.showNotification('Order placed successfully!');
                        this.clearCart();
                        this.navigateTo('/');
                    }
                }
            }
        } catch (error) {
            console.error('Checkout error:', error);
            this.showNotification('Checkout failed. Please try again.');
        }
    }

    getUserInfo() {
        if (window.TelegramApp && window.TelegramApp.user) {
            return window.TelegramApp.user;
        }

        // Fallback to localStorage or prompt
        let user = localStorage.getItem('stone_user');
        if (!user) {
            user = {
                id: 'guest_' + Math.random().toString(36).substr(2, 9),
                first_name: 'Guest',
                username: 'guest'
            };
            localStorage.setItem('stone_user', JSON.stringify(user));
        } else {
            user = JSON.parse(user);
        }

        return user;
    }

    // Event listeners
    setupEventListeners() {
        // Cart toggle
        document.addEventListener('click', (e) => {
            if (e.target.closest('.nav-cart')) {
                this.navigateTo('/cart');
            }
        });

        // Search
        document.addEventListener('click', (e) => {
            if (e.target.closest('.nav-search')) {
                this.showSearch();
            }
        });
    }

    showSearch() {
        const searchHTML = `
            <div id="search-overlay" style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.95);
                z-index: 9999;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 24px;
            ">
                <div style="position: absolute; top: 24px; right: 24px;">
                    <button onclick="document.getElementById('search-overlay').remove()"
                            style="background: none; border: none; color: white; font-size: 24px;">
                        ×
                    </button>
                </div>

                <h2 style="font-size: 48px; font-weight: 900; margin-bottom: 24px;">SEARCH</h2>
                <input type="text" placeholder="ENTER SEARCH TERM..." style="
                    width: 100%;
                    max-width: 500px;
                    padding: 16px;
                    background: none;
                    border: none;
                    border-bottom: 2px solid rgba(255,255,255,0.2);
                    color: white;
                    font-size: 24px;
                    text-align: center;
                    outline: none;
                " id="search-input">

                <div id="search-results" style="margin-top: 48px; max-width: 800px;"></div>
            </div>
        `;

        const overlay = document.createElement('div');
        overlay.innerHTML = searchHTML;
        document.body.appendChild(overlay);

        // Focus input
        setTimeout(() => {
            const input = document.getElementById('search-input');
            if (input) {
                input.focus();

                // Add input event listener
                input.addEventListener('input', (e) => {
                    this.handleSearch(e.target.value);
                });
            }
        }, 100);
    }

    handleSearch(query) {
        const resultsContainer = document.getElementById('search-results');
        if (!resultsContainer || !query.trim()) {
            resultsContainer.innerHTML = '';
            return;
        }

        // Simple search
        const filtered = this.products?.filter(product =>
            product.name.toLowerCase().includes(query.toLowerCase()) ||
            product.brand?.toLowerCase().includes(query.toLowerCase())
        ) || [];

        resultsContainer.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 24px;">
                ${filtered.map(product => `
                    <div onclick="window.stoneStore.navigateTo('/product/${product.id}');
                                 document.getElementById('search-overlay').remove()"
                         style="cursor: pointer;">
                        <div style="background: #1A1A1A; height: 200px; margin-bottom: 12px;">
                            ${product.main_image ? `
                                <img src="${product.main_image}" alt="${product.name}"
                                     style="width: 100%; height: 100%; object-fit: cover;">
                            ` : ''}
                        </div>
                        <div style="font-size: 12px; opacity: 0.7;">${product.brand || 'STONE'}</div>
                        <div style="font-weight: 500;">${product.name}</div>
                        <div style="font-weight: 600;">${product.price_formatted}₽</div>
                    </div>
                `).join('')}
            </div>
        `;
    }
}

// Initialize store
document.addEventListener('DOMContentLoaded', () => {
    window.stoneStore = new StoneStore();
});

// Export for modules
export default StoneStore;