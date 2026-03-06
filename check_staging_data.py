```python
"""
Check what data exists in staging DynamoDB tables and debug specific blog post detection
Enhanced with web accessibility checks and crawler configuration verification
"""

import boto3
import requests
from decimal import Decimal
from datetime import datetime
import json
from urllib.parse import urlparse

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# Staging tables
posts_table = dynamodb.Table('aws-blog-posts-staging')
profiles_table = dynamodb.Table('euc-user-profiles-staging')

# Target blog post details for debugging
TARGET_POST = {
    'title': 'Amazon WorkSpaces launches Graphics G6, Gr6, and G6f bundles',
    'date': 'March 2, 2026',
    'date_formats': ['2026-03-02', '03/02/2026', 'March 2, 2026', '2026-03-02T00:00:00'],
    'keywords': ['WorkSpaces', 'Graphics', 'G6', 'Gr6', 'G6f', 'bundles'],
    'expected_sources': [
        'https://aws.amazon.com/blogs/desktop-and-application-streaming/',
        'https://aws.amazon.com/about-aws/whats-new/',
        'https://aws.amazon.com/blogs/aws/'
    ]
}

# Staging endpoint
STAGING_URL = 'https://staging.awseuccontent.com'

print("=" * 80)
print("STAGING DATA CHECK & CRAWLER DEBUG")
print("=" * 80)

# Test staging endpoint accessibility
print("\n🌐 TESTING STAGING ENDPOINT ACCESSIBILITY")
print("-" * 80)
try:
    response = requests.get(STAGING_URL, timeout=10)
    print(f"Staging site status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Staging site is accessible")
    else:
        print(f"⚠️  Staging site returned status code: {response.status_code}")
except requests.exceptions.RequestException as e:
    print(f"❌ Failed to access staging site: {e}")

# Test crawler endpoint if available
try:
    crawler_test_url = f"{STAGING_URL}/api/crawler/status"
    response = requests.get(crawler_test_url, timeout=5)
    if response.status_code == 200:
        print(f"✅ Crawler API accessible")
        try:
            crawler_status = response.json()
            print(f"   Last crawl: {crawler_status.get('last_crawl', 'N/A')}")
            print(f"   Status: {crawler_status.get('status', 'N/A')}")
        except:
            pass
except:
    print("⚠️  Crawler API endpoint not found or not accessible")

# Check posts table
print("\n📊 AWS BLOG POSTS (STAGING)")
print("-" * 80)

try:
    response = posts_table.scan(
        Select='COUNT'
    )
    post_count = response['Count']
    print(f"Total posts: {post_count}")
    
    # Search for the specific blog post
    print(f"\n🔍 SEARCHING FOR TARGET POST: '{TARGET_POST['title']}'")
    print("-" * 80)
    
    found_target = False
    target_post_data = None
    
    if post_count > 0:
        # Scan all posts to find the target
        response = posts_table.scan()
        all_posts = response.get('Items', [])
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = posts_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            all_posts.extend(response.get('Items', []))
        
        print(f"Scanning {len(all_posts)} total posts...")
        
        # Search by exact title match
        for post in all_posts:
            if post.get('title', '').strip() == TARGET_POST['title']:
                found_target = True
                target_post_data = post
                break
        
        # Search by partial title match
        if not found_target:
            print("\n⚠️  Exact title not found. Searching for partial matches...")
            partial_matches = []
            for post in all_posts:
                title = post.get('title', '').lower()
                # Check if at least 3 keywords match
                matches = sum(1 for keyword in TARGET_POST['keywords'] if keyword.lower() in title)
                if matches >= 3:
                    partial_matches.append((post, matches))
            
            if partial_matches:
                partial_matches.sort(key=lambda x: x[1], reverse=True)
                print(f"\n   Found {len(partial_matches)} potential matches:")
                for post, match_count in partial_matches[:5]:
                    print(f"\n   - {post.get('title')} (matches: {match_count})")
                    print(f"     Date: {post.get('date_published')}")
                    print(f"     URL: {post.get('url')}")
            else:
                print("   ❌ No partial matches found")
        
        # Search by date
        print(f"\n🗓️  SEARCHING FOR POSTS WITH DATE: '{TARGET_POST['date']}'")
        print("-" * 80)
        date_matches = []
        for post in all_posts:
            post_date = post.get('date_published', '')
            if any(date_fmt in str(post_date) for date_fmt in TARGET_POST['date_formats']):
                date_matches.append(post)
        
        if date_matches:
            print(f"   Found {len(date_matches)} posts with matching date:")
            for post in date_matches[:5]:
                print(f"   - {post.get('title')}")
                print(f"     Date: {post.get('date_published')}")
                print(f"     URL: {post.get('url')}")
        else:
            print("   ❌ No posts found with matching date")
        
        # Analyze date range in database
        print("\n📅 DATE RANGE ANALYSIS")
        print("-" * 80)
        dates = []
        date_parse_errors = 0
        for post in all_posts:
            date_str = post.get('date_published', '')
            if date_str:
                try:
                    # Try to parse various date formats
                    if 'T' in str(date_str):
                        date_obj = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
                    elif '-' in str(date_str) and len(str(date_str).split('-')[0]) == 4:
                        date_obj = datetime.strptime(str(date_str).split('T')[0], '%Y-%m-%d')
                    elif '/' in str(date_str):
                        date_obj = datetime.strptime(str(date_str), '%m/%d/%Y')
                    else:
                        continue
                    dates.append(date_obj)
                except:
                    date_parse_errors += 1
        
        if date_parse_errors > 0:
            print(f"⚠️  Failed to parse {date_parse_errors} dates")
        
        if dates:
            min_date = min(dates)
            max_date = max(dates)
            print(f"Earliest post: {min_date.strftime('%Y-%m-%d')}")
            print(f"Latest post: {max_date.strftime('%Y-%m-%d')}")
            print(f"Target date: 2026-03-02")
            print(f"Date range span: {(max_date - min_date).days} days")
            
            # Check if target date is in range
            target_date = datetime(2026, 3, 2)
            if target_date < min_date:
                print(f"\n⚠️  TARGET DATE IS BEFORE EARLIEST POST (Gap: {(min_date - target_date).days} days)")
                print("   🔴 CRITICAL ISSUE: Date filtering is excluding older posts")
                print("   Action: Check crawler date range configuration")
            elif target_date > max_date:
                print(f"\n⚠️  TARGET DATE IS AFTER LATEST POST (Gap: {(target_date - max_date).days} days)")
                print("   🔴 CRITICAL ISSUE: Crawler hasn't processed posts from March 2026")
                print("   Action: Verify crawler is running and check source feeds")
            else:
                print(f"\n✅ Target date is within range (between {min_date.strftime('%Y-%m-%d')} and {max_date.strftime('%Y-%m-%d')})")
                print("   ⚠️  Post should exist but wasn't found - possible content filtering issue")
        else:
            print("❌ No valid dates found in any posts")
        
        # Analyze post sources
        print("\n🔗 SOURCE ANALYSIS")
        print("-" * 80)
        sources = {}
        for post in all_posts:
            source = post.get('source', 'Unknown')
            url = post.get('url', '')
            # Extract domain from URL
            if url:
                try:
                    domain = urlparse(url).netloc
                    if domain:
                        source = domain
                except:
                    pass
            sources[source] = sources.get(source, 0) + 1
        
        print(f"Posts by source:")
        for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {source}: {count} posts")
        
        print(f"\n🎯 Expected sources for target post:")
        for src in TARGET_POST['expected_sources']:
            print(f"   - {src}")
        
        # Check if expected sources are being crawled
        crawled_sources = list(sources.keys())
        missing_sources = []
        for expected in TARGET_POST['expected_sources']:
            found = False
            for crawled in crawled_sources:
                if expected in crawled or crawled in expected:
                    found = True
                    break
            if not found:
                missing_sources.append(expected)
        
        if missing_sources:
            print(f"\n⚠️  Missing expected sources in database:")
            for src in missing_sources:
                print(f"   ❌ {src}")
            print("\n   🔴 ISSUE: Crawler may not be configured to monitor these sources")
        else:
            print(f"\n✅ All expected sources are represented in database")
        
        # Display target post details if found
        if found_target and target_post_data:
            print("\n" + "=" * 80)
            print("✅ TARGET POST FOUND IN DATABASE!")
            print("=" * 80)
            print(f"Title: {target_post_data.get('title')}")
            print(f"URL: {target_post_data.get('url')}")
            print(f"Date: {target_post_data.get('date_published')}")
            print(f"Source: {target_post_data.get('source')}")
            print(f"Summary: {target_post_data.get('summary', 'N/A')[:150]}...")
            print(f"Label: {target_post_data.get('label', 'N/A')}")
            print(f"Content length: {len(target_post_data.get('content', ''))} chars")
            
            # Test if post is accessible via URL
            post_url = target_post_data.get('url')
            if post_url:
                print(f"\n🔗 Testing post URL accessibility...")
                try:
                    response = requests.head(post_url, timeout=5, allow_redirects=True)
                    print(f"   URL status: {response.status_code}")
                    if response.status_code == 200:
                        print("   ✅ Post URL is accessible")
                    else:
                        print(f"   ⚠️  Post URL returned {response.status_code}")
                except Exception as e:
                    print(f"   ❌ Failed to access post URL: {e}")
            
            print(f"\n✅ CONCLUSION: Post exists in database")
            print("   Issue is likely with frontend filtering, date parsing, or display logic")
        else:
            print("\n" + "=" * 80)
            print("❌ TARGET POST NOT FOUND IN DATABASE!")
            print("=" * 80)
            print("\n🔍 ROOT CAUSE ANALYSIS:")
            print("\nPossible causes (in order of likelihood):")
            print("\n1. 🕷️  CRAWLER SOURCE CONFIGURATION")
            print("   - Crawler may not be monitoring the correct RSS feed or blog source")
            print("   - The post may be published on a source not in crawler's source list")
            print(f"   - Expected sources: {', '.join(TARGET_POST['expected_sources'])}")
            print("   - Action: Verify crawler source configuration in staging environment")
            
            print("\n2. ⏰ DATE FILTERING IN CRAWLER")
            if dates and target_date < min_date:
                print(f"   - 🔴 CONFIRMED: Target date ({target_date.strftime('%Y-%m-%d')}) is before earliest post ({min_date.strftime('%Y-%m-%d')})")
                print("   - Crawler is configured to ignore posts before a certain date")
                print("   - Action: Update crawler date filter or remove date restrictions")
            elif dates and target_date > max_date:
                print(f"   - 🔴 CONFIRMED: Target date ({target_date.strftime('%Y-%m-%d')}) is after latest post ({max_date.strftime('%Y-%m-%d')})")
                print("   - Crawler hasn't processed recent posts or hasn't run recently")
                print("   - Action: Trigger crawler manually or check crawler schedule")
            else:
                print("   - Date range appears valid, but post still missing")
                print("   - Action: Check if crawler has specific date exclusion rules")
            
            print("\n3. 🔍 CONTENT FILTERING OR PARSING")
            print("   - Post may be filtered out by keyword/category rules")
            print("   - Title format may not match expected patterns")
            print("   - Action: Review crawler content filtering logic")
            
            print("\n4. 💾 DATABASE INGESTION FAILURE")
            print("   - Post may have been crawled but failed to write to DynamoDB")
            print("   - Possible permission issues or data validation errors")
            print("   - Action: Check CloudWatch logs for DynamoDB write errors")
            
            print("\n5. 🔄 CRAWLER NOT RUNNING")
            print("   - Crawler may not have run since post was published")
            print("   - Scheduled crawler may be disabled in staging")
            print("   - Action: Check crawler execution logs and schedule configuration")
        
        # Get sample posts for reference
        print("\n\n📋 SAMPLE POSTS (First 5)")
        print("-" * 80)
        response = posts_table.scan(Limit=5)
        posts = response.get('Items', [])
        
        for i, post in enumerate(posts, 1):
            print(f"\n{i}. {post.get('title', 'No title')}")
            print(f"   URL: {post.get('url', 'No URL')}")
            print(f"   Date: {post.get('date_published', 'No date')}")
            print(f"   Source: {post.get('source', 'No source')}")
            print(f"   Has summary: {'Yes' if post.get('summary') else 'No'}")
            print(f"   Has label: {'Yes' if post.get('label') else 'No'}")
    else:
        print("\n⚠️  NO POSTS FOUND IN STAGING TABLE!")
        print("   This is why the staging site appears empty.")
        print("\n❌ CRAWLER NOT RUNNING OR FAILING")
        print("\n   Possible causes:")
        print("   1.