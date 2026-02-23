"""
Deploy API Lambda with cart endpoints to staging
"""

import boto3
import zipfile
import os
import time

# Configuration
LAMBDA_FUNCTION_NAME = 'aws-blog-api'
REGION = 'us-east-1'
SOURCE_DIR = 'lambda_api'

def create_deployment_package():
    """Create a zip file with the Lambda code"""
    print("Creating deployment package...")
    
    zip_filename = 'api_lambda_deploy.zip'
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add lambda_function.py
        lambda_file = os.path.join(SOURCE_DIR, 'lambda_function.py')
        zipf.write(lambda_file, 'lambda_function.py')
        print(f"  Added: lambda_function.py")
    
    print(f"✅ Created {zip_filename}")
    return zip_filename

def deploy_to_lambda(zip_filename):
    """Deploy the zip file to Lambda"""
    print(f"\nDeploying to Lambda function: {LAMBDA_FUNCTION_NAME}...")
    
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    # Read the zip file
    with open(zip_filename, 'rb') as f:
        zip_content = f.read()
    
    # Update Lambda function code
    response = lambda_client.update_function_code(
        FunctionName=LAMBDA_FUNCTION_NAME,
        ZipFile=zip_content,
        Publish=False  # Update $LATEST (staging uses $LATEST)
    )
    
    print(f"✅ Deployed to Lambda")
    print(f"   Version: {response['Version']}")
    print(f"   Last Modified: {response['LastModified']}")
    print(f"   Code Size: {response['CodeSize']} bytes")
    
    return response

def wait_for_update():
    """Wait for Lambda to finish updating"""
    print("\nWaiting for Lambda to finish updating...")
    
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    max_attempts = 30
    for attempt in range(max_attempts):
        response = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        state = response['Configuration']['State']
        
        if state == 'Active':
            print("✅ Lambda is active and ready")
            return True
        
        print(f"   State: {state} (attempt {attempt + 1}/{max_attempts})")
        time.sleep(2)
    
    print("⚠️  Lambda did not become active within timeout")
    return False

def main():
    """Main deployment function"""
    print("=" * 60)
    print("Deploy Cart API to Staging")
    print("=" * 60)
    
    try:
        # Create deployment package
        zip_filename = create_deployment_package()
        
        # Deploy to Lambda
        deploy_to_lambda(zip_filename)
        
        # Wait for update to complete
        wait_for_update()
        
        print("\n" + "=" * 60)
        print("✅ DEPLOYMENT COMPLETE")
        print("=" * 60)
        print("\nStaging API endpoint:")
        print("https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging")
        print("\nNew cart endpoints:")
        print("  GET    /cart              - Get user's cart")
        print("  POST   /cart              - Add post to cart")
        print("  DELETE /cart/{post_id}    - Remove post from cart")
        print("  DELETE /cart              - Clear all cart items")
        print("\nNext steps:")
        print("1. Run: python test_cart_endpoints.py")
        print("2. Sign in to staging.awseuccontent.com to get JWT token")
        print("3. Test all cart endpoints")
        
    except Exception as e:
        print(f"\n❌ DEPLOYMENT FAILED: {e}")
        raise

if __name__ == "__main__":
    main()
