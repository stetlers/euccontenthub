#!/usr/bin/env python3
"""Restore simple centered header with buttons positioned on right"""

simple_header = """

/* ============================================
   HEADER - SIMPLE CENTERED WITH BUTTONS RIGHT
   ============================================ */
header {
    text-align: center !important;
    margin-bottom: 40px !important;
    padding: 40px 20px !important;
    position: relative !important;
}

.header-content {
    display: block !important;
    position: relative !important;
}

.header-left {
    text-align: center !important;
}

.header-left h1 {
    font-size: 2.5rem !important;
    margin-bottom: 10px !important;
    font-weight: 700 !important;
}

.header-left .subtitle,
.subtitle {
    font-size: 1.1rem !important;
    opacity: 0.9 !important;
}

.header-right {
    position: absolute !important;
    top: 0 !important;
    right: 0 !important;
    display: flex !important;
    gap: 16px !important;
    align-items: center !important;
}

#authContainer {
    display: flex !important;
    gap: 12px !important;
    align-items: center !important;
}

/* Responsive header */
@media (max-width: 768px) {
    header h1 {
        font-size: 1.8rem !important;
    }
    
    .header-right {
        position: static !important;
        flex-direction: column !important;
        margin-top: 20px !important;
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

# Append simple header
complete_css = existing_css + simple_header

# Write complete CSS
with open('frontend/styles-refined.css', 'w', encoding='utf-8') as f:
    f.write(complete_css)

print("✅ Restored simple centered header with buttons on right")
print("\nFixed:")
print("  ✅ Header text centered (like original)")
print("  ✅ Title and subtitle aligned")
print("  ✅ Buttons positioned absolutely on right")
print("  ✅ Responsive layout for mobile")
