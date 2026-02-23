"""
Deploy crawler Lambda with staging environment support
"""

import boto3
import zipfile
import os

lambda_client = boto3.client('lambda', region_name='us-east-1')

def deploy_crawler():
    """Deploy crawler Lambda"""
    print("="*60)
    print("DEPLOYING CRAWLER LAMBDA")
    print("="*60)
    
    # Create deployment package
    zip_file = 'enhanced_crawler_lambda.zip'
    
    print(f"\n1. Creating deployment package: {zip_file}")
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write('enhanced_crawler_lambda.py', 'lambda_function.py')
    print(f"   ✓ Created {zip_file}")
    
    # Deploy to Lambda
    print(f"\n2. Deploying to Lambda: aws-blog-crawler")
    with open(zip_file, 'rb') as f:
        zip_content = f.read()
    
    response = lambda_client.update_function_code(
        FunctionName='aws-blog-crawler',
        ZipFile=zip_content,
        Publish=False
    )
    
    print(f"   ✓ Updated Lambda function code")
    print(f"   Function ARN: {response['FunctionArn']}")
    print(f"   Last Modified: {response['LastModified']}")
    
    # Wait for update to complete
    print(f"\n3. Waiting for Lambda update to complete...")
    waiter = lambda_client.get_waiter('function_updated')
    waiter.wait(FunctionName='aws-blog-crawler')
    print(f"   ✓ Lambda update complete")
    
    # Clean up
    os.remove(zip_file)
    print(f"\n4. Cleaned up {zip_file}")
    
    print(f"\n{'='*60}")
    print("✓ CRAWLER DEPLOYMENT COMPLETE")
    print(f"{'='*60}")


def deploy_api_lambda():
    """Deploy API Lambda"""
    print("\n" + "="*60)
    print("DEPLOYING API LAMBDA")
    print("="*60)
    
    # Create deployment package
    zip_file = 'api_lambda.zip'
    
    print(f"\n1. Creating deployment package: {zip_file}")
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write('lambda_api/lambda_function.py', 'lambda_function.py')
    print(f"   ✓ Created {zip_file}")
    
    # Deploy to Lambda
    print(f"\n2. Deploying to Lambda: aws-blog-api")
    with open(zip_file, 'rb') as f:
        zip_content = f.read()
    
    response = lambda_client.update_function_code(
        FunctionName='aws-blog-api',
        ZipFile=zip_content,
        Publish=False
    )
    
    print(f"   ✓ Updated Lambda function code")
    print(f"   Function ARN: {response['FunctionArn']}")
    print(f"   Last Modified: {response['LastModified']}")
    
    # Wait for update to complete
    print(f"\n3. Waiting for Lambda update to complete...")
    waiter = lambda_client.get_waiter('function_updated')
    waiter.wait(FunctionName='aws-blog-api')
    print(f"   ✓ Lambda update complete")
    
    # Clean up
    os.remove(zip_file)
    print(f"\n4. Cleaned up {zip_file}")
    
    print(f"\n{'='*60}")
    print("✓ API LAMBDA DEPLOYMENT COMPLETE")
    print(f"{'='*60}")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("STAGING CRAWLER FIX DEPLOYMENT")
    print("="*60)
    print("\nThis will deploy:")
    print("1. Crawler Lambda - with environment detection from event payload")
    print("2. API Lambda - passes environment to crawler")
    print()
    
    try:
        # Deploy crawler first
        deploy_crawler()
        
        # Deploy API Lambda
        deploy_api_lambda()
        
        print("\n" + "="*60)
        print("✓ ALL DEPLOYMENTS COMPLETE")
        print("="*60)
        print("\nNext steps:")
        print("1. Test staging crawler:")
        print("   - Visit https://staging.awseuccontent.com")
        print("   - Click 'Crawl for New Posts' button")
        print("   - Check CloudWatch logs for 'Environment: staging'")
        print("   - Verify posts are added to aws-blog-posts-staging table")
        print()
        print("2. Verify staging isolation:")
        print("   python check_staging_vs_production.py")
        
    except Exception as e:
        print(f"\n✗ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
