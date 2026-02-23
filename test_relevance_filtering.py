"""
Test relevance filtering for AWS docs
"""

import json
import urllib.request

AWS_DOCS_SEARCH_API = 'https://proxy.search.docs.aws.com/search'

def search_with_relevance_filter(query, limit=5):
    """Search AWS docs with EUC relevance filtering"""
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
        
        results = []
        suggestions = data.get('suggestions', [])
        
        # EUC service identifiers
        euc_service_identifiers = [
            'workspaces', 'appstream', 'workdocs', 'chime', 'connect',
            'dcv', 'nice-dcv', 'thin-client', 'thinclient'
        ]
        
        skipped_non_euc = 0
        skipped_invalid = 0
        
        for suggestion in suggestions:
            if len(results) >= limit:
                break
                
            if 'textExcerptSuggestion' in suggestion:
                text_suggestion = suggestion['textExcerptSuggestion']
                url = text_suggestion.get('link', '')
                title = text_suggestion.get('title', '')
                
                # Filter invalid URLs
                if '.doccarchive' in url:
                    skipped_invalid += 1
                    continue
                
                if not (url.endswith('.html') or url.endswith('/')):
                    skipped_invalid += 1
                    continue
                
                # RELEVANCE FILTER
                url_lower = url.lower()
                title_lower = title.lower()
                is_euc_relevant = any(
                    service_id in url_lower or service_id in title_lower 
                    for service_id in euc_service_identifiers
                )
                
                if not is_euc_relevant:
                    skipped_non_euc += 1
                    continue
                
                results.append({
                    'title': title,
                    'url': url
                })
        
        print(f"\n✅ Found {len(results)} EUC-relevant results")
        print(f"   Skipped {skipped_invalid} invalid URLs")
        print(f"   Skipped {skipped_non_euc} non-EUC docs")
        
        return results
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return []


def test_query(query):
    """Test a query with relevance filtering"""
    print(f"\n{'='*80}")
    print(f"Testing: {query}")
    print(f"{'='*80}")
    
    results = search_with_relevance_filter(query, limit=5)
    
    print(f"\nResults:")
    for i, result in enumerate(results, 1):
        print(f"\n[{i}] {result['title']}")
        print(f"    {result['url']}")
        
        # Verify it's EUC-related
        url_lower = result['url'].lower()
        title_lower = result['title'].lower()
        if any(s in url_lower or s in title_lower for s in ['workspaces', 'appstream', 'chime', 'connect', 'workdocs', 'dcv']):
            print(f"    ✅ EUC-relevant")
        else:
            print(f"    ⚠️  NOT EUC-relevant (should have been filtered!)")


if __name__ == '__main__':
    # Test queries that might return non-EUC results
    test_query("virtual desktop")  # This returned RES docs before
    test_query("How do I configure Amazon WorkSpaces?")
    test_query("Tell me about AppStream 2.0")
    test_query("application streaming")
