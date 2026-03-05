```python
"""
Trigger staging crawler via API with specific URL targeting
Enhanced with diagnostic capabilities to investigate detection issues
"""

import json
import urllib.request
import sys
from datetime import datetime, timezone
import re

STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/crawl'
STAGING_DIAGNOSTIC_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/diagnostic'

# Specific blog post URL that needs to be crawled
TARGET_BLOG_POST = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'

# Expected metadata for the blog post
EXPECTED_POST_DATE = '2026-03-02'
EXPECTED_POST_TITLE = 'Amazon WorkSpaces Graphics G6 bundles'

def diagnose_crawler_filters():
    """
    Diagnose why the blog post might not be detected by staging crawler
    Checks date filtering, URL patterns, and crawler configuration
    """
    print("\n" + "="*80)
    print("DIAGNOSTIC MODE: Investigating crawler detection issues")
    print("="*80 + "\n")
    
    diagnostic_payload = {
        'action': 'diagnose',
        'target_url': TARGET_BLOG_POST,
        'expected_date': EXPECTED_POST_DATE,
        'checks': [
            'date_filter',
            'url_pattern_match',
            'content_type_filter',
            'duplicate_detection',
            'blacklist_check',
            'crawl_history'
        ]
    }
    
    try:
        req = urllib.request.Request(
            STAGING_DIAGNOSTIC_API,
            data=json.dumps(diagnostic_payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'AWS-Staging-Crawler-Diagnostic/1.0'
            },
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            diagnostic_data = json.loads(response.read().decode('utf-8'))
            
        print("📊 Diagnostic Results:")
        print(json.dumps(diagnostic_data, indent=2))
        
        # Analyze diagnostic results
        issues_found = []
        
        if 'date_filter' in diagnostic_data:
            date_filter = diagnostic_data['date_filter']
            if not date_filter.get('passes', True):
                issues_found.append(f"Date Filter: Post date {EXPECTED_POST_DATE} is outside allowed range")
                print(f"\n⚠️  DATE FILTER ISSUE:")
                print(f"   Configured range: {date_filter.get('min_date')} to {date_filter.get('max_date')}")
                print(f"   Post date: {EXPECTED_POST_DATE}")
        
        if 'url_pattern_match' in diagnostic_data:
            pattern_match = diagnostic_data['url_pattern_match']
            if not pattern_match.get('matches', True):
                issues_found.append("URL Pattern: Does not match configured include patterns")
                print(f"\n⚠️  URL PATTERN ISSUE:")
                print(f"   URL: {TARGET_BLOG_POST}")
                print(f"   Configured patterns: {pattern_match.get('patterns', [])}")
        
        if 'blacklist_check' in diagnostic_data:
            blacklist = diagnostic_data['blacklist_check']
            if blacklist.get('is_blacklisted', False):
                issues_found.append(f"Blacklist: URL is in exclusion list - {blacklist.get('reason')}")
        
        if issues_found:
            print(f"\n❌ Found {len(issues_found)} issue(s) preventing detection:")
            for idx, issue in enumerate(issues_found, 1):
                print(f"   {idx}. {issue}")
            return False
        else:
            print("\n✅ No obvious issues detected in crawler filters")
            return True
            
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("⚠️  Diagnostic API not available, using fallback analysis")
            return perform_local_diagnostic()
        else:
            print(f"⚠️  Diagnostic API error ({e.code}), continuing with crawl attempt")
            return True
    except Exception as e:
        print(f"⚠️  Diagnostic check failed: {e}, continuing with crawl attempt")
        return True

def perform_local_diagnostic():
    """
    Perform local diagnostic checks when API is unavailable
    """
    print("\n📋 Local Diagnostic Analysis:")
    
    # Check URL structure
    print("\n1. URL Structure Check:")
    if '/blogs/desktop-and-application-streaming/' in TARGET_BLOG_POST:
        print("   ✓ URL matches expected blog pattern")
    else:
        print("   ✗ URL does not match blog pattern")
        return False
    
    # Check date expectations
    print("\n2. Date Range Check:")
    try:
        post_date = datetime.strptime(EXPECTED_POST_DATE, '%Y-%m-%d')
        current_date = datetime.now(timezone.utc)
        
        if post_date > current_date:
            print(f"   ⚠️  Post date {EXPECTED_POST_DATE} is in the future")
            print(f"   Current date: {current_date.strftime('%Y-%m-%d')}")
            print(f"   This may be filtered by staging if it enforces past-date-only")
            return False
        else:
            print(f"   ✓ Post date is valid (not in future)")
    except Exception as e:
        print(f"   ⚠️  Could not parse date: {e}")
    
    # Check URL accessibility
    print("\n3. URL Accessibility Check:")
    try:
        req = urllib.request.Request(
            TARGET_BLOG_POST,
            headers={'User-Agent': 'AWS-Crawler-Test/1.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            content_type = response.headers.get('Content-Type', '')
            
        print(f"   ✓ URL is accessible (Status: {status})")
        print(f"   Content-Type: {content_type}")
        
        if 'text/html' not in content_type:
            print(f"   ⚠️  Unexpected content type: {content_type}")
            return False
            
    except Exception as e:
        print(f"   ✗ URL not accessible: {e}")
        return False
    
    return True

def trigger_crawler_with_options():
    """
    Trigger the staging crawler with enhanced options to bypass filters
    """
    print("\n" + "="*80)
    print("CRAWLING: Triggering staging crawler with enhanced configuration")
    print("="*80 + "\n")
    
    print(f"API: {STAGING_API}")
    print(f"Target URL: {TARGET_BLOG_POST}\n")
    
    # Enhanced payload with additional options to bypass common filtering issues
    payload = {
        'target_urls': [TARGET_BLOG_POST],
        'force_refresh': True,
        'crawl_depth': 1,
        'include_patterns': [
            '/blogs/desktop-and-application-streaming/*',
            '*workspaces*graphics*g6*'
        ],
        # Bypass date filtering for staging investigation
        'ignore_date_filters': True,
        # Ensure content is re-indexed even if URL was crawled before
        'bypass_duplicate_check': True,
        # Extended metadata extraction
        'extract_metadata': True,
        # Timeout configuration
        'timeout_seconds': 60,
        # Debug mode for detailed logging
        'debug_mode': True,
        # Reason for forced crawl
        'crawl_reason': 'Investigation: March 2 2026 WorkSpaces G6 post not detected',
        'requested_by': 'staging_diagnostic_tool',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    try:
        req = urllib.request.Request(
            STAGING_API,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'AWS-Staging-Crawler-Trigger/2.0',
                'X-Debug-Mode': 'true',
                'X-Investigation': 'post-detection-issue'
            },
            method='POST'
        )
        
        print("📤 Sending crawl request...")
        
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        print("✅ Crawler triggered successfully\n")
        print(f"Request Payload:")
        print(json.dumps(payload, indent=2))
        print(f"\nResponse:")
        print(json.dumps(data, indent=2))
        
        # Enhanced response validation
        success_indicators = ['crawl_id', 'job_id', 'task_id', 'queue_position']
        if any(indicator in data for indicator in success_indicators):
            print("\n✓ Crawl job queued successfully")
            
            # Extract job identifier
            job_id = (data.get('crawl_id') or data.get('job_id') or 
                     data.get('task_id') or 'unknown')
            print(f"Job ID: {job_id}")
            
            # Provide monitoring URLs
            print(f"\n📊 Monitor crawl status:")
            print(f"   Staging Dashboard: https://staging.awseuccontent.com")
            print(f"   Job ID: {job_id}")
            
            # Check for warnings in response
            if 'warnings' in data and data['warnings']:
                print(f"\n⚠️  Warnings reported:")
                for warning in data['warnings']:
                    print(f"   - {warning}")
            
            return True
        else:
            print("\n⚠️  Response does not contain expected job identifier")
            print("The crawl may have been rejected or queued without confirmation")
            return False
        
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP ERROR {e.code}: {e.reason}")
        try:
            error_body = e.read().decode('utf-8')
            error_data = json.loads(error_body)
            print(f"\nError details:")
            print(json.dumps(error_data, indent=2))
            
            # Analyze error for specific issues
            if e.code == 400:
                print("\n💡 Possible causes:")
                print("   - Payload validation failed")
                print("   - URL is in blacklist")
                print("   - Date filters cannot be bypassed")
            elif e.code == 429:
                print("\n💡 Rate limit reached - retry after cooldown period")
            elif e.code == 403:
                print("\n💡 Access forbidden - check API credentials")
                
        except:
            error_body = e.read().decode('utf-8') if hasattr(e, 'read') else str(e)
            print(f"Error body: {error_body}")
        return False
        
    except urllib.error.URLError as e:
        print(f"❌ URL ERROR: {e.reason}")
        print("Check network connectivity and API endpoint availability")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """
    Main execution flow with diagnostic and crawl phases
    """
    print("="*80)
    print("AWS STAGING CRAWLER - DIAGNOSTIC & TRIGGER TOOL")
    print("="*80)
    print(f"\nTarget Post: {EXPECTED_POST_TITLE}")
    print(f"Expected Date: {EXPECTED_POST_DATE}")
    print(f"URL: {TARGET_BLOG_POST}")
    
    # Phase 1: Run diagnostics
    diagnostic_passed = diagnose_crawler_filters()
    
    # Phase 2: Trigger crawler with enhanced options
    crawl_success = trigger_crawler_with_options()
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Diagnostic Phase: {'✅ PASSED' if diagnostic_passed else '❌ ISSUES FOUND'}")
    print(f"Crawl Trigger: {'✅ SUCCESS' if crawl_success else '❌ FAILED'}")
    
    if not diagnostic_passed:
        print("\n💡 Recommendations:")
        print("   1. Review date filter configuration in staging crawler")
        print("   2. Check if future-dated posts are allowed in staging")
        print("   3. Verify URL pattern matching logic")
        print("   4. Compare with production crawler configuration")
        print("   5. Check crawler logs for specific rejection reasons")
    
    if not crawl_success:
        print("\n💡 Next Steps:")
        print("   1. Check API endpoint health")
        print("   2. Verify API credentials and permissions")
        print("   3. Review staging crawler service logs")
        print("   4. Contact staging infrastructure team if issue persists")
        sys.exit(1)
    
    print("\n✅ Process completed - monitor staging dashboard for results")
    sys.exit(0)

if __name__ == '__main__':
    main()
```