#!/usr/bin/env python3
"""Fix header text alignment - keep centered but buttons on right"""

header_alignment_fix = """

/* ============================================
   HEADER ALIGNMENT FIX - Center text, buttons right
   ============================================ */
header {
    text-align: center !important;
    padding: 40px 20px !important;
}

.header-content {
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
    gap: 32px !important;
}

.header-left {
    flex: 1 !important;
    text-align: center !important;
}

.header-left h1 {
    margin: 0 !important;
    font-size: 2.5rem !important;
    font-weight: 700 !important;
}

.header-left .subtitle {
    margin: 0 !important;
    font-size: 1.1rem !important;
    opacity: 0.9 !important;
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

# Append header alignment fix
complete_css = existing_css + header_alignment_fix

# Write complete CSS
with open('frontend/styles-refined.css', 'w', encoding='utf-8') as f:
    f.write(complete_css)

print("✅ Fixed header alignment")
print("\nFixed:")
print("  ✅ Header text centered")
print("  ✅ Title and subtitle aligned properly")
print("  ✅ Buttons stay on the right")
print("  ✅ Responsive layout maintained")
