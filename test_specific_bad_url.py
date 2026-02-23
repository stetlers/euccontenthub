"""
Test to find what query returns the bad URL
"""

import json
import urllib.request

AWS_DOCS_SEARCH_API = 'https://proxy.search.docs.aws.com/search'

def search_and_check(query):
    """Search and check for the bad URL"""
    print(f"\nTesting: {query}")
    
    try:
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
                'User-Agent': 'Mozilla/5.0'
            },
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        suggestions = data.get('suggestions', [])
        
        # Check for the bad URL
        for i, suggestion in enumerate(suggestions, 1):
            if 'textExcerptSuggestion' in suggestion:
                text_suggestion = suggestion['textExcerptSuggestion']
                url = text_suggestion.get('link', '')
                title = text_suggestion.get('title', '')
                
                if 'res/latest/ug/virtual-desktops' in url:
                    print(f"  ❌ FOUND BAD URL at position {i}:")
                    print(f"     Title: {title}")
                    print(f"     URL: {url}")
                    return True
        
        print(f"  ✅ Bad URL not found in top 100 results")
        return False
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False


if __name__ == '__main__':
    # Test various queries
    queries = [
        "AppStream 2.0",
        "Amazon AppStream 2.0",
        "WorkSpaces Applications",
        "Amazon WorkSpaces Applications",
        "AppStream storage connector",
        "WorkSpaces",
        "Amazon WorkSpaces",
        "virtual desktop",
        "DaaS",
        "application streaming"
    ]
    
    for query in queries:
        search_and_check(query)
