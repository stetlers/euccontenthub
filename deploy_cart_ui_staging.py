import boto3
import os
import time

# Configuration
STAGING_BUCKET = 'aws-blog-viewer-staging-031421429609'
STAGING_DISTRIBUTION_ID = 'E1IB9VDMV64CQA'

# Files to deploy
FILES_TO_DEPLOY = [
    'frontend/cart-ui.js',
    'frontend/cart.css'
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
            'CallerReference': f'cart-ui-deploy-{int(time.time())}'
        }
    )
    
    invalidation_id = response['Invalidation']['Id']
    print(f"✅ Invalidation created: {invalidation_id}")
    print(f"⏳ Cache invalidation in progress (takes 2-3 minutes)")

def main():
    print("=" * 60)
    print("Cart UI Deployment to Staging")
    print("=" * 60)
    
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
    print("\n📋 Deployed files:")
    for file in FILES_TO_DEPLOY:
        print(f"   - {os.path.basename(file)}")

if __name__ == '__main__':
    main()
