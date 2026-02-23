#!/usr/bin/env python3
"""Restore original simple header - just centered text with buttons positioned top-right"""

original_header = """

/* ============================================
   HEADER - RESTORE ORIGINAL SIMPLE CENTERED
   ============================================ */
header {
    text-align: center !important;
    margin-bottom: 40px !important;
    padding: 40px 20px !important;
    background: linear-gradient(135deg, var(--primary-color) 0%, #3a4a5e 100%) !important;
    color: white !important;
    border-radius: 12px !important;
    box-shadow: var(--shadow) !important;
    position: relative !important;
}

header h1 {
    font-size: 2.5rem !important;
    margin-bottom: 10px !important;
    font-weight: 700 !important;
}

.subtitle {
    font-size: 1.1rem !important;
    opacity: 0.9 !important;
}

/* Buttons positioned top-right */
.header-right {
    position: absolute !important;
    top: 20px !important;
    right: 20px !important;
    display: flex !important;
    gap: 16px !important;
    align-items: center !important;
}

@media (max-width: 768px) {
    header h1 {
        font-size: 1.8rem !important;
    }
    
    .header-right {
        position: static !important;
        flex-direction: column !important;
        margin-top: 20px !important;
    }
}
"""

# Read existing CSS
with open('frontend/styles-refined.css', 'r', encoding='utf-8') as f:
    existing_css = f.read()

# Append original header
complete_css = existing_css + original_header

# Write complete CSS
with open('frontend/styles-refined.css', 'w', encoding='utf-8') as f:
    f.write(complete_css)

print("✅ Restored original simple centered header")
print("   - Title and subtitle centered")
print("   - Buttons in top-right corner")
