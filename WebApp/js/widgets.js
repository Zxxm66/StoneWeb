// Widget Renderer
class WidgetRenderer {
    constructor() {
        this.widgets = [];
    }

    async loadWidgets() {
        try {
            const response = await fetch('/api/widgets');
            const data = await response.json();

            if (data.success) {
                this.widgets = data.widgets;
                this.render();
            }
        } catch (error) {
            console.error('Error loading widgets:', error);
        }
    }

    render() {
        const container = document.getElementById('widgets-container');
        if (!container) return;

        container.innerHTML = '';

        this.widgets.forEach((widget, index) => {
            const widgetElement = this.createWidget(widget, index);
            container.appendChild(widgetElement);
        });

        // Активируем анимации
        setTimeout(() => {
            document.querySelectorAll('.widget').forEach((el, i) => {
                setTimeout(() => {
                    el.style.opacity = '1';
                    el.style.transform = 'translateY(0)';
                }, i * 200);
            });
        }, 100);
    }

    createWidget(widget, index) {
        const div = document.createElement('div');
        div.className = `widget fade-in delay-${index % 3}`;
        div.style.opacity = '0';
        div.style.transform = 'translateY(20px)';
        div.style.transition = 'opacity 0.8s ease, transform 0.8s ease';

        switch(widget.widget_type) {
            case 'marquee':
                div.innerHTML = this.createMarqueeWidget(widget);
                break;
            case 'hero':
                div.innerHTML = this.createHeroWidget(widget);
                break;
            case 'info':
                div.innerHTML = this.createInfoWidget(widget);
                break;
            case 'collection':
                div.innerHTML = this.createCollectionWidget(widget);
                break;
            default:
                div.innerHTML = this.createDefaultWidget(widget);
        }

        return div;
    }

    createMarqueeWidget(widget) {
        const config = widget.config || {};
        return `
            <section class="marquee-widget" style="
                background: ${config.bgColor || '#000'};
                color: ${config.color || '#fff'};
            ">
                <div class="marquee-content" style="
                    font-size: ${config.fontSize || '11px'};
                    animation-duration: ${config.speed || 20}s;
                ">
                    ${widget.content || ''}
                </div>
            </section>
        `;
    }

    createHeroWidget(widget) {
        return `
            <section class="hero-widget">
                <div class="hero-content">
                    <h1 class="hero-title balenciaga-heading">
                        ${widget.title || 'STONE'}
                    </h1>
                    <p class="hero-subtitle balenciaga-subheading">
                        ${widget.content || 'PREMIUM SNEAKERS'}
                    </p>
                    <a href="/catalog" class="hero-cta">SHOP NOW</a>
                </div>
            </section>
        `;
    }

    createInfoWidget(widget) {
        return `
            <section class="info-widget">
                <h2 class="info-title balenciaga-subheading">
                    ${widget.title || 'INFORMATION'}
                </h2>
                <p class="info-content">
                    ${widget.content || ''}
                </p>
            </section>
        `;
    }

    createCollectionWidget(widget) {
        return `
            <section class="collection-widget">
                <h2 class="collection-title balenciaga-heading">
                    ${widget.title || 'NEW COLLECTION'}
                </h2>
                <p class="collection-description">
                    ${widget.content || 'Explore our carefully curated selection of premium sneakers.'}
                </p>
                <a href="/catalog" class="collection-link">VIEW COLLECTION</a>
            </section>
        `;
    }

    createDefaultWidget(widget) {
        return `
            <section class="widget-default">
                <h2>${widget.title || 'Widget'}</h2>
                <p>${widget.content || ''}</p>
            </section>
        `;
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    const renderer = new WidgetRenderer();
    renderer.loadWidgets();
});