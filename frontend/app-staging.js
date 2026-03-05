```javascript
// Configuration - Staging environment
const API_ENDPOINT = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'; // Staging API endpoint

let allPosts = [];
let filteredPosts = [];
let voterId = null;
let userBookmarks = []; // Track user's bookmarks
let currentFilter = 'all'; // Track current filter
let currentLabelFilters = []; // Track selected label filters (can be multiple)
let cartManager = null; // Cart manager instance
let cartUI = null; // Cart UI instance

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
});

function updateAuthUI() {
    // Update UI elements based on authentication state
    const isAuthenticated = window.authManager && window.authManager.isAuthenticated();
    
    console.log('updateAuthUI called, isAuthenticated:', isAuthenticated);
    
    // Hide/show crawler button
    const crawlBtn = document.getElementById('crawlBtn');
    if (crawlBtn) {
        crawlBtn.style.display = isAuthenticated ? 'flex' : 'none';
        console.log('Crawler button display set to:', crawlBtn.style.display);
    }
}

// Make it globally accessible
window.updateAuthUI = updateAuthUI;

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
        
        // Initialize CartUI after posts are loaded
        // We'll do this in loadPosts() after allPosts is populated
        
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
        renderLabelFilters();
        handleFilter();
        loading.style.display = 'none';
        
        // Render charts
        renderCharts();
        
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

    // Start with all posts or search results
    let posts = query ? allPosts.filter(post => {
        const title = (post.title || '').toLowerCase();
        const authors = (post.authors || '').toLowerCase();
        const tags = (post.tags || '').toLowerCase();
        return title.includes(query) || authors.includes(query) || tags.includes(query);
    }) : [...allPosts];

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
                return