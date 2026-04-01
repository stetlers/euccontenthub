// Configuration - Detect environment and use appropriate API endpoint
const isStagingEnv = window.location.hostname === 'staging.awseuccontent.com';
const API_ENDPOINT = isStagingEnv
    ? 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'
    : 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod';

let allPosts = [];
let filteredPosts = [];
let voterId = null;
let userBookmarks = []; // Track user's bookmarks
let currentFilter = 'all'; // Track current filter
let currentLabelFilters = []; // Track selected label filters (can be multiple)
let currentSourceFilter = 'all'; // Track source filter (all, aws.amazon.com, builder.aws.com)
const SOURCE_FILTER_CONFIG = [
    { label: 'All Sources', value: 'all', icon: '🌐' },
    { label: 'AWS Blog', value: 'aws-blog', icon: '📝' },
    { label: 'Builder.AWS', value: 'builder.aws.com', icon: '🏗️' }
];
let cartManager = null; // Cart manager instance
let cartUI = null; // Cart UI instance
let heartbeatSent = false; // Ensure only one heartbeat per page load

// Chart instances
let leaderboardChart = null;
let recentBlogsChart = null;
let topLovedChart = null;
let topVotesChart = null;
let topCommentsChart = null;

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    initializeVoterId();
    initializeCart();
    // Wait a bit for authManager to initialize, then update UI
    setTimeout(updateAuthUI, 100);
    loadPosts();
    loadUserBookmarks(); // Load bookmarks if authenticated
    setupEventListeners();
    setupPrivacyModal();
    setupTermsModal();
    setupDataDeletionModal();
    loadWhatsNewChiron();
    loadReleasesPerMonthChart();
    loadKBLeaderboard();
});

function updateAuthUI() {
    // Update UI elements based on authentication state
    const isAuthenticated = window.authManager && window.authManager.isAuthenticated();
    
    console.log('updateAuthUI called, isAuthenticated:', isAuthenticated);
    
    // Fire-and-forget heartbeat (once per page load)
    if (isAuthenticated && !heartbeatSent) {
        heartbeatSent = true;
        fetch(`${API_ENDPOINT}/heartbeat`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${window.authManager.getIdToken()}` }
        }).then(r => r.json()).then(data => processBadgeResponse(data)).catch(err => console.error('Heartbeat failed:', err));
    }
    
    // Hide/show crawler button
    const crawlBtn = document.getElementById('crawlBtn');
    if (crawlBtn) {
        crawlBtn.style.display = isAuthenticated ? 'flex' : 'none';
        console.log('Crawler button display set to:', crawlBtn.style.display);
    }

    // Update proposals dropdown/button based on auth state
    if (window.articleProposal && window.articleProposal.updateProposalsButton) {
        window.articleProposal.updateProposalsButton();
    }

    // Start pipeline status polling for authenticated users
    if (isAuthenticated) {
        startPipelineStatusPolling();
    }
}

// Make it globally accessible
window.updateAuthUI = updateAuthUI;

// Pipeline status polling
let pipelineStatusInterval = null;

function startPipelineStatusPolling() {
    if (pipelineStatusInterval) return;
    fetchPipelineStatus();
    pipelineStatusInterval = setInterval(fetchPipelineStatus, 30000);
}

function fetchPipelineStatus() {
    if (!window.authManager || !window.authManager.isAuthenticated()) return;
    const statusEl = document.getElementById('pipelineStatus');
    if (!statusEl) return;
    
    fetch(`${API_ENDPOINT}/pipeline-status`, {
        headers: { 'Authorization': `Bearer ${window.authManager.getIdToken()}` }
    })
    .then(r => r.json())
    .then(data => {
        const q = data.queue_depth || 0;
        const f = data.in_flight || 0;
        const d = data.dlq_depth || 0;
        statusEl.style.display = 'inline-flex';
        statusEl.innerHTML = `📊 Queue: ${q} | Processing: ${f}${d > 0 ? ` | <span style="color:#ef4444">⚠ DLQ: ${d}</span>` : ''}`;
    })
    .catch(() => {});
}

function initializeVoterId() {
    // Get or create a unique voter ID (stored in localStorage)
    voterId = localStorage.getItem('voter_id');
    if (!voterId) {
        voterId = 'voter_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('voter_id', voterId);
    }
}

function initializeCart() {
    // Initialize cart manager
    if (typeof CartManager !== 'undefined') {
        cartManager = new CartManager(API_ENDPOINT);
        window.cartManager = cartManager; // Make it globally accessible
        
        // Listen for cart changes to update UI
        cartManager.addListener((event, data) => {
            console.log('Cart event:', event, data);
            updateCartButtons();
            
            // Show notifications
            if (event === 'added') {
                showNotification('Added to cart', 'success');
            } else if (event === 'removed') {
                showNotification('Removed from cart', 'success');
            } else if (event === 'cleared') {
                showNotification('Cart cleared', 'success');
            } else if (event === 'error') {
                showNotification('Cart operation failed', 'error');
            }
        });
        
        console.log('Cart manager initialized');
    } else {
        console.warn('CartManager not loaded');
    }
}

async function loadUserBookmarks() {
    // Only load if authenticated
    if (!window.authManager || !window.authManager.isAuthenticated()) {
        userBookmarks = [];
        return;
    }
    
    try {
        const response = await fetch(`${API_ENDPOINT}/bookmarks`, {
            headers: {
                'Authorization': `Bearer ${window.authManager.getIdToken()}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            userBookmarks = data.bookmarks.map(post => post.post_id);
        }
    } catch (error) {
        console.error('Error loading bookmarks:', error);
        userBookmarks = [];
    }
}

function setupEventListeners() {
    const searchInput = document.getElementById('searchInput');
    const sortBy = document.getElementById('sortBy');
    const refreshBtn = document.getElementById('refreshBtn');
    const crawlBtn = document.getElementById('crawlBtn');
    const statCards = document.querySelectorAll('.stat-card');
    const closeModal = document.getElementById('closeModal');
    const commentsModal = document.getElementById('commentsModal');
    const submitComment = document.getElementById('submitComment');
    const commentText = document.getElementById('commentText');

    searchInput.addEventListener('input', debounce(handleSearch, 300));
    sortBy.addEventListener('change', handleSort);
    refreshBtn.addEventListener('click', loadPosts);
    crawlBtn.addEventListener('click', handleCrawl);
    
    // Add click handlers to stat cards
    statCards.forEach(card => {
        card.addEventListener('click', () => {
            const filter = card.dataset.filter;
            setFilter(filter);
        });
    });
    
    // Modal close handlers
    closeModal.addEventListener('click', closeCommentsModal);
    commentsModal.addEventListener('click', (e) => {
        if (e.target === commentsModal) {
            closeCommentsModal();
        }
    });
    
    // Comment submission
    submitComment.addEventListener('click', handleSubmitComment);
    
    // Character counter
    commentText.addEventListener('input', () => {
        const count = commentText.value.length;
        document.getElementById('charCount').textContent = `${count} / 1000`;
    });
    
    // ESC key to close modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && commentsModal.classList.contains('show')) {
            closeCommentsModal();
        }
    });
}

function setFilter(filter) {
    currentFilter = filter;
    
    // Update active state on stat cards
    document.querySelectorAll('.stat-card').forEach(card => {
        if (card.dataset.filter === filter) {
            card.classList.add('active');
        } else {
            card.classList.remove('active');
        }
    });
    
    // Update filter label
    const filterLabels = {
        'all': 'All Posts',
        'my-bookmarks': 'My Bookmarks',
        'most-loved': 'Most Loved Posts',
        'needs-review': 'Needs Review (0 votes)',
        'needs-update': 'Needs Update',
        'remove-post': 'Remove Post',
        'most-voted': 'Any Votes',
        'resolved': 'Resolved Posts'
    };
    
    document.getElementById('filterLabel').textContent = `Showing: ${filterLabels[filter]}`;
    
    // Apply filter
    handleFilter();
}

function renderLabelFilters() {
    const container = document.getElementById('labelFilters');
    if (!container) return;
    
    // Count posts by label
    const labelCounts = {
        'Announcement': 0,
        'Best Practices': 0,
        'Curation': 0,
        'Customer Story': 0,
        'Technical How-To': 0,
        'Thought Leadership': 0
    };
    
    allPosts.forEach(post => {
        const label = post.label;
        if (label && labelCounts.hasOwnProperty(label)) {
            labelCounts[label]++;
        }
    });
    
    // Label configurations
    const labelConfigs = [
        { label: 'Announcement', icon: '📢', text: 'Announcement' },
        { label: 'Best Practices', icon: '✅', text: 'Best Practices' },
        { label: 'Curation', icon: '📚', text: 'Curation' },
        { label: 'Customer Story', icon: '🏢', text: 'Customer Story' },
        { label: 'Technical How-To', icon: '🔧', text: 'Technical How-To' },
        { label: 'Thought Leadership', icon: '💡', text: 'Thought Leadership' }
    ];
    
    // Create filter buttons with multi-select support
    container.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
            <span style="font-weight: 600; color: #666;">Filter by Category:</span>
            ${labelConfigs.map(config => {
                const count = labelCounts[config.label] || 0;
                const activeClass = currentLabelFilters.includes(config.label) ? 'active' : '';
                
                return `
                    <button class="label-filter-btn ${activeClass}" data-label="${config.label}">
                        <span>${config.icon} ${config.text}</span>
                        <span class="label-filter-count">${count}</span>
                    </button>
                `;
            }).join('')}
            ${currentLabelFilters.length > 0 ? `
                <button class="label-filter-clear" onclick="clearLabelFilters()">
                    ✕ Clear All
                </button>
            ` : ''}
        </div>
    `;
    
    // Add click handlers for multi-select
    container.querySelectorAll('.label-filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const label = btn.dataset.label;
            toggleLabelFilter(label);
        });
    });
}

function toggleLabelFilter(label) {
    const index = currentLabelFilters.indexOf(label);
    
    if (index > -1) {
        // Remove if already selected
        currentLabelFilters.splice(index, 1);
    } else {
        // Add if not selected
        currentLabelFilters.push(label);
    }
    
    // Re-render filters and apply
    renderLabelFilters();
    handleFilter();
}

function clearLabelFilters() {
    currentLabelFilters = [];
    renderLabelFilters();
    handleFilter();
}

function renderSourceFilter() {
    const container = document.getElementById('sourceFilterContainer');
    if (!container) return;

    const counts = {};
    let total = allPosts.length;
    SOURCE_FILTER_CONFIG.forEach(cfg => {
        if (cfg.value === 'all') {
            counts[cfg.value] = total;
        } else if (cfg.value === 'aws-blog') {
            counts[cfg.value] = allPosts.filter(p => !p.source || p.source === 'aws-blog' || p.source === 'aws.amazon.com').length;
        } else {
            counts[cfg.value] = allPosts.filter(p => p.source === cfg.value).length;
        }
    });

    container.innerHTML = `
        <div class="source-filter-toggle">
            ${SOURCE_FILTER_CONFIG.map(cfg => `
                <button class="source-filter-btn ${currentSourceFilter === cfg.value ? 'active' : ''}"
                    data-source="${cfg.value}">
                    <span class="source-filter-icon">${cfg.icon}</span>
                    <span>${cfg.label}</span>
                    <span class="source-filter-count">${counts[cfg.value] || 0}</span>
                </button>
            `).join('')}
        </div>
    `;

    container.querySelectorAll('.source-filter-btn').forEach(btn => {
        btn.addEventListener('click', () => setSourceFilter(btn.dataset.source));
    });
}

function setSourceFilter(source) {
    currentSourceFilter = source;
    renderSourceFilter();
    handleFilter();
}

async function loadPosts() {
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const postsContainer = document.getElementById('postsContainer');

    console.log('Loading posts from:', API_ENDPOINT);
    loading.style.display = 'block';
    error.style.display = 'none';
    postsContainer.innerHTML = '';

    try {
        console.log('Fetching posts...');
        const response = await fetch(`${API_ENDPOINT}/posts`);
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch posts: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Received data:', data);
        allPosts = data.posts || [];
        filteredPosts = [...allPosts];
        console.log('Loaded', allPosts.length, 'posts');

        updateStats();
        renderSourceFilter();
        renderLabelFilters();
        handleFilter();
        loading.style.display = 'none';
        
        // Render charts
        renderCharts();
        
        // Initialize PanelExpander after charts are rendered
        if (!window.panelExpander) {
            window.panelExpander = new PanelExpander();
            window.panelExpander.init();
        }
        
        // Set initial filter to 'all' and mark it as active
        setFilter('all');
        
        // Initialize CartUI after posts are loaded
        if (cartManager && typeof CartUI !== 'undefined' && !cartUI) {
            cartUI = new CartUI(cartManager, allPosts);
            console.log('Cart UI initialized');
        }
    } catch (err) {
        console.error('Error loading posts:', err);
        console.error('Error details:', err.message, err.stack);
        loading.style.display = 'none';
        error.style.display = 'block';
        error.innerHTML = `<p>Error loading blog posts: ${err.message}</p><p>Check console for details.</p>`;
    }
}

function handleSearch(event) {
    const query = event.target.value.toLowerCase().trim();

    if (!query) {
        filteredPosts = [...allPosts];
    } else {
        filteredPosts = allPosts.filter(post => {
            const title = (post.title || '').toLowerCase();
            const authors = (post.authors || '').toLowerCase();
            const tags = (post.tags || '').toLowerCase();
            
            return title.includes(query) || 
                   authors.includes(query) || 
                   tags.includes(query);
        });
    }

    handleFilter();
}

function handleFilter() {
    const searchInput = document.getElementById('searchInput');
    const query = searchInput.value.toLowerCase().trim();

    // Start with all posts
    let posts = [...allPosts];

    // Apply source filter FIRST
    if (currentSourceFilter === 'aws-blog') {
        posts = posts.filter(post => !post.source || post.source === 'aws-blog' || post.source === 'aws.amazon.com');
    } else if (currentSourceFilter !== 'all') {
        posts = posts.filter(post => post.source === currentSourceFilter);
    }

    // Apply search query
    if (query) {
        posts = posts.filter(post => {
            const title = (post.title || '').toLowerCase();
            const authors = (post.authors || '').toLowerCase();
            const tags = (post.tags || '').toLowerCase();
            return title.includes(query) || authors.includes(query) || tags.includes(query);
        });
    }

    // Apply multi-label filter
    if (currentLabelFilters.length > 0) {
        posts = posts.filter(post => currentLabelFilters.includes(post.label));
    }

    // Apply current filter
    switch (currentFilter) {
        case 'my-bookmarks':
            filteredPosts = posts.filter(post => userBookmarks.includes(post.post_id));
            break;
        case 'needs-review':
            filteredPosts = posts.filter(post => 
                (post.needs_update_votes || 0) === 0 && 
                (post.remove_post_votes || 0) === 0 &&
                (post.status || 'pending') === 'pending'
            );
            break;
        case 'most-loved':
            filteredPosts = posts.filter(post => 
                (post.love_votes || 0) > 0
            );
            break;
        case 'needs-update':
            filteredPosts = posts.filter(post => 
                (post.needs_update_votes || 0) > 0 &&
                (post.status || 'pending') === 'pending'
            );
            break;
        case 'remove-post':
            filteredPosts = posts.filter(post => 
                (post.remove_post_votes || 0) > 0 &&
                (post.status || 'pending') === 'pending'
            );
            break;
        case 'most-voted':
            filteredPosts = posts.filter(post => 
                ((post.needs_update_votes || 0) > 0 || (post.remove_post_votes || 0) > 0) &&
                (post.status || 'pending') === 'pending'
            );
            break;
        case 'resolved':
            filteredPosts = posts.filter(post => (post.status || 'pending') === 'resolved');
            break;
        default:
            filteredPosts = posts;
    }

    updateStats();
    renderLabelFilters();
    handleSort();
}

function handleSort() {
    const sortBy = document.getElementById('sortBy').value;

    filteredPosts.sort((a, b) => {
        switch (sortBy) {
            case 'date-desc':
                return new Date(b.date_published || 0) - new Date(a.date_published || 0);
            case 'date-asc':
                return new Date(a.date_published || 0) - new Date(b.date_published || 0);
            case 'title-asc':
                return (a.title || '').localeCompare(b.title || '');
            case 'title-desc':
                return (b.title || '').localeCompare(a.title || '');
            case 'votes-desc':
                const votesA = (a.needs_update_votes || 0) + (a.remove_post_votes || 0);
                const votesB = (b.needs_update_votes || 0) + (b.remove_post_votes || 0);
                return votesB - votesA;
            default:
                return 0;
        }
    });

    renderPosts();
}

function renderPosts() {
    const postsContainer = document.getElementById('postsContainer');
    postsContainer.innerHTML = '';

    if (filteredPosts.length === 0) {
        postsContainer.innerHTML = `
            <div class="no-results">
                <h2>No posts found</h2>
                <p>Try adjusting your search or filter criteria</p>
            </div>
        `;
        // Update service name button even when no results
        setTimeout(addServiceNameButtonsToCards, 100);
        return;
    }

    filteredPosts.forEach(post => {
        const postCard = createPostCard(post);
        postsContainer.appendChild(postCard);
    });
    
    // Add service name buttons to cards after rendering
    setTimeout(addServiceNameButtonsToCards, 100);
}

function createLabelBadge(label, confidence) {
    if (!label) return '';
    
    // Map label to CSS class and icon
    const labelConfig = {
        'Announcement': { class: 'label-announcement', icon: '📢' },
        'Best Practices': { class: 'label-best-practices', icon: '✅' },
        'Curation': { class: 'label-curation', icon: '📚' },
        'Customer Story': { class: 'label-customer-story', icon: '🏢' },
        'Technical How-To': { class: 'label-technical-how-to', icon: '🔧' },
        'Thought Leadership': { class: 'label-thought-leadership', icon: '💡' }
    };
    
    const config = labelConfig[label] || { class: 'label-announcement', icon: '🏷️' };
    const confidencePercent = confidence ? Math.round(confidence * 100) : 0;
    
    return `
        <div class="label-badge ${config.class}" title="Confidence: ${confidencePercent}%">
            <span class="label-icon">${config.icon}</span>
            <span>${label}</span>
            <span class="label-confidence">${confidencePercent}%</span>
        </div>
    `;
}

function createPostCard(post) {
    const card = document.createElement('div');
    const status = post.status || 'pending';
    card.className = `post-card status-${status}`;
    card.dataset.postId = post.post_id;

    const title = post.title || 'Untitled';
    const authors = post.authors || 'Unknown Author';
    const datePublished = formatDate(post.date_published);
    const tags = post.tags ? post.tags.split(',').map(t => t.trim()).filter(t => t) : [];
    const url = post.url || '#';
    const needsUpdateVotes = post.needs_update_votes || 0;
    const removePostVotes = post.remove_post_votes || 0;
    const loveVotes = post.love_votes || 0;
    const voters = post.voters || [];
    const lovers = post.lovers || [];
    const hasVoted = voters.includes(voterId);
    const hasLoved = lovers.includes(voterId);
    const isBookmarked = userBookmarks.includes(post.post_id);
    const isInCart = cartManager ? cartManager.isInCart(post.post_id) : false;
    const commentCount = post.comment_count || 0;
    const resolvedDate = post.resolved_date ? formatDate(post.resolved_date) : null;
    const label = post.label || null;
    const labelConfidence = post.label_confidence || 0;
    const source = post.source || '';

    card.innerHTML = `
        <div class="post-flip-inner">
            <div class="post-flip-front">
                ${status === 'resolved' ? '<span class="post-status-badge resolved">✓ Resolved</span>' : ''}
                ${status === 'archived' ? '<span class="post-status-badge archived">📦 Archived</span>' : ''}
                <div class="post-front-title">
                    <a href="${url}" target="_blank" rel="noopener noreferrer" class="post-title-link">${escapeHtml(title)}</a>
                </div>
                <div class="post-front-author">👤 ${escapeHtml(authors)}</div>
                <div class="post-front-meta">
                    ${createLabelBadge(label, labelConfidence)}
                </div>
                <div class="post-front-actions">
                    <button class="post-action-btn love-btn ${hasLoved ? 'loved' : ''}" data-post-id="${post.post_id}" data-vote-type="love" ${hasLoved || status === 'resolved' ? 'disabled' : ''} title="${hasLoved ? 'Loved' : 'Love'}">${hasLoved ? '❤️' : '🤍'} <span>${loveVotes}</span></button>
                    <button class="post-action-btn vote-btn needs-update" data-post-id="${post.post_id}" data-vote-type="needs_update" ${hasVoted || status === 'resolved' ? 'disabled' : ''} title="Needs Update">🔧 <span>${needsUpdateVotes}</span></button>
                    <button class="post-action-btn vote-btn remove-post" data-post-id="${post.post_id}" data-vote-type="remove_post" ${hasVoted || status === 'resolved' ? 'disabled' : ''} title="Remove">🗑️ <span>${removePostVotes}</span></button>
                    <span class="post-action-btn comment-badge" data-post-id="${post.post_id}" data-post-title="${escapeHtml(title)}" title="Comments">💬 <span>${commentCount}</span></span>
                    <button class="post-action-btn bookmark-btn ${isBookmarked ? 'bookmarked' : ''}" data-post-id="${post.post_id}" title="${isBookmarked ? 'Unbookmark' : 'Bookmark'}">${isBookmarked ? '⭐' : '☆'}</button>
                    <button class="post-action-btn cart-btn ${isInCart ? 'in-cart' : ''}" data-post-id="${post.post_id}" title="${isInCart ? 'In cart' : 'Add to cart'}">${isInCart ? '✓' : '+'}</button>
                </div>
            </div>
            <div class="post-flip-back">
                <div class="post-back-summary">${post.summary ? escapeHtml(post.summary) : '<em>No AI summary available yet.</em>'}</div>
                <div class="post-back-meta">
                    <div>👤 ${escapeHtml(authors)}</div>
                    <div>📅 ${datePublished}</div>
                    ${status === 'resolved' && resolvedDate ? '<div>✅ Resolved: ' + resolvedDate + '</div>' : ''}
                </div>
                ${tags.length > 0 ? '<div class="post-back-tags">' + tags.slice(0, 5).map(tag => '<span class="post-back-tag">' + escapeHtml(tag) + '</span>').join('') + (tags.length > 5 ? '<span class="post-back-tag">+' + (tags.length - 5) + ' more</span>' : '') + '</div>' : ''}
                ${source ? '<div class="post-back-source">' + escapeHtml(source) + '</div>' : ''}
                <a href="${url}" target="_blank" rel="noopener noreferrer" class="post-back-link">View Post →</a>
            </div>
        </div>
    `;

    // Flip toggle
    card.addEventListener('click', () => card.classList.toggle('flipped'));

    // Event isolation
    card.querySelectorAll('.post-action-btn, .post-title-link, .post-back-link').forEach(el => {
        el.addEventListener('click', (e) => e.stopPropagation());
    });

    // Vote buttons
    card.querySelectorAll('.vote-btn:not([disabled])').forEach(btn => btn.addEventListener('click', handleVote));
    const loveBtn = card.querySelector('.love-btn:not([disabled])');
    if (loveBtn) loveBtn.addEventListener('click', handleVote);

    // Comment badge
    const commentBadge = card.querySelector('.comment-badge');
    if (commentBadge) commentBadge.addEventListener('click', () => openCommentsModal(post.post_id, title));

    // Bookmark
    const bookmarkBtn = card.querySelector('.bookmark-btn');
    if (bookmarkBtn) bookmarkBtn.addEventListener('click', () => handleBookmark(post.post_id, bookmarkBtn));

    // Cart
    const cartBtn = card.querySelector('.cart-btn');
    if (cartBtn) cartBtn.addEventListener('click', () => handleCart(post.post_id, cartBtn));

    return card;
}



async function handleVote(event) {
    // Check authentication first
    if (!window.authManager || !window.authManager.isAuthenticated()) {
        showNotification('Please sign in to vote', 'error');
        setTimeout(() => {
            window.authManager.signIn();
        }, 1500);
        return;
    }
    
    const button = event.currentTarget;
    const postId = button.dataset.postId;
    const voteType = button.dataset.voteType;
    const card = button.closest('.post-card');

    // Create ripple effect
    createRipple(event, button);

    // Add voting animation to button
    button.classList.add('voting');

    // Disable button immediately
    button.disabled = true;
    button.classList.add('disabled');

    try {
        // Use authenticated user ID instead of anonymous voter ID
        const userId = window.authManager.getUser().sub;
        
        const response = await fetch(`${API_ENDPOINT}/posts/${postId}/vote`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.authManager.getIdToken()}`
            },
            body: JSON.stringify({
                vote_type: voteType,
                voter_id: userId
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to vote');
        }

        const data = await response.json();
        processBadgeResponse(data);
        
        // Update the post in our local data
        const postIndex = allPosts.findIndex(p => p.post_id === postId);
        if (postIndex !== -1) {
            allPosts[postIndex] = data.post;
        }

        // Trigger success animations
        animateVoteSuccess(button, card);
        
        // Create confetti
        createConfetti(button);
        
        // Refresh the display
        setTimeout(() => {
            handleFilter();
        }, 300);
        
        // Show success message
        showNotification('Vote recorded successfully! 🎉', 'success');
    } catch (err) {
        console.error('Error voting:', err);
        showNotification(err.message || 'Failed to record vote', 'error');
        
        // Re-enable button on error
        button.disabled = false;
        button.classList.remove('disabled', 'voting');
    }
}

async function handleBookmark(postId, button) {
    // Check authentication first
    if (!window.authManager || !window.authManager.isAuthenticated()) {
        showNotification('Please sign in to bookmark posts', 'error');
        setTimeout(() => {
            window.authManager.signIn();
        }, 1500);
        return;
    }
    
    const isCurrentlyBookmarked = button.classList.contains('bookmarked');
    
    // Optimistic UI update
    button.classList.toggle('bookmarked');
    button.textContent = button.classList.contains('bookmarked') ? '⭐' : '☆';
    button.title = button.classList.contains('bookmarked') ? 'Remove bookmark' : 'Bookmark this post';
    
    try {
        const userId = window.authManager.getUser().sub;
        
        const response = await fetch(`${API_ENDPOINT}/posts/${postId}/bookmark`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.authManager.getIdToken()}`
            },
            body: JSON.stringify({
                user_id: userId
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to toggle bookmark');
        }
        
        const data = await response.json();
        processBadgeResponse(data);
        
        // Update local bookmarks array
        if (data.bookmarked) {
            if (!userBookmarks.includes(postId)) {
                userBookmarks.push(postId);
            }
            showNotification('Bookmark added! ⭐', 'success');
        } else {
            userBookmarks = userBookmarks.filter(id => id !== postId);
            showNotification('Bookmark removed', 'info');
        }
        
    } catch (error) {
        console.error('Error toggling bookmark:', error);
        // Revert UI on error
        button.classList.toggle('bookmarked');
        button.textContent = isCurrentlyBookmarked ? '⭐' : '☆';
        button.title = isCurrentlyBookmarked ? 'Remove bookmark' : 'Bookmark this post';
        showNotification('Failed to update bookmark', 'error');
    }
}

async function handleCart(postId, button) {
    // Check if cart manager is initialized
    if (!cartManager) {
        showNotification('Cart not available', 'error');
        return;
    }
    
    const isCurrentlyInCart = button.classList.contains('in-cart');
    
    try {
        if (isCurrentlyInCart) {
            // Remove from cart
            await cartManager.removeFromCart(postId);
        } else {
            // Add to cart
            await cartManager.addToCart(postId);
        }
        
        // UI will be updated by cart event listener
        
    } catch (error) {
        console.error('Error updating cart:', error);
        showNotification('Failed to update cart', 'error');
    }
}

function updateCartButtons() {
    // Update all cart buttons to reflect current cart state
    if (!cartManager) return;
    
    const cartButtons = document.querySelectorAll('.cart-btn');
    cartButtons.forEach(button => {
        const postId = button.dataset.postId;
        const isInCart = cartManager.isInCart(postId);
        
        if (isInCart) {
            button.classList.add('in-cart');
            button.querySelector('.cart-icon').textContent = '✓';
            button.title = 'Remove from cart';
        } else {
            button.classList.remove('in-cart');
            button.querySelector('.cart-icon').textContent = '+';
            button.title = 'Add to cart';
        }
    });
}

function createRipple(event, button) {
    const ripple = document.createElement('span');
    ripple.classList.add('ripple');
    
    const rect = button.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;
    
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    
    button.appendChild(ripple);
    
    setTimeout(() => ripple.remove(), 600);
}

function animateVoteSuccess(button, card) {
    // Add glow to card
    card.classList.add('vote-success');
    setTimeout(() => card.classList.remove('vote-success'), 1000);
    
    // Animate vote count
    const voteCount = button.querySelector('.vote-count');
    if (voteCount) {
        voteCount.classList.add('incrementing');
        setTimeout(() => voteCount.classList.remove('incrementing'), 500);
    }
    
    // Show checkmark
    const checkmark = document.createElement('div');
    checkmark.classList.add('vote-checkmark');
    checkmark.textContent = '✓';
    button.style.position = 'relative';
    button.appendChild(checkmark);
    
    setTimeout(() => checkmark.remove(), 600);
}

function createConfetti(button) {
    const rect = button.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    
    // Create 20 confetti pieces
    for (let i = 0; i < 20; i++) {
        const confetti = document.createElement('div');
        confetti.classList.add('confetti');
        
        // Random position around button
        const angle = (Math.PI * 2 * i) / 20;
        const velocity = 50 + Math.random() * 50;
        const x = centerX + Math.cos(angle) * velocity;
        const y = centerY + Math.sin(angle) * velocity;
        
        confetti.style.left = x + 'px';
        confetti.style.top = y + 'px';
        confetti.style.animationDelay = (i * 0.02) + 's';
        
        // Random rotation
        confetti.style.transform = `rotate(${Math.random() * 360}deg)`;
        
        document.body.appendChild(confetti);
        
        // Remove after animation
        setTimeout(() => confetti.remove(), 1500);
    }
}

function updateStats() {
    // Total posts
    document.getElementById('totalPosts').textContent = allPosts.length;
    
    // Filtered count
    document.getElementById('filteredCount').textContent = filteredPosts.length;
    
    // Count posts by category (only pending posts for voting categories)
    const myBookmarksCount = allPosts.filter(p => userBookmarks.includes(p.post_id)).length;
    
    const needsReviewCount = allPosts.filter(p => 
        (p.needs_update_votes || 0) === 0 && 
        (p.remove_post_votes || 0) === 0 &&
        (p.status || 'pending') === 'pending'
    ).length;
    
    const mostLovedCount = allPosts.filter(p => 
        (p.love_votes || 0) > 0
    ).length;
    
    const needsUpdateCount = allPosts.filter(p => 
        (p.needs_update_votes || 0) > 0 &&
        (p.status || 'pending') === 'pending'
    ).length;
    
    const removePostCount = allPosts.filter(p => 
        (p.remove_post_votes || 0) > 0 &&
        (p.status || 'pending') === 'pending'
    ).length;
    
    const mostVotedCount = allPosts.filter(p => 
        ((p.needs_update_votes || 0) > 0 || (p.remove_post_votes || 0) > 0) &&
        (p.status || 'pending') === 'pending'
    ).length;
    
    const resolvedCount = allPosts.filter(p => (p.status || 'pending') === 'resolved').length;
    
    // Update stat cards
    const myBookmarksEl = document.getElementById('myBookmarksCount');
    if (myBookmarksEl) {
        myBookmarksEl.textContent = myBookmarksCount;
        // Show/hide bookmark card based on auth status
        const bookmarkCard = myBookmarksEl.closest('.stat-card');
        if (bookmarkCard) {
            bookmarkCard.style.display = (window.authManager && window.authManager.isAuthenticated()) ? 'block' : 'none';
        }
    }
    
    // Show/hide crawler button based on auth status
    const crawlBtn = document.getElementById('crawlBtn');
    if (crawlBtn) {
        crawlBtn.style.display = (window.authManager && window.authManager.isAuthenticated()) ? 'flex' : 'none';
    }
    
    document.getElementById('needsReviewCount').textContent = needsReviewCount;
    document.getElementById('mostLovedCount').textContent = mostLovedCount;
    document.getElementById('needsUpdateCount').textContent = needsUpdateCount;
    document.getElementById('removePostCount').textContent = removePostCount;
    document.getElementById('mostVotedCount').textContent = mostVotedCount;
    document.getElementById('resolvedCount').textContent = resolvedCount;
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.classList.add('show');
    }, 10);

    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Badge Toast Notifications
function showBadgeToast(badge) {
    const toast = document.createElement('div');
    toast.className = 'badge-toast';
    toast.innerHTML = `
        <div class="badge-toast-icon">${badge.icon}</div>
        <div class="badge-toast-content">
            <div class="badge-toast-title">🎉 Achievement Unlocked!</div>
            <div class="badge-toast-name">${badge.name}</div>
        </div>
        <button class="badge-toast-close" onclick="this.parentElement.remove()">×</button>
    `;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

function processBadgeResponse(responseData) {
    const newBadges = responseData?.new_badges;
    if (!newBadges || !Array.isArray(newBadges) || newBadges.length === 0) return;
    newBadges.forEach((badge, index) => {
        setTimeout(() => showBadgeToast(badge), index * 1000);
    });
}
window.processBadgeResponse = processBadgeResponse;

// What's New Chiron (News Ticker)
const SERVICE_TAG_CSS_MAP = {
    'WorkSpaces Personal': 'workspaces-personal',
    'WorkSpaces Applications': 'workspaces-applications',
    'WorkSpaces Core': 'workspaces-core',
    'WorkSpaces Secure Browser': 'workspaces-secure-browser',
    'WorkSpaces Thin Client': 'workspaces-thin-client',
    'DCV': 'dcv'
};

async function loadWhatsNewChiron() {
    const chiron = document.getElementById('whatsNewChiron');
    const track = document.getElementById('chironTrack');
    if (!chiron || !track) return;

    try {
        const response = await fetch(`${API_ENDPOINT}/whats-new`);
        if (!response.ok) return;

        const data = await response.json();
        let announcements = data.announcements || data;
        if (!Array.isArray(announcements) || announcements.length === 0) return;

        // Sort by date descending (most recent first)
        announcements.sort((a, b) => (b.date_published || '').localeCompare(a.date_published || ''));

        const itemsHtml = announcements.map(a => {
            const cssClass = SERVICE_TAG_CSS_MAP[a.service_tag] || '';
            const title = escapeHtml(a.title || '');
            const tag = escapeHtml(a.service_tag || '');
            const url = escapeHtml(a.url || '#');
            const date = formatDate(a.date_published);
            return `<span class="chiron-item">` +
                `<span class="service-badge ${cssClass}">${tag}</span>` +
                `<a href="${url}" target="_blank" rel="noopener" class="chiron-title">${title}</a>` +
                `<span class="chiron-date">${date}</span>` +
                `</span>`;
        }).join('');

        // Duplicate for seamless looping
        track.innerHTML = itemsHtml + itemsHtml;

        // Remove CSS animation — use JS for scrolling
        track.style.animation = 'none';

        // JS-based smooth scrolling
        let scrollPos = 0;
        let speed = 1.5;
        let paused = false;
        const halfWidth = track.scrollWidth / 2;

        function scrollTicker() {
            if (!paused) {
                scrollPos += speed;
                if (scrollPos >= halfWidth) scrollPos -= halfWidth;
                track.style.transform = `translateX(-${scrollPos}px)`;
            }
            requestAnimationFrame(scrollTicker);
        }
        requestAnimationFrame(scrollTicker);

        // Pause on hover over the track
        chiron.querySelector('.chiron-track-container').addEventListener('mouseenter', () => { paused = true; });
        chiron.querySelector('.chiron-track-container').addEventListener('mouseleave', () => { paused = false; });

        // Speed controls
        const controlsDiv = document.createElement('div');
        controlsDiv.className = 'chiron-controls';
        controlsDiv.innerHTML = `
            <button class="chiron-speed-btn chiron-rewind" title="Slower">⏪</button>
            <button class="chiron-speed-btn chiron-forward" title="Faster">⏩</button>
        `;
        chiron.appendChild(controlsDiv);

        controlsDiv.querySelector('.chiron-rewind').addEventListener('click', () => {
            speed = Math.max(0.5, speed / 1.5);
        });
        controlsDiv.querySelector('.chiron-forward').addEventListener('click', () => {
            speed = Math.min(10, speed * 1.5);
        });

        chiron.style.display = 'flex';
    } catch (err) {
        console.warn('Failed to load What\'s New chiron:', err);
    }
}

// Releases per Month Chart (trailing 12 months)
async function loadReleasesPerMonthChart() {
    const canvas = document.getElementById('releasesPerMonthChart');
    if (!canvas) return;

    try {
        const response = await fetch(`${API_ENDPOINT}/whats-new`);
        if (!response.ok) return;

        const data = await response.json();
        const announcements = data.announcements || [];

        // Build trailing 12 months
        const now = new Date();
        const months = [];
        for (let i = 11; i >= 0; i--) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
            months.push(d.toISOString().slice(0, 7)); // YYYY-MM
        }

        const monthLabels = months.map(m => {
            const [y, mo] = m.split('-');
            return new Date(y, mo - 1).toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
        });

        // Aggregate count per month (parse dates flexibly)
        const counts = months.map(m => {
            return announcements.filter(a => {
                const dp = a.date_published || '';
                if (dp.startsWith(m)) return true;
                try {
                    const d = new Date(dp);
                    if (!isNaN(d)) return d.toISOString().slice(0, 7) === m;
                } catch (e) {}
                return false;
            }).length;
        });

        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: monthLabels,
                datasets: [{
                    label: 'Releases',
                    data: counts,
                    backgroundColor: '#FF9900',
                    borderRadius: 4,
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    y: { beginAtZero: true, ticks: { stepSize: 1 } },
                },
            },
        });
    } catch (err) {
        console.warn('Failed to load releases chart:', err);
    }
}

// KB Contributor Leaderboard
async function loadKBLeaderboard() {
    const container = document.getElementById('kbLeaderboard');
    if (!container) return;

    try {
        const response = await fetch(`${API_ENDPOINT}/kb-contributors?period=all&limit=10`);
        if (!response.ok) {
            container.innerHTML = '<p class="kb-leaderboard-empty">No contributors yet</p>';
            return;
        }

        const data = await response.json();
        const contributors = data.contributors || data.leaderboard || [];

        if (contributors.length === 0) {
            container.innerHTML = '<p class="kb-leaderboard-empty">No contributors yet. Be the first!</p>';
            return;
        }

        const rankBadges = ['🥇', '🥈', '🥉'];
        container.innerHTML = contributors.slice(0, 10).map((c, i) => `
            <div class="kb-leaderboard-item">
                <span class="kb-leaderboard-rank">${rankBadges[i] || (i + 1)}</span>
                <span class="kb-leaderboard-name">${(c.display_name || c.user_id || 'Anonymous').replace(/</g, '&lt;')}</span>
                <div class="kb-leaderboard-stats">
                    <span>${c.total_edits || 0} edits</span>
                    <span>${c.total_points || 0} pts</span>
                </div>
            </div>
        `).join('');
    } catch (err) {
        console.warn('Failed to load KB leaderboard:', err);
        container.innerHTML = '<p class="kb-leaderboard-empty">No contributors yet</p>';
    }
}

function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch {
        return 'Unknown';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}


async function handleResolve(event) {
    const button = event.currentTarget;
    const postId = button.dataset.postId;
    const card = button.closest('.post-card');
    
    // Confirm action
    if (!confirm('Mark this post as resolved? This indicates the blog has been updated or removed.')) {
        return;
    }
    
    button.disabled = true;
    button.textContent = 'Resolving...';
    
    try {
        const response = await fetch(`${API_ENDPOINT}/posts/${postId}/resolve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                status: 'resolved',
                resolved_by: voterId
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to resolve post');
        }
        
        const data = await response.json();
        
        // Update the post in our local data
        const postIndex = allPosts.findIndex(p => p.post_id === postId);
        if (postIndex !== -1) {
            allPosts[postIndex] = data.post;
        }
        
        // Add success animation
        card.classList.add('vote-success');
        
        // Refresh the display
        setTimeout(() => {
            handleFilter();
        }, 500);
        
        showNotification('Post marked as resolved! ✅', 'success');
    } catch (err) {
        console.error('Error resolving post:', err);
        showNotification(err.message || 'Failed to resolve post', 'error');
        button.disabled = false;
        button.innerHTML = '<span class="resolve-icon">✓</span><span>Mark as Resolved</span>';
    }
}

async function handleUnresolve(event) {
    const button = event.currentTarget;
    const postId = button.dataset.postId;
    const card = button.closest('.post-card');
    
    button.disabled = true;
    button.textContent = 'Reopening...';
    
    try {
        const response = await fetch(`${API_ENDPOINT}/posts/${postId}/resolve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                status: 'pending'
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to reopen post');
        }
        
        const data = await response.json();
        
        // Update the post in our local data
        const postIndex = allPosts.findIndex(p => p.post_id === postId);
        if (postIndex !== -1) {
            allPosts[postIndex] = data.post;
        }
        
        // Refresh the display
        setTimeout(() => {
            handleFilter();
        }, 300);
        
        showNotification('Post reopened for review', 'success');
    } catch (err) {
        console.error('Error reopening post:', err);
        showNotification(err.message || 'Failed to reopen post', 'error');
        button.disabled = false;
        button.innerHTML = '<span class="unresolve-icon">↺</span><span>Reopen</span>';
    }
}


async function handleCrawl() {
    // Check authentication first
    if (!window.authManager || !window.authManager.isAuthenticated()) {
        showNotification('Please sign in to crawl for new posts', 'error');
        setTimeout(() => {
            window.location.href = '/auth.html';
        }, 1500);
        return;
    }
    
    const crawlBtn = document.getElementById('crawlBtn');
    const crawlIcon = crawlBtn.querySelector('.crawl-icon');
    const crawlText = crawlBtn.querySelector('.crawl-text');
    
    // Confirm action
    if (!confirm('Start crawling AWS blog for new/updated posts?\n\nThis will take 5-10 minutes to complete and runs in the background.')) {
        return;
    }
    
    // Disable button and show loading state
    crawlBtn.disabled = true;
    crawlIcon.textContent = '⏳';
    crawlText.textContent = 'Starting...';
    crawlBtn.classList.add('crawling');
    
    try {
        console.log('Triggering crawler...');
        
        // Get token and validate
        const token = window.authManager.getIdToken();
        console.log('Token exists:', !!token);
        
        if (!token) {
            throw new Error('No authentication token available. Please sign out and sign in again.');
        }
        
        const response = await fetch(`${API_ENDPOINT}/crawl`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to start crawler');
        }
        
        const data = await response.json();
        console.log('Crawler response:', data);
        
        // Show success state
        crawlIcon.textContent = '✓';
        crawlText.textContent = 'Crawler Running';
        
        showNotification('Crawler started! This will take 5-10 minutes. The page will auto-refresh when complete.', 'success');
        
        // Start polling for completion
        startCrawlerPolling();
        
    } catch (err) {
        console.error('Error starting crawler:', err);
        showNotification(err.message || 'Failed to start crawler', 'error');
        
        // Reset button
        crawlBtn.disabled = false;
        crawlIcon.textContent = '🔄';
        crawlText.textContent = 'Crawl for New Posts';
        crawlBtn.classList.remove('crawling');
    }
}

function startCrawlerPolling() {
    let pollCount = 0;
    const maxPolls = 60; // Poll for up to 10 minutes (every 10 seconds)
    
    const pollInterval = setInterval(async () => {
        pollCount++;
        
        try {
            // Fetch posts to see if last_crawled has updated
            const response = await fetch(`${API_ENDPOINT}/posts`);
            if (response.ok) {
                const data = await response.json();
                const posts = data.posts || [];
                
                // Check if any post was crawled in the last 2 minutes
                const now = new Date();
                const recentlyCrawled = posts.some(post => {
                    if (post.last_crawled) {
                        const crawledDate = new Date(post.last_crawled);
                        const diffMinutes = (now - crawledDate) / 1000 / 60;
                        return diffMinutes < 2;
                    }
                    return false;
                });
                
                if (recentlyCrawled || pollCount >= maxPolls) {
                    clearInterval(pollInterval);
                    
                    // Reset button
                    const crawlBtn = document.getElementById('crawlBtn');
                    const crawlIcon = crawlBtn.querySelector('.crawl-icon');
                    const crawlText = crawlBtn.querySelector('.crawl-text');
                    
                    crawlBtn.disabled = false;
                    crawlIcon.textContent = '🔄';
                    crawlText.textContent = 'Crawl for New Posts';
                    crawlBtn.classList.remove('crawling');
                    
                    if (recentlyCrawled) {
                        showNotification('Crawler completed! Reloading posts...', 'success');
                        // Reload posts
                        setTimeout(() => loadPosts(), 1000);
                    } else {
                        showNotification('Crawler is still running. Check back in a few minutes.', 'info');
                    }
                }
            }
        } catch (err) {
            console.error('Error polling crawler status:', err);
        }
    }, 10000); // Poll every 10 seconds
}


// Comments Modal Functions
let currentPostId = null;
let currentPostTitle = null;

function openCommentsModal(postId, postTitle) {
    currentPostId = postId;
    currentPostTitle = postTitle;
    
    const modal = document.getElementById('commentsModal');
    const modalPostTitle = document.getElementById('modalPostTitle');
    const commentText = document.getElementById('commentText');
    
    modalPostTitle.textContent = postTitle;
    commentText.value = '';
    document.getElementById('charCount').textContent = '0 / 1000';
    
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
    
    loadComments(postId);
}

function closeCommentsModal() {
    const modal = document.getElementById('commentsModal');
    modal.classList.remove('show');
    document.body.style.overflow = '';
    currentPostId = null;
    currentPostTitle = null;
}

async function loadComments(postId) {
    const container = document.getElementById('commentsContainer');
    container.innerHTML = `
        <div class="loading-comments">
            <div class="spinner"></div>
            <p>Loading comments...</p>
        </div>
    `;
    
    try {
        // Include auth token if available to see pending comments
        const headers = {};
        if (window.authManager && window.authManager.isAuthenticated()) {
            headers['Authorization'] = `Bearer ${window.authManager.getIdToken()}`;
        }
        
        const response = await fetch(`${API_ENDPOINT}/posts/${postId}/comments`, { headers });
        
        if (!response.ok) {
            throw new Error('Failed to load comments');
        }
        
        const data = await response.json();
        const comments = data.comments || [];
        
        if (comments.length === 0) {
            container.innerHTML = `
                <div class="no-comments">
                    <p>No comments yet. Be the first to add feedback!</p>
                </div>
            `;
        } else {
            container.innerHTML = comments.map(comment => createCommentHTML(comment)).join('');
        }
    } catch (err) {
        console.error('Error loading comments:', err);
        container.innerHTML = `
            <div class="error">
                <p>Failed to load comments. Please try again.</p>
            </div>
        `;
    }
}

function createCommentHTML(comment) {
    const timestamp = formatDate(comment.timestamp);
    const text = escapeHtml(comment.text);
    const displayName = comment.display_name || 'User';
    const voterId = comment.voter_id || '';
    const moderationStatus = comment.moderation_status || 'approved';
    
    // Check if this is a pending comment
    const isPending = moderationStatus === 'pending_review';
    const pendingClass = isPending ? 'comment-pending' : '';
    
    // Build the comment HTML
    let commentHTML = `
        <div class="comment-item ${pendingClass}">
            <div class="comment-header">
                <div class="comment-meta">
                    <span class="comment-author clickable-username" data-user-id="${voterId}">
                        👤 ${escapeHtml(displayName)}
                    </span>
                    <span class="comment-timestamp">${timestamp}</span>`;
    
    // Add pending status badge if applicable
    if (isPending) {
        commentHTML += `
                    <span class="comment-status">⏳ Pending Review</span>`;
    }
    
    commentHTML += `
                </div>
            </div>
            <div class="comment-text">${text}</div>`;
    
    // Add pending notice if applicable
    if (isPending) {
        commentHTML += `
            <div class="pending-notice">
                <strong>⚠️ Pending Administrative Review</strong>
                <p>This comment is visible only to you and will be reviewed by an administrator before being published.</p>
            </div>`;
    }
    
    commentHTML += `
        </div>
    `;
    
    return commentHTML;
}

async function handleSubmitComment() {
    // Check authentication first
    if (!window.authManager || !window.authManager.isAuthenticated()) {
        showNotification('Please sign in to comment', 'error');
        setTimeout(() => {
            window.authManager.signIn();
        }, 1500);
        return;
    }
    
    const commentText = document.getElementById('commentText');
    const submitBtn = document.getElementById('submitComment');
    const text = commentText.value.trim();
    
    if (!text) {
        showNotification('Please enter a comment', 'error');
        return;
    }
    
    if (!currentPostId) {
        showNotification('Error: No post selected', 'error');
        return;
    }
    
    submitBtn.disabled = true;
    submitBtn.textContent = 'Posting...';
    
    try {
        const userId = window.authManager.getUser().sub;
        
        const response = await fetch(`${API_ENDPOINT}/posts/${currentPostId}/comments`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.authManager.getIdToken()}`
            },
            body: JSON.stringify({
                text: text,
                voter_id: userId
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to post comment');
        }
        
        const data = await response.json();
        processBadgeResponse(data);
        
        // Check moderation status
        const moderationStatus = data.comment?.moderation_status;
        
        // Update the post in local data
        const postIndex = allPosts.findIndex(p => p.post_id === currentPostId);
        if (postIndex !== -1) {
            allPosts[postIndex] = data.post;
        }
        
        // Clear the text area
        commentText.value = '';
        document.getElementById('charCount').textContent = '0 / 1000';
        
        // Reload comments
        await loadComments(currentPostId);
        
        // Refresh the posts display to update comment count
        handleFilter();
        
        // Show appropriate notification based on moderation status
        if (moderationStatus === 'pending_review') {
            showNotification('Comment submitted for review. It will be visible to you but not to other users until approved by an administrator. ⏳', 'warning');
        } else {
            showNotification('Comment posted successfully! 💬', 'success');
        }
        
    } catch (err) {
        console.error('Error posting comment:', err);
        showNotification(err.message || 'Failed to post comment', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Post Comment';
    }
}


// Chart Rendering Functions
function renderCharts() {
    renderLeaderboardChart();
    renderRecentBlogsChart();
    renderTopLovedChart();
    renderTopVotesChart();
    renderTopCommentsChart();
}

function renderLeaderboardChart() {
    const ctx = document.getElementById('leaderboardChart');
    if (!ctx) return;
    
    // Calculate user activity from all posts
    const userActivity = {};
    
    allPosts.forEach(post => {
        // Count votes
        const voters = post.voters || [];
        voters.forEach(userId => {
            if (!userActivity[userId]) {
                userActivity[userId] = { votes: 0, loves: 0, comments: 0, total: 0 };
            }
            userActivity[userId].votes++;
            userActivity[userId].total++;
        });
        
        // Count loves
        const lovers = post.lovers || [];
        lovers.forEach(userId => {
            if (!userActivity[userId]) {
                userActivity[userId] = { votes: 0, loves: 0, comments: 0, total: 0 };
            }
            userActivity[userId].loves++;
            userActivity[userId].total++;
        });
        
        // Count comments
        const comments = post.comments || [];
        comments.forEach(comment => {
            const userId = comment.voter_id;
            if (userId) {
                if (!userActivity[userId]) {
                    userActivity[userId] = { votes: 0, loves: 0, comments: 0, total: 0 };
                }
                userActivity[userId].comments++;
                userActivity[userId].total++;
            }
        });
    });
    
    // Convert to array and sort by total activity
    const topUsers = Object.entries(userActivity)
        .map(([userId, stats]) => ({
            userId,
            displayName: getDisplayNameForUser(userId),
            ...stats
        }))
        .sort((a, b) => b.total - a.total)
        .slice(0, 6);
    
    // Destroy existing chart
    if (leaderboardChart) {
        leaderboardChart.destroy();
    }
    
    if (topUsers.length === 0) {
        ctx.getContext('2d').font = '14px Arial';
        ctx.getContext('2d').fillStyle = '#999';
        ctx.getContext('2d').textAlign = 'center';
        ctx.getContext('2d').fillText('No activity yet', ctx.width / 2, ctx.height / 2);
        return;
    }
    
    // Add medals to top 3
    const labels = topUsers.map((user, index) => {
        const medal = index === 0 ? '🥇 ' : index === 1 ? '🥈 ' : index === 2 ? '🥉 ' : '';
        return medal + user.displayName;
    });
    
    leaderboardChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Loves',
                    data: topUsers.map(u => u.loves),
                    backgroundColor: 'rgba(233, 30, 99, 0.7)',
                    borderColor: 'rgba(233, 30, 99, 1)',
                    borderWidth: 2
                },
                {
                    label: 'Votes',
                    data: topUsers.map(u => u.votes),
                    backgroundColor: 'rgba(33, 150, 243, 0.7)',
                    borderColor: 'rgba(33, 150, 243, 1)',
                    borderWidth: 2
                },
                {
                    label: 'Comments',
                    data: topUsers.map(u => u.comments),
                    backgroundColor: 'rgba(255, 152, 0, 0.7)',
                    borderColor: 'rgba(255, 152, 0, 1)',
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return topUsers[context[0].dataIndex].displayName;
                        },
                        footer: function(context) {
                            const user = topUsers[context[0].dataIndex];
                            return `Total Activity: ${user.total}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                },
                y: {
                    stacked: true
                }
            },
            onClick: (event, activeElements) => {
                if (activeElements.length > 0) {
                    const index = activeElements[0].index;
                    const user = topUsers[index];
                    // Show profile popup
                    showUserProfilePopup(user.userId, event.native.clientX, event.native.clientY);
                }
            }
        }
    });
    
    // Make canvas cursor pointer on hover
    ctx.style.cursor = 'pointer';
}

// Helper function to get display name from comments or fallback
// Cache for user display names
const userDisplayNameCache = {};

function getDisplayNameForUser(userId) {
    // Check cache first
    if (userDisplayNameCache[userId]) {
        return userDisplayNameCache[userId];
    }
    
    // Try to find display name from comments
    for (const post of allPosts) {
        const comments = post.comments || [];
        for (const comment of comments) {
            if (comment.voter_id === userId && comment.display_name) {
                userDisplayNameCache[userId] = comment.display_name;
                return comment.display_name;
            }
        }
    }
    
    // Fetch from profile API asynchronously (won't block, will update on next render)
    fetchUserDisplayName(userId);
    
    // Fallback to truncated user ID
    return userId.substring(0, 8) + '...';
}

async function fetchUserDisplayName(userId) {
    try {
        const response = await fetch(`${API_ENDPOINT}/profile/${userId}`);
        if (response.ok) {
            const data = await response.json();
            if (data.profile && data.profile.display_name) {
                userDisplayNameCache[userId] = data.profile.display_name;
                // Re-render charts to update with new display name
                renderCharts();
            }
        }
    } catch (error) {
        console.error('Error fetching display name:', error);
    }
}


function renderRecentBlogsChart() {
    const ctx = document.getElementById('recentBlogsChart');
    if (!ctx) return;
    
    // Calculate blogs added in last 30 days, grouped by week
    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    
    // Create 4 weekly buckets
    const weeks = [
        { label: 'Week 1', start: new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000), count: 0 },
        { label: 'Week 2', start: new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000), count: 0 },
        { label: 'Week 3', start: new Date(now.getTime() - 21 * 24 * 60 * 60 * 1000), count: 0 },
        { label: 'Week 4', start: new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000), count: 0 }
    ];
    
    allPosts.forEach(post => {
        const publishedDate = new Date(post.date_published);
        if (publishedDate >= thirtyDaysAgo) {
            // Find which week this belongs to
            for (let i = 0; i < weeks.length; i++) {
                const weekStart = weeks[i].start;
                const weekEnd = i === 0 ? now : weeks[i - 1].start;
                
                if (publishedDate >= weekStart && publishedDate < weekEnd) {
                    weeks[i].count++;
                    break;
                }
            }
        }
    });
    
    // Reverse to show oldest to newest
    weeks.reverse();
    
    // Destroy existing chart if it exists
    if (recentBlogsChart) {
        recentBlogsChart.destroy();
    }
    
    recentBlogsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: weeks.map(w => w.label),
            datasets: [{
                label: 'Blogs Added',
                data: weeks.map(w => w.count),
                backgroundColor: 'rgba(255, 153, 0, 0.7)',
                borderColor: 'rgba(255, 153, 0, 1)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.y} blog${context.parsed.y !== 1 ? 's' : ''} added`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

function renderTopLovedChart() {
    const ctx = document.getElementById('topLovedChart');
    if (!ctx) return;
    
    // Get top 6 posts by love votes
    const postsWithLoves = allPosts
        .map(post => ({
            title: post.title,
            loves: post.love_votes || 0
        }))
        .filter(post => post.loves > 0)
        .sort((a, b) => b.loves - a.loves)
        .slice(0, 6);
    
    // Destroy existing chart if it exists
    if (topLovedChart) {
        topLovedChart.destroy();
    }
    
    if (postsWithLoves.length === 0) {
        // Show empty state
        ctx.getContext('2d').font = '14px Arial';
        ctx.getContext('2d').fillStyle = '#999';
        ctx.getContext('2d').textAlign = 'center';
        ctx.getContext('2d').fillText('No loves yet', ctx.width / 2, ctx.height / 2);
        return;
    }
    
    topLovedChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: postsWithLoves.map(p => truncateTitle(p.title, 30)),
            datasets: [{
                label: 'Loves',
                data: postsWithLoves.map(p => p.loves),
                backgroundColor: 'rgba(233, 30, 99, 0.7)',
                borderColor: 'rgba(233, 30, 99, 1)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return postsWithLoves[context[0].dataIndex].title;
                        },
                        label: function(context) {
                            return `${context.parsed.x} love${context.parsed.x !== 1 ? 's' : ''}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

function renderTopVotesChart() {
    const ctx = document.getElementById('topVotesChart');
    if (!ctx) return;
    
    // Get top 6 posts by total votes
    const postsWithVotes = allPosts
        .map(post => ({
            title: post.title,
            votes: (post.needs_update_votes || 0) + (post.remove_post_votes || 0)
        }))
        .filter(post => post.votes > 0)
        .sort((a, b) => b.votes - a.votes)
        .slice(0, 6);
    
    // Destroy existing chart if it exists
    if (topVotesChart) {
        topVotesChart.destroy();
    }
    
    if (postsWithVotes.length === 0) {
        // Show empty state
        ctx.getContext('2d').font = '14px Arial';
        ctx.getContext('2d').fillStyle = '#999';
        ctx.getContext('2d').textAlign = 'center';
        ctx.getContext('2d').fillText('No votes yet', ctx.width / 2, ctx.height / 2);
        return;
    }
    
    topVotesChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: postsWithVotes.map(p => truncateTitle(p.title, 30)),
            datasets: [{
                label: 'Total Votes',
                data: postsWithVotes.map(p => p.votes),
                backgroundColor: 'rgba(33, 150, 243, 0.7)',
                borderColor: 'rgba(33, 150, 243, 1)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return postsWithVotes[context[0].dataIndex].title;
                        },
                        label: function(context) {
                            return `${context.parsed.x} vote${context.parsed.x !== 1 ? 's' : ''}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

function renderTopCommentsChart() {
    const ctx = document.getElementById('topCommentsChart');
    if (!ctx) return;
    
    // Get top 6 posts by comment count
    const postsWithComments = allPosts
        .map(post => ({
            title: post.title,
            comments: post.comment_count || 0
        }))
        .filter(post => post.comments > 0)
        .sort((a, b) => b.comments - a.comments)
        .slice(0, 6);
    
    // Destroy existing chart if it exists
    if (topCommentsChart) {
        topCommentsChart.destroy();
    }
    
    if (postsWithComments.length === 0) {
        // Show empty state
        ctx.getContext('2d').font = '14px Arial';
        ctx.getContext('2d').fillStyle = '#999';
        ctx.getContext('2d').textAlign = 'center';
        ctx.getContext('2d').fillText('No comments yet', ctx.width / 2, ctx.height / 2);
        return;
    }
    
    topCommentsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: postsWithComments.map(p => truncateTitle(p.title, 30)),
            datasets: [{
                label: 'Comments',
                data: postsWithComments.map(p => p.comments),
                backgroundColor: 'rgba(76, 175, 80, 0.7)',
                borderColor: 'rgba(76, 175, 80, 1)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return postsWithComments[context[0].dataIndex].title;
                        },
                        label: function(context) {
                            return `${context.parsed.x} comment${context.parsed.x !== 1 ? 's' : ''}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

function truncateTitle(title, maxLength) {
    if (title.length <= maxLength) return title;
    return title.substring(0, maxLength - 3) + '...';
}


// ============================================================================
// Article Proposal Feature
// ============================================================================

class ArticleProposal {
    constructor() {
        this.modal = document.getElementById('proposalModal');
        this.form = document.getElementById('proposalForm');
        this.result = document.getElementById('proposalResult');
        this.currentProposal = null;
        
        this.init();
    }
    
    init() {
        // Setup proposals dropdown for authenticated users
        this.setupProposalsDropdown();

        // Open modal button (fallback for unauthenticated users)
        const proposeBtn = document.getElementById('proposeArticleBtn');
        if (proposeBtn) {
            proposeBtn.addEventListener('click', () => this.openModal());
        }
        
        // Close modal
        const closeBtn = document.getElementById('closeProposalModal');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeModal());
        }
        
        // Close on outside click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.closeModal();
            }
        });
        
        // Character counter
        const input = document.getElementById('proposalInput');
        const charCount = document.getElementById('proposalCharCount');
        if (input && charCount) {
            input.addEventListener('input', () => {
                charCount.textContent = `${input.value.length} / 1000`;
            });
        }
        
        // Submit proposal
        const submitBtn = document.getElementById('submitProposal');
        if (submitBtn) {
            submitBtn.addEventListener('click', () => this.submitProposal());
        }
        
        // New proposal button
        const newBtn = document.getElementById('newProposal');
        if (newBtn) {
            newBtn.addEventListener('click', () => this.resetForm());
        }
        
        // Copy proposal button
        const copyBtn = document.getElementById('copyProposal');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => this.copyProposal());
        }
    }

    setupProposalsDropdown() {
        const proposeBtn = document.getElementById('proposeArticleBtn');
        if (!proposeBtn) return;

        // Create the dropdown container (hidden initially)
        const dropdown = document.createElement('div');
        dropdown.className = 'proposals-dropdown';
        dropdown.id = 'proposalsDropdown';
        dropdown.style.display = 'none';
        dropdown.innerHTML = `
            <button class="proposals-dropdown-btn" id="proposalsDropdownBtn">
                <span class="propose-icon">✍️</span>
                <span class="propose-text">Proposals ▾</span>
            </button>
            <div class="proposals-dropdown-menu" id="proposalsDropdownMenu">
                <button class="dropdown-item" id="proposeArticleMenuItem">✏️ Propose Article</button>
                <button class="dropdown-item" id="proposeFeatureMenuItem">🚀 Propose Feature</button>
                <button class="dropdown-item" id="reviewMenuItem">📋 Review</button>
            </div>
        `;

        // Insert dropdown next to the original button
        proposeBtn.parentNode.insertBefore(dropdown, proposeBtn.nextSibling);

        // Toggle dropdown menu on click
        const dropdownBtn = dropdown.querySelector('#proposalsDropdownBtn');
        const dropdownMenu = dropdown.querySelector('#proposalsDropdownMenu');

        dropdownBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdownMenu.classList.toggle('show');
        });

        // "Propose Article" opens the existing article proposal modal
        dropdown.querySelector('#proposeArticleMenuItem').addEventListener('click', (e) => {
            e.stopPropagation();
            dropdownMenu.classList.remove('show');
            this.openModal();
        });

        // "Propose Feature" opens the feature proposal modal
        dropdown.querySelector('#proposeFeatureMenuItem').addEventListener('click', (e) => {
            e.stopPropagation();
            dropdownMenu.classList.remove('show');
            if (window.featureProposal) {
                window.featureProposal.openModal();
            }
        });

        // "Review" opens the proposals review modal
        dropdown.querySelector('#reviewMenuItem').addEventListener('click', (e) => {
            e.stopPropagation();
            dropdownMenu.classList.remove('show');
            if (typeof window.openProposalsReview === 'function') {
                window.openProposalsReview();
            } else {
                showNotification('Proposals review coming soon!', 'info');
            }
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!dropdown.contains(e.target)) {
                dropdownMenu.classList.remove('show');
            }
        });

        // Store reference for auth state updates
        this.dropdown = dropdown;
        this.originalBtn = proposeBtn;

        // Set initial state based on current auth
        this.updateProposalsButton();
    }

    updateProposalsButton() {
        const isAuthenticated = window.authManager && window.authManager.isAuthenticated();
        if (this.dropdown && this.originalBtn) {
            if (isAuthenticated) {
                this.originalBtn.style.display = 'none';
                this.dropdown.style.display = 'block';
            } else {
                this.originalBtn.style.display = 'flex';
                this.dropdown.style.display = 'none';
            }
        }
    }
    
    openModal() {
        this.modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
    
    closeModal() {
        this.modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
    
    async submitProposal() {
            // Check authentication first
            if (!window.authManager || !window.authManager.isAuthenticated()) {
                showNotification('Please sign in to propose an article', 'error');
                setTimeout(() => {
                    window.authManager.signIn();
                }, 1500);
                return;
            }

            const input = document.getElementById('proposalInput').value.trim();
            const category = document.getElementById('proposalCategory').value;

            if (!input) {
                showNotification('Please describe what you want to write about', 'error');
                return;
            }

            if (input.length < 20) {
                showNotification('Please provide more details (at least 20 characters)', 'error');
                return;
            }

            // Show loading state
            const submitBtn = document.getElementById('submitProposal');
            const btnText = submitBtn.querySelector('.btn-text');
            const btnLoading = submitBtn.querySelector('.btn-loading');

            submitBtn.disabled = true;
            btnText.style.display = 'none';
            btnLoading.style.display = 'flex';

            try {
                const token = window.authManager.getIdToken();

                const response = await fetch(`${API_ENDPOINT}/propose-article`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        user_input: input,
                        category: category || undefined
                    })
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.message || `HTTP ${response.status}`);
                }

                const data = await response.json();
                this.currentProposal = data.proposal;
                processBadgeResponse(data);

                // Show success notification and offer to view proposals
                showNotification('Your proposal has been submitted successfully!', 'success');

                // Display the saved proposal
                this.displayProposal(data.proposal);

                // Add a "View Proposals" link in the result area
                this.addViewProposalsLink();

            } catch (error) {
                console.error('Error submitting proposal:', error);
                showNotification(`Error submitting proposal: ${error.message}`, 'error');
            } finally {
                // Restore button state
                submitBtn.disabled = false;
                btnText.style.display = 'inline';
                btnLoading.style.display = 'none';
            }
        }

    
    displayProposal(proposal) {
        // Hide form, show result
        this.form.style.display = 'none';
        this.result.style.display = 'block';
        
        // Support both flat and nested ai_generated_content formats
        const ai = proposal.ai_generated_content || {};
        const summary = proposal.summary || ai.summary || '';
        const targetAudience = proposal.target_audience || ai.target_audience || '';
        const estimatedLength = proposal.estimated_length || ai.estimated_length || '';
        const writingTips = proposal.writing_tips || ai.writing_tips || '';
        const outline = proposal.outline || ai.outline || [];
        const keyTopics = proposal.key_topics || ai.key_topics || [];
        
        // Populate result fields
        document.getElementById('resultTitle').textContent = proposal.title || '';
        document.getElementById('resultCategory').textContent = proposal.category || '';
        document.getElementById('resultSummary').textContent = summary;
        document.getElementById('resultAudience').textContent = targetAudience;
        document.getElementById('resultLength').textContent = estimatedLength;
        document.getElementById('resultTips').textContent = writingTips;
        
        // Populate outline
        const outlineList = document.getElementById('resultOutline');
        outlineList.innerHTML = '';
        outline.forEach(item => {
            const li = document.createElement('li');
            li.textContent = item;
            outlineList.appendChild(li);
        });
        
        // Populate topics
        const topicsDiv = document.getElementById('resultTopics');
        topicsDiv.innerHTML = '';
        keyTopics.forEach(topic => {
            const tag = document.createElement('span');
            tag.className = 'topic-tag';
            tag.textContent = topic;
            topicsDiv.appendChild(tag);
        });
        
        // Scroll to top of modal
        this.modal.querySelector('.modal-content').scrollTop = 0;
    }
    
    addViewProposalsLink() {
        const actionsDiv = this.result.querySelector('.proposal-actions');
        if (!actionsDiv) return;
        
        // Avoid adding duplicate link
        if (actionsDiv.querySelector('.view-proposals-link')) return;
        
        const viewBtn = document.createElement('button');
        viewBtn.className = 'btn-secondary view-proposals-link';
        viewBtn.textContent = '📋 View All Proposals';
        viewBtn.addEventListener('click', () => {
            this.closeModal();
            // Trigger the proposals review if available
            if (window.proposalsReview) {
                window.proposalsReview.openModal();
            } else {
                showNotification('Proposals review coming soon!', 'success');
            }
        });
        actionsDiv.insertBefore(viewBtn, actionsDiv.firstChild);
    }
    
    resetForm() {
        // Show form, hide result
        this.form.style.display = 'flex';
        this.result.style.display = 'none';
        
        // Clear form
        document.getElementById('proposalInput').value = '';
        document.getElementById('proposalCategory').value = '';
        document.getElementById('proposalCharCount').textContent = '0 / 1000';
        
        this.currentProposal = null;
    }
    
    copyProposal() {
        if (!this.currentProposal) return;
        
        const p = this.currentProposal;
        const ai = p.ai_generated_content || {};
        const summary = p.summary || ai.summary || '';
        const outline = p.outline || ai.outline || [];
        const keyTopics = p.key_topics || ai.key_topics || [];
        const targetAudience = p.target_audience || ai.target_audience || '';
        const estimatedLength = p.estimated_length || ai.estimated_length || '';
        const writingTips = p.writing_tips || ai.writing_tips || '';
        
        const text = `
ARTICLE PROPOSAL
================

Title: ${p.title}
Category: ${p.category}

Summary:
${summary}

Outline:
${outline.map((item, i) => `${i + 1}. ${item}`).join('\n')}

Key Topics:
${keyTopics.join(', ')}

Target Audience:
${targetAudience}

Estimated Length:
${estimatedLength}

Writing Tips:
${writingTips}

Description:
${p.description || p.original_input || ''}
        `.trim();
        
        navigator.clipboard.writeText(text).then(() => {
            const copyBtn = document.getElementById('copyProposal');
            const originalText = copyBtn.textContent;
            copyBtn.textContent = '✓ Copied!';
            copyBtn.style.background = '#48bb78';
            
            setTimeout(() => {
                copyBtn.textContent = originalText;
                copyBtn.style.background = '';
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy:', err);
            alert('Failed to copy to clipboard');
        });
    }
}

// Initialize article proposal feature
document.addEventListener('DOMContentLoaded', () => {
    window.articleProposal = new ArticleProposal();
});

// ============================================================================
// Feature Proposal Modal
// ============================================================================

const EUC_SERVICES = [
    'Amazon WorkSpaces Personal', 'Amazon WorkSpaces Pools', 'Amazon WorkSpaces Core',
    'Amazon WorkSpaces Applications (formerly AppStream 2.0)', 'Amazon WorkSpaces Secure Browser',
    'Amazon WorkSpaces Thin Client', 'Amazon DCV', 'Other/General EUC'
];
const PRIORITY_LEVELS = ['Nice to Have', 'Important', 'Critical'];

class FeatureProposal {
    constructor() {
        this.modal = null;
        this.currentProposal = null;
        this.createModal();
    }

    createModal() {
        this.modal = document.createElement('div');
        this.modal.className = 'modal feature-proposal-modal';
        this.modal.style.display = 'none';

        const serviceOptions = EUC_SERVICES.map(s => `<option value="${s}">${s}</option>`).join('');
        const priorityOptions = PRIORITY_LEVELS.map(p => `<option value="${p}">${p}</option>`).join('');

        this.modal.innerHTML = `
            <div class="modal-content feature-proposal-content">
                <div class="modal-header">
                    <h2>🚀 Propose a Feature</h2>
                    <button class="close-modal modal-close" id="closeFeatureProposal">&times;</button>
                </div>
                <div class="feature-proposal-form" id="featureProposalForm">
                    <div class="form-group">
                        <label for="featureService">EUC Service *</label>
                        <select id="featureService" required>
                            <option value="">Select a service...</option>
                            ${serviceOptions}
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="featureTitle">Feature Title * <span class="field-hint">(min 10 characters)</span></label>
                        <input type="text" id="featureTitle" placeholder="e.g. Auto-scaling for WorkSpaces pools" minlength="10" required />
                    </div>
                    <div class="form-group">
                        <label for="featureDescription">Description * <span class="field-hint">(min 30, max 2000 characters)</span></label>
                        <textarea id="featureDescription" placeholder="Describe the feature you'd like to see..." rows="5" minlength="30" maxlength="2000" required></textarea>
                        <div class="char-counter" id="featureDescCharCount">0 / 2000</div>
                    </div>
                    <div class="form-group">
                        <label for="featurePriority">Priority *</label>
                        <select id="featurePriority" required>
                            ${priorityOptions}
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="featureUseCase">Use Case <span class="field-hint">(optional, max 1000 characters)</span></label>
                        <textarea id="featureUseCase" placeholder="Describe your use case or scenario..." rows="3" maxlength="1000"></textarea>
                    </div>
                    <button class="btn-primary submit-feature-btn" id="submitFeatureProposal">
                        <span class="btn-text">🚀 Submit Feature Proposal</span>
                        <span class="btn-loading" style="display:none;">
                            <span class="spinner"></span> Submitting...
                        </span>
                    </button>
                </div>
                <div class="feature-proposal-result" id="featureProposalResult" style="display:none;">
                    <div class="result-section">
                        <h3 id="featureResultTitle"></h3>
                        <div class="result-tags">
                            <span class="service-tag" id="featureResultService"></span>
                            <span class="priority-tag" id="featureResultPriority"></span>
                        </div>
                    </div>
                    <div class="result-section" id="featureResultRefinedSection">
                        <h4>✨ AI-Refined Description</h4>
                        <p id="featureResultRefined"></p>
                    </div>
                    <div class="result-section" id="featureResultRelatedSection">
                        <h4>🔗 Related Features & Workarounds</h4>
                        <p id="featureResultRelated"></p>
                    </div>
                    <div class="result-section" id="featureResultCategorySection">
                        <h4>📂 Request Category</h4>
                        <p id="featureResultCategory"></p>
                    </div>
                    <div class="proposal-actions">
                        <button class="btn-secondary" id="copyFeatureProposal">📋 Copy</button>
                        <button class="btn-secondary" id="newFeatureProposal">✨ New Proposal</button>
                        <button class="btn-secondary" id="viewAllFromFeature">📋 View All Proposals</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(this.modal);

        // Close button
        this.modal.querySelector('#closeFeatureProposal').addEventListener('click', () => this.closeModal());

        // Close on outside click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) this.closeModal();
        });

        // Character counter for description
        const descInput = this.modal.querySelector('#featureDescription');
        const descCount = this.modal.querySelector('#featureDescCharCount');
        descInput.addEventListener('input', () => {
            descCount.textContent = `${descInput.value.length} / 2000`;
        });

        // Submit
        this.modal.querySelector('#submitFeatureProposal').addEventListener('click', () => this.submitProposal());

        // Result actions
        this.modal.querySelector('#copyFeatureProposal').addEventListener('click', () => this.copyProposal());
        this.modal.querySelector('#newFeatureProposal').addEventListener('click', () => this.resetForm());
        this.modal.querySelector('#viewAllFromFeature').addEventListener('click', () => {
            this.closeModal();
            if (window.proposalsReview) {
                window.proposalsReview.openModal();
            }
        });
    }

    openModal() {
        this.modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    closeModal() {
        this.modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }

    async submitProposal() {
        if (!window.authManager || !window.authManager.isAuthenticated()) {
            showNotification('Please sign in to propose a feature', 'error');
            setTimeout(() => { window.authManager.signIn(); }, 1500);
            return;
        }

        const service = this.modal.querySelector('#featureService').value;
        const title = this.modal.querySelector('#featureTitle').value.trim();
        const description = this.modal.querySelector('#featureDescription').value.trim();
        const priority = this.modal.querySelector('#featurePriority').value;
        const useCase = this.modal.querySelector('#featureUseCase').value.trim();

        if (!service) {
            showNotification('Please select a service', 'error');
            return;
        }
        if (!title || title.length < 10) {
            showNotification('Title must be at least 10 characters', 'error');
            return;
        }
        if (!description || description.length < 30) {
            showNotification('Description must be at least 30 characters', 'error');
            return;
        }

        const submitBtn = this.modal.querySelector('#submitFeatureProposal');
        const btnText = submitBtn.querySelector('.btn-text');
        const btnLoading = submitBtn.querySelector('.btn-loading');
        submitBtn.disabled = true;
        btnText.style.display = 'none';
        btnLoading.style.display = 'flex';

        try {
            const token = window.authManager.getIdToken();
            const response = await fetch(`${API_ENDPOINT}/propose-feature`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ service, title, description, priority, use_case: useCase || undefined })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();
            this.currentProposal = data.proposal;
            processBadgeResponse(data);
            showNotification('Feature proposal submitted successfully!', 'success');
            this.displayResult(data.proposal);
        } catch (error) {
            console.error('Error submitting feature proposal:', error);
            showNotification(`Error: ${error.message}`, 'error');
        } finally {
            submitBtn.disabled = false;
            btnText.style.display = 'inline';
            btnLoading.style.display = 'none';
        }
    }

    displayResult(proposal) {
        this.modal.querySelector('#featureProposalForm').style.display = 'none';
        this.modal.querySelector('#featureProposalResult').style.display = 'block';

        this.modal.querySelector('#featureResultTitle').textContent = proposal.title || '';
        this.modal.querySelector('#featureResultService').textContent = proposal.service || '';
        const priorityEl = this.modal.querySelector('#featureResultPriority');
        priorityEl.textContent = proposal.priority || '';
        priorityEl.className = 'priority-tag priority-' + (proposal.priority || '').toLowerCase().replace(/\s+/g, '-');

        const ai = proposal.ai_generated_content || {};

        const refinedSection = this.modal.querySelector('#featureResultRefinedSection');
        if (ai.refined_description) {
            refinedSection.style.display = 'block';
            this.modal.querySelector('#featureResultRefined').textContent = ai.refined_description;
        } else {
            refinedSection.style.display = 'none';
        }

        const relatedSection = this.modal.querySelector('#featureResultRelatedSection');
        if (ai.related_features) {
            relatedSection.style.display = 'block';
            this.modal.querySelector('#featureResultRelated').textContent = ai.related_features;
        } else {
            relatedSection.style.display = 'none';
        }

        const categorySection = this.modal.querySelector('#featureResultCategorySection');
        if (ai.request_category) {
            categorySection.style.display = 'block';
            this.modal.querySelector('#featureResultCategory').textContent = ai.request_category;
        } else {
            categorySection.style.display = 'none';
        }

        this.modal.querySelector('.modal-content').scrollTop = 0;
    }

    resetForm() {
        this.modal.querySelector('#featureProposalForm').style.display = 'flex';
        this.modal.querySelector('#featureProposalResult').style.display = 'none';
        this.modal.querySelector('#featureService').value = '';
        this.modal.querySelector('#featureTitle').value = '';
        this.modal.querySelector('#featureDescription').value = '';
        this.modal.querySelector('#featurePriority').value = PRIORITY_LEVELS[0];
        this.modal.querySelector('#featureUseCase').value = '';
        this.modal.querySelector('#featureDescCharCount').textContent = '0 / 2000';
        this.currentProposal = null;
    }

    copyProposal() {
        if (!this.currentProposal) return;
        const p = this.currentProposal;
        const ai = p.ai_generated_content || {};

        const text = `
FEATURE PROPOSAL
================

Service: ${p.service}
Title: ${p.title}
Priority: ${p.priority}

Description:
${p.description}
${p.use_case ? `\nUse Case:\n${p.use_case}` : ''}
${ai.refined_description ? `\nAI-Refined Description:\n${ai.refined_description}` : ''}
${ai.related_features ? `\nRelated Features:\n${ai.related_features}` : ''}
${ai.request_category ? `\nCategory: ${ai.request_category}` : ''}
        `.trim();

        navigator.clipboard.writeText(text).then(() => {
            const copyBtn = this.modal.querySelector('#copyFeatureProposal');
            const originalText = copyBtn.textContent;
            copyBtn.textContent = '✓ Copied!';
            copyBtn.style.background = '#48bb78';
            setTimeout(() => {
                copyBtn.textContent = originalText;
                copyBtn.style.background = '';
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy:', err);
            showNotification('Failed to copy to clipboard', 'error');
        });
    }
}

// Initialize feature proposal
document.addEventListener('DOMContentLoaded', () => {
    window.featureProposal = new FeatureProposal();
});

// ============================================================================
// Proposals Review Modal
// ============================================================================

class ProposalsReview {
    constructor() {
        this.modal = null;
        this.proposals = [];
        this.currentFilter = 'all';
        this.currentTypeFilter = 'all';
        this.expandedProposalId = null;
        this.currentUserId = null;
        this.createModal();
    }

    createModal() {
        this.modal = document.createElement('div');
        this.modal.className = 'modal proposals-review-modal';
        this.modal.style.display = 'none';
        this.modal.innerHTML = `
            <div class="modal-content proposals-review-content">
                <div class="modal-header">
                    <h2>Community Proposals</h2>
                    <button class="close-modal modal-close" id="closeProposalsReview">&times;</button>
                </div>
                <div class="proposals-filter-tabs">
                    <button class="filter-tab active" data-status="all">All</button>
                    <button class="filter-tab" data-status="pending">Pending</button>
                    <button class="filter-tab" data-status="approved">Approved</button>
                    <button class="filter-tab" data-status="rejected">Rejected</button>
                </div>
                <div class="proposals-type-filter">
                    <button class="type-filter-btn active" data-type="all">All</button>
                    <button class="type-filter-btn" data-type="article">📝 Articles</button>
                    <button class="type-filter-btn" data-type="feature">🚀 Features</button>
                </div>
                <div class="proposals-disclaimer">
                    <p>📋 Proposals are community-driven. Vote 👍 to support or 👎 to oppose. A proposal is <strong>approved</strong> at 5 upvotes and <strong>rejected</strong> at 3 downvotes. Leave 💬 feedback to help refine ideas.</p>
                </div>
                <div class="proposals-list" id="reviewProposalsList">
                    <div class="proposals-loading">Loading proposals...</div>
                </div>
            </div>
        `;
        document.body.appendChild(this.modal);

        // Close button
        this.modal.querySelector('#closeProposalsReview').addEventListener('click', () => this.closeModal());

        // Close on outside click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.closeModal();
            }
        });

        // Filter tabs
        this.modal.querySelectorAll('.filter-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                this.modal.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this.currentFilter = tab.dataset.status;
                this.fetchProposals();
            });
        });

        // Type filter buttons
        this.modal.querySelectorAll('.type-filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.modal.querySelectorAll('.type-filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentTypeFilter = btn.dataset.type;
                this.fetchProposals();
            });
        });
    }

    openModal() {
        this.currentUserId = window.authManager && window.authManager.isAuthenticated()
            ? window.authManager.getUser()?.sub
            : null;
        this.modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        this.fetchProposals();
    }

    closeModal() {
        this.modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        this.expandedProposalId = null;
    }

    async fetchProposals() {
        const listEl = this.modal.querySelector('#reviewProposalsList');
        listEl.innerHTML = '<div class="proposals-loading">Loading proposals...</div>';

        try {
            let url = `${API_ENDPOINT}/proposals`;
            const params = [];
            if (this.currentFilter !== 'all') {
                params.push(`status=${this.currentFilter}`);
            }
            if (this.currentTypeFilter !== 'all') {
                params.push(`proposal_type=${this.currentTypeFilter}`);
            }
            if (params.length > 0) {
                url += '?' + params.join('&');
            }

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            this.proposals = data.proposals || [];
            this.renderProposals();
        } catch (error) {
            console.error('Error fetching proposals:', error);
            listEl.innerHTML = '<div class="proposals-empty">Unable to load proposals. Please try again.</div>';
        }
    }

    renderProposals() {
        const listEl = this.modal.querySelector('#reviewProposalsList');

        if (this.proposals.length === 0) {
            listEl.innerHTML = '<div class="proposals-empty">No proposals found.</div>';
            return;
        }

        listEl.innerHTML = this.proposals.map(p => this.createProposalCard(p)).join('');

        // Attach click handlers for expanding cards
        listEl.querySelectorAll('.proposal-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (e.target.closest('.proposal-upvote-btn') || e.target.closest('.proposal-downvote-btn') || e.target.closest('.proposal-comment-form') || e.target.closest('.proposal-delete-btn') || e.target.closest('.proposal-delete-btn-inline') || e.target.closest('.proposal-feedback-btn')) return;
                const proposalId = card.dataset.proposalId;
                this.toggleExpand(proposalId);
            });
        });

        // Feedback button expands the card
        listEl.querySelectorAll('.proposal-feedback-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const proposalId = btn.dataset.proposalId;
                this.expandedProposalId = proposalId;
                this.renderProposals();
            });
        });

        // Attach vote button handlers (up and down)
        listEl.querySelectorAll('.proposal-upvote-btn, .proposal-downvote-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const proposalId = btn.dataset.proposalId;
                const voteType = btn.dataset.voteType;
                this.handleVote(proposalId, btn, voteType);
            });
        });

        // Attach comment submit handlers
        listEl.querySelectorAll('.proposal-comment-submit').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const proposalId = btn.dataset.proposalId;
                this.handleComment(proposalId);
            });
        });

        // Attach delete handlers (both inline and expanded)
        listEl.querySelectorAll('.proposal-delete-btn, .proposal-delete-btn-inline').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const proposalId = btn.dataset.proposalId;
                this.handleDelete(proposalId);
            });
        });
    }

    createProposalCard(proposal) {
        const isExpanded = this.expandedProposalId === proposal.proposal_id;
        const description = proposal.description || '';
        const snippet = description.length > 150 ? description.substring(0, 150) + '...' : description;
        const statusClass = `status-${(proposal.status || 'pending').toLowerCase()}`;
        const hasVoted = this.currentUserId && (proposal.voters || []).includes(this.currentUserId);
        const upvotes = proposal.upvotes || proposal.votes || 0;
        const downvotes = proposal.downvotes || 0;
        const displayName = proposal.display_name || 'Anonymous';
        const dateStr = formatDate(proposal.created_at);
        const category = proposal.category || 'General';
        const isFeature = proposal.proposal_type === 'feature';

        const ai = proposal.ai_generated_content || {};

        let expandedHtml = '';
        const isOwner = this.currentUserId && proposal.user_id === this.currentUserId;
        const comments = proposal.comments || [];
        const commentCount = comments.length;

        if (isExpanded) {
            const commentsHtml = comments.map(c => `
                <div class="proposal-comment">
                    <div class="proposal-comment-header">
                        <span class="proposal-comment-author">${escapeHtml(c.display_name || 'User')}</span>
                        <span class="proposal-comment-date">${formatDate(c.created_at)}</span>
                    </div>
                    <p class="proposal-comment-text">${escapeHtml(c.text)}</p>
                </div>
            `).join('');

            let detailsHtml = '';
            if (isFeature) {
                detailsHtml = `
                    <div class="proposal-full-description">
                        <h4>Full Description</h4>
                        <p>${escapeHtml(description)}</p>
                    </div>
                    ${proposal.use_case ? `<div class="proposal-detail-section"><h4>Use Case</h4><p>${escapeHtml(proposal.use_case)}</p></div>` : ''}
                    ${ai.refined_description ? `<div class="proposal-detail-section"><h4>✨ AI-Refined Description</h4><p>${escapeHtml(ai.refined_description)}</p></div>` : ''}
                    ${ai.related_features ? `<div class="proposal-detail-section"><h4>🔗 Related Features & Workarounds</h4><p>${escapeHtml(ai.related_features)}</p></div>` : ''}
                    ${ai.request_category ? `<div class="proposal-detail-section"><h4>📂 Request Category</h4><p>${escapeHtml(ai.request_category)}</p></div>` : ''}
                    ${proposal.architecture_diagram_url ? `<div class="proposal-detail-section"><h4>🏗️ Architecture Diagram</h4><img src="${escapeHtml(proposal.architecture_diagram_url)}" alt="Architecture Diagram" style="max-width:100%;border-radius:8px;border:1px solid #e5e7eb;"><br><a href="${escapeHtml(proposal.architecture_diagram_url)}" download="architecture-diagram.png" style="display:inline-block;margin-top:8px;padding:6px 12px;background:#10b981;color:white;border-radius:6px;text-decoration:none;font-size:0.85em;">⬇️ Download Diagram (PNG)</a></div>` : ''}
                    ${(proposal.code_snippets && proposal.code_snippets.length > 0) ? `<div class="proposal-detail-section"><h4>💻 Code Snippets</h4>${proposal.code_snippets.map(s => `<div style="margin-bottom:8px;"><div style="font-size:0.8em;color:#666;margin-bottom:4px;">${escapeHtml(s.language || 'code')}</div><pre style="background:#1e293b;color:#e2e8f0;padding:12px;border-radius:8px;overflow-x:auto;font-size:0.85em;"><code>${escapeHtml(s.code || '')}</code></pre></div>`).join('')}</div>` : ''}
                    ${proposal.source_innovation_id ? `<div class="proposal-detail-section" style="background:#f0f7ff;border:1px solid #93c5fd;border-radius:8px;padding:12px;"><span style="color:#1e40af;">💡 Promoted from Innovation Hub</span></div>` : ''}
                `;
            } else {
                const outline = ai.outline || [];
                const keyTopics = ai.key_topics || [];
                detailsHtml = `
                    <div class="proposal-full-description">
                        <h4>Full Description</h4>
                        <p>${escapeHtml(description)}</p>
                    </div>
                    ${ai.summary ? `<div class="proposal-detail-section"><h4>Summary</h4><p>${escapeHtml(ai.summary)}</p></div>` : ''}
                    ${outline.length > 0 ? `<div class="proposal-detail-section"><h4>Outline</h4><ol>${outline.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ol></div>` : ''}
                    ${keyTopics.length > 0 ? `<div class="proposal-detail-section"><h4>Key Topics</h4><div class="proposal-topics">${keyTopics.map(t => `<span class="topic-tag">${escapeHtml(t)}</span>`).join('')}</div></div>` : ''}
                    ${ai.target_audience ? `<div class="proposal-detail-section"><h4>Target Audience</h4><p>${escapeHtml(ai.target_audience)}</p></div>` : ''}
                    ${ai.estimated_length ? `<div class="proposal-detail-section"><h4>Estimated Length</h4><p>${escapeHtml(ai.estimated_length)}</p></div>` : ''}
                    ${ai.writing_tips ? `<div class="proposal-detail-section"><h4>Writing Tips</h4><p>${escapeHtml(ai.writing_tips)}</p></div>` : ''}
                    ${proposal.architecture_diagram_url ? `<div class="proposal-detail-section"><h4>🏗️ Architecture Diagram</h4><img src="${escapeHtml(proposal.architecture_diagram_url)}" alt="Architecture Diagram" style="max-width:100%;border-radius:8px;border:1px solid #e5e7eb;"><br><a href="${escapeHtml(proposal.architecture_diagram_url)}" download="architecture-diagram.png" style="display:inline-block;margin-top:8px;padding:6px 12px;background:#10b981;color:white;border-radius:6px;text-decoration:none;font-size:0.85em;">⬇️ Download Diagram (PNG)</a></div>` : ''}
                    ${(proposal.code_snippets && proposal.code_snippets.length > 0) ? `<div class="proposal-detail-section"><h4>💻 Code Snippets</h4>${proposal.code_snippets.map(s => `<div style="margin-bottom:8px;"><div style="font-size:0.8em;color:#666;margin-bottom:4px;">${escapeHtml(s.language || 'code')}</div><pre style="background:#1e293b;color:#e2e8f0;padding:12px;border-radius:8px;overflow-x:auto;font-size:0.85em;"><code>${escapeHtml(s.code || '')}</code></pre></div>`).join('')}</div>` : ''}
                    ${proposal.source_innovation_id ? `<div class="proposal-detail-section" style="background:#f0f7ff;border:1px solid #93c5fd;border-radius:8px;padding:12px;"><span style="color:#1e40af;">💡 Promoted from Innovation Hub</span></div>` : ''}
                `;
            }

            expandedHtml = `
                <div class="proposal-expanded-details">
                    ${detailsHtml}
                    <div class="proposal-comments-section">
                        <h4>💬 Feedback (${commentCount})</h4>
                        <div class="proposal-comments-list">${commentsHtml || '<p class="no-comments-yet">No feedback yet. Be the first!</p>'}</div>
                        <div class="proposal-comment-form">
                            <textarea class="proposal-comment-input" data-proposal-id="${proposal.proposal_id}" placeholder="Share your feedback on this proposal..." rows="2" maxlength="500"></textarea>
                            <button class="proposal-comment-submit btn-primary" data-proposal-id="${proposal.proposal_id}">Post Feedback</button>
                        </div>
                    </div>
                    ${isOwner ? `<div class="proposal-actions-bar"><button class="proposal-delete-btn" data-proposal-id="${proposal.proposal_id}">🗑️ Delete Proposal</button></div>` : ''}
                </div>
            `;
        }

        // Feature-specific badges and tags
        const featureBadgeHtml = isFeature ? '<span class="feature-request-badge">🚀 Feature Request</span>' : '';
        const serviceTagHtml = isFeature && proposal.service ? `<span class="service-tag">${escapeHtml(proposal.service)}</span>` : '';
        const priorityClass = isFeature && proposal.priority ? 'priority-' + proposal.priority.toLowerCase().replace(/\s+/g, '-') : '';
        const priorityTagHtml = isFeature && proposal.priority ? `<span class="priority-tag ${priorityClass}">${escapeHtml(proposal.priority)}</span>` : '';
        const categoryHtml = !isFeature ? `<span class="proposal-card-category">${escapeHtml(category)}</span>` : '';

        return `
            <div class="proposal-card ${isExpanded ? 'proposal-card-expanded' : ''}" data-proposal-id="${proposal.proposal_id}">
                <div class="proposal-card-header">
                    <div class="proposal-card-title-row">
                        <h3 class="proposal-card-title">${escapeHtml(proposal.title || 'Untitled')}</h3>
                        <span class="status-badge ${statusClass}">${escapeHtml(proposal.status || 'pending')}</span>
                    </div>
                    ${featureBadgeHtml}
                    ${serviceTagHtml}
                    ${priorityTagHtml}
                    ${categoryHtml}
                </div>
                <p class="proposal-card-snippet">${escapeHtml(snippet)}</p>
                <div class="proposal-card-footer">
                    <div class="proposal-card-meta">
                        <span class="proposal-card-author">${escapeHtml(displayName)}</span>
                        <span class="proposal-card-date">${dateStr}</span>
                    </div>
                    <div class="proposal-card-actions">
                        ${isOwner ? `<button class="proposal-delete-btn-inline" data-proposal-id="${proposal.proposal_id}" title="Delete your proposal">🗑️</button>` : ''}
                        <button class="proposal-feedback-btn" data-proposal-id="${proposal.proposal_id}" title="View & leave feedback">
                            💬 <span>${commentCount}</span>
                        </button>
                        <button class="proposal-upvote-btn ${hasVoted ? 'already-voted' : ''}" 
                                data-proposal-id="${proposal.proposal_id}" data-vote-type="up"
                                ${hasVoted ? 'disabled' : ''} title="Upvote - approve this proposal">
                            👍 <span class="proposal-vote-count">${upvotes}</span>
                        </button>
                        <button class="proposal-downvote-btn ${hasVoted ? 'already-voted' : ''}" 
                                data-proposal-id="${proposal.proposal_id}" data-vote-type="down"
                                ${hasVoted ? 'disabled' : ''} title="Downvote - reject this proposal">
                            👎 <span class="proposal-vote-count">${downvotes}</span>
                        </button>
                    </div>
                </div>
                <div class="proposal-expand-hint">${isExpanded ? '▲ Click to collapse' : '▼ Click to expand details & feedback'}</div>
                ${expandedHtml}
            </div>
        `;
    }

    toggleExpand(proposalId) {
        this.expandedProposalId = this.expandedProposalId === proposalId ? null : proposalId;
        this.renderProposals();
    }

    async handleVote(proposalId, btn, voteType) {
        if (!window.authManager || !window.authManager.isAuthenticated()) {
            showNotification('Please sign in to vote on proposals', 'info');
            return;
        }

        if (btn.disabled) return;

        try {
            const token = window.authManager.getIdToken();
            const response = await fetch(`${API_ENDPOINT}/proposals/${proposalId}/vote`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ vote_type: voteType })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `HTTP ${response.status}`);
            }

            const data = await response.json();
            const updatedProposal = data.proposal;

            // Update the proposal in our local list
            const idx = this.proposals.findIndex(p => p.proposal_id === proposalId);
            if (idx !== -1) {
                this.proposals[idx] = updatedProposal;
            }

            // Re-render to reflect new vote counts and status
            this.renderProposals();

            const statusMsg = updatedProposal.status !== 'pending' ? ` Proposal is now ${updatedProposal.status}!` : '';
            showNotification(`Vote recorded!${statusMsg}`, 'success');
        } catch (error) {
            console.error('Error voting on proposal:', error);
            showNotification(`Error voting: ${error.message}`, 'error');
        }
    }

    async handleComment(proposalId) {
        if (!window.authManager || !window.authManager.isAuthenticated()) {
            showNotification('Please sign in to leave feedback', 'info');
            return;
        }

        const textarea = this.modal.querySelector(`.proposal-comment-input[data-proposal-id="${proposalId}"]`);
        const text = textarea ? textarea.value.trim() : '';
        if (!text) {
            showNotification('Please enter your feedback', 'error');
            return;
        }

        try {
            const token = window.authManager.getIdToken();
            const response = await fetch(`${API_ENDPOINT}/proposals/${proposalId}/comments`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ text })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `HTTP ${response.status}`);
            }

            const data = await response.json();

            // Add comment to local proposal data
            const idx = this.proposals.findIndex(p => p.proposal_id === proposalId);
            if (idx !== -1) {
                if (!this.proposals[idx].comments) this.proposals[idx].comments = [];
                this.proposals[idx].comments.push(data.comment);
            }

            this.renderProposals();
            showNotification('Feedback posted!', 'success');
        } catch (error) {
            console.error('Error posting feedback:', error);
            showNotification(`Error: ${error.message}`, 'error');
        }
    }

    async handleDelete(proposalId) {
        if (!confirm('Are you sure you want to delete this proposal? This cannot be undone.')) return;

        try {
            const token = window.authManager.getIdToken();
            const response = await fetch(`${API_ENDPOINT}/proposals/${proposalId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `HTTP ${response.status}`);
            }

            // Remove from local list
            this.proposals = this.proposals.filter(p => p.proposal_id !== proposalId);
            this.expandedProposalId = null;
            this.renderProposals();
            showNotification('Proposal deleted', 'success');
        } catch (error) {
            console.error('Error deleting proposal:', error);
            showNotification(`Error: ${error.message}`, 'error');
        }
    }
}

// Initialize proposals review
document.addEventListener('DOMContentLoaded', () => {
    window.proposalsReview = new ProposalsReview();
    window.openProposalsReview = () => window.proposalsReview.openModal();
});

// ============================================================================
// User Profile Popup
// ============================================================================

// Add event delegation for clickable usernames
document.addEventListener('click', async (e) => {
    if (e.target.classList.contains('clickable-username') || 
        e.target.closest('.clickable-username')) {
        const usernameEl = e.target.classList.contains('clickable-username') ? 
            e.target : e.target.closest('.clickable-username');
        const userId = usernameEl.dataset.userId;
        
        if (userId) {
            await showUserProfilePopup(userId, e.clientX, e.clientY);
        }
    }
});

async function showUserProfilePopup(userId, x, y) {
    // Remove any existing popup
    const existingPopup = document.getElementById('userProfilePopup');
    if (existingPopup) {
        existingPopup.remove();
    }
    
    // Create popup
    const popup = document.createElement('div');
    popup.id = 'userProfilePopup';
    popup.className = 'user-profile-popup';
    popup.innerHTML = `
        <div class="profile-popup-content">
            <div class="profile-popup-loading">
                <div class="spinner"></div>
                <p>Loading profile...</p>
            </div>
        </div>
    `;
    
    document.body.appendChild(popup);
    
    // Position popup near click
    const popupWidth = 320;
    const popupHeight = 200;
    let left = x + 10;
    let top = y + 10;
    
    // Keep popup on screen
    if (left + popupWidth > window.innerWidth) {
        left = x - popupWidth - 10;
    }
    if (top + popupHeight > window.innerHeight) {
        top = y - popupHeight - 10;
    }
    
    popup.style.left = left + 'px';
    popup.style.top = top + 'px';
    
    // Fetch profile data
    try {
        const response = await fetch(`${API_ENDPOINT}/profile/${userId}`);
        
        if (!response.ok) {
            throw new Error('Profile not found');
        }
        
        const data = await response.json();
        const profile = data.profile;
        
        // Update popup with profile data
        const credlyLink = profile.credly_url ? 
            `<a href="${escapeHtml(profile.credly_url)}" target="_blank" rel="noopener noreferrer" class="credly-badge-link">
                🏅 View Credly Badge
            </a>` : '';
        
        const builderLink = profile.builder_id ? 
            `<a href="https://builder.aws.com/community/@${escapeHtml(profile.builder_id)}" target="_blank" rel="noopener noreferrer" class="builder-profile-link">
                🏗️ View Builder Profile
            </a>` : '';
        
        popup.querySelector('.profile-popup-content').innerHTML = `
            <div class="profile-popup-header">
                <div class="profile-popup-avatar">👤</div>
                <div class="profile-popup-name">${escapeHtml(profile.display_name)}</div>
            </div>
            ${profile.bio ? `
                <div class="profile-popup-bio">
                    ${escapeHtml(profile.bio)}
                </div>
            ` : ''}
            <div class="profile-popup-links">
                ${credlyLink}
                ${builderLink}
            </div>
            <div class="profile-popup-stats">
                <div class="profile-popup-stat">
                    <span class="stat-value">${profile.stats.loves_count || 0}</span>
                    <span class="stat-label">Loves</span>
                </div>
                <div class="profile-popup-stat">
                    <span class="stat-value">${profile.stats.votes_count || 0}</span>
                    <span class="stat-label">Votes</span>
                </div>
                <div class="profile-popup-stat">
                    <span class="stat-value">${profile.stats.comments_count || 0}</span>
                    <span class="stat-label">Comments</span>
                </div>
            </div>
            ${(profile.badges && profile.badges.length > 0) ? `
                <div class="profile-popup-badges">
                    <div class="profile-popup-badges-title">🏆 Achievements</div>
                    <div class="profile-popup-badges-grid">
                        ${profile.badges.map(b => {
                            const reg = (typeof BADGE_REGISTRY_CLIENT !== 'undefined') ? BADGE_REGISTRY_CLIENT[b.badge_id] : null;
                            const icon = reg ? reg.icon : '🏅';
                            const name = reg ? reg.name : b.badge_id;
                            return `<span class="profile-popup-badge" title="${name}">${icon}</span>`;
                        }).join('')}
                    </div>
                </div>
            ` : ''}
        `;
        
    } catch (error) {
        console.error('Error loading profile:', error);
        popup.querySelector('.profile-popup-content').innerHTML = `
            <div class="profile-popup-error">
                <p>Could not load profile</p>
            </div>
        `;
    }
}

// Close popup when clicking outside
document.addEventListener('click', (e) => {
    const popup = document.getElementById('userProfilePopup');
    if (popup && !popup.contains(e.target) && !e.target.classList.contains('clickable-username')) {
        popup.remove();
    }
});

// Close popup on escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const popup = document.getElementById('userProfilePopup');
        if (popup) {
            popup.remove();
        }
    }
});


// Privacy Modal
function setupPrivacyModal() {
    const privacyLink = document.getElementById('privacyLink');
    const privacyModal = document.getElementById('privacyModal');
    const closePrivacyModal = document.getElementById('closePrivacyModal');
    
    if (privacyLink) {
        privacyLink.addEventListener('click', (e) => {
            e.preventDefault();
            privacyModal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        });
    }
    
    if (closePrivacyModal) {
        closePrivacyModal.addEventListener('click', () => {
            privacyModal.style.display = 'none';
            document.body.style.overflow = 'auto';
        });
    }
    
    // Close on outside click
    if (privacyModal) {
        privacyModal.addEventListener('click', (e) => {
            if (e.target === privacyModal) {
                privacyModal.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        });
    }
    
    // ESC key to close
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && privacyModal && privacyModal.style.display === 'flex') {
            privacyModal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    });
}

// Terms of Service Modal
function setupTermsModal() {
    const termsLink = document.getElementById('termsLink');
    const termsModal = document.getElementById('termsModal');
    const closeTermsModal = document.getElementById('closeTermsModal');
    
    if (termsLink) {
        termsLink.addEventListener('click', (e) => {
            e.preventDefault();
            termsModal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        });
    }
    
    if (closeTermsModal) {
        closeTermsModal.addEventListener('click', () => {
            termsModal.style.display = 'none';
            document.body.style.overflow = 'auto';
        });
    }
    
    // Close on outside click
    if (termsModal) {
        termsModal.addEventListener('click', (e) => {
            if (e.target === termsModal) {
                termsModal.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        });
    }
    
    // ESC key to close
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && termsModal && termsModal.style.display === 'flex') {
            termsModal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    });
}

// Data Deletion Modal
function setupDataDeletionModal() {
    const dataDeletionLink = document.getElementById('dataDeletionLink');
    const dataDeletionModal = document.getElementById('dataDeletionModal');
    const closeDataDeletionModal = document.getElementById('closeDataDeletionModal');
    
    if (dataDeletionLink) {
        dataDeletionLink.addEventListener('click', (e) => {
            e.preventDefault();
            dataDeletionModal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        });
    }
    
    if (closeDataDeletionModal) {
        closeDataDeletionModal.addEventListener('click', () => {
            dataDeletionModal.style.display = 'none';
            document.body.style.overflow = 'auto';
        });
    }
    
    // Close on outside click
    if (dataDeletionModal) {
        dataDeletionModal.addEventListener('click', (e) => {
            if (e.target === dataDeletionModal) {
                dataDeletionModal.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        });
    }
    
    // ESC key to close
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && dataDeletionModal && dataDeletionModal.style.display === 'flex') {
            dataDeletionModal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    });
}


// Service Name Change Badge - Per-card button
function createServiceNameBadge(post) {
    if (!window.serviceNameDetector || !window.serviceNameDetector.loaded) return '';
    
    const renamed = window.serviceNameDetector.detectRenamedService(post);
    if (!renamed) return '';
    
    // Return empty string - button will be added via JavaScript after card is created
    return '';
}

// Add service name buttons to post cards after they're rendered
function addServiceNameButtonsToCards() {
    if (!window.serviceNameDetector || !window.serviceNameDetector.loaded) return;
    
    const postCards = document.querySelectorAll('.post-card');
    
    postCards.forEach(card => {
        // Skip if button already exists
        if (card.querySelector('.service-name-btn')) return;
        
        const postId = card.dataset.postId;
        const post = allPosts.find(p => p.post_id === postId);
        if (!post) return;
        
        const renamed = window.serviceNameDetector.detectRenamedService(post);
        if (!renamed) return;
        
        // Create button
        const button = document.createElement('button');
        button.className = 'service-name-btn';
        button.innerHTML = `
            <span class="service-icon">🔄</span>
            <span class="service-tooltip">
                <strong>⚠️ Service Name Change</strong><br>
                ${escapeHtml(renamed.oldName)}<br>
                → ${escapeHtml(renamed.newName)}<br>
                <em>Renamed: ${renamed.renameDate}</em>
            </span>
        `;
        
        // Add to card (append to body of card, will be positioned via CSS)
        card.appendChild(button);
    });
}

// Initialize service name detector
if (window.serviceNameDetector) {
    window.serviceNameDetector.init().then(() => {
        // Add buttons after posts are loaded
        setTimeout(addServiceNameButtonsToCards, 1000);
    }).catch(err => {
        console.warn('Service name detector initialization failed:', err);
    });
}


// ============================================================================
// PANEL EXPANDER
// Expand-to-fullscreen capability for all 7 dashboard chart panels
// ============================================================================

class PanelExpander {
    static PANELS = {
        leaderboard:   { title: '🏆 Community Leaderboard', canvasId: 'leaderboardChart', renderer: 'renderExpandedLeaderboard', isHtml: false },
        recentBlogs:   { title: '📅 Posts Added (Last 30 Days)', canvasId: 'recentBlogsChart', renderer: 'renderExpandedRecentBlogs', isHtml: false },
        topLoved:      { title: '❤️ Most Loved Posts', canvasId: 'topLovedChart', renderer: 'renderExpandedTopLoved', isHtml: false },
        topVotes:      { title: '🔥 Top Posts by Votes', canvasId: 'topVotesChart', renderer: 'renderExpandedTopVotes', isHtml: false },
        topComments:   { title: '💬 Top Posts by Comments', canvasId: 'topCommentsChart', renderer: 'renderExpandedTopComments', isHtml: false },
        releases:      { title: '🚀 EUC Releases per Month', canvasId: 'releasesPerMonthChart', renderer: 'renderExpandedReleases', isHtml: false },
        kbLeaderboard: { title: '📝 KB Contributor Leaderboard', elementId: 'kbLeaderboard', renderer: 'renderExpandedKBLeaderboard', isHtml: true }
    };

    constructor() {
        this.overlay = null;
        this.activePanelId = null;
        this.expandedChart = null;
        this.triggerBtn = null;
        this._focusTrapHandler = null;
    }

    init() {
        this.createOverlay();
        this.injectExpandButtons();
    }

    injectExpandButtons() {
        const containers = document.querySelectorAll('.chart-container');
        containers.forEach(container => {
            // Determine panel id by matching canvas or element id
            let panelId = null;
            for (const [id, config] of Object.entries(PanelExpander.PANELS)) {
                const matchId = config.canvasId || config.elementId;
                if (container.querySelector('#' + matchId)) {
                    panelId = id;
                    break;
                }
            }
            if (!panelId) return;

            // Don't inject if already present
            if (container.querySelector('.panel-expand-btn')) return;

            // Ensure container is positioned for absolute child
            if (getComputedStyle(container).position === 'static') {
                container.style.position = 'relative';
            }

            const btn = document.createElement('button');
            btn.className = 'panel-expand-btn';
            btn.setAttribute('aria-label', 'Expand to full screen');
            btn.setAttribute('title', 'Expand to full screen');
            btn.setAttribute('data-panel-id', panelId);
            btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>';
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.open(panelId);
            });
            container.appendChild(btn);
        });
    }

    createOverlay() {
        if (this.overlay) return;

        this.overlay = document.createElement('div');
        this.overlay.className = 'panel-expand-overlay';
        this.overlay.setAttribute('role', 'dialog');
        this.overlay.setAttribute('aria-modal', 'true');
        this.overlay.setAttribute('aria-label', '');

        this.overlay.innerHTML = `
            <div class="panel-expand-backdrop"></div>
            <div class="panel-expand-content">
                <div class="panel-expand-header">
                    <h2 class="panel-expand-title"></h2>
                    <button class="panel-expand-close" aria-label="Close expanded view" title="Close">&times;</button>
                </div>
                <div class="panel-expand-controls"></div>
                <div class="panel-expand-body">
                    <canvas class="panel-expand-canvas"></canvas>
                    <div class="panel-expand-html-content"></div>
                </div>
            </div>
        `;

        document.body.appendChild(this.overlay);

        // Close button handler
        this.overlay.querySelector('.panel-expand-close').addEventListener('click', () => this.close());

        // Backdrop click handler
        this.overlay.querySelector('.panel-expand-backdrop').addEventListener('click', () => this.close());

        // Escape key handler
        this._escHandler = (e) => {
            if (e.key === 'Escape' && this.overlay.classList.contains('visible')) {
                this.close();
            }
        };
        document.addEventListener('keydown', this._escHandler);
    }

    open(panelId) {
        const config = PanelExpander.PANELS[panelId];
        if (!config) return;

        this.activePanelId = panelId;
        this.triggerBtn = document.querySelector(`.panel-expand-btn[data-panel-id="${panelId}"]`);

        // Set aria-label and title
        this.overlay.setAttribute('aria-label', config.title + ' expanded view');
        this.overlay.querySelector('.panel-expand-title').textContent = config.title;

        // Show/hide canvas vs HTML container
        const canvas = this.overlay.querySelector('.panel-expand-canvas');
        const htmlContent = this.overlay.querySelector('.panel-expand-html-content');
        const controls = this.overlay.querySelector('.panel-expand-controls');
        controls.innerHTML = '';

        if (config.isHtml) {
            canvas.style.display = 'none';
            htmlContent.style.display = 'block';
            htmlContent.innerHTML = '';
        } else {
            canvas.style.display = 'block';
            htmlContent.style.display = 'none';
        }

        // Show overlay
        this.overlay.classList.add('visible');
        this.overlay.classList.remove('closing');

        // Call the renderer
        try {
            if (config.isHtml) {
                this[config.renderer](htmlContent);
            } else {
                this[config.renderer](canvas, controls);
            }
        } catch (err) {
            console.error('Failed to render expanded panel:', err);
            const body = this.overlay.querySelector('.panel-expand-body');
            body.innerHTML = '<div class="panel-expand-error"><p>Chart unavailable</p></div>';
        }

        // Focus close button
        const closeBtn = this.overlay.querySelector('.panel-expand-close');
        if (closeBtn) closeBtn.focus();

        // Attach focus trap
        this._focusTrapHandler = (e) => this.trapFocus(e);
        document.addEventListener('keydown', this._focusTrapHandler);
    }

    close() {
        if (!this.overlay || !this.overlay.classList.contains('visible')) return;

        this.overlay.classList.add('closing');

        setTimeout(() => {
            this.overlay.classList.remove('visible');
            this.overlay.classList.remove('closing');

            // Destroy expanded Chart.js instance
            if (this.expandedChart) {
                this.expandedChart.destroy();
                this.expandedChart = null;
            }

            // Clear controls and HTML content
            const controls = this.overlay.querySelector('.panel-expand-controls');
            if (controls) controls.innerHTML = '';
            const htmlContent = this.overlay.querySelector('.panel-expand-html-content');
            if (htmlContent) htmlContent.innerHTML = '';

            // Restore the canvas element in case body was replaced by error
            const body = this.overlay.querySelector('.panel-expand-body');
            if (body && !body.querySelector('.panel-expand-canvas')) {
                body.innerHTML = '<canvas class="panel-expand-canvas"></canvas><div class="panel-expand-html-content"></div>';
            }

            // Restore focus to trigger button
            if (this.triggerBtn && document.body.contains(this.triggerBtn)) {
                this.triggerBtn.focus();
            } else {
                const fallback = document.querySelector('.chart-container');
                if (fallback) fallback.focus();
            }

            // Remove focus trap
            if (this._focusTrapHandler) {
                document.removeEventListener('keydown', this._focusTrapHandler);
                this._focusTrapHandler = null;
            }

            this.activePanelId = null;
        }, 200);
    }

    trapFocus(event) {
        if (event.key !== 'Tab' || !this.overlay.classList.contains('visible')) return;

        const focusable = this.overlay.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        if (focusable.length === 0) return;

        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (event.shiftKey) {
            if (document.activeElement === first) {
                event.preventDefault();
                last.focus();
            }
        } else {
            if (document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }
    }

    // ── Expanded Chart Renderers ───────────────────────────────────────────

    renderExpandedLeaderboard(canvas, controlsContainer) {
        if (!allPosts || allPosts.length === 0) {
            canvas.parentElement.innerHTML = '<div class="panel-expand-empty">No data available</div>';
            return;
        }

        const renderChart = (period) => {
            const now = new Date();
            let posts = allPosts;
            if (period === 'month') {
                const cutoff = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                posts = allPosts.filter(p => new Date(p.date_published) >= cutoff);
            } else if (period === 'week') {
                const cutoff = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                posts = allPosts.filter(p => new Date(p.date_published) >= cutoff);
            }

            const userActivity = {};
            posts.forEach(post => {
                (post.lovers || []).forEach(uid => {
                    if (!userActivity[uid]) userActivity[uid] = { loves: 0, votes: 0, comments: 0, total: 0, userId: uid };
                    userActivity[uid].loves++;
                    userActivity[uid].total++;
                });
                (post.voters || []).forEach(uid => {
                    if (!userActivity[uid]) userActivity[uid] = { loves: 0, votes: 0, comments: 0, total: 0, userId: uid };
                    userActivity[uid].votes++;
                    userActivity[uid].total++;
                });
                (post.comments || []).forEach(c => {
                    const uid = c.voter_id;
                    if (uid) {
                        if (!userActivity[uid]) userActivity[uid] = { loves: 0, votes: 0, comments: 0, total: 0, userId: uid };
                        userActivity[uid].comments++;
                        userActivity[uid].total++;
                    }
                });
            });

            const topUsers = Object.values(userActivity)
                .sort((a, b) => b.total - a.total)
                .slice(0, 15);

            if (topUsers.length === 0) {
                if (this.expandedChart) { this.expandedChart.destroy(); this.expandedChart = null; }
                canvas.style.display = 'none';
                let emptyEl = canvas.parentElement.querySelector('.panel-expand-empty');
                if (!emptyEl) { emptyEl = document.createElement('div'); emptyEl.className = 'panel-expand-empty'; canvas.parentElement.appendChild(emptyEl); }
                emptyEl.textContent = 'No activity data for this period';
                emptyEl.style.display = '';
                return;
            }

            // Ensure canvas is visible and hide empty message
            canvas.style.display = '';
            const emptyEl = canvas.parentElement.querySelector('.panel-expand-empty');
            if (emptyEl) emptyEl.style.display = 'none';

            const labels = topUsers.map((u, i) => {
                const medal = i === 0 ? '🥇 ' : i === 1 ? '🥈 ' : i === 2 ? '🥉 ' : '';
                return medal + getDisplayNameForUser(u.userId);
            });

            if (this.expandedChart) this.expandedChart.destroy();

            this.expandedChart = new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        { label: 'Loves', data: topUsers.map(u => u.loves), backgroundColor: 'rgba(233, 30, 99, 0.7)', borderColor: 'rgba(233, 30, 99, 1)', borderWidth: 2 },
                        { label: 'Votes', data: topUsers.map(u => u.votes), backgroundColor: 'rgba(33, 150, 243, 0.7)', borderColor: 'rgba(33, 150, 243, 1)', borderWidth: 2 },
                        { label: 'Comments', data: topUsers.map(u => u.comments), backgroundColor: 'rgba(255, 152, 0, 0.7)', borderColor: 'rgba(255, 152, 0, 1)', borderWidth: 2 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',
                    plugins: {
                        legend: { display: true, position: 'top' },
                        tooltip: {
                            callbacks: {
                                title: (ctx) => ctx.length > 0 ? getDisplayNameForUser(topUsers[ctx[0].dataIndex].userId) : '',
                                footer: (ctx) => ctx.length > 0 ? 'Total: ' + topUsers[ctx[0].dataIndex].total : ''
                            }
                        }
                    },
                    scales: {
                        x: { stacked: true, beginAtZero: true, ticks: { stepSize: 1 } },
                        y: { stacked: true }
                    },
                    onClick: (event, activeElements) => {
                        if (activeElements.length > 0) {
                            const user = topUsers[activeElements[0].index];
                            showUserProfilePopup(user.userId, event.native.clientX, event.native.clientY);
                        }
                    }
                }
            });
        };

        // Render time toggle buttons
        controlsContainer.innerHTML = `
            <div class="panel-expand-time-toggle" role="group" aria-label="Time period">
                <button class="time-toggle-btn active" data-period="all">All Time</button>
                <button class="time-toggle-btn" data-period="month">This Month</button>
                <button class="time-toggle-btn" data-period="week">This Week</button>
            </div>
        `;

        controlsContainer.querySelectorAll('.time-toggle-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                controlsContainer.querySelectorAll('.time-toggle-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                renderChart(btn.dataset.period);
            });
        });

        renderChart('all');
    }

    renderExpandedRecentBlogs(canvas) {
        if (!allPosts || allPosts.length === 0) {
            canvas.parentElement.innerHTML = '<div class="panel-expand-empty">No data available</div>';
            return;
        }

        const now = new Date();
        const weeks = [];
        for (let i = 0; i < 12; i++) {
            const end = new Date(now.getTime() - i * 7 * 24 * 60 * 60 * 1000);
            const start = new Date(now.getTime() - (i + 1) * 7 * 24 * 60 * 60 * 1000);
            weeks.push({ start, end, count: 0 });
        }
        weeks.reverse();

        allPosts.forEach(post => {
            const d = new Date(post.date_published);
            for (const week of weeks) {
                if (d >= week.start && d < week.end) {
                    week.count++;
                    break;
                }
            }
        });

        const formatShort = (d) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        const labels = weeks.map(w => formatShort(w.start));

        if (this.expandedChart) this.expandedChart.destroy();

        this.expandedChart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Posts Added',
                    data: weeks.map(w => w.count),
                    backgroundColor: 'rgba(255, 153, 0, 0.7)',
                    borderColor: 'rgba(255, 153, 0, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const week = weeks[ctx.dataIndex];
                                const count = week.count;
                                return `${count} post${count !== 1 ? 's' : ''} — ${formatShort(week.start)}–${formatShort(week.end)}`;
                            }
                        }
                    }
                },
                scales: {
                    y: { beginAtZero: true, ticks: { stepSize: 1 } }
                },
                onClick: (event, activeElements) => {
                    if (activeElements.length > 0) {
                        const week = weeks[activeElements[0].index];
                        this.close();
                        setTimeout(() => {
                            filteredPosts = allPosts.filter(p => {
                                const d = new Date(p.date_published);
                                return d >= week.start && d < week.end;
                            });
                            const searchInput = document.getElementById('searchInput');
                            if (searchInput) searchInput.value = '';
                            const formatShortDate = (d) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                            document.getElementById('filterLabel').textContent = `Showing: Posts from ${formatShortDate(week.start)} – ${formatShortDate(week.end)}`;
                            handleSort();
                        }, 250);
                    }
                }
            }
        });
    }

    renderExpandedTopLoved(canvas) {
        if (!allPosts || allPosts.length === 0) {
            canvas.parentElement.innerHTML = '<div class="panel-expand-empty">No data available</div>';
            return;
        }

        const topPosts = allPosts
            .filter(p => (p.love_votes || 0) > 0)
            .sort((a, b) => (b.love_votes || 0) - (a.love_votes || 0))
            .slice(0, 15);

        if (topPosts.length === 0) {
            canvas.parentElement.innerHTML = '<div class="panel-expand-empty">No loved posts yet</div>';
            return;
        }

        if (this.expandedChart) this.expandedChart.destroy();

        this.expandedChart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: topPosts.map(p => truncateTitle(p.title, 40)),
                datasets: [{
                    label: 'Loves',
                    data: topPosts.map(p => p.love_votes || 0),
                    backgroundColor: 'rgba(233, 30, 99, 0.7)',
                    borderColor: 'rgba(233, 30, 99, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: (ctx) => ctx.length > 0 ? topPosts[ctx[0].dataIndex].title : '',
                            label: (ctx) => {
                                const post = topPosts[ctx.dataIndex];
                                if (!post) return '';
                                return [`Author: ${post.authors || 'Unknown'}`, `${post.love_votes || 0} love${(post.love_votes || 0) !== 1 ? 's' : ''}`, `URL: ${post.url || ''}`];
                            }
                        }
                    }
                },
                scales: {
                    x: { beginAtZero: true, ticks: { stepSize: 1 } }
                },
                onClick: (event, activeElements) => {
                    if (activeElements.length > 0) {
                        const post = topPosts[activeElements[0].index];
                        const idx = filteredPosts.findIndex(p => p.post_id === post.post_id);
                        this.close();
                        setTimeout(() => {
                            if (window.zoomMode && idx >= 0) {
                                window.zoomMode.open(idx);
                            } else if (!window.zoomMode) {
                                showNotification('Zoom mode unavailable', 'error');
                            }
                        }, 300);
                    }
                }
            }
        });
    }

    renderExpandedTopVotes(canvas) {
        if (!allPosts || allPosts.length === 0) {
            canvas.parentElement.innerHTML = '<div class="panel-expand-empty">No data available</div>';
            return;
        }

        const topPosts = allPosts
            .map(p => ({ ...p, totalVotes: (p.needs_update_votes || 0) + (p.remove_post_votes || 0) }))
            .filter(p => p.totalVotes > 0)
            .sort((a, b) => b.totalVotes - a.totalVotes)
            .slice(0, 15);

        if (topPosts.length === 0) {
            canvas.parentElement.innerHTML = '<div class="panel-expand-empty">No votes yet</div>';
            return;
        }

        if (this.expandedChart) this.expandedChart.destroy();

        this.expandedChart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: topPosts.map(p => truncateTitle(p.title, 40)),
                datasets: [
                    { label: 'Needs Update', data: topPosts.map(p => p.needs_update_votes || 0), backgroundColor: 'rgba(255, 152, 0, 0.7)', borderColor: 'rgba(255, 152, 0, 1)', borderWidth: 2 },
                    { label: 'Remove Post', data: topPosts.map(p => p.remove_post_votes || 0), backgroundColor: 'rgba(244, 67, 54, 0.7)', borderColor: 'rgba(244, 67, 54, 1)', borderWidth: 2 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            title: (ctx) => ctx.length > 0 ? topPosts[ctx[0].dataIndex].title : '',
                            afterTitle: (ctx) => {
                                if (ctx.length === 0) return '';
                                const post = topPosts[ctx[0].dataIndex];
                                return `Total: ${post.totalVotes} votes\nNeeds Update: ${post.needs_update_votes || 0}\nRemove Post: ${post.remove_post_votes || 0}`;
                            }
                        }
                    }
                },
                scales: {
                    x: { stacked: true, beginAtZero: true, ticks: { stepSize: 1 } },
                    y: { stacked: true }
                },
                onClick: (event, activeElements) => {
                    if (activeElements.length > 0) {
                        const post = topPosts[activeElements[0].index];
                        const idx = filteredPosts.findIndex(p => p.post_id === post.post_id);
                        this.close();
                        setTimeout(() => {
                            if (window.zoomMode && idx >= 0) {
                                window.zoomMode.open(idx);
                            } else if (!window.zoomMode) {
                                showNotification('Zoom mode unavailable', 'error');
                            }
                        }, 300);
                    }
                }
            }
        });
    }

    renderExpandedTopComments(canvas) {
        if (!allPosts || allPosts.length === 0) {
            canvas.parentElement.innerHTML = '<div class="panel-expand-empty">No data available</div>';
            return;
        }

        const topPosts = allPosts
            .filter(p => (p.comment_count || 0) > 0)
            .sort((a, b) => (b.comment_count || 0) - (a.comment_count || 0))
            .slice(0, 15);

        if (topPosts.length === 0) {
            canvas.parentElement.innerHTML = '<div class="panel-expand-empty">No comments yet</div>';
            return;
        }

        if (this.expandedChart) this.expandedChart.destroy();

        this.expandedChart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: topPosts.map(p => truncateTitle(p.title, 40)),
                datasets: [{
                    label: 'Comments',
                    data: topPosts.map(p => p.comment_count || 0),
                    backgroundColor: 'rgba(76, 175, 80, 0.7)',
                    borderColor: 'rgba(76, 175, 80, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: (ctx) => ctx.length > 0 ? topPosts[ctx[0].dataIndex].title : '',
                            label: (ctx) => {
                                const post = topPosts[ctx.dataIndex];
                                if (!post) return '';
                                const count = post.comment_count || 0;
                                const lines = [`${count} comment${count !== 1 ? 's' : ''}`];
                                const comments = post.comments || [];
                                if (comments.length > 0) {
                                    const latest = comments[comments.length - 1];
                                    const preview = (latest.text || '').length > 80 ? (latest.text || '').substring(0, 77) + '...' : (latest.text || '');
                                    lines.push('Latest: "' + preview + '"');
                                } else {
                                    lines.push('No comments yet');
                                }
                                return lines;
                            }
                        }
                    }
                },
                scales: {
                    x: { beginAtZero: true, ticks: { stepSize: 1 } }
                },
                onClick: (event, activeElements) => {
                    if (activeElements.length > 0) {
                        const post = topPosts[activeElements[0].index];
                        this.close();
                        setTimeout(() => {
                            openCommentsModal(post.post_id, post.title);
                        }, 300);
                    }
                }
            }
        });
    }

    async renderExpandedReleases(canvas) {
        try {
            const response = await fetch(`${API_ENDPOINT}/whats-new`);
            if (!response.ok) throw new Error('Failed to fetch releases');

            const data = await response.json();
            const announcements = data.announcements || [];

            const now = new Date();
            const months = [];
            for (let i = 11; i >= 0; i--) {
                const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
                months.push({ key: d.toISOString().slice(0, 7), date: d, items: [] });
            }

            announcements.forEach(a => {
                const dp = a.date_published || '';
                for (const month of months) {
                    if (dp.startsWith(month.key)) { month.items.push(a); break; }
                    try {
                        const d = new Date(dp);
                        if (!isNaN(d) && d.toISOString().slice(0, 7) === month.key) { month.items.push(a); break; }
                    } catch (e) {}
                }
            });

            const labels = months.map(m => m.date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' }));

            if (this.expandedChart) this.expandedChart.destroy();

            this.expandedChart = new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Releases',
                        data: months.map(m => m.items.length),
                        backgroundColor: '#FF9900',
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                title: (ctx) => ctx.length > 0 ? labels[ctx[0].dataIndex] : '',
                                label: (ctx) => {
                                    const items = months[ctx.dataIndex].items;
                                    if (!items || items.length === 0) return 'No releases';
                                    return items.slice(0, 5).map(a => `${a.title || 'Untitled'} (${a.service_name || 'AWS'}) — ${a.date_published || ''}`);
                                },
                                afterLabel: (ctx) => {
                                    const items = months[ctx.dataIndex].items;
                                    if (items.length > 5) return `...and ${items.length - 5} more`;
                                    return '';
                                }
                            }
                        }
                    },
                    scales: {
                        y: { beginAtZero: true, ticks: { stepSize: 1 } }
                    }
                }
            });
        } catch (err) {
            console.warn('Failed to load expanded releases:', err);
            const body = canvas.parentElement;
            body.innerHTML = `<div class="panel-expand-error"><p>Failed to load data</p><button onclick="window.panelExpander.renderExpandedReleases(this.closest('.panel-expand-body').querySelector('.panel-expand-canvas'))">Retry</button></div>`;
        }
    }

    async renderExpandedKBLeaderboard(container) {
        try {
            const response = await fetch(`${API_ENDPOINT}/kb-contributors?period=all&limit=20`);
            if (!response.ok) throw new Error('Failed to fetch KB contributors');

            const data = await response.json();
            const contributors = data.contributors || data.leaderboard || [];

            if (contributors.length === 0) {
                container.innerHTML = '<div class="panel-expand-empty">No contributors yet</div>';
                return;
            }

            const rankBadges = ['🥇', '🥈', '🥉'];
            container.innerHTML = contributors.slice(0, 20).map((c, i) => {
                const name = (c.display_name || c.user_id || 'Anonymous').replace(/</g, '&lt;');
                const badge = rankBadges[i] || (i + 1);
                const topics = c.topics || [];
                const topicStr = topics.length > 0 ? topics.join(', ') : 'No topics';
                return `
                    <div class="kb-leaderboard-item" style="cursor:pointer;padding:10px 12px;border-bottom:1px solid rgba(255,255,255,0.1);" data-kb-index="${i}">
                        <div style="display:flex;align-items:center;gap:10px;">
                            <span class="kb-leaderboard-rank" style="min-width:32px;text-align:center;font-size:1.1rem;">${badge}</span>
                            <span class="kb-leaderboard-name" style="flex:1;font-weight:500;">${name}</span>
                            <div class="kb-leaderboard-stats" style="display:flex;gap:12px;font-size:0.85rem;opacity:0.8;">
                                <span>${c.total_edits || 0} edits</span>
                                <span>${c.total_points || 0} pts</span>
                            </div>
                        </div>
                        <div class="panel-expand-detail" style="display:none;margin-top:8px;margin-left:42px;">
                            <p style="margin:0 0 4px;font-size:0.85rem;opacity:0.7;">Entries: ${c.entry_count || c.total_edits || 0}</p>
                            <p style="margin:0;font-size:0.85rem;opacity:0.7;">Topics: ${topicStr}</p>
                        </div>
                    </div>
                `;
            }).join('');

            container.querySelectorAll('.kb-leaderboard-item').forEach(row => {
                row.addEventListener('click', () => {
                    const detail = row.querySelector('.panel-expand-detail');
                    if (detail) {
                        detail.style.display = detail.style.display === 'none' ? 'block' : 'none';
                    }
                });
            });
        } catch (err) {
            console.warn('Failed to load expanded KB leaderboard:', err);
            container.innerHTML = `<div class="panel-expand-error"><p>Failed to load data</p><button onclick="window.panelExpander.open('kbLeaderboard')">Retry</button></div>`;
        }
    }
}


// ============================================================================
// INNOVATION HUB
// Community-driven conceptual architectures with code snippets
// ============================================================================

class InnovationHub {
    constructor(apiEndpoint) {
        this.apiEndpoint = apiEndpoint;
        this.innovations = [];
        this.filters = { service: '', complexity: '', sort: 'newest', search: '' };
        this.browseContainer = null;
        this.detailModal = null;
        this.submissionModal = null;
        this.searchTimeout = null;
    }

    init() {
        this.createNavButton();
        this.createBrowseView();
        this.createDetailModal();
        this.createSubmissionModal();
    }

    createNavButton() {
        const header = document.querySelector('header');
        if (!header) return;
        const btn = document.createElement('button');
        btn.className = 'innovation-nav-btn';
        btn.innerHTML = '💡 Innovation Hub';
        btn.addEventListener('click', () => this.toggleBrowse());
        header.appendChild(btn);
    }

    toggleBrowse() {
        if (this.browseContainer.classList.contains('active')) {
            this.browseContainer.classList.remove('active');
        } else {
            this.browseContainer.classList.add('active');
            this.fetchInnovations();
        }
    }

    createBrowseView() {
        this.browseContainer = document.createElement('div');
        this.browseContainer.className = 'innovation-hub-container';
        this.browseContainer.innerHTML = `
            <div class="innovation-hub-inner">
                <div class="innovation-hub-header">
                    <h2>💡 Innovation Hub</h2>
                    <div class="innovation-hub-header-actions">
                        <button class="innovation-nav-btn" id="innovationSubmitBtn">+ Submit Innovation</button>
                        <button class="innovation-hub-close" id="innovationCloseBtn">✕ Close</button>
                    </div>
                </div>
                <div class="innovation-disclaimer">⚠️ All submissions are conceptual examples — not production code, not official AWS guidance. Use at your own discretion.</div>
                <div id="innovationFeatured"></div>
                <div class="innovation-filters">
                    <input type="text" id="innovationSearch" placeholder="Search innovations...">
                    <select id="innovationServiceFilter"><option value="">All Services</option></select>
                    <select id="innovationComplexityFilter">
                        <option value="">All Levels</option>
                        <option value="Beginner">Beginner</option>
                        <option value="Intermediate">Intermediate</option>
                        <option value="Advanced">Advanced</option>
                    </select>
                    <select id="innovationSort">
                        <option value="newest">Newest First</option>
                        <option value="oldest">Oldest First</option>
                        <option value="votes">Most Votes</option>
                    </select>
                </div>
                <div class="innovation-grid" id="innovationGrid"></div>
                <div class="innovation-empty" id="innovationEmpty" style="display:none;">No innovations found.</div>
            </div>`;
        document.body.appendChild(this.browseContainer);

        this.browseContainer.querySelector('#innovationCloseBtn').addEventListener('click', () => this.browseContainer.classList.remove('active'));
        this.browseContainer.querySelector('#innovationSubmitBtn').addEventListener('click', () => this.openSubmissionForm());
        this.browseContainer.querySelector('#innovationSearch').addEventListener('input', (e) => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => { this.filters.search = e.target.value; this.applyFilters(); }, 300);
        });
        this.browseContainer.querySelector('#innovationServiceFilter').addEventListener('change', (e) => { this.filters.service = e.target.value; this.applyFilters(); });
        this.browseContainer.querySelector('#innovationComplexityFilter').addEventListener('change', (e) => { this.filters.complexity = e.target.value; this.applyFilters(); });
        this.browseContainer.querySelector('#innovationSort').addEventListener('change', (e) => { this.filters.sort = e.target.value; this.applyFilters(); });
    }

    async fetchInnovations() {
        try {
            const params = new URLSearchParams();
            if (this.filters.service) params.set('service', this.filters.service);
            if (this.filters.complexity) params.set('complexity', this.filters.complexity);
            if (this.filters.sort) params.set('sort_by', this.filters.sort);
            if (this.filters.search) params.set('search', this.filters.search);
            const resp = await fetch(`${this.apiEndpoint}/innovations?${params.toString()}`);
            if (!resp.ok) throw new Error('Failed to fetch');
            const data = await resp.json();
            this.innovations = data.innovations || data || [];
            this.renderInnovations();
        } catch (err) {
            console.error('Failed to load innovations:', err);
            showNotification('Failed to load innovations. Please try again.', 'error');
        }
    }

    renderInnovations() {
        const grid = this.browseContainer.querySelector('#innovationGrid');
        const empty = this.browseContainer.querySelector('#innovationEmpty');
        grid.innerHTML = '';
        if (!this.innovations.length) { empty.style.display = 'block'; grid.style.display = 'none'; return; }
        empty.style.display = 'none'; grid.style.display = 'grid';

        // Update service filter options
        const services = new Set();
        this.innovations.forEach(i => (i.aws_services || []).forEach(s => services.add(s)));
        const serviceSelect = this.browseContainer.querySelector('#innovationServiceFilter');
        const currentVal = serviceSelect.value;
        serviceSelect.innerHTML = '<option value="">All Services</option>' + [...services].sort().map(s => `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`).join('');
        serviceSelect.value = currentVal;

        // Featured
        const featured = this.determineFeatured(this.innovations);
        const featuredEl = this.browseContainer.querySelector('#innovationFeatured');
        if (featured) {
            featuredEl.innerHTML = `
                <div class="innovation-featured" style="cursor:pointer;">
                    <span class="innovation-featured-badge">⭐ Featured Innovation</span>
                    <h3>${escapeHtml(featured.title)}</h3>
                    <p>${escapeHtml((featured.problem_statement || '').substring(0, 150))}${(featured.problem_statement || '').length > 150 ? '...' : ''}</p>
                    <div class="innovation-featured-meta">
                        <span class="innovation-complexity-badge ${(featured.complexity_level || '').toLowerCase()}">${escapeHtml(featured.complexity_level || '')}</span>
                        <span style="color:#94a3b8;font-size:0.8rem;">👍 ${(featured.upvotes || 0) - (featured.downvotes || 0)} votes</span>
                        <span style="color:#94a3b8;font-size:0.8rem;">💬 ${featured.comment_count || 0}</span>
                    </div>
                </div>`;
            featuredEl.querySelector('.innovation-featured').addEventListener('click', () => this.openDetail(featured));
        } else { featuredEl.innerHTML = ''; }

        this.innovations.forEach(innovation => grid.appendChild(this.createInnovationCard(innovation)));
    }

    createInnovationCard(innovation) {
        const card = document.createElement('div');
        card.className = 'innovation-card';
        const netVotes = (innovation.upvotes || 0) - (innovation.downvotes || 0);
        const desc = (innovation.problem_statement || '').substring(0, 120);
        card.innerHTML = `
            <h3>${escapeHtml(innovation.title || '')}</h3>
            <div class="innovation-card-desc">${escapeHtml(desc)}${desc.length < (innovation.problem_statement || '').length ? '...' : ''}</div>
            <div class="innovation-service-tags">${(innovation.aws_services || []).map(s => `<span class="innovation-service-tag">${escapeHtml(s)}</span>`).join('')}</div>
            <div class="innovation-card-disclaimer">Conceptual example — not production code, not official AWS guidance</div>
            <div class="innovation-card-footer">
                <span class="innovation-complexity-badge ${(innovation.complexity_level || '').toLowerCase()}">${escapeHtml(innovation.complexity_level || '')}</span>
                <div class="innovation-card-stats">
                    ${innovation.promoted_to_proposal_id ? '<span style="color:#10b981;font-weight:600;">📤 Promoted</span>' : ''}
                    <span>👍 ${netVotes}</span>
                    <span>💬 ${innovation.comment_count || 0}</span>
                </div>
            </div>`;
        card.addEventListener('click', () => this.openDetail(innovation));
        return card;
    }

    applyFilters() { this.fetchInnovations(); }

    determineFeatured(innovations) {
        if (!innovations.length) return null;
        return innovations.reduce((best, curr) => {
            const bestNet = (best.upvotes || 0) - (best.downvotes || 0);
            const currNet = (curr.upvotes || 0) - (curr.downvotes || 0);
            return currNet > bestNet ? curr : best;
        }, innovations[0]);
    }

    createDetailModal() {
        this.detailModal = document.createElement('div');
        this.detailModal.className = 'innovation-detail-modal';
        this.detailModal.innerHTML = '<div class="innovation-detail-inner" id="innovationDetailContent"></div>';
        document.body.appendChild(this.detailModal);
    }

    openDetail(innovation) {
        const content = this.detailModal.querySelector('#innovationDetailContent');
        const netVotes = (innovation.upvotes || 0) - (innovation.downvotes || 0);
        const snippetsHtml = (innovation.code_snippets || []).map(s => `
            <div class="innovation-code-block">
                <div class="innovation-code-label">${escapeHtml(s.language || 'code')}</div>
                <pre><code class="language-${escapeHtml(s.language || 'text')}">${escapeHtml(s.code || '')}</code></pre>
            </div>`).join('');

        content.innerHTML = `
            <div class="innovation-detail-header">
                <h2>${escapeHtml(innovation.title || '')}</h2>
                <button class="innovation-detail-close" id="innovationDetailClose">&times;</button>
            </div>
            <div class="innovation-disclaimer">⚠️ Conceptual example — not production code, not official AWS guidance</div>
            <div class="innovation-detail-meta">
                <span>By ${escapeHtml(innovation.display_name || 'Anonymous')}</span>
                <span>${innovation.created_at ? new Date(innovation.created_at).toLocaleDateString() : ''}</span>
                <span class="innovation-complexity-badge ${(innovation.complexity_level || '').toLowerCase()}">${escapeHtml(innovation.complexity_level || '')}</span>
            </div>
            <div class="innovation-detail-actions">
                <button id="innovationUpvote">👍 Upvote (${innovation.upvotes || 0})</button>
                <button id="innovationDownvote">👎 Downvote (${innovation.downvotes || 0})</button>
                <button id="innovationBookmark">⭐ Bookmark</button>
                <button id="innovationEdit" style="display:none;color:#3b82f6;">✏️ Edit</button>
                <button id="innovationDelete" style="display:none;color:#ef4444;">🗑️ Delete</button>
                <button id="innovationPromote" style="display:none;color:#10b981;">🚀 Promote to Proposal</button>
                <a id="innovationViewProposal" href="#" style="display:none;color:#6366f1;text-decoration:underline;cursor:pointer;">📋 View Proposal</a>
            </div>
            ${innovation.promoted_to_proposal_id ? '<div class="innovation-promoted-badge" style="background:#ecfdf5;border:1px solid #10b981;border-radius:8px;padding:8px 12px;margin:8px 0;color:#065f46;font-size:0.9em;">📤 This innovation has been promoted to a proposal</div>' : ''}
            <div class="innovation-detail-section"><h3>Problem Statement</h3><p>${escapeHtml(innovation.problem_statement || '')}</p></div>
            <div class="innovation-detail-section"><h3>Architecture Description</h3><p>${escapeHtml(innovation.architecture_description || '')}</p></div>
            ${innovation.architecture_diagram ? `<div class="innovation-detail-section"><h3>🏗️ Architecture Diagram</h3><div class="innovation-mermaid-container"><pre class="mermaid">${innovation.architecture_diagram}</pre></div></div>` : ''}
            ${snippetsHtml ? `<div class="innovation-detail-section"><h3>Code Snippets</h3>${snippetsHtml}</div>` : ''}
            <div class="innovation-detail-section"><h3>AWS Services</h3><div class="innovation-service-tags">${(innovation.aws_services || []).map(s => `<span class="innovation-service-tag">${escapeHtml(s)}</span>`).join('')}</div></div>
            <div class="innovation-comments">
                <h3>💬 Comments (<span id="innovationCommentCount">${innovation.comment_count || 0}</span>)</h3>
                <div id="innovationCommentsList"></div>
                <div class="innovation-comment-form">
                    <textarea id="innovationCommentText" placeholder="Add a comment..." maxlength="1000"></textarea>
                    <button id="innovationCommentSubmit">Post</button>
                </div>
            </div>`;

        // Show edit/delete/promote buttons if owner
        if (window.authManager && window.authManager.isAuthenticated()) {
            try {
                const token = window.authManager.getIdToken();
                if (token) {
                    const payload = JSON.parse(atob(token.split('.')[1]));
                    if (payload.sub === innovation.user_id) {
                        content.querySelector('#innovationEdit').style.display = '';
                        content.querySelector('#innovationDelete').style.display = '';
                        // Show promote button only if published and not already promoted
                        if (innovation.status === 'published' && !innovation.promoted_to_proposal_id) {
                            content.querySelector('#innovationPromote').style.display = '';
                        }
                    }
                    // Show view proposal link for anyone if promoted
                    if (innovation.promoted_to_proposal_id) {
                        content.querySelector('#innovationViewProposal').style.display = '';
                    }
                }
            } catch(e) {}
        } else if (innovation.promoted_to_proposal_id) {
            // Even unauthenticated users can see the proposal link
            content.querySelector('#innovationViewProposal').style.display = '';
        }

        content.querySelector('#innovationDetailClose').addEventListener('click', () => this.detailModal.classList.remove('active'));
        // Check if user already voted and disable buttons
        if (window.authManager && window.authManager.isAuthenticated()) {
            try {
                const token = window.authManager.getIdToken();
                const payload = JSON.parse(atob(token.split('.')[1]));
                const userId = payload.sub;
                const upvoters = innovation.upvoters || [];
                const downvoters = innovation.downvoters || [];
                if (upvoters.includes(userId) || downvoters.includes(userId)) {
                    const upBtn = content.querySelector('#innovationUpvote');
                    const downBtn = content.querySelector('#innovationDownvote');
                    upBtn.disabled = true; upBtn.style.opacity = '0.6';
                    downBtn.disabled = true; downBtn.style.opacity = '0.6';
                    if (upvoters.includes(userId)) upBtn.textContent = `👍 Upvoted (${innovation.upvotes || 0})`;
                    if (downvoters.includes(userId)) downBtn.textContent = `👎 Downvoted (${innovation.downvotes || 0})`;
                }
            } catch(e) {}
        }
        content.querySelector('#innovationUpvote').addEventListener('click', (e) => { e.stopPropagation(); this.voteOnInnovation(innovation.innovation_id, 'upvote'); });
        content.querySelector('#innovationDownvote').addEventListener('click', (e) => { e.stopPropagation(); this.voteOnInnovation(innovation.innovation_id, 'downvote'); });
        content.querySelector('#innovationBookmark').addEventListener('click', (e) => { e.stopPropagation(); this.toggleBookmark(innovation.innovation_id); });
        content.querySelector('#innovationEdit').addEventListener('click', (e) => { e.stopPropagation(); this.openEditForm(innovation); });
        content.querySelector('#innovationDelete').addEventListener('click', (e) => { e.stopPropagation(); this.deleteInnovation(innovation.innovation_id); });
        content.querySelector('#innovationPromote').addEventListener('click', (e) => { e.stopPropagation(); this.openPromotionPathSelector(innovation); });
        content.querySelector('#innovationViewProposal').addEventListener('click', (e) => {
            e.stopPropagation(); e.preventDefault();
            this.detailModal.classList.remove('active');
            setTimeout(() => {
                if (window.proposalsReview) { window.proposalsReview.openModal(); }
            }, 200);
        });
        content.querySelector('#innovationCommentSubmit').addEventListener('click', () => {
            const text = content.querySelector('#innovationCommentText').value.trim();
            if (text) this.submitComment(innovation.innovation_id, text);
        });

        this.detailModal.classList.add('active');
        this.loadComments(innovation.innovation_id);

        // Highlight code with Prism.js and render Mermaid diagrams
        setTimeout(async () => {
            if (typeof Prism !== 'undefined') Prism.highlightAll();
            if (typeof mermaid !== 'undefined') {
                const mermaidNodes = this.detailModal.querySelectorAll('.mermaid');
                for (const node of mermaidNodes) {
                    try {
                        const id = 'mermaid-' + Math.random().toString(36).substr(2, 9);
                        const { svg } = await mermaid.render(id, node.textContent);
                        node.innerHTML = svg;
                    } catch(e) {
                        console.warn('Mermaid render failed:', e);
                        const isOwner = window.authManager && window.authManager.isAuthenticated() && window.authManager.getUser()?.sub === innovation.user_id;
                        const regenBtn = isOwner ? `<button onclick="window.innovationHub.regenerateDiagram('${innovation.innovation_id}')" style="background:#3b82f6;color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:0.9rem;margin-top:8px;">🔄 Regenerate Diagram</button>` : '';
                        node.innerHTML = `<div style="background:#1e293b;border:1px solid #f59e0b;border-radius:8px;padding:16px;text-align:center;"><p style="color:#fbbf24;margin:0 0 4px;font-size:0.95rem;">⚠️ The AI-generated diagram has a syntax error and cannot be displayed.</p><p style="color:#94a3b8;margin:0;font-size:0.85rem;">${isOwner ? 'Click below to regenerate it with improved AI.' : 'The author can regenerate this diagram from their account.'}</p>${regenBtn}</div>`;
                    }
                }
            }
        }, 100);
    }

    async voteOnInnovation(id, type) {
        if (!window.authManager || !window.authManager.isAuthenticated()) {
            showNotification('Please sign in to vote.', 'info'); return;
        }
        try {
            const token = window.authManager.getIdToken();
            const resp = await fetch(`${this.apiEndpoint}/innovations/${id}/vote`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ innovation_id: id, vote_type: type })
            });
            const data = await resp.json();
            if (!resp.ok) { showNotification(data.error || 'Vote failed.', 'error'); return; }
            showNotification(`Vote recorded!`, 'success');
            // Update detail modal vote buttons with new counts
            const upBtn = this.detailModal.querySelector('#innovationUpvote');
            const downBtn = this.detailModal.querySelector('#innovationDownvote');
            if (data.innovation) {
                if (upBtn) upBtn.textContent = `👍 Upvote (${data.innovation.upvotes || 0})`;
                if (downBtn) downBtn.textContent = `👎 Downvote (${data.innovation.downvotes || 0})`;
            }
            if (upBtn) { upBtn.disabled = true; upBtn.style.opacity = '0.6'; }
            if (downBtn) { downBtn.disabled = true; downBtn.style.opacity = '0.6'; }
            this.fetchInnovations();
        } catch (err) { showNotification('Failed to vote. Please try again.', 'error'); }
    }

    async loadComments(innovationId) {
        try {
            const resp = await fetch(`${this.apiEndpoint}/innovations/${innovationId}/comments`);
            if (!resp.ok) return;
            const data = await resp.json();
            const comments = data.comments || [];
            const list = this.detailModal.querySelector('#innovationCommentsList');
            if (!comments.length) { list.innerHTML = '<p style="color:#64748b;font-size:0.85rem;">No comments yet.</p>'; return; }
            
            let currentUserId = null;
            try {
                if (window.authManager && window.authManager.isAuthenticated()) {
                    const token = window.authManager.getIdToken();
                    if (token) currentUserId = JSON.parse(atob(token.split('.')[1])).sub;
                }
            } catch(e) {}
            
            list.innerHTML = comments.map(c => {
                const isOwn = currentUserId && c.user_id === currentUserId;
                return `
                <div class="innovation-comment">
                    <div class="innovation-comment-header">
                        <span class="innovation-comment-author">${escapeHtml(c.display_name || 'Anonymous')}</span>
                        <span class="innovation-comment-time">${c.timestamp ? new Date(c.timestamp).toLocaleString() : ''}</span>
                        ${isOwn ? `<button class="innovation-comment-delete" data-comment-id="${c.comment_id}" data-innovation-id="${innovationId}" title="Delete comment">🗑️</button>` : ''}
                    </div>
                    <div class="innovation-comment-text">${escapeHtml(c.text || '')}</div>
                </div>`;
            }).join('');
            
            // Wire up delete buttons
            list.querySelectorAll('.innovation-comment-delete').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    if (!confirm('Delete this comment?')) return;
                    try {
                        const token = window.authManager.getIdToken();
                        const resp = await fetch(`${this.apiEndpoint}/innovations/${btn.dataset.innovationId}/comments`, {
                            method: 'DELETE',
                            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                            body: JSON.stringify({ comment_id: btn.dataset.commentId })
                        });
                        if (resp.ok) {
                            showNotification('Comment deleted.', 'success');
                            this.loadComments(btn.dataset.innovationId);
                        } else {
                            const d = await resp.json();
                            showNotification(d.error || 'Delete failed.', 'error');
                        }
                    } catch(err) { showNotification('Failed to delete comment.', 'error'); }
                });
            });
        } catch (err) { console.error('Failed to load comments:', err); }
    }

    async submitComment(innovationId, text) {
        if (!window.authManager || !window.authManager.isAuthenticated()) {
            showNotification('Please sign in to comment.', 'info'); return;
        }
        try {
            const token = window.authManager.getIdToken();
            const resp = await fetch(`${this.apiEndpoint}/innovations/${innovationId}/comments`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ innovation_id: innovationId, text: text })
            });
            if (!resp.ok) { const d = await resp.json(); showNotification(d.error || 'Comment failed.', 'error'); return; }
            showNotification('Comment posted!', 'success');
            this.detailModal.querySelector('#innovationCommentText').value = '';
            this.loadComments(innovationId);
            const countEl = this.detailModal.querySelector('#innovationCommentCount');
            if (countEl) countEl.textContent = parseInt(countEl.textContent || '0') + 1;
        } catch (err) { showNotification('Failed to post comment.', 'error'); }
    }

    async toggleBookmark(id) {
        if (!window.authManager || !window.authManager.isAuthenticated()) {
            showNotification('Please sign in to bookmark.', 'info'); return;
        }
        try {
            const token = window.authManager.getIdToken();
            const resp = await fetch(`${this.apiEndpoint}/innovations/${id}/bookmark`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ innovation_id: id })
            });
            const data = await resp.json();
            if (!resp.ok) { showNotification(data.error || 'Bookmark failed.', 'error'); return; }
            showNotification(data.action === 'bookmarked' ? 'Bookmarked!' : 'Bookmark removed.', 'success');
        } catch (err) { showNotification('Failed to toggle bookmark.', 'error'); }
    }

    openEditForm(innovation) {
        // Pre-fill the submission form with existing data for editing
        this.submissionModal.classList.add('active');
        this.submissionModal.querySelector('#innovationTitle').value = innovation.title || '';
        this.submissionModal.querySelector('#innovationProblem').value = innovation.problem_statement || '';
        this.submissionModal.querySelector('#innovationArch').value = innovation.architecture_description || '';
        // Set complexity radio button
        const complexityRadio = this.submissionModal.querySelector(`input[name="innovationComplexity"][value="${innovation.complexity_level || 'Beginner'}"]`);
        if (complexityRadio) complexityRadio.checked = true;
        this.submissionModal.querySelector('#innovationServices').value = (innovation.aws_services || []).join(', ');

        // Clear existing code snippets and re-add
        const snippetsContainer = this.submissionModal.querySelector('#innovationSnippets');
        if (snippetsContainer) {
            snippetsContainer.innerHTML = '';
            (innovation.code_snippets || []).forEach(s => {
                const div = document.createElement('div');
                div.className = 'innovation-snippet-entry';
                div.innerHTML = `<select class="snippet-lang"><option value="python">Python</option><option value="javascript">JavaScript</option><option value="typescript">TypeScript</option><option value="java">Java</option><option value="yaml">YAML</option><option value="json">JSON</option><option value="bash">Bash</option></select><textarea class="snippet-code" rows="4">${escapeHtml(s.code || '')}</textarea><button class="snippet-remove" type="button">✕</button>`;
                div.querySelector('select').value = s.language || 'python';
                div.querySelector('.snippet-remove').addEventListener('click', () => div.remove());
                snippetsContainer.appendChild(div);
            });
        }

        // Change submit button to update mode
        const submitBtn = this.submissionModal.querySelector('#innovationSubmitForm');
        if (submitBtn) {
            submitBtn.textContent = '💾 Update Innovation';
            submitBtn._editId = innovation.innovation_id;
        }
    }

    async updateInnovation(id, formData) {
        try {
            const token = window.authManager.getIdToken();
            const resp = await fetch(`${this.apiEndpoint}/innovations/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify(formData)
            });
            const data = await resp.json();
            if (!resp.ok) { showNotification(data.error || 'Update failed.', 'error'); return; }
            showNotification('Innovation updated! Diagram regenerated.', 'success');
            this.submissionModal.classList.remove('active');
            this.detailModal.classList.remove('active');
            this.fetchInnovations();
            // Reset submit button
            const submitBtn = this.submissionModal.querySelector('#innovationSubmitForm');
            if (submitBtn) { submitBtn.textContent = '🚀 Submit Innovation'; submitBtn._editId = null; }
        } catch (err) { showNotification('Failed to update innovation.', 'error'); }
    }

    async deleteInnovation(id) {
        if (!confirm('Are you sure you want to delete this innovation? This cannot be undone.')) return;
        if (!window.authManager || !window.authManager.isAuthenticated()) {
            showNotification('Please sign in to delete.', 'info'); return;
        }
        try {
            const token = window.authManager.getIdToken();
            const resp = await fetch(`${this.apiEndpoint}/innovations/${id}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ innovation_id: id })
            });
            if (!resp.ok) {
                const data = await resp.json();
                showNotification(data.error || data.message || 'Delete failed.', 'error'); return;
            }
            showNotification('Innovation deleted.', 'success');
            this.detailModal.classList.remove('active');
            this.fetchInnovations();
        } catch (err) { showNotification('Failed to delete innovation.', 'error'); }
    }

    async regenerateDiagram(id) {
        if (!window.authManager || !window.authManager.isAuthenticated()) {
            showNotification('Please sign in to regenerate.', 'info'); return;
        }
        const btn = this.detailModal.querySelector('button[onclick*="regenerateDiagram"]');
        if (btn) { btn.disabled = true; btn.textContent = '⏳ Regenerating...'; }
        try {
            const token = window.authManager.getIdToken();
            const resp = await fetch(`${this.apiEndpoint}/innovations/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ innovation_id: id, regenerate_diagram: true })
            });
            if (!resp.ok) {
                const data = await resp.json();
                showNotification(data.error || 'Regeneration failed.', 'error');
                if (btn) { btn.disabled = false; btn.textContent = '🔄 Regenerate Diagram'; }
                return;
            }
            const data = await resp.json();
            showNotification('Diagram regenerated. Reopening...', 'success');
            // Reopen the detail view with updated data
            if (data.innovation) {
                this.openDetail(data.innovation);
            } else {
                await this.fetchInnovations();
                const updated = this.innovations.find(i => i.innovation_id === id);
                if (updated) this.openDetail(updated);
            }
        } catch (err) {
            showNotification('Failed to regenerate diagram.', 'error');
            if (btn) { btn.disabled = false; btn.textContent = '🔄 Regenerate Diagram'; }
        }
    }

    createSubmissionModal() {
        this.submissionModal = document.createElement('div');
        this.submissionModal.className = 'innovation-submission-modal';
        this.submissionModal.innerHTML = `
            <div class="innovation-submission-inner">
                <div class="innovation-submission-header">
                    <h2>Submit an Innovation</h2>
                    <button class="innovation-detail-close" id="innovationSubmissionClose">&times;</button>
                </div>
                <div class="innovation-disclaimer">⚠️ Your submission will be labeled as a conceptual example — not production code, not official AWS guidance.</div>
                <div class="innovation-form-group"><label>Title (10–200 characters)</label><input type="text" id="innovationTitle" maxlength="200"><div class="innovation-form-error">Title must be 10–200 characters.</div></div>
                <div class="innovation-form-group"><label>Problem Statement (20–2000 characters)</label><textarea id="innovationProblem" maxlength="2000" rows="3"></textarea><div class="innovation-form-error">Problem statement must be 20–2000 characters.</div></div>
                <div class="innovation-form-group"><label>Architecture Description (50–5000 characters)</label><textarea id="innovationArch" maxlength="5000" rows="5"></textarea><div class="innovation-form-error">Architecture description must be 50–5000 characters.</div></div>
                <div class="innovation-form-group">
                    <label>Code Snippets (optional)</label>
                    <div class="innovation-snippet-list" id="innovationSnippets"></div>
                    <button class="innovation-add-snippet" id="innovationAddSnippet">+ Add Code Snippet</button>
                </div>
                <div class="innovation-form-group"><label>AWS Services (comma-separated, at least 1)</label><input type="text" id="innovationServices" placeholder="e.g. Amazon WorkSpaces, AWS Lambda"><div class="innovation-form-error">At least one AWS service is required.</div></div>
                <div class="innovation-form-group">
                    <label>Complexity Level</label>
                    <div class="innovation-complexity-radios">
                        <label><input type="radio" name="innovationComplexity" value="Beginner"> Beginner</label>
                        <label><input type="radio" name="innovationComplexity" value="Intermediate"> Intermediate</label>
                        <label><input type="radio" name="innovationComplexity" value="Advanced"> Advanced</label>
                    </div>
                    <div class="innovation-form-error">Please select a complexity level.</div>
                </div>
                <button class="innovation-submit-btn" id="innovationSubmitForm">Submit Innovation</button>
            </div>`;
        document.body.appendChild(this.submissionModal);

        this.submissionModal.querySelector('#innovationSubmissionClose').addEventListener('click', () => this.closeSubmissionForm());
        this.submissionModal.querySelector('#innovationAddSnippet').addEventListener('click', () => this.addSnippetField());
        this.submissionModal.querySelector('#innovationSubmitForm').addEventListener('click', () => this.submitInnovation());
    }

    addSnippetField() {
        const list = this.submissionModal.querySelector('#innovationSnippets');
        const item = document.createElement('div');
        item.className = 'innovation-snippet-item';
        item.innerHTML = `
            <button class="innovation-snippet-remove">✕ Remove</button>
            <select class="snippet-lang"><option value="python">Python</option><option value="javascript">JavaScript</option><option value="typescript">TypeScript</option><option value="java">Java</option><option value="yaml">YAML</option><option value="json">JSON</option><option value="bash">Bash</option></select>
            <textarea class="snippet-code" placeholder="Paste your code here..." rows="6"></textarea>`;
        item.querySelector('.innovation-snippet-remove').addEventListener('click', () => item.remove());
        list.appendChild(item);
    }

    openSubmissionForm() {
        if (!window.authManager || !window.authManager.isAuthenticated()) {
            showNotification('Please sign in to submit an innovation.', 'info'); return;
        }
        this.submissionModal.classList.add('active');
    }

    closeSubmissionForm() {
        this.submissionModal.classList.remove('active');
    }

    async submitInnovation() {
        // Clear errors
        this.submissionModal.querySelectorAll('.innovation-form-group').forEach(g => g.classList.remove('has-error'));
        const title = this.submissionModal.querySelector('#innovationTitle').value.trim();
        const problem = this.submissionModal.querySelector('#innovationProblem').value.trim();
        const arch = this.submissionModal.querySelector('#innovationArch').value.trim();
        const servicesRaw = this.submissionModal.querySelector('#innovationServices').value.trim();
        const complexity = this.submissionModal.querySelector('input[name="innovationComplexity"]:checked');
        const snippetItems = this.submissionModal.querySelectorAll('.innovation-snippet-item');

        let valid = true;
        if (title.length < 10 || title.length > 200) { this.submissionModal.querySelector('#innovationTitle').closest('.innovation-form-group').classList.add('has-error'); valid = false; }
        if (problem.length < 20 || problem.length > 2000) { this.submissionModal.querySelector('#innovationProblem').closest('.innovation-form-group').classList.add('has-error'); valid = false; }
        if (arch.length < 50 || arch.length > 5000) { this.submissionModal.querySelector('#innovationArch').closest('.innovation-form-group').classList.add('has-error'); valid = false; }
        const services = servicesRaw.split(',').map(s => s.trim()).filter(Boolean);
        if (!services.length) { this.submissionModal.querySelector('#innovationServices').closest('.innovation-form-group').classList.add('has-error'); valid = false; }
        if (!complexity) { this.submissionModal.querySelector('.innovation-complexity-radios').closest('.innovation-form-group').classList.add('has-error'); valid = false; }
        if (!valid) return;

        const code_snippets = [];
        snippetItems.forEach(item => {
            const lang = item.querySelector('.snippet-lang').value;
            const code = item.querySelector('.snippet-code').value;
            if (code.trim()) code_snippets.push({ language: lang, code: code });
        });

        const formData = {
            title, problem_statement: problem, architecture_description: arch,
            code_snippets, aws_services: services, complexity_level: complexity.value
        };

        // Check if we're in edit mode
        const editBtn = this.submissionModal.querySelector('#innovationSubmitForm');
        const editId = editBtn ? editBtn._editId : null;
        if (editId) {
            return this.updateInnovation(editId, formData);
        }

        try {
            const token = window.authManager.getIdToken();
            const submitBtn = this.submissionModal.querySelector('#innovationSubmitForm');
            submitBtn.disabled = true; submitBtn.textContent = 'Submitting...';
            const resp = await fetch(`${this.apiEndpoint}/innovations`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify(formData)
            });
            const data = await resp.json();
            submitBtn.disabled = false; submitBtn.textContent = 'Submit Innovation';
            if (!resp.ok) { showNotification(data.error || 'Submission failed.', 'error'); return; }
            showNotification('Innovation submitted successfully!', 'success');
            this.closeSubmissionForm();
            // Reset form
            this.submissionModal.querySelector('#innovationTitle').value = '';
            this.submissionModal.querySelector('#innovationProblem').value = '';
            this.submissionModal.querySelector('#innovationArch').value = '';
            this.submissionModal.querySelector('#innovationServices').value = '';
            this.submissionModal.querySelector('#innovationSnippets').innerHTML = '';
            const checked = this.submissionModal.querySelector('input[name="innovationComplexity"]:checked');
            if (checked) checked.checked = false;
            this.fetchInnovations();
        } catch (err) {
            showNotification('Failed to submit innovation.', 'error');
            const submitBtn = this.submissionModal.querySelector('#innovationSubmitForm');
            submitBtn.disabled = false; submitBtn.textContent = 'Submit Innovation';
        }
    }

    // ── Promotion Methods ──────────────────────────────────────────

    openPromotionPathSelector(innovation) {
        let modal = document.getElementById('innovationPromoteModal');
        if (modal) modal.remove();

        modal = document.createElement('div');
        modal.id = 'innovationPromoteModal';
        modal.className = 'innovation-submission-modal active';
        modal.innerHTML = `
            <div class="innovation-submission-inner" style="max-width:560px;">
                <div class="innovation-submission-header">
                    <h2>🚀 Promote to Proposal</h2>
                    <button class="innovation-submission-close" id="promoteModalClose">&times;</button>
                </div>
                <p style="color:#666;margin:0 0 16px;">Choose how you want to promote "<strong>${escapeHtml(innovation.title)}</strong>":</p>
                <div style="display:flex;gap:16px;flex-wrap:wrap;">
                    <div class="promote-path-card" data-path="article" style="flex:1;min-width:220px;border:2px solid #e5e7eb;border-radius:12px;padding:20px;cursor:pointer;transition:all 0.2s;">
                        <h3 style="margin:0 0 8px;">📝 Builder.AWS Article</h3>
                        <p style="color:#666;font-size:0.9em;margin:0;">Transform your innovation into a compelling technical article for the Builder.AWS community. Includes architecture diagram as downloadable PNG.</p>
                    </div>
                    <div class="promote-path-card" data-path="feature" style="flex:1;min-width:220px;border:2px solid #e5e7eb;border-radius:12px;padding:20px;cursor:pointer;transition:all 0.2s;">
                        <h3 style="margin:0 0 8px;">🎯 Service Feature Request</h3>
                        <p style="color:#666;font-size:0.9em;margin:0;">Distill your innovation into a formal feature request for the AWS EUC service team.</p>
                    </div>
                </div>
            </div>`;
        document.body.appendChild(modal);

        modal.querySelector('#promoteModalClose').addEventListener('click', () => modal.remove());
        modal.querySelectorAll('.promote-path-card').forEach(card => {
            card.addEventListener('mouseenter', () => { card.style.borderColor = '#3b82f6'; card.style.background = '#f0f7ff'; });
            card.addEventListener('mouseleave', () => { card.style.borderColor = '#e5e7eb'; card.style.background = ''; });
            card.addEventListener('click', () => {
                modal.remove();
                this.refineForPromotion(innovation, card.dataset.path);
            });
        });
    }

    async refineForPromotion(innovation, promotionPath) {
        if (!window.authManager || !window.authManager.isAuthenticated()) {
            showNotification('Please sign in to promote.', 'info'); return;
        }

        showNotification('AI is refining your innovation...', 'info');

        try {
            const token = window.authManager.getIdToken();
            const resp = await fetch(`${this.apiEndpoint}/innovations/${innovation.innovation_id}/promote`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ promotion_path: promotionPath, refine_only: true })
            });
            const data = await resp.json();
            if (!resp.ok) { showNotification(data.error || 'Refinement failed.', 'error'); return; }

            this.openPromotionReviewForm(innovation, promotionPath, data.refined_content);
        } catch (err) {
            showNotification('Failed to refine innovation. Please try again.', 'error');
        }
    }

    openPromotionReviewForm(innovation, promotionPath, refinedContent) {
        let modal = document.getElementById('innovationPromoteReviewModal');
        if (modal) modal.remove();

        modal = document.createElement('div');
        modal.id = 'innovationPromoteReviewModal';
        modal.className = 'innovation-submission-modal active';

        let formHtml = '';
        if (promotionPath === 'article') {
            const outline = (refinedContent.outline || []).join('\n');
            const keyTopics = (refinedContent.key_topics || []).join(', ');
            formHtml = `
                <div class="innovation-form-group"><label>Title</label><input type="text" id="promoteTitle" value="${escapeHtml(refinedContent.title || innovation.title || '')}" maxlength="200"></div>
                <div class="innovation-form-group"><label>Category</label>
                    <select id="promoteCategory">
                        ${['Announcement','Best Practices','Curation','Customer Story','Technical How-To','Thought Leadership'].map(c =>
                            `<option value="${c}" ${c === (refinedContent.category || 'Technical How-To') ? 'selected' : ''}>${c}</option>`
                        ).join('')}
                    </select>
                </div>
                <div class="innovation-form-group"><label>Summary</label><textarea id="promoteSummary" rows="3" maxlength="500">${escapeHtml(refinedContent.summary || '')}</textarea></div>
                <div class="innovation-form-group"><label>Outline (one section per line)</label><textarea id="promoteOutline" rows="5">${escapeHtml(outline)}</textarea></div>
                <div class="innovation-form-group"><label>Key Topics (comma-separated)</label><input type="text" id="promoteKeyTopics" value="${escapeHtml(keyTopics)}"></div>
                <div class="innovation-form-group"><label>Target Audience</label><input type="text" id="promoteTargetAudience" value="${escapeHtml(refinedContent.target_audience || '')}"></div>
                <div class="innovation-form-group"><label>Estimated Length</label>
                    <select id="promoteEstimatedLength">
                        ${['Short (600 words)','Medium (1200 words)','Long (2400 words)'].map(l =>
                            `<option value="${l}" ${l === (refinedContent.estimated_length || 'Long (2400 words)') ? 'selected' : ''}>${l}</option>`
                        ).join('')}
                    </select>
                </div>
                ${innovation.architecture_diagram ? '<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:12px;margin:8px 0;font-size:0.9em;color:#166534;">🏗️ Architecture diagram will be converted to PNG and included in the proposal.</div>' : ''}`;
        } else {
            const services = innovation.aws_services || [];
            formHtml = `
                <div class="innovation-form-group"><label>Primary AWS Service</label>
                    <select id="promoteService">
                        ${services.map(s => `<option value="${s}">${escapeHtml(s)}</option>`).join('')}
                        <option value="Other">Other</option>
                    </select>
                </div>
                <div class="innovation-form-group"><label>Feature Title</label><input type="text" id="promoteTitle" value="${escapeHtml(refinedContent.title || innovation.title || '')}" maxlength="200"></div>
                <div class="innovation-form-group"><label>Description</label><textarea id="promoteDescription" rows="4" maxlength="2000">${escapeHtml(refinedContent.refined_description || innovation.problem_statement || '')}</textarea></div>
                <div class="innovation-form-group"><label>Priority</label>
                    <select id="promotePriority">
                        ${['Critical','Nice to Have','Future Consideration'].map(p =>
                            `<option value="${p}">${p}</option>`
                        ).join('')}
                    </select>
                </div>
                <div class="innovation-form-group"><label>Use Case</label><textarea id="promoteUseCase" rows="3" maxlength="1000">${escapeHtml(innovation.architecture_description || '')}</textarea></div>`;
        }

        modal.innerHTML = `
            <div class="innovation-submission-inner" style="max-width:640px;max-height:85vh;overflow-y:auto;">
                <div class="innovation-submission-header">
                    <h2>${promotionPath === 'article' ? '📝 Article Proposal Review' : '🎯 Feature Proposal Review'}</h2>
                    <button class="innovation-submission-close" id="promoteReviewClose">&times;</button>
                </div>
                <p style="color:#666;margin:0 0 16px;">Review and edit the AI-refined content before submitting.</p>
                ${formHtml}
                <button class="innovation-submit-btn" id="promoteSubmitBtn" style="margin-top:16px;">🚀 Submit Proposal</button>
            </div>`;
        document.body.appendChild(modal);

        modal.querySelector('#promoteReviewClose').addEventListener('click', () => modal.remove());
        modal.querySelector('#promoteSubmitBtn').addEventListener('click', () => {
            this.submitPromotion(innovation, promotionPath, refinedContent, modal);
        });
    }

    async submitPromotion(innovation, promotionPath, refinedContent, modal) {
        if (!window.authManager || !window.authManager.isAuthenticated()) {
            showNotification('Please sign in.', 'info'); return;
        }

        const submitBtn = modal.querySelector('#promoteSubmitBtn');
        submitBtn.disabled = true; submitBtn.textContent = 'Submitting...';

        try {
            const token = window.authManager.getIdToken();
            let payload = { promotion_path: promotionPath, refine_only: false };

            if (promotionPath === 'article') {
                const outline = modal.querySelector('#promoteOutline').value.split('\n').map(s => s.trim()).filter(Boolean);
                const keyTopics = modal.querySelector('#promoteKeyTopics').value.split(',').map(s => s.trim()).filter(Boolean);
                payload.title = modal.querySelector('#promoteTitle').value.trim();
                payload.description = innovation.problem_statement || '';
                payload.category = modal.querySelector('#promoteCategory').value;
                payload.ai_generated_content = {
                    summary: modal.querySelector('#promoteSummary').value.trim(),
                    outline: outline,
                    key_topics: keyTopics,
                    target_audience: modal.querySelector('#promoteTargetAudience').value.trim(),
                    estimated_length: modal.querySelector('#promoteEstimatedLength').value,
                    writing_tips: refinedContent.writing_tips || ''
                };
            } else {
                payload.service = modal.querySelector('#promoteService').value;
                payload.title = modal.querySelector('#promoteTitle').value.trim();
                payload.description = modal.querySelector('#promoteDescription').value.trim();
                payload.priority = modal.querySelector('#promotePriority').value;
                payload.use_case = modal.querySelector('#promoteUseCase').value.trim();
            }

            const resp = await fetch(`${this.apiEndpoint}/innovations/${innovation.innovation_id}/promote`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();

            if (!resp.ok) { showNotification(data.error || 'Promotion failed.', 'error'); submitBtn.disabled = false; submitBtn.textContent = '🚀 Submit Proposal'; return; }

            showNotification('Innovation promoted to proposal!', 'success');
            modal.remove();
            this.detailModal.classList.remove('active');
            this.fetchInnovations();
        } catch (err) {
            showNotification('Failed to promote innovation.', 'error');
            submitBtn.disabled = false; submitBtn.textContent = '🚀 Submit Proposal';
        }
    }
}

// Initialize Innovation Hub
document.addEventListener('DOMContentLoaded', () => {
    window.innovationHub = new InnovationHub(API_ENDPOINT);
    window.innovationHub.init();
});

// ============================================================================
// INTERACTIVE TOUR
// Full-screen modal overlay with guided tour and exploration mode
// Converted from EUCContentHubTour.jsx to vanilla JS
// ============================================================================

class InteractiveTour {
    // ── Static Data ────────────────────────────────────────────────────────
    static FEATURES = [
        {
            id: 1, num: '01', icon: '🏠', name: 'EUC Content Hub', tag: 'header', color: '#6366f1',
            shortDesc: 'Your one-stop AWS EUC resource hub',
            description: 'A fully serverless, community-driven platform built end-to-end with Amazon Kiro. It unites content discovery, community engagement, expert AI chat, and gamified contribution in one seamless experience — solving every pain point from 10+ years in AWS EUC consulting.',
            bullets: ['490+ curated AWS EUC articles, blogs, and builder posts', 'Smart Crawler auto-indexes new content daily', 'Built 100% serverless on AWS — scalable and resilient']
        },
        {
            id: 2, num: '02', icon: '🔐', name: 'Sign In / Register', tag: 'auth', color: '#8b5cf6',
            shortDesc: 'Free account. Privacy-first design.',
            description: 'Create a free account to unlock the full EUC Content Hub experience — voting, commenting, bookmarking, chatbot history, and earning achievement badges. Designed from day one to protect participants with no PII required.',
            bullets: ['No personal or organizational data required', 'All comments screened through Amazon Bedrock', 'Conversations stored max 2 weeks, never indefinitely']
        },
        {
            id: 3, num: '03', icon: '✍️', name: 'Propose Article', tag: 'propose', color: '#a855f7',
            shortDesc: 'Submit ideas. Shape the EUC community.',
            description: 'Submit content ideas or feature proposals for existing AWS EUC services. Community votes and comments help surface what practitioners actually care about — providing real signal for the AWS EUC team.',
            bullets: ['Propose topics the community needs most', 'Real upvotes → real signal to the EUC team', 'Feature proposals for existing AWS EUC services']
        },
        {
            id: 4, num: '04', icon: '📡', name: 'Live News Ticker', tag: 'ticker', color: '#ec4899',
            shortDesc: 'Latest AWS EUC news, updated daily',
            description: 'A scrolling chyron at the top of the page surfaces the latest AWS EUC announcements and content additions every day. User-controlled scroll speed lets you pause and read what matters.',
            bullets: ['Updated daily with the latest EUC announcements', 'Adjustable scroll speed — pause on any item', 'Only publicly available information (no NDA content)']
        },
        {
            id: 5, num: '05', icon: '📊', name: 'Activity Dashboard', tag: 'dashboard', color: '#f97316',
            shortDesc: 'Community insights at a glance',
            description: 'A live analytics dashboard with expandable panels showing community leaderboards, weekly post additions, top loved and voted content, monthly EUC release activity, and KB contributor rankings. Click the expand button on any chart to open a full-screen interactive view with drill-down.',
            bullets: ['Community Leaderboard: top contributors by engagement', 'Trailing 12-month EUC releases-per-month chart', 'Top posts by loves, votes, and comments', 'Click the expand button on any chart to open a full-screen interactive view with drill-down']
        },
        {
            id: 6, num: '06', icon: '🔍', name: 'Search & Sort', tag: 'search', color: '#eab308',
            shortDesc: 'Find any EUC article in seconds',
            description: 'Instant full-text search across all 490+ indexed articles. Filter by title, author, or tags. Sort by newest, top-rated, or most commented. No more navigating across dozens of AWS documentation pages.',
            bullets: ['Search by title, author, or tags instantly', 'Sort: Newest First, Top Rated, Most Commented', '490 total posts with one-click Reload to refresh']
        },
        {
            id: 7, num: '07', icon: '🎛️', name: 'Smart Filters', tag: 'filters', color: '#22c55e',
            shortDesc: 'Slice the content library precisely',
            description: 'Quick-access filters let you zero in on exactly what you need. Filter by content source (AWS Blog, Builder.AWS, or All), see the full library, your most loved posts, content needing community review, articles flagged for updates, posts with any votes, and resolved items.',
            bullets: ['Source toggle: filter by AWS Blog, Builder.AWS, or All', 'Filters: Most Loved, Needs Review, Needs Update', 'Filters: Any Votes, Remove Post, Resolved', 'Category filters: Announcement, Technical How-To, and more']
        },
        {
            id: 8, num: '08', icon: '📄', name: 'Content Cards', tag: 'cards', color: '#14b8a6',
            shortDesc: 'Explore, vote, comment, and bookmark',
            description: 'Every article is displayed as a rich content card showing title, author, category, and an AI-generated quality score. Interact directly from the card — love it, comment, bookmark, add to your content cart, or flag for community review.',
            bullets: ['❤️ Love  🗳️ Vote  💬 Comment  ⭐ Star  ➕ Add to Cart', 'AI-generated quality/completion score per article', 'Stale content alerts when articles need updating']
        },
        {
            id: 9, num: '09', icon: '🏷️', name: 'Category Filters', tag: 'categories', color: '#06b6d4',
            shortDesc: 'Browse by content type',
            description: 'Quickly browse by content type: Announcements, Best Practices, Curation, Customer Stories, Technical How-To, and Thought Leadership. Each article is AI-classified using AWS-approved content categories.',
            bullets: ['Technical How-To: 374 articles (the deepest category)', 'Announcements: 76 | Customer Stories: 16', 'Best Practices: 10 | Thought Leadership: 5']
        },
        {
            id: 10, num: '10', icon: '🛒', name: 'Content Cart & Share', tag: 'cart', color: '#3b82f6',
            shortDesc: 'Curate and share AI-summarized packages',
            description: "Add articles to a cart and 'check out' with a shareable package that includes AI-generated summaries and links. Perfect for team handoffs, onboarding new colleagues, or capturing potential sales opportunities.",
            bullets: ['Add multiple articles to build a curated package', 'AI-generated summaries included automatically', 'Shareable link — ideal for team handoffs & onboarding']
        },
        {
            id: 11, num: '11', icon: '🤖', name: 'EUC AI Chatbot', tag: 'chatbot', color: '#8b5cf6',
            shortDesc: 'Ask anything. Get expert answers.',
            description: 'An AI chatbot powered by community knowledge and AWS Documentation. It first checks the community-contributed knowledge base, then falls back to AWS Docs for answers. Conversation history is saved for up to 2 weeks.',
            bullets: ['1️⃣ Ask → 2️⃣ Community KB → 3️⃣ AWS Docs fallback', 'Conversation history saved up to 2 weeks', 'Community members can contribute to the KB directly']
        },
        {
            id: 12, num: '12', icon: '🏆', name: 'Achievements & Badges', tag: 'badges', color: '#f59e0b',
            shortDesc: 'Earn recognition. Be seen.',
            description: 'Community engagement, gamified — Xbox Live-style achievement badges unlocked through participation. From creating your account to submitting approved proposals, your contributions are recognized and rewarded.',
            bullets: ['🌱 First Steps — Create your account', '🗳️ Lurker No More — Cast your first vote', '💡 Pitch Perfect — Get a proposal approved', '👑 OG — Account created in the first month of launch']
        },
        {
            id: 13, num: '13', icon: '💡', name: 'Innovation Hub', tag: 'innovation', color: '#10b981', isNew: true,
            shortDesc: 'From idea to article or feature request',
            description: 'A creative playground where community members share "art of the possible" ideas — innovative architectures, example code, and AWS service combinations. When an idea matures through community feedback, authors can promote it into a Builder.AWS article proposal or a service feature request. AI refines the content, the architecture diagram converts to a downloadable PNG, and everything carries forward into the proposal.',
            bullets: ['Submit innovative architecture ideas with code snippets', 'Community votes and comments help refine ideas', 'Promote mature ideas → Builder.AWS article or feature request', 'AI transforms your innovation into a polished proposal', 'Architecture diagram auto-converts to downloadable PNG']
        }
    ];

    static HOTSPOT_POSITIONS = {
        1:  { x: 30, y: 3 },   // Header title — top center-left
        2:  { x: 88, y: 3 },   // Sign In button — top right
        3:  { x: 96, y: 3 },   // Propose button — far top right
        4:  { x: 50, y: 10 },  // News Ticker chyron
        5:  { x: 50, y: 22 },  // Activity Dashboard
        6:  { x: 50, y: 38 },  // Search bar
        7:  { x: 5,  y: 52 },  // Filters sidebar — left
        8:  { x: 50, y: 52 },  // Content Cards — center
        9:  { x: 95, y: 52 },  // Categories sidebar — right
        10: { x: 3,  y: 96 },  // Cart — bottom-left corner
        11: { x: 97, y: 96 },  // Chatbot — bottom-right corner
        12: { x: 12, y: 3 },   // Achievements — upper-left near profile
        13: { x: 5, y: 3 }     // Innovation Hub — far top-left
    };

    static TOUR_DURATION = 7000;

    // ── Constructor ────────────────────────────────────────────────────────
    constructor(apiEndpoint) {
        this.apiEndpoint = apiEndpoint;
        this.activeId = null;
        this.tourStep = -1;
        this.completed = new Set();
        this.tourPaused = false;
        this.showWelcome = true;
        this.timerId = null;
        this.overlay = null;
        this._keyHandler = null;
    }

    // ── Lifecycle ──────────────────────────────────────────────────────────
    init() {
        this.injectStyles();
        this.buildOverlayDOM();
    }

    destroy() {
        this.clearAutoAdvance();
        if (this._keyHandler) {
            document.removeEventListener('keydown', this._keyHandler);
            this._keyHandler = null;
        }
        if (this.overlay && this.overlay.parentNode) {
            this.overlay.parentNode.removeChild(this.overlay);
        }
        this.overlay = null;
    }

    // ── CSS Injection (Task 3.2) ──────────────────────────────────────────
    injectStyles() {
        if (document.getElementById('euc-tour-styles')) return;
        const el = document.createElement('style');
        el.id = 'euc-tour-styles';
        el.textContent = `
            @keyframes pulseRing {
                0%   { transform: scale(1);    opacity: 0.8; }
                50%  { transform: scale(1.15); opacity: 0.4; }
                100% { transform: scale(1);    opacity: 0.8; }
            }
            @keyframes ripple {
                0%   { transform: scale(1);   opacity: 0.6; }
                100% { transform: scale(2.2); opacity: 0; }
            }
            @keyframes slideInRight {
                from { transform: translateX(40px); opacity: 0; }
                to   { transform: translateX(0);    opacity: 1; }
            }
            @keyframes fadeIn {
                from { opacity: 0; }
                to   { opacity: 1; }
            }
            @keyframes progressBar {
                from { width: 0%; }
                to   { width: 100%; }
            }
            @keyframes ticker {
                0%   { transform: translateX(0); }
                100% { transform: translateX(-50%); }
            }
            @keyframes glow {
                0%, 100% { box-shadow: 0 0 8px 2px rgba(99,102,241,0.3); }
                50%      { box-shadow: 0 0 18px 6px rgba(99,102,241,0.6); }
            }

            /* Tour overlay */
            .tour-overlay {
                position: fixed; inset: 0; z-index: 10000;
                background: rgba(0,0,0,0.85);
                display: none; flex-direction: column;
                font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
                color: #e2e8f0;
                animation: fadeIn 0.3s ease;
            }
            .tour-overlay.tour-visible { display: flex; }

            /* Top bar */
            .tour-topbar {
                display: flex; align-items: center; justify-content: space-between;
                padding: 14px 24px;
                border-bottom: 1px solid rgba(255,255,255,0.08);
                background: rgba(255,255,255,0.03);
                flex-shrink: 0;
            }
            .tour-topbar-left { display: flex; align-items: center; gap: 12px; }
            .tour-topbar-icon {
                width: 32px; height: 32px; border-radius: 8px;
                background: linear-gradient(135deg, #6366f1, #8b5cf6);
                display: flex; align-items: center; justify-content: center; font-size: 16px;
            }
            .tour-topbar-title { font-weight: 700; font-size: 15px; color: #f1f5f9; }
            .tour-topbar-sub { font-size: 11px; color: #64748b; margin-top: 1px; }
            .tour-topbar-actions { display: flex; align-items: center; gap: 10px; }

            /* Buttons */
            .tour-btn {
                border-radius: 8px; padding: 6px 14px; cursor: pointer;
                font-size: 12px; font-weight: 600; transition: background 0.15s;
                font-family: inherit;
            }
            .tour-btn:hover:not(:disabled) { filter: brightness(1.15); }
            .tour-btn:disabled { opacity: 0.35; cursor: not-allowed; }
            .tour-btn-pause {
                background: rgba(255,255,255,0.07);
                border: 1px solid rgba(255,255,255,0.12); color: #e2e8f0;
            }
            .tour-btn-exit {
                background: rgba(239,68,68,0.15);
                border: 1px solid rgba(239,68,68,0.3); color: #fca5a5;
            }
            .tour-btn-start {
                background: linear-gradient(135deg, #6366f1, #8b5cf6);
                border: none; color: #fff; padding: 8px 20px;
                font-size: 13px; font-weight: 700;
                box-shadow: 0 4px 15px rgba(99,102,241,0.4);
                transition: transform 0.15s, filter 0.15s;
            }
            .tour-btn-start:hover { transform: translateY(-1px); filter: brightness(1.15); }
            .tour-btn-start:active { transform: translateY(0); }
            .tour-btn-close {
                background: rgba(255,255,255,0.07);
                border: 1px solid rgba(255,255,255,0.12); color: #e2e8f0;
            }
            .tour-btn-nav {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.1); color: #e2e8f0;
                padding: 6px 18px;
            }
            .tour-btn-nav:hover:not(:disabled) { background: rgba(255,255,255,0.12); }

            /* Progress bar */
            .tour-progress-track {
                height: 3px; background: rgba(255,255,255,0.06); flex-shrink: 0;
            }
            .tour-progress-fill { height: 100%; }

            /* Three-panel layout */
            .tour-main { display: flex; flex: 1; overflow: hidden; }

            /* Sidebar */
            .tour-sidebar {
                width: 220px; flex-shrink: 0;
                border-right: 1px solid rgba(255,255,255,0.07);
                overflow-y: auto; padding: 12px 8px;
                display: flex; flex-direction: column; gap: 2px;
            }
            .tour-sidebar-label {
                font-size: 10px; font-weight: 700; color: #475569;
                letter-spacing: 0.08em; text-transform: uppercase;
                padding: 4px 8px 8px;
            }
            .tour-sidebar-btn {
                display: flex; align-items: center; gap: 8px;
                padding: 7px 10px; border-radius: 8px;
                border: 1px solid transparent; border-left: 3px solid transparent;
                background: transparent; cursor: pointer; text-align: left;
                width: 100%; transition: background 0.15s;
                font-family: inherit;
            }
            .tour-sidebar-btn:hover { background: rgba(255,255,255,0.08); }
            .tour-sidebar-btn-icon { font-size: 14px; line-height: 1; }
            .tour-sidebar-btn-name {
                font-size: 12px; font-weight: 500; color: #94a3b8;
                white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
                flex: 1; min-width: 0;
            }

            /* Center panel */
            .tour-center {
                flex: 1; display: flex; flex-direction: column;
                padding: 16px; overflow: hidden; min-width: 0;
            }
            .tour-diagram-wrap {
                flex: 1; position: relative; border-radius: 12px;
                overflow: hidden; border: 1px solid rgba(255,255,255,0.08);
                background: #0e1c2f; min-height: 0;
            }

            /* Diagram regions */
            .tour-diagram {
                position: absolute; inset: 0; display: flex; flex-direction: column;
                padding: 8px; box-sizing: border-box;
            }
            .tour-region { transition: all 0.25s ease; }

            /* Hotspots */
            .tour-hotspot {
                position: absolute; transform: translate(-50%, -50%);
                width: 22px; height: 22px; border-radius: 50%;
                display: flex; align-items: center; justify-content: center;
                font-size: 9px; font-weight: 800; color: #fff;
                transition: transform 0.2s ease, background 0.3s ease;
                border: none; padding: 0; font-family: inherit;
            }
            .tour-hotspot:hover { transform: translate(-50%, -50%) scale(1.15); }
            .tour-hotspot-ripple {
                position: absolute; inset: -4px; border-radius: 50%;
                animation: ripple 1.5s ease-out infinite; pointer-events: none;
            }

            /* Welcome overlay */
            .tour-welcome {
                position: absolute; inset: 0;
                background: rgba(10,15,30,0.82);
                display: flex; flex-direction: column; align-items: center;
                justify-content: center; gap: 20px;
                backdrop-filter: blur(6px); z-index: 20;
                animation: fadeIn 0.4s ease;
            }

            /* Detail panel */
            .tour-detail {
                width: 300px; flex-shrink: 0;
                border-left: 1px solid rgba(255,255,255,0.07);
                padding: 16px; overflow-y: auto;
                display: flex; flex-direction: column;
            }
            .tour-detail-content { animation: slideInRight 0.3s ease; flex: 1; }
            .tour-detail-empty {
                flex: 1; display: flex; flex-direction: column;
                align-items: center; justify-content: center;
                text-align: center; gap: 12px; color: #475569;
                animation: fadeIn 0.3s ease;
            }

            /* Step dots */
            .tour-dots {
                display: flex; align-items: center; justify-content: center;
                gap: 5px; margin-top: 10px; flex-shrink: 0;
            }
            .tour-dot { height: 6px; border-radius: 3px; transition: all 0.3s ease; }

            /* Nav controls */
            .tour-nav {
                display: flex; align-items: center; justify-content: center;
                gap: 10px; margin-top: 8px; flex-shrink: 0;
            }
            .tour-nav-counter { font-size: 11px; color: #64748b; }

            /* Mini chart bars */
            .tour-mini-chart {
                flex: 1; background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 6px; padding: 5px 6px;
            }
            .tour-mini-chart-label { font-size: 8px; font-weight: 600; color: #94a3b8; margin-bottom: 4px; }
            .tour-mini-chart-bars { display: flex; align-items: flex-end; gap: 2px; height: 24px; }

            /* Scrollbar */
            .tour-overlay ::-webkit-scrollbar { width: 4px; }
            .tour-overlay ::-webkit-scrollbar-track { background: transparent; }
            .tour-overlay ::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.4); border-radius: 4px; }
        `;
        document.head.appendChild(el);
    }

    // ── DOM Construction (Task 3.3) ───────────────────────────────────────
    buildOverlayDOM() {
        this.overlay = document.createElement('div');
        this.overlay.className = 'tour-overlay';
        this.overlay.setAttribute('role', 'dialog');
        this.overlay.setAttribute('aria-modal', 'true');
        this.overlay.setAttribute('aria-label', 'Interactive Feature Tour');
        document.body.appendChild(this.overlay);
    }

    getActiveFeature() {
        if (this.tourStep >= 0) return InteractiveTour.FEATURES[this.tourStep];
        if (this.activeId) return InteractiveTour.FEATURES.find(f => f.id === this.activeId);
        return null;
    }

    getHighlightId() {
        if (this.tourStep >= 0) return InteractiveTour.FEATURES[this.tourStep].id;
        return this.activeId;
    }

    render() {
        if (!this.overlay) return;
        const isTourActive = this.tourStep >= 0;
        const highlightId = this.getHighlightId();
        const displayFeature = this.getActiveFeature();

        let html = '';
        html += this.renderTopBar(isTourActive);
        if (isTourActive) html += this.renderProgressBar();
        html += '<div class="tour-main">';
        html += this.renderSidebar(highlightId, isTourActive);
        html += '<div class="tour-center">';
        html += '<div class="tour-diagram-wrap">';
        html += this.renderDiagram(highlightId);
        html += this.renderHotspots(highlightId, isTourActive);
        if (this.showWelcome && !isTourActive) html += this.renderWelcomeOverlay();
        html += '</div>';
        html += this.renderStepDots(highlightId, isTourActive);
        if (isTourActive) html += this.renderNavControls();
        html += '</div>';
        html += this.renderDetailPanel(displayFeature, isTourActive);
        html += '</div>';

        this.overlay.innerHTML = html;
        this._attachEventListeners();
    }

    renderTopBar(isTourActive) {
        let actions = '';
        if (isTourActive) {
            actions = `
                <button class="tour-btn tour-btn-pause" data-action="togglePause" aria-label="${this.tourPaused ? 'Resume tour' : 'Pause tour'}">
                    ${this.tourPaused ? '▶ Resume' : '⏸ Pause'}
                </button>
                <button class="tour-btn tour-btn-exit" data-action="stopTour" aria-label="Exit tour">✕ Exit Tour</button>
            `;
        } else {
            actions = `
                <button class="tour-btn tour-btn-start" data-action="startTour" aria-label="Start guided tour">▶ Start Guided Tour</button>
                <button class="tour-btn tour-btn-close" data-action="close" aria-label="Close tour overlay">✕ Close</button>
            `;
        }
        return `
            <div class="tour-topbar">
                <div class="tour-topbar-left">
                    <div class="tour-topbar-icon">🗺️</div>
                    <div>
                        <div class="tour-topbar-title">EUC Content Hub</div>
                        <div class="tour-topbar-sub">Interactive Feature Tour</div>
                    </div>
                </div>
                <div class="tour-topbar-actions">${actions}</div>
            </div>
        `;
    }

    renderProgressBar() {
        const f = InteractiveTour.FEATURES[this.tourStep];
        const anim = this.tourPaused ? 'none' : `progressBar ${InteractiveTour.TOUR_DURATION}ms linear forwards`;
        const w = this.tourPaused ? 'width:0%;' : '';
        return `
            <div class="tour-progress-track">
                <div class="tour-progress-fill" style="background:linear-gradient(90deg,${f.color},${f.color}cc);animation:${anim};${w}"></div>
            </div>
        `;
    }

    renderSidebar(highlightId, isTourActive) {
        let items = '';
        for (const f of InteractiveTour.FEATURES) {
            const isActive = highlightId === f.id;
            const isDone = this.completed.has(f.id);
            const borderStyle = isActive ? `border-color:${f.color}44;border-left:3px solid ${f.color};` : '';
            const bgStyle = isActive ? `background:${f.color}18;` : '';
            const opStyle = isTourActive && !isActive ? 'opacity:0.5;' : '';
            const curStyle = isTourActive ? 'cursor:default;' : '';
            const nameColor = isActive ? '#f1f5f9' : '#94a3b8';
            const nameWeight = isActive ? 600 : 500;
            let indicator = '';
            if (isDone) {
                indicator = '<span style="font-size:10px;color:#22c55e;flex-shrink:0;">✓</span>';
            } else if (isActive) {
                indicator = `<span style="width:6px;height:6px;border-radius:50%;background:${f.color};flex-shrink:0;"></span>`;
            }
            items += `
                <button class="tour-sidebar-btn" data-action="sidebarClick" data-feature-id="${f.id}"
                    style="${borderStyle}${bgStyle}${opStyle}${curStyle}"
                    aria-label="Feature ${f.num}: ${f.name}${isDone ? ' (completed)' : ''}${isActive ? ' (active)' : ''}">
                    <span class="tour-sidebar-btn-icon">${f.icon}</span>
                    <span class="tour-sidebar-btn-name" style="color:${nameColor};font-weight:${nameWeight};">${f.name}${f.isNew ? ' <span style="font-size:8px;font-weight:700;color:#fff;background:#ef4444;padding:1px 4px;border-radius:3px;vertical-align:middle;">NEW</span>' : ''}</span>
                    ${indicator}
                </button>
            `;
        }
        return `
            <div class="tour-sidebar">
                <div class="tour-sidebar-label">Features</div>
                ${items}
            </div>
        `;
    }

    renderDiagram(highlightId) {
        const activeTag = highlightId ? (InteractiveTour.FEATURES.find(f => f.id === highlightId) || {}).tag : null;

        const rs = (tag) => {
            const op = activeTag && activeTag !== tag ? 'opacity:0.45;' : 'opacity:1;';
            const feat = InteractiveTour.FEATURES.find(f => f.tag === tag);
            const filt = activeTag === tag && feat ? `filter:drop-shadow(0 0 6px ${feat.color}66);` : '';
            return `transition:all 0.25s ease;${op}${filt}`;
        };

        const cardBg = activeTag === 'cards' ? '#1e3a5f' : '#162032';
        const headerBg = activeTag === 'header' ? 'linear-gradient(90deg,#1a1060,#0e1a3d)' : 'linear-gradient(90deg,#0d1530,#091224)';
        const tickerBg = activeTag === 'ticker' ? '#1c1025' : '#120e1e';
        const filtersBg = activeTag === 'filters' ? '#0f2030' : '#0a1520';
        const cardsBg = activeTag === 'cards' ? '#0b1c2e' : '#081524';
        const catBg = activeTag === 'categories' ? '#0f2030' : '#0a1520';

        // Mini chart bars (static)
        const miniChart = (label, color) => {
            const bars = [30,55,40,70,45,80,35,60].map((h,i) =>
                `<div style="flex:1;height:${Math.min(h,100)}%;background:${color};border-radius:1px;opacity:${(0.7+i*0.04).toFixed(2)};"></div>`
            ).join('');
            return `<div class="tour-mini-chart"><div class="tour-mini-chart-label">${label}</div><div class="tour-mini-chart-bars">${bars}</div></div>`;
        };

        const cards = [
            { title: "AWS WorkSpaces Thin Client: What's New", cat: 'Announcement', pct: '90%' },
            { title: 'Configure AWS AppStream Session Mgmt', cat: 'Technical How-To', pct: '50%' },
            { title: 'Amazon WorkSpaces Graphics Bundles G6', cat: 'Announcement', pct: '90%' },
            { title: 'Microsoft Teams Optimization Now GA', cat: 'Announcement', pct: '90%' },
            { title: 'EUC with AWS Graviton: A Deep Dive', cat: 'Technical How-To', pct: '80%' },
            { title: 'How ZS Built Self-Serve Analytics', cat: 'Customer Story', pct: '80%' }
        ];

        const cardHtml = cards.map(c => {
            const catBgColor = c.cat === 'Announcement' ? 'rgba(168,85,247,0.25)' : c.cat === 'Customer Story' ? 'rgba(34,197,94,0.2)' : 'rgba(6,182,212,0.2)';
            const catColor = c.cat === 'Announcement' ? '#c084fc' : c.cat === 'Customer Story' ? '#86efac' : '#67e8f9';
            return `<div style="background:${cardBg};border-radius:5px;padding:5px 6px;border:1px solid rgba(255,255,255,0.06);">
                <div style="font-size:8px;font-weight:600;color:#cbd5e1;line-height:1.3;margin-bottom:3px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;">${c.title}</div>
                <div style="display:inline-block;font-size:7px;padding:1px 4px;border-radius:3px;background:${catBgColor};color:${catColor};font-weight:600;">${c.cat} ${c.pct}</div>
                <div style="display:flex;gap:5px;margin-top:4px;font-size:8px;color:#475569;"><span>❤️ 0</span><span>🗳️ 0</span><span>💬 0</span><span>⭐</span><span>➕</span></div>
            </div>`;
        }).join('');

        const filters = [
            { label: '490 Total Posts', active: true }, { label: '7 Most Loved', active: false },
            { label: '489 Needs Review', active: false }, { label: '0 Needs Update', active: false },
            { label: '1 Any Votes', active: false }, { label: '0 Resolved', active: false }
        ].map(f => `<div style="font-size:8px;color:${f.active ? '#f97316' : '#64748b'};padding:2px 4px;border-radius:3px;background:${f.active ? 'rgba(249,115,22,0.1)' : 'transparent'};font-weight:${f.active ? 700 : 400};">${f.label}</div>`).join('');

        const categories = [
            { label: 'Announcement', count: 76, color: '#a78bfa' },
            { label: 'Best Practices', count: 10, color: '#34d399' },
            { label: 'Curation', count: 9, color: '#60a5fa' },
            { label: 'Customer Story', count: 16, color: '#4ade80' },
            { label: 'Technical How-To', count: 374, color: '#67e8f9' },
            { label: 'Thought Leadership', count: 5, color: '#fbbf24' }
        ].map(c => `<div style="display:flex;justify-content:space-between;align-items:center;font-size:8px;color:#94a3b8;padding:2px 3px;">
            <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;">${c.label}</span>
            <span style="background:${c.color}22;color:${c.color};border-radius:8px;padding:0 4px;font-size:7px;font-weight:700;margin-left:3px;flex-shrink:0;">${c.count}</span>
        </div>`).join('');

        const cartBg = activeTag === 'cart' ? 'linear-gradient(135deg,#3b82f6,#6366f1)' : 'linear-gradient(135deg,#4f46e5,#7c3aed)';
        const chatBg = activeTag === 'chatbot' ? 'linear-gradient(135deg,#8b5cf6,#6366f1)' : 'linear-gradient(135deg,#f97316,#ea580c)';

        return `<div class="tour-diagram">
            <!-- Header -->
            <div class="tour-region" data-region="header" style="${rs('header')}background:${headerBg};border-radius:8px 8px 0 0;padding:10px 14px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;border:1px solid rgba(255,255,255,0.06);border-bottom:none;height:52px;box-sizing:border-box;">
                <div>
                    <div style="font-size:12px;font-weight:700;color:#e2e8f0;line-height:1;">EUC Content Hub</div>
                    <div style="font-size:9px;color:#64748b;margin-top:3px;">Discover &amp; explore AWS EUC content</div>
                </div>
                <div style="display:flex;gap:5px;">
                    <div data-region="auth" class="tour-region" style="${rs('auth')}background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.14);border-radius:5px;padding:3px 8px;font-size:9px;color:#94a3b8;font-weight:600;">🔐 Sign In</div>
                    <div data-region="propose" class="tour-region" style="${rs('propose')}background:linear-gradient(135deg,#6d28d9,#7c3aed);border-radius:5px;padding:3px 8px;font-size:9px;color:#e9d5ff;font-weight:600;">✍️ Propose</div>
                </div>
            </div>
            <!-- Ticker -->
            <div class="tour-region" data-region="ticker" style="${rs('ticker')}background:${tickerBg};border:1px solid rgba(255,255,255,0.06);border-bottom:none;display:flex;align-items:center;gap:6px;padding:5px 10px;flex-shrink:0;overflow:hidden;height:26px;box-sizing:border-box;">
                <div style="background:#f97316;border-radius:3px;padding:1px 5px;font-size:8px;font-weight:800;color:#fff;flex-shrink:0;">WHAT'S NEW</div>
                <div style="overflow:hidden;flex:1;">
                    <div style="display:inline-block;animation:ticker 18s linear infinite;white-space:nowrap;font-size:9px;color:#94a3b8;">
                        <span style="margin-right:40px;"><span style="color:#a78bfa;font-weight:600;">WorkSpaces Core</span> Amazon WorkSpaces now supports Microsoft Windows Server 2025</span>
                        <span style="margin-right:40px;"><span style="color:#34d399;font-weight:600;">WorkSpaces Apps</span> Amazon WorkSpaces Applications extends support to new regions</span>
                        <span style="margin-right:40px;"><span style="color:#a78bfa;font-weight:600;">WorkSpaces Core</span> Amazon WorkSpaces now supports Microsoft Windows Server 2025</span>
                        <span style="margin-right:40px;"><span style="color:#34d399;font-weight:600;">WorkSpaces Apps</span> Amazon WorkSpaces Applications extends support to new regions</span>
                    </div>
                </div>
            </div>
            <!-- Dashboard -->
            <div class="tour-region" data-region="dashboard" style="${rs('dashboard')}border:1px solid rgba(255,255,255,0.06);border-bottom:none;padding:6px;background:#0b1625;flex-shrink:0;">
                <div style="display:flex;gap:5px;margin-bottom:5px;">
                    ${miniChart('🏆 Leaderboard','#f59e0b')}${miniChart('📅 Posts Added','#f97316')}${miniChart('❤️ Most Loved','#ec4899')}${miniChart('🔥 Top Votes','#ef4444')}
                </div>
                <div style="display:flex;gap:5px;">
                    ${miniChart('💬 Comments','#22c55e')}${miniChart('🚀 EUC Releases','#f97316')}${miniChart('📝 KB Leaders','#eab308')}
                </div>
            </div>
            <!-- Search -->
            <div class="tour-region" data-region="search" style="${rs('search')}border:1px solid rgba(255,255,255,0.06);border-bottom:none;padding:5px 8px;background:#0e1b2e;display:flex;align-items:center;gap:6px;flex-shrink:0;height:32px;box-sizing:border-box;">
                <div style="flex:1;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:4px;padding:3px 8px;font-size:9px;color:#475569;">🔍 Search by title, author, or tags...</div>
                <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);border-radius:4px;padding:3px 8px;font-size:9px;color:#64748b;">Newest ▾</div>
                <div style="background:#f97316;border-radius:4px;padding:3px 8px;font-size:9px;color:#fff;font-weight:700;">Reload</div>
            </div>
            <!-- Main content area -->
            <div style="flex:1;display:flex;border:1px solid rgba(255,255,255,0.06);border-radius:0 0 8px 8px;overflow:hidden;min-height:0;">
                <!-- Filters -->
                <div class="tour-region" data-region="filters" style="${rs('filters')}width:90px;flex-shrink:0;border-right:1px solid rgba(255,255,255,0.06);background:${filtersBg};padding:6px;display:flex;flex-direction:column;gap:3px;">
                    <div style="font-size:8px;font-weight:700;color:#f97316;margin-bottom:2px;">📊 Filters</div>
                    ${filters}
                </div>
                <!-- Cards -->
                <div class="tour-region" data-region="cards" style="${rs('cards')}flex:1;background:${cardsBg};padding:6px;display:grid;grid-template-columns:1fr 1fr;gap:4px;overflow-y:hidden;align-content:start;">
                    ${cardHtml}
                </div>
                <!-- Categories -->
                <div class="tour-region" data-region="categories" style="${rs('categories')}width:90px;flex-shrink:0;border-left:1px solid rgba(255,255,255,0.06);background:${catBg};padding:6px;display:flex;flex-direction:column;gap:3px;">
                    <div style="font-size:8px;font-weight:700;color:#f59e0b;margin-bottom:2px;">🏷️ Categories</div>
                    ${categories}
                </div>
            </div>
            <!-- Cart floating button -->
            <div class="tour-region" data-region="cart" style="position:absolute;bottom:14px;left:14px;z-index:10;${rs('cart')}">
                <div style="width:24px;height:24px;border-radius:50%;background:${cartBg};display:flex;align-items:center;justify-content:center;font-size:11px;box-shadow:0 2px 8px rgba(99,102,241,0.5);">🛒</div>
            </div>
            <!-- Chatbot floating button -->
            <div class="tour-region" data-region="chatbot" style="position:absolute;bottom:14px;right:14px;z-index:10;${rs('chatbot')}">
                <div style="width:24px;height:24px;border-radius:50%;background:${chatBg};display:flex;align-items:center;justify-content:center;font-size:11px;box-shadow:0 2px 8px rgba(249,115,22,0.5);">💬</div>
            </div>
        </div>`;
    }

    renderHotspots(highlightId, isTourActive) {
        return InteractiveTour.FEATURES.map(f => {
            const pos = InteractiveTour.HOTSPOT_POSITIONS[f.id];
            const isActive = highlightId === f.id;
            const isDone = this.completed.has(f.id);
            const bg = isDone ? 'linear-gradient(135deg,#22c55e,#16a34a)'
                : isActive ? `linear-gradient(135deg,${f.color},${f.color}cc)`
                : 'linear-gradient(135deg,#f97316,#ea580c)';
            const z = isActive ? 15 : 10;
            const shadow = isActive ? `0 0 0 3px ${f.color}44,0 4px 12px ${f.color}66`
                : isDone ? '0 0 0 2px rgba(34,197,94,0.3)' : '0 2px 6px rgba(0,0,0,0.5)';
            const anim = isActive && !isDone ? 'animation:pulseRing 1.5s ease-in-out infinite;' : '';
            const cursor = isTourActive ? 'cursor:default;' : 'cursor:pointer;';
            const ripple = isActive ? `<div class="tour-hotspot-ripple" style="border:2px solid ${f.color};"></div>` : '';
            const label = isDone ? '✓' : f.num;
            return `<button class="tour-hotspot" data-action="hotspotClick" data-feature-id="${f.id}"
                style="left:${pos.x}%;top:${pos.y}%;background:${bg};z-index:${z};box-shadow:${shadow};${anim}${cursor}"
                aria-label="Feature ${f.num}: ${f.name}${isDone ? ' (completed)' : ''}${isActive ? ' (active)' : ''}">${label}${ripple}</button>`;
        }).join('');
    }

    renderWelcomeOverlay() {
        return `
            <div class="tour-welcome">
                <div style="font-size:48px;">🗺️</div>
                <div style="text-align:center;">
                    <div style="font-size:22px;font-weight:800;color:#f1f5f9;margin-bottom:8px;">Welcome to the EUC Content Hub Tour</div>
                    <div style="font-size:13px;color:#94a3b8;max-width:360px;line-height:1.6;">
                        Click <strong style="color:#a5b4fc;">Start Guided Tour</strong> to walk through all 12 features automatically, or click any <strong style="color:#fb923c;">numbered hotspot</strong> on the diagram to explore individually.
                    </div>
                </div>
                <button class="tour-btn tour-btn-start" data-action="startTour" aria-label="Start guided tour" style="border-radius:10px;padding:12px 32px;font-size:14px;box-shadow:0 6px 25px rgba(99,102,241,0.5);">▶ Start Guided Tour</button>
            </div>
        `;
    }

    renderStepDots(highlightId, isTourActive) {
        const dots = InteractiveTour.FEATURES.map((f, i) => {
            const isActive = isTourActive && i === this.tourStep;
            const isDone = this.completed.has(f.id);
            const w = isActive ? 20 : 6;
            const bg = isDone ? '#22c55e' : isActive ? f.color : highlightId === f.id ? f.color : 'rgba(255,255,255,0.15)';
            return `<div class="tour-dot" style="width:${w}px;background:${bg};" aria-label="Step ${i+1}${isDone ? ' completed' : ''}${isActive ? ' current' : ''}"></div>`;
        }).join('');
        return `<div class="tour-dots">${dots}</div>`;
    }

    renderNavControls() {
        const isFirst = this.tourStep === 0;
        const isLast = this.tourStep === InteractiveTour.FEATURES.length - 1;
        return `
            <div class="tour-nav">
                <button class="tour-btn tour-btn-nav" data-action="prevStep" ${isFirst ? 'disabled' : ''} aria-label="Previous feature">← Prev</button>
                <span class="tour-nav-counter">${this.tourStep + 1} of ${InteractiveTour.FEATURES.length}</span>
                <button class="tour-btn tour-btn-nav" data-action="nextStep" aria-label="${isLast ? 'Finish tour' : 'Next feature'}">${isLast ? 'Finish ✓' : 'Next →'}</button>
            </div>
        `;
    }

    renderDetailPanel(displayFeature, isTourActive) {
        if (!displayFeature) {
            return `
                <div class="tour-detail">
                    <div class="tour-detail-empty">
                        <div style="font-size:36px;">👆</div>
                        <div style="font-size:13px;font-weight:600;color:#64748b;">Select a feature</div>
                        <div style="font-size:11px;color:#374151;line-height:1.6;max-width:200px;">Click any numbered hotspot on the diagram, or choose a feature from the list on the left.</div>
                    </div>
                </div>
            `;
        }
        const f = displayFeature;
        const stepInfo = isTourActive ? `<span style="font-size:9px;color:#64748b;"> of ${String(InteractiveTour.FEATURES.length).padStart(2,'0')}</span>` : '';
        const bullets = f.bullets.map(b => `
            <div style="display:flex;gap:8px;align-items:flex-start;">
                <div style="width:5px;height:5px;border-radius:50%;background:${f.color};flex-shrink:0;margin-top:5px;"></div>
                <div style="font-size:12px;color:#cbd5e1;line-height:1.5;">${b}</div>
            </div>
        `).join('');
        return `
            <div class="tour-detail">
                <div class="tour-detail-content">
                    <div style="display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:20px;background:${f.color}22;border:1px solid ${f.color}44;margin-bottom:14px;">
                        <span style="font-size:12px;">${f.icon}</span>
                        <span style="font-size:10px;font-weight:700;color:${f.color};letter-spacing:0.05em;">Feature ${f.num}</span>
                        ${stepInfo}
                    </div>
                    <div style="font-size:20px;font-weight:800;color:#f1f5f9;line-height:1.2;margin-bottom:6px;">${f.name}${f.isNew ? ' <span style="font-size:10px;font-weight:700;color:#fff;background:#ef4444;padding:2px 6px;border-radius:4px;vertical-align:middle;margin-left:6px;">NEW!</span>' : ''}</div>
                    <div style="font-size:12px;color:${f.color};font-weight:600;margin-bottom:14px;">${f.shortDesc}</div>
                    <div style="height:1px;background:linear-gradient(90deg,${f.color}44,transparent);margin-bottom:14px;"></div>
                    <p style="font-size:12.5px;color:#94a3b8;line-height:1.7;margin:0 0 16px;">${f.description}</p>
                    <div style="background:rgba(255,255,255,0.03);border:1px solid ${f.color}22;border-radius:10px;padding:10px 12px;display:flex;flex-direction:column;gap:8px;">
                        <div style="font-size:10px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:2px;">Key Points</div>
                        ${bullets}
                    </div>
                    <a href="https://awseuccontent.com" target="_blank" rel="noopener noreferrer"
                        style="display:block;margin-top:16px;text-align:center;padding:9px;border-radius:8px;background:${f.color}18;border:1px solid ${f.color}33;color:${f.color};font-size:12px;font-weight:600;text-decoration:none;"
                        aria-label="Explore ${f.name} on awseuccontent.com">Explore on awseuccontent.com →</a>
                </div>
            </div>
        `;
    }

    // ── Event Delegation ──────────────────────────────────────────────────
    _attachEventListeners() {
        if (!this.overlay || this._clickHandlerAttached) return;
        this._clickHandlerAttached = true;
        this.overlay.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-action]');
            if (!btn) return;
            const action = btn.dataset.action;
            switch (action) {
                case 'startTour': this.startTour(); break;
                case 'stopTour': this.stopTour(); break;
                case 'close': this.close(); break;
                case 'togglePause': this.togglePause(); break;
                case 'nextStep': this.nextStep(); break;
                case 'prevStep': this.prevStep(); break;
                case 'hotspotClick': this.clickHotspot(parseInt(btn.dataset.featureId)); break;
                case 'sidebarClick': this.clickSidebarItem(parseInt(btn.dataset.featureId)); break;
            }
        });
    }

    // ── Tour Control (Task 4.1) ───────────────────────────────────────────
    open(startGuided = false) {
        if (!this.overlay) return;
        this.overlay.classList.add('tour-visible');
        if (startGuided) {
            this.startTour();
        } else {
            this.render();
        }
        this._attachKeyboardHandler();
    }

    close() {
        if (!this.overlay) return;
        const wasTourActive = this.tourStep >= 0;
        this.clearAutoAdvance();
        this.tourStep = -1;
        this.tourPaused = false;
        this.overlay.classList.remove('tour-visible');
        if (this._keyHandler) {
            document.removeEventListener('keydown', this._keyHandler);
            this._keyHandler = null;
        }
        if (wasTourActive) {
            this.saveTourCompleted();
        }
    }

    startTour() {
        this.tourStep = 0;
        this.completed = new Set();
        this.showWelcome = false;
        this.activeId = null;
        this.tourPaused = false;
        this.render();
        this.scheduleAutoAdvance();
    }

    stopTour() {
        this.clearAutoAdvance();
        this.tourStep = -1;
        this.tourPaused = false;
        this.saveTourCompleted();
        this.render();
    }

    nextStep() {
        this.clearAutoAdvance();
        if (this.tourStep >= 0 && this.tourStep < InteractiveTour.FEATURES.length) {
            this.completed.add(InteractiveTour.FEATURES[this.tourStep].id);
        }
        if (this.tourStep < InteractiveTour.FEATURES.length - 1) {
            this.tourStep++;
            this.render();
            this.scheduleAutoAdvance();
        } else {
            this.stopTour();
            this.close();
        }
    }

    prevStep() {
        if (this.tourStep > 0) {
            this.clearAutoAdvance();
            this.tourStep--;
            this.render();
            this.scheduleAutoAdvance();
        }
    }

    togglePause() {
        this.tourPaused = !this.tourPaused;
        if (this.tourPaused) {
            this.clearAutoAdvance();
        } else {
            this.scheduleAutoAdvance();
        }
        this.render();
    }

    goToStep(index) {
        if (index < 0 || index >= InteractiveTour.FEATURES.length) return;
        this.clearAutoAdvance();
        this.tourStep = index;
        this.render();
        this.scheduleAutoAdvance();
    }

    scheduleAutoAdvance() {
        this.clearAutoAdvance();
        if (this.tourStep < 0 || this.tourPaused) return;
        this.timerId = setTimeout(() => {
            if (this.tourStep < 0) return; // guard: overlay may have closed
            this.nextStep();
        }, InteractiveTour.TOUR_DURATION);
    }

    clearAutoAdvance() {
        if (this.timerId) {
            clearTimeout(this.timerId);
            this.timerId = null;
        }
    }

    // ── Exploration Mode (Task 4.2) ───────────────────────────────────────
    clickHotspot(featureId) {
        if (featureId < 1 || featureId > InteractiveTour.FEATURES.length) return;
        if (this.tourStep >= 0) {
            // During guided tour, jump to that step
            const idx = InteractiveTour.FEATURES.findIndex(f => f.id === featureId);
            if (idx >= 0) this.goToStep(idx);
            return;
        }
        this.showWelcome = false;
        this.activeId = this.activeId === featureId ? null : featureId;
        this.render();
    }

    clickSidebarItem(featureId) {
        if (featureId < 1 || featureId > InteractiveTour.FEATURES.length) return;
        if (this.tourStep >= 0) {
            // During guided tour, jump to that step
            const idx = InteractiveTour.FEATURES.findIndex(f => f.id === featureId);
            if (idx >= 0) this.goToStep(idx);
            return;
        }
        this.showWelcome = false;
        this.activeId = featureId;
        this.render();
    }

    // ── Keyboard Accessibility (Task 4.3) ─────────────────────────────────
    _attachKeyboardHandler() {
        if (this._keyHandler) {
            document.removeEventListener('keydown', this._keyHandler);
        }
        this._keyHandler = (e) => {
            if (!this.overlay || !this.overlay.classList.contains('tour-visible')) return;

            // Escape closes overlay
            if (e.key === 'Escape') {
                e.preventDefault();
                this.close();
                return;
            }

            // Arrow keys navigate features
            if (['ArrowDown', 'ArrowRight', 'ArrowUp', 'ArrowLeft'].includes(e.key)) {
                e.preventDefault();
                const features = InteractiveTour.FEATURES;
                if (this.tourStep >= 0) {
                    // In tour mode, arrow keys move steps
                    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
                        this.nextStep();
                    } else {
                        this.prevStep();
                    }
                } else {
                    // In exploration mode, arrow keys cycle features
                    const currentIdx = this.activeId ? features.findIndex(f => f.id === this.activeId) : -1;
                    let nextIdx;
                    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
                        nextIdx = currentIdx < features.length - 1 ? currentIdx + 1 : 0;
                    } else {
                        nextIdx = currentIdx > 0 ? currentIdx - 1 : features.length - 1;
                    }
                    this.clickSidebarItem(features[nextIdx].id);
                }
                return;
            }

            // Focus trap: Tab cycles within overlay
            if (e.key === 'Tab') {
                const focusable = this.overlay.querySelectorAll('button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])');
                if (focusable.length === 0) return;
                const first = focusable[0];
                const last = focusable[focusable.length - 1];
                if (e.shiftKey) {
                    if (document.activeElement === first || !this.overlay.contains(document.activeElement)) {
                        e.preventDefault();
                        last.focus();
                    }
                } else {
                    if (document.activeElement === last || !this.overlay.contains(document.activeElement)) {
                        e.preventDefault();
                        first.focus();
                    }
                }
            }
        };
        document.addEventListener('keydown', this._keyHandler);
    }

    // ── Persistence (Task 4.4) ────────────────────────────────────────────
    async saveTourCompleted() {
        try {
            const token = window.authManager && window.authManager.getIdToken();
            if (!token) return;
            await fetch(`${this.apiEndpoint}/profile`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ tour_completed: true })
            });
        } catch (err) {
            console.error('Failed to save tour completion:', err);
            if (typeof showNotification === 'function') {
                showNotification('Could not save tour progress', 'error');
            }
        }
    }
}

// Initialize interactive tour
document.addEventListener('DOMContentLoaded', () => {
    window.interactiveTour = new InteractiveTour(API_ENDPOINT);
    window.interactiveTour.init();
});
