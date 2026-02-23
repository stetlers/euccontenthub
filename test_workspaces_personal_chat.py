#!/usr/bin/env python3
"""
Test WorkSpaces Personal vs WorkSpaces Applications in Chat
Verify that the chatbot correctly distinguishes between the two services
"""

import requests
import json

STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'
PRODUCTION_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod'

def test_workspaces_query(api_endpoint, environment):
    """Test query about 'WorkSpaces' (should return WorkSpaces Personal)"""
    print(f"\n{'=' * 70}")
    print(f"Test 1: Query about 'WorkSpaces' in {environment.upper()}")
    print(f"{'=' * 70}")
    
    url = f"{api_endpoint}/chat"
    payload = {
        "message": "How do I get started with WorkSpaces?",
        "conversation_id": f"test_workspaces_{environment}"
    }
    
    print(f"Query: {payload['message']}")
    print(f"Expected: Should mention WorkSpaces Personal (not WorkSpaces Applications)")
    print()
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            ai_response = data.get('response', '')
            recommendations = data.get('recommendations', [])
            
            print(f"✅ Response received")
            print(f"\nAI Response (first 300 chars):")
            print(f"   {ai_response[:300]}...")
            
            # Check if response mentions WorkSpaces Personal
            mentions_personal = 'WorkSpaces Personal' in ai_response or 'Amazon WorkSpaces' in ai_response
            mentions_applications = 'WorkSpaces Applications' in ai_response or 'AppStream' in ai_response
            
            print(f"\n📊 Analysis:")
            print(f"   Mentions WorkSpaces Personal: {mentions_personal}")
            print(f"   Mentions WorkSpaces Applications: {mentions_applications}")
            
            if mentions_personal and not mentions_applications:
                print(f"   ✅ CORRECT - Talks about WorkSpaces Personal")
            elif mentions_applications:
                print(f"   ❌ INCORRECT - Mentions WorkSpaces Applications (should be Personal)")
            else:
                print(f"   ⚠️  UNCLEAR - Doesn't clearly mention either service")
            
            print(f"\n📝 Recommendations: {len(recommendations)}")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"   {i}. {rec.get('title', 'N/A')[:60]}...")
            
            return mentions_personal and not mentions_applications
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def test_appstream_query(api_endpoint, environment):
    """Test query about 'AppStream 2.0' (should return WorkSpaces Applications)"""
    print(f"\n{'=' * 70}")
    print(f"Test 2: Query about 'AppStream 2.0' in {environment.upper()}")
    print(f"{'=' * 70}")
    
    url = f"{api_endpoint}/chat"
    payload = {
        "message": "Tell me about AppStream 2.0 deployment",
        "conversation_id": f"test_appstream_{environment}"
    }
    
    print(f"Query: {payload['message']}")
    print(f"Expected: Should mention WorkSpaces Applications (renamed from AppStream 2.0)")
    print()
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            ai_response = data.get('response', '')
            recommendations = data.get('recommendations', [])
            
            print(f"✅ Response received")
            print(f"\nAI Response (first 300 chars):")
            print(f"   {ai_response[:300]}...")
            
            # Check if response mentions WorkSpaces Applications
            mentions_applications = 'WorkSpaces Applications' in ai_response
            mentions_rename = 'AppStream' in ai_response and 'renamed' in ai_response.lower()
            
            print(f"\n📊 Analysis:")
            print(f"   Mentions WorkSpaces Applications: {mentions_applications}")
            print(f"   Mentions rename from AppStream: {mentions_rename}")
            
            if mentions_applications:
                print(f"   ✅ CORRECT - Talks about WorkSpaces Applications")
            else:
                print(f"   ❌ INCORRECT - Doesn't mention WorkSpaces Applications")
            
            print(f"\n📝 Recommendations: {len(recommendations)}")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"   {i}. {rec.get('title', 'N/A')[:60]}...")
            
            return mentions_applications
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def test_workspaces_personal_explicit(api_endpoint, environment):
    """Test explicit query about 'WorkSpaces Personal'"""
    print(f"\n{'=' * 70}")
    print(f"Test 3: Query about 'WorkSpaces Personal' in {environment.upper()}")
    print(f"{'=' * 70}")
    
    url = f"{api_endpoint}/chat"
    payload = {
        "message": "What is Amazon WorkSpaces Personal?",
        "conversation_id": f"test_workspaces_personal_{environment}"
    }
    
    print(f"Query: {payload['message']}")
    print(f"Expected: Should explain WorkSpaces Personal (VDI service)")
    print()
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            ai_response = data.get('response', '')
            recommendations = data.get('recommendations', [])
            
            print(f"✅ Response received")
            print(f"\nAI Response (first 300 chars):")
            print(f"   {ai_response[:300]}...")
            
            # Check if response is about VDI/virtual desktops
            mentions_vdi = any(term in ai_response.lower() for term in ['vdi', 'virtual desktop', 'desktop as a service', 'daas'])
            mentions_applications = 'WorkSpaces Applications' in ai_response
            
            print(f"\n📊 Analysis:")
            print(f"   Mentions VDI/Virtual Desktop: {mentions_vdi}")
            print(f"   Incorrectly mentions WorkSpaces Applications: {mentions_applications}")
            
            if mentions_vdi and not mentions_applications:
                print(f"   ✅ CORRECT - Explains WorkSpaces Personal as VDI")
            elif mentions_applications:
                print(f"   ❌ INCORRECT - Confuses with WorkSpaces Applications")
            else:
                print(f"   ⚠️  UNCLEAR - Doesn't clearly explain the service")
            
            print(f"\n📝 Recommendations: {len(recommendations)}")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"   {i}. {rec.get('title', 'N/A')[:60]}...")
            
            return mentions_vdi and not mentions_applications
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def main():
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python test_workspaces_personal_chat.py <environment>")
        print("Environments: staging, production")
        sys.exit(1)
    
    environment = sys.argv[1].lower()
    
    if environment == 'staging':
        api_endpoint = STAGING_API
    elif environment == 'production':
        api_endpoint = PRODUCTION_API
    else:
        print(f"❌ Invalid environment: {environment}")
        print("Valid environments: staging, production")
        sys.exit(1)
    
    print("🧪 Testing WorkSpaces Personal vs WorkSpaces Applications")
    print(f"Environment: {environment.upper()}")
    print(f"API: {api_endpoint}")
    
    results = {
        'workspaces_query': test_workspaces_query(api_endpoint, environment),
        'appstream_query': test_appstream_query(api_endpoint, environment),
        'workspaces_personal_explicit': test_workspaces_personal_explicit(api_endpoint, environment)
    }
    
    print(f"\n{'=' * 70}")
    print("📊 Test Summary")
    print(f"{'=' * 70}")
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name.replace('_', ' ').title()}")
    
    all_passed = all(results.values())
    
    print(f"\n{'=' * 70}")
    if all_passed:
        print(f"✅ All tests passed in {environment.upper()}!")
        print("\n💡 The chatbot correctly distinguishes between:")
        print("   - WorkSpaces Personal (VDI service)")
        print("   - WorkSpaces Applications (formerly AppStream 2.0)")
    else:
        print(f"⚠️  Some tests failed in {environment.upper()}")
        print("\n💡 The chatbot may still be confusing:")
        print("   - WorkSpaces (should map to WorkSpaces Personal)")
        print("   - AppStream 2.0 (should map to WorkSpaces Applications)")
    print(f"{'=' * 70}")

if __name__ == '__main__':
    main()
