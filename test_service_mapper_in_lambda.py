"""Test service mapper integration in Lambda"""
import boto3
import json
import time

# Initialize Lambda client
lambda_client = boto3.client('lambda', region_name='us-east-1')
logs_client = boto3.client('logs', region_name='us-east-1')

FUNCTION_NAME = 'aws-blog-chat-assistant'
LOG_GROUP = f'/aws/lambda/{FUNCTION_NAME}'

print("Testing service mapper integration in Lambda...")
print("=" * 70)

# Test payload
test_payload = {
    'body': json.dumps({
        'message': 'Tell me about AppStream 2.0',
        'conversation_id': 'test-service-mapper-123'
    })
}

print("\n1. Invoking Lambda with test query...")
print(f"   Query: 'Tell me about AppStream 2.0'")

try:
    response = lambda_client.invoke(
        FunctionName=FUNCTION_NAME,
        InvocationType='RequestResponse',
        Payload=json.dumps(test_payload)
    )
    
    # Parse response
    response_payload = json.loads(response['Payload'].read())
    status_code = response_payload.get('statusCode', 0)
    
    print(f"   Status Code: {status_code}")
    
    if status_code == 200:
        body = json.loads(response_payload['body'])
        print(f"   ✓ Lambda invocation successful")
        print(f"   Response: {body.get('response', '')[:100]}...")
        print(f"   Recommendations: {len(body.get('recommendations', []))} posts")
    else:
        print(f"   ✗ Lambda returned error: {response_payload}")
    
    # Wait for logs to be available
    print("\n2. Waiting for logs to be available...")
    time.sleep(3)
    
    # Check logs for service mapper initialization
    print("\n3. Checking CloudWatch logs for service mapper...")
    
    # Get the most recent log stream
    streams_response = logs_client.describe_log_streams(
        logGroupName=LOG_GROUP,
        orderBy='LastEventTime',
        descending=True,
        limit=1
    )
    
    if streams_response['logStreams']:
        stream_name = streams_response['logStreams'][0]['logStreamName']
        
        # Get log events
        events_response = logs_client.get_log_events(
            logGroupName=LOG_GROUP,
            logStreamName=stream_name,
            limit=200,
            startFromHead=True  # Get from beginning to see initialization
        )
        
        # Look for service mapper logs
        init_logs = []
        for event in events_response['events']:
            message = event['message']
            if any(keyword in message.lower() for keyword in ['service mapper', 'eucservicemapper', 'service mapping']):
                init_logs.append(message.strip())
        
        if init_logs:
            print("\n   Service Mapper Logs Found:")
            print("   " + "-" * 66)
            for log in init_logs:
                print(f"   {log}")
            print()
            
            # Check for success indicators
            success_indicators = ['initialized successfully', 'services loaded', 'services']
            error_indicators = ['ERROR', 'Failed', 'not found']
            
            if any(indicator in ' '.join(init_logs) for indicator in success_indicators):
                print("   ✓ Service mapper appears to be initialized")
            elif any(indicator in ' '.join(init_logs) for indicator in error_indicators):
                print("   ✗ Service mapper initialization may have failed")
            else:
                print("   ⚠ Service mapper status unclear from logs")
        else:
            print("   ⚠ No service mapper initialization logs found")
            print("   This might mean:")
            print("   - Lambda is reusing a warm container (no cold start)")
            print("   - Logs haven't propagated yet")
            print("   - Service mapper import failed silently")
            
            # Show START log to confirm we're looking at the right invocation
            start_logs = [e['message'] for e in events_response['events'] if 'START RequestId' in e['message']]
            if start_logs:
                print(f"\n   Latest invocation: {start_logs[-1].strip()}")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("Test complete")
