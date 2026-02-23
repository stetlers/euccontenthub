"""
Test AWS Docs API to see what URLs it returns
"""

import json
import urllib.request

AWS_DOCS_SEARCH_API = 'https://proxy.search.docs.aws.com/search'

def test_search(query):
    """Test AWS docs search and check URLs"""
    print(f"\n{'='*80}")
    print(f"Testing: {query}")
    print(f"{'='*80}\n")
    
    try:
        # Build request body
        request_body = {
            'textQuery': {
                'input': query,
            },
            'contextAttributes': [
                {'key': 'domain', 'value': 'docs.aws.amazon.com'}
            ],
            'acceptSuggestionBody': 'RawText',
            'locales': ['en_us'],
        }
        
        json_data = json.dumps(request_body).encode('utf-8')
        
        req = urllib.request.Request(
            AWS_DOCS_SEARCH_API,
            data=json_data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        suggestions = data.get('suggestions', [])
        
        print(f"Found {len(suggestions)} results\n")
        
        for i, suggestion in enumerate(suggestions[:5], 1):
            if 'textExcerptSuggestion' in suggestion:
                text_suggestion = suggestion['textExcerptSuggestion']
                title = text_suggestion.get('title', 'No title')
                url = text_suggestion.get('link', 'No URL')
                
                print(f"{i}. {title}")
                print(f"   URL: {url}")
                
                # Check if URL looks valid
                if '.doccarchive' in url:
                    print(f"   ⚠️  WARNING: This is a DocC archive URL (API reference)")
                elif url.endswith('.html'):
                    print(f"   ✅ Valid HTML page")
                else:
                    print(f"   ⚠️  Unusual URL format")
                
                print()
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # Test queries that might return bad URLs
    test_search("AppStream 2.0")
    test_search("Amazon WorkSpaces configuration")
    test_search("Lambda function URLs")
