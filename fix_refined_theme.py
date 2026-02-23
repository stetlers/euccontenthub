#!/usr/bin/env python3
"""Add missing critical styles to refined theme"""

# Critical styles that are missing
missing_styles = """

/* ============================================
   MODAL STYLES - CRITICAL FOR PROFILE & LEGAL PAGES
   ============================================ */
.modal {
    display: none;
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    animation: fadeIn 0.3s ease-out;
}

.modal.show {
    display: flex;
    align-items: center;
    justify-content: center;
}

.modal-content {
    background: white;
    border-radius: 12px;
    width: 90%;
    max-width: 700px;
    max-height: 85vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
    from {
        transform: translateY(50px);
        opacity: 0;
    }
    to {
        transform: translateY(0);
        opacity: 1;
    }
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 24px;
    border-bottom: 2px solid var(--border-color);
}

.modal-header h2 {
    margin: 0;
    font-size: 1.5rem;
    color: var(--primary-color);
}

.modal-close {
    background: none;
    border: none;
    font-size: 2rem;
    color: #999;
    cursor: pointer;
    padding: 0;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: all 0.3s;
}

.modal-close:hover {
    background: #f0f0f0;
    color: #333;
}

.modal-body {
    padding: 24px;
    overflow-y: auto;
    flex: 1;
}

.modal-post-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--primary-color);
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-color);
}

/* Comment Form Footer */
.comment-form-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 12px;
}

.char-count {
    font-size: 0.85rem;
    color: #999;
}

.btn-submit-comment {
    padding: 10px 24px;
    background: var(--secondary-color);
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
}

.btn-submit-comment:hover:not(:disabled) {
    background: #ec8b00;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(255, 153, 0, 0.3);
}

.btn-submit-comment:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

/* ============================================
   LOVE BUTTON - CRITICAL FIX
   ============================================ */
.love-section {
    display: flex;
    justify-content: center;
    margin-bottom: 12px;
}

.love-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px 28px;
    border: 2px solid var(--border-color);
    border-radius: 24px;
    background: white;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    font-size: 1rem;
    font-weight: 600;
}

.love-btn:not(.disabled):hover {
    transform: translateY(-3px) scale(1.05);
    box-shadow: 0 6px 16px rgba(233, 30, 99, 0.4);
    border-color: #E91E63;
    background: #FCE4EC;
}

.love-btn.loved {
    border-color: #E91E63;
    background: linear-gradient(135deg, #FCE4EC 0%, #ffffff 100%);
}

.love-btn.disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.love-icon {
    font-size: 1.5rem;
    transition: transform 0.3s;
}

.love-btn:not(.disabled):hover .love-icon {
    transform: scale(1.2);
}

.love-btn.loved .love-icon {
    animation: heartBeat 0.6s ease-in-out;
}

.love-count {
    font-weight: 700;
    color: #E91E63;
    min-width: 24px;
    text-align: center;
    font-size: 1.125rem;
}

.loved-message {
    text-align: center;
    font-size: 0.85rem;
    color: #E91E63;
    font-weight: 600;
    margin-top: 8px;
}

/* ============================================
   CRAWL BUTTON - Match Reload Data Style
   ============================================ */
.btn-crawl {
    padding: 14px 28px;
    font-size: 1rem;
    font-weight: 700;
    border: 2px solid transparent;
    border-radius: 10px;
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    display: flex;
    align-items: center;
    gap: 10px;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.btn-crawl:hover {
    transform: translateY(-4px) scale(1.05);
    box-shadow: 0 8px 24px rgba(16, 185, 129, 0.5);
    background: linear-gradient(135deg, #059669 0%, #047857 100%);
}

.btn-crawl:active {
    transform: translateY(-1px) scale(0.98);
}

.btn-crawl.crawling {
    opacity: 0.7;
    cursor: wait;
}

.crawl-icon {
    font-size: 1.25rem;
}

.btn-crawl.crawling .crawl-icon {
    animation: spin 2s linear infinite;
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

/* ============================================
   VOTE BUTTONS - Proper Styling
   ============================================ */
.vote-buttons {
    display: flex;
    gap: 10px;
    margin-bottom: 8px;
}

.vote-btn {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding: 12px 8px;
    border: 2px solid var(--border-color);
    border-radius: 6px;
    background: white;
    cursor: pointer;
    transition: all 0.3s;
    font-size: 0.85rem;
    position: relative;
    overflow: hidden;
}

.vote-btn:not(.disabled):hover {
    transform: translateY(-2px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.vote-btn.needs-update:not(.disabled):hover {
    border-color: #2196F3;
    background: #E3F2FD;
}

.vote-btn.remove-post:not(.disabled):hover {
    border-color: #f44336;
    background: #FFEBEE;
}

.vote-btn.disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.vote-btn:not(.disabled):active {
    transform: scale(0.95);
}

.vote-btn.voting {
    animation: pulse 0.6s ease-in-out;
}

@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
}

.vote-icon {
    font-size: 1.5rem;
}

.vote-label {
    font-weight: 600;
    color: var(--text-color);
}

.vote-count {
    display: inline-block;
    background: var(--secondary-color);
    color: white;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 700;
    min-width: 24px;
    transition: all 0.3s;
}

.vote-count.incrementing {
    animation: countPop 0.5s ease-out;
}

@keyframes countPop {
    0% { transform: scale(1); }
    50% { transform: scale(1.5); background: #4CAF50; }
    100% { transform: scale(1); }
}

.voted-message {
    text-align: center;
    font-size: 0.85rem;
    color: #4CAF50;
    font-weight: 600;
}

/* ============================================
   RESPONSIVE - Modal
   ============================================ */
@media (max-width: 768px) {
    .modal-content {
        width: 95%;
        max-height: 90vh;
    }
    
    .modal-header {
        padding: 16px;
    }
    
    .modal-body {
        padding: 16px;
    }
    
    .comment-form-footer {
        flex-direction: column;
        gap: 12px;
        align-items: stretch;
    }
    
    .btn-submit-comment {
        width: 100%;
    }
}
"""

# Read existing refined CSS
with open('frontend/styles-refined.css', 'r', encoding='utf-8') as f:
    existing_css = f.read()

# Append missing styles
complete_css = existing_css + missing_styles

# Write complete CSS
with open('frontend/styles-refined.css', 'w', encoding='utf-8') as f:
    f.write(complete_css)

print("✅ Added missing critical styles to frontend/styles-refined.css")
print("\nAdded:")
print("  ✅ Modal styles (profile, legal pages)")
print("  ✅ Comment form footer")
print("  ✅ Love button (larger, animated)")
print("  ✅ Crawl button (matches Reload Data style)")
print("  ✅ Vote buttons (proper styling)")
print("  ✅ Responsive modal styles")
