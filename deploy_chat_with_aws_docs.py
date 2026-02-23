"""
Deploy Chat Lambda with AWS Docs Integration to Staging
"""

import boto3
import zipfile
import os
import time

# AWS clients
lambda_client = boto3.client('lambda', region_name='us-east-1')

# Lambda configuration
LAMBDA_NAME = 'aws-blog-chat-assistant'
LAMBDA_FILE = 'chat_lambda_with_aws_docs.py'
ZIP_FILE = 'chat_lambda_with_aws_docs.zip'

def create_deployment_package():
    """Create Lambda deployment package with service mapper"""
    print(f"Creating deployment package: {ZIP_FILE}")
    
    # Files to include in deployment package
    required_files = [
        ('chat_lambda_with_aws_docs.py', 'lambda_function.py'),  # Rename to lambda_function.py
        ('euc_service_mapper.py', 'euc_service_mapper.py'),
        ('euc-service-name-mapping.json', 'euc-service-name-mapping.json')
    ]
    
    # Verify all source files exist before creating zip
    missing_files = []
    for source_file, _ in required_files:
        if not os.path.exists(source_file):
            missing_files.append(source_file)
    
    if missing_files:
        raise FileNotFoundError(
            f"Required files missing: {', '.join(missing_files)}\n"
            f"Cannot create deployment package without all required files."
        )
    
    print(f"✓ All required files found")
    
    with zipfile.ZipFile(ZIP_FILE, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for source_file, archive_name in required_files:
            zipf.write(source_file, archive_name)
            print(f"  Added: {source_file} -> {archive_name}")
    
    print(f"✓ Created {ZIP_FILE}")
    return ZIP_FILE


def deploy_to_lambda():
    """Deploy to Lambda function"""
    print(f"\nDeploying to Lambda: {LAMBDA_NAME}")
    
    # Read zip file
    with open(ZIP_FILE, 'rb') as f:
        zip_content = f.read()
    
    try:
        # Update Lambda function code
        response = lambda_client.update_function_code(
            FunctionName=LAMBDA_NAME,
            ZipFile=zip_content,
            Publish=False  # Don't publish version yet
        )
        
        print(f"✓ Updated Lambda function code")
        print(f"  Function ARN: {response['FunctionArn']}")
        print(f"  Last Modified: {response['LastModified']}")
        print(f"  Code Size: {response['CodeSize']} bytes")
        
        # Wait for update to complete
        print("\nWaiting for Lambda update to complete...")
        waiter = lambda_client.get_waiter('function_updated')
        waiter.wait(FunctionName=LAMBDA_NAME)
        print("✓ Lambda update complete")
        
        return True
        
    except Exception as e:
        print(f"✗ Error deploying to Lambda: {str(e)}")
        return False


def update_staging_alias():
    """Update staging alias to point to $LATEST"""
    print("\nUpdating staging alias...")
    
    try:
        # Get current function version
        response = lambda_client.get_function(FunctionName=LAMBDA_NAME)
        version = response['Configuration']['Version']
        
        print(f"Current version: {version}")
        
        # Update staging alias to point to $LATEST
        try:
            lambda_client.update_alias(
                FunctionName=LAMBDA_NAME,
                Name='staging',
                FunctionVersion='$LATEST',
                Description='Staging environment with AWS docs integration'
            )
            print("✓ Updated staging alias to $LATEST")
        except lambda_client.exceptions.ResourceNotFoundException:
            # Create alias if it doesn't exist
            lambda_client.create_alias(
                FunctionName=LAMBDA_NAME,
                Name='staging',
                FunctionVersion='$LATEST',
                Description='Staging environment with AWS docs integration'
            )
            print("✓ Created staging alias pointing to $LATEST")
        
        return True
        
    except Exception as e:
        print(f"✗ Error updating staging alias: {str(e)}")
        return False


def verify_deployment():
    """Verify the deployment"""
    print("\nVerifying deployment...")
    
    try:
        # Get function configuration
        response = lambda_client.get_function(FunctionName=LAMBDA_NAME)
        config = response['Configuration']
        
        print(f"✓ Function Name: {config['FunctionName']}")
        print(f"✓ Runtime: {config['Runtime']}")
        print(f"✓ Handler: {config['Handler']}")
        print(f"✓ Memory: {config['MemorySize']} MB")
        print(f"✓ Timeout: {config['Timeout']} seconds")
        print(f"✓ Last Modified: {config['LastModified']}")
        
        # Check environment variables
        env_vars = config.get('Environment', {}).get('Variables', {})
        table_name = env_vars.get('DYNAMODB_TABLE_NAME', 'Not set')
        print(f"✓ DynamoDB Table: {table_name}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error verifying deployment: {str(e)}")
        return False


def cleanup():
    """Clean up temporary files"""
    print("\nCleaning up...")
    
    if os.path.exists(ZIP_FILE):
        os.remove(ZIP_FILE)
        print(f"✓ Removed {ZIP_FILE}")


def main():
    """Main deployment flow"""
    print("=" * 60)
    print("DEPLOYING CHAT LAMBDA WITH AWS DOCS INTEGRATION")
    print("=" * 60)
    
    try:
        # Step 1: Create deployment package
        create_deployment_package()
        
        # Step 2: Deploy to Lambda
        if not deploy_to_lambda():
            print("\n✗ Deployment failed!")
            return
        
        # Step 3: Update staging alias
        if not update_staging_alias():
            print("\n⚠ Warning: Failed to update staging alias")
        
        # Step 4: Verify deployment
        verify_deployment()
        
        print("\n" + "=" * 60)
        print("✓ DEPLOYMENT COMPLETE!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Test the staging endpoint:")
        print("   python test_chat_with_aws_docs.py")
        print("\n2. Test on staging website:")
        print("   https://staging.awseuccontent.com")
        print("\n3. If tests pass, deploy to production:")
        print("   python deploy_chat_production.py")
        
    except Exception as e:
        print(f"\n✗ Deployment failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        cleanup()


if __name__ == '__main__':
    main()
