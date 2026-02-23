"""
Test AppStream 2.0 rename detection in staging
"""

import json
import urllib.request

# Staging API endpoint
STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'


def test_appstream_rename():
    """Test AppStream 2.0 rename in staging"""
    print("\n=== Test: AppStream 2.0 Rename (Staging) ===")
    
    payload = {
        'message': 'Tell me about AppStream 2.0 deployment'
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


if __name__ == '__main__':
    test_appstream_rename()
