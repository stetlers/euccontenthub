#!/usr/bin/env python3
"""
Frontend Deployment Script for EUC Content Hub
Deploys frontend files to staging or production S3 bucket and invalidates CloudFront cache

Usage:
    python deploy_frontend.py staging   # Deploy to staging
    python deploy_frontend.py production # Deploy to production
"""

import boto3
import sys
import os
import time
from pathlib import Path

# Environment configurations
ENVIRONMENTS = {
    'staging': {
        'bucket': 'aws-blog-viewer-staging-031421429609',
        'distribution_id': 'E1IB9VDMV64CQA',
        'url': 'https://staging.awseuccontent.com'
    },
    'production': {
        'bucket': 'aws-blog-viewer-031421429609',
        'distribution_id': 'E20CC1TSSWTCWN',
        'url': 'https://awseuccontent.com'
    }
}

# Frontend files to deploy
FRONTEND_FILES = [
    'index.html',
    'app.js',
    'auth.js',
    'profile.js',
    'chat-widget.js',
    'chat-widget.css',
    'styles.css'
]

def get_content_type(filename):
    """Get content type based on file extension"""
    ext = filename.split('.')[-1].lower()
    content_types = {
        'html': 'text/html',
        'js': 'application/javascript',
        'css': 'text/css',
        'json': 'application/json',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'svg': 'image/svg+xml'
    }
    return content_types.get(ext, 'application/octet-stream')

def deploy_frontend(environment):
    """Deploy frontend files to specified environment"""
    
    if environment not in ENVIRONMENTS:
        print(f"❌ Error: Unknown environment '{environment}'")
        print(f"   Valid environments: {', '.join(ENVIRONMENTS.keys())}")
        sys.exit(1)
    
    config = ENVIRONMENTS[environment]
    bucket = config['bucket']
    distribution_id = config['distribution_id']
    url = config['url']
    
    print("=" * 70)
    print(f"Frontend Deployment to {environment.upper()}")
    print("=" * 70)
    print(f"Bucket: {bucket}")
    print(f"CloudFront: {distribution_id}")
    print(f"URL: {url}")
    print()
    
    # Initialize AWS clients
    s3 = boto3.client('s3', region_name='us-east-1')
    cloudfront = boto3.client('cloudfront', region_name='us-east-1')
    
    # Check if frontend directory exists
    frontend_dir = Path('frontend')
    if not frontend_dir.exists():
        print(f"❌ Error: frontend/ directory not found")
        sys.exit(1)
    
    # Upload files
    print("Uploading files...")
    uploaded_count = 0
    
    for filename in FRONTEND_FILES:
        file_path = frontend_dir / filename
        
        if not file_path.exists():
            print(f"  ⚠️  Warning: {filename} not found, skipping")
            continue
        
        try:
            content_type = get_content_type(filename)
            print(f"  📤 Uploading {filename}... ", end='', flush=True)
            
            s3.upload_file(
                str(file_path),
                bucket,
                filename,
                ExtraArgs={
                    'ContentType': content_type,
                    'CacheControl': 'max-age=300'  # 5 minutes cache
                }
            )
            
            print("✅")
            uploaded_count += 1
            
        except Exception as e:
            print(f"❌")
            print(f"     Error: {str(e)}")
    
    print(f"\n✅ Uploaded {uploaded_count}/{len(FRONTEND_FILES)} files")
    
    # Invalidate CloudFront cache
    print(f"\nInvalidating CloudFront cache...")
    try:
        response = cloudfront.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                'Paths': {
                    'Quantity': 1,
                    'Items': ['/*']
                },
                'CallerReference': str(time.time())
            }
        )
        
        invalidation_id = response['Invalidation']['Id']
        print(f"  ✅ Invalidation created: {invalidation_id}")
        print(f"  ⏳ Cache invalidation in progress (takes 1-2 minutes)")
        
    except Exception as e:
        print(f"  ❌ Error creating invalidation: {str(e)}")
    
    # Summary
    print()
    print("=" * 70)
    print(f"✅ Deployment to {environment.upper()} complete!")
    print("=" * 70)
    print(f"🔗 View at: {url}")
    print()
    
    if environment == 'staging':
        print("💡 Next steps:")
        print("   1. Test the staging site thoroughly")
        print("   2. If everything works, deploy to production:")
        print("      python deploy_frontend.py production")
    else:
        print("💡 Deployment complete!")
        print("   Monitor the site for any issues")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python deploy_frontend.py <environment>")
        print("Environments: staging, production")
        sys.exit(1)
    
    environment = sys.argv[1].lower()
    deploy_frontend(environment)
