#!/usr/bin/env python3
"""
Deploy Use Case Matcher Integration
Deploys updated chat Lambda with use case matching capabilities
"""

import boto3
import zipfile
import os
import sys
from pathlib import Path

def create_deployment_package():
    """Create deployment package with use case matcher"""
    print("Creating deployment package...")
    
    # Files to include
    files = [
        'chat_lambda_with_aws_docs.py',
        'euc_service_mapper.py',
        'euc-service-name-mapping.json',
        'euc_use_case_matcher.py',
        'euc-use-case-matcher.json'
    ]
    
    # Create zip file
    zip_path = 'chat_lambda_use_case_matcher.zip'
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add lambda_function.py (renamed from chat_lambda_with_aws_docs.py)
        zipf.write('chat_lambda_with_aws_docs.py', 'lambda_function.py')
        print(f"  ✅ Added lambda_function.py")
        
        # Add service mapper files
        zipf.write('euc_service_mapper.py', 'euc_service_mapper.py')
        print(f"  ✅ Added euc_service_mapper.py")
        
        zipf.write('euc-service-name-mapping.json', 'euc-service-name-mapping.json')
        print(f"  ✅ Added euc-service-name-mapping.json")
        
        # Add use case matcher files
        zipf.write('euc_use_case_matcher.py', 'euc_use_case_matcher.py')
        print(f"  ✅ Added euc_use_case_matcher.py")
        
        zipf.write('euc-use-case-matcher.json', 'euc-use-case-matcher.json')
        print(f"  ✅ Added euc-use-case-matcher.json")
    
    print(f"\n✅ Created {zip_path}")
    return zip_path

def deploy_to_lambda(zip_path, environment='staging'):
    """Deploy to Lambda function"""
    print(f"\nDeploying to {environment}...")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    function_name = 'aws-blog-chat-assistant'
    
    # Read zip file
    with open(zip_path, 'rb') as f:
        zip_content = f.read()
    
    # Update function code
    print(f"  Updating Lambda function code...")
    response = lambda_client.update_function_code(
        FunctionName=function_name,
        ZipFile=zip_content,
        Publish=True  # Create new version
    )
    
    new_version = response['Version']
    print(f"  ✅ Created version {new_version}")
    
    # Update alias
    if environment == 'staging':
        alias_name = 'staging'
        print(f"  Updating {alias_name} alias to $LATEST...")
        
        try:
            lambda_client.update_alias(
                FunctionName=function_name,
                Name=alias_name,
                FunctionVersion='$LATEST'
            )
            print(f"  ✅ Updated {alias_name} alias")
        except lambda_client.exceptions.ResourceNotFoundException:
            # Create alias if it doesn't exist
            lambda_client.create_alias(
                FunctionName=function_name,
                Name=alias_name,
                FunctionVersion='$LATEST'
            )
            print(f"  ✅ Created {alias_name} alias")
    
    elif environment == 'production':
        alias_name = 'production'
        print(f"  Updating {alias_name} alias to version {new_version}...")
        
        lambda_client.update_alias(
            FunctionName=function_name,
            Name=alias_name,
            FunctionVersion=new_version
        )
        print(f"  ✅ Updated {alias_name} alias to version {new_version}")
    
    return new_version

def main():
    if len(sys.argv) != 2:
        print("Usage: python deploy_use_case_matcher.py <environment>")
        print("Environments: staging, production")
        sys.exit(1)
    
    environment = sys.argv[1].lower()
    
    if environment not in ['staging', 'production']:
        print(f"❌ Invalid environment: {environment}")
        print("Valid environments: staging, production")
        sys.exit(1)
    
    print("=" * 70)
    print(f"Deploy Use Case Matcher Integration to {environment.upper()}")
    print("=" * 70)
    print()
    
    # Create deployment package
    zip_path = create_deployment_package()
    
    # Deploy to Lambda
    version = deploy_to_lambda(zip_path, environment)
    
    # Cleanup
    os.remove(zip_path)
    print(f"\n🗑️  Cleaned up {zip_path}")
    
    print()
    print("=" * 70)
    print(f"✅ Deployment to {environment.upper()} complete!")
    print("=" * 70)
    print(f"Version: {version}")
    print()
    
    if environment == 'staging':
        print("💡 Next steps:")
        print("   1. Test staging: https://staging.awseuccontent.com")
        print("   2. Ask: 'I need non-persistent desktops for task workers'")
        print("   3. Verify it recommends WorkSpaces Applications")
        print("   4. Ask: 'I have multiple use cases with existing EC2'")
        print("   5. Verify it recommends WorkSpaces Core Managed Instances")
        print("   6. If tests pass, deploy to production:")
        print("      python deploy_use_case_matcher.py production")
    else:
        print("💡 Deployment complete!")
        print("   Test at: https://awseuccontent.com")

if __name__ == '__main__':
    main()
