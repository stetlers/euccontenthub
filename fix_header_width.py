#!/usr/bin/env python3
"""Fix header-left to take full width for proper centering"""

width_fix = """

/* ============================================
   HEADER WIDTH FIX - Full width for centering
   ============================================ */
.header-content {
    display: block !important;
    position: relative !important;
    width: 100% !important;
}

.header-left {
    width: 100% !important;
    text-align: center !important;
    display: block !important;
}

.header-left h1 {
    text-align: center !important;
    width: 100% !important;
    display: block !important;
}

.header-left .subtitle {
    text-align: center !important;
    width: 100% !important;
    display: block !important;
}
"""

# Read existing CSS
with open('frontend/styles-refined.css', 'r', encoding='utf-8') as f:
    existing_css = f.read()

# Append width fix
complete_css = existing_css + width_fix

# Write complete CSS
with open('frontend/styles-refined.css', 'w', encoding='utf-8') as f:
    f.write(complete_css)

print("✅ Fixed header width for proper centering")
