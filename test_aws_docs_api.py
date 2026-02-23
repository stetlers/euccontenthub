"""
Test script for AWS Documentation Search API
Tests the correct API endpoint found from AWS MCP server source code
"""

import json
import urllib.request
import urllib.parse

# Correct API endpoint from AWS MCP server
AWS_DOCS_SEARCH_API = 'https://proxy.search.docs.aws.com/search'

def test_aws_docs_search(query, limit=5):
    """
    Test AWS documentation search with the correct API endpoint
    """
    print(f"\n{'='*80}")
    print(f"Testing AWS Docs Search API")
    print(f"Query: {query}")
    print(f"Limit: {limit}")
    print(f"{'='*80}\n")
    
    try:
        # Build request body (matches AWS MCP server format)
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
        
        print(f"Request URL: {AWS_DOCS_SEARCH_API}")
        print(f"Request Body: {json.dumps(request_body, indent=2)}\n")
        
        # Convert request body to JSON
        json_data = json.dumps(request_body).encode('utf-8')
        
        # Make POST request with proper headers
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
            print(f"Response Status: {response.status}")
            data = json.loads(response.read().decode('utf-8'))
        
        # Parse results (matches AWS MCP server response format)
        results = []
        suggestions = data.get('suggestions', [])
        
        print(f"Found {len(suggestions)} total suggestions\n")
        
        for i, suggestion in enumerate(suggestions[:limit]):
            if 'textExcerptSuggestion' in suggestion:
                text_suggestion = suggestion['textExcerptSuggestion']
                
                # Extract context (snippet) - prioritize seo_abstract, then abstract, then summary
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
                
                # Truncate long snippets
                if context and len(context) > 200:
                    context = context[:200] + '...'
                
                result = {
                    'rank': i + 1,
                    'title': text_suggestion.get('title', ''),
                    'url': text_suggestion.get('link', ''),
                    'snippet': context or ''
                }
                results.append(result)
                
                print(f"Result {i+1}:")
                print(f"  Title: {result['title']}")
                print(f"  URL: {result['url']}")
                print(f"  Snippet: {result['snippet'][:100]}...")
                print()
        
        print(f"✅ SUCCESS: Found {len(results)} results")
        return results
    
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP ERROR: {e.code} - {e.reason}")
        print(f"Response: {e.read().decode('utf-8')}")
        return []
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


if __name__ == '__main__':
    # Test 1: WorkSpaces query
    test_aws_docs_search("Amazon WorkSpaces configuration", limit=3)
    
    # Test 2: Lambda query
    test_aws_docs_search("AWS Lambda function URLs", limit=3)
    
    # Test 3: S3 query
    test_aws_docs_search("S3 bucket versioning", limit=3)
    
    print(f"\n{'='*80}")
    print("All tests completed!")
    print(f"{'='*80}\n")
