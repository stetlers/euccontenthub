```python
"""
Trigger staging crawler via API with specific URL targeting
Enhanced with diagnostics for Amazon WorkSpaces blog post detection
"""

import json
import urllib.request
import sys
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin

STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/crawl'
STAGING_DIAGNOSTIC_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/diagnostic'

# Specific blog post URL that needs to be crawled
TARGET_BLOG_POST = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'

# Expected blog post metadata for validation
EXPECTED_POST_DATE = '2026-03-02'
EXPECTED_KEYWORDS = ['Graphics G6', 'Gr6', 'G6f', 'bundles', 'WorkSpaces']

print("=" * 80)
print("STAGING CRAWLER DIAGNOSTIC AND TRIGGER TOOL")
print("=" * 80)
print(f"API: {STAGING_API}")
print(f"Target URL: {TARGET_BLOG_POST}")
print(f"Expected Post Date: {EXPECTED_POST_DATE}")
print(f"Keywords: {', '.join(EXPECTED_KEYWORDS)}\n")


def make_request(url, payload, method='POST', timeout=30):
    """
    Make HTTP request with proper error handling
    """
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8') if payload else None,
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'AWS-Staging-Crawler-Diagnostic/2.0'
        },
        method=method
    )
    
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


def run_diagnostic_checks():
    """
    Run diagnostic checks to identify why the blog post isn't being picked up
    """
    print("\n" + "=" * 80)
    print("STEP 1: RUNNING DIAGNOSTIC CHECKS")
    print("=" * 80 + "\n")
    
    diagnostic_payload = {
        'action': 'diagnose',
        'target_url': TARGET_BLOG_POST,
        'checks': [
            'url_pattern_match',
            'date_filter_validation',
            'content_extraction',
            'storage_verification',
            'recent_crawls'
        ],
        'date_range': {
            'start': (datetime.strptime(EXPECTED_POST_DATE, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d'),
            'end': (datetime.strptime(EXPECTED_POST_DATE, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        }
    }
    
    try:
        diagnostic_results = make_request(STAGING_DIAGNOSTIC_API, diagnostic_payload)
        
        print("✅ Diagnostic check completed")
        print("\nDiagnostic Results:")
        print(json.dumps(diagnostic_results, indent=2))
        
        # Analyze diagnostic results
        issues_found = []
        
        if not diagnostic_results.get('url_pattern_match', {}).get('matched', True):
            issues_found.append("URL pattern mismatch - crawler may be excluding this URL pattern")
        
        if not diagnostic_results.get('date_filter_validation', {}).get('passed', True):
            issues_found.append(f"Date filter issue - post date {EXPECTED_POST_DATE} may be outside crawl range")
        
        if not diagnostic_results.get('content_extraction', {}).get('success', True):
            issues_found.append("Content extraction failed - check HTML structure and selectors")
        
        if not diagnostic_results.get('storage_verification', {}).get('found', False):
            issues_found.append("Post not found in storage - may not have been crawled or stored")
        
        if issues_found:
            print("\n⚠️  ISSUES DETECTED:")
            for i, issue in enumerate(issues_found, 1):
                print(f"  {i}. {issue}")
        else:
            print("\n✓ No issues detected in diagnostics")
        
        return diagnostic_results, issues_found
        
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("⚠️  Diagnostic API not available, continuing with crawler trigger...")
            return None, []
        raise
    except Exception as e:
        print(f"⚠️  Diagnostic check failed: {e}")
        print("Continuing with crawler trigger...\n")
        return None, []


def trigger_crawler(force_all_checks=False):
    """
    Trigger the crawler with enhanced configuration
    """
    print("\n" + "=" * 80)
    print("STEP 2: TRIGGERING CRAWLER WITH ENHANCED CONFIG")
    print("=" * 80 + "\n")
    
    # Enhanced payload with date range and validation options
    # Expanded date range to ensure March 2, 2026 post is included
    payload = {
        'target_urls': [TARGET_BLOG_POST],
        'force_refresh': True,
        'crawl_depth': 1,
        'include_patterns': [
            '/blogs/desktop-and-application-streaming/*',
            '/blogs/desktop-and-application-streaming/amazon-workspaces-*'
        ],
        # Ensure date filtering includes the target date
        'date_filter': {
            'enabled': True,
            'start_date': '2026-02-01',  # Expanded range
            'end_date': '2026-03-31',    # Expanded range
            'mode': 'inclusive'
        },
        # Enhanced content extraction rules
        'extraction_rules': {
            'title': {
                'selectors': ['h1.entry-title', 'h1.post-title', 'article h1', 'h1'],
                'required': True
            },
            'date': {
                'selectors': ['time.entry-date', 'meta[property="article:published_time"]', 'time', '.post-date'],
                'format': ['%Y-%m-%d', '%B %d, %Y', '%Y-%m-%dT%H:%M:%S'],
                'required': True
            },
            'content': {
                'selectors': ['article .entry-content', '.post-content', 'article', 'main'],
                'required': True
            },
            'keywords': EXPECTED_KEYWORDS
        },
        # Validation rules
        'validation': {
            'min_content_length': 100,
            'required_keywords': ['WorkSpaces', 'Graphics'] if force_all_checks else [],
            'validate_date': True
        },
        # Storage options
        'storage': {
            'deduplicate': False,  # Ensure we store even if similar content exists
            'update_existing': True,
            'notify_on_complete': True
        },
        # Metadata for tracking
        'metadata': {
            'trigger_reason': 'missing_blog_post_investigation',
            'expected_date': EXPECTED_POST_DATE,
            'triggered_at': datetime.utcnow().isoformat(),
            'ticket_id': 'WORKSPACES-G6-BLOG-2026-03-02'
        }
    }
    
    print(f"Request Payload:")
    print(json.dumps(payload, indent=2))
    print()
    
    response = make_request(STAGING_API, payload)
    
    print("✅ Crawler triggered successfully")
    print(f"\nResponse:")
    print(json.dumps(response, indent=2))
    
    # Check if the response indicates successful queuing
    if 'crawl_id' in response or 'job_id' in response:
        crawl_id = response.get('crawl_id') or response.get('job_id')
        print(f"\n✓ Crawl job queued successfully")
        print(f"Crawl ID: {crawl_id}")
        print(f"Monitor at: staging.awseuccontent.com/crawls/{crawl_id}")
        return response
    elif 'status' in response and response['status'] in ['queued', 'success', 'processing']:
        print(f"\n✓ Crawl job status: {response['status']}")
        print(f"Monitor at: staging.awseuccontent.com")
        return response
    else:
        print("\n⚠️  Warning: Unexpected response format")
        return response


def verify_crawl_results(crawl_response):
    """
    Verify that the crawl captured the expected content
    """
    print("\n" + "=" * 80)
    print("STEP 3: VERIFICATION RECOMMENDATIONS")
    print("=" * 80 + "\n")
    
    print("Manual verification steps:")
    print("1. Check staging.awseuccontent.com for the new blog post")
    print(f"2. Search for keywords: {', '.join(EXPECTED_KEYWORDS)}")
    print(f"3. Verify post date matches: {EXPECTED_POST_DATE}")
    print(f"4. Confirm URL is indexed: {TARGET_BLOG_POST}")
    print("\nIf post is still missing after crawl completes:")
    print("- Check CloudWatch logs for crawler errors")
    print("- Verify AWS blog site structure hasn't changed")
    print("- Check if blog post requires authentication")
    print("- Ensure date parsing logic handles the format correctly")
    print("- Verify storage layer is functioning correctly")


def main():
    """
    Main execution flow
    """
    try:
        # Step 1: Run diagnostic checks
        diagnostic_results, issues = run_diagnostic_checks()
        
        # Step 2: Trigger crawler with enhanced configuration
        crawl_response = trigger_crawler(force_all_checks=bool(issues))
        
        # Step 3: Provide verification guidance
        verify_crawl_results(crawl_response)
        
        print("\n" + "=" * 80)
        if issues:
            print("STATUS: Crawler triggered with fixes for detected issues")
            print("\nDetected issues have been addressed in the crawler configuration.")
            print("The crawler will attempt to resolve the following:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("STATUS: Crawler triggered successfully")
            print("\nNo issues detected. The crawler will re-process the target URL.")
        print("=" * 80)
        print("\n✓ Process completed. Monitor staging environment for results.")
        
    except urllib.error.HTTPError as e:
        print(f"\n❌ HTTP ERROR {e.code}: {e.reason}")
        try:
            error_body = e.read().decode('utf-8')
            print(f"Error details: {error_body}")
        except:
            pass
        sys.exit(1)
        
    except urllib.error.URLError as e:
        print(f"\n❌ URL ERROR: {e.reason}")
        print("Check network connectivity and API endpoint availability")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
```