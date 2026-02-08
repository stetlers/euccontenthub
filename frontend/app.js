// Configuration - Update this with your API Gateway URL after deployment
const API_ENDPOINT = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod'; // Will be replaced during deployment

let allPosts = [];
let filteredPosts = [];
let voterId = null;
let userBookmarks = []; // Track user's bookmarks
let currentFilter = 'all'; // Track current filter
let currentLabelFilters = []; // Track selected label filters (can be multiple)

// Chart instances
let leaderboardChart = null;
let recentBlogsChart = null;
let topLovedChart = null;
let topVotesChart = null;
let topCommentsChart = null;

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    initializeVoterId();
    loadPosts();
    loadUserBookmarks(); // Load bookmarks if authenticated
    setupEventListeners();
    setupPrivacyModal();
    setupTermsModal();
    setupDataDeletionModal();
});

function initializeVoterId() {
    // Get or create a unique voter ID (stored in localStorage)
    voterId = localStorage.getItem('voter_id');
    if (!voterId) {
        voterId = 'voter_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('voter_id', voterId);
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
        return;
    }

    filteredPosts.forEach(post => {
        const postCard = createPostCard(post);
        postsContainer.appendChild(postCard);
    });
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
    const dateUpdated = post.date_updated ? formatDate(post.date_updated) : null;
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
    
    const commentCount = post.comment_count || 0;
    
    const resolvedDate = post.resolved_date ? formatDate(post.resolved_date) : null;
    
    const label = post.label || null;
    const labelConfidence = post.label_confidence || 0;

    card.innerHTML = `
        ${status === 'resolved' ? '<div class="status-badge resolved">✓ Resolved</div>' : ''}
        ${status === 'archived' ? '<div class="status-badge archived">📦 Archived</div>' : ''}
        <div class="post-header">
            <h2 class="post-title">
                <a href="${url}" target="_blank" rel="noopener noreferrer">${escapeHtml(title)}</a>
            </h2>
            <button 
                class="bookmark-btn ${isBookmarked ? 'bookmarked' : ''}" 
                data-post-id="${post.post_id}"
                title="${isBookmarked ? 'Remove bookmark' : 'Bookmark this post'}"
            >
                <span class="bookmark-icon">${isBookmarked ? '⭐' : '☆'}</span>
            </button>
        </div>
        ${createLabelBadge(label, labelConfidence)}
        ${post.summary ? `<p class="post-summary">${escapeHtml(post.summary)}</p>` : ''}
        <div class="post-meta">
            <div class="meta-item">
                <span class="meta-icon">👤</span>
                <span>${escapeHtml(authors)}</span>
            </div>
            <div class="meta-item">
                <span class="meta-icon">📅</span>
                <span>Published: ${datePublished}</span>
            </div>
            ${dateUpdated ? `
                <div class="meta-item">
                    <span class="meta-icon">🔄</span>
                    <span>Updated: ${dateUpdated}</span>
                </div>
            ` : ''}
            ${status === 'resolved' && resolvedDate ? `
                <div class="meta-item">
                    <span class="meta-icon">✅</span>
                    <span>Resolved: ${resolvedDate}</span>
                </div>
            ` : ''}
            <div class="meta-item">
                <span class="comment-badge ${commentCount > 0 ? 'has-comments' : ''}" data-post-id="${post.post_id}" data-post-title="${escapeHtml(title)}">
                    💬 ${commentCount} ${commentCount === 1 ? 'Comment' : 'Comments'}
                </span>
            </div>
        </div>
        ${tags.length > 0 ? `
            <div class="post-tags">
                ${tags.slice(0, 5).map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}
                ${tags.length > 5 ? `<span class="tag">+${tags.length - 5} more</span>` : ''}
            </div>
        ` : ''}
        <div class="vote-section">
            <div class="love-section">
                <button 
                    class="love-btn ${hasLoved ? 'loved' : ''} ${status === 'resolved' ? 'disabled' : ''}" 
                    data-post-id="${post.post_id}" 
                    data-vote-type="love"
                    ${hasLoved || status === 'resolved' ? 'disabled' : ''}
                    title="${hasLoved ? 'You loved this post' : 'Love this post'}"
                >
                    <span class="love-icon">${hasLoved ? '❤️' : '🤍'}</span>
                    <span class="love-count">${loveVotes}</span>
                </button>
            </div>
            <div class="vote-buttons">
                <button 
                    class="vote-btn needs-update ${hasVoted || status === 'resolved' ? 'disabled' : ''}" 
                    data-post-id="${post.post_id}" 
                    data-vote-type="needs_update"
                    ${hasVoted || status === 'resolved' ? 'disabled' : ''}
                >
                    <span class="vote-icon">🔧</span>
                    <span class="vote-label">Needs Update</span>
                    <span class="vote-count">${needsUpdateVotes}</span>
                </button>
                <button 
                    class="vote-btn remove-post ${hasVoted || status === 'resolved' ? 'disabled' : ''}" 
                    data-post-id="${post.post_id}" 
                    data-vote-type="remove_post"
                    ${hasVoted || status === 'resolved' ? 'disabled' : ''}
                >
                    <span class="vote-icon">🗑️</span>
                    <span class="vote-label">Remove Post</span>
                    <span class="vote-count">${removePostVotes}</span>
                </button>
            </div>
            ${hasVoted ? '<p class="voted-message">✓ You have voted on this post</p>' : ''}
            ${hasLoved ? '<p class="loved-message">❤️ You loved this post</p>' : ''}
            ${status === 'resolved' ? `<p class="resolved-message">✅ Action taken - Post updated</p>` : ''}
        </div>
        ${(needsUpdateVotes > 0 || removePostVotes > 0) && status === 'pending' ? `
            <div class="action-section">
                <button class="resolve-btn" data-post-id="${post.post_id}">
                    <span class="resolve-icon">✓</span>
                    <span>Mark as Resolved</span>
                </button>
            </div>
        ` : ''}
        ${status === 'resolved' ? `
            <div class="action-section">
                <button class="unresolve-btn" data-post-id="${post.post_id}">
                    <span class="unresolve-icon">↺</span>
                    <span>Reopen</span>
                </button>
            </div>
        ` : ''}
    `;

    // Add event listeners to vote buttons
    const voteButtons = card.querySelectorAll('.vote-btn:not(.disabled)');
    voteButtons.forEach(btn => {
        btn.addEventListener('click', handleVote);
    });
    
    // Add event listener to love button
    const loveBtn = card.querySelector('.love-btn:not(.disabled)');
    if (loveBtn) {
        loveBtn.addEventListener('click', handleVote);
    }
    
    // Add event listener to resolve button
    const resolveBtn = card.querySelector('.resolve-btn');
    if (resolveBtn) {
        resolveBtn.addEventListener('click', handleResolve);
    }
    
    // Add event listener to unresolve button
    const unresolveBtn = card.querySelector('.unresolve-btn');
    if (unresolveBtn) {
        unresolveBtn.addEventListener('click', handleUnresolve);
    }
    
    // Add event listener to comment badge
    const commentBadge = card.querySelector('.comment-badge');
    if (commentBadge) {
        commentBadge.addEventListener('click', () => {
            openCommentsModal(post.post_id, title);
        });
    }
    
    // Add event listener to bookmark button
    const bookmarkBtn = card.querySelector('.bookmark-btn');
    if (bookmarkBtn) {
        bookmarkBtn.addEventListener('click', () => handleBookmark(post.post_id, bookmarkBtn));
    }

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
    const icon = button.querySelector('.bookmark-icon');
    icon.textContent = button.classList.contains('bookmarked') ? '⭐' : '☆';
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
        icon.textContent = isCurrentlyBookmarked ? '⭐' : '☆';
        button.title = isCurrentlyBookmarked ? 'Remove bookmark' : 'Bookmark this post';
        showNotification('Failed to update bookmark', 'error');
    }
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
        const response = await fetch(`${API_ENDPOINT}/crawl`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
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
        const response = await fetch(`${API_ENDPOINT}/posts/${postId}/comments`);
        
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
    
    return `
        <div class="comment-item">
            <div class="comment-header">
                <div class="comment-meta">
                    <span class="comment-author clickable-username" data-user-id="${voterId}">
                        👤 ${escapeHtml(displayName)}
                    </span>
                    <span class="comment-timestamp">${timestamp}</span>
                </div>
            </div>
            <div class="comment-text">${text}</div>
        </div>
    `;
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
        
        showNotification('Comment posted successfully! 💬', 'success');
        
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
function getDisplayNameForUser(userId) {
    // Try to find display name from comments
    for (const post of allPosts) {
        const comments = post.comments || [];
        for (const comment of comments) {
            if (comment.voter_id === userId && comment.display_name) {
                return comment.display_name;
            }
        }
    }
    // Fallback to truncated user ID
    return userId.substring(0, 8) + '...';
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
        // Open modal button
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
            alert('Please describe what you want to write about');
            return;
        }
        
        if (input.length < 20) {
            alert('Please provide more details (at least 20 characters)');
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
            const response = await fetch(`${API_ENDPOINT}/propose-article`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
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
            this.displayProposal(data.proposal);
            
        } catch (error) {
            console.error('Error submitting proposal:', error);
            alert(`Sorry, there was an error generating your proposal: ${error.message}`);
        } finally {
            submitBtn.disabled = false;
            btnText.style.display = 'inline';
            btnLoading.style.display = 'none';
        }
    }
    
    displayProposal(proposal) {
        // Hide form, show result
        this.form.style.display = 'none';
        this.result.style.display = 'block';
        
        // Populate result fields
        document.getElementById('resultTitle').textContent = proposal.title;
        document.getElementById('resultCategory').textContent = proposal.category;
        document.getElementById('resultSummary').textContent = proposal.summary;
        document.getElementById('resultAudience').textContent = proposal.target_audience;
        document.getElementById('resultLength').textContent = proposal.estimated_length;
        document.getElementById('resultTips').textContent = proposal.writing_tips;
        
        // Populate outline
        const outlineList = document.getElementById('resultOutline');
        outlineList.innerHTML = '';
        proposal.outline.forEach(item => {
            const li = document.createElement('li');
            li.textContent = item;
            outlineList.appendChild(li);
        });
        
        // Populate topics
        const topicsDiv = document.getElementById('resultTopics');
        topicsDiv.innerHTML = '';
        proposal.key_topics.forEach(topic => {
            const tag = document.createElement('span');
            tag.className = 'topic-tag';
            tag.textContent = topic;
            topicsDiv.appendChild(tag);
        });
        
        // Scroll to top of modal
        this.modal.querySelector('.modal-content').scrollTop = 0;
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
        
        const text = `
ARTICLE PROPOSAL
================

Title: ${this.currentProposal.title}
Category: ${this.currentProposal.category}

Summary:
${this.currentProposal.summary}

Outline:
${this.currentProposal.outline.map((item, i) => `${i + 1}. ${item}`).join('\n')}

Key Topics:
${this.currentProposal.key_topics.join(', ')}

Target Audience:
${this.currentProposal.target_audience}

Estimated Length:
${this.currentProposal.estimated_length}

Writing Tips:
${this.currentProposal.writing_tips}

Original Idea:
${this.currentProposal.original_input}
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
    new ArticleProposal();
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
