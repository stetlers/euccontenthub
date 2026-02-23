#!/usr/bin/env python3
"""
Fix header alignment by adding equal visual weight on both sides.
The buttons on the right are ~300px wide, so we add matching padding on the left.
"""

fix_css = """

/* ============================================
   VISUAL CENTERING FIX - Feb 23, 2026
   Add equal padding on both sides for true visual center
   ============================================ */
header {
    position: relative !important;
    padding-left: 320px !important;
    padding-right: 320px !important;
}

header h1,
header .subtitle,
header p {
    text-align: center !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    width: 100% !important;
}

.header-content,
.header-left {
    display: block !important;
    width: 100% !important;
    text-align: center !important;
}

.header-right {
    position: absolute !important;
    top: 20px !important;
    right: 32px !important;
    display: flex !important;
    gap: 16px !important;
    z-index: 10 !important;
}

@media (max-width: 1024px) {
    header {
        padding-left: 32px !important;
        padding-right: 32px !important;
    }
    
    .header-right {
        position: static !important;
        margin-top: 20px !important;
        justify-content: center !important;
    }
}
"""

# Read current CSS
with open('frontend/styles-refined.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Append fix
css += fix_css

# Write back
with open('frontend/styles-refined.css', 'w', encoding='utf-8') as f:
    f.write(css)

print("✅ Added visual centering fix")

# Deploy
import subprocess

result = subprocess.run([
    'aws', 's3', 'cp',
    'frontend/styles-refined.css',
    's3://aws-blog-viewer-staging-031421429609/styles.css',
    '--content-type', 'text/css',
    '--cache-control', 'no-cache, no-store, must-revalidate'
], capture_output=True, text=True)

if result.returncode == 0:
    print("✅ Deployed to S3")
    
    result2 = subprocess.run([
        'aws', 'cloudfront', 'create-invalidation',
        '--distribution-id', 'E1IB9VDMV64CQA',
        '--paths', '/styles.css'
    ], capture_output=True, text=True)
    
    if result2.returncode == 0:
        print("✅ CloudFront invalidated")
        print("\n🎉 Done! Hard refresh staging to see the fix")
    else:
        print("❌ CloudFront failed:", result2.stderr)
else:
    print("❌ S3 upload failed:", result.stderr)
