// Chat Widget JavaScript
// Configuration - will be replaced during deployment
const CHAT_API_ENDPOINT = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging';

class ChatWidget {
    constructor() {
        this.isOpen = false;
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
                    <button class="chat-close-btn" id="chatCloseBtn">×</button>
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
        const chatSendBtn = document.getElementById('chatSendBtn');
        const chatInput = document.getElementById('chatInput');
        
        chatButton.addEventListener('click', () => this.toggleChat());
        chatCloseBtn.addEventListener('click', () => this.closeChat());
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
        document.getElementById('chatWindow').classList.remove('open');
        document.getElementById('chatButton').classList.remove('open');
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
                    <div class="chat-welcome-example" data-query="Tell me about serverless computing">
                        💡 "Tell me about serverless computing"
                    </div>
                    <div class="chat-welcome-example" data-query="How do I get started with containers?">
                        🐳 "How do I get started with containers?"
                    </div>
                    <div class="chat-welcome-example" data-query="Show me best practices for security">
                        🔒 "Show me best practices for security"
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
            
            // Add assistant response
            this.addMessage('assistant', response.response, response.recommendations);
            
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
    
    addMessage(role, content, recommendations = null) {
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
                <div class="chat-message-bubble">${this.escapeHtml(content)}</div>
                ${recommendationsHTML}
                ${proposalSuggestionHTML}
                <div class="chat-message-time">${time}</div>
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Store message
        this.messages.push({ role, content, recommendations, timestamp: new Date() });
    }
    
    createRecommendationHTML(rec) {
        const labelClass = this.getLabelClass(rec.label);
        const labelIcon = this.getLabelIcon(rec.label);
        
        return `
            <div class="chat-recommendation" onclick="window.open('${rec.url}', '_blank')">
                <div class="chat-recommendation-header">
                    <span class="chat-recommendation-label ${labelClass}">
                        ${labelIcon} ${rec.label}
                    </span>
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
