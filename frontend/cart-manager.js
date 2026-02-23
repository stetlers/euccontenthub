// Cart Manager Module for EUC Content Hub
// Handles cart state, persistence, and API communication

class CartManager {
    constructor(apiEndpoint) {
        this.apiEndpoint = apiEndpoint;
        this.cart = []; // Array of post_ids
        this.listeners = []; // Event listeners for cart changes
        this.isLoading = false;
        
        // Load cart on initialization
        this.loadCart();
    }
    
    // ============================================
    // State Management
    // ============================================
    
    /**
     * Get current cart contents
     * @returns {Array<string>} Array of post_ids
     */
    getCart() {
        return [...this.cart]; // Return copy to prevent external modification
    }
    
    /**
     * Get number of items in cart
     * @returns {number} Cart item count
     */
    getCartCount() {
        return this.cart.length;
    }
    
    /**
     * Check if post is in cart
     * @param {string} postId - Post ID to check
     * @returns {boolean} True if post is in cart
     */
    isInCart(postId) {
        return this.cart.includes(postId);
    }
    
    /**
     * Add post to cart
     * @param {string} postId - Post ID to add
     * @returns {Promise<boolean>} True if added, false if already in cart
     */
    async addToCart(postId) {
        if (!postId) {
            console.error('addToCart: postId is required');
            return false;
        }
        
        // Check for duplicates
        if (this.isInCart(postId)) {
            console.log('Post already in cart:', postId);
            return false;
        }
        
        // Optimistic update - add to local state immediately
        this.cart.push(postId);
        this.notifyListeners('added', postId);
        
        // Persist to storage
        try {
            if (this.isAuthenticated()) {
                await this.addToCartAPI(postId);
            } else {
                this.saveToLocalStorage();
            }
            return true;
        } catch (error) {
            // Rollback on error
            console.error('Failed to add to cart:', error);
            this.cart = this.cart.filter(id => id !== postId);
            this.notifyListeners('error', postId);
            throw error;
        }
    }
    
    /**
     * Remove post from cart
     * @param {string} postId - Post ID to remove
     * @returns {Promise<boolean>} True if removed, false if not in cart
     */
    async removeFromCart(postId) {
        if (!postId) {
            console.error('removeFromCart: postId is required');
            return false;
        }
        
        // Check if post is in cart
        if (!this.isInCart(postId)) {
            console.log('Post not in cart:', postId);
            return false;
        }
        
        // Optimistic update - remove from local state immediately
        const originalCart = [...this.cart];
        this.cart = this.cart.filter(id => id !== postId);
        this.notifyListeners('removed', postId);
        
        // Persist to storage
        try {
            if (this.isAuthenticated()) {
                await this.removeFromCartAPI(postId);
            } else {
                this.saveToLocalStorage();
            }
            return true;
        } catch (error) {
            // Rollback on error
            console.error('Failed to remove from cart:', error);
            this.cart = originalCart;
            this.notifyListeners('error', postId);
            throw error;
        }
    }
    
    /**
     * Clear all items from cart
     * @returns {Promise<void>}
     */
    async clearCart() {
        // Optimistic update - clear local state immediately
        const originalCart = [...this.cart];
        this.cart = [];
        this.notifyListeners('cleared');
        
        // Persist to storage
        try {
            if (this.isAuthenticated()) {
                await this.clearCartAPI();
            } else {
                this.saveToLocalStorage();
            }
        } catch (error) {
            // Rollback on error
            console.error('Failed to clear cart:', error);
            this.cart = originalCart;
            this.notifyListeners('error');
            throw error;
        }
    }
    
    // ============================================
    // Persistence
    // ============================================
    
    /**
     * Load cart from storage (localStorage or API)
     * @returns {Promise<void>}
     */
    async loadCart() {
        if (this.isLoading) {
            return;
        }
        
        this.isLoading = true;
        
        try {
            if (this.isAuthenticated()) {
                // Load from API for authenticated users
                await this.loadFromAPI();
            } else {
                // Load from localStorage for anonymous users
                this.loadFromLocalStorage();
            }
        } catch (error) {
            console.error('Failed to load cart:', error);
            // Fall back to empty cart on error
            this.cart = [];
        } finally {
            this.isLoading = false;
            this.notifyListeners('loaded');
        }
    }
    
    /**
     * Save cart to storage (localStorage or API)
     * @returns {Promise<void>}
     */
    async saveCart() {
        if (this.isAuthenticated()) {
            // Save to API for authenticated users
            await this.saveToAPI();
        } else {
            // Save to localStorage for anonymous users
            this.saveToLocalStorage();
        }
    }
    
    /**
     * Load cart from localStorage
     */
    loadFromLocalStorage() {
        try {
            const stored = localStorage.getItem('euc_cart');
            if (stored) {
                const data = JSON.parse(stored);
                this.cart = Array.isArray(data.cart) ? data.cart : [];
                console.log('Loaded cart from localStorage:', this.cart.length, 'items');
            } else {
                this.cart = [];
            }
        } catch (error) {
            console.error('Failed to load from localStorage:', error);
            this.cart = [];
        }
    }
    
    /**
     * Save cart to localStorage
     */
    saveToLocalStorage() {
        try {
            const data = {
                cart: this.cart,
                timestamp: new Date().toISOString()
            };
            localStorage.setItem('euc_cart', JSON.stringify(data));
            console.log('Saved cart to localStorage:', this.cart.length, 'items');
        } catch (error) {
            console.error('Failed to save to localStorage:', error);
            throw error;
        }
    }
    
    /**
     * Load cart from API
     * @returns {Promise<void>}
     */
    async loadFromAPI() {
        try {
            const response = await fetch(`${this.apiEndpoint}/cart`, {
                headers: {
                    'Authorization': `Bearer ${this.getIdToken()}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            const data = await response.json();
            this.cart = Array.isArray(data.cart) ? data.cart : [];
            console.log('Loaded cart from API:', this.cart.length, 'items');
        } catch (error) {
            console.error('Failed to load from API:', error);
            throw error;
        }
    }
    
    /**
     * Save cart to API (for authenticated users)
     * Note: API endpoints handle individual operations (add/remove/clear)
     * This method is called after optimistic updates
     * @returns {Promise<void>}
     */
    async saveToAPI() {
        // API persistence happens through individual operations
        // (addToCart, removeFromCart, clearCart make their own API calls)
        // This method is here for consistency but doesn't need to do anything
        // since we use optimistic updates with individual API calls
        console.log('Cart synced with API');
    }
    
    /**
     * Merge localStorage cart with API cart on sign-in
     * @returns {Promise<void>}
     */
    async mergeCartsOnSignIn() {
        console.log('Merging carts on sign-in...');
        
        try {
            // Get localStorage cart
            const localCart = [];
            try {
                const stored = localStorage.getItem('euc_cart');
                if (stored) {
                    const data = JSON.parse(stored);
                    localCart.push(...(Array.isArray(data.cart) ? data.cart : []));
                }
            } catch (error) {
                console.error('Failed to read localStorage cart:', error);
            }
            
            // Get API cart
            await this.loadFromAPI();
            const apiCart = [...this.cart];
            
            // Merge carts (remove duplicates)
            const mergedCart = [...new Set([...apiCart, ...localCart])];
            
            console.log(`Merging: ${localCart.length} local + ${apiCart.length} API = ${mergedCart.length} total`);
            
            // Add local items to API cart
            for (const postId of localCart) {
                if (!apiCart.includes(postId)) {
                    try {
                        await this.addToCartAPI(postId);
                    } catch (error) {
                        console.error('Failed to add item during merge:', postId, error);
                    }
                }
            }
            
            // Reload from API to get final state
            await this.loadFromAPI();
            
            // Clear localStorage cart
            localStorage.removeItem('euc_cart');
            console.log('Cart merge complete, localStorage cleared');
            
            this.notifyListeners('merged');
            
        } catch (error) {
            console.error('Failed to merge carts:', error);
            // Preserve localStorage cart on failure
            throw error;
        }
    }
    
    /**
     * Add post to cart via API
     * @param {string} postId - Post ID to add
     * @returns {Promise<void>}
     */
    async addToCartAPI(postId) {
        const response = await fetch(`${this.apiEndpoint}/cart`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.getIdToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ post_id: postId })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to add to cart');
        }
        
        return response.json();
    }
    
    /**
     * Remove post from cart via API
     * @param {string} postId - Post ID to remove
     * @returns {Promise<void>}
     */
    async removeFromCartAPI(postId) {
        const response = await fetch(`${this.apiEndpoint}/cart/${postId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${this.getIdToken()}`
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to remove from cart');
        }
        
        return response.json();
    }
    
    /**
     * Clear cart via API
     * @returns {Promise<void>}
     */
    async clearCartAPI() {
        const response = await fetch(`${this.apiEndpoint}/cart`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${this.getIdToken()}`
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to clear cart');
        }
        
        return response.json();
    }
    
    // ============================================
    // Validation
    // ============================================
    
    /**
     * Validate post ID exists in posts array
     * @param {string} postId - Post ID to validate
     * @param {Array} allPosts - Array of all posts
     * @returns {boolean} True if post exists
     */
    validatePostId(postId, allPosts) {
        if (!allPosts || !Array.isArray(allPosts)) {
            return false;
        }
        return allPosts.some(post => post.post_id === postId);
    }
    
    /**
     * Remove invalid post IDs from cart
     * @param {Array} allPosts - Array of all posts
     * @returns {number} Number of invalid posts removed
     */
    cleanInvalidPosts(allPosts) {
        const originalLength = this.cart.length;
        this.cart = this.cart.filter(postId => this.validatePostId(postId, allPosts));
        const removedCount = originalLength - this.cart.length;
        
        if (removedCount > 0) {
            console.log(`Removed ${removedCount} invalid posts from cart`);
            this.saveCart(); // Persist cleaned cart
            this.notifyListeners('cleaned', removedCount);
        }
        
        return removedCount;
    }
    
    // ============================================
    // Event System
    // ============================================
    
    /**
     * Add event listener for cart changes
     * @param {Function} callback - Callback function (event, data)
     */
    addListener(callback) {
        if (typeof callback === 'function') {
            this.listeners.push(callback);
        }
    }
    
    /**
     * Remove event listener
     * @param {Function} callback - Callback function to remove
     */
    removeListener(callback) {
        this.listeners = this.listeners.filter(cb => cb !== callback);
    }
    
    /**
     * Notify all listeners of cart change
     * @param {string} event - Event type (added, removed, cleared, loaded, merged, cleaned, error)
     * @param {*} data - Event data
     */
    notifyListeners(event, data) {
        this.listeners.forEach(callback => {
            try {
                callback(event, data);
            } catch (error) {
                console.error('Error in cart listener:', error);
            }
        });
    }
    
    // ============================================
    // Authentication Helpers
    // ============================================
    
    /**
     * Check if user is authenticated
     * @returns {boolean} True if authenticated
     */
    isAuthenticated() {
        return window.authManager && window.authManager.isAuthenticated();
    }
    
    /**
     * Get ID token for API requests
     * @returns {string|null} ID token or null
     */
    getIdToken() {
        if (window.authManager && window.authManager.isAuthenticated()) {
            return window.authManager.getIdToken();
        }
        return null;
    }
}

// Export for use in other modules
window.CartManager = CartManager;
