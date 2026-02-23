#!/usr/bin/env python3
"""Fix activity history styling and buttons"""

activity_styles = """

/* ============================================
   DELETE ACCOUNT BUTTON - Danger Style
   ============================================ */
.btn-delete-account {
    padding: 12px 28px;
    font-size: 1rem;
    font-weight: 700;
    border: 2px solid #f44336;
    border-radius: 10px;
    background: white;
    color: #f44336;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    margin-top: 20px;
}

.btn-delete-account:hover {
    background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
    color: white;
    transform: translateY(-3px) scale(1.05);
    box-shadow: 0 6px 20px rgba(244, 67, 54, 0.5);
}

.btn-delete-account:active {
    transform: translateY(-1px) scale(0.98);
}

/* ============================================
   ACTIVITY VIEW - Card-Based Design
   ============================================ */
.activity-view {
    display: flex;
    flex-direction: column;
    gap: 24px;
}

.activity-tabs {
    display: flex;
    gap: 8px;
    border-bottom: 2px solid var(--border-color);
    overflow-x: auto;
}

.activity-tab {
    padding: 12px 24px;
    background: none;
    border: none;
    border-bottom: 3px solid transparent;
    font-size: 0.9375rem;
    font-weight: 700;
    color: #666;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    white-space: nowrap;
    display: flex;
    align-items: center;
    gap: 8px;
}

.activity-tab:hover {
    color: var(--primary-color);
    background: var(--bg-hover);
    transform: translateY(-2px);
}

.activity-tab.active {
    color: var(--secondary-color);
    border-bottom-color: var(--secondary-color);
    background: linear-gradient(135deg, rgba(255, 153, 0, 0.1) 0%, rgba(255, 153, 0, 0.05) 100%);
}

.activity-tab-badge {
    display: inline-block;
    background: var(--secondary-color);
    color: white;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 700;
    min-width: 20px;
    text-align: center;
}

.activity-tab.active .activity-tab-badge {
    background: white;
    color: var(--secondary-color);
}

.activity-tab-content {
    display: none;
}

.activity-tab-content.active {
    display: block;
}

.activity-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
}

/* ============================================
   ACTIVITY ITEMS - Card Style
   ============================================ */
.activity-item {
    padding: 20px;
    background: white;
    border-radius: 12px;
    border: 2px solid var(--border-color);
    border-left: 4px solid var(--secondary-color);
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    box-shadow: var(--shadow);
}

.activity-item:hover {
    transform: translateY(-4px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
    border-left-color: var(--primary-color);
}

.activity-item-header {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 12px;
}

.activity-item-title {
    font-weight: 700;
    font-size: 1rem;
    color: var(--primary-color);
    text-decoration: none;
    line-height: 1.4;
    transition: color 0.3s;
}

.activity-item-title:hover {
    color: var(--secondary-color);
}

.activity-item-date {
    font-size: 0.8125rem;
    color: #999;
    font-weight: 600;
}

.activity-item-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    font-size: 0.8125rem;
    color: #666;
    font-weight: 600;
}

.activity-item-meta span {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    background: var(--bg-hover);
    border-radius: 6px;
}

.activity-item-content {
    margin-top: 12px;
    padding: 12px;
    background: var(--bg-hover);
    border-radius: 8px;
    font-size: 0.9375rem;
    line-height: 1.6;
    color: var(--text-color);
    border-left: 3px solid var(--secondary-color);
}

.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: #999;
    font-size: 1rem;
    font-weight: 600;
    background: var(--bg-hover);
    border-radius: 12px;
    border: 2px dashed var(--border-color);
}

.empty-state::before {
    content: '📭';
    display: block;
    font-size: 3rem;
    margin-bottom: 16px;
}

/* ============================================
   BACK TO PROFILE BUTTON
   ============================================ */
.btn-back-to-profile {
    padding: 10px 20px;
    font-size: 0.9375rem;
    font-weight: 600;
    border: 2px solid var(--border-color);
    border-radius: 8px;
    background: white;
    color: var(--text-color);
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    display: inline-flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 20px;
}

.btn-back-to-profile:hover {
    background: var(--bg-hover);
    border-color: var(--secondary-color);
    transform: translateX(-4px);
}

.btn-back-to-profile:active {
    transform: translateX(-2px) scale(0.98);
}

/* ============================================
   VIEW ACTIVITY BUTTON
   ============================================ */
.btn-view-activity {
    padding: 12px 24px;
    font-size: 0.9375rem;
    font-weight: 700;
    border: 2px solid var(--secondary-color);
    border-radius: 10px;
    background: white;
    color: var(--secondary-color);
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    display: inline-flex;
    align-items: center;
    gap: 8px;
}

.btn-view-activity:hover {
    background: linear-gradient(135deg, var(--secondary-color) 0%, #ec8b00 100%);
    color: white;
    transform: translateY(-3px) scale(1.05);
    box-shadow: 0 6px 16px rgba(255, 153, 0, 0.4);
}

.btn-view-activity:active {
    transform: translateY(-1px) scale(0.98);
}

/* ============================================
   RESPONSIVE - Activity View
   ============================================ */
@media (max-width: 768px) {
    .activity-list {
        grid-template-columns: 1fr;
    }
    
    .activity-tabs {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }
    
    .activity-tab {
        padding: 10px 16px;
        font-size: 0.875rem;
    }
    
    .activity-item {
        padding: 16px;
    }
}
"""

# Read existing CSS
with open('frontend/styles-refined.css', 'r', encoding='utf-8') as f:
    existing_css = f.read()

# Append activity styles
complete_css = existing_css + activity_styles

# Write complete CSS
with open('frontend/styles-refined.css', 'w', encoding='utf-8') as f:
    f.write(complete_css)

print("✅ Added activity history and button styles")
print("\nAdded:")
print("  ✅ Delete Account button (danger red style)")
print("  ✅ Activity tabs (animated, with badges)")
print("  ✅ Activity items (card-based grid layout)")
print("  ✅ Activity item hover effects")
print("  ✅ Empty state styling")
print("  ✅ Back to Profile button")
print("  ✅ View Activity button")
print("  ✅ Responsive design for mobile")
