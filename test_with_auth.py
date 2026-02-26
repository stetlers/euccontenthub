"""
Test KB document endpoint with a valid JWT token
"""
import boto3
import requests
import json

# Get a test token from Cognito (you'll need to sign in to get a real token)
# For now, let's just test that the endpoint routing works

url = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/kb-document/euc-qa-pairs'

print(f"\n🧪 Testing: {url}")
print("=" * 60)

# Test without auth (should get 401)
print("\n1. Testing without authentication...")
response = requests.get(url)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

if response.status_code == 401:
    print("✅ Endpoint is working! (Returns 401 as expected without auth)")
elif response.status_code == 500:
    print("❌ Endpoint returns 500 error - Lambda integration issue")
    print("\nLet's check if it's a Lambda alias issue...")
    
    # Try invoking Lambda directly
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    event = {
        "resource": "/kb-document/{id}",
        "path": "/kb-document/euc-qa-pairs",
        "httpMethod": "GET",
        "headers": {},
        "pathParameters": {"id": "euc-qa-pairs"},
        "stageVariables": {
            "lambdaAlias": "staging",
            "environment": "staging",
            "TABLE_SUFFIX": "-staging"
        },
        "requestContext": {"stage": "staging"}
    }
    
    print("\n2. Testing Lambda directly...")
    try:
        response = lambda_client.invoke(
            FunctionName='aws-blog-api:staging',
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )
        
        result = json.loads(response['Payload'].read())
        print(f"Lambda Status: {result.get('statusCode')}")
        print(f"Lambda Response: {json.loads(result.get('body', '{}'))}")
        
        if result.get('statusCode') == 401:
            print("\n✅ Lambda is working correctly!")
            print("❌ The issue is with API Gateway integration")
        
    except Exception as e:
        print(f"Error: {e}")
