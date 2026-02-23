#!/usr/bin/env python3
"""Fix subtitle alignment in staging styles.css"""

import re

# Read the current styles.css
with open('frontend/styles.css', 'r', encoding='utf-8') as f:
    css_content = f.read()

# Add the alignment fix at the end
alignment_fix = """

/* ============================================
   HEADER ALIGNMENT FIX - Feb 23, 2026
   Ensure title and subtitle center to same point
   ============================================ */
.header-content {
    display: block !important;
    width: 100% !important;
    text-align: center !important;
}

.header-left {
    display: block !important;
    width: 100% !important;
    text-align: center !important;
}

header h1,
.header-left h1 {
    text-align: center !important;
    margin-left: auto !important;
    margin-right: auto !important;
    width: 100% !important;
}

header .subtitle,
.header-left .subtitle,
.subtitle {
    text-align: center !important;
    margin-left: auto !important;
    margin-right: auto !important;
    width: 100% !important;
    max-width: 600px !important;
}

.header-right {
    position: absolute !important;
    top: 20px !important;
    right: 20px !important;
    display: flex !important;
    gap: 12px !important;
}

@media (max-width: 768px) {
    .header-right {
        position: static !important;
        margin-top: 20px !important;
        justify-content: center !important;
    }
}
"""

# Append the fix
css_content += alignment_fix

# Write back
with open('frontend/styles.css', 'w', encoding='utf-8') as f:
    f.write(css_content)

print("✅ Fixed subtitle alignment in styles.css")
print("📤 Now deploying to S3...")

import subprocess

# Deploy to S3
result = subprocess.run([
    'aws', 's3', 'cp', 
    'frontend/styles.css', 
    's3://aws-blog-viewer-staging-031421429609/styles.css',
    '--content-type', 'text/css',
    '--cache-control', 'no-cache, no-store, must-revalidate'
], capture_output=True, text=True)

if result.returncode == 0:
    print("✅ Deployed to S3")
    
    # Invalidate CloudFront
    result2 = subprocess.run([
        'aws', 'cloudfront', 'create-invalidation',
        '--distribution-id', 'E1IB9VDMV64CQA',
        '--paths', '/styles.css'
    ], capture_output=True, text=True)
    
    if result2.returncode == 0:
        print("✅ CloudFront cache invalidated")
        print("\n🎉 Complete! Visit https://staging.awseuccontent.com")
        print("   Add ?v=" + str(hash(alignment_fix))[-8:] + " to force refresh")
    else:
        print("❌ CloudFront invalidation failed:", result2.stderr)
else:
    print("❌ S3 upload failed:", result.stderr)
