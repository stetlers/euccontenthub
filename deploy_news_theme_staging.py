#!/usr/bin/env python3
"""Deploy news aggregator theme to staging"""

import boto3
import time

s3 = boto3.client('s3', region_name='us-east-1')
cloudfront = boto3.client('cloudfront', region_name='us-east-1')

bucket = 'aws-blog-viewer-staging-031421429609'
distribution_id = 'E1IB9VDMV64CQA'

print("="*70)
print("DEPLOYING NEWS AGGREGATOR THEME TO STAGING")
print("="*70)

# Upload new styles
print("\n1. Uploading new styles.css...")
s3.upload_file(
    'frontend/styles-news-theme.css',
    bucket,
    'styles.css',
    ExtraArgs={
        'ContentType': 'text/css',
        'CacheControl': 'no-cache, no-store, must-revalidate'
    }
)
print("   ✅ Uploaded styles.css")

# Upload updated index.html
print("\n2. Uploading updated index.html...")
s3.upload_file(
    'frontend/index-staging.html',
    bucket,
    'index.html',
    ExtraArgs={
        'ContentType': 'text/html',
        'CacheControl': 'no-cache, no-store, must-revalidate'
    }
)
print("   ✅ Uploaded index.html")

# Invalidate CloudFront
print("\n3. Invalidating CloudFront cache...")
response = cloudfront.create_invalidation(
    DistributionId=distribution_id,
    InvalidationBatch={
        'Paths': {
            'Quantity': 2,
            'Items': ['/styles.css', '/index.html']
        },
        'CallerReference': f'news-theme-{time.time()}'
    }
)

invalidation_id = response['Invalidation']['Id']
print(f"   ✅ Invalidation created: {invalidation_id}")

print("\n" + "="*70)
print("✅ NEWS THEME DEPLOYED TO STAGING")
print("="*70)
print("\n🔗 View at: https://staging.awseuccontent.com")
print("\n⏳ Wait 1-2 minutes for CloudFront cache to clear")
print("💡 Hard refresh (Ctrl+Shift+R) to see changes immediately")
print("\n📝 Note: This is a complete visual redesign")
print("   - Compact header with AWS branding")
print("   - List-based layout (like Hacker News)")
print("   - Left-side voting")
print("   - Sticky toolbar")
print("   - News aggregator feel")
