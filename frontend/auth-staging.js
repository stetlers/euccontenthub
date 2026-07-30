// Authentication Module for Amazon WorkSpaces Community Hub - STAGING
// Handles Cognito OAuth flow and user session management

const AUTH_CONFIG = {
    userPoolId: 'us-east-1_MOvNrTnua',
    // STAGING uses a dedicated Cognito app client wired to Amazon Federate
    // (employee SSO) so we can match the internal demo-portal login WITHOUT
    // touching the shared production client (3pv5jf235vj14gu148b9vjt3od), which
    // stays on Google. Production auth.js is unaffected.
    clientId: '7v0tr8fb006f2n0dfia47e3jk',
    domain: 'euc-content-hub.auth.us-east-1.amazoncognito.com',
    redirectUri: 'https://staging.awseuccontent.com/callback',  // STAGING URL
    region: 'us-east-1',
    // Name of the Amazon Federate OIDC provider on the Cognito app client.
    // Deep-links the sign-in button straight to Federate (one-click employee
    // login, no Hosted-UI provider chooser). Empty = fall back to the chooser.
    idpName: 'FederateOIDCInteg'
};

class AuthManager {
    constructor() {
        this.user = null;
        this.tokens = null;
        this.init();
    }
    
    init() {
        // Check if we're on the callback page
        if (window.location.pathname === '/callback') {
            this.handleCallback();
            return;
        }
        
        // Load existing session
        this.loadSession();
        
        // Update UI based on auth state
        this.updateUI();
    }
    
    // Get login URL
    getLoginUrl() {
        const params = new URLSearchParams({
            client_id: AUTH_CONFIG.clientId,
            response_type: 'code',
            scope: 'email openid profile',
            redirect_uri: AUTH_CONFIG.redirectUri
        });

        // If a specific IdP is configured, deep-link straight to it via the
        // /oauth2/authorize endpoint so users skip the Hosted-UI provider
        // chooser and land on the Federate (employee SSO) login directly.
        if (AUTH_CONFIG.idpName) {
            params.set('identity_provider', AUTH_CONFIG.idpName);
            return `https://${AUTH_CONFIG.domain}/oauth2/authorize?${params.toString()}`;
        }

        return `https://${AUTH_CONFIG.domain}/login?${params.toString()}`;
    }
    
    // Get logout URL
    getLogoutUrl() {
        const params = new URLSearchParams({
            client_id: AUTH_CONFIG.clientId,
            logout_uri: window.location.origin
        });
        
        return `https://${AUTH_CONFIG.domain}/logout?${params.toString()}`;
    }
    
    // Handle OAuth callback
    async handleCallback() {
        const params = new URLSearchParams(window.location.search);
        const code = params.get('code');
        const error = params.get('error');
        
        if (error) {
            console.error('Auth error:', error);
            alert('Authentication failed: ' + error);
            window.location.href = '/';
            return;
        }
        
        if (!code) {
            console.error('No authorization code received');
            window.location.href = '/';
            return;
        }
        
        // Show loading
        document.body.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100vh; font-family: Arial;">
                <div style="text-align: center;">
                    <div style="font-size: 48px; margin-bottom: 20px;">🔐</div>
                    <h2>Completing sign-in...</h2>
                    <p>Please wait while we set up your account.</p>
                </div>
            </div>
        `;
        
        try {
            // Exchange code for tokens
            const tokens = await this.exchangeCodeForTokens(code);
            
            // Get user info from ID token
            const userInfo = this.parseJWT(tokens.id_token);
            
            // Save session
            this.saveSession(tokens, userInfo);
            
            // Trigger cart merge if CartManager is available
            if (window.cartManager && typeof window.cartManager.mergeCartsOnSignIn === 'function') {
                try {
                    await window.cartManager.mergeCartsOnSignIn();
                    console.log('Cart merge completed successfully');
                } catch (error) {
                    console.error('Cart merge failed:', error);
                    // Don't block sign-in if cart merge fails
                }
            }
            
            // Redirect to home
            window.location.href = '/';
            
        } catch (error) {
            console.error('Token exchange failed:', error);
            alert('Failed to complete sign-in. Please try again.');
            window.location.href = '/';
        }
    }
    
    // Exchange authorization code for tokens
    async exchangeCodeForTokens(code) {
        const params = new URLSearchParams({
            grant_type: 'authorization_code',
            client_id: AUTH_CONFIG.clientId,
            code: code,
            redirect_uri: AUTH_CONFIG.redirectUri
        });
        
        const response = await fetch(`https://${AUTH_CONFIG.domain}/oauth2/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: params.toString()
        });
        
        if (!response.ok) {
            throw new Error('Token exchange failed');
        }
        
        return await response.json();
    }
    
    // Parse JWT token
    parseJWT(token) {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(c => {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        
        return JSON.parse(jsonPayload);
    }
    
    // Save session to localStorage
    saveSession(tokens, userInfo) {
        this.tokens = tokens;
        this.user = {
            sub: userInfo.sub,
            email: userInfo.email,
            email_verified: userInfo.email_verified,
            name: userInfo.name || userInfo.email.split('@')[0]
        };
        
        localStorage.setItem('auth_tokens', JSON.stringify(tokens));
        localStorage.setItem('auth_user', JSON.stringify(this.user));
        localStorage.setItem('auth_expires', Date.now() + (tokens.expires_in * 1000));
    }
    
    // Load session from localStorage
    loadSession() {
        try {
            const tokensStr = localStorage.getItem('auth_tokens');
            const userStr = localStorage.getItem('auth_user');
            const expires = localStorage.getItem('auth_expires');
            
            if (!tokensStr || !userStr || !expires) {
                return false;
            }
            
            // Check if expired
            if (Date.now() > parseInt(expires)) {
                this.clearSession();
                return false;
            }
            
            this.tokens = JSON.parse(tokensStr);
            this.user = JSON.parse(userStr);
            
            return true;
        } catch (error) {
            console.error('Failed to load session:', error);
            this.clearSession();
            return false;
        }
    }
    
    // Clear session
    clearSession() {
        this.tokens = null;
        this.user = null;
        localStorage.removeItem('auth_tokens');
        localStorage.removeItem('auth_user');
        localStorage.removeItem('auth_expires');
    }
    
    // Check if user is authenticated
    isAuthenticated() {
        return this.user !== null && this.tokens !== null;
    }
    
    // Get current user
    getUser() {
        return this.user;
    }
    
    // Get access token
    getAccessToken() {
        return this.tokens ? this.tokens.access_token : null;
    }
    
    // Get ID token
    getIdToken() {
        return this.tokens ? this.tokens.id_token : null;
    }
    
    // Sign in
    signIn() {
        window.location.href = this.getLoginUrl();
    }
    
    // Sign out
    signOut() {
        this.clearSession();
        window.location.href = this.getLogoutUrl();
    }
    
    // Update UI based on auth state
    updateUI() {
        const authContainer = document.getElementById('authContainer');
        if (!authContainer) return;
        
        if (this.isAuthenticated()) {
            // Fetch display name from profile
            this.fetchDisplayName().then(displayName => {
                // Show user profile with display name
                authContainer.innerHTML = `
                    <div class="user-profile">
                        <button class="user-menu-btn" id="userMenuBtn">
                            <span class="user-avatar">👤</span>
                            <span class="user-name" id="userName">${this.escapeHtml(displayName)}</span>
                            <span class="user-dropdown">▼</span>
                        </button>
                        <div class="user-menu" id="userMenu" style="display: none;">
                            <div class="user-menu-header">
                                <div class="user-menu-email">${this.escapeHtml(this.user.email)}</div>
                            </div>
                            <button class="user-menu-item" id="profileBtn">
                                <span>👤</span> My Profile
                            </button>
                            <button class="user-menu-item" id="kbEditorBtn">
                                <span>📚</span> Edit Knowledge Base
                            </button>
                            <button class="user-menu-item" id="tourBtn">
                                <span>🗺️</span> Take the Tour
                            </button>
                            <button class="user-menu-item" id="signOutBtn">
                                <span>🚪</span> Sign Out
                            </button>
                        </div>
                    </div>
                `;
                
                // Add event listeners
                document.getElementById('userMenuBtn').addEventListener('click', () => {
                    const menu = document.getElementById('userMenu');
                    menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
                });
                
                document.getElementById('signOutBtn').addEventListener('click', () => {
                    this.signOut();
                });
                
                // Profile button click handler
                document.getElementById('profileBtn').addEventListener('click', () => {
                    if (window.profileManager) {
                        window.profileManager.openProfile();
                    }
                });
                
                // KB Editor button click handler
                document.getElementById('kbEditorBtn').addEventListener('click', () => {
                    if (window.kbEditor) {
                        window.kbEditor.showEditor();
                    } else {
                        console.error('KB Editor not initialized');
                    }
                });
                
                // Tour button click handler
                document.getElementById('tourBtn').addEventListener('click', () => {
                    if (window.interactiveTour) {
                        window.interactiveTour.open();
                    }
                    const menu = document.getElementById('userMenu');
                    if (menu) menu.style.display = 'none';
                });
                
                // Close menu when clicking outside
                document.addEventListener('click', (e) => {
                    const menu = document.getElementById('userMenu');
                    const btn = document.getElementById('userMenuBtn');
                    if (menu && btn && !menu.contains(e.target) && !btn.contains(e.target)) {
                        menu.style.display = 'none';
                    }
                });
            });

            // Signed in: tear down the welcome gate so the hub is visible.
            this.removeWelcomeGate();

        } else {
            // Show sign in button
            authContainer.innerHTML = `
                <button class="btn-sign-in" id="signInBtn">
                    <span>🔐</span> Sign In
                </button>
            `;

            document.getElementById('signInBtn').addEventListener('click', () => {
                this.signIn();
            });

            // Signed out: gate the hub behind a full-screen welcome page.
            this.renderWelcomeGate();
        }
        
        // Trigger app-level auth UI updates
        if (window.updateAuthUI) {
            window.updateAuthUI();
        }
    }
    
    // Render the full-screen welcome gate shown to signed-out visitors.
    // Blocks access to the hub until the user authenticates (matches the
    // internal demo-portal experience). Idempotent — safe to call repeatedly.
    renderWelcomeGate() {
        if (document.getElementById('welcomeGate')) return;

        const gate = document.createElement('div');
        gate.id = 'welcomeGate';
        gate.className = 'welcome-gate';
        gate.innerHTML = `
            <div class="welcome-gate-card">
                <img src="portal_logo.png?v=20260729" alt="" class="welcome-gate-logo" aria-hidden="true">
                <h1 class="welcome-gate-title">Amazon WorkSpaces Community Hub</h1>
                <p class="welcome-gate-subtitle">
                    Your hub for End User Computing content, discussions, and community knowledge.
                    Sign in to continue.
                </p>
                <div class="welcome-gate-options">
                    <button class="welcome-gate-btn welcome-gate-btn-primary" id="gateInternalBtn">
                        <span class="welcome-gate-btn-icon">🛡️</span>
                        <span class="welcome-gate-btn-text">
                            <span class="welcome-gate-btn-label">Amazon Employee</span>
                            <span class="welcome-gate-btn-desc">Sign in with Midway (internal)</span>
                        </span>
                    </button>
                    <button class="welcome-gate-btn welcome-gate-btn-secondary" id="gatePartnerBtn" disabled>
                        <span class="welcome-gate-btn-icon">🤝</span>
                        <span class="welcome-gate-btn-text">
                            <span class="welcome-gate-btn-label">Partner</span>
                            <span class="welcome-gate-btn-desc">Coming soon</span>
                        </span>
                        <span class="welcome-gate-badge">Soon</span>
                    </button>
                </div>
            </div>
            <div class="welcome-gate-footer">Amazon WorkSpaces Community Hub — Staging</div>
        `;

        document.body.appendChild(gate);
        document.body.classList.add('welcome-gate-active');

        document.getElementById('gateInternalBtn').addEventListener('click', () => {
            this.signIn();
        });
    }

    // Remove the welcome gate (called once the user is authenticated).
    removeWelcomeGate() {
        const gate = document.getElementById('welcomeGate');
        if (gate) gate.remove();
        document.body.classList.remove('welcome-gate-active');
    }

    async fetchDisplayName() {
        try {
            // Get API endpoint (defined in app.js or use window global)
            const apiEndpoint = window.API_ENDPOINT || (typeof API_ENDPOINT !== 'undefined' ? API_ENDPOINT : 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging');
            
            console.log('Fetching display name from:', apiEndpoint);
            
            const response = await fetch(`${apiEndpoint}/profile`, {
                headers: {
                    'Authorization': `Bearer ${this.getIdToken()}`
                }
            });
            
            console.log('Profile fetch response:', response.status);
            
            if (response.ok) {
                const data = await response.json();
                console.log('Profile data:', data);
                const displayName = data.profile.display_name || this.user.name;
                console.log('Using display name:', displayName);
                return displayName;
            }
        } catch (error) {
            console.log('Could not fetch display name, using default:', error);
        }
        
        // Fallback to user name from token
        console.log('Falling back to token name:', this.user.name);
        return this.user.name;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize auth manager
window.authManager = new AuthManager();
