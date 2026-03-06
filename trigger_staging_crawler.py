```python
"""
Trigger staging crawler via API with specific URL targeting
Enhanced with date filtering diagnostics and crawler validation
Version 3.0 - Comprehensive investigation for March 2, 2026 WorkSpaces Graphics G6 post
Root cause: Post from March 2, 2026 not being detected - investigating date filtering,
URL patterns, scraping selectors, and publication status
New: DynamoDB staging table inspection, crawler log retrieval, configuration audit
"""

import json
import urllib.request
import urllib.error
import sys
import time
from datetime import datetime, timezone, timedelta
import hashlib
import re

STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/crawl'
DYNAMODB_VERIFICATION_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/verify'
STAGING_TABLE_QUERY_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/query'
CRAWLER_LOGS_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/logs'

# Specific blog post URL that needs to be crawled
TARGET_BLOG_POST = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'

# Expected publication date of the blog post for validation
EXPECTED_POST_DATE = '2026-03-02'

# Generate unique investigation ID for tracking
INVESTIGATION_ID = hashlib.md5(f"{TARGET_BLOG_POST}{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:12]

print("=" * 80)
print("STAGING CRAWLER INVESTIGATION - VERSION 3.0 - COMPREHENSIVE DIAGNOSTICS")
print("=" * 80)
print(f"Investigation ID: {INVESTIGATION_ID}")
print(f"Target: {TARGET_BLOG_POST}")
print(f"Expected Date: {EXPECTED_POST_DATE}")
print(f"Issue: Post not being detected by staging crawler")
print(f"Current Time (UTC): {datetime.now(timezone.utc).isoformat()}")
print("=" * 80)
print()

# Pre-flight check: Verify target URL is accessible
print("PRE-FLIGHT CHECK 1: URL ACCESSIBILITY & PUBLICATION STATUS")
print("-" * 80)
url_accessible = False
response_details = {}
page_content = ""
http_status = None

try:
    req = urllib.request.Request(TARGET_BLOG_POST, headers={'User-Agent': 'AWS-BlogCrawler-Investigation/3.0'})
    with urllib.request.urlopen(req, timeout=30) as response:
        status_code = response.status
        http_status = status_code
        content_type = response.headers.get('Content-Type', 'unknown')
        content_length = response.headers.get('Content-Length', 'unknown')
        final_url = response.url
        last_modified = response.headers.get('Last-Modified', 'unknown')
        
        response_details = {
            'status': status_code,
            'content_type': content_type,
            'content_length': content_length,
            'final_url': final_url,
            'redirected': final_url != TARGET_BLOG_POST,
            'last_modified': last_modified
        }
        
        print(f"✓  URL is accessible and published")
        print(f"   Status Code: {status_code}")
        print(f"   Content-Type: {content_type}")
        print(f"   Content-Length: {content_length} bytes")
        print(f"   Last-Modified: {last_modified}")
        
        if response_details['redirected']:
            print(f"⚠️  URL redirected to: {final_url}")
            print(f"   CRITICAL: Crawler must follow redirects - this may cause detection failure")
        
        url_accessible = True
        
        # Read content for metadata inspection
        page_content = response.read().decode('utf-8', errors='ignore')
        print(f"✓  Page content retrieved ({len(page_content)} bytes)")
        
except urllib.error.HTTPError as e:
    http_status = e.code
    print(f"❌ CRITICAL ISSUE: HTTP Error {e.code}")
    if e.code == 404:
        print(f"   POST NOT FOUND - The URL does not exist or is not published yet")
    elif e.code == 403:
        print(f"   ACCESS FORBIDDEN - Check crawler permissions or IP blocking")
    elif e.code == 500 or e.code >= 500:
        print(f"   SERVER ERROR - AWS blog server issue")
    print(f"   ROOT CAUSE: Post is not accessible - crawler cannot detect unpublished posts")
    print(f"   ACTION: Verify post is actually published at this URL")
    sys.exit(1)
except urllib.error.URLError as e:
    print(f"❌ CRITICAL ISSUE: URL Error - {e.reason}")
    print(f"   ROOT CAUSE: Network/DNS issue preventing access")
    sys.exit(1)
except Exception as e:
    print(f"❌ CRITICAL ISSUE: {type(e).__name__}: {e}")
    print(f"   Investigation halted - fix URL accessibility first")
    sys.exit(1)
print()

# Detailed date metadata extraction and validation
print("PRE-FLIGHT CHECK 2: DATE METADATA EXTRACTION & SELECTOR VALIDATION")
print("-" * 80)

date_patterns = [
    (r'<meta\s+property=["\']article:published_time["\']\s+content=["\']([^"\']+)["\']', 'article:published_time'),
    (r'<meta\s+property=["\']og:published_time["\']\s+content=["\']([^"\']+)["\']', 'og:published_time'),
    (r'<meta\s+property=["\']article:modified_time["\']\s+content=["\']([^"\']+)["\']', 'article:modified_time'),
    (r'<time[^>]+datetime=["\']([^"\']+)["\']', 'time[datetime]'),
    (r'"datePublished"\s*:\s*"([^"]+)"', 'JSON-LD datePublished'),
    (r'"publishDate"\s*:\s*"([^"]+)"', 'JSON-LD publishDate'),
    (r'"dateCreated"\s*:\s*"([^"]+)"', 'JSON-LD dateCreated'),
    (r'<meta\s+name=["\']date["\']\s+content=["\']([^"\']+)["\']', 'meta[name=date]'),
    (r'<meta\s+name=["\']publish[_-]?date["\']\s+content=["\']([^"\']+)["\']', 'meta[name=publish_date]'),
    (r'<meta\s+name=["\']DC\.date["\']\s+content=["\']([^"\']+)["\']', 'Dublin Core date'),
    (r'<meta\s+itemprop=["\']datePublished["\']\s+content=["\']([^"\']+)["\']', 'itemprop datePublished'),
]

dates_found = []
for pattern, source in date_patterns:
    matches = re.findall(pattern, page_content, re.IGNORECASE)
    if matches:
        for match in matches:
            dates_found.append({'date': match, 'source': source})
            print(f"   Found date: {match} (selector: {source})")

if dates_found:
    print(f"✓  Found {len(dates_found)} date metadata field(s)")
    
    # Verify expected date is present
    expected_date_found = any(EXPECTED_POST_DATE in d['date'] for d in dates_found)
    if expected_date_found:
        print(f"✓  Expected date '{EXPECTED_POST_DATE}' found in page metadata")
        print(f"   Date extraction should work correctly")
    else:
        print(f"❌ CRITICAL: Expected date '{EXPECTED_POST_DATE}' NOT found in page metadata")
        print(f"   Actual dates found: {[d['date'][:10] for d in dates_found]}")
        print(f"   ROOT CAUSE: Date mismatch - post may have different publication date")
        print(f"   ACTION: Update EXPECTED_POST_DATE or verify post date on website")
else:
    print(f"❌ CRITICAL: No date metadata found in page source")
    print(f"   ROOT CAUSE: Missing date selectors - crawler cannot extract publication date")
    print(f"   ACTION: Page may not have standard date metadata tags")
    print(f"   REMEDY: Enhanced scraping selectors added to payload")

print()

# Content validation
print("PRE-FLIGHT CHECK 3: CONTENT VALIDATION")
print("-" * 80)

# Check for title
title_pattern = r'<title>([^<]+)</title>'
title_match = re.search(title_pattern, page_content, re.IGNORECASE)
if title_match:
    title = title_match.group(1).strip()
    print(f"✓  Page title found: {title[:100]}...")
    if 'WorkSpaces' in title and ('G6' in title or 'Graphics' in title):
        print(f"✓  Title matches expected content (WorkSpaces Graphics G6)")
    else:
        print(f"⚠️  Title may not match expected content - verify this is the correct post")
else:
    print(f"❌ CRITICAL: Could not extract page title")
    print(f"   Page may be malformed or blocked")

# Check for key content markers
content_markers = ['WorkSpaces', 'Graphics', 'G6', 'Gr6', 'G6f', 'bundles']
found_markers = [marker for marker in content_markers if marker in page_content]
print(f"\nContent markers found: {found_markers}")
if len(found_markers) >= 4:
    print(f"✓  Sufficient content markers found - this appears to be the correct post")
else:
    print(f"⚠️  Few content markers found - verify post content")

# Check for AWS blog structure
if 'aws.amazon.com/blogs' in page_content:
    print(f"✓  AWS blog structure detected")
else:
    print(f"⚠️  AWS blog structure not clearly detected")

print("-" * 80)
print()

# URL pattern analysis
print("PRE-FLIGHT CHECK 4: URL PATTERN ANALYSIS")
print("-" * 80)
url_components = TARGET_BLOG_POST.split('/')
blog_category = None
post_slug = None

try:
    if 'blogs' in url_components:
        blogs_index = url_components.index('blogs')
        if len(url_components) > blogs_index + 1:
            blog_category = url_components[blogs_index + 1]
            print(f"✓  Blog category: {blog_category}")
        if len(url_components) > blogs_index + 2:
            post_slug = url_components[blogs_index + 2]
            print(f"✓  Post slug: {post_slug}")
    
    print(f"\nURL pattern check:")
    print(f"   - Contains 'blogs': {'✓' if 'blogs' in TARGET_BLOG_POST else '❌'}")
    print(f"   - Contains 'desktop-and-application-streaming': {'✓' if 'desktop-and-application-streaming' in TARGET_BLOG_POST else '❌'}")
    print(f"   - Follows AWS blog URL structure: ✓")
    
except Exception as e:
    print(f"⚠️  Could not parse URL structure: {e}")

print("-" * 80)
print()

# Date analysis and filtering logic check
date_filter_issue = False
try:
    expected_dt = datetime.strptime(EXPECTED_POST_DATE, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    current_dt = datetime.now(timezone.utc)
    days_diff = (expected_dt - current_dt).days
    
    print("PRE-FLIGHT CHECK 5: DATE FILTERING LOGIC ANALYSIS")
    print("-" * 80)
    print(f"Expected Post Date: {expected_dt.isoformat()}")
    print(f"Current Date:       {current_dt.isoformat()}")
    print(f"Days Difference:    {days_diff} days")
    print()
    
    if days_diff > 0:
        print(f"❌ DATE FILTERING ISSUE DETECTED: Post date is {days_diff} days in the FUTURE")
        print(f"")
        print(f"   ROOT CAUSE: Future date filtering")
        print(f"   - Default crawler behavior rejects future-dated posts")
        print(f"   - Date validation logic marks post as invalid")
        print(f"   - This is likely why the post is not detected")
        print(f"")
        date_filter_issue = True
    elif days_diff < -365:
        print(f"⚠️  Post date is {abs(days_diff)} days in the PAST")
        print(f"   May be outside crawler's default date window")
        date_filter_issue = True
    else:
        print(f"✓  Post date is within normal range ({days_diff} days)")
        print(f"   Date filtering should not be an issue")
    
    print("-" * 80)
    print()
    
except Exception as e:
    print(f"⚠️  WARNING: Could not parse expected date: {e}")
    print()

# NEW: Check staging DynamoDB table for partial data
print("PRE-FLIGHT CHECK 6: STAGING TABLE INSPECTION")
print("-" * 80)
staging_data_found = False
staging_records = []

try:
    # Query staging table for this URL or partial matches
    url_hash = hashlib.sha256(TARGET_BLOG_POST.encode()).hexdigest()
    
    query_payload = {
        'action': 'query_by_url',
        'url': TARGET_BLOG_POST,
        'url_hash': url_hash,
        'include_partial': True,
        'investigation_id': INVESTIGATION_ID
    }
    
    print(f"Querying staging table for URL: {TARGET_BLOG_POST}")
    print(f"URL hash: {url_hash}")
    
    req = urllib.request.Request(
        STAGING_TABLE_QUERY_API,
        data=json.dumps(query_payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'User-Agent': 'AWS-BlogCrawler-Investigation/3.0'}
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode('utf-8'))
        
        if result.get('statusCode') == 200:
            body = json.loads(result.get('body', '{}'))
            staging_records = body.get('records', [])
            
            if staging_records:
                print(f"✓  Found {len(staging_records)} record(s) in staging table")
                staging_data_found = True
                
                for idx, record in enumerate(staging_records, 1):
                    print(f"\n   Record {idx}:")
                    print(f"      URL: {record.get('url', 'N/A')}")
                    print(f"      Title: {record.get('title', 'N/A')[:80]}")
                    print(f"      Date: {record.get('published_date', 'N/A')}")
                    print(f"      Status: {record.get('status', 'N/A')}")
                    print(f"      Crawled: {record.get('crawl_timestamp', 'N/A')}")
                    print(f"      Filtered: {record.get('filtered', 'N/A')}")
                    print(f"      Filter Reason: {recor