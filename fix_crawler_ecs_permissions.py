"""
Add ECS RunTask permission to crawler Lambda role
"""
import boto3
import json

iam_client = boto3.client('iam')

# The crawler Lambda role
role_name = 'aws-blog-crawler-stack-LambdaExecutionRole-H6gEnf8SFwwd'

# Policy to allow running ECS tasks
policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecs:RunTask",
                "ecs:DescribeTasks"
            ],
            "Resource": [
                "arn:aws:ecs:us-east-1:031421429609:task-definition/selenium-crawler-task:*",
                "arn:aws:ecs:us-east-1:031421429609:task/selenium-crawler-cluster/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": [
                "arn:aws:iam::031421429609:role/selenium-crawler-task-execution-role",
                "arn:aws:iam::031421429609:role/selenium-crawler-task-role"
            ]
        }
    ]
}

policy_name = "ECSSeleniumCrawlerInvokePolicy"

print("=" * 80)
print("Adding ECS Permissions to Crawler Lambda Role")
print("=" * 80)
print(f"Role: {role_name}")
print(f"Policy: {policy_name}")
print()

try:
    # Try to create the policy (will fail if it already exists)
    try:
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        print("✅ Policy created successfully!")
    except iam_client.exceptions.NoSuchEntityException:
        print(f"❌ Role {role_name} not found")
        exit(1)
    
    print("\nPermissions granted:")
    print("  • ecs:RunTask - Start ECS tasks")
    print("  • ecs:DescribeTasks - Check task status")
    print("  • iam:PassRole - Pass execution roles to ECS")
    print()
    print("The crawler Lambda can now invoke ECS tasks!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
