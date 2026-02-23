#!/usr/bin/env python3
"""Get the results of the crawler run"""

import boto3
from datetime import datetime, timedelta

logs_client = boto3.client('logs', region_name='us-east-1')

def get_logs():
    """Get recent logs"""
    start_time = int((datetime.utcnow() - timedelta(minutes=5)).timestamp() * 1000)
    
    try:
        response = logs_client.filter_log_events(
            logGroupName='/aws/lambda/aws-blog-crawler',
            startTime=start_time
        )
        
        messages = [event['message'] for event in response.get('events', [])]
        
        # Look for key messages
        for msg in messages:
            if 'changed' in msg.lower() or 'selenium' in msg.lower() or 'invok' in msg.lower():
                print(msg.strip())
        
        # Print last 20 lines
        print("\n" + "="*60)
        print("Last 20 log lines:")
        print("="*60)
        for msg in messages[-20:]:
            print(msg.strip())
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    get_logs()
