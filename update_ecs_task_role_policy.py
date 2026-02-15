"""
Update ECS Task Role Policy for Production Deployment

Ensures the builder-crawler-task-role has permissions to:
1. Access both staging and production DynamoDB tables
2. Invoke both staging and production summary generator Lambda aliases
3. Write CloudWatch logs
"""

import json
import boto3

iam = boto3.client('iam')

policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": [
                "arn:aws:dynamodb:us-east-1:031421429609:table/aws-blog-posts",
                "arn:aws:dynamodb:us-east-1:031421429609:table/aws-blog-posts-staging"
            ]
        },
        {
            "Effect": "Allow",
            "Action": "lambda:InvokeFunction",
            "Resource": [
                "arn:aws:lambda:us-east-1:031421429609:function:aws-blog-summary-generator:production",
                "arn:aws:lambda:us-east-1:031421429609:function:aws-blog-summary-generator:staging"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:us-east-1:031421429609:log-group:/ecs/builder-selenium-crawler:*"
        }
    ]
}

print("Updating ECS task role policy...")
print(f"Role: builder-crawler-task-role")
print(f"Policy: BuilderCrawlerTaskPolicy")

try:
    response = iam.put_role_policy(
        RoleName='builder-crawler-task-role',
        PolicyName='BuilderCrawlerTaskPolicy',
        PolicyDocument=json.dumps(policy_document)
    )
    
    print("\n✅ Successfully updated ECS task role policy")
    print("\nPermissions granted:")
    print("  - DynamoDB: aws-blog-posts, aws-blog-posts-staging")
    print("  - Lambda: aws-blog-summary-generator:production, aws-blog-summary-generator:staging")
    print("  - CloudWatch Logs: /ecs/builder-selenium-crawler")
    
except Exception as e:
    print(f"\n❌ Error updating policy: {e}")
    exit(1)
