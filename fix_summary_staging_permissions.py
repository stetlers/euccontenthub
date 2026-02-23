"""
Add staging table permissions to summary generator and classifier Lambdas
"""
import boto3
import json

iam_client = boto3.client('iam')

# Lambda roles that need staging table access
roles_to_update = [
    {
        'name': 'aws-blog-summary-lambda-role',
        'description': 'Summary Generator Lambda'
    },
    {
        'name': 'aws-blog-classifier-lambda-role',
        'description': 'Classifier Lambda'
    }
]

# Policy to allow access to staging table
policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:Scan",
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query"
            ],
            "Resource": [
                "arn:aws:dynamodb:us-east-1:031421429609:table/aws-blog-posts-staging"
            ]
        }
    ]
}

policy_name = "StagingTableAccessPolicy"

print("=" * 80)
print("Adding Staging Table Permissions")
print("=" * 80)

for role_info in roles_to_update:
    role_name = role_info['name']
    description = role_info['description']
    
    print(f"\n{description}")
    print(f"Role: {role_name}")
    
    try:
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        print("✅ Policy added successfully!")
        
    except iam_client.exceptions.NoSuchEntityException:
        print(f"⚠️  Role not found - skipping")
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("Permissions Update Complete!")
print("=" * 80)
print("\nBoth summary generator and classifier can now access staging table.")
print("You can now run the crawler again and summaries/labels should work.")
