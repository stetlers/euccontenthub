import boto3
import os
import time

# Configuration
STAGING_BUCKET = 'aws-blog-viewer-staging-031421429609'
STAGING_DISTRIBUTION_ID = 'E1IB9VDMV64CQA'

# Files to deploy
FILES_TO_DEPLOY = [
    'frontend/cart-manager.js',  # API calls uncommented
    'frontend/auth.js',           # Cart merge trigger added
]

def deploy_to_s3(bucket_name, files):
    """Deploy files to S3 bucket"""
    s3 = boto3.client('s3', region_name='us-east-1')
    
    for file_path in files:
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            continue
        
        # Get the filename (without frontend/ prefix)
        filename = os.path.basename(file_path)
        
        # Determine content type
        content_type = 'text/html' if filename.endswith('.html') else \
                      'text/css' if filename.endswith('.css') else \
                      'application/javascript'
        
        print(f"📤 Uploading {filename} to {bucket_name}...")
        
        with open(file_path, 'rb') as f:
            s3.put_object(
                Bucket=bucket_name,
                Key=filename,
                Body=f.read(),
                ContentType=content_type,
                CacheControl='no-cache, no-store, must-revalidate'
            )
        
        print(f"✅ Uploaded {filename}")

def invalidate_cloudfront(distribution_id):
    """Invalidate CloudFront cache"""
    cloudfront = boto3.client('cloudfront', region_name='us-east-1')
    
    print(f"\n🔄 Invalidating CloudFront cache for {distribution_id}...")
    
    response = cloudfront.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            'Paths': {
                'Quantity': 1,
                'Items': ['/*']
            },
            'CallerReference': f'cart-api-integration-{int(time.time())}'
        }
    )
    
    invalidation_id = response['Invalidation']['Id']
    print(f"✅ Invalidation created: {invalidation_id}")
    print(f"⏳ Cache invalidation in progress (takes 2-3 minutes)")

def main():
    print("=" * 60)
    print("Cart API Integration - Staging Deployment")
    print("=" * 60)
    print("\nChanges:")
    print("  ✅ API Gateway configured with /cart endpoints")
    print("  ✅ CartManager: API calls enabled for authenticated users")
    print("  ✅ Auth.js: Cart merge trigger added on sign-in")
    print("  ✅ localStorage fallback for anonymous users")
    
    # Deploy to staging
    print(f"\n📦 Deploying to staging bucket: {STAGING_BUCKET}")
    deploy_to_s3(STAGING_BUCKET, FILES_TO_DEPLOY)
    
    # Invalidate CloudFront cache
    invalidate_cloudfront(STAGING_DISTRIBUTION_ID)
    
    print("\n" + "=" * 60)
    print("✅ Deployment Complete!")
    print("=" * 60)
    print(f"\n🌐 Staging URL: https://staging.awseuccontent.com")
    print("⏳ Wait 2-3 minutes for CloudFront cache to clear")
    print("\n📋 Testing Steps:")
    print("  1. Visit staging site as anonymous user")
    print("  2. Add posts to cart (should use localStorage)")
    print("  3. Sign in with Google")
    print("  4. Cart should merge and persist to DynamoDB")
    print("  5. Refresh page - cart should load from API")
    print("  6. Sign out and back in - cart should persist")

if __name__ == '__main__':
    main()
