"""
Add permission for summary generator to invoke classifier Lambda (staging alias)
"""
import boto3
import json

iam_client = boto3.client('iam')

role_name = 'aws-blog-summary-lambda-role'

# Policy to allow invoking classifier Lambda with staging alias
policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "lambda:InvokeFunction",
            "Resource": [
                "arn:aws:lambda:us-east-1:031421429609:function:aws-blog-classifier",
                "arn:aws:lambda:us-east-1:031421429609:function:aws-blog-classifier:*"
            ]
        }
    ]
}

policy_name = "ClassifierInvokePolicy"

print("=" * 80)
print("Adding Classifier Invoke Permission to Summary Generator")
print("=" * 80)
print(f"\nRole: {role_name}")
print(f"Policy: {policy_name}")

try:
    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_document)
    )
    print("\n✅ Policy added successfully!")
    print("\nSummary generator can now invoke classifier Lambda (all versions/aliases)")
    
except iam_client.exceptions.NoSuchEntityException:
    print(f"\n⚠️  Role not found")
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "=" * 80)
