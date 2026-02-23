"""
Test Chat Lambda in Production
Verify AWS Docs Integration + Service Mapper features
"""

import json
import urllib.request

# Production API endpoint
PRODUCTION_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod'


def test_appstream_rename_production():
    """Test AppStream 2.0 rename in production"""
    print("\n=== Test 1: AppStream 2.0 Rename (Production) ===")
    
    payload = {
        'message': 'Tell me about AppStream 2.0'
    }
    
    req = urllib.request.Request(
        f'{PRODUCTION_API}/chat',
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


def test_workspaces_web_rename_production():
    """Test WorkSpaces Web rename in production"""
    print("\n=== Test 2: WorkSpaces Web Rename (Production) ===")
    
    payload = {
        'message': 'How do I use WorkSpaces Web?'
    }
    
    req = urllib.request.Request(
        f'{PRODUCTION_API}/chat',
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


def test_aws_docs_integration_production():
    """Test AWS Docs integration in production"""
    print("\n=== Test 3: AWS Docs Integration (Production) ===")
    
    payload = {
        'message': 'How do I configure Amazon WorkSpaces?'
    }
    
    req = urllib.request.Request(
        f'{PRODUCTION_API}/chat',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        ai_response = result['response']
        print(f"\nAI Response:\n{ai_response[:300]}...\n")
        
        # Check if AWS docs were included
        if 'aws_docs' in result and result['aws_docs']:
            print(f"✓ AWS Docs included: {len(result['aws_docs'])} results")
            for i, doc in enumerate(result['aws_docs'][:3], 1):
                print(f"{i}. {doc['title'][:80]}")
                print(f"   URL: {doc['url']}")
        else:
            print("⚠ No AWS docs included (might not be a service-specific query)")
        
        print(f"\nBlog Recommendations ({len(result['recommendations'])}):")
        for i, rec in enumerate(result['recommendations'][:3], 1):
            print(f"{i}. {rec['title'][:80]}")
        
        return result
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_query_expansion_production():
    """Test query expansion with service variants"""
    print("\n=== Test 4: Query Expansion (Production) ===")
    
    payload = {
        'message': 'Can you tell me about WorkSpaces Applications?'
    }
    
    req = urllib.request.Request(
        f'{PRODUCTION_API}/chat',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        ai_response = result['response']
        print(f"\nAI Response:\n{ai_response[:300]}...\n")
        
        # Check if we got AppStream posts (via query expansion)
        appstream_posts = [r for r in result['recommendations'] 
                          if 'appstream' in r['title'].lower() or 
                             'appstream' in r.get('summary', '').lower()]
        
        if appstream_posts:
            print(f"✓ Query expansion working: Found {len(appstream_posts)} AppStream posts")
        else:
            print("⚠ Query expansion might not be working (no AppStream posts found)")
        
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
    print("=" * 80)
    print("Production Chat Lambda Tests")
    print("Testing AWS Docs Integration + Service Mapper Features")
    print("=" * 80)
    
    # Run tests
    test_appstream_rename_production()
    test_workspaces_web_rename_production()
    test_aws_docs_integration_production()
    test_query_expansion_production()
    
    print("\n" + "=" * 80)
    print("Tests Complete")
    print("=" * 80)
    print("\nNext: Test on production website at https://awseuccontent.com")
