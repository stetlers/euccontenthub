```python
"""
Check crawler Lambda logs from the most recent invocation
Enhanced to investigate missing Amazon WorkSpaces blog post detection
"""
import boto3
from datetime import datetime, timedelta
import re
import json

logs = boto3.client('logs', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')

print("=" * 80)
print("CRAWLER LAMBDA LOGS AND INVESTIGATION")
print("=" * 80)

# Target blog post URL to investigate
TARGET_URL = "https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/"
TARGET_DATE = "2026-03-02"
TARGET_CATEGORY = "desktop-and-application-streaming"

def check_crawler_configuration():
    """Check crawler Lambda configuration for potential issues"""
    print("\n" + "=" * 80)
    print("CHECKING CRAWLER CONFIGURATION")
    print("=" * 80)
    
    try:
        response = lambda_client.get_function_configuration(
            FunctionName='aws-blog-crawler'
        )
        
        print(f"Runtime: {response.get('Runtime', 'N/A')}")
        print(f"Timeout: {response.get('Timeout', 'N/A')} seconds")
        print(f"Memory: {response.get('MemorySize', 'N/A')} MB")
        print(f"Last Modified: {response.get('LastModified', 'N/A')}")
        
        # Check environment variables for date filters
        env_vars = response.get('Environment', {}).get('Variables', {})
        if env_vars:
            print("\nEnvironment Variables:")
            for key, value in env_vars.items():
                if any(term in key.lower() for term in ['date', 'filter', 'url', 'category']):
                    print(f"  {key}: {value}")
                    # Flag potential date range issues
                    if 'date' in key.lower() and value:
                        try:
                            env_date = datetime.strptime(value[:10], '%Y-%m-%d')
                            target_date_obj = datetime.strptime(TARGET_DATE, '%Y-%m-%d')
                            if 'after' in key.lower() and env_date > target_date_obj:
                                print(f"    ⚠ WARNING: {key} is AFTER target date {TARGET_DATE}")
                            if 'before' in key.lower() and env_date < target_date_obj:
                                print(f"    ⚠ WARNING: {key} is BEFORE target date {TARGET_DATE}")
                        except (ValueError, TypeError):
                            pass
        else:
            print("\nNo environment variables found")
        
        return True
    except Exception as e:
        print(f"Could not retrieve crawler configuration: {e}")
        return False

def analyze_date_filtering(events):
    """Analyze date filtering logic in crawler"""
    date_patterns = []
    date_comparisons = []
    date_parsing_errors = []
    cutoff_dates = []
    
    for event in events:
        message = event["message"].strip()
        
        # Look for date-related filtering
        if any(term in message.lower() for term in ['date', 'publish', 'timestamp', 'after', 'before']):
            date_match = re.search(r'\d{4}-\d{2}-\d{2}', message)
            if date_match:
                date_patterns.append({
                    'message': message,
                    'date': date_match.group(0),
                    'timestamp': event['timestamp']
                })
        
        # Look for comparison operators with dates
        if re.search(r'(>|<|>=|<=|==|!=).*\d{4}', message):
            date_comparisons.append(message)
        
        # Look for date parsing errors
        if any(term in message.lower() for term in ['date parse', 'invalid date', 'date format', 'strptime']):
            date_parsing_errors.append(message)
        
        # Look for cutoff dates or date range filters
        if any(term in message.lower() for term in ['cutoff', 'since', 'from date', 'after date', 'date range']):
            cutoff_dates.append(message)
    
    return date_patterns, date_comparisons, date_parsing_errors, cutoff_dates

def analyze_url_detection(events):
    """Analyze URL detection and pattern matching"""
    detected_urls = []
    url_patterns = []
    rejected_urls = []
    category_filters = []
    
    for event in events:
        message = event["message"].strip()
        
        # Extract all URLs
        urls = re.findall(r'https?://[^\s\'"]+', message)
        for url in urls:
            url_entry = {'url': url, 'message': message, 'timestamp': event['timestamp']}
            
            if any(term in message.lower() for term in ['skip', 'reject', 'filter', 'ignore', 'exclude']):
                rejected_urls.append(url_entry)
            elif any(term in message.lower() for term in ['process', 'crawl', 'fetch', 'found', 'detected', 'adding']):
                detected_urls.append(url_entry)
        
        # Look for URL pattern matching logic
        if 'pattern' in message.lower() or 'regex' in message.lower() or 'match' in message.lower():
            url_patterns.append(message)
        
        # Look for category filtering
        if 'category' in message.lower() or 'blog category' in message.lower():
            category_filters.append(message)
    
    return detected_urls, rejected_urls, url_patterns, category_filters

def analyze_scraping_patterns(events):
    """Analyze scraping patterns and content extraction"""
    scraping_issues = []
    content_extraction = []
    parser_errors = []
    metadata_extraction = []
    
    for event in events:
        message = event["message"].strip()
        
        # Look for parsing/scraping related messages
        if any(term in message.lower() for term in ['parse', 'extract', 'scrape', 'html', 'content']):
            content_extraction.append(message)
        
        # Look for parser errors
        if any(term in message.lower() for term in ['parse error', 'extraction failed', 'selector', 'xpath', 'beautifulsoup']):
            parser_errors.append(message)
        
        # Look for missing elements
        if any(term in message.lower() for term in ['not found', 'missing', 'empty', 'null', 'none returned']):
            scraping_issues.append(message)
        
        # Look for metadata extraction (title, date, author)
        if any(term in message.lower() for term in ['title', 'author', 'publish date', 'metadata']):
            metadata_extraction.append(message)
    
    return content_extraction, parser_errors, scraping_issues, metadata_extraction

def check_for_target_post(events):
    """Check if target blog post was encountered in any form"""
    target_indicators = {
        'url_match': False,
        'category_match': False,
        'keyword_match': False,
        'date_match': False,
        'url_processed': False,
        'url_rejected': False,
        'related_messages': []
    }
    
    for event in events:
        message = event["message"].strip()
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        
        # Check for exact URL or URL slug
        if 'amazon-workspaces-launches-graphics-g6' in message.lower():
            target_indicators['url_match'] = True
            target_indicators['related_messages'].append(f"[{timestamp.strftime('%H:%M:%S')}] URL Match: {message}")
            if any(term in message.lower() for term in ['process', 'crawl', 'fetch', 'success']):
                target_indicators['url_processed'] = True
            if any(term in message.lower() for term in ['skip', 'reject', 'filter', 'ignore']):
                target_indicators['url_rejected'] = True
        
        # Check for category
        if TARGET_CATEGORY in message.lower():
            target_indicators['category_match'] = True
            target_indicators['related_messages'].append(f"[{timestamp.strftime('%H:%M:%S')}] Category: {message}")
        
        # Check for keywords
        if 'workspaces' in message.lower() and ('graphics' in message.lower() or 'g6' in message.lower()):
            target_indicators['keyword_match'] = True
            target_indicators['related_messages'].append(f"[{timestamp.strftime('%H:%M:%S')}] Keywords: {message}")
        
        # Check for date - be flexible with date formats
        if TARGET_DATE in message or '2026-03-02' in message or 'march 2, 2026' in message.lower() or 'march 02, 2026' in message.lower():
            target_indicators['date_match'] = True
            target_indicators['related_messages'].append(f"[{timestamp.strftime('%H:%M:%S')}] Date: {message}")
        
        # Check for any part of the URL fragments
        if any(term in message.lower() for term in ['g6-gr6-and-g6f', 'gr6', 'g6f-bundles']):
            target_indicators['url_match'] = True
            target_indicators['related_messages'].append(f"[{timestamp.strftime('%H:%M:%S')}] URL Fragment: {message}")
    
    return target_indicators

def analyze_rss_feed_parsing(events):
    """Analyze RSS feed parsing and post discovery"""
    rss_feeds = []
    feed_errors = []
    post_discovery = []
    
    for event in events:
        message = event["message"].strip()
        
        # Look for RSS feed processing
        if any(term in message.lower() for term in ['rss', 'feed', 'xml']):
            rss_feeds.append(message)
        
        # Look for feed parsing errors
        if 'feed' in message.lower() and any(term in message.lower() for term in ['error', 'fail', 'invalid', 'timeout']):
            feed_errors.append(message)
        
        # Look for post discovery messages
        if any(term in message.lower() for term in ['found post', 'discovered', 'new post', 'blog entry']):
            post_discovery.append(message)
    
    return rss_feeds, feed_errors, post_discovery

def analyze_log_events(events):
    """Analyze log events for crawler behavior and potential issues"""
    print(f"\nFound {len(events)} log events\n")
    print("=" * 80)
    print("RAW LOG EVENTS")
    print("=" * 80)
    
    # Tracking variables for investigation
    crawl_errors = []
    
    for event in events:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event["message"].strip()
        
        # Print all log messages
        print(f'{timestamp.strftime("%H:%M:%S")} | {message}')
        
        # Collect errors
        if any(term in message.lower() for term in ['error', 'exception', 'fail', 'traceback']):
            crawl_errors.append({
                'timestamp': timestamp,
                'message': message
            })
    
    # Perform detailed analysis
    print("\n" + "=" * 80)
    print("DETAILED ANALYSIS")
    print("=" * 80)
    
    # 1. Date filtering analysis
    print("\n1. DATE FILTERING ANALYSIS")
    print("-" * 80)
    date_patterns, date_comparisons, date_parsing_errors, cutoff_dates = analyze_date_filtering(events)
    if date_patterns:
        print(f"Found {len(date_patterns)} date-related patterns:")
        for pattern in date_patterns[:10]:
            print(f"  Date: {pattern['date']} | {pattern['message'][:100]}")
        
        # Check if target date is in range of found dates
        found_dates = [p['date'] for p in date_patterns]
        if TARGET_DATE in found_dates:
            print(f"✓ Target date {TARGET_DATE} was found in logs")
        else:
            print(f"⚠ Target date {TARGET_DATE} was NOT found in logs")
            # Show date range
            if found_dates:
                min_date = min(found_dates)
                max_date = max(found_dates)
                print(f"  Date range in logs: {min_date} to {max_date}")
                if TARGET_DATE < min_date:
                    print(f"  ⚠ Target date is BEFORE earliest date in logs")
                elif TARGET_DATE > max_date:
                    print(f"  ⚠ Target date is AFTER latest date in logs")
    else:
        print("⚠ No date filtering patterns detected in logs")
    
    if date_comparisons:
        print(f"\nFound {len(date_comparisons)} date comparison operations:")
        for comp in date_comparisons[:5]:
            print(f"  {comp[:150]}")
    
    if date_parsing_errors:
        print(f"\n⚠ Found {len(date_parsing_errors)} date parsing errors:")
        for error in date_parsing_errors[:3]:
            print(f"  {error[:150]}")
    
    if cutoff_dates:
        print(f"\nFound {len(cutoff_dates)} cutoff/range date filters:")
        for cutoff in cutoff_dates[:5]:
            print(f"  {cutoff[:150]}")
    
    # 2. URL detection analysis
    print("\n2. URL DETECTION ANALYSIS")
    print("-" * 80)
    detected_urls, rejected_urls, url_patterns, category_filters = analyze_url_detection(events)
    print(f"Detected URLs: {len(detected_urls)}")
    print(f"Rejected/Filtered URLs: {len(rejected_urls)}")
    print(f"URL Pattern Rules: {len(url_patterns)}")
    print(f"Category Filter Messages: {len(category_filters)}")
    
    if detected_urls:
        print("\nSample detected URLs:")
        for url_entry in detected_urls[:5]:
            ts = datetime.fromtimestamp(url_entry['timestamp'] / 1000)
            print(f"  [{ts.strftime('%H:%M:%S')}] {url_entry['url']}")
    
    if rejected_urls:
        print("\nSample rejected URLs:")
        for url_entry in rejected_urls[:5]:
            ts = datetime.fromtimestamp(url_entry['timestamp'] / 1000)
            print(f"  [{ts.strftime('%H:%M:%S')}] {url_entry['url']}")
            print(f"    Reason: {url_entry['message'][:80]}")
    
    # Check if target URL or category was rejected
    target_in_rejected = any(TARGET_CATEGORY in url['url'] for url in rejected_urls)
    if target_in_rejected:
        print(f"\n⚠ WARNING: URLs from category '{TARGET_CATEGORY}' were REJECTED")
        matching_rejected = [url for url in rejected_urls if TARGET_CATEGORY in url['url']]
        for url in matching_rejected[:3]:
            print(f"  Rejected: {url['url']}")
            print(f"  Message: {url['message'][:100]}")
    
    if category_filters:
        print(f"\nCategory filtering detected ({len(category_filters)} messages):")
        for cat_filter in category_filters[:3]:
            print(f"  {cat_filter[:150]}")
    
    # 3. RSS Feed analysis
    print("\n3. RSS FEED PARSING ANALYSIS")
    print("-" * 80)
    rss_feeds, feed_errors