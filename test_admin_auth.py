import boto3
import json

lambda_client = boto3.client('lambda', region_name='us-east-1')

# Test 1: Try to delete comment with verified user (test-user-123 who we verified earlier)
print('=== Test 1: Delete comment with VERIFIED user ===')
payload_verified = {
    'path': '/posts/test-post-123/comments',
    'httpMethod': 'DELETE',
    'headers': {
        'Authorization': 'Bearer test-token'
    },
    'body': json.dumps({
        'post_id': 'test-post-123',
        'comment_id': 'test-comment-123'
    }),
    'requestContext': {
        'authorizer': {
            'claims': {
                'sub': 'test-user-123',  # This user has valid verification
                'email': 'test@example.com'
            }
        }
    },
    'pathParameters': {
        'id': 'test-post-123'
    },
    'stageVariables': {
        'TABLE_SUFFIX': '-staging'
    }
}

response = lambda_client.invoke(
    FunctionName='aws-blog-api',
    InvocationType='RequestResponse',
    Payload=json.dumps(payload_verified)
)

result = json.loads(response['Payload'].read())
print(f'Status Code: {result.get("statusCode")}')
print(f'Response: {json.dumps(json.loads(result.get("body", "{}")), indent=2)}')

# Test 2: Try to delete comment with unverified user
print('\n=== Test 2: Delete comment with UNVERIFIED user ===')
payload_unverified = {
    'path': '/posts/test-post-123/comments',
    'httpMethod': 'DELETE',
    'headers': {
        'Authorization': 'Bearer test-token'
    },
    'body': json.dumps({
        'post_id': 'test-post-123',
        'comment_id': 'test-comment-123'
    }),
    'requestContext': {
        'authorizer': {
            'claims': {
                'sub': 'unverified-user-456',  # This user has no verification
                'email': 'unverified@example.com'
            }
        }
    },
    'pathParameters': {
        'id': 'test-post-123'
    },
    'stageVariables': {
        'TABLE_SUFFIX': '-staging'
    }
}

response = lambda_client.invoke(
    FunctionName='aws-blog-api',
    InvocationType='RequestResponse',
    Payload=json.dumps(payload_unverified)
)

result = json.loads(response['Payload'].read())
print(f'Status Code: {result.get("statusCode")}')
print(f'Response: {json.dumps(json.loads(result.get("body", "{}")), indent=2)}')

# Test 3: Check the verified user's profile to confirm verification status
print('\n=== Test 3: Verify user profile status ===')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
profiles_table = dynamodb.Table('euc-user-profiles-staging')

profile_response = profiles_table.get_item(Key={'user_id': 'test-user-123'})
if 'Item' in profile_response:
    profile = profile_response['Item']
    print(f'User: test-user-123')
    print(f'amazon_verified: {profile.get("amazon_verified", False)}')
    print(f'amazon_verified_expires_at: {profile.get("amazon_verified_expires_at", "Not set")}')
    print(f'amazon_verification_revoked: {profile.get("amazon_verification_revoked", False)}')
else:
    print('Profile not found')
