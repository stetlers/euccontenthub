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
dynamodb = boto3.client('dynamodb', region_name='us-east-1')

print("=" * 80)
print("CRAWLER LAMBDA LOGS AND INVESTIGATION")
print("=" * 80)

# Target blog post URL to investigate
TARGET_URL = "https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/"
TARGET_DATE = "2026-03-02"
TARGET_CATEGORY = "desktop-and-application-streaming"
TARGET_TITLE_KEYWORDS = ["workspaces", "graphics", "g6", "gr6", "g6f", "bundles"]

def check_dynamodb_staging_table():
    """Check staging DynamoDB table for the target blog post"""
    print("\n" + "=" * 80)
    print("CHECKING STAGING DYNAMODB TABLE")
    print("=" * 80)
    
    try:
        # Try common staging table naming patterns
        staging_table_names = [
            'aws-blog-posts-staging',
            'blog-posts-staging',
            'BlogPostsStaging',
            'aws-euc-blog-posts-staging'
        ]
        
        table_found = False
        for table_name in staging_table_names:
            try:
                # Check if table exists
                response = dynamodb.describe_table(TableName=table_name)
                table_found = True
                print(f"✓ Found staging table: {table_name}")
                print(f"  Item Count: {response['Table'].get('ItemCount', 'N/A')}")
                print(f"  Status: {response['Table'].get('TableStatus', 'N/A')}")
                
                # Query for target post by URL or date
                print(f"\nSearching for target post in {table_name}...")
                
                # Scan for items matching date and category (limited scan)
                scan_response = dynamodb.scan(
                    TableName=table_name,
                    FilterExpression='contains(#url, :category) AND begins_with(#date, :target_date)',
                    ExpressionAttributeNames={
                        '#url': 'url',
                        '#date': 'publish_date'
                    },
                    ExpressionAttributeValues={
                        ':category': {'S': TARGET_CATEGORY},
                        ':target_date': {'S': TARGET_DATE}
                    },
                    Limit=100
                )
                
                items = scan_response.get('Items', [])
                print(f"Found {len(items)} items matching date {TARGET_DATE} and category {TARGET_CATEGORY}")
                
                # Check specifically for target post
                target_found = False
                for item in items:
                    url = item.get('url', {}).get('S', '')
                    title = item.get('title', {}).get('S', '')
                    
                    if 'amazon-workspaces-launches-graphics-g6' in url.lower():
                        target_found = True
                        print(f"\n✓ TARGET POST FOUND in DynamoDB:")
                        print(f"  URL: {url}")
                        print(f"  Title: {title}")
                        print(f"  Date: {item.get('publish_date', {}).get('S', 'N/A')}")
                        return True
                
                if not target_found:
                    print(f"\n⚠ TARGET POST NOT FOUND in DynamoDB staging table")
                    
                    # Sample some recent posts for comparison
                    if items:
                        print(f"\nSample posts from {TARGET_DATE} in {TARGET_CATEGORY}:")
                        for item in items[:3]:
                            print(f"  - {item.get('title', {}).get('S', 'N/A')[:80]}")
                            print(f"    {item.get('url', {}).get('S', 'N/A')}")
                    
                    # Try broader search without date filter
                    broad_scan = dynamodb.scan(
                        TableName=table_name,
                        FilterExpression='contains(#url, :keyword)',
                        ExpressionAttributeNames={'#url': 'url'},
                        ExpressionAttributeValues={':keyword': {'S': 'amazon-workspaces-launches-graphics'}},
                        Limit=50
                    )
                    
                    broad_items = broad_scan.get('Items', [])
                    if broad_items:
                        print(f"\n⚠ Found {len(broad_items)} similar posts with different dates:")
                        for item in broad_items[:5]:
                            print(f"  - {item.get('title', {}).get('S', 'N/A')[:80]}")
                            print(f"    Date: {item.get('publish_date', {}).get('S', 'N/A')}")
                            print(f"    URL: {item.get('url', {}).get('S', 'N/A')}")
                    
                    return False
                
                break  # Table found and processed
                
            except dynamodb.exceptions.ResourceNotFoundException:
                continue
            except Exception as e:
                print(f"  Error checking table {table_name}: {e}")
                continue
        
        if not table_found:
            print("⚠ No staging DynamoDB table found. Tried:")
            for name in staging_table_names:
                print(f"  - {name}")
            print("\nPlease verify the staging table name and ensure proper permissions.")
        
        return False
        
    except Exception as e:
        print(f"Error checking DynamoDB: {e}")
        return False

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
            date_filter_issues = []
            for key, value in env_vars.items():
                if any(term in key.lower() for term in ['date', 'filter', 'url', 'category', 'stage', 'env']):
                    print(f"  {key}: {value}")
                    # Flag potential date range issues
                    if 'date' in key.lower() and value:
                        try:
                            env_date = datetime.strptime(value[:10], '%Y-%m-%d')
                            target_date_obj = datetime.strptime(TARGET_DATE, '%Y-%m-%d')
                            if 'after' in key.lower() and env_date > target_date_obj:
                                issue = f"    ⚠ WARNING: {key} ({value}) is AFTER target date {TARGET_DATE}"
                                print(issue)
                                date_filter_issues.append(issue)
                            if 'before' in key.lower() and env_date < target_date_obj:
                                issue = f"    ⚠ WARNING: {key} ({value}) is BEFORE target date {TARGET_DATE}"
                                print(issue)
                                date_filter_issues.append(issue)
                        except (ValueError, TypeError):
                            pass
            
            if date_filter_issues:
                print(f"\n⚠ CRITICAL: Found {len(date_filter_issues)} date filter configuration issues!")
                print("This may prevent posts from the target date from being crawled.")
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
        if any(term in message.lower() for term in ['date parse', 'invalid date', 'date format', 'strptime', 'valueerror']):
            date_parsing_errors.append(message)
        
        # Look for cutoff dates or date range filters
        if any(term in message.lower() for term in ['cutoff', 'since', 'from date', 'after date', 'date range', 'skip.*date', 'filter.*date']):
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
            elif any(term in message.lower() for term in ['process', 'crawl', 'fetch', 'found', 'detected', 'adding', 'queue']):
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
        if any(term in message.lower() for term in ['parse error', 'extraction failed', 'selector', 'xpath', 'beautifulsoup', 'html parser']):
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
            if any(term in message.lower() for term in ['process', 'crawl', 'fetch', 'success', 'save', 'insert']):
                target_indicators['url_processed'] = True
            if any(term in message.lower() for term in ['skip', 'reject', 'filter', 'ignore', 'exclude']):
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
    posts_by_date = {}
    
    for event in events:
        message = event["message"].strip()
        
        # Look for RSS feed processing
        if any(term in message.lower() for term in ['rss', 'feed', 'xml']):
            rss_feeds.append(message)
        
        # Look for feed parsing errors
        if 'feed' in message.lower() and any(term in message.lower