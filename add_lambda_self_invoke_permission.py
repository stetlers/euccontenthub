"""
Add IAM permission for summary generator Lambda to invoke itself (for auto-chaining)
"""
import boto3
import json

iam_client = boto3.client('iam')
role_name = 'aws-blog-summary-lambda-role'

print("\n" + "="*80)
print("Adding Self-Invoke Permission to Summary Generator Lambda")
print("="*80)

# Create inline policy to allow Lambda to invoke itself
policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "lambda:InvokeFunction",
            "Resource": [
                "arn:aws:lambda:us-east-1:031421429609:function:aws-blog-summary-generator",
                "arn:aws:lambda:us-east-1:031421429609:function:aws-blog-summary-generator:*"
            ]
        }
    ]
}

policy_name = 'SummaryGeneratorSelfInvoke'

print(f"\n1. Creating inline policy: {policy_name}")
print(f"   Role: {role_name}")
print(f"   Allows: lambda:InvokeFunction on self and aliases")

try:
    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_document)
    )
    print(f"   ✓ Policy created successfully")
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

print("\n" + "="*80)
print("✅ Permission Added Successfully!")
print("="*80)
print("\nThe summary generator Lambda can now invoke itself for auto-chaining.")
print("This enables automatic processing of all posts without manual intervention.")
