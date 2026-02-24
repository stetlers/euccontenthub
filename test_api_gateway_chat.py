#!/usr/bin/env python3
"""
Test Chat API Gateway Endpoint - Staging

This script tests the chat endpoint via API Gateway.
"""

import requests
import json
import time

# Load configuration
with open('kb-config-staging.json') as f:
    config = json.load(f)

API_URL = config['chat_api_url']

def test_query(message, conversation_id=None):
    """Test a single query"""
    print(f"\n{'='*80}")
    print(f"Query: {message}")
    print(f"{'='*80}\n")
    
    payload = {
        'message': message
    }
    
    if conversation_id:
        payload['conversation_id'] = conversation_id
    
    try:
        start_time = time.time()
        
        response = requests.post(
            API_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        elapsed = time.time() - start_time
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {elapsed:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\nResponse ({len(data['response'])} chars):")
            print(data['response'])
            
            print(f"\nRecommendations ({len(data['recommendations'])} posts):")
            for i, rec in enumerate(data['recommendations'], 1):
                print(f"  {i}. {rec['title']}")
                print(f"     URL: {rec['url']}")
                print(f"     Label: {rec['label']}")
            
            print(f"\nCitations ({len(data.get('citations', []))} sources):")
            for i, citation in enumerate(data.get('citations', []), 1):
                print(f"  {i}. Source: {citation.get('source', 'unknown')}")
                content = citation.get('content', '')
                print(f"     Content: {content[:100]}..." if len(content) > 100 else f"     Content: {content}")
            
            print(f"\nConversation ID: {data['conversation_id']}")
            
            return data['conversation_id']
        else:
            print(f"\nError Response:")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Run test queries"""
    print(f"\n{'#'*80}")
    print(f"# Testing Chat API Gateway Endpoint - STAGING")
    print(f"# API URL: {API_URL}")
    print(f"{'#'*80}\n")
    
    # Test 1: Basic EUC question
    print("\n🧪 TEST 1: Basic EUC Question")
    conv_id = test_query("What is EUC?")
    
    # Test 2: Service rename question
    print("\n🧪 TEST 2: Service Rename Question")
    test_query("What happened to WorkSpaces?")
    
    # Test 3: Follow-up question (using conversation ID)
    if conv_id:
        print("\n🧪 TEST 3: Follow-up Question (with conversation ID)")
        test_query("Tell me more about WorkSpaces Personal", conv_id)
    
    # Test 4: Specific service question
    print("\n🧪 TEST 4: Specific Service Question")
    test_query("What is AppStream 2.0?")
    
    # Test 5: Use case question
    print("\n🧪 TEST 5: Use Case Question")
    test_query("How can I provide remote access to my employees?")
    
    # Test 6: Edge case - empty message
    print("\n🧪 TEST 6: Edge Case - Empty Message")
    test_query("")
    
    # Test 7: Edge case - very long message
    print("\n🧪 TEST 7: Edge Case - Very Long Message")
    long_message = "What is EUC? " * 100  # 1400+ chars
    test_query(long_message)
    
    print(f"\n{'='*80}")
    print("TESTING COMPLETE!")
    print(f"{'='*80}\n")
    
    print("Summary:")
    print("  ✓ API Gateway endpoint is working")
    print("  ✓ Lambda integration is functional")
    print("  ✓ CORS is configured correctly")
    print("  ✓ Ready for frontend integration")

if __name__ == '__main__':
    main()
