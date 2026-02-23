"""
Check for Builder.AWS specific messages in crawler logs
"""
import boto3

logs_client = boto3.client('logs', region_name='us-east-1')
log_group = '/aws/lambda/aws-blog-crawler'

print("Searching for Builder.AWS messages in crawler logs...")
print("=" * 80)

try:
    # Get the most recent log stream
    streams = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=1
    )
    
    if streams['logStreams']:
        stream_name = streams['logStreams'][0]['logStreamName']
        
        # Get all events
        events = logs_client.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            startFromHead=True
        )
        
        # Search for Builder.AWS related messages
        builder_messages = []
        for event in events['events']:
            message = event['message'].strip()
            if any(keyword in message.lower() for keyword in ['builder', 'ecs', 'task', 'changed']):
                builder_messages.append(message)
        
        if builder_messages:
            print(f"Found {len(builder_messages)} Builder.AWS related messages:\n")
            for msg in builder_messages[-20:]:  # Last 20 messages
                print(msg)
        else:
            print("No Builder.AWS related messages found")
            print("\nThis suggests the Builder.AWS crawler section may not have run.")
            print("Checking if 'builder_aws' appears in logs...")
            
            # Check for any mention
            for event in events['events']:
                if 'builder' in event['message'].lower():
                    print(f"  Found: {event['message'].strip()}")
    
except Exception as e:
    print(f"Error: {e}")
