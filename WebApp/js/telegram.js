// Telegram WebApp Integration
class TelegramWebApp {
    constructor() {
        this.tg = window.Telegram?.WebApp;
        this.isInitialized = false;
        this.user = null;
        this.initData = null;
    }

    async init() {
        if (!this.tg) {
            console.warn('Telegram WebApp SDK not loaded');
            return false;
        }

        try {
            // Expand to full screen
            this.tg.expand();
            this.tg.ready();

            // Set up theme
            this.setupTheme();

            // Get user data
            this.user = this.tg.initDataUnsafe?.user;
            this.initData = this.tg.initData;

            // Set up back button
            this.setupBackButton();

            // Set up main button
            this.setupMainButton();

            this.isInitialized = true;

            console.log('Telegram WebApp initialized:', {
                platform: this.tg.platform,
                colorScheme: this.tg.colorScheme,
                user: this.user
            });

            return true;
        } catch (error) {
            console.error('Failed to initialize Telegram WebApp:', error);
            return false;
        }
    }

    setupTheme() {
        const theme = this.tg.colorScheme;
        document.documentElement.setAttribute('data-theme', theme || 'dark');

        // Listen for theme changes
        this.tg.onEvent('themeChanged', () => {
            document.documentElement.setAttribute('data-theme', this.tg.colorScheme);
        });
    }

    setupBackButton() {
        if (this.tg.BackButton) {
            this.tg.BackButton.onClick(() => {
                window.history.back();
            });

            this.tg.BackButton.show();
        }
    }

    setupMainButton() {
        if (this.tg.MainButton) {
            this.tg.MainButton.setText('CHECKOUT');
            this.tg.MainButton.setParams({
                color: '#FFFFFF',
                text_color: '#000000'
            });

            this.tg.MainButton.onClick(() => {
                this.tg.sendData(JSON.stringify({
                    action: 'checkout',
                    timestamp: Date.now()
                }));
            });
        }
    }

    showMainButton() {
        if (this.tg?.MainButton) {
            this.tg.MainButton.show();
        }
    }

    hideMainButton() {
        if (this.tg?.MainButton) {
            this.tg.MainButton.hide();
        }
    }

    showAlert(message) {
        if (this.tg?.showAlert) {
            this.tg.showAlert(message);
        } else {
            alert(message);
        }
    }

    showConfirm(message, callback) {
        if (this.tg?.showConfirm) {
            this.tg.showConfirm(message, callback);
        } else {
            if (confirm(message)) {
                callback(true);
            }
        }
    }

    close() {
        if (this.tg?.close) {
            this.tg.close();
        }
    }

    getUserId() {
        return this.user?.id;
    }

    getUsername() {
        return this.user?.username;
    }

    getFirstName() {
        return this.user?.first_name;
    }

    sendData(data) {
        if (this.tg?.sendData) {
            this.tg.sendData(data);
        }
    }

    // Cart management
    updateCart(cart) {
        if (this.tg?.MainButton) {
            if (cart && cart.items && cart.items.length > 0) {
                this.tg.MainButton.setText(`CHECKOUT (${cart.total}₽)`);
                this.tg.MainButton.show();
            } else {
                this.tg.MainButton.hide();
            }
        }
    }
}

// Create global instance
window.TelegramApp = new TelegramWebApp();

// Initialize when Telegram SDK is ready
if (window.Telegram?.WebApp) {
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(() => {
            window.TelegramApp.init();
        }, 100);
    });
}

// Export for modules
export default TelegramWebApp;