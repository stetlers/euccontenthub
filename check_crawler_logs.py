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
dynamodb = boto3.client('dynamodb', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')

print("=" * 80)
print("CRAWLER INVESTIGATION TOOL - Amazon WorkSpaces Blog Post")
print("=" * 80)

# Target blog post URL to investigate
TARGET_URL = "https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/"
TARGET_DATE = "2026-03-02"
TARGET_KEYWORDS = ["workspaces", "graphics", "bundles", "g6"]

def check_blog_post_accessibility():
    """Check if the blog post URL is accessible"""
    print("\n" + "=" * 80)
    print("1. CHECKING BLOG POST ACCESSIBILITY")
    print("=" * 80)
    try:
        import urllib.request
        import ssl
        
        # Create SSL context that doesn't verify certificates (for staging)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        staging_url = TARGET_URL.replace("aws.amazon.com", "staging.awseuccontent.com")
        
        print(f"Testing production URL: {TARGET_URL}")
        try:
            req = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'AWS-Blog-Crawler/1.0'})
            response = urllib.request.urlopen(req, timeout=10, context=ctx)
            print(f"✓ Production URL accessible (Status: {response.getcode()})")
        except Exception as e:
            print(f"✗ Production URL not accessible: {str(e)}")
        
        print(f"\nTesting staging URL: {staging_url}")
        try:
            req = urllib.request.Request(staging_url, headers={'User-Agent': 'AWS-Blog-Crawler/1.0'})
            response = urllib.request.urlopen(req, timeout=10, context=ctx)
            print(f"✓ Staging URL accessible (Status: {response.getcode()})")
            
            # Read content to verify it's the right post
            content = response.read().decode('utf-8', errors='ignore')
            keywords_found = [kw for kw in TARGET_KEYWORDS if kw.lower() in content.lower()]
            print(f"  Keywords found in content: {', '.join(keywords_found) if keywords_found else 'None'}")
            
        except Exception as e:
            print(f"✗ Staging URL not accessible: {str(e)}")
            
    except ImportError:
        print("⚠ urllib not available, skipping accessibility check")
    except Exception as e:
        print(f"Error during accessibility check: {str(e)}")

def check_dynamodb_entries():
    """Check if the blog post exists in DynamoDB"""
    print("\n" + "=" * 80)
    print("2. CHECKING DYNAMODB ENTRIES")
    print("=" * 80)
    
    table_names = ['aws-blogs-staging', 'aws-blogs-production', 'aws-blogs']
    
    for table_name in table_names:
        try:
            print(f"\nChecking table: {table_name}")
            
            # Scan for entries matching our criteria
            response = dynamodb.scan(
                TableName=table_name,
                FilterExpression='contains(#url, :url_fragment) OR contains(title, :title_fragment)',
                ExpressionAttributeNames={
                    '#url': 'url'
                },
                ExpressionAttributeValues={
                    ':url_fragment': {'S': 'workspaces-launches-graphics'},
                    ':title_fragment': {'S': 'WorkSpaces'}
                },
                Limit=10
            )
            
            if response.get('Items'):
                print(f"  ✓ Found {len(response['Items'])} matching entries")
                for item in response['Items']:
                    url = item.get('url', {}).get('S', 'N/A')
                    title = item.get('title', {}).get('S', 'N/A')
                    date = item.get('published_date', {}).get('S', 'N/A')
                    print(f"    - {date}: {title[:60]}...")
                    print(f"      URL: {url}")
            else:
                print(f"  ✗ No matching entries found in {table_name}")
                
        except dynamodb.exceptions.ResourceNotFoundException:
            print(f"  ⚠ Table {table_name} does not exist")
        except Exception as e:
            print(f"  Error scanning {table_name}: {str(e)}")

def check_crawler_configuration():
    """Check crawler Lambda configuration"""
    print("\n" + "=" * 80)
    print("3. CHECKING CRAWLER CONFIGURATION")
    print("=" * 80)
    
    function_names = ['aws-blog-crawler', 'aws-blog-crawler-staging']
    
    for function_name in function_names:
        try:
            print(f"\nChecking function: {function_name}")
            response = lambda_client.get_function_configuration(FunctionName=function_name)
            
            print(f"  Runtime: {response.get('Runtime', 'N/A')}")
            print(f"  Timeout: {response.get('Timeout', 'N/A')} seconds")
            print(f"  Memory: {response.get('MemorySize', 'N/A')} MB")
            print(f"  Last Modified: {response.get('LastModified', 'N/A')}")
            
            env_vars = response.get('Environment', {}).get('Variables', {})
            if env_vars:
                print("  Environment Variables:")
                for key, value in env_vars.items():
                    if 'DATE' in key.upper() or 'FILTER' in key.upper() or 'URL' in key.upper():
                        print(f"    {key}: {value}")
            else:
                print("  No relevant environment variables found")
                
        except lambda_client.exceptions.ResourceNotFoundException:
            print(f"  ⚠ Function {function_name} does not exist")
        except Exception as e:
            print(f"  Error checking {function_name}: {str(e)}")

def analyze_log_events(events):
    """Analyze log events for crawler behavior and potential issues"""
    print("\n" + "=" * 80)
    print("4. ANALYZING CRAWLER LOGS")
    print("=" * 80)
    print(f"\nFound {len(events)} log events\n")
    
    # Tracking variables for investigation
    found_target_url = False
    found_target_category = False
    found_target_date = False
    crawl_errors = []
    processed_urls = []
    filtered_urls = []
    dynamodb_writes = []
    date_filters = []
    
    for event in events:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event["message"].strip()
        
        # Print all log messages
        print(f'{timestamp.strftime("%H:%M:%S")} | {message}')
        
        # Check for target URL or category
        if "desktop-and-application-streaming" in message.lower():
            found_target_category = True
        
        if any(kw in message.lower() for kw in TARGET_KEYWORDS) and "graphic" in message.lower():
            found_target_url = True
        
        if TARGET_DATE in message or "2026-03-02" in message:
            found_target_date = True
        
        # Extract processed URLs
        if "processing" in message.lower() or "crawling" in message.lower():
            url_match = re.search(r'https?://[^\s]+', message)
            if url_match:
                processed_urls.append(url_match.group(0))
        
        # Detect filtering or skipping
        if "skip" in message.lower() or "filter" in message.lower() or "ignor" in message.lower():
            filtered_urls.append(message)
        
        # Detect date filtering
        if "date" in message.lower() and ("filter" in message.lower() or "range" in message.lower()):
            date_filters.append(message)
        
        # Detect DynamoDB writes
        if "dynamodb" in message.lower() or "writing" in message.lower() or "saved" in message.lower():
            dynamodb_writes.append(message)
        
        # Collect errors
        if "error" in message.lower() or "exception" in message.lower() or "fail" in message.lower():
            crawl_errors.append(message)
    
    # Print investigation summary
    print("\n" + "=" * 80)
    print("LOG ANALYSIS SUMMARY")
    print("=" * 80)
    print(f"Target URL: {TARGET_URL}")
    print(f"Target Date: {TARGET_DATE}")
    print(f"\nFound target category (desktop-and-application-streaming): {found_target_category}")
    print(f"Found target blog post keywords: {found_target_url}")
    print(f"Found target date in logs: {found_target_date}")
    print(f"\nTotal URLs processed: {len(processed_urls)}")
    print(f"Total URLs filtered/skipped: {len(filtered_urls)}")
    print(f"Total DynamoDB write operations: {len(dynamodb_writes)}")
    print(f"Total date filter messages: {len(date_filters)}")
    print(f"Total errors: {len(crawl_errors)}")
    
    if crawl_errors:
        print("\n⚠ Errors detected:")
        for error in crawl_errors[:10]:
            print(f"  - {error}")
    
    if date_filters:
        print("\n📅 Date filtering messages:")
        for msg in date_filters[:5]:
            print(f"  - {msg}")
    
    if dynamodb_writes:
        print("\n💾 DynamoDB write operations:")
        for msg in dynamodb_writes[:5]:
            print(f"  - {msg}")
    else:
        print("\n⚠ No DynamoDB write operations detected!")
    
    if filtered_urls:
        print("\n🚫 Filtered/Skipped entries (showing first 10):")
        for filtered in filtered_urls[:10]:
            print(f"  - {filtered}")
    
    # Provide recommendations
    print("\n" + "=" * 80)
    print("DIAGNOSTIC RECOMMENDATIONS")
    print("=" * 80)
    
    issues_found = False
    
    if not found_target_category:
        issues_found = True
        print("⚠ ISSUE: The 'desktop-and-application-streaming' category was not found in logs.")
        print("  → Check if the crawler is configured to crawl this blog category")
        print("  → Verify the RSS feed or sitemap includes this category")
        print("  → Check crawler's category whitelist/blacklist configuration")
    
    if not found_target_url:
        issues_found = True
        print("⚠ ISSUE: The target blog post about WorkSpaces Graphics bundles was not detected.")
        print("  → Check date filters in crawler (post date: March 2, 2026)")
        print("  → Verify the blog post is published on staging.awseuccontent.com")
        print("  → Check if URL pattern matches crawler configuration")
        print("  → Review content filtering logic (keywords, categories)")
    
    if not found_target_date:
        issues_found = True
        print("⚠ ISSUE: The target date (March 2, 2026) was not found in logs.")
        print("  → Verify date range configuration allows posts from March 2026")
        print("  → Check if date parsing is working correctly")
        print("  → Review date format expectations in crawler code")
    
    if crawl_errors:
        issues_found = True
        print("⚠ ISSUE: Errors were detected during crawling - investigate above error messages")
    
    if not dynamodb_writes:
        issues_found = True
        print("⚠ ISSUE: No DynamoDB write operations detected!")
        print("  → Check IAM permissions for DynamoDB PutItem/BatchWriteItem")
        print("  → Verify DynamoDB table name configuration")
        print("  → Review crawler logic for database write conditions")
        print("  → Check if crawler is in dry-run mode")
    
    if not issues_found:
        print("✓ No obvious issues detected in logs")
        print("  The crawler appears to be running normally")
        print("  The blog post may not match filtering criteria")
    
    return {
        'found_target_url': found_target_url,
        'found_target_category': found_target_category,
        'found_target_date': found_target_date,
        'processed_urls': len(processed_urls),
        'filtered_urls': len(filtered_urls),
        'dynamodb_writes': len(dynamodb_writes),
        'errors': len(crawl_errors)
    }

def get_crawler_logs(minutes=5):
    """Retrieve and analyze crawler logs"""
    print("\n" + "=" * 80)
    print(f"FETCHING CRAWLER LOGS (last {minutes} minutes)")
    print("=" * 80)
    
    log_groups = ['/aws/lambda/aws-blog-crawler', '/aws/lambda/aws-blog-crawler-staging']
    
    for log_group in log_groups:
        try:
            print(f"\nChecking log group: {log_group}")
            response = logs.filter_log_events(
                logGroupName=log_group,
                startTime=int((datetime.now() - timedelta(minutes=minutes)).timestamp() * 1000)
            )
            
            if response['events']:
                print(f"Found {len(response['events'])} events")
                return analyze_log_events(response['events'])
            else:
                print(f"No logs found in {log_group}")
                
        except logs.exceptions.ResourceNotFoundException:
            print(f"⚠ Log group {log_group} does not exist")
        except Exception as e:
            print(f"Error accessing {log_group}: {str(e)}")
    
    return None

def main():
    """Main execution flow"""
    # Step 1: Check blog post accessibility
    check_blog_post_accessibility()
    
    # Step 2: Check DynamoDB entries
    check_dynamodb_entries()
    
    # Step 3: Check crawler configuration
    check_crawler_configuration()
    
    # Step 4: Analyze recent logs (last 5 minutes)
    result = get_crawler_logs(minutes=5)
    
    if result is None:
        print("\nNo recent logs found. Checking last 30 minutes...")
        result = get_crawler_logs(minutes=30)
    
    if result is None:
        print("\nNo logs found in last 30 minutes.")
        print("\nTroubleshooting tips:")
        print("1. Verify the Lambda function exists and is named correctly")
        print("2. Check if crawler has been invoked recently")
        print("3. Verify IAM permissions to read CloudWatch Logs")
        print("4. Try manually invoking the crawler Lambda function")
        print("5. Check CloudWatch Events/EventBridge rules for scheduling")
    
    # Final summary
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("1. Verify blog post exists at staging.awseuccontent.com")
    print("2. Check crawler configuration for date range filters")
    print("3. Review category/URL pattern matching logic in crawler code")
    print("4. Verify DynamoDB table permissions and configuration")
    print("5. Test crawler with