"""
Test AWS Docs API to see what it returns for EUC queries
"""

import json
import urllib.request

AWS_DOCS_SEARCH_API = 'https://proxy.search.docs.aws.com/search'

def test_search(query):
    """Test AWS docs search and check relevance"""
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
        
        for i, suggestion in enumerate(suggestions[:10], 1):
            if 'textExcerptSuggestion' in suggestion:
                text_suggestion = suggestion['textExcerptSuggestion']
                title = text_suggestion.get('title', 'No title')
                url = text_suggestion.get('link', 'No URL')
                
                # Extract metadata
                metadata = text_suggestion.get('metadata', {})
                product = metadata.get('aws-docs-search-product', 'Unknown')
                guide_type = metadata.get('aws-docs-search-guide', 'Unknown')
                
                print(f"{i}. {title}")
                print(f"   URL: {url}")
                print(f"   Product: {product}")
                print(f"   Guide Type: {guide_type}")
                
                # Check relevance
                query_lower = query.lower()
                url_lower = url.lower()
                title_lower = title.lower()
                
                # Check if URL/title contains relevant service names
                relevant_services = ['workspaces', 'appstream', 'workdocs', 'chime', 'connect']
                is_relevant = any(service in url_lower or service in title_lower for service in relevant_services)
                
                if is_relevant:
                    print(f"   ✅ RELEVANT to EUC query")
                else:
                    print(f"   ⚠️  NOT RELEVANT to EUC query")
                
                print()
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # Test EUC-specific queries
    test_search("How do I configure Amazon WorkSpaces?")
    test_search("Tell me about AppStream 2.0")
    test_search("Amazon WorkSpaces Applications storage connector")
