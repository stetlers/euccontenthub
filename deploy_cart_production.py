import boto3
import os
import time

# Configuration
PRODUCTION_BUCKET = 'aws-blog-viewer-031421429609'
PRODUCTION_DISTRIBUTION_ID = 'E20CC1TSSWTCWN'

# Files to deploy
FILES_TO_DEPLOY = [
    'frontend/cart-manager.js',  # API calls enabled
    'frontend/cart-ui.js',
    'frontend/cart.css',
    'frontend/app.js',
    'frontend/auth.js',          # Cart merge trigger added
    'frontend/index.html'
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
            'CallerReference': f'cart-production-deploy-{int(time.time())}'
        }
    )
    
    invalidation_id = response['Invalidation']['Id']
    print(f"✅ Invalidation created: {invalidation_id}")
    print(f"⏳ Cache invalidation in progress (takes 2-3 minutes)")

def main():
    print("=" * 60)
    print("🚀 Cart Feature - Production Deployment")
    print("=" * 60)
    
    print("\n⚠️  PRODUCTION DEPLOYMENT")
    print("This will deploy the complete cart feature to https://awseuccontent.com")
    print("\nFeatures included:")
    print("   - Cart UI with floating button and panel")
    print("   - Export in 3 formats (Slack, Plain Text, HTML)")
    print("   - API-based persistence for authenticated users")
    print("   - localStorage fallback for anonymous users")
    print("   - Automatic cart merge on sign-in")
    print("   - Cross-device sync for authenticated users")
    print("\nFiles to deploy:")
    for file in FILES_TO_DEPLOY:
        print(f"   - {os.path.basename(file)}")
    
    response = input("\n✋ Continue with production deployment? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Deployment cancelled")
        return
    
    # Deploy to production
    print(f"\n📦 Deploying to production bucket: {PRODUCTION_BUCKET}")
    deploy_to_s3(PRODUCTION_BUCKET, FILES_TO_DEPLOY)
    
    # Invalidate CloudFront cache
    invalidate_cloudfront(PRODUCTION_DISTRIBUTION_ID)
    
    print("\n" + "=" * 60)
    print("✅ Production Deployment Complete!")
    print("=" * 60)
    print(f"\n🌐 Production URL: https://awseuccontent.com")
    print("⏳ Wait 2-3 minutes for CloudFront cache to clear")
    print("\n📋 Deployed files:")
    for file in FILES_TO_DEPLOY:
        print(f"   - {os.path.basename(file)}")
    
    print("\n📝 Note: Complete cart feature with API integration")
    print("   - Authenticated users: Cart persists to DynamoDB")
    print("   - Anonymous users: Cart persists to localStorage")
    print("   - Automatic merge on sign-in")
    print("   - Cross-device sync for authenticated users")

if __name__ == '__main__':
    main()
