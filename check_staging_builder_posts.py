```python
import boto3
from datetime import datetime, timedelta
import time
import requests
from bs4 import BeautifulSoup
import feedparser
import json

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

# Check for the specific Amazon WorkSpaces blog post from March 2, 2026
print("Checking for Amazon WorkSpaces Graphics blog post...\n")
target_url = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'
target_date = '2026-03-02'

try:
    # Try to get the specific post by URL
    response = table.get_item(Key={'url': target_url})
    
    if 'Item' in response:
        post = response['Item']
        print("✓ POST FOUND in staging database!")
        print(f"  Title: {post.get('title', 'N/A')}")
        print(f"  Source: {post.get('source', 'N/A')}")
        print(f"  Date: {post.get('date', 'N/A')}")
        print(f"  Last crawled: {post.get('last_crawled', 'Never')}")
        print()
    else:
        print("✗ POST NOT FOUND in staging database!")
        print(f"  Target URL: {target_url}")
        print(f"  Expected date: {target_date}")
        print()
        
        # ENHANCED: Attempt to fetch the post directly from the web to verify it exists
        print("  Attempting to fetch post directly from AWS blog...")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            web_response = requests.get(target_url, headers=headers, timeout=10)
            
            if web_response.status_code == 200:
                soup = BeautifulSoup(web_response.content, 'html.parser')
                
                # Extract metadata to verify post exists and check date
                title_tag = soup.find('h1') or soup.find('title')
                date_meta = soup.find('meta', {'property': 'article:published_time'}) or \
                           soup.find('meta', {'name': 'publishdate'}) or \
                           soup.find('time')
                
                if title_tag:
                    print(f"  ✓ Post EXISTS on web: {title_tag.get_text().strip()[:60]}...")
                    
                    if date_meta:
                        date_content = date_meta.get('content') or date_meta.get('datetime') or date_meta.get_text()
                        print(f"  ✓ Published date found: {date_content}")
                        
                        # Parse the date to check if it matches expected date
                        try:
                            if 'T' in str(date_content):
                                parsed_date = datetime.fromisoformat(str(date_content).replace('Z', '+00:00'))
                            else:
                                parsed_date = datetime.strptime(str(date_content)[:10], '%Y-%m-%d')
                            
                            if parsed_date.strftime('%Y-%m-%d') == target_date:
                                print(f"  ✓ Date matches expected: {target_date}")
                            else:
                                print(f"  ⚠ Date mismatch: Expected {target_date}, found {parsed_date.strftime('%Y-%m-%d')}")
                        except Exception as e:
                            print(f"  ⚠ Could not parse date: {e}")
                    else:
                        print("  ⚠ No date metadata found on page")
                    
                    print("  ✗ ISSUE: Post exists on web but NOT in database - crawler not detecting it")
                else:
                    print("  ⚠ Could not extract title from page")
            elif web_response.status_code == 404:
                print(f"  ✗ Post returns 404 - may not be published yet")
            else:
                print(f"  ⚠ Unexpected status code: {web_response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"  ⚠ Could not fetch post from web: {str(e)}")
        print()
        
except Exception as e:
    print(f"✗ Error checking for specific post: {str(e)}\n")

# Check all desktop-and-application-streaming blog posts
print("Checking all Desktop and Application Streaming blog posts...\n")
try:
    response = table.scan(
        FilterExpression='contains(#url, :blog_path)',
        ExpressionAttributeNames={'#url': 'url'},
        ExpressionAttributeValues={':blog_path': 'aws.amazon.com/blogs/desktop-and-application-streaming/'}
    )
    
    das_posts = response['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='contains(#url, :blog_path)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={':blog_path': 'aws.amazon.com/blogs/desktop-and-application-streaming/'},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        das_posts.extend(response['Items'])
    
    print(f"Total Desktop and Application Streaming posts: {len(das_posts)}\n")
    
    # Sort by date and show most recent posts
    das_posts.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    print("Most recent posts (up to 10):")
    print("=" * 80)
    for i, post in enumerate(das_posts[:10], 1):
        print(f"{i}. {post.get('title', 'No title')[:70]}...")
        print(f"   URL: {post.get('url', 'N/A')[:70]}...")
        print(f"   Date: {post.get('date', 'N/A')}")
        print(f"   Last crawled: {post.get('last_crawled', 'Never')}")
        print()
    
    # ENHANCED: Analyze date range to detect date filtering issues
    print("\nDATE FILTERING ANALYSIS:")
    print("=" * 80)
    if das_posts:
        dates = [p.get('date', '') for p in das_posts if p.get('date')]
        if dates:
            print(f"Date range: {min(dates)} to {max(dates)}")
            
            # Check if recent dates are missing
            posts_on_target = [p for p in das_posts if p.get('date', '').startswith(target_date)]
            print(f"Posts on {target_date}: {len(posts_on_target)}")
            
            if posts_on_target:
                print("  Posts found on target date:")
                for post in posts_on_target:
                    print(f"    - {post.get('title', 'N/A')[:60]}...")
            
            # Check for posts in the last 30 days from target date
            recent_posts = [p for p in das_posts if p.get('date', '') >= '2026-02-01']
            print(f"Posts since 2026-02-01: {len(recent_posts)}")
            
            # ENHANCED: Check for date gaps that might indicate filtering issues
            if dates:
                dates_sorted = sorted(set(d[:10] for d in dates if len(d) >= 10))
                
                # Detect gaps of more than 30 days
                date_gaps = []
                for i in range(len(dates_sorted) - 1):
                    try:
                        date1 = datetime.strptime(dates_sorted[i], '%Y-%m-%d')
                        date2 = datetime.strptime(dates_sorted[i + 1], '%Y-%m-%d')
                        gap = (date1 - date2).days
                        if gap > 30:
                            date_gaps.append((dates_sorted[i + 1], dates_sorted[i], gap))
                    except:
                        continue
                
                if date_gaps:
                    print(f"\n⚠ DATE GAPS DETECTED (>30 days):")
                    for start, end, days in date_gaps[:5]:
                        print(f"  Gap from {start} to {end}: {days} days")
                    print(f"  This may indicate date filtering or crawler execution issues")
            
            # Display date distribution
            date_counts = {}
            for post in das_posts:
                date = post.get('date', '')
                if date:
                    month_key = date[:7]  # YYYY-MM
                    date_counts[month_key] = date_counts.get(month_key, 0) + 1
            
            print("\nPosts by month (most recent 6 months):")
            for month in sorted(date_counts.keys(), reverse=True)[:6]:
                print(f"  {month}: {date_counts[month]} posts")
                
            # ENHANCED: Check if March 2026 has abnormally low post count
            if '2026-03' in date_counts:
                avg_count = sum(date_counts.values()) / len(date_counts)
                if date_counts['2026-03'] < avg_count * 0.5:
                    print(f"  ⚠ March 2026 has unusually low post count compared to average ({avg_count:.1f})")
            else:
                print(f"  ⚠ No posts found for March 2026 (2026-03)")
        else:
            print("No valid dates found in posts")
    else:
        print("No posts found to analyze")
    
    print()
    
except Exception as e:
    print(f"Error scanning desktop-and-application-streaming posts: {str(e)}\n")

# ENHANCED: Check RSS feed directly to verify crawler source
print("\nRSS FEED VALIDATION:")
print("=" * 80)
try:
    rss_url = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/feed/'
    print(f"Fetching RSS feed: {rss_url}")
    
    feed = feedparser.parse(rss_url)
    
    if feed.entries:
        print(f"✓ RSS feed accessible with {len(feed.entries)} entries\n")
        
        # Check if target post is in RSS feed
        target_in_feed = False
        march_2_posts = []
        
        for entry in feed.entries[:20]:  # Check first 20 entries
            entry_url = entry.get('link', '')
            entry_date = entry.get('published', '') or entry.get('updated', '')
            
            if entry_url == target_url:
                target_in_feed = True
                print(f"✓ TARGET POST FOUND IN RSS FEED:")
                print(f"  Title: {entry.get('title', 'N/A')}")
                print(f"  Published: {entry_date}")
                print(f"  URL: {entry_url}")
                print(f"  ✗ ISSUE: Post in RSS but not in database - crawler parsing issue\n")
            
            # Check for any March 2, 2026 posts
            if entry_date:
                try:
                    parsed_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        parsed_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        parsed_date = datetime(*entry.updated_parsed[:6])
                    
                    if parsed_date and parsed_date.strftime('%Y-%m-%d') == target_date:
                        march_2_posts.append({
                            'title': entry.get('title', 'N/A'),
                            'url': entry.get('link', 'N/A'),
                            'date': entry_date
                        })
                except:
                    pass
        
        if not target_in_feed:
            print(f"✗ Target post NOT found in RSS feed (checked first 20 entries)")
            print(f"  This may indicate the post is not yet published or is older than recent entries\n")
        
        if march_2_posts:
            print(f"Posts from {target_date} in RSS feed: {len(march_2_posts)}")
            for post in march_2_posts:
                print(f"  - {post['title'][:60]}...")
                print(f"    {post['url']}")
            print()
        else:
            print(f"✗ No posts from {target_date} found in RSS feed")
            print(f"  This indicates the post may not be in the feed or crawler date parsing issues\n")
        
        # Show most recent entries from feed
        print("Most recent RSS feed entries (first 5):")
        for i, entry in enumerate(feed.entries[:5], 1):
            entry_date = entry.get('published', '') or entry.get('updated', '')
            print(f"{i}. {entry.get('title', 'No title')[:60]}...")
            print(f"   Date: {entry_date}")
            print(f"   URL: {entry.get('link', 'N/A')[:70]}...")
            print()
            
    else:
        print(f"✗ RSS feed returned no entries or is not accessible")
        print(f"  Feed status: {feed.get('status', 'unknown')}")
        if feed.get('bozo'):
            print(f"  Feed error: {feed.get('bozo_exception', 'unknown')}")
        print(f"  ✗ CRITICAL: Crawler cannot function without RSS feed access\n")
    
except Exception as e:
    print(f"✗ Error fetching RSS feed: {str(e)}")
    print(f"  This may indicate network issues or RSS feed changes\n")

# Check for URL pattern variations that might be missed
print("\nURL PATTERN DETECTION ANALYSIS:")
print("=" * 80)
try:
    # Check for posts with various URL patterns
    url_patterns_to_check = [
        'amazon-workspaces',
        'workspaces-graphics',
        'graphics-g6',
        'g6-gr6-g6f',
        'bundles',
        'launches-graphics'  # Added pattern from target URL
    ]
    
    print("Checking for posts containing key terms in URL:")
    for pattern in url_patterns_to_check:
        response = table.scan(
            FilterExpression='contains(#url, :pattern)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={':pattern': pattern}
        )
        
        matching_posts = response['Items']
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression='contains(#url, :pattern)',
                ExpressionAttributeNames={'#url': 'url'},
                ExpressionAttributeValues={':pattern': pattern},
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            matching_posts.extend(response['Items'])
        
        print(f"  '{pattern}': {len(matching_posts)} posts")
        
        # Show WorkSpaces-related posts from 2026
        if pattern == 'amazon-workspaces' and matching_posts:
            recent_ws = [p for p in matching_posts if p.get('date', '').startswith('2026')]
            if recent_ws:
                print(f"    Recent WorkSpaces posts in 2026: {len(recent_ws)}")
                for post in sorted(recent_ws, key=lambda x: x.get('date', ''), reverse=True)[:3]:
                    print(f"      - {post.get('date')}: {post.get('title', '