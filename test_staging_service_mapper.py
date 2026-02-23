"""
Test script to verify service mapper integration in staging
Tests Tasks 1-4: Initialization, Query Expansion, and Enhanced Scoring
"""

import json
import boto3
from decimal import Decimal

# Staging API endpoint
STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'

def test_workspaces_applications_query():
    """
    Test query with 'WorkSpaces Applications' (current name)
    Should find AppStream 2.0 posts via query expansion
    """
    print("\n=== Test 1: WorkSpaces Applications Query ===")
    
    import urllib.request
    
    payload = {
        'message': 'Can you tell me about WorkSpaces Applications?'
    }
    
    req = urllib.request.Request(
        f'{STAGING_API}/chat',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        print(f"Response: {result['response'][:200]}...")
        print(f"\nRecommendations ({len(result['recommendations'])}):")
        for i, rec in enumerate(result['recommendations'][:5], 1):
            print(f"{i}. {rec['title'][:80]}")
            print(f"   Reason: {rec['relevance_reason'][:100]}")
        
        # Check if we got AppStream posts
        appstream_posts = [r for r in result['recommendations'] 
                          if 'appstream' in r['title'].lower() or 
                             'appstream' in r.get('summary', '').lower()]
        
        print(f"\n✓ Found {len(appstream_posts)} AppStream-related posts")
        
        return result
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_appstream_query():
    """
    Test query with 'AppStream 2.0' (historical name)
    Should find posts via query expansion
    """
    print("\n=== Test 2: AppStream 2.0 Query ===")
    
    import urllib.request
    
    payload = {
        'message': 'Tell me about AppStream 2.0'
    }
    
    req = urllib.request.Request(
        f'{STAGING_API}/chat',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        print(f"Response: {result['response'][:200]}...")
        print(f"\nRecommendations ({len(result['recommendations'])}):")
        for i, rec in enumerate(result['recommendations'][:5], 1):
            print(f"{i}. {rec['title'][:80]}")
            print(f"   Reason: {rec['relevance_reason'][:100]}")
        
        # Check if we got AppStream posts
        appstream_posts = [r for r in result['recommendations'] 
                          if 'appstream' in r['title'].lower() or 
                             'appstream' in r.get('summary', '').lower()]
        
        print(f"\n✓ Found {len(appstream_posts)} AppStream-related posts")
        
        return result
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_workspaces_web_query():
    """
    Test query with 'WorkSpaces Web' (historical name)
    Should find WorkSpaces Secure Browser posts
    """
    print("\n=== Test 3: WorkSpaces Web Query ===")
    
    import urllib.request
    
    payload = {
        'message': 'How do I use WorkSpaces Web?'
    }
    
    req = urllib.request.Request(
        f'{STAGING_API}/chat',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        print(f"Response: {result['response'][:200]}...")
        print(f"\nRecommendations ({len(result['recommendations'])}):")
        for i, rec in enumerate(result['recommendations'][:5], 1):
            print(f"{i}. {rec['title'][:80]}")
            print(f"   Reason: {rec['relevance_reason'][:100]}")
        
        # Check if we got WorkSpaces Web/Secure Browser posts
        web_posts = [r for r in result['recommendations'] 
                    if 'workspaces web' in r['title'].lower() or 
                       'secure browser' in r['title'].lower() or
                       'workspaces web' in r.get('summary', '').lower() or
                       'secure browser' in r.get('summary', '').lower()]
        
        print(f"\n✓ Found {len(web_posts)} WorkSpaces Web/Secure Browser posts")
        
        return result
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_non_service_query():
    """
    Test query without service names (backward compatibility)
    Should work normally without expansion
    """
    print("\n=== Test 4: Non-Service Query (Backward Compatibility) ===")
    
    import urllib.request
    
    payload = {
        'message': 'What are best practices for remote work?'
    }
    
    req = urllib.request.Request(
        f'{STAGING_API}/chat',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        print(f"Response: {result['response'][:200]}...")
        print(f"\nRecommendations ({len(result['recommendations'])}):")
        for i, rec in enumerate(result['recommendations'][:3], 1):
            print(f"{i}. {rec['title'][:80]}")
        
        print(f"\n✓ Query processed successfully (backward compatibility)")
        
        return result
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def check_cloudwatch_logs():
    """
    Check CloudWatch logs for service mapper initialization and query expansion
    """
    print("\n=== CloudWatch Logs Check ===")
    
    logs_client = boto3.client('logs', region_name='us-east-1')
    
    log_group = '/aws/lambda/aws-blog-chat-assistant'
    
    try:
        # Get recent log streams
        response = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        if not response['logStreams']:
            print("No recent log streams found")
            return
        
        # Get logs from most recent stream
        stream_name = response['logStreams'][0]['logStreamName']
        print(f"Checking log stream: {stream_name}")
        
        events_response = logs_client.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            limit=100,
            startFromHead=False
        )
        
        # Look for service mapper logs
        mapper_logs = []
        for event in events_response['events']:
            message = event['message']
            if 'service mapper' in message.lower() or 'query expansion' in message.lower() or 'detected service' in message.lower():
                mapper_logs.append(message)
        
        if mapper_logs:
            print(f"\n✓ Found {len(mapper_logs)} service mapper log entries:")
            for log in mapper_logs[-10:]:  # Show last 10
                print(f"  {log.strip()}")
        else:
            print("\n⚠ No service mapper logs found in recent stream")
            print("This might mean:")
            print("  1. Lambda hasn't been invoked recently")
            print("  2. Service mapper failed to initialize")
            print("  3. Need to check older log streams")
    
    except Exception as e:
        print(f"✗ Error checking logs: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    print("=" * 80)
    print("Service Mapper Integration - Staging Tests")
    print("Testing Tasks 1-4: Initialization, Query Expansion, Enhanced Scoring")
    print("=" * 80)
    
    # Run tests
    test_workspaces_applications_query()
    test_appstream_query()
    test_workspaces_web_query()
    test_non_service_query()
    
    # Check logs
    check_cloudwatch_logs()
    
    print("\n" + "=" * 80)
    print("Tests Complete")
    print("=" * 80)
