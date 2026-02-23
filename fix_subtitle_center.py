#!/usr/bin/env python3
"""Fix subtitle to be centered like the title"""

subtitle_fix = """

/* ============================================
   SUBTITLE FIX - Center alignment
   ============================================ */
.header-left .subtitle,
.subtitle,
header .subtitle,
header p {
    text-align: center !important;
    font-size: 1.1rem !important;
    opacity: 0.9 !important;
    margin: 0 !important;
}
"""

# Read existing CSS
with open('frontend/styles-refined.css', 'r', encoding='utf-8') as f:
    existing_css = f.read()

# Append subtitle fix
complete_css = existing_css + subtitle_fix

# Write complete CSS
with open('frontend/styles-refined.css', 'w', encoding='utf-8') as f:
    f.write(complete_css)

print("✅ Fixed subtitle alignment to center")
