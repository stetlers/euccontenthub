// Chat Widget JavaScript - KB-Powered Version
// Configuration - detect environment
const CHAT_API_ENDPOINT = window.location.hostname === 'staging.awseuccontent.com'
    ? 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'
    : 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod';

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
        chatButton.title = 'Chat with WorkSpaces Community Finder';
        
        // Create chat window
        const chatWindow = document.createElement('div');
        chatWindow.className = 'chat-window';
        chatWindow.id = 'chatWindow';
        chatWindow.innerHTML = `
            <div class="chat-header">
                <div class="chat-header-top">
                    <div class="chat-header-title">
                        <span class="chat-header-icon">🤖</span>
                        <span>WorkSpaces Community Finder</span>
                        <span class="chat-kb-badge" title="Powered by AWS Bedrock AI + AWS Documentation">AI</span>
                    </div>
                    <div class="chat-header-actions">
                        <button class="chat-history-btn" id="chatHistoryBtn" title="Conversation history">
                            <span>📜</span>
                        </button>
                        <button class="chat-new-btn" id="chatNewBtn" title="New conversation">
                            <span>➕</span>
                        </button>
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
                        placeholder="Ask me anything about AWS WorkSpaces services..."
                        rows="1"
                        maxlength="500"
                    ></textarea>
                    <button class="chat-send-btn" id="chatSendBtn">
                        <span>➤</span>
                    </button>
                </div>
                <div class="chat-char-count" id="chatCharCount">0/500</div>
            </div>
        `;
        
        document.body.appendChild(chatButton);
        document.body.appendChild(chatWindow);
        
        // Create history panel
        const historyPanel = document.createElement('div');
        historyPanel.className = 'chat-history-panel';
        historyPanel.id = 'chatHistoryPanel';
        historyPanel.style.display = 'none';
        historyPanel.innerHTML = `
            <div class="chat-history-header">
                <h3>📜 Conversation History</h3>
                <button class="chat-history-close" id="chatHistoryClose">×</button>
            </div>
            <div class="chat-history-list" id="chatHistoryList">
                <div style="text-align:center;color:#94a3b8;padding:20px;">Loading...</div>
            </div>
        `;
        document.body.appendChild(historyPanel);
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
        
        // History and new conversation buttons
        const chatHistoryBtn = document.getElementById('chatHistoryBtn');
        const chatNewBtn = document.getElementById('chatNewBtn');
        const chatHistoryClose = document.getElementById('chatHistoryClose');
        
        if (chatHistoryBtn) chatHistoryBtn.addEventListener('click', () => this.toggleHistory());
        if (chatNewBtn) chatNewBtn.addEventListener('click', () => this.newConversation());
        if (chatHistoryClose) chatHistoryClose.addEventListener('click', () => this.toggleHistory());
        
        // Send on Enter (but Shift+Enter for new line)
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize textarea and update char count
        chatInput.addEventListener('input', () => {
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
            this.updateCharCount();
        });
        
        // Close on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.closeChat();
            }
        });
    }
    
    updateCharCount() {
        const chatInput = document.getElementById('chatInput');
        const charCount = document.getElementById('chatCharCount');
        if (chatInput && charCount) {
            const count = chatInput.value.length;
            charCount.textContent = `${count}/500`;
            charCount.style.color = count > 450 ? '#e74c3c' : '#95a5a6';
        }
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
            expandIcon.textContent = '⛶';
            expandBtn.title = 'Collapse view';
        } else {
            expandIcon.textContent = '⛶';
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
                <div class="chat-welcome-subtitle">Ask me about AWS WorkSpaces services and I'll provide accurate answers with citations!</div>
                <div class="chat-welcome-examples">
                    <div class="chat-welcome-example" data-query="What is Amazon WorkSpaces?">
                        💡 "What is Amazon WorkSpaces?"
                    </div>
                    <div class="chat-welcome-example" data-query="What happened to WorkSpaces?">
                        🔄 "What happened to WorkSpaces?"
                    </div>
                    <div class="chat-welcome-example" data-query="What is AppStream 2.0?">
                        🚀 "What is AppStream 2.0?"
                    </div>
                    <div class="chat-welcome-example" data-query="How can I provide remote access to my employees?">
                        💻 "How can I provide remote access to my employees?"
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
        this.updateCharCount();
        
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
            if (!this.isExpanded && (response.citations?.length > 0 || response.recommendations?.length > 0)) {
                this.toggleExpanded();
            }
            
            // Add assistant response — pass aws_docs and source separately
            this.addMessage('assistant', response.response, response.recommendations, response.citations, response.aws_docs, response.source);
            
            // Save conversation turn to history
            this.saveConversationTurn(message, response.response);
            
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
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `API error: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
    }
    
    addMessage(role, content, recommendations = null, citations = null, awsDocs = null, source = null) {
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
        
        // Add citations if present (from Bedrock Knowledge Base)
        let citationsHTML = '';
        if (citations && citations.length > 0) {
            citationsHTML = `
                <div class="chat-citations">
                    <div class="chat-citations-title">📚 Sources:</div>
                    ${citations.map((citation, index) => `
                        <div class="chat-citation">
                            <span class="chat-citation-number">[${index + 1}]</span>
                            <span class="chat-citation-source">${this.escapeHtml(citation.source)}</span>
                            <div class="chat-citation-content">${this.escapeHtml(citation.content)}</div>
                        </div>
                    `).join('')}
                </div>
            `;
        }
        
        let recommendationsHTML = '';
        if (recommendations && recommendations.length > 0) {
            recommendationsHTML = `
                <div class="chat-recommendations">
                    <div class="chat-recommendations-title">📝 Recommended Blog Posts:</div>
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
                    <button class="chat-proposal-btn" onclick="document.getElementById('proposeArticleBtn')?.click(); document.getElementById('chatCloseBtn').click();">
                        ✍️ Propose a Community Article
                    </button>
                </div>
            `;
        }
        
        messageDiv.innerHTML = `
            <div class="chat-message-avatar">${avatar}</div>
            <div class="chat-message-content">
                <div class="chat-message-bubble">${this.formatContent(content)}</div>
                ${role === 'assistant' ? (() => {
                    const hasAwsDocs = awsDocs && awsDocs.length > 0;
                    const hasCitations = citations && citations.length > 0;
                    const hasRecs = recommendations && recommendations.length > 0;
                    // Use explicit source field from lambda if available
                    if (source === 'kb') return '<div class="chat-source-badge chat-source-kb" title="Response sourced from curated knowledge base"><span>📚</span> KB</div>';
                    if (source === 'ai') return '<div class="chat-source-badge chat-source-ai" title="Response from AI — not in knowledge base yet"><span>🤖</span> AI</div>';
                    // Fallback: infer from response data
                    if (hasAwsDocs) return '<div class="chat-source-badge chat-source-docs" title="Response sourced from AWS Documentation"><span>📄</span> AWS Docs</div>';
                    if (hasCitations) return '<div class="chat-source-badge chat-source-kb" title="Response sourced from curated knowledge base"><span>📚</span> KB</div>';
                    if (hasRecs) return '<div class="chat-source-badge chat-source-docs" title="Response includes blog recommendations"><span>📝</span> Blog</div>';
                    return '';
                })() : ''}
                ${citationsHTML}
                ${awsDocs && awsDocs.length > 0 ? `
                    <div class="chat-citations">
                        <div class="chat-citations-title">📄 AWS Documentation References:</div>
                        ${awsDocs.map((doc, index) => `
                            <div class="chat-citation">
                                <span class="chat-citation-number">[${index + 1}]</span>
                                <a href="${doc.url}" target="_blank" class="chat-citation-link" style="color:#60a5fa;text-decoration:none;">${this.escapeHtml(doc.title)}</a>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
                ${recommendationsHTML}
                ${proposalSuggestionHTML}
                <div class="chat-message-time">${time}</div>
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Store message
        this.messages.push({ role, content, recommendations, citations, timestamp: new Date() });
    }
    
    formatContent(content) {
        // Render a safe subset of Markdown. We ALWAYS escape first so model
        // output can never inject HTML, then re-introduce a known set of tags.
        return this.renderMarkdown(content);
    }

    renderMarkdown(text) {
        if (!text) return '';

        // Apply inline Markdown to text that has ALREADY been HTML-escaped.
        // escapeHtml only touches & < > ", so [](), *, _, ` are still intact.
        const inline = (s) => s
            .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
                '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>');

        const lines = this.escapeHtml(text).split('\n');
        let html = '';
        let inList = false;
        const closeList = () => { if (inList) { html += '</ul>'; inList = false; } };

        for (const raw of lines) {
            const line = raw.replace(/\s+$/, '');
            const bullet = line.match(/^\s*[-*•]\s+(.*)$/);
            const heading = line.match(/^\s*#{1,6}\s+(.*)$/);

            if (bullet) {
                if (!inList) { html += '<ul class="chat-md-list">'; inList = true; }
                html += `<li>${inline(bullet[1])}</li>`;
            } else if (heading) {
                closeList();
                html += `<div class="chat-md-heading">${inline(heading[1])}</div>`;
            } else if (line.trim() === '') {
                closeList();
                html += '<br>';
            } else {
                closeList();
                html += `${inline(line)}<br>`;
            }
        }
        closeList();
        return html;
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
                <div class="chat-recommendation-meta">
                    <span class="chat-recommendation-authors">👤 ${this.escapeHtml(rec.authors)}</span>
                    <span class="chat-recommendation-date">📅 ${rec.date_published}</span>
                </div>
                <a href="${rec.url}" target="_blank" class="chat-recommendation-link" onclick="event.stopPropagation()">
                    View Post →
                </a>
            </div>
        `;
    }
    
    getLabelClass(label) {
        const labelMap = {
            'Announcement': 'label-announcement',
            'Product Announcement': 'label-announcement',
            'Best Practices': 'label-best-practices',
            'Curation': 'label-curation',
            'Customer Story': 'label-customer-story',
            'Case Study': 'label-customer-story',
            'Technical How-To': 'label-technical-how-to',
            'Thought Leadership': 'label-thought-leadership'
        };
        return labelMap[label] || 'label-announcement';
    }
    
    getLabelIcon(label) {
        const iconMap = {
            'Announcement': '📢',
            'Product Announcement': '📢',
            'Best Practices': '✅',
            'Curation': '📚',
            'Customer Story': '🏢',
            'Case Study': '🏢',
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
        if (!text) return '';
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
        
        // Try to access cart manager
        const cart = window.cartManager || (typeof cartManager !== 'undefined' ? cartManager : null);
        
        if (!cart) {
            console.error('Cart manager not found');
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
    
    // ============================================
    // Conversation History
    // ============================================
    
    newConversation() {
        this.conversationId = this.generateConversationId();
        this.messages = [];
        this.showWelcomeMessage();
        this.showNotification('New conversation started', 'info');
    }
    
    toggleHistory() {
        const panel = document.getElementById('chatHistoryPanel');
        if (!panel) return;
        
        if (panel.style.display === 'none') {
            panel.style.display = 'block';
            this.loadHistory();
        } else {
            panel.style.display = 'none';
        }
    }
    
    async loadHistory() {
        const listEl = document.getElementById('chatHistoryList');
        if (!listEl) return;
        
        if (!window.authManager || !window.authManager.isAuthenticated()) {
            listEl.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px;">Sign in to see conversation history</div>';
            return;
        }
        
        listEl.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px;">Loading...</div>';
        
        try {
            const token = window.authManager.getIdToken();
            const response = await fetch(`${CHAT_API_ENDPOINT}/chat/history`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (!response.ok) throw new Error('Failed to load history');
            
            const data = await response.json();
            const conversations = data.conversations || [];
            
            if (conversations.length === 0) {
                listEl.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px;">No previous conversations</div>';
                return;
            }
            
            listEl.innerHTML = conversations.map(c => {
                const date = c.updated_at ? new Date(c.updated_at).toLocaleDateString() : '';
                const preview = c.title || c.last_message || 'Conversation';
                return `<div class="chat-history-item" data-conversation-id="${c.conversation_id}" style="padding:10px 12px;border-bottom:1px solid rgba(255,255,255,0.06);cursor:pointer;transition:background 0.15s;">
                    <div style="font-size:0.85rem;color:#e2e8f0;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${this.escapeHtml(preview)}</div>
                    <div style="font-size:0.75rem;color:#64748b;margin-top:2px;">${date}</div>
                </div>`;
            }).join('');
            
            listEl.querySelectorAll('.chat-history-item').forEach(item => {
                item.addEventListener('mouseenter', () => { item.style.background = 'rgba(255,255,255,0.05)'; });
                item.addEventListener('mouseleave', () => { item.style.background = ''; });
                item.addEventListener('click', () => {
                    this.loadConversation(item.dataset.conversationId);
                });
            });
        } catch (err) {
            console.error('Failed to load history:', err);
            listEl.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px;">Failed to load history</div>';
        }
    }
    
    async loadConversation(conversationId) {
        if (!window.authManager || !window.authManager.isAuthenticated()) return;
        
        try {
            const token = window.authManager.getIdToken();
            const response = await fetch(`${CHAT_API_ENDPOINT}/chat/history/${conversationId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (!response.ok) throw new Error('Failed to load conversation');
            
            const data = await response.json();
            const messages = data.messages || [];
            
            // Set this as the active conversation
            this.conversationId = conversationId;
            this.messages = [];
            
            // Clear chat and replay messages
            const messagesContainer = document.getElementById('chatMessages');
            if (messagesContainer) {
                const welcome = messagesContainer.querySelector('.chat-welcome');
                if (welcome) welcome.remove();
                messagesContainer.innerHTML = '';
            }
            
            messages.forEach(msg => {
                this.addMessage(msg.role, msg.content);
            });
            
            // Close history panel
            const panel = document.getElementById('chatHistoryPanel');
            if (panel) panel.style.display = 'none';
            
        } catch (err) {
            console.error('Failed to load conversation:', err);
            this.showNotification('Failed to load conversation', 'error');
        }
    }
    
    async saveConversationTurn(userMessage, assistantResponse) {
        // Save the conversation turn to the API so it appears in history
        if (!window.authManager || !window.authManager.isAuthenticated()) return;
        
        try {
            const token = window.authManager.getIdToken();
            const apiEndpoint = window.location.hostname === 'staging.awseuccontent.com'
                ? 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'
                : 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod';
            
            await fetch(`${apiEndpoint}/chat/history/${this.conversationId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    conversation_id: this.conversationId,
                    title: userMessage.substring(0, 100),
                    messages: this.messages.map(m => ({ role: m.role, content: m.content }))
                })
            });
        } catch (err) {
            console.warn('Failed to save conversation:', err);
        }
    }
}

// Initialize chat widget when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    try {
        window.chatWidget = new ChatWidget();
        console.log('Chat widget (KB-powered) initialized successfully');
    } catch (error) {
        console.error('Error initializing chat widget:', error);
    }
});
