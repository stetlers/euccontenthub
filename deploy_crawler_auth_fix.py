#!/usr/bin/env python3
"""
Deploy crawler authentication fix to staging and production

This script:
1. Deploys API Lambda with @require_auth on /crawl endpoint
2. Deploys frontend with Authorization header in crawler request
3. Tests the fix in staging
4. Optionally deploys to production
"""

import boto3
import zipfile
import os
import time
import sys

def create_lambda_zip():
    """Create deployment package for API Lambda"""
    print("\n" + "="*70)
    print("STEP 1: Creating Lambda deployment package")
    print("="*70)
    
    zip_filename = 'api_lambda_deploy.zip'
    
    # Remove old zip if exists
    if os.path.exists(zip_filename):
        os.remove(zip_filename)
        print(f"  🗑️  Removed old {zip_filename}")
    
    # Create new zip
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add lambda_function.py from lambda_api directory
        zipf.write('lambda_api/lambda_function.py', 'lambda_function.py')
        print(f"  ✅ Added lambda_function.py")
    
    print(f"  ✅ Created {zip_filename}")
    return zip_filename

def deploy_lambda(environment):
    """Deploy Lambda to specified environment"""
    print("\n" + "="*70)
    print(f"STEP 2: Deploying Lambda to {environment.upper()}")
    print("="*70)
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    function_name = 'aws-blog-api'
    
    # Read zip file
    with open('api_lambda_deploy.zip', 'rb') as f:
        zip_content = f.read()
    
    # Update function code
    print(f"  📤 Uploading code to {function_name}...")
    response = lambda_client.update_function_code(
        FunctionName=function_name,
        ZipFile=zip_content
    )
    
    version = response['Version']
    print(f"  ✅ Uploaded code (version: {version})")
    
    # Wait for update to complete
    print(f"  ⏳ Waiting for Lambda to be ready...")
    waiter = lambda_client.get_waiter('function_updated')
    waiter.wait(FunctionName=function_name)
    print(f"  ✅ Lambda is ready")
    
    # Publish new version
    print(f"  📦 Publishing new version...")
    publish_response = lambda_client.publish_version(
        FunctionName=function_name,
        Description=f'Add authentication to /crawl endpoint - {environment}'
    )
    new_version = publish_response['Version']
    print(f"  ✅ Published version: {new_version}")
    
    # Update alias
    alias_name = 'production' if environment == 'production' else 'staging'
    
    try:
        print(f"  🔄 Updating {alias_name} alias to version {new_version}...")
        lambda_client.update_alias(
            FunctionName=function_name,
            Name=alias_name,
            FunctionVersion=new_version
        )
        print(f"  ✅ Updated {alias_name} alias")
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"  ⚠️  Alias {alias_name} not found, creating...")
        lambda_client.create_alias(
            FunctionName=function_name,
            Name=alias_name,
            FunctionVersion=new_version
        )
        print(f"  ✅ Created {alias_name} alias")
    
    return new_version

def deploy_frontend(environment):
    """Deploy frontend to specified environment"""
    print("\n" + "="*70)
    print(f"STEP 3: Deploying Frontend to {environment.upper()}")
    print("="*70)
    
    s3 = boto3.client('s3', region_name='us-east-1')
    cloudfront = boto3.client('cloudfront', region_name='us-east-1')
    
    if environment == 'staging':
        bucket = 'aws-blog-viewer-staging-031421429609'
        distribution_id = 'E1IB9VDMV64CQA'
        source_file = 'frontend/app-staging.js'
    else:
        bucket = 'aws-blog-viewer-031421429609'
        distribution_id = 'E20CC1TSSWTCWN'
        source_file = 'frontend/app.js'
    
    # Upload app.js
    print(f"  📤 Uploading {source_file} to {bucket}...")
    s3.upload_file(
        source_file,
        bucket,
        'app.js',
        ExtraArgs={
            'ContentType': 'application/javascript',
            'CacheControl': 'max-age=300'
        }
    )
    print(f"  ✅ Uploaded app.js")
    
    # Invalidate CloudFront
    print(f"  🔄 Invalidating CloudFront cache...")
    response = cloudfront.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            'Paths': {
                'Quantity': 1,
                'Items': ['/app.js']
            },
            'CallerReference': str(time.time())
        }
    )
    invalidation_id = response['Invalidation']['Id']
    print(f"  ✅ Invalidation created: {invalidation_id}")
    print(f"  ⏳ Cache will clear in 5-15 minutes")

def test_staging():
    """Test the fix in staging"""
    print("\n" + "="*70)
    print("STEP 4: Testing Staging")
    print("="*70)
    
    print("\n  📋 Manual Test Checklist:")
    print("  1. Open https://staging.awseuccontent.com in incognito window")
    print("  2. Verify crawler button is NOT visible when signed out")
    print("  3. Try to call API directly (should get 401):")
    print("     curl -X POST https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/crawl")
    print("  4. Sign in to staging")
    print("  5. Verify crawler button IS visible when signed in")
    print("  6. Click crawler button (should work)")
    print("\n  ⏳ Wait 5-15 minutes for CloudFront cache to clear before testing")

def main():
    print("\n" + "="*70)
    print("CRAWLER AUTHENTICATION FIX DEPLOYMENT")
    print("="*70)
    print("\nThis will:")
    print("  • Add @require_auth to /crawl endpoint in API Lambda")
    print("  • Add Authorization header to crawler request in frontend")
    print("  • Deploy to staging first, then optionally to production")
    print("\n" + "="*70)
    
    # Create Lambda zip
    create_lambda_zip()
    
    # Deploy to staging
    print("\n🎯 Deploying to STAGING...")
    lambda_version = deploy_lambda('staging')
    deploy_frontend('staging')
    
    print("\n" + "="*70)
    print("✅ STAGING DEPLOYMENT COMPLETE")
    print("="*70)
    print(f"  Lambda version: {lambda_version}")
    print(f"  Frontend: https://staging.awseuccontent.com")
    print(f"  API: https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging")
    
    # Test staging
    test_staging()
    
    # Ask about production
    print("\n" + "="*70)
    response = input("\n❓ Deploy to PRODUCTION? (yes/no): ").strip().lower()
    
    if response == 'yes':
        print("\n🎯 Deploying to PRODUCTION...")
        lambda_version = deploy_lambda('production')
        deploy_frontend('production')
        
        print("\n" + "="*70)
        print("✅ PRODUCTION DEPLOYMENT COMPLETE")
        print("="*70)
        print(f"  Lambda version: {lambda_version}")
        print(f"  Frontend: https://awseuccontent.com")
        print(f"  API: https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod")
        print("\n  ⏳ Wait 5-15 minutes for CloudFront cache to clear")
    else:
        print("\n⏸️  Production deployment skipped")
        print("   Run this script again when ready to deploy to production")
    
    print("\n" + "="*70)
    print("🎉 DEPLOYMENT COMPLETE")
    print("="*70)

if __name__ == '__main__':
    main()
