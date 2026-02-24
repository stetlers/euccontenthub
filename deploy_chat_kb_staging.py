#!/usr/bin/env python3
"""
Deploy Chat Lambda with KB Integration - Staging

This script deploys the new chat Lambda that uses Bedrock Agent + Knowledge Base.
"""

import boto3
import json
import zipfile
import os
import time
from datetime import datetime

# Load configuration
with open('kb-config-staging.json') as f:
    config = json.load(f)

REGION = config['region']
ACCOUNT_ID = config['account_id']
AGENT_ID = config['agent_id']
AGENT_ALIAS_ID = config['agent_alias_id']
ENVIRONMENT = 'staging'

# Lambda configuration
LAMBDA_NAME = f'euc-chat-kb-{ENVIRONMENT}'
LAMBDA_ROLE_NAME = f'EUCChatKBLambdaRole-{ENVIRONMENT}'

# Initialize AWS clients
lambda_client = boto3.client('lambda', region_name=REGION)
iam = boto3.client('iam', region_name=REGION)

def print_step(step_num, description):
    """Print formatted step header"""
    print(f"\n{'='*80}")
    print(f"STEP {step_num}: {description}")
    print(f"{'='*80}\n")

def create_lambda_role():
    """Create IAM role for Lambda"""
    print_step(1, "Creating IAM Role for Lambda")
    
    # Trust policy
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Permissions policy
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": f"arn:aws:logs:{REGION}:{ACCOUNT_ID}:*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeAgent"
                ],
                "Resource": [
                    f"arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:agent-alias/{AGENT_ID}/{AGENT_ALIAS_ID}"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:Scan",
                    "dynamodb:Query"
                ],
                "Resource": [
                    f"arn:aws:dynamodb:{REGION}:{ACCOUNT_ID}:table/aws-blog-posts-staging"
                ]
            }
        ]
    }
    
    try:
        # Check if role exists
        try:
            role = iam.get_role(RoleName=LAMBDA_ROLE_NAME)
            print(f"✓ Role {LAMBDA_ROLE_NAME} already exists")
            role_arn = role['Role']['Arn']
        except iam.exceptions.NoSuchEntityException:
            # Create role
            role = iam.create_role(
                RoleName=LAMBDA_ROLE_NAME,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f'Role for Chat Lambda with KB - {ENVIRONMENT}',
                Tags=[
                    {'Key': 'Environment', 'Value': ENVIRONMENT},
                    {'Key': 'Project', 'Value': 'EUC-Content-Hub'}
                ]
            )
            role_arn = role['Role']['Arn']
            print(f"✓ Created role: {LAMBDA_ROLE_NAME}")
        
        # Attach inline policy
        policy_name = f'ChatKBLambdaPolicy-{ENVIRONMENT}'
        iam.put_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(permissions_policy)
        )
        print(f"✓ Attached policy: {policy_name}")
        
        return role_arn
        
    except Exception as e:
        print(f"✗ Error creating IAM role: {str(e)}")
        raise

def create_deployment_package():
    """Create Lambda deployment package"""
    print_step(2, "Creating Deployment Package")
    
    zip_file = 'chat_lambda_kb_staging.zip'
    
    try:
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write('chat_lambda_kb_staging.py', 'lambda_function.py')
        
        print(f"✓ Created deployment package: {zip_file}")
        
        # Get file size
        size_mb = os.path.getsize(zip_file) / (1024 * 1024)
        print(f"  Package size: {size_mb:.2f} MB")
        
        return zip_file
        
    except Exception as e:
        print(f"✗ Error creating deployment package: {str(e)}")
        raise

def deploy_lambda(role_arn, zip_file):
    """Deploy or update Lambda function"""
    print_step(3, "Deploying Lambda Function")
    
    # Read deployment package
    with open(zip_file, 'rb') as f:
        zip_content = f.read()
    
    # Environment variables (AWS_REGION is provided automatically by Lambda)
    environment = {
        'Variables': {
            'AGENT_ID': AGENT_ID,
            'AGENT_ALIAS_ID': AGENT_ALIAS_ID,
            'DYNAMODB_TABLE': 'aws-blog-posts-staging'
        }
    }
    
    try:
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName=LAMBDA_NAME)
            function_exists = True
            print(f"Function {LAMBDA_NAME} exists, updating...")
        except lambda_client.exceptions.ResourceNotFoundException:
            function_exists = False
            print(f"Function {LAMBDA_NAME} does not exist, creating...")
        
        if function_exists:
            # Update function code
            lambda_client.update_function_code(
                FunctionName=LAMBDA_NAME,
                ZipFile=zip_content
            )
            print(f"✓ Updated function code")
            
            # Wait for update to complete
            time.sleep(2)
            
            # Update function configuration
            lambda_client.update_function_configuration(
                FunctionName=LAMBDA_NAME,
                Environment=environment,
                Timeout=30,
                MemorySize=512
            )
            print(f"✓ Updated function configuration")
            
        else:
            # Create function
            response = lambda_client.create_function(
                FunctionName=LAMBDA_NAME,
                Runtime='python3.11',
                Role=role_arn,
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_content},
                Description=f'Chat Lambda with Bedrock KB integration - {ENVIRONMENT}',
                Timeout=30,
                MemorySize=512,
                Environment=environment,
                Tags={
                    'Environment': ENVIRONMENT,
                    'Project': 'EUC-Content-Hub'
                }
            )
            print(f"✓ Created function: {LAMBDA_NAME}")
            print(f"  Function ARN: {response['FunctionArn']}")
        
        # Get function info
        function_info = lambda_client.get_function(FunctionName=LAMBDA_NAME)
        function_arn = function_info['Configuration']['FunctionArn']
        
        return function_arn
        
    except Exception as e:
        print(f"✗ Error deploying Lambda: {str(e)}")
        raise

def skip_function_url():
    """Skip function URL creation (not allowed by company policy)"""
    print_step(4, "Skipping Function URL Creation")
    
    print("⚠️  Function URLs with public access are not allowed by company policy")
    print("✓ Lambda will be accessed via API Gateway instead")
    print("✓ This is more secure and follows best practices")
    
    return None

def main():
    """Main deployment function"""
    print(f"\n{'#'*80}")
    print(f"# Chat Lambda KB Deployment - {ENVIRONMENT.upper()}")
    print(f"# Region: {REGION}")
    print(f"# Account: {ACCOUNT_ID}")
    print(f"# Agent ID: {AGENT_ID}")
    print(f"# Timestamp: {datetime.now().isoformat()}")
    print(f"{'#'*80}\n")
    
    try:
        # Step 1: Create IAM role
        role_arn = create_lambda_role()
        
        # Wait for IAM role to propagate
        print("\nWaiting 10 seconds for IAM role to propagate...")
        time.sleep(10)
        
        # Step 2: Create deployment package
        zip_file = create_deployment_package()
        
        # Step 3: Deploy Lambda
        function_arn = deploy_lambda(role_arn, zip_file)
        
        # Step 4: Skip function URL (not allowed by company policy)
        skip_function_url()
        
        # Summary
        print(f"\n{'='*80}")
        print("DEPLOYMENT COMPLETE!")
        print(f"{'='*80}\n")
        
        print("Resources Created:")
        print(f"  IAM Role: {role_arn}")
        print(f"  Lambda Function: {LAMBDA_NAME}")
        print(f"  Function ARN: {function_arn}")
        
        print("\nNext Steps:")
        print("  1. Setup API Gateway: python setup_api_gateway_chat_staging.py")
        print("  2. Test Lambda: python test_chat_lambda_direct.py")
        print("  3. Test API Gateway: python test_api_gateway_chat.py")
        
        # Update configuration
        config['chat_lambda_name'] = LAMBDA_NAME
        config['chat_lambda_arn'] = function_arn
        config['chat_lambda_deployed_at'] = datetime.now().isoformat()
        
        with open('kb-config-staging.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n✓ Configuration updated: kb-config-staging.json")
        
        # Clean up
        if os.path.exists(zip_file):
            os.remove(zip_file)
            print(f"✓ Cleaned up deployment package")
        
    except Exception as e:
        print(f"\n{'='*80}")
        print("DEPLOYMENT FAILED!")
        print(f"{'='*80}\n")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
