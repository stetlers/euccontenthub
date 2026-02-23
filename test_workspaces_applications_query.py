"""Test query expansion with WorkSpaces Applications"""
import boto3
import json
import time

lambda_client = boto3.client('lambda', region_name='us-east-1')
logs_client = boto3.client('logs', region_name='us-east-1')

FUNCTION_NAME = 'aws-blog-chat-assistant'
LOG_GROUP = f'/aws/lambda/{FUNCTION_NAME}'

print("Testing query expansion with 'WorkSpaces Applications'...")
print("=" * 70)

# Test payload
test_payload = {
    'body': json.dumps({
        'message': 'Can you tell me about WorkSpaces Applications?',
        'conversation_id': 'test-query-expansion-456'
    })
}

print("\n1. Invoking Lambda...")
print(f"   Query: 'Can you tell me about WorkSpaces Applications?'")

try:
    response = lambda_client.invoke(
        FunctionName=FUNCTION_NAME,
        InvocationType='RequestResponse',
        Payload=json.dumps(test_payload)
    )
    
    response_payload = json.loads(response['Payload'].read())
    status_code = response_payload.get('statusCode', 0)
    
    print(f"   Status Code: {status_code}")
    
    if status_code == 200:
        body = json.loads(response_payload['body'])
        print(f"   ✓ Lambda invocation successful")
        print(f"\n2. AI Response:")
        print(f"   {body.get('response', '')}")
        print(f"\n3. Recommendations: {len(body.get('recommendations', []))} posts")
        for i, rec in enumerate(body.get('recommendations', [])[:3], 1):
            print(f"   {i}. {rec.get('title', '')[:70]}")
    else:
        print(f"   ✗ Error: {response_payload}")
        exit(1)
    
    # Wait for logs
    print("\n4. Waiting for logs...")
    time.sleep(3)
    
    # Check logs for query expansion
    print("\n5. Checking CloudWatch logs for query expansion...")
    
    streams_response = logs_client.describe_log_streams(
        logGroupName=LOG_GROUP,
        orderBy='LastEventTime',
        descending=True,
        limit=1
    )
    
    if streams_response['logStreams']:
        stream_name = streams_response['logStreams'][0]['logStreamName']
        
        events_response = logs_client.get_log_events(
            logGroupName=LOG_GROUP,
            logStreamName=stream_name,
            limit=300,
            startFromHead=True
        )
        
        # Look for expansion logs
        expansion_logs = []
        for event in events_response['events']:
            message = event['message']
            if any(keyword in message for keyword in ['Query expansion', 'Detected service', 'Expanded terms', 'appstream', 'AppStream']):
                expansion_logs.append(message.strip())
        
        if expansion_logs:
            print("\n   Query Expansion Logs:")
            print("   " + "-" * 66)
            for log in expansion_logs[-10:]:  # Show last 10
                print(f"   {log}")
            print()
            
            # Check for success indicators
            if any('appstream' in log.lower() for log in expansion_logs):
                print("   ✓ Query expansion working! Found 'appstream' variants")
            else:
                print("   ⚠ Query expansion may not be working as expected")
        else:
            print("   ⚠ No query expansion logs found")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("Test complete")
