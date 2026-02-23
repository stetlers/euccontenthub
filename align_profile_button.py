#!/usr/bin/env python3
"""Align profile button to the right"""

alignment_fix = """

/* ============================================
   PROFILE BUTTON ALIGNMENT - Move to Right
   ============================================ */
.user-profile {
    margin-left: auto !important;
}

/* Ensure header-right uses flexbox properly */
.header-right {
    display: flex !important;
    gap: 16px !important;
    align-items: center !important;
    margin-left: auto !important;
}
"""

# Read existing CSS
with open('frontend/styles-refined.css', 'r', encoding='utf-8') as f:
    existing_css = f.read()

# Append alignment fix
complete_css = existing_css + alignment_fix

# Write complete CSS
with open('frontend/styles-refined.css', 'w', encoding='utf-8') as f:
    f.write(complete_css)

print("✅ Profile button aligned to the right")
