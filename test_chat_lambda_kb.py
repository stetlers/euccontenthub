#!/usr/bin/env python3
"""
Test Chat Lambda with KB Integration - Staging

This script tests the new chat Lambda that uses Bedrock Agent + Knowledge Base.
"""

import requests
import json
import time

# Load configuration
with open('kb-config-staging.json') as f:
    config = json.load(f)

LAMBDA_URL = config['chat_lambda_url']

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
            LAMBDA_URL,
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
            
            print(f"\nCitations ({len(data['citations'])} sources):")
            for i, citation in enumerate(data['citations'], 1):
                print(f"  {i}. Source: {citation['source']}")
                print(f"     Content: {citation['content'][:100]}...")
            
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
    print(f"# Testing Chat Lambda with KB Integration - STAGING")
    print(f"# Lambda URL: {LAMBDA_URL}")
    print(f"{'#'*80}\n")
    
    # Test 1: Basic EUC question
    conv_id = test_query("What is EUC?")
    
    # Test 2: Service rename question
    test_query("What happened to WorkSpaces?")
    
    # Test 3: Follow-up question (using conversation ID)
    if conv_id:
        test_query("Tell me more about WorkSpaces Personal", conv_id)
    
    # Test 4: Specific service question
    test_query("What is AppStream 2.0?")
    
    # Test 5: Use case question
    test_query("How can I provide remote access to my employees?")
    
    print(f"\n{'='*80}")
    print("TESTING COMPLETE!")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    main()
