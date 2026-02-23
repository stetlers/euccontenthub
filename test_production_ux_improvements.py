#!/usr/bin/env python3
"""
Test Production Chatbot UX Improvements
Tests the three new features:
1. Expandable view
2. Cart/clipboard integration
3. EUC-focused example questions
"""

import requests
import json

PRODUCTION_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod'
PRODUCTION_URL = 'https://awseuccontent.com'

def test_chat_response_structure():
    """Test that chat returns recommendations and AWS docs (for expandable view)"""
    print("=" * 70)
    print("Test 1: Chat Response Structure (for Expandable View)")
    print("=" * 70)
    
    url = f"{PRODUCTION_API}/chat"
    payload = {
        "message": "How do I configure Amazon WorkSpaces?",
        "conversation_id": "test_ux_improvements"
    }
    
    print(f"POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for recommendations (triggers expandable view)
            has_recommendations = 'recommendations' in data and len(data.get('recommendations', [])) > 0
            has_aws_docs = 'aws_docs' in data and len(data.get('aws_docs', [])) > 0
            
            print(f"\n✅ Response received")
            print(f"   - Has recommendations: {has_recommendations} ({len(data.get('recommendations', []))} posts)")
            print(f"   - Has AWS docs: {has_aws_docs} ({len(data.get('aws_docs', []))} docs)")
            print(f"   - Should trigger expandable view: {has_recommendations or has_aws_docs}")
            
            if has_recommendations:
                print(f"\n📝 Sample Recommendation:")
                rec = data['recommendations'][0]
                print(f"   - Title: {rec.get('title', 'N/A')[:60]}...")
                print(f"   - Post ID: {rec.get('post_id', 'N/A')}")
                print(f"   - Has post_id for cart: {'post_id' in rec}")
            
            if has_aws_docs:
                print(f"\n📚 Sample AWS Doc:")
                doc = data['aws_docs'][0]
                print(f"   - Title: {doc.get('title', 'N/A')[:60]}...")
                print(f"   - URL: {doc.get('url', 'N/A')}")
                print(f"   - Has URL for clipboard: {'url' in doc}")
            
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def test_frontend_files():
    """Test that frontend files are deployed and contain new features"""
    print("\n" + "=" * 70)
    print("Test 2: Frontend Files Deployment")
    print("=" * 70)
    
    files_to_check = [
        ('chat-widget.js', ['isExpanded', 'toggleExpanded', 'addToCart', 'copyToClipboard', 'showNotification']),
        ('chat-widget.css', ['chat-window.expanded', 'chat-recommendation-add-btn', 'chat-citation-add-btn', 'chat-notification']),
        ('app.js', ['window.cartManager']),
        ('cart-manager.js', ['CartManager', 'addToCart']),
        ('cart-ui.js', ['CartUI'])
    ]
    
    all_passed = True
    
    for filename, keywords in files_to_check:
        url = f"{PRODUCTION_URL}/{filename}"
        print(f"\nChecking {filename}...")
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                
                found_keywords = []
                missing_keywords = []
                
                for keyword in keywords:
                    if keyword in content:
                        found_keywords.append(keyword)
                    else:
                        missing_keywords.append(keyword)
                
                if missing_keywords:
                    print(f"   ⚠️  Found {len(found_keywords)}/{len(keywords)} keywords")
                    print(f"   Missing: {', '.join(missing_keywords)}")
                    all_passed = False
                else:
                    print(f"   ✅ All {len(keywords)} keywords found")
                    print(f"   Keywords: {', '.join(found_keywords[:3])}...")
            else:
                print(f"   ❌ HTTP {response.status_code}")
                all_passed = False
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            all_passed = False
    
    return all_passed

def test_example_questions():
    """Test that example questions are EUC-focused"""
    print("\n" + "=" * 70)
    print("Test 3: EUC-Focused Example Questions")
    print("=" * 70)
    
    url = f"{PRODUCTION_URL}/chat-widget.js"
    
    print(f"Checking {url}...")
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            content = response.text
            
            # Check for new EUC-focused questions
            new_questions = [
                "How do I get started with Amazon WorkSpaces?",
                "What are best practices for WorkSpaces security?",
                "Tell me about AppStream 2.0 deployment"
            ]
            
            # Check for old generic questions (should NOT be present)
            old_questions = [
                "Tell me about serverless computing",
                "How do I get started with containers?",
                "Show me best practices for security"
            ]
            
            found_new = []
            found_old = []
            
            for question in new_questions:
                if question in content:
                    found_new.append(question)
            
            for question in old_questions:
                if question in content:
                    found_old.append(question)
            
            print(f"\n✅ New EUC-focused questions: {len(found_new)}/{len(new_questions)}")
            for q in found_new:
                print(f"   ✅ {q}")
            
            if found_old:
                print(f"\n⚠️  Old generic questions still present: {len(found_old)}")
                for q in found_old:
                    print(f"   ⚠️  {q}")
                return False
            else:
                print(f"\n✅ No old generic questions found")
            
            return len(found_new) == len(new_questions)
        else:
            print(f"❌ HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    print("🧪 Testing Production Chatbot UX Improvements")
    print("=" * 70)
    print(f"Production URL: {PRODUCTION_URL}")
    print(f"Production API: {PRODUCTION_API}")
    print()
    
    results = {
        'chat_response': test_chat_response_structure(),
        'frontend_files': test_frontend_files(),
        'example_questions': test_example_questions()
    }
    
    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name.replace('_', ' ').title()}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ All tests passed! UX improvements deployed successfully.")
        print("\n💡 Features now live:")
        print("   1. Expandable view (auto-expands on response)")
        print("   2. Cart integration (➕ button on recommendations)")
        print("   3. Clipboard integration (📋 button on AWS docs)")
        print("   4. EUC-focused example questions")
    else:
        print("⚠️  Some tests failed. Check results above.")
    print("=" * 70)

if __name__ == '__main__':
    main()
