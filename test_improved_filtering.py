"""
Test improved EUC relevance filtering
"""

import json
import urllib.request

AWS_DOCS_SEARCH_API = 'https://proxy.search.docs.aws.com/search'

def search_with_improved_filter(query, limit=5):
    """Search with improved EUC filtering"""
    try:
        request_body = {
            'textQuery': {'input': query},
            'contextAttributes': [{'key': 'domain', 'value': 'docs.aws.amazon.com'}],
            'acceptSuggestionBody': 'RawText',
            'locales': ['en_us'],
        }
        
        json_data = json.dumps(request_body).encode('utf-8')
        req = urllib.request.Request(
            AWS_DOCS_SEARCH_API,
            data=json_data,
            headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        results = []
        suggestions = data.get('suggestions', [])
        
        # EUC URL patterns (strict)
        euc_url_patterns = [
            '/workspaces/', '/workspaces-', 
            '/appstream', 
            '/workdocs/', '/workdocs-',
            '/chime/', '/chime-',
            '/connect/', '/connect-',
            '/dcv/', '/nice-dcv/',
            '/workspaces-thin-client/'
        ]
        
        # Title keywords (flexible)
        euc_title_keywords = [
            'workspaces', 'appstream', 'workdocs', 'chime', 'connect',
            'dcv', 'nice dcv', 'thin client'
        ]
        
        skipped_invalid = 0
        skipped_non_euc = 0
        
        for suggestion in suggestions:
            if len(results) >= limit:
                break
                
            if 'textExcerptSuggestion' in suggestion:
                text_suggestion = suggestion['textExcerptSuggestion']
                url = text_suggestion.get('link', '')
                title = text_suggestion.get('title', '')
                
                # Filter invalid URLs
                if '.doccarchive' in url or not (url.endswith('.html') or url.endswith('/')):
                    skipped_invalid += 1
                    continue
                
                # IMPROVED RELEVANCE FILTER
                url_lower = url.lower()
                title_lower = title.lower()
                
                # Check URL patterns (strict)
                url_matches = any(pattern in url_lower for pattern in euc_url_patterns)
                
                # Check title keywords (flexible)
                title_matches = any(keyword in title_lower for keyword in euc_title_keywords)
                
                is_euc_relevant = url_matches or title_matches
                
                if not is_euc_relevant:
                    print(f"  ⚠️  Skipped: {title}")
                    print(f"      URL: {url}")
                    skipped_non_euc += 1
                    continue
                
                results.append({'title': title, 'url': url})
        
        print(f"\n✅ Found {len(results)} EUC-relevant results")
        print(f"   Skipped {skipped_invalid} invalid URLs")
        print(f"   Skipped {skipped_non_euc} non-EUC docs")
        
        return results
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return []


def test_query(query):
    """Test a query"""
    print(f"\n{'='*80}")
    print(f"Testing: {query}")
    print(f"{'='*80}")
    
    results = search_with_improved_filter(query, limit=5)
    
    print(f"\nResults:")
    for i, result in enumerate(results, 1):
        print(f"\n[{i}] {result['title']}")
        print(f"    {result['url']}")


if __name__ == '__main__':
    # Test problematic queries
    test_query("AppStream 2.0 storage connector")  # Should NOT return Athena connector
    test_query("How do I configure Amazon WorkSpaces?")
    test_query("virtual desktop")
