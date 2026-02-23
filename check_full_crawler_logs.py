#!/usr/bin/env python3
"""
Get full crawler logs from the most recent invocation
"""
import boto3
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')

print("="*80)
print("FULL CRAWLER LOGS - MOST RECENT INVOCATION")
print("="*80)

log_group = '/aws/lambda/aws-blog-crawler'
start_time = int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)

try:
    # Get all log streams
    streams_response = logs_client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=1
    )
    
    if not streams_response['logStreams']:
        print("No log streams found")
        exit(1)
    
    latest_stream = streams_response['logStreams'][0]
    stream_name = latest_stream['logStreamName']
    
    print(f"\nLatest log stream: {stream_name}")
    print(f"Last event: {datetime.fromtimestamp(latest_stream['lastEventTimestamp']/1000)}")
    print("\n" + "="*80)
    print("LOG CONTENTS:")
    print("="*80 + "\n")
    
    # Get all events from this stream
    response = logs_client.get_log_events(
        logGroupName=log_group,
        logStreamName=stream_name,
        startFromHead=True
    )
    
    for event in response['events']:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event['message'].strip()
        print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
    
    print("\n" + "="*80)
    print("KEY FINDINGS:")
    print("="*80)
    
    all_text = '\n'.join([e['message'] for e in response['events']])
    
    # Check what was invoked
    if 'source' in all_text.lower():
        for line in all_text.split('\n'):
            if 'source' in line.lower() and ('all' in line or 'builder' in line or 'aws-blog' in line):
                print(f"\n✓ {line.strip()}")
    
    # Check if Builder crawl started
    if 'CRAWLING BUILDER.AWS' in all_text:
        print("\n✓ Builder.AWS crawl was initiated")
    else:
        print("\n✗ Builder.AWS crawl was NOT initiated")
        print("   This is the problem!")
    
    # Check for errors
    if 'ERROR' in all_text or 'Error' in all_text or 'Exception' in all_text:
        print("\n⚠️  Errors found:")
        for line in all_text.split('\n'):
            if any(kw in line for kw in ['ERROR', 'Error', 'Exception', 'Traceback']):
                print(f"   {line.strip()}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
