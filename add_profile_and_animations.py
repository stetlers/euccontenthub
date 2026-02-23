#!/usr/bin/env python3
"""Add profile modal styles and click animations"""

additional_styles = """

/* ============================================
   PROFILE MODAL - Match Refined Theme
   ============================================ */
.profile-form {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.form-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.form-group label {
    font-weight: 600;
    color: var(--primary-color);
    font-size: 0.9375rem;
}

.form-input,
.form-textarea {
    padding: 12px 16px;
    border: 2px solid var(--border-color);
    border-radius: 8px;
    font-size: 1rem;
    font-family: inherit;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.form-input:focus,
.form-textarea:focus {
    outline: none;
    border-color: var(--secondary-color);
    box-shadow: 0 0 0 3px rgba(255, 153, 0, 0.1);
    transform: translateY(-2px);
}

.form-textarea {
    resize: vertical;
    min-height: 100px;
}

.form-help {
    font-size: 0.8125rem;
    color: #666;
}

.profile-stats {
    background: var(--bg-hover);
    padding: 20px;
    border-radius: 12px;
    margin-top: 10px;
    border: 2px solid var(--border-color);
}

.profile-stats h3 {
    margin: 0 0 15px 0;
    font-size: 1rem;
    color: var(--primary-color);
    font-weight: 700;
}

/* Profile Modal Buttons */
.modal-footer {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
    padding: 20px 24px;
    border-top: 2px solid var(--border-color);
}

.btn-save-profile,
.btn-cancel {
    padding: 12px 28px;
    font-size: 1rem;
    font-weight: 700;
    border: 2px solid transparent;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.btn-save-profile {
    background: linear-gradient(135deg, var(--secondary-color) 0%, #ec8b00 100%);
    color: white;
    box-shadow: 0 4px 12px rgba(255, 153, 0, 0.3);
}

.btn-save-profile:hover {
    transform: translateY(-3px) scale(1.05);
    box-shadow: 0 6px 20px rgba(255, 153, 0, 0.5);
}

.btn-save-profile:active {
    transform: translateY(-1px) scale(0.98);
}

.btn-cancel {
    background: white;
    color: var(--text-color);
    border-color: var(--border-color);
}

.btn-cancel:hover {
    background: var(--bg-hover);
    border-color: var(--secondary-color);
    transform: translateY(-2px);
}

.btn-cancel:active {
    transform: translateY(0) scale(0.98);
}

/* ============================================
   CLICK ANIMATIONS - Love & Vote Buttons
   ============================================ */

/* Love button click animation */
.love-btn:not(.disabled):active {
    animation: lovePop 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes lovePop {
    0% { transform: scale(1); }
    50% { transform: scale(0.9); }
    100% { transform: scale(1.05); }
}

/* When loved, trigger heartbeat */
.love-btn.loved {
    animation: heartBeat 0.6s ease-in-out;
}

/* Vote button click animation */
.vote-btn:not(.disabled):active {
    animation: votePop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes votePop {
    0% { transform: scale(1); }
    50% { transform: scale(0.92); }
    100% { transform: scale(1); }
}

/* Vote count animation when incrementing */
.vote-count.incrementing {
    animation: countBounce 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes countBounce {
    0% { transform: scale(1); }
    25% { transform: scale(1.4) translateY(-5px); background: #4CAF50; }
    50% { transform: scale(1.2) translateY(-2px); }
    75% { transform: scale(1.3) translateY(-3px); }
    100% { transform: scale(1); }
}

/* Love count animation */
.love-count.incrementing {
    animation: loveCountPop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes loveCountPop {
    0% { transform: scale(1); }
    25% { transform: scale(1.5) rotate(-10deg); }
    50% { transform: scale(1.2) rotate(5deg); }
    75% { transform: scale(1.4) rotate(-5deg); }
    100% { transform: scale(1) rotate(0deg); }
}

/* Ripple effect on button click */
.vote-btn .ripple,
.love-btn .ripple {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.6);
    transform: scale(0);
    animation: ripple 0.6s ease-out;
    pointer-events: none;
}

@keyframes ripple {
    to {
        transform: scale(4);
        opacity: 0;
    }
}

/* Amazon Email Verification Styles */
.verification-section {
    background: var(--bg-hover);
    padding: 20px;
    border-radius: 12px;
    margin-top: 20px;
    border: 2px solid var(--border-color);
}

.verification-section h3 {
    margin: 0 0 10px 0;
    font-size: 1rem;
    color: var(--primary-color);
    font-weight: 700;
}

.verification-description {
    font-size: 0.9375rem;
    color: #666;
    margin-bottom: 15px;
    line-height: 1.6;
}

.verification-status {
    margin-bottom: 15px;
}

.verification-badge {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px;
    border-radius: 10px;
    border-left: 4px solid;
    transition: all 0.3s;
}

.verification-badge.verified {
    background: linear-gradient(135deg, #e8f5e9 0%, #f1f8f4 100%);
    border-left-color: #4caf50;
}

.verification-badge.expired {
    background: linear-gradient(135deg, #fff3e0 0%, #fff8f0 100%);
    border-left-color: #ff9800;
}

.verification-badge.unverified {
    background: linear-gradient(135deg, #e3f2fd 0%, #f0f7fc 100%);
    border-left-color: #2196f3;
}

.verification-badge.revoked {
    background: linear-gradient(135deg, #ffebee 0%, #fff5f5 100%);
    border-left-color: #f44336;
}

.badge-icon {
    font-size: 1.5rem;
    line-height: 1;
}

.badge-content {
    flex: 1;
}

.badge-title {
    font-weight: 700;
    font-size: 0.9375rem;
    margin-bottom: 4px;
    color: var(--primary-color);
}

.badge-subtitle {
    font-size: 0.8125rem;
    color: #666;
    line-height: 1.4;
}

.verification-form {
    margin-top: 15px;
}

.verification-form .form-group {
    margin-bottom: 15px;
}

.verification-form .btn-primary {
    width: 100%;
    padding: 12px 24px;
    font-size: 1rem;
    font-weight: 700;
    border: 2px solid transparent;
    border-radius: 10px;
    background: linear-gradient(135deg, #2196f3 0%, #1976d2 100%);
    color: white;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    box-shadow: 0 4px 12px rgba(33, 150, 243, 0.3);
}

.verification-form .btn-primary:hover {
    transform: translateY(-3px) scale(1.02);
    box-shadow: 0 6px 20px rgba(33, 150, 243, 0.5);
}

.verification-form .btn-primary:active {
    transform: translateY(-1px) scale(0.98);
}

.verification-form .btn-primary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
}
"""

# Read existing CSS
with open('frontend/styles-refined.css', 'r', encoding='utf-8') as f:
    existing_css = f.read()

# Append new styles
complete_css = existing_css + additional_styles

# Write complete CSS
with open('frontend/styles-refined.css', 'w', encoding='utf-8') as f:
    f.write(complete_css)

print("✅ Added profile modal styles and click animations")
print("\nAdded:")
print("  ✅ Profile form styling (matches refined theme)")
print("  ✅ Profile modal buttons (Save/Cancel)")
print("  ✅ Love button click animation (lovePop)")
print("  ✅ Vote button click animation (votePop)")
print("  ✅ Count increment animations (bounce effect)")
print("  ✅ Ripple effect on clicks")
print("  ✅ Email verification section styling")
