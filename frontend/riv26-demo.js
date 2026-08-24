// re:Invent 2026 Interactive Demo launcher for Amazon WorkSpaces Community Hub
// Opens the self-contained demo bundle (riv26demo/) in a full-screen overlay.
// The demo ships its own CSS/JS, so it runs inside an iframe to keep it fully
// isolated from styles-console.css.

class Riv26Demo {
    constructor(demoUrl = 'riv26demo/index.html') {
        this.demoUrl = demoUrl;
        this.container = null;
        this.iframe = null;
        this.loaded = false;
    }

    init() {
        this.createOverlay();
        this.setupTriggerButton();
        this.setupKeyboardListeners();
    }

    createOverlay() {
        const container = document.createElement('div');
        container.className = 'riv26-demo-container';
        container.id = 'riv26DemoContainer';
        container.innerHTML = `
            <div class="riv26-demo-bar">
                <div class="riv26-demo-bar-actions">
                    <button class="riv26-demo-restart" id="riv26DemoRestartBtn" title="Restart the demo from the beginning">&#8635; Restart</button>
                    <button class="riv26-demo-close" id="riv26DemoCloseBtn" title="Close (ESC)">&#10005; Close</button>
                </div>
            </div>
            <div class="riv26-demo-frame-wrap">
                <iframe class="riv26-demo-frame" id="riv26DemoFrame" title="re:Invent 2026 Interactive Demo"></iframe>
            </div>
        `;
        document.body.appendChild(container);

        this.container = container;
        this.iframe = container.querySelector('#riv26DemoFrame');

        container.querySelector('#riv26DemoCloseBtn').addEventListener('click', () => this.close());
        container.querySelector('#riv26DemoRestartBtn').addEventListener('click', () => this.restart());

        // The demo owns arrow keys and Escape inside its own document, so bind a
        // parallel Escape handler there once it loads. Same-origin, so reachable.
        this.iframe.addEventListener('load', () => this.bindFrameEscape());
    }

    setupTriggerButton() {
        // Button lives statically in index-staging.html so it renders for signed-out
        // users too, and so the injected "Proposals" dropdown lands to its left.
        const btn = document.getElementById('riv26DemoBtn');
        if (!btn) return;
        btn.addEventListener('click', () => this.toggle());
    }

    setupKeyboardListeners() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen()) {
                this.close();
            }
        });
    }

    bindFrameEscape() {
        try {
            const doc = this.iframe.contentDocument;
            if (!doc) return;
            doc.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') this.close();
            });
        } catch (e) {
            // Cross-origin or not yet available; the Close button still works.
        }
    }

    isOpen() {
        return !!this.container && this.container.classList.contains('active');
    }

    toggle() {
        if (this.isOpen()) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        if (!this.container) return;
        // Load the bundle on first open so the 280 KB of demo assets never cost
        // the hub's initial page load.
        if (!this.loaded) {
            this.iframe.src = this.demoUrl;
            this.loaded = true;
        }
        this.container.classList.add('active');
        document.body.classList.add('riv26-demo-open');
        this.iframe.focus();
    }

    close() {
        if (!this.container) return;
        this.container.classList.remove('active');
        document.body.classList.remove('riv26-demo-open');
    }

    restart() {
        if (!this.iframe) return;
        this.iframe.src = this.demoUrl;
        this.loaded = true;
        this.iframe.focus();
    }
}

// Initialize re:Invent 2026 demo launcher
document.addEventListener('DOMContentLoaded', () => {
    window.riv26Demo = new Riv26Demo();
    window.riv26Demo.init();
});
