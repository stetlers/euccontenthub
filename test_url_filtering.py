"""
Test URL filtering in search_aws_documentation function
"""

import json
import urllib.request

AWS_DOCS_SEARCH_API = 'https://proxy.search.docs.aws.com/search'

def search_aws_documentation_with_filtering(query, limit=5):
    """
    Search AWS docs with URL filtering
    """
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
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        # Parse results with filtering
        results = []
        suggestions = data.get('suggestions', [])
        skipped_count = 0
        
        for i, suggestion in enumerate(suggestions):
            # Stop if we have enough valid results
            if len(results) >= limit:
                break
                
            if 'textExcerptSuggestion' in suggestion:
                text_suggestion = suggestion['textExcerptSuggestion']
                url = text_suggestion.get('link', '')
                title = text_suggestion.get('title', '')
                
                # Filter out invalid URLs
                if '.doccarchive' in url:
                    print(f"  ⚠️  Skipped DocC archive: {title}")
                    skipped_count += 1
                    continue
                
                if not (url.endswith('.html') or url.endswith('/')):
                    print(f"  ⚠️  Skipped non-HTML: {title}")
                    skipped_count += 1
                    continue
                
                # Extract context
                context = None
                metadata = text_suggestion.get('metadata', {})
                if 'seo_abstract' in metadata:
                    context = metadata['seo_abstract']
                elif 'abstract' in metadata:
                    context = metadata['abstract']
                elif 'summary' in text_suggestion:
                    context = text_suggestion['summary']
                elif 'suggestionBody' in text_suggestion:
                    context = text_suggestion['suggestionBody']
                
                if context and len(context) > 200:
                    context = context[:200] + '...'
                
                results.append({
                    'title': title,
                    'url': url,
                    'snippet': context or ''
                })
        
        print(f"\n✅ Found {len(results)} valid results (skipped {skipped_count} invalid URLs)")
        return results
    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return []


def test_query(query):
    """Test a query with URL filtering"""
    print(f"\n{'='*80}")
    print(f"Testing: {query}")
    print(f"{'='*80}\n")
    
    results = search_aws_documentation_with_filtering(query, limit=5)
    
    print(f"\nValid Results:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Snippet: {result['snippet'][:80]}...")


if __name__ == '__main__':
    # Test queries that might return bad URLs
    test_query("AppStream 2.0 storage connector")
    test_query("Amazon WorkSpaces configuration")
    test_query("Lambda function URLs")
