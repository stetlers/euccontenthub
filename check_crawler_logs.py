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
    
    for event in events:
        message = event["message"].strip()
        
        # Look for date-related filtering
        if any(term in message.lower() for term in ['date', 'publish', 'timestamp', 'after', 'before']):
            date_match = re.search(r'\d{4}-\d{2}-\d{2}', message)
            if date_match:
                date_patterns.append({
                    'message': message,
                    'date': date_match.group(0)
                })
        
        # Look for comparison operators with dates
        if re.search(r'(>|<|>=|<=|==|!=).*\d{4}', message):
            date_comparisons.append(message)
    
    return date_patterns, date_comparisons

def analyze_url_detection(events):
    """Analyze URL detection and pattern matching"""
    detected_urls = []
    url_patterns = []
    rejected_urls = []
    
    for event in events:
        message = event["message"].strip()
        
        # Extract all URLs
        urls = re.findall(r'https?://[^\s\'"]+', message)
        for url in urls:
            url_entry = {'url': url, 'message': message}
            
            if any(term in message.lower() for term in ['skip', 'reject', 'filter', 'ignore']):
                rejected_urls.append(url_entry)
            elif any(term in message.lower() for term in ['process', 'crawl', 'fetch', 'found']):
                detected_urls.append(url_entry)
        
        # Look for URL pattern matching logic
        if 'pattern' in message.lower() or 'regex' in message.lower() or 'match' in message.lower():
            url_patterns.append(message)
    
    return detected_urls, rejected_urls, url_patterns

def analyze_scraping_patterns(events):
    """Analyze scraping patterns and content extraction"""
    scraping_issues = []
    content_extraction = []
    parser_errors = []
    
    for event in events:
        message = event["message"].strip()
        
        # Look for parsing/scraping related messages
        if any(term in message.lower() for term in ['parse', 'extract', 'scrape', 'html', 'content']):
            content_extraction.append(message)
        
        # Look for parser errors
        if any(term in message.lower() for term in ['parse error', 'extraction failed', 'selector', 'xpath']):
            parser_errors.append(message)
        
        # Look for missing elements
        if any(term in message.lower() for term in ['not found', 'missing', 'empty', 'null']):
            scraping_issues.append(message)
    
    return content_extraction, parser_errors, scraping_issues

def check_for_target_post(events):
    """Check if target blog post was encountered in any form"""
    target_indicators = {
        'url_match': False,
        'category_match': False,
        'keyword_match': False,
        'date_match': False,
        'related_messages': []
    }
    
    for event in events:
        message = event["message"].strip()
        
        # Check for category
        if TARGET_CATEGORY in message.lower():
            target_indicators['category_match'] = True
            target_indicators['related_messages'].append(f"Category: {message}")
        
        # Check for keywords
        if 'workspaces' in message.lower() and 'graphics' in message.lower():
            target_indicators['keyword_match'] = True
            target_indicators['related_messages'].append(f"Keywords: {message}")
        
        # Check for date
        if TARGET_DATE in message:
            target_indicators['date_match'] = True
            target_indicators['related_messages'].append(f"Date: {message}")
        
        # Check for any part of the URL
        if 'g6' in message.lower() or 'gr6' in message.lower() or 'g6f' in message.lower():
            target_indicators['url_match'] = True
            target_indicators['related_messages'].append(f"URL Fragment: {message}")
    
    return target_indicators

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
    date_patterns, date_comparisons = analyze_date_filtering(events)
    if date_patterns:
        print(f"Found {len(date_patterns)} date-related patterns:")
        for pattern in date_patterns[:5]:
            print(f"  Date: {pattern['date']} | {pattern['message'][:100]}")
        if TARGET_DATE in [p['date'] for p in date_patterns]:
            print(f"✓ Target date {TARGET_DATE} was found in logs")
        else:
            print(f"⚠ Target date {TARGET_DATE} was NOT found in logs")
    else:
        print("⚠ No date filtering patterns detected in logs")
    
    if date_comparisons:
        print(f"\nFound {len(date_comparisons)} date comparison operations:")
        for comp in date_comparisons[:3]:
            print(f"  {comp[:100]}")
    
    # 2. URL detection analysis
    print("\n2. URL DETECTION ANALYSIS")
    print("-" * 80)
    detected_urls, rejected_urls, url_patterns = analyze_url_detection(events)
    print(f"Detected URLs: {len(detected_urls)}")
    print(f"Rejected/Filtered URLs: {len(rejected_urls)}")
    print(f"URL Pattern Rules: {len(url_patterns)}")
    
    if detected_urls:
        print("\nSample detected URLs:")
        for url_entry in detected_urls[:5]:
            print(f"  {url_entry['url']}")
    
    if rejected_urls:
        print("\nSample rejected URLs:")
        for url_entry in rejected_urls[:5]:
            print(f"  {url_entry['url']}")
            print(f"    Reason: {url_entry['message'][:80]}")
    
    # Check if target URL was rejected
    target_in_rejected = any(TARGET_CATEGORY in url['url'] for url in rejected_urls)
    if target_in_rejected:
        print(f"\n⚠ WARNING: URLs from category '{TARGET_CATEGORY}' were REJECTED")
    
    # 3. Scraping patterns analysis
    print("\n3. SCRAPING PATTERNS ANALYSIS")
    print("-" * 80)
    content_extraction, parser_errors, scraping_issues = analyze_scraping_patterns(events)
    print(f"Content extraction attempts: {len(content_extraction)}")
    print(f"Parser errors: {len(parser_errors)}")
    print(f"Scraping issues: {len(scraping_issues)}")
    
    if parser_errors:
        print("\nParser errors detected:")
        for error in parser_errors[:3]:
            print(f"  - {error[:100]}")
    
    if scraping_issues:
        print("\nScraping issues detected:")
        for issue in scraping_issues[:3]:
            print(f"  - {issue[:100]}")
    
    # 4. Target post detection
    print("\n4. TARGET POST DETECTION")
    print("-" * 80)
    target_indicators = check_for_target_post(events)
    print(f"URL Match: {target_indicators['url_match']}")
    print(f"Category Match: {target_indicators['category_match']}")
    print(f"Keyword Match: {target_indicators['keyword_match']}")
    print(f"Date Match: {target_indicators['date_match']}")
    
    if target_indicators['related_messages']:
        print("\nRelated messages found:")
        for msg in target_indicators['related_messages']:
            print(f"  {msg[:150]}")
    else:
        print("\n⚠ No messages related to target post found")
    
    # Print investigation summary
    print("\n" + "=" * 80)
    print("INVESTIGATION SUMMARY")
    print("=" * 80)
    print(f"Target URL: {TARGET_URL}")
    print(f"Target Date: {TARGET_DATE}")
    print(f"Target Category: {TARGET_CATEGORY}")
    print(f"\nTotal crawl errors: {len(crawl_errors)}")
    
    if crawl_errors:
        print("\nRecent errors (showing first 5):")
        for error in crawl_errors[:5]:
            print(f"  [{error['timestamp'].strftime('%H:%M:%S')}] {error['message'][:100]}")
    
    # Provide recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    recommendations = []
    
    if not target_indicators['category_match']:
        recommendations.append("⚠ The target category 'desktop-and-application-streaming' was not found")
        recommendations.append("  → Verify the crawler is configured to crawl this category")
        recommendations.append("  → Check RSS feed or sitemap includes this category")
    
    if not target_indicators['date_match'] and date_patterns:
        recommendations.append(f"⚠ The target date {TARGET_DATE} was not found in date filtering")
        recommendations.append("  → Check date range filters in crawler configuration")
        recommendations.append("  → Verify date comparison logic allows posts from March 2026")
    
    if not target_indicators['keyword_match']:
        recommendations.append("⚠ Keywords 'WorkSpaces' and 'Graphics' not found together")
        recommendations.append("  → Verify blog post is published and accessible")
        recommendations.append("  → Check if content filtering is too restrictive")
    
    if rejected_urls and target_in_rejected:
        recommendations.append("⚠ URLs from target category were rejected/filtered")
        recommendations.append("  → Review URL filtering rules and patterns")
        recommendations.append("  → Check for overly restrictive regex patterns")
    
    if parser_errors:
        recommendations.append("⚠ Parser errors detected during crawling")
        recommendations.append("  → HTML structure may have changed")
        recommendations.append("  → Update CSS selectors or XPath expressions")
    
    if not date_patterns:
        recommendations.append("⚠ No date filtering detected in logs")
        recommendations.append("  → Date filtering logic may not be working")
        recommendations.append("  → Check if date extraction from posts is functional")
    
    if recommendations:
        for rec in recommendations:
            print(rec)
    else:
        print("✓ No obvious issues detected from log analysis")
    
    print("\nNext steps:")
    print("1. Verify blog post exists at staging.awseuccontent.com")
    print("2. Check crawler environment variables for date filters")
    print("3. Review category/URL pattern matching configuration")
    print("4. Manually test crawler with target URL if possible")
    print("5. Check if RSS feed includes the new post")
    print("6. Verify staging environment is accessible from Lambda")
    print("=" * 80)

def main():
    # Check crawler configuration first
    check_crawler_configuration()
    
    print("\n" + "=" * 80)
    print("ANALYZING CLOUDWATCH LOGS")
    print("=" * 80)
    
    try:
        # Try last 5 minutes first
        response = logs.filter_log_events(
            logGroupName='/aws/lambda/aws-blog-crawler',
            startTime=int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)
        )
        
        if response['events']:
            analyze_log_events(response['events'])
        else:
            print("\nNo logs found in last 5 minutes")
            print("Checking last 30 minutes...")
            
            response = logs.filter_log_events(
                logGroupName='/aws/lambda/aws-blog-crawler',
                startTime=int((datetime.now() - timedelta(minutes=30)).timestamp() * 1000)
            )
            
            if response['events']:
                # Show last 150 events for comprehensive investigation
                analyze_log_events(response['events'][-150:])
            else:
                print("No logs found in last 30 minutes either")
                print("\nTroubleshooting tips:")
                print("1. Verify the Lambda function name is 'aws-blog-crawler'")
                print("2. Check if crawler has been invoked recently")
                print("3. Verify IAM permissions to read CloudWatch Logs")
                print("4. Try manually invoking the crawler Lambda function")
                print("5. Check CloudWatch Logs retention settings")
                
    except logs.exceptions.ResourceNotFoundException:
        print(f"Error: Log group '/aws/lambda/aws-blog-crawler' not found")
        print("\nPossible causes:")
        print("- Lambda function name is incorrect")