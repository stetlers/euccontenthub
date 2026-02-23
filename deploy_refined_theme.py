#!/usr/bin/env python3
"""Deploy refined theme to staging"""

import boto3
import time

s3 = boto3.client('s3', region_name='us-east-1')
cloudfront = boto3.client('cloudfront', region_name='us-east-1')

bucket = 'aws-blog-viewer-staging-031421429609'
distribution_id = 'E1IB9VDMV64CQA'

print("="*70)
print("DEPLOYING REFINED THEME TO STAGING")
print("="*70)
print("\nChanges:")
print("  ✨ Modern color palette (richer, more sophisticated)")
print("  ✨ Better typography (improved weights and spacing)")
print("  ✨ Refined shadows (more depth and dimension)")
print("  ✨ Smooth animations (subtle card entrance)")
print("  ✨ Better header (more balanced)")
print("  ✨ Improved spacing (better visual hierarchy)")
print("\n  ✅ KEEPS card layout")
print("  ✅ KEEPS dashboard charts")
print("  ✅ KEEPS all functionality")

# Upload refined styles
print("\n📤 Uploading refined styles.css...")
s3.upload_file(
    'frontend/styles-refined.css',
    bucket,
    'styles.css',
    ExtraArgs={
        'ContentType': 'text/css',
        'CacheControl': 'no-cache, no-store, must-revalidate'
    }
)
print("   ✅ Uploaded")

# Invalidate CloudFront
print("\n🔄 Invalidating CloudFront cache...")
response = cloudfront.create_invalidation(
    DistributionId=distribution_id,
    InvalidationBatch={
        'Paths': {
            'Quantity': 1,
            'Items': ['/styles.css']
        },
        'CallerReference': f'refined-theme-{time.time()}'
    }
)

invalidation_id = response['Invalidation']['Id']
print(f"   ✅ Invalidation created: {invalidation_id}")

print("\n" + "="*70)
print("✅ REFINED THEME DEPLOYED")
print("="*70)
print("\n🔗 View at: https://staging.awseuccontent.com")
print("\n⏳ Wait 1-2 minutes, then hard refresh (Ctrl+Shift+R)")
print("\n💡 This is a subtle refinement - same layout, better polish!")
