"""
Deploy cart fix to staging - fixes API endpoint and adds cart functionality
"""

import boto3
import os
import mimetypes
import time

# Configuration
STAGING_BUCKET = 'aws-blog-viewer-staging-031421429609'
STAGING_DISTRIBUTION_ID = 'E1IB9VDMV64CQA'
REGION = 'us-east-1'

# Files to deploy
FILES_TO_DEPLOY = [
    'frontend/app-staging.js',
    'frontend/index-staging.html'
]

def upload_file_to_s3(file_path, bucket_name):
    """Upload a file to S3 with correct content type"""
    s3_client = boto3.client('s3', region_name=REGION)
    
    # Get the file name (without frontend/ prefix)
    file_name = os.path.basename(file_path)
    
    # Determine content type
    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = 'application/octet-stream'
    
    # Upload file
    with open(file_path, 'rb') as f:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=f,
            ContentType=content_type,
            CacheControl='no-cache'  # Disable caching for testing
        )
    
    print(f"  ✅ Uploaded: {file_name} ({content_type})")
    return file_name

def invalidate_cloudfront(distribution_id, paths):
    """Invalidate CloudFront cache for specified paths"""
    cloudfront_client = boto3.client('cloudfront', region_name=REGION)
    
    # Create invalidation paths (add leading slash)
    invalidation_paths = ['/' + path for path in paths]
    
    response = cloudfront_client.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            'Paths': {
                'Quantity': len(invalidation_paths),
                'Items': invalidation_paths
            },
            'CallerReference': f'cart-fix-{int(time.time())}'
        }
    )
    
    invalidation_id = response['Invalidation']['Id']
    print(f"  ✅ CloudFront invalidation created: {invalidation_id}")
    return invalidation_id

def main():
    """Main deployment function"""
    print("=" * 60)
    print("Deploy Cart Fix to Staging")
    print("=" * 60)
    
    try:
        # Upload files
        print("\n📤 Uploading files to S3...")
        uploaded_files = []
        
        for file_path in FILES_TO_DEPLOY:
            if os.path.exists(file_path):
                file_name = upload_file_to_s3(file_path, STAGING_BUCKET)
                uploaded_files.append(file_name)
            else:
                print(f"  ⚠️  File not found: {file_path}")
        
        # Invalidate CloudFront cache
        print("\n🔄 Invalidating CloudFront cache...")
        invalidate_cloudfront(STAGING_DISTRIBUTION_ID, uploaded_files)
        
        print("\n" + "=" * 60)
        print("✅ DEPLOYMENT COMPLETE")
        print("=" * 60)
        print("\nWhat was fixed:")
        print("  ✅ index-staging.html now loads app-staging.js (not app.js)")
        print("  ✅ index-staging.html now loads cart-manager.js")
        print("  ✅ app-staging.js points to /staging API endpoint")
        print("  ✅ app-staging.js has cart initialization")
        print("  ✅ app-staging.js has cart buttons in post cards")
        print("  ✅ app-staging.js has handleCart and updateCartButtons functions")
        print("\nTesting:")
        print("  1. Wait 1-2 minutes for CloudFront cache to clear")
        print("  2. Open https://staging.awseuccontent.com")
        print("  3. Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)")
        print("  4. Sign in if you want to test authenticated cart")
        print("  5. Click '+' button on any post")
        print("  6. Should see 'Added to cart' notification")
        print("  7. Button should change to '✓'")
        print("  8. Check browser console for cart events")
        print("\nNote: Cart UI (floating button + panel) not yet implemented")
        print("      Cart is working but not visible - check console to see cart contents")
        
    except Exception as e:
        print(f"\n❌ DEPLOYMENT FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
