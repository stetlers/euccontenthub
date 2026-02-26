"""
Test KB document endpoint with detailed logging
"""
import boto3
import json

lambda_client = boto3.client('lambda', region_name='us-east-1')

# Simulate API Gateway event
event = {
    "resource": "/kb-document/{id}",
    "path": "/kb-document/euc-qa-pairs",
    "httpMethod": "GET",
    "headers": {
        "Authorization": "Bearer test-token"
    },
    "pathParameters": {
        "id": "euc-qa-pairs"
    },
    "stageVariables": {
        "lambdaAlias": "staging",
        "environment": "staging",
        "TABLE_SUFFIX": "-staging"
    },
    "requestContext": {
        "stage": "staging"
    }
}

print("\n🧪 Testing Lambda directly with KB document event...")
print("=" * 60)

try:
    response = lambda_client.invoke(
        FunctionName='aws-blog-api:staging',
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )
    
    result = json.loads(response['Payload'].read())
    print(f"\nStatus Code: {result.get('statusCode')}")
    print(f"\nResponse Body:")
    print(json.dumps(json.loads(result.get('body', '{}')), indent=2))
    
except Exception as e:
    print(f"Error: {e}")
