"""
Test script to verify rename context integration (Tasks 6-9)
Tests that AI responses mention service renames
"""

import json
import urllib.request

# Staging API endpoint
STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'


def test_appstream_rename():
    """
    Test query with 'AppStream 2.0' (historical name)
    AI should mention it's now called WorkSpaces Applications
    """
    print("\n=== Test 1: AppStream 2.0 Rename Context ===")
    
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
        
        ai_response = result['response']
        print(f"\nAI Response:\n{ai_response}\n")
        
        # Check if response mentions the rename
        mentions_workspaces_apps = 'workspaces applications' in ai_response.lower()
        mentions_rename = any(word in ai_response.lower() for word in ['renamed', 'now called', 'formerly', 'previously'])
        
        if mentions_workspaces_apps and mentions_rename:
            print("✓ AI response mentions the service rename!")
        elif mentions_workspaces_apps:
            print("⚠ AI response mentions WorkSpaces Applications but doesn't explicitly mention rename")
        else:
            print("✗ AI response does NOT mention the rename")
        
        print(f"\nRecommendations ({len(result['recommendations'])}):")
        for i, rec in enumerate(result['recommendations'][:3], 1):
            print(f"{i}. {rec['title'][:80]}")
        
        return result
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_workspaces_web_rename():
    """
    Test query with 'WorkSpaces Web' (historical name)
    AI should mention it's now called WorkSpaces Secure Browser
    """
    print("\n=== Test 2: WorkSpaces Web Rename Context ===")
    
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
        
        ai_response = result['response']
        print(f"\nAI Response:\n{ai_response}\n")
        
        # Check if response mentions the rename
        mentions_secure_browser = 'secure browser' in ai_response.lower()
        mentions_rename = any(word in ai_response.lower() for word in ['renamed', 'now called', 'formerly', 'previously'])
        
        if mentions_secure_browser and mentions_rename:
            print("✓ AI response mentions the service rename!")
        elif mentions_secure_browser:
            print("⚠ AI response mentions Secure Browser but doesn't explicitly mention rename")
        else:
            print("✗ AI response does NOT mention the rename")
        
        print(f"\nRecommendations ({len(result['recommendations'])}):")
        for i, rec in enumerate(result['recommendations'][:3], 1):
            print(f"{i}. {rec['title'][:80]}")
        
        return result
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_wsp_rename():
    """
    Test query with 'WSP' (historical name)
    AI should mention it's now called Amazon DCV
    """
    print("\n=== Test 3: WSP Rename Context ===")
    
    payload = {
        'message': 'What is WSP?'
    }
    
    req = urllib.request.Request(
        f'{STAGING_API}/chat',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        ai_response = result['response']
        print(f"\nAI Response:\n{ai_response}\n")
        
        # Check if response mentions the rename
        mentions_dcv = 'dcv' in ai_response.lower()
        mentions_rename = any(word in ai_response.lower() for word in ['renamed', 'now called', 'formerly', 'previously'])
        
        if mentions_dcv and mentions_rename:
            print("✓ AI response mentions the service rename!")
        elif mentions_dcv:
            print("⚠ AI response mentions DCV but doesn't explicitly mention rename")
        else:
            print("✗ AI response does NOT mention the rename")
        
        print(f"\nRecommendations ({len(result['recommendations'])}):")
        for i, rec in enumerate(result['recommendations'][:3], 1):
            print(f"{i}. {rec['title'][:80]}")
        
        return result
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_current_name_no_rename():
    """
    Test query with current service name (no historical name)
    AI should NOT mention any rename
    """
    print("\n=== Test 4: Current Name (No Rename Context) ===")
    
    payload = {
        'message': 'Tell me about Amazon WorkSpaces'
    }
    
    req = urllib.request.Request(
        f'{STAGING_API}/chat',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        ai_response = result['response']
        print(f"\nAI Response:\n{ai_response}\n")
        
        # Check that response does NOT mention rename
        mentions_rename = any(word in ai_response.lower() for word in ['renamed', 'formerly', 'previously known as'])
        
        if not mentions_rename:
            print("✓ AI response correctly does NOT mention rename (current name used)")
        else:
            print("⚠ AI response mentions rename even though current name was used")
        
        print(f"\nRecommendations ({len(result['recommendations'])}):")
        for i, rec in enumerate(result['recommendations'][:3], 1):
            print(f"{i}. {rec['title'][:80]}")
        
        return result
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def check_cloudwatch_logs():
    """
    Check CloudWatch logs for rename detection
    """
    print("\n=== CloudWatch Logs Check ===")
    
    import boto3
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
        
        # Look for rename detection logs
        rename_logs = []
        for event in events_response['events']:
            message = event['message']
            if 'rename detected' in message.lower():
                rename_logs.append(message)
        
        if rename_logs:
            print(f"\n✓ Found {len(rename_logs)} rename detection log entries:")
            for log in rename_logs[-10:]:  # Show last 10
                print(f"  {log.strip()}")
        else:
            print("\n⚠ No rename detection logs found in recent stream")
    
    except Exception as e:
        print(f"✗ Error checking logs: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    print("=" * 80)
    print("Rename Context Integration - Staging Tests")
    print("Testing Tasks 6-9: Rename Detection and AI Response Enhancement")
    print("=" * 80)
    
    # Run tests
    test_appstream_rename()
    test_workspaces_web_rename()
    test_wsp_rename()
    test_current_name_no_rename()
    
    # Check logs
    check_cloudwatch_logs()
    
    print("\n" + "=" * 80)
    print("Tests Complete")
    print("=" * 80)
