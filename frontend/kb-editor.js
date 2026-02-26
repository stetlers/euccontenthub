/**
 * KB Editor Module
 * Provides UI for editing Knowledge Base documents
 */

class KBEditor {
    constructor() {
        this.currentDocument = null;
        this.originalContent = null;
        this.hasUnsavedChanges = false;
        this.isLoading = false;
    }

    /**
     * Initialize KB editor
     */
    init() {
        // Add event listener for beforeunload to warn about unsaved changes
        window.addEventListener('beforeunload', (e) => {
            if (this.hasUnsavedChanges) {
                e.preventDefault();
                e.returnValue = '';
            }
        });
    }

    /**
     * Show KB editor modal with document list
     */
    async showEditor() {
        // Check authentication
        if (!window.authManager || !window.authManager.isAuthenticated()) {
            showNotification('Please sign in to edit Knowledge Base documents', 'error');
            return;
        }

        // Create modal
        const modal = document.createElement('div');
        modal.className = 'modal kb-editor-modal';
        modal.innerHTML = `
            <div class="modal-content kb-editor-content">
                <div class="kb-editor-header">
                    <h2>📚 Edit Knowledge Base</h2>
                    <button class="close-btn" onclick="kbEditor.closeEditor()">&times;</button>
                </div>
                
                <div class="kb-editor-body">
                    <div class="kb-document-list" id="kbDocumentList">
                        <div class="loading-spinner">Loading documents...</div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.style.display = 'block';

        // Load documents
        await this.loadDocuments();
    }

    /**
     * Load KB documents from API
     */
    async loadDocuments() {
        const listContainer = document.getElementById('kbDocumentList');
        
        try {
            // Get token from auth manager
            const token = window.authManager?.getIdToken();
            
            if (!token) {
                throw new Error('Not authenticated. Please sign in first.');
            }
            
            const response = await fetch(`${API_ENDPOINT}/kb-documents`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load documents');
            }

            const data = await response.json();
            const documents = data.documents || [];

            if (documents.length === 0) {
                listContainer.innerHTML = '<p class="no-documents">No documents available</p>';
                return;
            }

            // Render document list
            listContainer.innerHTML = documents.map(doc => `
                <div class="kb-document-card" onclick="kbEditor.editDocument('${doc.id}')">
                    <div class="kb-doc-icon">${doc.category === 'Q&A' ? '❓' : '🔄'}</div>
                    <div class="kb-doc-info">
                        <h3>${doc.name}</h3>
                        <p>${doc.description}</p>
                        <div class="kb-doc-meta">
                            <span>${doc.category}</span>
                            <span>•</span>
                            <span>${doc.question_count || doc.service_count || 0} items</span>
                            <span>•</span>
                            <span>${(doc.size / 1024).toFixed(1)} KB</span>
                        </div>
                    </div>
                    <div class="kb-doc-arrow">→</div>
                </div>
            `).join('');

        } catch (error) {
            console.error('Error loading documents:', error);
            listContainer.innerHTML = `
                <div class="error-message">
                    <p>Failed to load documents</p>
                    <button onclick="kbEditor.loadDocuments()">Retry</button>
                </div>
            `;
        }
    }

    /**
     * Edit a specific document
     */
    async editDocument(documentId) {
        if (this.isLoading) return;
        this.isLoading = true;

        try {
            const token = window.authManager?.getIdToken();
            if (!token) {
                throw new Error('Not authenticated');
            }
            
            const response = await fetch(`${API_ENDPOINT}/kb-document/${documentId}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load document');
            }

            const data = await response.json();
            this.currentDocument = data;
            this.originalContent = data.content;
            this.hasUnsavedChanges = false;

            // Show editor interface
            this.showEditorInterface();

        } catch (error) {
            console.error('Error loading document:', error);
            showNotification('Failed to load document', 'error');
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Show document editor interface
     */
    showEditorInterface() {
        const modal = document.querySelector('.kb-editor-modal .modal-content');
        
        modal.innerHTML = `
            <div class="kb-editor-header">
                <button class="back-btn" onclick="kbEditor.showEditor()">← Back</button>
                <h2>${this.currentDocument.name}</h2>
                <button class="close-btn" onclick="kbEditor.closeEditor()">&times;</button>
            </div>
            
            <div class="kb-editor-toolbar">
                <div class="kb-editor-tabs">
                    <button class="tab-btn active" onclick="kbEditor.switchTab('edit')">✏️ Edit</button>
                    <button class="tab-btn" onclick="kbEditor.switchTab('preview')">👁️ Preview</button>
                </div>
                <div class="kb-editor-actions">
                    <button class="btn-secondary" onclick="kbEditor.showContributions()">📊 My Contributions</button>
                    <button class="btn-secondary" onclick="kbEditor.showLeaderboard()">🏆 Leaderboard</button>
                </div>
            </div>
            
            <div class="kb-editor-body">
                <div class="kb-editor-pane" id="editPane">
                    <textarea 
                        id="kbContentEditor" 
                        class="kb-content-editor"
                        placeholder="Edit markdown content..."
                    >${this.currentDocument.content}</textarea>
                    
                    <div class="kb-editor-stats">
                        <span id="charCount">${this.currentDocument.content.length} characters</span>
                        <span>•</span>
                        <span id="lineCount">${this.currentDocument.content.split('\n').length} lines</span>
                    </div>
                </div>
                
                <div class="kb-editor-pane hidden" id="previewPane">
                    <div class="kb-content-preview markdown-content" id="kbContentPreview"></div>
                </div>
            </div>
            
            <div class="kb-editor-footer">
                <div class="kb-change-comment">
                    <label for="changeComment">Change Comment (required, 10-500 chars):</label>
                    <textarea 
                        id="changeComment" 
                        placeholder="Describe what you changed and why..."
                        maxlength="500"
                    ></textarea>
                    <div class="comment-counter">
                        <span id="commentCharCount">0</span> / 500 characters
                    </div>
                </div>
                
                <div class="kb-editor-buttons">
                    <button class="btn-secondary" onclick="kbEditor.resetContent()">Reset</button>
                    <button class="btn-primary" onclick="kbEditor.saveDocument()" id="saveBtn">
                        💾 Save Changes
                    </button>
                </div>
            </div>
        `;

        // Add event listeners
        const editor = document.getElementById('kbContentEditor');
        const changeComment = document.getElementById('changeComment');

        editor.addEventListener('input', () => {
            this.hasUnsavedChanges = true;
            this.updateStats();
        });

        changeComment.addEventListener('input', () => {
            this.updateCommentCounter();
        });

        this.updateStats();
    }

    /**
     * Switch between edit and preview tabs
     */
    switchTab(tab) {
        const editPane = document.getElementById('editPane');
        const previewPane = document.getElementById('previewPane');
        const tabs = document.querySelectorAll('.tab-btn');

        tabs.forEach(btn => btn.classList.remove('active'));

        if (tab === 'edit') {
            editPane.classList.remove('hidden');
            previewPane.classList.add('hidden');
            tabs[0].classList.add('active');
        } else {
            editPane.classList.add('hidden');
            previewPane.classList.remove('hidden');
            tabs[1].classList.add('active');
            this.updatePreview();
        }
    }

    /**
     * Update preview pane with rendered markdown
     */
    updatePreview() {
        const editor = document.getElementById('kbContentEditor');
        const preview = document.getElementById('kbContentPreview');
        
        if (!editor || !preview) return;

        const content = editor.value;
        
        // Simple markdown rendering (basic support)
        let html = content
            // Headers
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            // Bold
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Italic
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Links
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
            // Line breaks
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');

        preview.innerHTML = `<p>${html}</p>`;
    }

    /**
     * Update character and line count
     */
    updateStats() {
        const editor = document.getElementById('kbContentEditor');
        const charCount = document.getElementById('charCount');
        const lineCount = document.getElementById('lineCount');

        if (!editor) return;

        const content = editor.value;
        const chars = content.length;
        const lines = content.split('\n').length;

        if (charCount) charCount.textContent = `${chars} characters`;
        if (lineCount) lineCount.textContent = `${lines} lines`;
    }

    /**
     * Update change comment character counter
     */
    updateCommentCounter() {
        const comment = document.getElementById('changeComment');
        const counter = document.getElementById('commentCharCount');

        if (!comment || !counter) return;

        const count = comment.value.length;
        counter.textContent = count;

        // Visual feedback
        if (count < 10) {
            counter.style.color = '#e74c3c';
        } else if (count > 450) {
            counter.style.color = '#f39c12';
        } else {
            counter.style.color = '#27ae60';
        }
    }

    /**
     * Reset content to original
     */
    resetContent() {
        if (!confirm('Are you sure you want to reset all changes?')) {
            return;
        }

        const editor = document.getElementById('kbContentEditor');
        if (editor) {
            editor.value = this.originalContent;
            this.hasUnsavedChanges = false;
            this.updateStats();
            showNotification('Content reset to original', 'info');
        }
    }

    /**
     * Save document changes
     */
    async saveDocument() {
        const editor = document.getElementById('kbContentEditor');
        const commentField = document.getElementById('changeComment');
        const saveBtn = document.getElementById('saveBtn');

        if (!editor || !commentField) return;

        const newContent = editor.value.trim();
        const changeComment = commentField.value.trim();

        // Validation
        if (!newContent) {
            showNotification('Content cannot be empty', 'error');
            return;
        }

        if (changeComment.length < 10) {
            showNotification('Change comment must be at least 10 characters', 'error');
            commentField.focus();
            return;
        }

        if (changeComment.length > 500) {
            showNotification('Change comment must be less than 500 characters', 'error');
            return;
        }

        if (newContent === this.originalContent) {
            showNotification('No changes detected', 'info');
            return;
        }

        // Disable save button
        saveBtn.disabled = true;
        saveBtn.textContent = '💾 Saving...';

        try {
            const token = window.authManager?.getIdToken();
            if (!token) {
                throw new Error('Not authenticated');
            }
            
            const response = await fetch(`${API_ENDPOINT}/kb-document/${this.currentDocument.id}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: newContent,
                    change_comment: changeComment
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to save document');
            }

            const data = await response.json();

            // Update state
            this.originalContent = newContent;
            this.hasUnsavedChanges = false;
            commentField.value = '';

            // Show success message with points
            showNotification(
                `✅ Document saved! You earned ${data.contribution_points} points. Ingestion in progress...`,
                'success'
            );

            // Optionally show ingestion status
            if (data.ingestion_job_id) {
                setTimeout(() => {
                    this.checkIngestionStatus(data.ingestion_job_id);
                }, 3000);
            }

        } catch (error) {
            console.error('Error saving document:', error);
            showNotification(error.message || 'Failed to save document', 'error');
        } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = '💾 Save Changes';
        }
    }

    /**
     * Check ingestion status
     */
    async checkIngestionStatus(jobId) {
        try {
            const token = window.authManager?.getIdToken();
            if (!token) {
                throw new Error('Not authenticated');
            }
            
            const response = await fetch(`${API_ENDPOINT}/kb-ingestion-status/${jobId}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.status === 'COMPLETE') {
                    showNotification('✅ Knowledge Base updated successfully!', 'success');
                } else if (data.status === 'FAILED') {
                    showNotification('⚠️ Ingestion failed. Please contact support.', 'error');
                } else {
                    showNotification(`Ingestion status: ${data.status}`, 'info');
                }
            }
        } catch (error) {
            console.error('Error checking ingestion status:', error);
        }
    }

    /**
     * Show user's contributions
     */
    async showContributions() {
        const modal = document.querySelector('.kb-editor-modal .modal-content');
        
        modal.innerHTML = `
            <div class="kb-editor-header">
                <button class="back-btn" onclick="kbEditor.showEditor()">← Back</button>
                <h2>📊 My Contributions</h2>
                <button class="close-btn" onclick="kbEditor.closeEditor()">&times;</button>
            </div>
            
            <div class="kb-editor-body">
                <div class="kb-contributions-container" id="contributionsContainer">
                    <div class="loading-spinner">Loading contributions...</div>
                </div>
            </div>
        `;

        try {
            const token = window.authManager?.getIdToken();
            if (!token) {
                throw new Error('Not authenticated');
            }
            
            const response = await fetch(`${API_ENDPOINT}/kb-my-contributions?limit=20`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load contributions');
            }

            const data = await response.json();
            const container = document.getElementById('contributionsContainer');

            container.innerHTML = `
                <div class="kb-stats-card">
                    <h3>${data.display_name}</h3>
                    <div class="kb-stats-grid">
                        <div class="stat-item">
                            <div class="stat-value">${data.stats.total_edits}</div>
                            <div class="stat-label">Total Edits</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${data.stats.total_lines_added}</div>
                            <div class="stat-label">Lines Added</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${data.stats.documents_edited_count}</div>
                            <div class="stat-label">Documents</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${data.stats.total_points || 0}</div>
                            <div class="stat-label">Points</div>
                        </div>
                    </div>
                </div>
                
                <h3>Recent Contributions</h3>
                <div class="kb-contributions-list">
                    ${data.recent_contributions.length > 0 ? 
                        data.recent_contributions.map(contrib => `
                            <div class="kb-contribution-item">
                                <div class="contrib-header">
                                    <strong>${contrib.document_name}</strong>
                                    <span class="contrib-date">${new Date(contrib.timestamp).toLocaleDateString()}</span>
                                </div>
                                <p class="contrib-comment">${contrib.change_comment}</p>
                                <div class="contrib-stats">
                                    <span class="stat-positive">+${contrib.lines_added}</span>
                                    <span class="stat-negative">-${contrib.lines_removed}</span>
                                    <span class="stat-modified">~${contrib.lines_modified}</span>
                                </div>
                            </div>
                        `).join('') :
                        '<p class="no-contributions">No contributions yet. Start editing!</p>'
                    }
                </div>
            `;

        } catch (error) {
            console.error('Error loading contributions:', error);
            document.getElementById('contributionsContainer').innerHTML = `
                <div class="error-message">
                    <p>Failed to load contributions</p>
                    <button onclick="kbEditor.showContributions()">Retry</button>
                </div>
            `;
        }
    }

    /**
     * Show contributor leaderboard
     */
    async showLeaderboard() {
        const modal = document.querySelector('.kb-editor-modal .modal-content');
        
        modal.innerHTML = `
            <div class="kb-editor-header">
                <button class="back-btn" onclick="kbEditor.showEditor()">← Back</button>
                <h2>🏆 Contributor Leaderboard</h2>
                <button class="close-btn" onclick="kbEditor.closeEditor()">&times;</button>
            </div>
            
            <div class="kb-editor-toolbar">
                <div class="kb-period-selector">
                    <button class="period-btn active" onclick="kbEditor.loadLeaderboard('month')">This Month</button>
                    <button class="period-btn" onclick="kbEditor.loadLeaderboard('all')">All Time</button>
                </div>
            </div>
            
            <div class="kb-editor-body">
                <div class="kb-leaderboard-container" id="leaderboardContainer">
                    <div class="loading-spinner">Loading leaderboard...</div>
                </div>
            </div>
        `;

        await this.loadLeaderboard('month');
    }

    /**
     * Load leaderboard data
     */
    async loadLeaderboard(period) {
        const container = document.getElementById('leaderboardContainer');
        if (!container) return;

        // Update active button
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.classList.remove('active');
            if ((period === 'month' && btn.textContent === 'This Month') ||
                (period === 'all' && btn.textContent === 'All Time')) {
                btn.classList.add('active');
            }
        });

        container.innerHTML = '<div class="loading-spinner">Loading...</div>';

        try {
            const token = window.authManager?.getIdToken();
            if (!token) {
                throw new Error('Not authenticated');
            }
            
            const response = await fetch(`${API_ENDPOINT}/kb-contributors?period=${period}&limit=10`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load leaderboard');
            }

            const data = await response.json();

            if (data.contributors.length === 0) {
                container.innerHTML = '<p class="no-contributors">No contributors yet. Be the first!</p>';
                return;
            }

            container.innerHTML = `
                <div class="kb-leaderboard-list">
                    ${data.contributors.map(contrib => `
                        <div class="kb-leaderboard-item ${contrib.rank <= 3 ? 'top-rank' : ''}">
                            <div class="rank-badge rank-${contrib.rank}">
                                ${contrib.rank === 1 ? '🥇' : contrib.rank === 2 ? '🥈' : contrib.rank === 3 ? '🥉' : `#${contrib.rank}`}
                            </div>
                            <div class="contributor-info">
                                <div class="contributor-name">${contrib.display_name}</div>
                                <div class="contributor-stats">
                                    ${contrib.total_edits} edits • ${contrib.lines_added} lines • ${contrib.documents_edited} docs
                                </div>
                                ${contrib.latest_contribution ? `
                                    <div class="contributor-latest">
                                        Latest: ${contrib.latest_contribution.document} 
                                        (${new Date(contrib.latest_contribution.timestamp).toLocaleDateString()})
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;

        } catch (error) {
            console.error('Error loading leaderboard:', error);
            container.innerHTML = `
                <div class="error-message">
                    <p>Failed to load leaderboard</p>
                    <button onclick="kbEditor.loadLeaderboard('${period}')">Retry</button>
                </div>
            `;
        }
    }

    /**
     * Close editor modal
     */
    closeEditor() {
        if (this.hasUnsavedChanges) {
            if (!confirm('You have unsaved changes. Are you sure you want to close?')) {
                return;
            }
        }

        const modal = document.querySelector('.kb-editor-modal');
        if (modal) {
            modal.remove();
        }

        this.currentDocument = null;
        this.originalContent = null;
        this.hasUnsavedChanges = false;
    }
}

// Initialize global KB editor instance
window.kbEditor = new KBEditor();
window.kbEditor.init(); console.log('KB Editor initialized and assigned to window.kbEditor');

