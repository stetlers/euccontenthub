// Cart UI Module for EUC Content Hub
// Handles cart button, badge, and panel display

class CartUI {
    constructor(cartManager, allPosts) {
        this.cartManager = cartManager;
        this.allPosts = allPosts;
        this.isPanelOpen = false;
        
        this.init();
    }
    
    init() {
        // Create cart button
        this.createCartButton();
        
        // Create cart panel
        this.createCartPanel();
        
        // Listen for cart changes
        this.cartManager.addListener((event, data) => {
            this.updateBadge();
            if (this.isPanelOpen) {
                this.renderCartItems();
            }
        });
        
        // Initial badge update
        this.updateBadge();
    }
    
    createCartButton() {
        const button = document.createElement('button');
        button.id = 'cart-button';
        button.className = 'cart-floating-btn';
        button.innerHTML = `
            <span class="cart-icon">🛒</span>
            <span class="cart-badge" id="cart-badge">0</span>
        `;
        button.title = 'View Cart';
        button.addEventListener('click', () => this.togglePanel());
        
        document.body.appendChild(button);
    }
    
    createCartPanel() {
        const panel = document.createElement('div');
        panel.id = 'cart-panel';
        panel.className = 'cart-panel';
        panel.innerHTML = `
            <div class="cart-panel-header">
                <h2>🛒 My Cart</h2>
                <button class="cart-close-btn" id="cart-close-btn">×</button>
            </div>
            <div class="cart-panel-body" id="cart-panel-body">
                <!-- Cart items will be rendered here -->
            </div>
            <div class="cart-panel-footer">
                <button class="cart-clear-btn" id="cart-clear-btn">Clear All</button>
                <button class="cart-export-btn" id="cart-export-btn">📋 Export Cart</button>
            </div>
        `;
        
        document.body.appendChild(panel);
        
        // Add event listeners
        document.getElementById('cart-close-btn').addEventListener('click', () => this.closePanel());
        document.getElementById('cart-clear-btn').addEventListener('click', () => this.handleClearCart());
        document.getElementById('cart-export-btn').addEventListener('click', () => this.handleExport());
        
        // Close on overlay click
        panel.addEventListener('click', (e) => {
            if (e.target === panel) {
                this.closePanel();
            }
        });
        
        // Close on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isPanelOpen) {
                this.closePanel();
            }
        });
    }
    
    updateBadge() {
        const badge = document.getElementById('cart-badge');
        const count = this.cartManager.getCartCount();
        
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'flex' : 'none';
        }
    }
    
    togglePanel() {
        if (this.isPanelOpen) {
            this.closePanel();
        } else {
            this.openPanel();
        }
    }
    
    openPanel() {
        const panel = document.getElementById('cart-panel');
        panel.classList.add('open');
        this.isPanelOpen = true;
        this.renderCartItems();
        
        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    }
    
    closePanel() {
        const panel = document.getElementById('cart-panel');
        panel.classList.remove('open');
        this.isPanelOpen = false;
        
        // Restore body scroll
        document.body.style.overflow = '';
    }
    
    renderCartItems() {
        const body = document.getElementById('cart-panel-body');
        const cart = this.cartManager.getCart();
        
        if (cart.length === 0) {
            body.innerHTML = `
                <div class="cart-empty">
                    <p>🛒 Your cart is empty</p>
                    <p class="cart-empty-hint">Click the + button on posts to add them to your cart</p>
                </div>
            `;
            return;
        }
        
        // Get post details for cart items
        const cartPosts = cart.map(postId => {
            return this.allPosts.find(post => post.post_id === postId);
        }).filter(post => post !== undefined);
        
        body.innerHTML = cartPosts.map(post => `
            <div class="cart-item" data-post-id="${post.post_id}">
                <div class="cart-item-content">
                    <h3 class="cart-item-title">
                        <a href="${post.url}" target="_blank" rel="noopener noreferrer">${this.escapeHtml(post.title)}</a>
                    </h3>
                    <p class="cart-item-meta">
                        <span>👤 ${this.escapeHtml(post.authors || 'Unknown')}</span>
                        <span>📅 ${this.formatDate(post.date_published)}</span>
                    </p>
                    ${post.summary ? `<p class="cart-item-summary">${this.escapeHtml(post.summary)}</p>` : ''}
                </div>
                <button class="cart-item-remove" data-post-id="${post.post_id}" title="Remove from cart">
                    ×
                </button>
            </div>
        `).join('');
        
        // Add remove button listeners
        body.querySelectorAll('.cart-item-remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const postId = e.target.dataset.postId;
                this.handleRemoveItem(postId);
            });
        });
    }
    
    async handleRemoveItem(postId) {
        try {
            await this.cartManager.removeFromCart(postId);
            // UI will update via event listener
        } catch (error) {
            console.error('Error removing item:', error);
            this.showNotification('Failed to remove item', 'error');
        }
    }
    
    async handleClearCart() {
        if (!confirm('Are you sure you want to clear all items from your cart?')) {
            return;
        }
        
        try {
            await this.cartManager.clearCart();
            // UI will update via event listener
        } catch (error) {
            console.error('Error clearing cart:', error);
            this.showNotification('Failed to clear cart', 'error');
        }
    }
    
    handleExport() {
        const cart = this.cartManager.getCart();
        
        if (cart.length === 0) {
            this.showNotification('Cart is empty', 'error');
            return;
        }
        
        // Show format selection menu
        this.showExportMenu();
    }
    
    showExportMenu() {
        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.className = 'export-modal-overlay';
        overlay.innerHTML = `
            <div class="export-modal">
                <h3>Export Cart</h3>
                <p>Choose a format to copy to clipboard:</p>
                <div class="export-options">
                    <button class="export-option-btn" data-format="markdown">
                        <span class="export-icon">📝</span>
                        <div>
                            <span class="export-label">Slack Format</span>
                            <span class="export-desc">Optimized for Slack messages (mrkdwn)</span>
                        </div>
                    </button>
                    <button class="export-option-btn" data-format="plaintext">
                        <span class="export-icon">📄</span>
                        <div>
                            <span class="export-label">Plain Text</span>
                            <span class="export-desc">For email, notes, simple sharing</span>
                        </div>
                    </button>
                    <button class="export-option-btn" data-format="html">
                        <span class="export-icon">🌐</span>
                        <div>
                            <span class="export-label">HTML</span>
                            <span class="export-desc">For web pages, rich formatting</span>
                        </div>
                    </button>
                </div>
                <button class="export-cancel-btn">Cancel</button>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        // Add event listeners
        overlay.querySelectorAll('.export-option-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const format = btn.dataset.format;
                this.handleExportFormat(format);
                overlay.remove();
            });
        });
        
        overlay.querySelector('.export-cancel-btn').addEventListener('click', () => {
            overlay.remove();
        });
        
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.remove();
            }
        });
    }
    
    handleExportFormat(format) {
        const cart = this.cartManager.getCart();
        
        // Get post details
        const cartPosts = cart.map(postId => {
            return this.allPosts.find(post => post.post_id === postId);
        }).filter(post => post !== undefined);
        
        let exportText = '';
        
        switch (format) {
            case 'markdown':
                exportText = this.generateMarkdown(cartPosts);
                break;
            case 'plaintext':
                exportText = this.generatePlainText(cartPosts);
                break;
            case 'html':
                exportText = this.generateHTML(cartPosts);
                break;
        }
        
        // Copy to clipboard
        this.copyToClipboard(exportText);
    }
    
    generateMarkdown(posts) {
        // Slack format - title, URL, summary (clean format)
        let markdown = `📚 My AWS Content Cart (${posts.length} items)\n\n`;
        
        posts.forEach((post, index) => {
            // Title (plain text, no formatting)
            markdown += `${post.title}\n`;
            // URL (Slack auto-links it)
            markdown += `${post.url}\n`;
            // Summary if available
            if (post.summary) {
                markdown += `${post.summary}\n`;
            }
            markdown += '\n';
        });
        
        return markdown;
    }
    
    generatePlainText(posts) {
        let text = 'MY AWS CONTENT CART\n';
        text += '='.repeat(50) + '\n\n';
        text += `Generated: ${new Date().toLocaleDateString()}\n`;
        text += `Total items: ${posts.length}\n\n`;
        
        posts.forEach((post, index) => {
            text += `${index + 1}. ${post.title}\n`;
            text += `   URL: ${post.url}\n`;
            text += `   Authors: ${post.authors || 'Unknown'}\n`;
            text += `   Published: ${this.formatDate(post.date_published)}\n`;
            if (post.summary) {
                text += `   Summary: ${post.summary}\n`;
            }
            if (post.label) {
                text += `   Category: ${post.label}\n`;
            }
            text += '\n';
        });
        
        return text;
    }
    
    generateHTML(posts) {
        let html = '<!DOCTYPE html>\n<html>\n<head>\n';
        html += '  <meta charset="UTF-8">\n';
        html += '  <title>My AWS Content Cart</title>\n';
        html += '  <style>\n';
        html += '    body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }\n';
        html += '    h1 { color: #232f3e; border-bottom: 3px solid #ff9900; padding-bottom: 10px; }\n';
        html += '    .post { margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }\n';
        html += '    .post h2 { color: #232f3e; margin-top: 0; }\n';
        html += '    .post a { color: #0073bb; text-decoration: none; }\n';
        html += '    .post a:hover { text-decoration: underline; }\n';
        html += '    .meta { color: #666; font-size: 14px; margin: 10px 0; }\n';
        html += '    .summary { line-height: 1.6; }\n';
        html += '    .category { display: inline-block; background: #ff9900; color: white; padding: 4px 12px; border-radius: 4px; font-size: 12px; }\n';
        html += '  </style>\n';
        html += '</head>\n<body>\n';
        html += '  <h1>My AWS Content Cart</h1>\n';
        html += `  <p><strong>Generated:</strong> ${new Date().toLocaleDateString()}</p>\n`;
        html += `  <p><strong>Total items:</strong> ${posts.length}</p>\n\n`;
        
        posts.forEach((post, index) => {
            html += '  <div class="post">\n';
            html += `    <h2>${index + 1}. <a href="${post.url}" target="_blank">${this.escapeHtml(post.title)}</a></h2>\n`;
            html += `    <div class="meta">\n`;
            html += `      <strong>Authors:</strong> ${this.escapeHtml(post.authors || 'Unknown')}<br>\n`;
            html += `      <strong>Published:</strong> ${this.formatDate(post.date_published)}\n`;
            html += `    </div>\n`;
            if (post.summary) {
                html += `    <p class="summary">${this.escapeHtml(post.summary)}</p>\n`;
            }
            if (post.label) {
                html += `    <span class="category">${this.escapeHtml(post.label)}</span>\n`;
            }
            html += '  </div>\n\n';
        });
        
        html += '</body>\n</html>';
        
        return html;
    }
    
    async copyToClipboard(text) {
        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(text);
                this.showNotification('Copied to clipboard! 📋', 'success');
            } else {
                // Fallback for older browsers
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                this.showNotification('Copied to clipboard! 📋', 'success');
            }
        } catch (error) {
            console.error('Failed to copy:', error);
            this.showNotification('Failed to copy to clipboard', 'error');
        }
    }
    
    showNotification(message, type) {
        // Use existing notification system if available
        if (typeof showNotification === 'function') {
            showNotification(message, type);
        } else {
            alert(message);
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
    }
}

// Export for use in other modules
window.CartUI = CartUI;
