import boto3
import json

iam = boto3.client('iam', region_name='us-east-1')

print("=" * 60)
print("Adding Selenium Crawler Invoke Permission")
print("=" * 60)

# Get the sitemap crawler's role name
lambda_client = boto3.client('lambda', region_name='us-east-1')
response = lambda_client.get_function(FunctionName='aws-blog-crawler')
role_arn = response['Configuration']['Role']
role_name = role_arn.split('/')[-1]

print(f"\n1. Sitemap crawler role: {role_name}")

# Create policy to allow invoking Selenium crawler
policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "lambda:InvokeFunction",
            "Resource": "arn:aws:lambda:us-east-1:031421429609:function:aws-blog-builder-selenium-crawler"
        }
    ]
}

policy_name = "InvokeSeleniumCrawlerPolicy"

print(f"\n2. Creating/updating inline policy: {policy_name}")

try:
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_document)
    )
    print(f"✓ Policy added successfully")
    print(f"\nPolicy allows:")
    print(f"  - Action: lambda:InvokeFunction")
    print(f"  - Resource: aws-blog-builder-selenium-crawler")
    
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "=" * 60)
print("Permission fix complete!")
print("=" * 60)
