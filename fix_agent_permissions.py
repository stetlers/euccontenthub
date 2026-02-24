#!/usr/bin/env python3
"""
Fix Agent IAM Permissions

Update the agent role to allow invoking Claude 3 Sonnet model.
"""

import boto3
import json

# Load configuration
with open('kb-config-staging.json') as f:
    config = json.load(f)

REGION = config['region']
ACCOUNT_ID = config['account_id']
KB_ID = config['knowledge_base_id']

# Initialize IAM client
iam = boto3.client('iam', region_name=REGION)

role_name = 'BedrockAgentRole-staging'
policy_name = 'BedrockAgentPolicy-staging'

# Updated permissions policy with both models
permissions_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": [
                f"arn:aws:bedrock:{REGION}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
                f"arn:aws:bedrock:{REGION}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:Retrieve"
            ],
            "Resource": [
                f"arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:knowledge-base/{KB_ID}"
            ]
        }
    ]
}

print(f"Updating IAM policy for role: {role_name}")

try:
    # Update inline policy
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName=policy_name,
        PolicyDocument=json.dumps(permissions_policy)
    )
    
    print(f"\nPolicy updated successfully!")
    print(f"  Role: {role_name}")
    print(f"  Policy: {policy_name}")
    print(f"\nAllowed models:")
    print(f"  - Claude 3 Sonnet")
    print(f"  - Claude 3.5 Sonnet v2")
    
    print(f"\nWait 10 seconds for IAM to propagate, then test: python test_agent_simple.py")
    
except Exception as e:
    print(f"\nError: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)
