"""
Test staging Lambda to verify URL filtering is working
"""

import json
import urllib.request

STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/chat'

def test_staging_chat(query):
    """Test staging chat endpoint"""
    print(f"\n{'='*80}")
    print(f"Testing Staging Chat: {query}")
    print(f"{'='*80}\n")
    
    try:
        # Build request
        request_body = {
            'message': query
        }
        
        json_data = json.dumps(request_body).encode('utf-8')
        
        req = urllib.request.Request(
            STAGING_API,
            data=json_data,
            headers={
                'Content-Type': 'application/json'
            },
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        # Check response
        print(f"✅ Response received")
        print(f"\nAI Response: {data.get('response', 'No response')}")
        
        # Check AWS docs
        aws_docs = data.get('aws_docs', [])
        print(f"\n📚 AWS Documentation References: {len(aws_docs)}")
        
        for i, doc in enumerate(aws_docs, 1):
            url = doc.get('url', '')
            title = doc.get('title', 'No title')
            
            print(f"\n[{i}] {title}")
            print(f"    URL: {url}")
            
            # Check if URL is valid
            if '.doccarchive' in url:
                print(f"    ❌ INVALID: DocC archive URL (should have been filtered!)")
            elif url.endswith('.html') or url.endswith('/'):
                print(f"    ✅ Valid URL")
            else:
                print(f"    ⚠️  Unusual URL format")
        
        # Check blog recommendations
        recommendations = data.get('recommendations', [])
        print(f"\n📝 Blog Recommendations: {len(recommendations)}")
        
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec.get('title', 'No title')}")
            print(f"   Reason: {rec.get('relevance_reason', 'No reason')}")
        
        return data
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    # Test queries that previously returned bad URLs
    test_staging_chat("How do I configure Amazon WorkSpaces?")
    test_staging_chat("Tell me about AppStream 2.0 storage connector")
    test_staging_chat("How do I create Lambda function URLs?")
