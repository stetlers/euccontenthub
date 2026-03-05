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
s3 = boto3.client('s3', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')

print("=" * 80)
print("CRAWLER LAMBDA LOGS (last 5 minutes)")
print("=" * 80)

# Target blog post URL to investigate
TARGET_URL = "https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/"
TARGET_STAGING_URL = "https://staging.awseuccontent.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/"
TARGET_DATE = "2026-03-02"
TARGET_CATEGORY = "desktop-and-application-streaming"

def check_staging_content():
    """Verify if the blog post exists on staging environment"""
    print("\n" + "=" * 80)
    print("STAGING CONTENT VERIFICATION")
    print("=" * 80)
    
    try:
        import urllib.request
        import urllib.error
        from urllib.parse import urlparse
        
        urls_to_check = [
            TARGET_STAGING_URL,
            f"https://staging.awseuccontent.com/blogs/{TARGET_CATEGORY}/",
            "https://staging.awseuccontent.com/blogs/feed/"
        ]
        
        for url in urls_to_check:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'AWS-Blog-Crawler-Diagnostic/1.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    status = response.status
                    content_length = len(response.read())
                    print(f"✓ {url}")
                    print(f"  Status: {status}, Content-Length: {content_length} bytes")
            except urllib.error.HTTPError as e:
                print(f"✗ {url}")
                print(f"  HTTP Error {e.code}: {e.reason}")
            except urllib.error.URLError as e:
                print(f"✗ {url}")
                print(f"  URL Error: {e.reason}")
            except Exception as e:
                print(f"✗ {url}")
                print(f"  Error: {str(e)}")
    except ImportError:
        print("urllib not available, skipping staging content check")
    except Exception as e:
        print(f"Error checking staging content: {e}")

def check_crawler_configuration():
    """Check Lambda environment variables and configuration"""
    print("\n" + "=" * 80)
    print("CRAWLER CONFIGURATION CHECK")
    print("=" * 80)
    
    try:
        response = lambda_client.get_function_configuration(
            FunctionName='aws-blog-crawler'
        )
        
        env_vars = response.get('Environment', {}).get('Variables', {})
        
        print("Environment Variables:")
        config_keys = [
            'SOURCE_DOMAIN',
            'BASE_URL',
            'STAGING_URL',
            'BLOG_CATEGORIES',
            'DATE_FILTER',
            'START_DATE',
            'END_DATE',
            'ENABLED_CATEGORIES'
        ]
        
        for key in config_keys:
            value = env_vars.get(key, 'NOT SET')
            print(f"  {key}: {value}")
            
            # Check for misconfigurations
            if key == 'SOURCE_DOMAIN' and 'staging' not in str(value).lower():
                print(f"    ⚠ WARNING: SOURCE_DOMAIN may not point to staging")
            
            if key in ['BLOG_CATEGORIES', 'ENABLED_CATEGORIES']:
                if TARGET_CATEGORY not in str(value).lower():
                    print(f"    ⚠ WARNING: Target category '{TARGET_CATEGORY}' not found in {key}")
            
            if key in ['START_DATE', 'END_DATE']:
                if value != 'NOT SET':
                    try:
                        filter_date = datetime.strptime(value, '%Y-%m-%d')
                        target_date = datetime.strptime(TARGET_DATE, '%Y-%m-%d')
                        if key == 'START_DATE' and target_date < filter_date:
                            print(f"    ⚠ WARNING: Target date {TARGET_DATE} is before START_DATE")
                        if key == 'END_DATE' and target_date > filter_date:
                            print(f"    ⚠ WARNING: Target date {TARGET_DATE} is after END_DATE")
                    except ValueError:
                        pass
        
        print(f"\nTimeout: {response.get('Timeout', 'Unknown')} seconds")
        print(f"Memory: {response.get('MemorySize', 'Unknown')} MB")
        print(f"Last Modified: {response.get('LastModified', 'Unknown')}")
        
    except lambda_client.exceptions.ResourceNotFoundException:
        print("✗ Lambda function 'aws-blog-crawler' not found")
        print("  Check if function name is correct")
    except Exception as e:
        print(f"Error checking Lambda configuration: {e}")

def analyze_log_events(events):
    """Analyze log events for crawler behavior and potential issues"""
    print(f"\nFound {len(events)} log events\n")
    
    # Tracking variables for investigation
    found_target_url = False
    found_staging_domain = False
    found_target_category = False
    found_target_keywords = False
    crawl_errors = []
    processed_urls = []
    filtered_urls = []
    date_filters_applied = []
    rss_feeds_crawled = []
    
    for event in events:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event["message"].strip()
        
        # Print all log messages
        print(f'{timestamp.strftime("%H:%M:%S")} | {message}')
        
        # Check for staging domain
        if "staging.awseuccontent.com" in message.lower():
            found_staging_domain = True
        
        # Check for target URL or category
        if TARGET_CATEGORY in message.lower():
            found_target_category = True
        
        if "workspaces" in message.lower() and ("graphics" in message.lower() or "g6" in message.lower()):
            found_target_keywords = True
        
        # Check for exact URL match
        if TARGET_STAGING_URL in message or TARGET_URL in message:
            found_target_url = True
        
        # Extract processed URLs
        if "processing" in message.lower() or "crawling" in message.lower() or "fetching" in message.lower():
            url_match = re.search(r'https?://[^\s]+', message)
            if url_match:
                processed_urls.append(url_match.group(0))
        
        # Track RSS feeds
        if "rss" in message.lower() or "feed" in message.lower():
            rss_feeds_crawled.append(message)
        
        # Detect date filtering
        if "date" in message.lower() and ("filter" in message.lower() or "skip" in message.lower()):
            date_filters_applied.append(message)
        
        # Detect filtering or skipping
        if "skip" in message.lower() or "filter" in message.lower() or "ignor" in message.lower():
            filtered_urls.append(message)
        
        # Collect errors
        if "error" in message.lower() or "exception" in message.lower() or "fail" in message.lower():
            crawl_errors.append(message)
    
    # Print investigation summary
    print("\n" + "=" * 80)
    print("INVESTIGATION SUMMARY")
    print("=" * 80)
    print(f"Target Production URL: {TARGET_URL}")
    print(f"Target Staging URL: {TARGET_STAGING_URL}")
    print(f"Target Date: {TARGET_DATE}")
    print(f"Target Category: {TARGET_CATEGORY}")
    print(f"\nCrawling staging domain: {found_staging_domain}")
    print(f"Found target category ({TARGET_CATEGORY}): {found_target_category}")
    print(f"Found target blog post keywords: {found_target_keywords}")
    print(f"Found exact target URL: {found_target_url}")
    print(f"\nTotal URLs processed: {len(processed_urls)}")
    print(f"Total RSS feeds crawled: {len(rss_feeds_crawled)}")
    print(f"Total date filters applied: {len(date_filters_applied)}")
    print(f"Total URLs filtered/skipped: {len(filtered_urls)}")
    print(f"Total errors: {len(crawl_errors)}")
    
    if crawl_errors:
        print("\nErrors detected:")
        for error in crawl_errors[:10]:
            print(f"  - {error}")
    
    if date_filters_applied:
        print("\nDate filters applied (showing first 5):")
        for date_filter in date_filters_applied[:5]:
            print(f"  - {date_filter}")
    
    if rss_feeds_crawled:
        print("\nRSS feeds crawled:")
        for feed in rss_feeds_crawled[:10]:
            print(f"  - {feed}")
    
    if filtered_urls:
        print("\nFiltered/Skipped entries (showing first 10):")
        for filtered in filtered_urls[:10]:
            print(f"  - {filtered}")
    
    # Provide recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    if not found_staging_domain:
        print("⚠ CRITICAL: The staging domain (staging.awseuccontent.com) was not found in logs.")
        print("  → Verify crawler is configured to crawl staging environment")
        print("  → Check SOURCE_DOMAIN or BASE_URL environment variable")
        print("  → Ensure crawler isn't pointed at production instead of staging")
    
    if not found_target_category:
        print(f"⚠ WARNING: The '{TARGET_CATEGORY}' category was not found in logs.")
        print("  → Check if the crawler is configured to crawl this blog category")
        print("  → Verify BLOG_CATEGORIES or ENABLED_CATEGORIES includes this category")
        print(f"  → Verify the RSS feed includes this category: https://staging.awseuccontent.com/blogs/{TARGET_CATEGORY}/feed/")
    
    if not found_target_url and not found_target_keywords:
        print("⚠ CRITICAL: The target blog post about WorkSpaces Graphics bundles was not detected.")
        print("  → Check date filters in crawler (post date: March 2, 2026)")
        print("  → Verify the blog post is published on staging.awseuccontent.com")
        print("  → Check if URL pattern matches crawler configuration")
        print("  → Review content filtering logic (keywords, categories)")
    
    if date_filters_applied:
        print("⚠ INFO: Date filters were applied during crawling")
        print("  → Review START_DATE and END_DATE environment variables")
        print(f"  → Ensure date range includes {TARGET_DATE}")
    
    if crawl_errors:
        print("⚠ CRITICAL: Errors were detected during crawling - investigate above error messages")
    
    print("\nNext steps:")
    print("1. Run staging content verification (see above)")
    print("2. Verify blog post exists at: staging.awseuccontent.com")
    print("3. Check crawler configuration for:")
    print("   - Correct staging domain (staging.awseuccontent.com)")
    print(f"   - Date range includes {TARGET_DATE}")
    print(f"   - Category '{TARGET_CATEGORY}' is enabled")
    print("4. Review category/URL pattern matching logic")
    print("5. Check RSS feed contains the blog post")
    print("6. Test crawler with explicit URL if available")
    print("=" * 80)

try:
    # Check staging content first
    check_staging_content()
    
    # Check crawler configuration
    check_crawler_configuration()
    
    print("\n" + "=" * 80)
    print("CLOUDWATCH LOGS ANALYSIS")
    print("=" * 80)
    
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
            # Show last 100 events for better investigation
            analyze_log_events(response['events'][-100:])
        else:
            print("No logs found in last 30 minutes either")
            print("Checking last 2 hours...")
            
            response = logs.filter_log_events(
                logGroupName='/aws/lambda/aws-blog-crawler',
                startTime=int((datetime.now() - timedelta(hours=2)).timestamp() * 1000)
            )
            
            if response['events']:
                analyze_log_events(response['events'][-100:])
            else:
                print("No logs found in last 2 hours")
                print("\nTroubleshooting tips:")
                print("1. Verify the Lambda function name is 'aws-blog-crawler'")
                print("2. Check if crawler has been invoked recently")
                print("3. Verify IAM permissions to read CloudWatch Logs")
                print("4. Try manually invoking the crawler Lambda function")
                print("5. Check CloudWatch Logs console directly")
            
except Exception as e:
    print(f'Error accessing CloudWatch Logs: {e}')
    print("\nPossible causes:")
    print("- IAM permissions issue (logs:FilterLogEvents, lambda:GetFunctionConfiguration)")
    print("- Incorrect log group name")
    print("- Region mismatch (currently set to us-east-1)")
    print("- Network connectivity issue")
    print("- Lambda function doesn't exist")
```