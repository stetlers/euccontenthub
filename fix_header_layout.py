#!/usr/bin/env python3
"""Fix header layout to properly align profile button to the right"""

header_layout_fix = """

/* ============================================
   HEADER LAYOUT FIX - Proper Flexbox Alignment
   ============================================ */
header {
    text-align: left !important;
}

.header-content {
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
    gap: 32px !important;
}

.header-left {
    flex: 1 !important;
}

.header-right {
    display: flex !important;
    gap: 16px !important;
    align-items: center !important;
    flex-shrink: 0 !important;
}

#authContainer {
    display: flex !important;
    gap: 12px !important;
    align-items: center !important;
}

/* User profile should not push left */
.user-profile {
    display: inline-flex !important;
}

/* Responsive header */
@media (max-width: 768px) {
    .header-content {
        flex-direction: column !important;
        align-items: stretch !important;
        gap: 20px !important;
    }
    
    .header-left {
        text-align: center !important;
    }
    
    .header-right {
        flex-direction: column !important;
        width: 100% !important;
    }
    
    #authContainer {
        width: 100% !important;
        justify-content: center !important;
    }
}
"""

# Read existing CSS
with open('frontend/styles-refined.css', 'r', encoding='utf-8') as f:
    existing_css = f.read()

# Append header layout fix
complete_css = existing_css + header_layout_fix

# Write complete CSS
with open('frontend/styles-refined.css', 'w', encoding='utf-8') as f:
    f.write(complete_css)

print("✅ Fixed header layout for proper alignment")
print("\nFixed:")
print("  ✅ Header uses flexbox with space-between")
print("  ✅ Header-left takes available space")
print("  ✅ Header-right stays on the right")
print("  ✅ Profile button stays in header-right")
print("  ✅ Responsive layout for mobile")
