// Zoom/Presentation Mode for EUC Content Hub
// Issue #12 Implementation

class ZoomMode {
    constructor() {
        this.isActive = false;
        this.currentIndex = 0;
        this.posts = [];
        this.modal = null;
        this.init();
    }

    init() {
        // Create zoom mode modal
        this.createModal();
        // Add keyboard listeners
        this.setupKeyboardListeners();
        // Add zoom buttons to post cards
        this.addZoomButtonsToCards();
    }

    createModal() {
        const modal = document.createElement('div');
        modal.id = 'zoomModal';
        modal.className = 'zoom-modal';
        modal.innerHTML = `
            <div class="zoom-overlay"></div>
            <div class="zoom-content">
                <button class="zoom-close" title="Close (ESC)">×</button>
                <button class="zoom-nav zoom-prev" title="Previous (←)">‹</button>
                <button class="zoom-nav zoom-next" title="Next (→)">›</button>
                <div class="zoom-card" id="zoomCard"></div>
                <div class="zoom-counter" id="zoomCounter"></div>
            </div>
        `;
        document.body.appendChild(modal);
        this.modal = modal;

        // Event listeners
        modal.querySelector('.zoom-close').addEventListener('click', () => this.close());
        modal.querySelector('.zoom-prev').addEventListener('click', () => this.navigate(-1));
        modal.querySelector('.zoom-next').addEventListener('click', () => this.navigate(1));
        modal.querySelector('.zoom-overlay').addEventListener('click', () => this.close());
    }

    setupKeyboardListeners() {
        document.addEventListener('keydown', (e) => {
            if (!this.isActive) return;

            switch(e.key) {
                case 'Escape':
                    this.close();
                    break;
                case 'ArrowLeft':
                    this.navigate(-1);
                    break;
                case 'ArrowRight':
                case ' ':
                    e.preventDefault();
                    this.navigate(1);
                    break;
                case 'Home':
                    this.goToIndex(0);
                    break;
                case 'End':
                    this.goToIndex(this.posts.length - 1);
                    break;
            }
        });
    }

    addZoomButtonsToCards() {
        // This will be called after posts are rendered
        // We'll add a mutation observer to catch dynamically added cards
        const observer = new MutationObserver(() => {
            this.attachZoomButtons();
        });

        const postsContainer = document.getElementById('postsContainer');
        if (postsContainer) {
            observer.observe(postsContainer, { childList: true, subtree: false });
            // Also attach immediately in case posts are already there
            setTimeout(() => this.attachZoomButtons(), 1000);
        }
    }

    attachZoomButtons() {
        const postCards = document.querySelectorAll('.post-card');
        console.log('Attaching zoom buttons to', postCards.length, 'cards');
        
        postCards.forEach((card, index) => {
            // Check if zoom button already exists
            if (card.querySelector('.zoom-btn')) return;

            const zoomBtn = document.createElement('button');
            zoomBtn.className = 'zoom-btn';
            zoomBtn.innerHTML = '🔍';
            zoomBtn.title = 'Open in presentation mode';
            zoomBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                console.log('Zoom button clicked, index:', index);
                this.open(index);
            });

            // Add to post header
            const postHeader = card.querySelector('.post-header');
            if (postHeader) {
                postHeader.appendChild(zoomBtn);
            }
        });
    }

    open(startIndex = 0) {
        // Get posts from the currently rendered post cards
        const postCards = document.querySelectorAll('.post-card');
        
        console.log('Opening zoom mode, found', postCards.length, 'post cards');
        
        if (postCards.length === 0) {
            console.error('No post cards found in DOM');
            alert('No posts available to display');
            return;
        }

        // Build posts array from the DOM
        this.posts = Array.from(postCards).map(card => {
            return {
                post_id: card.dataset.postId,
                title: card.querySelector('.post-title a')?.textContent || 'Untitled',
                authors: card.querySelector('.meta-item:nth-child(1) span:last-child')?.textContent || 'Unknown',
                date_published: card.querySelector('.meta-item:nth-child(2) span:last-child')?.textContent?.replace('Published: ', '') || '',
                summary: card.querySelector('.post-summary')?.textContent || 'No summary available',
                url: card.querySelector('.post-title a')?.href || '#',
                source: card.querySelector('.post-title a')?.href?.includes('builder.aws') ? 'builder.aws.com' : 'aws.amazon.com',
                label: card.querySelector('.label-badge span:nth-child(2)')?.textContent || 'Uncategorized',
                label_confidence: parseFloat(card.querySelector('.label-confidence')?.textContent?.replace('%', '') || '0') / 100,
                love_votes: parseInt(card.querySelector('.love-count')?.textContent || '0'),
                needs_update_votes: parseInt(card.querySelector('.needs-update .vote-count')?.textContent || '0'),
                remove_post_votes: parseInt(card.querySelector('.remove-post .vote-count')?.textContent || '0')
            };
        });

        console.log('Built posts array with', this.posts.length, 'posts');

        this.currentIndex = startIndex;
        this.isActive = true;
        this.modal.classList.add('active');
        document.body.style.overflow = 'hidden';
        this.render();
    }

    close() {
        this.isActive = false;
        this.modal.classList.remove('active');
        document.body.style.overflow = '';
    }

    navigate(direction) {
        const newIndex = this.currentIndex + direction;
        if (newIndex >= 0 && newIndex < this.posts.length) {
            this.currentIndex = newIndex;
            this.render();
        }
    }

    goToIndex(index) {
        if (index >= 0 && index < this.posts.length) {
            this.currentIndex = index;
            this.render();
        }
    }

    render() {
        const post = this.posts[this.currentIndex];
        if (!post) return;

        const card = document.getElementById('zoomCard');
        const counter = document.getElementById('zoomCounter');

        // Format data
        const title = post.title || 'Untitled';
        const authors = post.authors || 'Unknown Author';
        const datePublished = this.formatDate(post.date_published);
        const summary = post.summary || 'No summary available';
        const url = post.url || '#';
        const source = post.source || 'aws.amazon.com';
        const label = post.label || 'Uncategorized';
        const labelConfidence = post.label_confidence ? Math.round(post.label_confidence * 100) : 0;
        const loveVotes = post.love_votes || 0;
        const needsUpdateVotes = post.needs_update_votes || 0;
        const removePostVotes = post.remove_post_votes || 0;

        // Get label config
        const labelConfig = this.getLabelConfig(label);

        // Render card
        card.innerHTML = `
            <div class="zoom-source-badge">${this.escapeHtml(source)}</div>
            <h1 class="zoom-title">${this.escapeHtml(title)}</h1>
            <div class="zoom-label-badge" style="background: ${labelConfig.color}">
                ${labelConfig.icon} ${this.escapeHtml(label)} 
                <span class="zoom-label-confidence">${labelConfidence}%</span>
            </div>
            <p class="zoom-summary">${this.escapeHtml(summary)}</p>
            <div class="zoom-meta">
                <div class="zoom-meta-item">
                    <span class="zoom-meta-icon">👤</span>
                    <span>${this.escapeHtml(authors)}</span>
                </div>
                <div class="zoom-meta-item">
                    <span class="zoom-meta-icon">📅</span>
                    <span>${datePublished}</span>
                </div>
            </div>
            <div class="zoom-votes">
                <div class="zoom-vote-item love">
                    <span class="zoom-vote-icon">❤️</span>
                    <span class="zoom-vote-count">${loveVotes}</span>
                    <span class="zoom-vote-label">Loved</span>
                </div>
                <div class="zoom-vote-item update">
                    <span class="zoom-vote-icon">🔧</span>
                    <span class="zoom-vote-count">${needsUpdateVotes}</span>
                    <span class="zoom-vote-label">Needs Update</span>
                </div>
                <div class="zoom-vote-item remove">
                    <span class="zoom-vote-icon">🗑️</span>
                    <span class="zoom-vote-count">${removePostVotes}</span>
                    <span class="zoom-vote-label">Remove</span>
                </div>
            </div>
            <a href="${url}" target="_blank" rel="noopener noreferrer" class="zoom-open-btn">
                Open Article →
            </a>
        `;

        // Update counter
        counter.textContent = `${this.currentIndex + 1} of ${this.posts.length}`;

        // Update navigation button states
        const prevBtn = this.modal.querySelector('.zoom-prev');
        const nextBtn = this.modal.querySelector('.zoom-next');
        prevBtn.disabled = this.currentIndex === 0;
        nextBtn.disabled = this.currentIndex === this.posts.length - 1;
    }

    getLabelConfig(label) {
        const configs = {
            'Announcement': { icon: '📢', color: '#3b82f6' },
            'Best Practices': { icon: '✅', color: '#10b981' },
            'Curation': { icon: '📚', color: '#8b5cf6' },
            'Customer Story': { icon: '🏢', color: '#f59e0b' },
            'Technical How-To': { icon: '🔧', color: '#ef4444' },
            'Thought Leadership': { icon: '💡', color: '#ec4899' }
        };
        return configs[label] || { icon: '🏷️', color: '#6b7280' };
    }

    formatDate(dateString) {
        if (!dateString) return 'Unknown date';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize zoom mode when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.zoomMode = new ZoomMode();
    console.log('Zoom mode initialized');
    
    // Expose a function to refresh zoom buttons after posts are rendered
    window.refreshZoomButtons = () => {
        if (window.zoomMode) {
            window.zoomMode.attachZoomButtons();
        }
    };
});
