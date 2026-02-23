"""
Deploy Chat Lambda with AWS Docs Integration + Service Mapper to Production
"""

import boto3
import zipfile
import os
import time

# AWS clients
lambda_client = boto3.client('lambda', region_name='us-east-1')

# Lambda configuration
LAMBDA_NAME = 'aws-blog-chat-assistant'
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
    """Deploy to Lambda function and publish new version"""
    print(f"\nDeploying to Lambda: {LAMBDA_NAME}")
    
    # Read zip file
    with open(ZIP_FILE, 'rb') as f:
        zip_content = f.read()
    
    try:
        # Update Lambda function code and publish new version
        response = lambda_client.update_function_code(
            FunctionName=LAMBDA_NAME,
            ZipFile=zip_content,
            Publish=True  # Publish new version for production
        )
        
        version = response['Version']
        
        print(f"✓ Updated Lambda function code")
        print(f"  Function ARN: {response['FunctionArn']}")
        print(f"  Version: {version}")
        print(f"  Last Modified: {response['LastModified']}")
        print(f"  Code Size: {response['CodeSize']} bytes")
        
        # Wait for update to complete
        print("\nWaiting for Lambda update to complete...")
        waiter = lambda_client.get_waiter('function_updated')
        waiter.wait(FunctionName=LAMBDA_NAME)
        print("✓ Lambda update complete")
        
        return version
        
    except Exception as e:
        print(f"✗ Error deploying to Lambda: {str(e)}")
        return None


def update_production_alias(version):
    """Update production alias to point to new version"""
    print(f"\nUpdating production alias to version {version}...")
    
    try:
        # Get current production alias
        try:
            current_alias = lambda_client.get_alias(
                FunctionName=LAMBDA_NAME,
                Name='production'
            )
            current_version = current_alias['FunctionVersion']
            print(f"Current production version: {current_version}")
        except lambda_client.exceptions.ResourceNotFoundException:
            current_version = None
            print("Production alias does not exist yet")
        
        # Update production alias to point to new version
        try:
            lambda_client.update_alias(
                FunctionName=LAMBDA_NAME,
                Name='production',
                FunctionVersion=version,
                Description=f'Production environment with AWS docs integration and service mapper (deployed {time.strftime("%Y-%m-%d %H:%M:%S")})'
            )
            print(f"✓ Updated production alias to version {version}")
        except lambda_client.exceptions.ResourceNotFoundException:
            # Create alias if it doesn't exist
            lambda_client.create_alias(
                FunctionName=LAMBDA_NAME,
                Name='production',
                FunctionVersion=version,
                Description=f'Production environment with AWS docs integration and service mapper (deployed {time.strftime("%Y-%m-%d %H:%M:%S")})'
            )
            print(f"✓ Created production alias pointing to version {version}")
        
        if current_version:
            print(f"\n⚠ ROLLBACK INFO:")
            print(f"  If issues occur, rollback to version {current_version}:")
            print(f"  aws lambda update-alias --function-name {LAMBDA_NAME} --name production --function-version {current_version}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error updating production alias: {str(e)}")
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
        
        # Get production alias info
        try:
            alias = lambda_client.get_alias(
                FunctionName=LAMBDA_NAME,
                Name='production'
            )
            print(f"✓ Production Alias Version: {alias['FunctionVersion']}")
        except:
            print("⚠ Production alias not found")
        
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
    print("DEPLOYING CHAT LAMBDA TO PRODUCTION")
    print("AWS Docs Integration + Service Mapper")
    print("=" * 60)
    
    # Confirmation prompt
    print("\n⚠ WARNING: This will deploy to PRODUCTION")
    print("Features being deployed:")
    print("  - AWS Documentation Search Integration")
    print("  - EUC Service Name Mapping")
    print("  - Query Expansion with Service Variants")
    print("  - Service Rename Context in AI Responses")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    input()
    
    try:
        # Step 1: Create deployment package
        create_deployment_package()
        
        # Step 2: Deploy to Lambda and get new version
        version = deploy_to_lambda()
        if not version:
            print("\n✗ Deployment failed!")
            return
        
        # Step 3: Update production alias
        if not update_production_alias(version):
            print("\n⚠ Warning: Failed to update production alias")
            print(f"  You can manually update it to version {version}")
        
        # Step 4: Verify deployment
        verify_deployment()
        
        print("\n" + "=" * 60)
        print("✓ PRODUCTION DEPLOYMENT COMPLETE!")
        print("=" * 60)
        print(f"\nDeployed version: {version}")
        print("\nNext steps:")
        print("1. Test the production endpoint:")
        print("   https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod/chat")
        print("\n2. Test on production website:")
        print("   https://awseuccontent.com")
        print("\n3. Monitor CloudWatch logs:")
        print("   /aws/lambda/aws-blog-chat-assistant")
        print("\n4. Test queries:")
        print("   - 'Tell me about AppStream 2.0' (should mention WorkSpaces Applications)")
        print("   - 'How do I use WorkSpaces Web?' (should mention Secure Browser)")
        print("   - 'What is WSP?' (should mention Amazon DCV)")
        
    except KeyboardInterrupt:
        print("\n\n✗ Deployment cancelled by user")
    except Exception as e:
        print(f"\n✗ Deployment failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        cleanup()


if __name__ == '__main__':
    main()
