#!/usr/bin/env python3
"""
Deploy Frontend with KB Editor to Staging

Deploys the updated frontend with KB editor integration to staging S3 bucket
and invalidates CloudFront cache.
"""

import boto3
import os
import mimetypes
import time
from pathlib import Path

# Configuration
STAGING_BUCKET = 'aws-blog-viewer-staging-031421429609'
STAGING_DISTRIBUTION_ID = 'E1IB9VDMV64CQA'

# Files to deploy
FILES_TO_DEPLOY = [
    'frontend/index.html',
    'frontend/auth.js',
    'frontend/app.js',
    'frontend/kb-editor.js',
    'frontend/kb-editor-styles.css',
    'frontend/chat-widget-kb.js',
]

def upload_file(s3_client, local_path, bucket, s3_key):
    """Upload a file to S3 with correct content type"""
    
    # Determine content type
    content_type, _ = mimetypes.guess_type(local_path)
    if content_type is None:
        content_type = 'application/octet-stream'
    
    # Upload file
    with open(local_path, 'rb') as f:
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=f.read(),
            ContentType=content_type
        )
    
    print(f"  ✅ Uploaded: {s3_key}")

def main():
    print("=" * 70)
    print("Deploy Frontend with KB Editor - STAGING")
    print("=" * 70)
    print()
    
    # Initialize AWS clients
    s3 = boto3.client('s3', region_name='us-east-1')
    cloudfront = boto3.client('cloudfront', region_name='us-east-1')
    
    # Upload files
    print("📤 Uploading files to S3...")
    for file_path in FILES_TO_DEPLOY:
        if not os.path.exists(file_path):
            print(f"  ⚠️  File not found: {file_path}")
            continue
        
        # Determine S3 key (remove 'frontend/' prefix)
        s3_key = file_path.replace('frontend/', '')
        
        upload_file(s3, file_path, STAGING_BUCKET, s3_key)
    
    # Invalidate CloudFront cache
    print(f"\n🔄 Invalidating CloudFront cache...")
    try:
        response = cloudfront.create_invalidation(
            DistributionId=STAGING_DISTRIBUTION_ID,
            InvalidationBatch={
                'Paths': {
                    'Quantity': 6,
                    'Items': [
                        '/index.html',
                        '/auth.js',
                        '/app.js',
                        '/kb-editor.js',
                        '/kb-editor-styles.css',
                        '/chat-widget-kb.js'
                    ]
                },
                'CallerReference': f'kb-editor-deploy-{int(time.time())}'
            }
        )
        
        invalidation_id = response['Invalidation']['Id']
        print(f"  ✅ Invalidation created: {invalidation_id}")
        print(f"  ⏳ Cache invalidation in progress (2-3 minutes)...")
        
    except Exception as e:
        print(f"  ⚠️  Warning: Could not invalidate cache: {str(e)}")
        print(f"  💡 You may need to wait 5-10 minutes or clear browser cache")
    
    # Summary
    print()
    print("=" * 70)
    print("✅ Deployment Complete!")
    print("=" * 70)
    print()
    print("🔗 Staging URL: https://staging.awseuccontent.com")
    print()
    print("📝 What was deployed:")
    print("  • KB Editor UI (kb-editor.js)")
    print("  • KB Editor Styles (kb-editor-styles.css)")
    print("  • Updated auth.js (with KB editor menu option)")
    print("  • Updated index.html (includes KB editor)")
    print()
    print("🧪 Testing:")
    print("  1. Go to https://staging.awseuccontent.com")
    print("  2. Sign in with your account")
    print("  3. Click your profile dropdown")
    print("  4. Click '📚 Edit Knowledge Base'")
    print("  5. Try editing a document")
    print()
    print("💡 Features:")
    print("  • Document list with metadata")
    print("  • Markdown editor with preview")
    print("  • Change comment tracking (required)")
    print("  • Contribution points and leaderboard")
    print("  • Personal contribution dashboard")

if __name__ == '__main__':
    main()
