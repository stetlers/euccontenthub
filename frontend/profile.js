// Profile Management Module
// Handles user profile viewing and editing

class ProfileManager {
    constructor(apiEndpoint) {
        this.apiEndpoint = apiEndpoint;
        this.currentProfile = null;
        this.init();
    }
    
    init() {
        // Add profile modal to page
        this.createProfileModal();
        
        // Add profile link to header menu
        this.addProfileMenuItems();
        
        // Set up event listeners
        this.setupEventListeners();
    }
    
    createProfileModal() {
        const modal = document.createElement('div');
        modal.id = 'profileModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content profile-modal-content">
                <div class="modal-header">
                    <h2 id="profileModalTitle">My Profile</h2>
                    <button class="modal-close" id="closeProfileModal">&times;</button>
                </div>
                
                <div class="modal-body">
                    <!-- Profile Form -->
                    <div id="profileForm" class="profile-form">
                        <div class="form-group">
                            <label for="displayName">Display Name *</label>
                            <input 
                                type="text" 
                                id="displayName" 
                                class="form-input"
                                placeholder="How others will see you"
                                minlength="3"
                                maxlength="50"
                                required
                            />
                            <small class="form-help">3-50 characters. Use a pseudonym if you prefer.</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="profileBio">Bio</label>
                            <textarea 
                                id="profileBio" 
                                class="form-textarea"
                                placeholder="Tell us about yourself..."
                                maxlength="500"
                                rows="4"
                            ></textarea>
                            <small class="form-help">
                                <span id="bioCharCount">0</span> / 500 characters
                            </small>
                        </div>
                        
                        <div class="form-group">
                            <label for="credlyUrl">Credly Badge URL (optional)</label>
                            <input 
                                type="url" 
                                id="credlyUrl" 
                                class="form-input"
                                placeholder="https://www.credly.com/badges/..."
                            />
                            <small class="form-help">Link to your professional certifications</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="builderId">Builder Center ID (optional)</label>
                            <input 
                                type="text" 
                                id="builderId" 
                                class="form-input"
                                placeholder="your-username"
                                maxlength="50"
                            />
                            <small class="form-help">Your Builder.AWS community username (letters, numbers, _, - only)</small>
                        </div>
                        
                        <div class="profile-stats">
                            <h3>📊 Your Activity</h3>
                            <div class="stats-grid">
                                <div class="stat-item">
                                    <div class="stat-value" id="profileBookmarksCount">0</div>
                                    <div class="stat-label">Bookmarks</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-value" id="profileLovesCount">0</div>
                                    <div class="stat-label">Loves Given</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-value" id="profileVotesCount">0</div>
                                    <div class="stat-label">Votes Cast</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-value" id="profileCommentsCount">0</div>
                                    <div class="stat-label">Comments Posted</div>
                                </div>
                            </div>
                            <button id="viewActivityBtn" class="btn-secondary">
                                View Activity History
                            </button>
                        </div>
                        
                        <div class="form-actions">
                            <button id="cancelProfileBtn" class="btn-secondary">Cancel</button>
                            <button id="saveProfileBtn" class="btn-primary">
                                <span class="btn-text">Save Profile</span>
                                <span class="btn-loading" style="display: none;">
                                    <span class="spinner-small"></span> Saving...
                                </span>
                            </button>
                        </div>
                        
                        <div class="danger-zone">
                            <h3>⚠️ Danger Zone</h3>
                            <p>Once you delete your account, there is no going back. This will permanently delete:</p>
                            <ul>
                                <li>Your profile information</li>
                                <li>All your bookmarks</li>
                                <li>All your votes and loves</li>
                                <li>All your comments</li>
                            </ul>
                            <button id="deleteAccountBtn" class="btn-danger">
                                Delete Account
                            </button>
                        </div>
                    </div>
                    
                    <!-- Activity View -->
                    <div id="activityView" class="activity-view" style="display: none;">
                        <div class="activity-tabs">
                            <button class="activity-tab active" data-tab="bookmarks">
                                Bookmarks (<span id="bookmarksTabCount">0</span>)
                            </button>
                            <button class="activity-tab" data-tab="loves">
                                Loves (<span id="lovesTabCount">0</span>)
                            </button>
                            <button class="activity-tab" data-tab="votes">
                                Votes (<span id="votesTabCount">0</span>)
                            </button>
                            <button class="activity-tab" data-tab="comments">
                                Comments (<span id="commentsTabCount">0</span>)
                            </button>
                        </div>
                        
                        <div class="activity-content">
                            <div id="bookmarksTab" class="activity-tab-content active">
                                <div id="bookmarksList" class="activity-list"></div>
                            </div>
                            <div id="lovesTab" class="activity-tab-content">
                                <div id="lovesList" class="activity-list"></div>
                            </div>
                            <div id="votesTab" class="activity-tab-content">
                                <div id="votesList" class="activity-list"></div>
                            </div>
                            <div id="commentsTab" class="activity-tab-content">
                                <div id="commentsList" class="activity-list"></div>
                            </div>
                        </div>
                        
                        <div class="form-actions">
                            <button id="backToProfileBtn" class="btn-secondary">
                                ← Back to Profile
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    addProfileMenuItems() {
        // The profile button is already created by auth.js
        // We just need to add the click handler
        // No need to create a duplicate button
    }
    
    setupEventListeners() {
        // Profile button is handled by auth.js since it's created dynamically
        // No need to set up listener here
        
        // Close modal
        const closeBtn = document.getElementById('closeProfileModal');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeProfile());
        }
        
        // Close on outside click
        const modal = document.getElementById('profileModal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeProfile();
                }
            });
        }
        
        // Save profile
        const saveBtn = document.getElementById('saveProfileBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveProfile());
        }
        
        // Cancel
        const cancelBtn = document.getElementById('cancelProfileBtn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.closeProfile());
        }
        
        // Bio character counter
        const bioInput = document.getElementById('profileBio');
        if (bioInput) {
            bioInput.addEventListener('input', () => {
                const count = bioInput.value.length;
                document.getElementById('bioCharCount').textContent = count;
            });
        }
        
        // View activity
        const viewActivityBtn = document.getElementById('viewActivityBtn');
        if (viewActivityBtn) {
            viewActivityBtn.addEventListener('click', () => this.showActivity());
        }
        
        // Back to profile
        const backBtn = document.getElementById('backToProfileBtn');
        if (backBtn) {
            backBtn.addEventListener('click', () => this.showProfileForm());
        }
        
        // Activity tabs
        const activityTabs = document.querySelectorAll('.activity-tab');
        activityTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.dataset.tab;
                this.switchActivityTab(tabName);
            });
        });
        
        // Delete account
        const deleteBtn = document.getElementById('deleteAccountBtn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => this.deleteAccount());
        }
    }
    
    async openProfile() {
        if (!window.authManager || !window.authManager.isAuthenticated()) {
            showNotification('Please sign in to view your profile', 'error');
            return;
        }
        
        // Show modal
        const modal = document.getElementById('profileModal');
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        
        // Load profile data
        await this.loadProfile();
    }
    
    closeProfile() {
        const modal = document.getElementById('profileModal');
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        
        // Reset to profile form view
        this.showProfileForm();
    }
    
    async loadProfile() {
        try {
            const response = await fetch(`${this.apiEndpoint}/profile`, {
                headers: {
                    'Authorization': `Bearer ${window.authManager.getIdToken()}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to load profile');
            }
            
            const data = await response.json();
            this.currentProfile = data.profile;
            
            // Populate form
            document.getElementById('displayName').value = this.currentProfile.display_name || '';
            document.getElementById('profileBio').value = this.currentProfile.bio || '';
            document.getElementById('credlyUrl').value = this.currentProfile.credly_url || '';
            document.getElementById('builderId').value = this.currentProfile.builder_id || '';
            
            // Update character count
            const bioLength = (this.currentProfile.bio || '').length;
            document.getElementById('bioCharCount').textContent = bioLength;
            
            // Update stats
            const stats = this.currentProfile.stats || {};
            document.getElementById('profileBookmarksCount').textContent = stats.bookmarks_count || 0;
            document.getElementById('profileLovesCount').textContent = stats.loves_count || 0;
            document.getElementById('profileVotesCount').textContent = stats.votes_count || 0;
            document.getElementById('profileCommentsCount').textContent = stats.comments_count || 0;
            
        } catch (error) {
            console.error('Error loading profile:', error);
            showNotification('Failed to load profile', 'error');
        }
    }
    
    async saveProfile() {
        const displayName = document.getElementById('displayName').value.trim();
        const bio = document.getElementById('profileBio').value.trim();
        const credlyUrl = document.getElementById('credlyUrl').value.trim();
        const builderId = document.getElementById('builderId').value.trim();
        
        // Validation
        if (!displayName || displayName.length < 3) {
            showNotification('Display name must be at least 3 characters', 'error');
            return;
        }
        
        if (displayName.length > 50) {
            showNotification('Display name must be 50 characters or less', 'error');
            return;
        }
        
        if (bio.length > 500) {
            showNotification('Bio must be 500 characters or less', 'error');
            return;
        }
        
        if (credlyUrl && !credlyUrl.startsWith('https://www.credly.com/')) {
            showNotification('Credly URL must start with https://www.credly.com/', 'error');
            return;
        }
        
        if (builderId && !/^[a-zA-Z0-9_-]+$/.test(builderId)) {
            showNotification('Builder Center ID can only contain letters, numbers, underscores, and hyphens', 'error');
            return;
        }
        
        // Show loading state
        const saveBtn = document.getElementById('saveProfileBtn');
        const btnText = saveBtn.querySelector('.btn-text');
        const btnLoading = saveBtn.querySelector('.btn-loading');
        
        saveBtn.disabled = true;
        btnText.style.display = 'none';
        btnLoading.style.display = 'inline-flex';
        
        try {
            const response = await fetch(`${this.apiEndpoint}/profile`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${window.authManager.getIdToken()}`
                },
                body: JSON.stringify({
                    display_name: displayName,
                    bio: bio,
                    credly_url: credlyUrl,
                    builder_id: builderId
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to save profile');
            }
            
            const data = await response.json();
            this.currentProfile = data.profile;
            
            showNotification('Profile saved successfully! ✓', 'success');
            
            // Update user menu display name
            this.updateUserMenuName(displayName);
            
        } catch (error) {
            console.error('Error saving profile:', error);
            showNotification(error.message || 'Failed to save profile', 'error');
        } finally {
            saveBtn.disabled = false;
            btnText.style.display = 'inline';
            btnLoading.style.display = 'none';
        }
    }
    
    async showActivity() {
        // Hide profile form, show activity view
        document.getElementById('profileForm').style.display = 'none';
        document.getElementById('activityView').style.display = 'block';
        document.getElementById('profileModalTitle').textContent = 'My Activity';
        
        // Load activity data
        await this.loadActivity();
    }
    
    showProfileForm() {
        document.getElementById('profileForm').style.display = 'block';
        document.getElementById('activityView').style.display = 'none';
        document.getElementById('profileModalTitle').textContent = 'My Profile';
    }
    
    async loadActivity() {
        try {
            // Load activity history
            const activityResponse = await fetch(`${this.apiEndpoint}/profile/activity`, {
                headers: {
                    'Authorization': `Bearer ${window.authManager.getIdToken()}`
                }
            });
            
            if (!activityResponse.ok) {
                throw new Error('Failed to load activity');
            }
            
            const activityData = await activityResponse.json();
            
            // Load bookmarks
            const bookmarksResponse = await fetch(`${this.apiEndpoint}/bookmarks`, {
                headers: {
                    'Authorization': `Bearer ${window.authManager.getIdToken()}`
                }
            });
            
            const bookmarksData = bookmarksResponse.ok ? await bookmarksResponse.json() : { bookmarks: [] };
            
            // Update tab counts
            document.getElementById('bookmarksTabCount').textContent = bookmarksData.bookmarks.length;
            document.getElementById('lovesTabCount').textContent = activityData.loves.length;
            document.getElementById('votesTabCount').textContent = activityData.votes.length;
            document.getElementById('commentsTabCount').textContent = activityData.comments.length;
            
            // Render bookmarks
            this.renderBookmarks(bookmarksData.bookmarks);
            
            // Render loves
            this.renderLoves(activityData.loves);
            
            // Render votes
            this.renderVotes(activityData.votes);
            
            // Render comments
            this.renderComments(activityData.comments);
            
        } catch (error) {
            console.error('Error loading activity:', error);
            showNotification('Failed to load activity', 'error');
        }
    }
    
    renderBookmarks(bookmarks) {
        const container = document.getElementById('bookmarksList');
        
        if (bookmarks.length === 0) {
            container.innerHTML = '<div class="empty-state">No bookmarks yet</div>';
            return;
        }
        
        container.innerHTML = bookmarks.map(post => `
            <div class="activity-item">
                <div class="activity-item-header">
                    <a href="${post.url}" target="_blank" class="activity-item-title">
                        ${this.escapeHtml(post.title)}
                    </a>
                </div>
                <div class="activity-item-meta">
                    <span>📅 ${this.formatDate(post.date_published)}</span>
                    ${post.label ? `<span>🏷️ ${post.label}</span>` : ''}
                </div>
            </div>
        `).join('');
    }
    
    renderLoves(loves) {
        const container = document.getElementById('lovesList');
        
        if (loves.length === 0) {
            container.innerHTML = '<div class="empty-state">No loves yet</div>';
            return;
        }
        
        container.innerHTML = loves.map(love => `
            <div class="activity-item">
                <div class="activity-item-header">
                    <a href="${love.url}" target="_blank" class="activity-item-title">
                        ${this.escapeHtml(love.title)}
                    </a>
                </div>
                <div class="activity-item-meta">
                    <span>❤️ ${love.love_votes} Love${love.love_votes !== 1 ? 's' : ''}</span>
                </div>
            </div>
        `).join('');
    }
    
    renderVotes(votes) {
        const container = document.getElementById('votesList');
        
        if (votes.length === 0) {
            container.innerHTML = '<div class="empty-state">No votes yet</div>';
            return;
        }
        
        container.innerHTML = votes.map(vote => `
            <div class="activity-item">
                <div class="activity-item-header">
                    <a href="${vote.url}" target="_blank" class="activity-item-title">
                        ${this.escapeHtml(vote.title)}
                    </a>
                </div>
                <div class="activity-item-meta">
                    <span>🔧 ${vote.needs_update_votes} Needs Update</span>
                    <span>🗑️ ${vote.remove_post_votes} Remove Post</span>
                </div>
            </div>
        `).join('');
    }
    
    renderComments(comments) {
        const container = document.getElementById('commentsList');
        
        if (comments.length === 0) {
            container.innerHTML = '<div class="empty-state">No comments yet</div>';
            return;
        }
        
        container.innerHTML = comments.map(comment => `
            <div class="activity-item">
                <div class="activity-item-header">
                    <div class="activity-item-title">
                        On: ${this.escapeHtml(comment.post_title)}
                    </div>
                    <div class="activity-item-date">
                        ${this.formatDate(comment.timestamp)}
                    </div>
                </div>
                <div class="activity-item-content">
                    ${this.escapeHtml(comment.text)}
                </div>
            </div>
        `).join('');
    }
    
    switchActivityTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.activity-tab').forEach(tab => {
            if (tab.dataset.tab === tabName) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });
        
        // Update tab content
        document.querySelectorAll('.activity-tab-content').forEach(content => {
            if (content.id === `${tabName}Tab`) {
                content.classList.add('active');
            } else {
                content.classList.remove('active');
            }
        });
    }
    
    updateUserMenuName(displayName) {
        const userName = document.getElementById('userName');
        if (userName) {
            userName.textContent = displayName;
        }
        
        // Also update auth manager if available
        if (window.authManager) {
            window.authManager.updateUI();
        }
    }
    
    async deleteAccount() {
        // Confirm deletion
        const confirmed = confirm(
            '⚠️ DELETE ACCOUNT\n\n' +
            'This will permanently delete:\n' +
            '• Your profile information\n' +
            '• All your bookmarks\n' +
            '• All your votes and loves\n' +
            '• All your comments\n\n' +
            'This action CANNOT be undone!\n\n' +
            'Type "DELETE" in the next prompt to confirm.'
        );
        
        if (!confirmed) {
            return;
        }
        
        // Second confirmation
        const confirmation = prompt('Type DELETE (in capital letters) to confirm account deletion:');
        
        if (confirmation !== 'DELETE') {
            showNotification('Account deletion cancelled', 'info');
            return;
        }
        
        try {
            const response = await fetch(`${this.apiEndpoint}/profile`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${window.authManager.getIdToken()}`
                }
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to delete account');
            }
            
            showNotification('Account deleted successfully. Signing you out...', 'success');
            
            // Close modal
            this.closeProfile();
            
            // Sign out after 2 seconds
            setTimeout(() => {
                if (window.authManager) {
                    window.authManager.signOut();
                }
            }, 2000);
            
        } catch (error) {
            console.error('Error deleting account:', error);
            showNotification(error.message || 'Failed to delete account', 'error');
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return 'Unknown';
        }
    }
}

// Initialize profile manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (typeof API_ENDPOINT !== 'undefined') {
        window.profileManager = new ProfileManager(API_ENDPOINT);
        console.log('Profile manager initialized');
    }
});
