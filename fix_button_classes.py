#!/usr/bin/env python3
"""Fix btn-primary and btn-danger classes to match refined theme"""

button_fixes = """

/* ============================================
   BUTTON CLASSES - Primary & Danger (OVERRIDE)
   ============================================ */

/* Primary Button - Save Profile */
.btn-primary {
    padding: 12px 28px !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    border: 2px solid transparent !important;
    border-radius: 10px !important;
    background: linear-gradient(135deg, var(--secondary-color) 0%, #ec8b00 100%) !important;
    color: white !important;
    cursor: pointer !important;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    box-shadow: 0 4px 12px rgba(255, 153, 0, 0.3) !important;
}

.btn-primary:hover:not(:disabled) {
    background: linear-gradient(135deg, #ec8b00 0%, #d67d00 100%) !important;
    transform: translateY(-3px) scale(1.05) !important;
    box-shadow: 0 6px 20px rgba(255, 153, 0, 0.5) !important;
}

.btn-primary:active {
    transform: translateY(-1px) scale(0.98) !important;
}

.btn-primary:disabled {
    opacity: 0.6 !important;
    cursor: not-allowed !important;
    transform: none !important;
}

/* Danger Button - Delete Account */
.btn-danger {
    padding: 12px 28px !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    border: 2px solid #f44336 !important;
    border-radius: 10px !important;
    background: white !important;
    color: #f44336 !important;
    cursor: pointer !important;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
}

.btn-danger:hover {
    background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%) !important;
    color: white !important;
    transform: translateY(-3px) scale(1.05) !important;
    box-shadow: 0 6px 20px rgba(244, 67, 54, 0.5) !important;
}

.btn-danger:active {
    transform: translateY(-1px) scale(0.98) !important;
}

/* Form Actions Container */
.form-actions {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
    margin-top: 24px;
    padding-top: 20px;
    border-top: 2px solid var(--border-color);
}

/* Activity Stats in Profile */
.profile-stats {
    background: var(--bg-hover) !important;
    padding: 20px !important;
    border-radius: 12px !important;
    margin-top: 10px !important;
    border: 2px solid var(--border-color) !important;
}

.profile-stats h3 {
    margin: 0 0 15px 0 !important;
    font-size: 1rem !important;
    color: var(--primary-color) !important;
    font-weight: 700 !important;
}

.profile-stats ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

.profile-stats li {
    padding: 10px 0;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.9375rem;
}

.profile-stats li:last-child {
    border-bottom: none;
}

.profile-stats .stat-label {
    font-weight: 600;
    color: var(--text-color);
}

.profile-stats .stat-value {
    font-weight: 700;
    color: var(--secondary-color);
    background: rgba(255, 153, 0, 0.1);
    padding: 4px 12px;
    border-radius: 12px;
}

/* View Activity Button */
.btn-view-activity,
button[onclick*="showActivity"] {
    padding: 12px 24px !important;
    font-size: 0.9375rem !important;
    font-weight: 700 !important;
    border: 2px solid var(--secondary-color) !important;
    border-radius: 10px !important;
    background: white !important;
    color: var(--secondary-color) !important;
    cursor: pointer !important;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 8px !important;
    margin-top: 16px !important;
}

.btn-view-activity:hover,
button[onclick*="showActivity"]:hover {
    background: linear-gradient(135deg, var(--secondary-color) 0%, #ec8b00 100%) !important;
    color: white !important;
    transform: translateY(-3px) scale(1.05) !important;
    box-shadow: 0 6px 16px rgba(255, 153, 0, 0.4) !important;
}

.btn-view-activity:active,
button[onclick*="showActivity"]:active {
    transform: translateY(-1px) scale(0.98) !important;
}

/* Back to Profile Button */
button[onclick*="showProfileForm"] {
    padding: 10px 20px !important;
    font-size: 0.9375rem !important;
    font-weight: 600 !important;
    border: 2px solid var(--border-color) !important;
    border-radius: 8px !important;
    background: white !important;
    color: var(--text-color) !important;
    cursor: pointer !important;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 8px !important;
    margin-bottom: 20px !important;
}

button[onclick*="showProfileForm"]:hover {
    background: var(--bg-hover) !important;
    border-color: var(--secondary-color) !important;
    transform: translateX(-4px) !important;
}

button[onclick*="showProfileForm"]:active {
    transform: translateX(-2px) scale(0.98) !important;
}
"""

# Read existing CSS
with open('frontend/styles-refined.css', 'r', encoding='utf-8') as f:
    existing_css = f.read()

# Append button fixes
complete_css = existing_css + button_fixes

# Write complete CSS
with open('frontend/styles-refined.css', 'w', encoding='utf-8') as f:
    f.write(complete_css)

print("✅ Fixed btn-primary and btn-danger classes")
print("\nFixed:")
print("  ✅ Save Profile button (btn-primary) - Orange gradient")
print("  ✅ Delete Account button (btn-danger) - Red danger style")
print("  ✅ View Activity button - Orange outline")
print("  ✅ Back to Profile button - Subtle style")
print("  ✅ Profile stats styling")
print("  ✅ Form actions container")
print("\n⚠️  Using !important to override existing styles")
