"""
Check classifier Lambda IAM permissions
"""
import boto3
import json
from urllib.parse import unquote

iam = boto3.client('iam')

role_name = 'aws-blog-classifier-lambda-role'

print(f"Checking permissions for: {role_name}")
print("=" * 80)

# Get inline policies
response = iam.list_role_policies(RoleName=role_name)
print(f"\nInline policies: {response['PolicyNames']}\n")

# Check StagingTableAccessPolicy
if 'StagingTableAccessPolicy' in response['PolicyNames']:
    policy = iam.get_role_policy(
        RoleName=role_name,
        PolicyName='StagingTableAccessPolicy'
    )
    
    # URL decode the policy document
    policy_doc = unquote(policy['PolicyDocument']) if isinstance(policy['PolicyDocument'], str) else policy['PolicyDocument']
    
    print("StagingTableAccessPolicy:")
    print("-" * 80)
    print(json.dumps(policy_doc, indent=2))
