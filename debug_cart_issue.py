"""
Debug cart API issue when signed in
"""

import boto3
import json

# Configuration
LAMBDA_FUNCTION_NAME = 'aws-blog-api'
REGION = 'us-east-1'

def test_cart_endpoint():
    """Test cart endpoint with mock authenticated user"""
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    # Get a real post ID first
    print("1. Getting a real post ID...")
    event = {
        'httpMethod': 'GET',
        'path': '/posts',
        'pathParameters': {},
        'queryStringParameters': {},
        'headers': {},
        'requestContext': {'stage': 'staging'},
        'stageVariables': {'TABLE_SUFFIX': '-staging'}
    }
    
    response = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )
    
    result = json.loads(response['Payload'].read())
    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        posts = body.get('posts', [])
        if posts:
            test_post_id = posts[0]['post_id']
            print(f"✅ Got test post ID: {test_post_id}")
        else:
            print("❌ No posts found")
            return
    else:
        print(f"❌ Failed to get posts: {result}")
        return
    
    # Test adding to cart
    print(f"\n2. Testing POST /cart with post_id: {test_post_id}")
    event = {
        'httpMethod': 'POST',
        'path': '/cart',
        'pathParameters': {},
        'queryStringParameters': {},
        'headers': {
            'Authorization': 'Bearer mock-token'
        },
        'body': json.dumps({'post_id': test_post_id}),
        'requestContext': {'stage': 'staging'},
        'stageVariables': {'TABLE_SUFFIX': '-staging'},
        'user': {
            'sub': 'test-user-debug',
            'email': 'test@example.com'
        }
    }
    
    response = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )
    
    result = json.loads(response['Payload'].read())
    print(f"Status: {result['statusCode']}")
    print(f"Response: {json.dumps(json.loads(result['body']), indent=2)}")
    
    if result['statusCode'] != 200:
        print("\n❌ POST /cart failed!")
        print("This is likely why you're seeing 'Failed to update cart'")
        return
    
    # Test getting cart
    print(f"\n3. Testing GET /cart")
    event = {
        'httpMethod': 'GET',
        'path': '/cart',
        'pathParameters': {},
        'queryStringParameters': {},
        'headers': {
            'Authorization': 'Bearer mock-token'
        },
        'requestContext': {'stage': 'staging'},
        'stageVariables': {'TABLE_SUFFIX': '-staging'},
        'user': {
            'sub': 'test-user-debug',
            'email': 'test@example.com'
        }
    }
    
    response = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )
    
    result = json.loads(response['Payload'].read())
    print(f"Status: {result['statusCode']}")
    print(f"Response: {json.dumps(json.loads(result['body']), indent=2)}")
    
    # Clean up - remove from cart
    print(f"\n4. Testing DELETE /cart/{test_post_id}")
    event = {
        'httpMethod': 'DELETE',
        'path': f'/cart/{test_post_id}',
        'pathParameters': {'post_id': test_post_id},
        'queryStringParameters': {},
        'headers': {
            'Authorization': 'Bearer mock-token'
        },
        'requestContext': {'stage': 'staging'},
        'stageVariables': {'TABLE_SUFFIX': '-staging'},
        'user': {
            'sub': 'test-user-debug',
            'email': 'test@example.com'
        }
    }
    
    response = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )
    
    result = json.loads(response['Payload'].read())
    print(f"Status: {result['statusCode']}")
    print(f"Response: {json.dumps(json.loads(result['body']), indent=2)}")

def check_lambda_logs():
    """Check recent Lambda logs for errors"""
    print("\n5. Checking Lambda logs for cart-related errors...")
    
    logs_client = boto3.client('logs', region_name=REGION)
    log_group = '/aws/lambda/aws-blog-api'
    
    try:
        # Get recent log streams
        response = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        for stream in response['logStreams']:
            stream_name = stream['logStreamName']
            
            # Get log events
            events_response = logs_client.get_log_events(
                logGroupName=log_group,
                logStreamName=stream_name,
                limit=50
            )
            
            # Look for cart-related errors
            for event in events_response['events']:
                message = event['message']
                if 'cart' in message.lower() or 'error' in message.lower():
                    print(f"\n📋 Log: {message[:200]}")
    
    except Exception as e:
        print(f"⚠️  Could not read logs: {e}")

def main():
    print("=" * 60)
    print("Cart API Debug")
    print("=" * 60)
    
    try:
        test_cart_endpoint()
        check_lambda_logs()
        
        print("\n" + "=" * 60)
        print("Debug complete")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
