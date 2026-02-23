#!/usr/bin/env python3
"""Fix subtitle to align with title - both centered to same point"""

final_alignment = """

/* ============================================
   HEADER ALIGNMENT - FINAL FIX
   Remove all conflicting rules and center everything properly
   ============================================ */
.header-content,
.header-left {
    display: block !important;
    width: 100% !important;
    text-align: inherit !important;
}

header h1,
.header-left h1 {
    text-align: center !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    width: 100% !important;
}

header p,
header .subtitle,
.header-left p,
.header-left .subtitle {
    text-align: center !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    width: 100% !important;
}
"""

# Read existing CSS
with open('frontend/styles-refined.css', 'r', encoding='utf-8') as f:
    existing_css = f.read()

# Append final alignment
complete_css = existing_css + final_alignment

# Write complete CSS
with open('frontend/styles-refined.css', 'w', encoding='utf-8') as f:
    f.write(complete_css)

print("✅ Fixed subtitle alignment - both title and subtitle now center to same point")
