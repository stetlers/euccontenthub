#!/usr/bin/env python3
"""
Verify production crawler authentication is working

Run this after CloudFront cache clears (2-3 minutes after deployment)
"""

import requests
import sys

def test_production():
    """Test production /crawl endpoint"""
    api_url = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod'
    
    print("="*70)
    print("PRODUCTION CRAWLER AUTHENTICATION TEST")
    print("="*70)
    print(f"\nAPI URL: {api_url}/crawl")
    
    # Test unauthenticated request
    print("\n1. Testing unauthenticated request...")
    try:
        response = requests.post(f"{api_url}/crawl")
        
        if response.status_code == 401:
            print("   ✅ PASS: Returns 401 Unauthorized")
            data = response.json()
            print(f"   Response: {data}")
            return True
        else:
            print(f"   ❌ FAIL: Expected 401, got {response.status_code}")
            print(f"   Response: {response.json()}")
            return False
    
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        return False

def main():
    print("\n🔐 Verifying production crawler authentication...\n")
    
    success = test_production()
    
    print("\n" + "="*70)
    if success:
        print("✅ PRODUCTION AUTHENTICATION WORKING!")
        print("="*70)
        print("\nNext steps:")
        print("1. Visit https://awseuccontent.com")
        print("2. Verify crawler button hidden when signed out")
        print("3. Sign in")
        print("4. Verify crawler button visible and works")
        return 0
    else:
        print("❌ PRODUCTION AUTHENTICATION NOT WORKING")
        print("="*70)
        print("\nTroubleshooting:")
        print("1. Wait a few more minutes for CloudFront cache to clear")
        print("2. Check Lambda version: aws lambda get-alias --function-name aws-blog-api --name production")
        print("3. Run: python force_complete_cache_clear.py")
        return 1

if __name__ == '__main__':
    sys.exit(main())
