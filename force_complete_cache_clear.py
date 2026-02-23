#!/usr/bin/env python3
"""Force complete CloudFront cache clear for staging"""

import boto3
import time

cloudfront = boto3.client('cloudfront', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1')

distribution_id = 'E1IB9VDMV64CQA'  # Staging
bucket = 'aws-blog-viewer-staging-031421429609'

print("="*70)
print("FORCE COMPLETE CACHE CLEAR - STAGING")
print("="*70)

# Step 1: Re-upload app.js with no-cache headers
print("\n1. Re-uploading app.js with no-cache headers...")
s3.upload_file(
    'frontend/app-staging.js',
    bucket,
    'app.js',
    ExtraArgs={
        'ContentType': 'application/javascript',
        'CacheControl': 'no-cache, no-store, must-revalidate',
        'Expires': '0'
    }
)
print("   ✅ Uploaded with no-cache headers")

# Step 2: Create invalidation for all files
print("\n2. Creating CloudFront invalidation for ALL files...")
response = cloudfront.create_invalidation(
    DistributionId=distribution_id,
    InvalidationBatch={
        'Paths': {
            'Quantity': 4,
            'Items': ['/*', '/app.js', '/index.html', '/auth.js']
        },
        'CallerReference': f'force-clear-{time.time()}'
    }
)

invalidation_id = response['Invalidation']['Id']
print(f"   ✅ Invalidation created: {invalidation_id}")

# Step 3: Check current app.js in S3
print("\n3. Verifying app.js in S3...")
obj = s3.get_object(Bucket=bucket, Key='app.js')
content = obj['Body'].read().decode('utf-8')

if 'const token = window.authManager.getIdToken()' in content:
    print("   ✅ S3 has the NEW version with token validation")
else:
    print("   ❌ S3 still has OLD version")

print("\n" + "="*70)
print("NEXT STEPS")
print("="*70)
print("\n1. Wait 2-3 minutes for invalidation to complete")
print("2. Hard refresh staging page (Ctrl+Shift+R or Cmd+Shift+R)")
print("3. Check browser console for 'Token exists: true/false' log")
print("4. Try crawler button again")
print("\n💡 If still not working, try incognito mode to bypass browser cache")
