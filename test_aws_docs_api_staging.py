"""
Test AWS Docs API integration in staging Lambda
"""

import json
import urllib.request

STAGING_API_URL = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/chat'

def test_staging_chat(message):
    """Test chat endpoint in staging"""
    print(f"\n{'='*80}")
    print(f"Testing Staging Chat with AWS Docs API")
    print(f"Message: {message}")
    print(f"{'='*80}\n")
    
    try:
        # Build request
        request_body = {
            'message': message
        }
        
        json_data = json.dumps(request_body).encode('utf-8')
        
        req = urllib.request.Request(
            STAGING_API_URL,
            data=json_data,
            headers={
                'Content-Type': 'application/json'
            },
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        print(f"✅ Response received")
        print(f"\nAI Response:")
        print(f"{data.get('response', 'No response')}\n")
        
        # Check for AWS docs
        aws_docs = data.get('aws_docs', [])
        if aws_docs:
            print(f"AWS Documentation Results ({len(aws_docs)}):")
            for i, doc in enumerate(aws_docs, 1):
                print(f"\n  {i}. {doc.get('title', 'No title')}")
                print(f"     URL: {doc.get('url', 'No URL')}")
                print(f"     Snippet: {doc.get('snippet', 'No snippet')[:100]}...")
        else:
            print("⚠️  No AWS docs returned (query may not have triggered AWS docs search)")
        
        # Check for blog recommendations
        recommendations = data.get('recommendations', [])
        if recommendations:
            print(f"\nBlog Post Recommendations ({len(recommendations)}):")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"\n  {i}. {rec.get('title', 'No title')}")
                print(f"     URL: {rec.get('url', 'No URL')}")
        
        return data
    
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP ERROR: {e.code} - {e.reason}")
        print(f"Response: {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    # Test 1: Query that should trigger AWS docs search
    test_staging_chat("How do I configure Amazon WorkSpaces?")
    
    # Test 2: Query with service rename
    test_staging_chat("Tell me about AppStream 2.0")
    
    # Test 3: Lambda query
    test_staging_chat("How do I create Lambda function URLs?")
    
    print(f"\n{'='*80}")
    print("All tests completed!")
    print(f"{'='*80}\n")
