#!/usr/bin/env python3
"""
Lambda Deployment Script for EUC Content Hub
Deploys Lambda functions to staging or production environment

Usage:
    python deploy_lambda.py <function_name> staging     # Deploy to staging
    python deploy_lambda.py <function_name> production  # Deploy to production

Examples:
    python deploy_lambda.py api_lambda staging
    python deploy_lambda.py api_lambda production
"""

import boto3
import sys
import zipfile
import os
import time
from datetime import datetime
from pathlib import Path

# Lambda function configurations
LAMBDA_FUNCTIONS = {
    'api_lambda': {
        'function_name': 'aws-blog-api',
        'source_file': 'lambda_api/lambda_function.py',
        'handler': 'lambda_function.lambda_handler',
        'description': 'API Lambda for blog posts viewer'
    },
    'crawler': {
        'function_name': 'aws-blog-crawler',
        'source_file': 'enhanced_crawler_lambda.py',
        'handler': 'lambda_function.lambda_handler',
        'description': 'AWS Blog crawler'
    },
    'builder_crawler': {
        'function_name': 'aws-blog-builder-selenium-crawler',
        'source_file': 'builder_selenium_crawler.py',
        'handler': 'lambda_function.lambda_handler',
        'description': 'Builder.AWS Selenium crawler'
    },
    'summary': {
        'function_name': 'aws-blog-summary-generator',
        'source_file': 'summary_lambda.py',
        'handler': 'lambda_function.lambda_handler',
        'description': 'AI summary generator'
    },
    'classifier': {
        'function_name': 'aws-blog-classifier',
        'source_file': 'classifier_lambda.py',
        'handler': 'lambda_function.lambda_handler',
        'description': 'Content classifier'
    },
    'chat': {
        'function_name': 'aws-blog-chat-assistant',
        'source_file': 'chat_lambda.py',
        'handler': 'lambda_function.lambda_handler',
        'description': 'AI chat assistant'
    }
}

def create_deployment_package(source_file, output_zip):
    """Create Lambda deployment package"""
    
    if not os.path.exists(source_file):
        print(f"❌ Error: Source file not found: {source_file}")
        return False
    
    try:
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add the source file as lambda_function.py (Lambda expects this name)
            zf.write(source_file, 'lambda_function.py')
        
        return True
    
    except Exception as e:
        print(f"❌ Error creating deployment package: {str(e)}")
        return False

def deploy_lambda(function_key, environment):
    """Deploy Lambda function to specified environment"""
    
    if function_key not in LAMBDA_FUNCTIONS:
        print(f"❌ Error: Unknown function '{function_key}'")
        print(f"   Valid functions: {', '.join(LAMBDA_FUNCTIONS.keys())}")
        sys.exit(1)
    
    if environment not in ['staging', 'production']:
        print(f"❌ Error: Unknown environment '{environment}'")
        print(f"   Valid environments: staging, production")
        sys.exit(1)
    
    config = LAMBDA_FUNCTIONS[function_key]
    function_name = config['function_name']
    source_file = config['source_file']
    description = config['description']
    
    print("=" * 70)
    print(f"Lambda Deployment: {function_name}")
    print("=" * 70)
    print(f"Environment: {environment.upper()}")
    print(f"Function: {function_name}")
    print(f"Source: {source_file}")
    print(f"Description: {description}")
    print()
    
    # Initialize AWS client
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create deployment package
    zip_file = f'{function_key}_deployment.zip'
    print(f"📦 Creating deployment package...")
    
    if not create_deployment_package(source_file, zip_file):
        sys.exit(1)
    
    print(f"  ✅ Package created: {zip_file}")
    
    # Upload to Lambda
    print(f"\n📤 Uploading to Lambda...")
    try:
        with open(zip_file, 'rb') as f:
            zip_content = f.read()
        
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        print(f"  ✅ Code uploaded successfully")
        print(f"  📝 Code SHA256: {response['CodeSha256'][:16]}...")
        
    except Exception as e:
        print(f"  ❌ Error uploading code: {str(e)}")
        os.remove(zip_file)
        sys.exit(1)
    
    # Wait for update to complete
    print(f"\n⏳ Waiting for Lambda update to complete...")
    try:
        waiter = lambda_client.get_waiter('function_updated')
        waiter.wait(FunctionName=function_name)
        print(f"  ✅ Lambda update complete")
    except Exception as e:
        print(f"  ⚠️  Warning: Could not verify update completion: {str(e)}")
    
    # Handle environment-specific deployment
    if environment == 'staging':
        print(f"\n🔧 Staging deployment (using $LATEST)")
        print(f"  ℹ️  Staging alias points to $LATEST")
        print(f"  ℹ️  Changes are immediately available in staging")
        
    else:  # production
        print(f"\n🔧 Production deployment")
        print(f"  📌 Publishing new version...")
        
        try:
            version_response = lambda_client.publish_version(
                FunctionName=function_name,
                Description=f"Production deployment {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            new_version = version_response['Version']
            print(f"  ✅ Published version: {new_version}")
            
            # Update production alias
            print(f"  🔄 Updating production alias...")
            lambda_client.update_alias(
                FunctionName=function_name,
                Name='production',
                FunctionVersion=new_version
            )
            print(f"  ✅ Production alias updated to version {new_version}")
            
        except Exception as e:
            print(f"  ❌ Error publishing version: {str(e)}")
            os.remove(zip_file)
            sys.exit(1)
    
    # Clean up
    os.remove(zip_file)
    print(f"\n🧹 Cleaned up deployment package")
    
    # Summary
    print()
    print("=" * 70)
    print(f"✅ Deployment to {environment.upper()} complete!")
    print("=" * 70)
    
    if environment == 'staging':
        print(f"🔗 Test staging API: https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging")
        print()
        print("💡 Next steps:")
        print("   1. Test the staging API thoroughly")
        print("   2. Check CloudWatch logs for any errors")
        print("   3. If everything works, deploy to production:")
        print(f"      python deploy_lambda.py {function_key} production")
    else:
        print(f"🔗 Production API: https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod")
        print()
        print("💡 Deployment complete!")
        print("   Monitor CloudWatch logs for any issues")
        print()
        print("🔄 Rollback if needed:")
        print(f"   aws lambda update-alias --function-name {function_name} \\")
        print(f"       --name production --function-version <previous-version>")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python deploy_lambda.py <function> <environment>")
        print()
        print("Functions:")
        for key, config in LAMBDA_FUNCTIONS.items():
            print(f"  {key:20} - {config['description']}")
        print()
        print("Environments: staging, production")
        sys.exit(1)
    
    function_key = sys.argv[1].lower()
    environment = sys.argv[2].lower()
    
    deploy_lambda(function_key, environment)
