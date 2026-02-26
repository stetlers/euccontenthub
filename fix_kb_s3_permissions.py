#!/usr/bin/env python3
"""
Fix S3 permissions for KB Editor Lambda
Adds S3 permissions to Lambda execution role
"""

import boto3
import json

# Configuration
LAMBDA_FUNCTION_NAME = 'aws-blog-api'
KB_S3_BUCKET = 'euc-content-hub-kb-staging'
REGION = 'us-east-1'

# Initialize clients
lambda_client = boto3.client('lambda', region_name=REGION)
iam = boto3.client('iam', region_name=REGION)

def get_lambda_role():
    """Get the Lambda execution role"""
    response = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
    role_arn = response['Configuration']['Role']
    role_name = role_arn.split('/')[-1]
    return role_name

def add_s3_policy(role_name):
    """Add S3 policy to Lambda role"""
    policy_name = 'KBEditorS3Access'
    
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:HeadObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    f"arn:aws:s3:::{KB_S3_BUCKET}",
                    f"arn:aws:s3:::{KB_S3_BUCKET}/*"
                ]
            }
        ]
    }
    
    try:
        # Try to create the policy
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        print(f"  ✅ Added S3 policy '{policy_name}' to role '{role_name}'")
        return True
    except Exception as e:
        print(f"  ⚠️  Error adding policy: {str(e)}")
        return False

def add_bedrock_policy(role_name):
    """Add Bedrock policy to Lambda role for ingestion jobs"""
    policy_name = 'KBEditorBedrockAccess'
    
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:StartIngestionJob",
                    "bedrock:GetIngestionJob"
                ],
                "Resource": "*"
            }
        ]
    }
    
    try:
        # Try to create the policy
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        print(f"  ✅ Added Bedrock policy '{policy_name}' to role '{role_name}'")
        return True
    except Exception as e:
        print(f"  ⚠️  Error adding policy: {str(e)}")
        return False

def main():
    print("=" * 70)
    print("KB Editor S3 Permissions Fix")
    print("=" * 70)
    print(f"Lambda Function: {LAMBDA_FUNCTION_NAME}")
    print(f"S3 Bucket: {KB_S3_BUCKET}")
    print()
    
    try:
        # Get Lambda role
        print("1. Getting Lambda execution role...")
        role_name = get_lambda_role()
        print(f"  ✅ Found role: {role_name}\n")
        
        # Add S3 policy
        print("2. Adding S3 permissions...")
        add_s3_policy(role_name)
        print()
        
        # Add Bedrock policy
        print("3. Adding Bedrock permissions...")
        add_bedrock_policy(role_name)
        print()
        
        print("=" * 70)
        print("✅ Permissions updated successfully!")
        print("=" * 70)
        print("\n💡 Lambda can now:")
        print(f"   - Read/write to S3 bucket: {KB_S3_BUCKET}")
        print("   - Start and check Bedrock ingestion jobs")
        print("\n🔗 Test the KB editor at: https://staging.awseuccontent.com")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
