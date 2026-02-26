"""
Add DynamoDB permissions for KB editor tables
"""
import boto3
import json

iam_client = boto3.client('iam', region_name='us-east-1')

# Lambda execution role
ROLE_NAME = 'aws-blog-viewer-stack-APILambdaRole-TYW5hnze4yLe'

# Policy for KB editor DynamoDB tables
policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": [
                "arn:aws:dynamodb:us-east-1:031421429609:table/kb-edit-history-staging",
                "arn:aws:dynamodb:us-east-1:031421429609:table/kb-contributor-stats-staging",
                "arn:aws:dynamodb:us-east-1:031421429609:table/kb-edit-history",
                "arn:aws:dynamodb:us-east-1:031421429609:table/kb-contributor-stats"
            ]
        }
    ]
}

print("\n🔧 Adding DynamoDB permissions for KB editor tables...")
print("=" * 70)

try:
    # Add inline policy to Lambda role
    iam_client.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName='KBEditorDynamoDBAccess',
        PolicyDocument=json.dumps(policy_document)
    )
    
    print(f"\n✅ Added policy 'KBEditorDynamoDBAccess' to role: {ROLE_NAME}")
    print("\nPermissions granted:")
    print("  - dynamodb:PutItem")
    print("  - dynamodb:GetItem")
    print("  - dynamodb:UpdateItem")
    print("  - dynamodb:Query")
    print("  - dynamodb:Scan")
    print("\nTables:")
    print("  - kb-edit-history-staging")
    print("  - kb-contributor-stats-staging")
    print("  - kb-edit-history (production)")
    print("  - kb-contributor-stats (production)")
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    exit(1)

print("\n" + "=" * 70)
print("✅ DynamoDB permissions added successfully!")
print("=" * 70)
print("\n💡 Try saving your KB editor changes again")
