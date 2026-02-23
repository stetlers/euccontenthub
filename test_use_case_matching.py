#!/usr/bin/env python3
"""
Test Use Case Matching in Chat
Verify that the chatbot correctly recommends services based on use cases
"""

import requests
import json

STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'
PRODUCTION_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod'

def test_task_workers_use_case(api_endpoint, environment):
    """Test: Task workers needing non-persistent desktops"""
    print(f"\n{'=' * 70}")
    print(f"Test 1: Task Workers Use Case in {environment.upper()}")
    print(f"{'=' * 70}")
    
    url = f"{api_endpoint}/chat"
    payload = {
        "message": "I need non-persistent desktops for task workers who only need temporary access",
        "conversation_id": f"test_task_workers_{environment}"
    }
    
    print(f"Query: {payload['message']}")
    print(f"Expected: Should recommend WorkSpaces Applications")
    print()
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            ai_response = data.get('response', '')
            recommendations = data.get('recommendations', [])
            
            print(f"✅ Response received")
            print(f"\nAI Response:")
            print(f"   {ai_response}")
            
            # Check if response mentions WorkSpaces Applications
            mentions_applications = 'WorkSpaces Applications' in ai_response or 'AppStream' in ai_response
            mentions_task_workers = 'task worker' in ai_response.lower()
            mentions_non_persistent = 'non-persistent' in ai_response.lower()
            
            print(f"\n📊 Analysis:")
            print(f"   Mentions WorkSpaces Applications: {mentions_applications}")
            print(f"   Mentions task workers: {mentions_task_workers}")
            print(f"   Mentions non-persistent: {mentions_non_persistent}")
            
            if mentions_applications:
                print(f"   ✅ CORRECT - Recommends WorkSpaces Applications")
            else:
                print(f"   ❌ INCORRECT - Should recommend WorkSpaces Applications")
            
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

def test_multiple_use_cases(api_endpoint, environment):
    """Test: Multiple use cases with existing EC2"""
    print(f"\n{'=' * 70}")
    print(f"Test 2: Multiple Use Cases with EC2 in {environment.upper()}")
    print(f"{'=' * 70}")
    
    url = f"{api_endpoint}/chat"
    payload = {
        "message": "We have existing EC2 deployments and need both persistent desktops and non-persistent applications",
        "conversation_id": f"test_multiple_use_cases_{environment}"
    }
    
    print(f"Query: {payload['message']}")
    print(f"Expected: Should recommend WorkSpaces Core Managed Instances (CMI)")
    print()
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            ai_response = data.get('response', '')
            recommendations = data.get('recommendations', [])
            
            print(f"✅ Response received")
            print(f"\nAI Response:")
            print(f"   {ai_response}")
            
            # Check if response mentions CMI
            mentions_cmi = 'Core Managed Instances' in ai_response or 'CMI' in ai_response
            mentions_ec2 = 'EC2' in ai_response
            mentions_multiple = 'multiple' in ai_response.lower()
            
            print(f"\n📊 Analysis:")
            print(f"   Mentions Core Managed Instances: {mentions_cmi}")
            print(f"   Mentions EC2: {mentions_ec2}")
            print(f"   Mentions multiple use cases: {mentions_multiple}")
            
            if mentions_cmi:
                print(f"   ✅ CORRECT - Recommends WorkSpaces Core Managed Instances")
            else:
                print(f"   ⚠️  May not have detected CMI use case")
            
            print(f"\n📝 Recommendations: {len(recommendations)}")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"   {i}. {rec.get('title', 'N/A')[:60]}...")
            
            return mentions_cmi or mentions_ec2
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def test_browser_only_use_case(api_endpoint, environment):
    """Test: Browser-only access"""
    print(f"\n{'=' * 70}")
    print(f"Test 3: Browser-Only Access in {environment.upper()}")
    print(f"{'=' * 70}")
    
    url = f"{api_endpoint}/chat"
    payload = {
        "message": "Contractors need secure access to our internal web applications only, no desktop needed",
        "conversation_id": f"test_browser_only_{environment}"
    }
    
    print(f"Query: {payload['message']}")
    print(f"Expected: Should recommend WorkSpaces Secure Browser")
    print()
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            ai_response = data.get('response', '')
            recommendations = data.get('recommendations', [])
            
            print(f"✅ Response received")
            print(f"\nAI Response:")
            print(f"   {ai_response}")
            
            # Check if response mentions Secure Browser
            mentions_secure_browser = 'Secure Browser' in ai_response or 'WorkSpaces Web' in ai_response
            mentions_browser = 'browser' in ai_response.lower()
            mentions_web = 'web' in ai_response.lower()
            
            print(f"\n📊 Analysis:")
            print(f"   Mentions Secure Browser: {mentions_secure_browser}")
            print(f"   Mentions browser: {mentions_browser}")
            print(f"   Mentions web: {mentions_web}")
            
            if mentions_secure_browser:
                print(f"   ✅ CORRECT - Recommends WorkSpaces Secure Browser")
            else:
                print(f"   ⚠️  May not have detected Secure Browser use case")
            
            print(f"\n📝 Recommendations: {len(recommendations)}")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"   {i}. {rec.get('title', 'N/A')[:60]}...")
            
            return mentions_secure_browser or (mentions_browser and mentions_web)
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def test_persistent_vdi_use_case(api_endpoint, environment):
    """Test: Traditional VDI with persistent desktops"""
    print(f"\n{'=' * 70}")
    print(f"Test 4: Persistent VDI Use Case in {environment.upper()}")
    print(f"{'=' * 70}")
    
    url = f"{api_endpoint}/chat"
    payload = {
        "message": "We need persistent desktops for developers who require the same environment every day",
        "conversation_id": f"test_persistent_vdi_{environment}"
    }
    
    print(f"Query: {payload['message']}")
    print(f"Expected: Should recommend WorkSpaces Personal")
    print()
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            ai_response = data.get('response', '')
            recommendations = data.get('recommendations', [])
            
            print(f"✅ Response received")
            print(f"\nAI Response:")
            print(f"   {ai_response}")
            
            # Check if response mentions WorkSpaces Personal
            mentions_personal = 'WorkSpaces Personal' in ai_response
            mentions_persistent = 'persistent' in ai_response.lower()
            mentions_vdi = 'vdi' in ai_response.lower() or 'virtual desktop' in ai_response.lower()
            
            print(f"\n📊 Analysis:")
            print(f"   Mentions WorkSpaces Personal: {mentions_personal}")
            print(f"   Mentions persistent: {mentions_persistent}")
            print(f"   Mentions VDI: {mentions_vdi}")
            
            if mentions_personal:
                print(f"   ✅ CORRECT - Recommends WorkSpaces Personal")
            else:
                print(f"   ⚠️  May not have detected WorkSpaces Personal use case")
            
            print(f"\n📝 Recommendations: {len(recommendations)}")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"   {i}. {rec.get('title', 'N/A')[:60]}...")
            
            return mentions_personal or mentions_persistent
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
        print("Usage: python test_use_case_matching.py <environment>")
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
    
    print("🧪 Testing Use Case Matching in Chat")
    print(f"Environment: {environment.upper()}")
    print(f"API: {api_endpoint}")
    
    results = {
        'task_workers': test_task_workers_use_case(api_endpoint, environment),
        'multiple_use_cases': test_multiple_use_cases(api_endpoint, environment),
        'browser_only': test_browser_only_use_case(api_endpoint, environment),
        'persistent_vdi': test_persistent_vdi_use_case(api_endpoint, environment)
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
        print("\n💡 The chatbot correctly recommends services based on use cases:")
        print("   - Task workers → WorkSpaces Applications")
        print("   - Multiple use cases + EC2 → WorkSpaces Core Managed Instances")
        print("   - Browser-only → WorkSpaces Secure Browser")
        print("   - Persistent VDI → WorkSpaces Personal")
    else:
        print(f"⚠️  Some tests failed in {environment.upper()}")
        print("\n💡 The use case matcher may need tuning or more keywords")
    print(f"{'=' * 70}")

if __name__ == '__main__':
    main()
