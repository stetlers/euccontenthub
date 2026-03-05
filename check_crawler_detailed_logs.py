```python
import boto3
from datetime import datetime, timedelta
import re
import json

logs_client = boto3.client('logs', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')

print("=" * 60)
print("Detailed Sitemap Crawler Logs - Enhanced Debugging")
print("=" * 60)

log_group = '/aws/lambda/aws-blog-crawler'
# Extended time window to capture more historical logs
start_time = int((datetime.now() - timedelta(hours=6)).timestamp() * 1000)

# Target blog post URL to track
target_url = "amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles"
target_date = "2026-03-02"
full_target_url = f"https://aws.amazon.com/blogs/desktop-and-application-streaming/{target_url}/"

print(f"\nInvestigating blog post from {target_date}")
print(f"URL fragment: {target_url}")
print(f"Full URL: {full_target_url}\n")

# Step 1: Check if blog post is accessible
print("=" * 60)
print("STEP 1: VERIFYING BLOG POST ACCESSIBILITY")
print("=" * 60)

try:
    import urllib.request
    import urllib.error
    
    req = urllib.request.Request(full_target_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        response = urllib.request.urlopen(req, timeout=10)
        status_code = response.getcode()
        content = response.read().decode('utf-8')
        
        print(f"✓ Blog post is accessible (HTTP {status_code})")
        print(f"  Content length: {len(content)} bytes")
        
        # Check for key indicators in content
        if target_date in content:
            print(f"  ✓ Publication date {target_date} found in content")
        else:
            print(f"  ⚠️  Publication date {target_date} NOT found in content")
        
        if 'WorkSpaces' in content or 'workspaces' in content.lower():
            print(f"  ✓ WorkSpaces keyword found in content")
        
    except urllib.error.HTTPError as e:
        print(f"✗ Blog post not accessible (HTTP {e.code})")
        print(f"  This may indicate the post is not published in staging")
    except urllib.error.URLError as e:
        print(f"✗ Network error accessing blog post: {e.reason}")
    except Exception as e:
        print(f"✗ Error accessing blog post: {e}")
        
except ImportError:
    print("⚠️  urllib not available, skipping accessibility check")

# Step 2: Check crawler logs
print("\n" + "=" * 60)
print("STEP 2: ANALYZING CRAWLER LOGS")
print("=" * 60)

try:
    response = logs_client.filter_log_events(
        logGroupName=log_group,
        startTime=start_time,
        filterPattern=''
    )
    
    print(f"\nTotal log events retrieved: {len(response['events'])}\n")
    
    # Statistics tracking
    sitemap_urls_found = []
    blog_posts_processed = []
    workspaces_posts = []
    target_post_found = False
    target_post_logs = []
    error_patterns = []
    date_filter_logs = []
    dynamodb_writes = []
    filtering_logs = []
    
    # Analyze all events for patterns
    for event in response['events']:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event['message'].strip()
        
        # Track sitemap processing
        if 'sitemap' in message.lower() and ('processing' in message.lower() or 'fetching' in message.lower()):
            sitemap_urls_found.append((timestamp, message))
        
        # Track blog post URLs being processed
        if '/blogs/desktop-and-application-streaming/' in message:
            blog_posts_processed.append((timestamp, message))
            if 'workspaces' in message.lower():
                workspaces_posts.append((timestamp, message))
        
        # Check for target post
        if target_url in message or target_date in message:
            target_post_found = True
            target_post_logs.append((timestamp, message))
        
        # Track date filtering logic
        if any(keyword in message.lower() for keyword in ['date filter', 'filtering by date', 'date range', 'lastmod', target_date]):
            date_filter_logs.append((timestamp, message))
        
        # Track DynamoDB operations
        if any(keyword in message.lower() for keyword in ['dynamodb', 'writing to table', 'put_item', 'batch_write']):
            dynamodb_writes.append((timestamp, message))
        
        # Track filtering logic
        if any(keyword in message.lower() for keyword in ['filtered out', 'skipping', 'ignoring', 'excluded']):
            filtering_logs.append((timestamp, message))
        
        # Track errors
        if any(keyword in message.lower() for keyword in ['error', 'failed', 'exception', 'timeout']):
            error_patterns.append((timestamp, message))
    
    # Summary statistics
    print("CRAWLER STATISTICS:")
    print(f"  Sitemaps processed: {len(sitemap_urls_found)}")
    print(f"  Blog posts found: {len(blog_posts_processed)}")
    print(f"  WorkSpaces-related posts: {len(workspaces_posts)}")
    print(f"  Target post detected: {'YES' if target_post_found else 'NO'}")
    print(f"  Date filtering logs: {len(date_filter_logs)}")
    print(f"  DynamoDB write operations: {len(dynamodb_writes)}")
    print(f"  Filtering operations: {len(filtering_logs)}")
    print(f"  Errors encountered: {len(error_patterns)}")
    
    # Display target post logs if found
    if target_post_logs:
        print("\n" + "=" * 60)
        print("TARGET POST FOUND IN LOGS")
        print("=" * 60)
        for ts, msg in target_post_logs:
            print(f"{ts.strftime('%Y-%m-%d %H:%M:%S')} | {msg}")
    
    # Display recent sitemaps processed
    if sitemap_urls_found:
        print("\n" + "=" * 60)
        print("RECENT SITEMAPS PROCESSED")
        print("=" * 60)
        for ts, sitemap in sitemap_urls_found[-10:]:
            print(f"{ts.strftime('%H:%M:%S')} | {sitemap}")
    
    # Display date filtering logs
    if date_filter_logs:
        print("\n" + "=" * 60)
        print("DATE FILTERING LOGIC")
        print("=" * 60)
        for ts, msg in date_filter_logs[-15:]:
            print(f"{ts.strftime('%H:%M:%S')} | {msg}")
    
    # Display filtering operations
    if filtering_logs:
        print("\n" + "=" * 60)
        print("FILTERING OPERATIONS (Posts excluded)")
        print("=" * 60)
        for ts, msg in filtering_logs[-20:]:
            print(f"{ts.strftime('%H:%M:%S')} | {msg}")
    
    # Display DynamoDB operations
    if dynamodb_writes:
        print("\n" + "=" * 60)
        print("DYNAMODB WRITE OPERATIONS")
        print("=" * 60)
        for ts, msg in dynamodb_writes[-15:]:
            print(f"{ts.strftime('%H:%M:%S')} | {msg}")
    
    # Display errors if any
    if error_patterns:
        print("\n" + "=" * 60)
        print("ERRORS DETECTED")
        print("=" * 60)
        for ts, err_msg in error_patterns[-20:]:
            print(f"{ts.strftime('%H:%M:%S')} | {err_msg}")
    
except logs_client.exceptions.ResourceNotFoundException:
    print(f"✗ Log group '{log_group}' not found.")
    print("  Please verify the log group name and ensure the Lambda function exists.")
    response = {'events': []}
except Exception as e:
    print(f"✗ Error retrieving logs: {e}")
    print(f"  Error type: {type(e).__name__}")
    response = {'events': []}

# Step 3: Check DynamoDB table for the blog post
print("\n" + "=" * 60)
print("STEP 3: CHECKING DYNAMODB TABLE")
print("=" * 60)

try:
    # Try common table names
    table_names = ['aws-blog-posts', 'BlogPosts', 'aws-blogs', 'blog-posts-staging']
    table_found = False
    
    for table_name in table_names:
        try:
            table = dynamodb.Table(table_name)
            # Query for the target post
            response_scan = table.scan(
                FilterExpression='contains(#url, :url_fragment) OR contains(#date, :target_date)',
                ExpressionAttributeNames={'#url': 'url', '#date': 'publishDate'},
                ExpressionAttributeValues={':url_fragment': target_url, ':target_date': target_date},
                Limit=10
            )
            
            table_found = True
            print(f"✓ Found DynamoDB table: {table_name}")
            
            if response_scan['Items']:
                print(f"  ✓ Target post FOUND in DynamoDB ({len(response_scan['Items'])} matching items)")
                for item in response_scan['Items']:
                    print(f"\n  Item details:")
                    print(f"    URL: {item.get('url', 'N/A')}")
                    print(f"    Title: {item.get('title', 'N/A')}")
                    print(f"    Date: {item.get('publishDate', 'N/A')}")
                    print(f"    Timestamp: {item.get('timestamp', 'N/A')}")
            else:
                print(f"  ✗ Target post NOT found in DynamoDB")
                print(f"    This indicates the post was not written to the database")
            
            # Get recent entries for comparison
            recent_scan = table.scan(Limit=5)
            print(f"\n  Recent entries in table (last 5):")
            for item in recent_scan.get('Items', [])[:5]:
                print(f"    - {item.get('publishDate', 'N/A')}: {item.get('url', 'N/A')[:80]}")
            
            break
            
        except dynamodb.meta.client.exceptions.ResourceNotFoundException:
            continue
        except Exception as e:
            print(f"  ⚠️  Error accessing table {table_name}: {e}")
            continue
    
    if not table_found:
        print(f"✗ Could not find DynamoDB table")
        print(f"  Tried table names: {', '.join(table_names)}")
        print(f"  Please verify the correct table name")
        
except Exception as e:
    print(f"✗ Error checking DynamoDB: {e}")

# Step 4: Check Lambda function configuration
print("\n" + "=" * 60)
print("STEP 4: CHECKING LAMBDA CONFIGURATION")
print("=" * 60)

try:
    function_name = 'aws-blog-crawler'
    lambda_config = lambda_client.get_function_configuration(FunctionName=function_name)
    
    print(f"✓ Lambda function: {function_name}")
    print(f"  Runtime: {lambda_config.get('Runtime', 'N/A')}")
    print(f"  Timeout: {lambda_config.get('Timeout', 'N/A')} seconds")
    print(f"  Memory: {lambda_config.get('MemorySize', 'N/A')} MB")
    print(f"  Last modified: {lambda_config.get('LastModified', 'N/A')}")
    
    # Check environment variables for date filters
    env_vars = lambda_config.get('Environment', {}).get('Variables', {})
    if env_vars:
        print(f"\n  Environment variables:")
        for key, value in env_vars.items():
            if any(keyword in key.lower() for keyword in ['date', 'filter', 'range', 'days']):
                print(f"    {key}: {value}")
    
except lambda_client.exceptions.ResourceNotFoundException:
    print(f"✗ Lambda function '{function_name}' not found")
except Exception as e:
    print(f"⚠️  Error checking Lambda configuration: {e}")

# Diagnosis and recommendations
print("\n" + "=" * 60)
print("DIAGNOSIS & RECOMMENDATIONS")
print("=" * 60)

if not target_post_found:
    print("✗ TARGET POST NOT FOUND IN CRAWLER LOGS")
    print("\nRoot cause analysis:")
    print("  1. Post may not be in the sitemap XML yet")
    print("  2. Sitemap cache needs to be refreshed")
    print("  3. Date filtering may exclude posts from future dates (2026-03-02)")
    print("  4. Post may be in draft state on staging environment")
    print("  5. Crawler may not be processing the correct sitemap index")
    
    print("\nImmediate actions:")
    print("  ☐ Manually check sitemap at: https://aws.amazon.com/blogs/desktop-and-application-streaming/sitemap.xml")
    print(f"  ☐ Search for: {target_url}")
    print(f"  ☐ Verify lastmod date matches: {target_date}")
    print("  ☐ Check crawler date range filter in Lambda code")
    print("  ☐ Review if future dates (2026) are being filtered out")
    print("  ☐ Trigger manual crawler run with verbose logging")
    print("  ☐ Clear any sitemap caching mechanisms")
else:
    print("✓ Target post WAS detected in crawler logs")
    
    if not dynamodb_writes:
        print("\n⚠️  WARNING: No DynamoDB write operations found in logs")
        print("  This suggests:")
        print("    - DynamoDB writes may be failing silently")
        print("    - IAM permissions issue for DynamoDB access")
        print("    - Lambda function may not have DynamoDB integration")
        print("\n  Actions:")
        print("    ☐ Check Lambda IAM role for DynamoDB permissions")
        print("    ☐ Verify DynamoDB table name in Lambda code")
        print("    ☐ Add explicit error handling for DynamoDB operations")

if filtering_logs:
    print(f"\n⚠️  Found {len(filtering_logs)} filtering operations")
    print("  Review filtering logs above to see if target post was excluded")

if error_patterns:
    print(f"\n⚠️  Found {len(error_patterns)} errors in logs")
    print("  Review error details above for potential issues")

# Detailed log output (last 200 lines for comprehensive context)
print("\n" + "=" * 60)
print("DETAILED LOG TAIL (Last 200 events)")
print("=" * 60 + "\n")

if response.get('events'):
    for event in response['events'][-200:]:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event['message'].strip()
        
        # Highlight important lines
        prefix = ""
        if target_url in message or target_date in message:
            prefix = ">>> [TARGET] "
        elif 'error' in message.lower() or 'failed' in message.lower():
            prefix = "[ERROR] "
        elif 