#!/usr/bin/env python3
"""
Test crawler authentication fix

Tests:
1. Unauthenticated request to /crawl should return 401
2. Authenticated request to /crawl should return 202
"""

import requests
import sys

def test_unauthenticated(api_url):
    """Test that unauthenticated requests are rejected"""
    print("\n" + "="*70)
    print("TEST 1: Unauthenticated Request (should fail with 401)")
    print("="*70)
    
    try:
        response = requests.post(f"{api_url}/crawl")
        
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.json()}")
        
        if response.status_code == 401:
            print("  ✅ PASS: Unauthenticated request rejected")
            return True
        else:
            print("  ❌ FAIL: Expected 401, got", response.status_code)
            return False
    
    except Exception as e:
        print(f"  ❌ ERROR: {str(e)}")
        return False

def test_authenticated(api_url, token):
    """Test that authenticated requests are accepted"""
    print("\n" + "="*70)
    print("TEST 2: Authenticated Request (should succeed with 202)")
    print("="*70)
    
    try:
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(f"{api_url}/crawl", headers=headers)
        
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.json()}")
        
        if response.status_code == 202:
            print("  ✅ PASS: Authenticated request accepted")
            return True
        else:
            print(f"  ❌ FAIL: Expected 202, got {response.status_code}")
            return False
    
    except Exception as e:
        print(f"  ❌ ERROR: {str(e)}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_crawler_auth_fix.py <environment> [token]")
        print("  environment: staging or production")
        print("  token: (optional) JWT token for authenticated test")
        sys.exit(1)
    
    environment = sys.argv[1].lower()
    token = sys.argv[2] if len(sys.argv) > 2 else None
    
    if environment == 'staging':
        api_url = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'
    elif environment == 'production':
        api_url = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod'
    else:
        print(f"❌ Invalid environment: {environment}")
        print("   Valid: staging, production")
        sys.exit(1)
    
    print("\n" + "="*70)
    print(f"TESTING CRAWLER AUTHENTICATION - {environment.upper()}")
    print("="*70)
    print(f"API URL: {api_url}")
    
    # Test 1: Unauthenticated
    test1_passed = test_unauthenticated(api_url)
    
    # Test 2: Authenticated (if token provided)
    test2_passed = None
    if token:
        test2_passed = test_authenticated(api_url, token)
    else:
        print("\n" + "="*70)
        print("TEST 2: Skipped (no token provided)")
        print("="*70)
        print("  To test authenticated requests:")
        print(f"  python test_crawler_auth_fix.py {environment} <your-jwt-token>")
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"  Test 1 (Unauthenticated): {'✅ PASS' if test1_passed else '❌ FAIL'}")
    if test2_passed is not None:
        print(f"  Test 2 (Authenticated): {'✅ PASS' if test2_passed else '❌ FAIL'}")
    else:
        print(f"  Test 2 (Authenticated): ⏭️  SKIPPED")
    
    if test1_passed and (test2_passed is None or test2_passed):
        print("\n  🎉 All tests passed!")
        return 0
    else:
        print("\n  ❌ Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
