```python
#!/usr/bin/env python3
"""
Check recent crawler invocations to see what happened
Debug specific blog post detection issues
"""
import boto3
from datetime import datetime, timedelta
import json
import re

logs_client = boto3.client('logs', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

print("="*80)
print("CHECKING RECENT CRAWLER INVOCATIONS")
print("="*80)

# Specific post to investigate
TARGET_POST_TITLE = 'Amazon WorkSpaces launches Graphics G6, Gr6, and G6f bundles'
TARGET_POST_DATE = '2026-03-02'
TARGET_DOMAIN = 'staging.awseuccontent.com'

print(f"\n🔍 INVESTIGATING SPECIFIC POST:")
print(f"   Title: {TARGET_POST_TITLE}")
print(f"   Date: {TARGET_POST_DATE}")
print(f"   Domain: {TARGET_DOMAIN}")
print("="*80)

# Check both possible log groups
log_groups = [
    '/aws/lambda/aws-blog-crawler',
    '/aws/lambda/enhanced-crawler'
]

start_time = int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)

# Track findings
findings = {
    'post_found_in_logs': False,
    'date_filtering_issue': False,
    'url_pattern_issue': False,
    'content_detection_issue': False,
    'database_storage_issue': False,
    'domain_crawled': False
}

for log_group in log_groups:
    print(f"\n{log_group}:")
    print("-" * 80)
    
    try:
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            limit=500  # Increased limit for better debugging
        )
        
        if not response['events']:
            print("No logs in last 24 hours")
            continue
        
        print(f"Found {len(response['events'])} log events\n")
        
        # Look for key events
        messages = [e['message'] for e in response['events']]
        all_text = '\n'.join(messages)
        
        # Check for invocations
        if 'START RequestId' in all_text:
            invocations = all_text.count('START RequestId')
            print(f"✓ Invoked {invocations} times in last 24 hours")
        
        # Check for staging domain crawling
        if TARGET_DOMAIN in all_text or 'staging.awseuccontent' in all_text:
            print(f"✓ Staging domain ({TARGET_DOMAIN}) was crawled")
            findings['domain_crawled'] = True
        else:
            print(f"✗ Staging domain ({TARGET_DOMAIN}) NOT found in logs")
        
        # Check for Builder.AWS crawling
        if 'CRAWLING BUILDER.AWS' in all_text:
            print(f"✓ Builder.AWS crawl initiated")
        
        # Check for the specific post title
        if TARGET_POST_TITLE in all_text:
            print(f"✓ TARGET POST FOUND IN LOGS: '{TARGET_POST_TITLE}'")
            findings['post_found_in_logs'] = True
            
            # Show context around the post
            for i, line in enumerate(messages):
                if TARGET_POST_TITLE in line:
                    print(f"\n  Context around post (lines {max(0, i-2)} to {min(len(messages), i+3)}):")
                    for j in range(max(0, i-2), min(len(messages), i+3)):
                        print(f"    {messages[j].strip()}")
        else:
            print(f"✗ TARGET POST NOT FOUND in logs")
        
        # Check for date filtering logic
        date_filter_patterns = [
            r'date.*filter',
            r'filtering.*date',
            TARGET_POST_DATE,
            r'2026-03',
            r'published.*date'
        ]
        
        for pattern in date_filter_patterns:
            if re.search(pattern, all_text, re.IGNORECASE):
                print(f"✓ Date filtering logic detected: {pattern}")
                if 'skip' in all_text.lower() or 'filter' in all_text.lower():
                    findings['date_filtering_issue'] = True
                    print(f"  ⚠️  Possible date filtering issue detected")
        
        # Check for URL patterns
        url_patterns = [
            r'url.*pattern',
            r'http.*staging\.awseuccontent',
            r'processing.*url'
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            if matches:
                print(f"✓ URL pattern found: {pattern} ({len(matches)} occurrences)")
        
        # Check for posts changed
        if 'posts changed' in all_text.lower():
            for line in messages:
                if 'posts changed' in line.lower():
                    print(f"✓ {line.strip()}")
                    # Extract number of changed posts
                    match = re.search(r'(\d+)\s+posts?\s+changed', line, re.IGNORECASE)
                    if match:
                        num_changed = int(match.group(1))
                        if num_changed == 0:
                            print(f"  ⚠️  Zero posts changed - possible content detection issue")
                            findings['content_detection_issue'] = True
        
        # Check for ECS invocation
        if 'invoking ECS' in all_text.lower() or 'Started ECS task' in all_text:
            print(f"✓ ECS Selenium crawler invoked")
            task_count = all_text.count('Started ECS task')
            if task_count > 0:
                print(f"  Started {task_count} ECS tasks")
        else:
            print(f"✗ ECS Selenium crawler NOT invoked")
        
        # Check for database operations
        db_patterns = [
            r'DynamoDB.*put',
            r'storing.*post',
            r'saved.*database',
            r'database.*error'
        ]
        
        for pattern in db_patterns:
            if re.search(pattern, all_text, re.IGNORECASE):
                print(f"✓ Database operation detected: {pattern}")
        
        # Check for errors
        if 'ERROR' in all_text or 'Error' in all_text:
            print(f"\n⚠️  Errors detected:")
            for line in messages:
                if 'ERROR' in line or 'Error' in line:
                    print(f"  {line.strip()}")
                    if 'date' in line.lower():
                        findings['date_filtering_issue'] = True
                    if 'url' in line.lower():
                        findings['url_pattern_issue'] = True
        
        # Show relevant log lines mentioning staging or 2026
        print(f"\nRelevant log lines (staging/2026/WorkSpaces):")
        for event in response['events']:
            message = event['message'].strip()
            if any(keyword in message.lower() for keyword in ['staging', '2026', 'workspaces', 'g6']):
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                print(f"  [{timestamp.strftime('%H:%M:%S')}] {message[:150]}")
        
        # Show last 10 log lines
        print(f"\nLast 10 log lines:")
        for event in response['events'][-10:]:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            print(f"  [{timestamp.strftime('%H:%M:%S')}] {message[:100]}")
        
    except logs_client.exceptions.ResourceNotFoundException:
        print("Log group does not exist")
    except Exception as e:
        print(f"ERROR: {e}")

# Check DynamoDB for the post
print("\n" + "="*80)
print("CHECKING DYNAMODB FOR POST")
print("="*80)

table_names = ['aws-blog-posts', 'blog-posts', 'crawler-posts']

for table_name in table_names:
    try:
        table = dynamodb.Table(table_name)
        
        # Try to scan for posts matching the title or date
        response = table.scan(
            FilterExpression='contains(#title, :title) OR begins_with(#date, :date)',
            ExpressionAttributeNames={
                '#title': 'title',
                '#date': 'published_date'
            },
            ExpressionAttributeValues={
                ':title': 'WorkSpaces',
                ':date': TARGET_POST_DATE
            },
            Limit=100
        )
        
        if response['Items']:
            print(f"\n✓ Found posts in table '{table_name}':")
            for item in response['Items']:
                title = item.get('title', 'N/A')
                pub_date = item.get('published_date', 'N/A')
                url = item.get('url', 'N/A')
                
                if TARGET_POST_TITLE in title:
                    print(f"\n  🎯 FOUND TARGET POST IN DATABASE!")
                    print(f"     Title: {title}")
                    print(f"     Date: {pub_date}")
                    print(f"     URL: {url}")
                    print(f"     Full item: {json.dumps(item, indent=2, default=str)}")
                else:
                    print(f"  - {title[:80]}... (Date: {pub_date})")
                    if TARGET_DOMAIN in url:
                        print(f"    URL: {url}")
        else:
            print(f"\n✗ No matching posts found in table '{table_name}'")
            findings['database_storage_issue'] = True
            
    except Exception as e:
        print(f"\n✗ Could not access table '{table_name}': {e}")

print("\n" + "="*80)
print("DIAGNOSTIC SUMMARY")
print("="*80)

print(f"\n📊 Investigation Results for: {TARGET_POST_TITLE}")
print(f"   Published: {TARGET_POST_DATE}")
print("-" * 80)

if findings['post_found_in_logs']:
    print("✓ Post was detected by crawler (found in logs)")
else:
    print("✗ Post was NOT detected by crawler (not in logs)")

if findings['domain_crawled']:
    print(f"✓ Domain {TARGET_DOMAIN} was crawled")
else:
    print(f"✗ Domain {TARGET_DOMAIN} was NOT crawled")

print("\n🔍 Potential Issues Identified:")

if findings['date_filtering_issue']:
    print("  ⚠️  DATE FILTERING ISSUE: The post date (2026-03-02) may be filtered out")
    print("      Check date range filters in crawler configuration")

if findings['url_pattern_issue']:
    print("  ⚠️  URL PATTERN ISSUE: URL pattern matching may be excluding this post")
    print("      Check URL regex patterns and domain whitelist")

if findings['content_detection_issue']:
    print("  ⚠️  CONTENT DETECTION ISSUE: Post content may not be parsed correctly")
    print("      Check HTML parsing logic and CSS selectors")

if findings['database_storage_issue']:
    print("  ⚠️  DATABASE STORAGE ISSUE: Post not found in DynamoDB tables")
    print("      Check database write operations and error handling")

if not any([findings['date_filtering_issue'], findings['url_pattern_issue'], 
            findings['content_detection_issue'], findings['database_storage_issue']]):
    print("  ℹ️  No obvious issues detected from logs and database")
    print("     The post may be published in the future or on a non-crawled domain")

print("\n" + "="*80)
print("RECOMMENDED ACTIONS")
print("="*80)
print("""
1. Verify the post actually exists on staging.awseuccontent.com
2. Check if the publish date (2026-03-02) is in the future - crawler may filter future dates
3. Review crawler date range configuration (--days-back parameter)
4. Verify staging.awseuccontent.com is in the crawler's domain list
5. Check if the post URL matches expected patterns
6. Test the HTML parser against the specific post page
7. Review DynamoDB write permissions and error logs
8. Run crawler manually with verbose logging for this specific URL
""")

print("\n" + "="*80)
print("KEY QUESTION")
print("="*80)
print("\nDid the crawler invoke ECS Selenium tasks?")
print("If NO, that's why summaries aren't being restored.")
```