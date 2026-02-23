// Chat Widget JavaScript
// Configuration - will be replaced during deployment
const CHAT_API_ENDPOINT = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod';

class ChatWidget {
    constructor() {
        this.isOpen = false;
        this.isExpanded = false;
        this.messages = [];
        this.conversationId = this.generateConversationId();
        this.isTyping = false;
        
        this.init();
    }
    
    init() {
        this.createWidget();
        this.attachEventListeners();
        this.showWelcomeMessage();
    }
    
    generateConversationId() {
        return 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    createWidget() {
        // Create chat button
        const chatButton = document.createElement('button');
        chatButton.className = 'chat-button';
        chatButton.id = 'chatButton';
        chatButton.innerHTML = '💬';
        chatButton.title = 'Chat with EUC Content Finder';
        
        // Create chat window
        const chatWindow = document.createElement('div');
        chatWindow.className = 'chat-window';
        chatWindow.id = 'chatWindow';
        chatWindow.innerHTML = `
            <div class="chat-header">
                <div class="chat-header-top">
                    <div class="chat-header-title">
                        <span class="chat-header-icon">🤖</span>
                        <span>EUC Content Finder</span>
                    </div>
                    <div class="chat-header-actions">
                        <button class="chat-expand-btn" id="chatExpandBtn" title="Expand view">
                            <span class="expand-icon">⛶</span>
                        </button>
                        <button class="chat-close-btn" id="chatCloseBtn">×</button>
                    </div>
                </div>
            </div>
            <div class="chat-messages" id="chatMessages"></div>
            <div class="chat-input-container" id="chatInputContainer">
                <div class="chat-input-wrapper">
                    <textarea 
                        class="chat-input" 
                        id="chatInput" 
                        placeholder="Ask me anything about AWS blogs..."
                        rows="1"
                        maxlength="500"
                    ></textarea>
                    <button class="chat-send-btn" id="chatSendBtn">
                        <span>➤</span>
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(chatButton);
        document.body.appendChild(chatWindow);
    }
    
    attachEventListeners() {
        const chatButton = document.getElementById('chatButton');
        const chatCloseBtn = document.getElementById('chatCloseBtn');
        const chatExpandBtn = document.getElementById('chatExpandBtn');
        const chatSendBtn = document.getElementById('chatSendBtn');
        const chatInput = document.getElementById('chatInput');
        
        chatButton.addEventListener('click', () => this.toggleChat());
        chatCloseBtn.addEventListener('click', () => this.closeChat());
        chatExpandBtn.addEventListener('click', () => this.toggleExpanded());
        chatSendBtn.addEventListener('click', () => this.sendMessage());
        
        // Send on Enter (but Shift+Enter for new line)
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize textarea
        chatInput.addEventListener('input', () => {
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
        });
        
        // Close on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.closeChat();
            }
        });
    }
    
    toggleChat() {
        if (this.isOpen) {
            this.closeChat();
        } else {
            this.openChat();
        }
    }
    
    openChat() {
        this.isOpen = true;
        document.getElementById('chatWindow').classList.add('open');
        document.getElementById('chatButton').classList.add('open');
        
        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
            setTimeout(() => chatInput.focus(), 100);
        }
    }
    
    closeChat() {
        this.isOpen = false;
        this.isExpanded = false;
        document.getElementById('chatWindow').classList.remove('open');
        document.getElementById('chatWindow').classList.remove('expanded');
        document.getElementById('chatButton').classList.remove('open');
        this.updateExpandButton();
    }
    
    toggleExpanded() {
        this.isExpanded = !this.isExpanded;
        const chatWindow = document.getElementById('chatWindow');
        
        if (this.isExpanded) {
            chatWindow.classList.add('expanded');
        } else {
            chatWindow.classList.remove('expanded');
        }
        
        this.updateExpandButton();
        this.scrollToBottom();
    }
    
    updateExpandButton() {
        const expandBtn = document.getElementById('chatExpandBtn');
        const expandIcon = expandBtn.querySelector('.expand-icon');
        
        if (this.isExpanded) {
            expandIcon.textContent = '⛶'; // Collapse icon
            expandBtn.title = 'Collapse view';
        } else {
            expandIcon.textContent = '⛶'; // Expand icon
            expandBtn.title = 'Expand view';
        }
    }
    
    showWelcomeMessage() {
        const messagesContainer = document.getElementById('chatMessages');
        if (!messagesContainer) return;
        
        messagesContainer.innerHTML = `
            <div class="chat-welcome">
                <div class="chat-welcome-icon">👋</div>
                <div class="chat-welcome-title">What can I help you find today?</div>
                <div class="chat-welcome-subtitle">Ask me about EUC articles and I'll recommend the best ones for you!</div>
                <div class="chat-welcome-examples">
                    <div class="chat-welcome-example" data-query="How do I get started with Amazon WorkSpaces?">
                        💻 "How do I get started with Amazon WorkSpaces?"
                    </div>
                    <div class="chat-welcome-example" data-query="What are best practices for WorkSpaces security?">
                        🔒 "What are best practices for WorkSpaces security?"
                    </div>
                    <div class="chat-welcome-example" data-query="Tell me about AppStream 2.0 deployment">
                        🚀 "Tell me about AppStream 2.0 deployment"
                    </div>
                </div>
            </div>
        `;
        
        // Add click handlers to example queries
        const examples = messagesContainer.querySelectorAll('.chat-welcome-example');
        examples.forEach(example => {
            example.addEventListener('click', (e) => {
                e.stopPropagation();
                const query = example.dataset.query;
                const input = document.getElementById('chatInput');
                if (input) {
                    input.value = query;
                    this.sendMessage();
                }
            });
        });
    }
    
    async sendMessage() {
        const input = document.getElementById('chatInput');
        if (!input) return;
        
        const message = input.value.trim();
        
        if (!message || this.isTyping) return;
        
        // Clear input
        input.value = '';
        input.style.height = 'auto';
        
        // Add user message to UI
        this.addMessage('user', message);
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            // Call chat API
            const response = await this.callChatAPI(message);
            
            // Remove typing indicator
            this.hideTypingIndicator();
            
            // Auto-expand when response is received
            if (!this.isExpanded && (response.aws_docs?.length > 0 || response.recommendations?.length > 0)) {
                this.toggleExpanded();
            }
            
            // Add assistant response
            this.addMessage('assistant', response.response, response.recommendations, response.aws_docs);
            
        } catch (error) {
            console.error('Chat error:', error);
            this.hideTypingIndicator();
            this.addMessage('assistant', 'Sorry, I encountered an error. Please try again or search manually.');
        }
    }
    
    async callChatAPI(message) {
        const response = await fetch(`${CHAT_API_ENDPOINT}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                conversation_id: this.conversationId
            })
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
    }
    
    addMessage(role, content, recommendations = null, awsDocs = null) {
        const messagesContainer = document.getElementById('chatMessages');
        if (!messagesContainer) return;
        
        // Remove welcome message if present
        const welcome = messagesContainer.querySelector('.chat-welcome');
        if (welcome) {
            welcome.remove();
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}`;
        
        const avatar = role === 'assistant' ? '🤖' : '👤';
        const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        
        // Add AWS docs citations to content if present
        let contentWithCitations = content;
        let citationsHTML = '';
        if (awsDocs && awsDocs.length > 0) {
            citationsHTML = `
                <div class="chat-citations">
                    <div class="chat-citations-title">📚 AWS Documentation References:</div>
                    ${awsDocs.map((doc, index) => `
                        <div class="chat-citation">
                            <span class="chat-citation-number">[${index + 1}]</span>
                            <a href="${doc.url}" target="_blank" class="chat-citation-link">
                                ${this.escapeHtml(doc.title)}
                            </a>
                            <button class="chat-citation-add-btn" onclick="window.chatWidget.copyToClipboard('${this.escapeHtml(doc.title)}', '${doc.url}')" title="Copy to clipboard">
                                📋
                            </button>
                        </div>
                    `).join('')}
                </div>
            `;
        }
        
        let recommendationsHTML = '';
        if (recommendations && recommendations.length > 0) {
            recommendationsHTML = `
                <div class="chat-recommendations">
                    ${recommendations.map(rec => this.createRecommendationHTML(rec)).join('')}
                </div>
            `;
        }
        
        // Add proposal suggestion for assistant messages
        let proposalSuggestionHTML = '';
        if (role === 'assistant') {
            proposalSuggestionHTML = `
                <div class="chat-proposal-suggestion">
                    <div class="chat-proposal-text">💡 Can't find what you're looking for?</div>
                    <button class="chat-proposal-btn" onclick="document.getElementById('proposeArticleBtn').click(); document.getElementById('chatCloseBtn').click();">
                        ✍️ Propose a Community Article
                    </button>
                </div>
            `;
        }
        
        messageDiv.innerHTML = `
            <div class="chat-message-avatar">${avatar}</div>
            <div class="chat-message-content">
                <div class="chat-message-bubble">${this.escapeHtml(contentWithCitations)}</div>
                ${citationsHTML}
                ${recommendationsHTML}
                ${proposalSuggestionHTML}
                <div class="chat-message-time">${time}</div>
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Store message
        this.messages.push({ role, content, recommendations, awsDocs, timestamp: new Date() });
    }
    
    createRecommendationHTML(rec) {
        const labelClass = this.getLabelClass(rec.label);
        const labelIcon = this.getLabelIcon(rec.label);
        
        return `
            <div class="chat-recommendation">
                <div class="chat-recommendation-header">
                    <span class="chat-recommendation-label ${labelClass}">
                        ${labelIcon} ${rec.label}
                    </span>
                    <button class="chat-recommendation-add-btn" onclick="event.stopPropagation(); window.chatWidget.addToCart('${rec.post_id}')" title="Add to cart">
                        ➕
                    </button>
                </div>
                <div class="chat-recommendation-title">${this.escapeHtml(rec.title)}</div>
                <div class="chat-recommendation-summary">${this.escapeHtml(this.truncate(rec.summary, 150))}</div>
                <div class="chat-recommendation-reason">💡 ${this.escapeHtml(rec.relevance_reason)}</div>
                <a href="${rec.url}" target="_blank" class="chat-recommendation-link" onclick="event.stopPropagation()">
                    View Post →
                </a>
            </div>
        `;
    }
    
    getLabelClass(label) {
        const labelMap = {
            'Announcement': 'label-announcement',
            'Best Practices': 'label-best-practices',
            'Curation': 'label-curation',
            'Customer Story': 'label-customer-story',
            'Technical How-To': 'label-technical-how-to',
            'Thought Leadership': 'label-thought-leadership'
        };
        return labelMap[label] || 'label-announcement';
    }
    
    getLabelIcon(label) {
        const iconMap = {
            'Announcement': '📢',
            'Best Practices': '✅',
            'Curation': '📚',
            'Customer Story': '🏢',
            'Technical How-To': '🔧',
            'Thought Leadership': '💡'
        };
        return iconMap[label] || '🏷️';
    }
    
    showTypingIndicator() {
        this.isTyping = true;
        const messagesContainer = document.getElementById('chatMessages');
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chat-message assistant';
        typingDiv.id = 'typingIndicator';
        typingDiv.innerHTML = `
            <div class="chat-message-avatar">🤖</div>
            <div class="chat-typing">
                <div class="chat-typing-dots">
                    <div class="chat-typing-dot"></div>
                    <div class="chat-typing-dot"></div>
                    <div class="chat-typing-dot"></div>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
        
        // Disable send button
        document.getElementById('chatSendBtn').disabled = true;
    }
    
    hideTypingIndicator() {
        this.isTyping = false;
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
        
        // Enable send button
        document.getElementById('chatSendBtn').disabled = false;
    }
    
    scrollToBottom() {
        const messagesContainer = document.getElementById('chatMessages');
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    truncate(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    }
    
    // ============================================
    // Cart Integration
    // ============================================
    
    addToCart(postId) {
        if (!postId) {
            console.error('No post ID provided');
            return;
        }
        
        // Try to access cart manager (check both window.cartManager and global cartManager)
        const cart = window.cartManager || (typeof cartManager !== 'undefined' ? cartManager : null);
        
        if (!cart) {
            console.error('Cart manager not found. window.cartManager:', window.cartManager, 'cartManager:', typeof cartManager);
            this.showNotification('Cart not available. Please refresh the page.', 'error');
            return;
        }
        
        // Check if already in cart
        if (cart.isInCart(postId)) {
            this.showNotification('Already in cart', 'info');
            return;
        }
        
        // Add to cart
        cart.addToCart(postId)
            .then(() => {
                this.showNotification('Added to cart!', 'success');
            })
            .catch(error => {
                console.error('Failed to add to cart:', error);
                this.showNotification('Failed to add to cart', 'error');
            });
    }
    
    copyToClipboard(title, url) {
        const text = `${title}\n${url}`;
        
        // Try modern clipboard API first
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text)
                .then(() => {
                    this.showNotification('Copied to clipboard!', 'success');
                })
                .catch(error => {
                    console.error('Failed to copy:', error);
                    this.fallbackCopyToClipboard(text);
                });
        } else {
            this.fallbackCopyToClipboard(text);
        }
    }
    
    fallbackCopyToClipboard(text) {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        
        try {
            document.execCommand('copy');
            this.showNotification('Copied to clipboard!', 'success');
        } catch (error) {
            console.error('Failed to copy:', error);
            this.showNotification('Failed to copy', 'error');
        }
        
        document.body.removeChild(textarea);
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `chat-notification chat-notification-${type}`;
        notification.textContent = message;
        
        // Add to chat window
        const chatWindow = document.getElementById('chatWindow');
        if (chatWindow) {
            chatWindow.appendChild(notification);
            
            // Trigger animation
            setTimeout(() => {
                notification.classList.add('show');
            }, 10);
            
            // Remove after 3 seconds
            setTimeout(() => {
                notification.classList.remove('show');
                setTimeout(() => {
                    notification.remove();
                }, 300);
            }, 3000);
        }
    }
}

// Initialize chat widget when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    try {
        window.chatWidget = new ChatWidget();
        console.log('Chat widget initialized successfully');
    } catch (error) {
        console.error('Error initializing chat widget:', error);
    }
});
