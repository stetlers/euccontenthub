```python
import boto3
from datetime import datetime, timedelta
import time
import requests
from bs4 import BeautifulSoup
import feedparser
import json
import re

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

# Diagnostic counters for root cause analysis
diagnostics = {
    'url_filtering_issues': [],
    'date_parsing_issues': [],
    'storage_issues': [],
    'crawler_logic_issues': []
}

# Check for the specific Amazon WorkSpaces blog post from March 2, 2026
print("="*100)
print("STAGING CRAWLER DIAGNOSTIC REPORT - Amazon WorkSpaces Graphics G6 Post")
print("="*100)
print(f"Target URL: https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/")
print(f"Expected Date: 2026-03-02")
print(f"Diagnostic Time: {datetime.now().isoformat()}")
print("="*100)
print()

target_url = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'
target_date = '2026-03-02'

# DIAGNOSTIC STEP 1: Database Storage Check
print("STEP 1: DATABASE STORAGE VERIFICATION")
print("-" * 80)
try:
    response = table.get_item(Key={'url': target_url})
    
    if 'Item' in response:
        post = response['Item']
        print("✓ POST FOUND in staging database!")
        print(f"  Title: {post.get('title', 'N/A')}")
        print(f"  Source: {post.get('source', 'N/A')}")
        print(f"  Date: {post.get('date', 'N/A')}")
        print(f"  Last crawled: {post.get('last_crawled', 'Never')}")
        print(f"  Storage timestamp: {post.get('timestamp', 'N/A')}")
        print("\n✓ STORAGE MECHANISM: Working correctly - post is stored")
        print()
    else:
        print("✗ POST NOT FOUND in staging database!")
        print(f"  Target URL: {target_url}")
        print(f"  Expected date: {target_date}")
        diagnostics['storage_issues'].append("Target post not found in database")
        print("\n✗ STORAGE MECHANISM: Post missing - investigating upstream issues...")
        print()
        
        # DIAGNOSTIC: Verify post exists on the web
        print("  → Verifying post existence on AWS blog website...")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            web_response = requests.get(target_url, headers=headers, timeout=15)
            
            if web_response.status_code == 200:
                soup = BeautifulSoup(web_response.content, 'html.parser')
                
                # Extract comprehensive metadata
                title_tag = soup.find('h1') or soup.find('title')
                date_meta = soup.find('meta', {'property': 'article:published_time'}) or \
                           soup.find('meta', {'name': 'publishdate'}) or \
                           soup.find('meta', {'name': 'date'}) or \
                           soup.find('time', {'class': 'published'}) or \
                           soup.find('time')
                
                # Check for alternative date patterns in page content
                date_patterns = [
                    r'Published[:\s]+(\d{4}-\d{2}-\d{2})',
                    r'Posted[:\s]+(\d{4}-\d{2}-\d{2})',
                    r'(\d{2}/\d{2}/\d{4})',
                    r'(\w+ \d{1,2},? \d{4})'
                ]
                
                found_dates = []
                page_text = soup.get_text()
                for pattern in date_patterns:
                    matches = re.findall(pattern, page_text)
                    found_dates.extend(matches)
                
                if title_tag:
                    extracted_title = title_tag.get_text().strip()
                    print(f"    ✓ Post EXISTS on web")
                    print(f"    Title: {extracted_title[:80]}...")
                    
                    if date_meta:
                        date_content = date_meta.get('content') or date_meta.get('datetime') or date_meta.get_text()
                        print(f"    ✓ Date metadata found: {date_content}")
                        
                        # Comprehensive date parsing
                        try:
                            parsed_date = None
                            if 'T' in str(date_content):
                                parsed_date = datetime.fromisoformat(str(date_content).replace('Z', '+00:00').split('+')[0].split('T')[0] + 'T00:00:00')
                            elif '-' in str(date_content):
                                parsed_date = datetime.strptime(str(date_content)[:10], '%Y-%m-%d')
                            elif '/' in str(date_content):
                                parsed_date = datetime.strptime(str(date_content), '%m/%d/%Y')
                            
                            if parsed_date:
                                parsed_date_str = parsed_date.strftime('%Y-%m-%d')
                                print(f"    Parsed date: {parsed_date_str}")
                                
                                if parsed_date_str == target_date:
                                    print(f"    ✓ Date matches expected: {target_date}")
                                else:
                                    print(f"    ⚠ Date mismatch: Expected {target_date}, found {parsed_date_str}")
                                    diagnostics['date_parsing_issues'].append(f"Date mismatch: expected {target_date}, found {parsed_date_str}")
                        except Exception as e:
                            print(f"    ✗ Date parsing error: {e}")
                            diagnostics['date_parsing_issues'].append(f"Could not parse date '{date_content}': {e}")
                    else:
                        print("    ⚠ No standard date metadata found")
                        if found_dates:
                            print(f"    Alternative date patterns found: {found_dates[:3]}")
                        diagnostics['date_parsing_issues'].append("No standard date metadata in HTML")
                    
                    print("\n    ✗✗ ROOT CAUSE INDICATOR: Post exists on web but NOT in database")
                    print("       → Crawler is NOT detecting/storing this post")
                    diagnostics['crawler_logic_issues'].append("Post exists on web but not stored in database")
                else:
                    print("    ⚠ Could not extract title from page - possible HTML structure issue")
                    diagnostics['crawler_logic_issues'].append("Could not parse HTML structure")
                    
            elif web_response.status_code == 404:
                print(f"    ✗ Post returns 404 - Not published or URL incorrect")
                diagnostics['url_filtering_issues'].append("Target URL returns 404")
            else:
                print(f"    ⚠ Unexpected HTTP status: {web_response.status_code}")
                diagnostics['crawler_logic_issues'].append(f"Unexpected HTTP status: {web_response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"    ✗ Request timeout - network or performance issue")
            diagnostics['crawler_logic_issues'].append("Request timeout when fetching post")
        except requests.exceptions.RequestException as e:
            print(f"    ✗ Request failed: {str(e)}")
            diagnostics['crawler_logic_issues'].append(f"Request exception: {str(e)}")
        print()
        
except Exception as e:
    print(f"✗ Database query error: {str(e)}")
    diagnostics['storage_issues'].append(f"Database query failed: {str(e)}")
    print()

# DIAGNOSTIC STEP 2: URL Filtering Analysis
print("\nSTEP 2: URL FILTERING ANALYSIS")
print("-" * 80)
das_posts = []  # Initialize das_posts for later use
try:
    # Check for URL variations and similar posts
    url_components = {
        'base_path': 'aws.amazon.com/blogs/desktop-and-application-streaming/',
        'slug_parts': ['amazon-workspaces', 'launches-graphics', 'g6', 'gr6', 'g6f', 'bundles']
    }
    
    print(f"Checking if blog path '{url_components['base_path']}' is being crawled...")
    
    response = table.scan(
        FilterExpression='contains(#url, :blog_path)',
        ExpressionAttributeNames={'#url': 'url'},
        ExpressionAttributeValues={':blog_path': url_components['base_path']}
    )
    
    das_posts = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='contains(#url, :blog_path)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={':blog_path': url_components['base_path']},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        das_posts.extend(response['Items'])
    
    print(f"✓ Blog path IS being crawled: {len(das_posts)} total posts found")
    
    if len(das_posts) == 0:
        print("  ✗✗ ROOT CAUSE: Blog path not in crawler's URL filter list")
        diagnostics['url_filtering_issues'].append("Blog path not being crawled at all")
    else:
        print("  ✓ URL Filtering: Blog path is included in crawler scope")
        
        # Check for posts with similar URL components
        similar_posts = []
        for post in das_posts:
            url = post.get('url', '')
            matching_components = sum(1 for component in url_components['slug_parts'] if component in url.lower())
            if matching_components >= 2:
                similar_posts.append({
                    'url': url,
                    'title': post.get('title', 'N/A'),
                    'date': post.get('date', 'N/A'),
                    'matches': matching_components
                })
        
        if similar_posts:
            print(f"\n  Similar posts found (sharing URL components): {len(similar_posts)}")
            for post in sorted(similar_posts, key=lambda x: x['matches'], reverse=True)[:5]:
                print(f"    - [{post['date']}] {post['title'][:50]}...")
                print(f"      Matching components: {post['matches']}")
        else:
            print(f"\n  ⚠ No similar posts found with shared URL components")
            print(f"    This specific post type may have unique URL pattern")
    
    print()
    
except Exception as e:
    print(f"✗ URL filtering analysis error: {str(e)}")
    diagnostics['url_filtering_issues'].append(f"Analysis failed: {str(e)}")
    print()

# DIAGNOSTIC STEP 3: Date Parsing and Filtering Analysis
print("\nSTEP 3: DATE PARSING AND FILTERING ANALYSIS")
print("-" * 80)
try:
    if das_posts:
        das_posts.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        print(f"Total Desktop and Application Streaming posts: {len(das_posts)}")
        
        # Analyze date distribution
        dates = [p.get('date', '') for p in das_posts if p.get('date')]
        
        if dates:
            min_date = min(dates)
            max_date = max(dates)
            print(f"Date range in database: {min_date} to {max_date}")
            
            # Check if target date is within range
            if min_date <= target_date <= max_date:
                print(f"  ✓ Target date {target_date} IS within crawled date range")
                posts_on_target = [p for p in das_posts if p.get('date', '').startswith(target_date)]
                print(f"  Posts stored on {target_date}: {len(posts_on_target)}")
                
                if posts_on_target:
                    print(f"    ✓ Other posts from target date ARE being stored:")
                    for post in posts_on_target:
                        print(f"      - {post.get('title', 'N/A')[:60]}...")
                    print(f"    → Date filtering is working, but specific post is missing")
                    diagnostics['crawler_logic_issues'].append("Date filtering works but specific post missing")
                else:
                    print(f"    ✗✗ ROOT CAUSE INDICATOR: No posts from {target_date} in database")
                    print(f"       → Crawler may have date filter excluding this date")
                    diagnostics['date_parsing_issues'].append(f"No posts from {target_date} despite date being in range")
            else:
                print(f"  ✗✗ ROOT CAUSE INDICATOR: Target date {target_date} is OUTSIDE crawled range")
                print(f"     → Crawler's date filter may exclude future dates or this specific date")
                diagnostics['date_parsing_issues'].append(f"Target date {target_date} outside range {min_date} to {max_date}")
            
            # Analyze date gaps
            print("\n  Analyzing date continuity...")
            dates_sorted = sorted(set(d[:10] for d in dates if len(d) >= 10))
            
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
                print(f"  ⚠ DATE GAPS DETECTED (>30 days): {len(date_gaps)} gaps found")
                for start, end, days in date_gaps[:3]:
                    print(f"    Gap: {start} to {end} = {days} days")
                    if start <= target_date <= end:
                        print(f"      ✗✗ ROOT CAUSE: Target date {target_date} falls in this gap!")
                        diagnostics['date_parsing_issues'].append(f"Target date falls in {days}-day gap from {start} to {end}")
                print(f"  → This indicates crawler execution gaps or date filter issues")
            else:
                print(f"  ✓ No significant date gaps detected")
            
            # Monthly distribution analysis
            print("\n  Monthly post distribution:")
            date_counts = {}
            for post in das_posts:
                date = post.get('date', '')
                if date:
                    month_key = date[:7]  # YYYY-MM
                    date_counts[month_key] = date_counts.get(month_key, 0) + 1
            
            for month in sorted(date_counts.keys(), reverse=True)[:12]:
                print(f"    {month}: {date_counts[month]} posts")
            
            # Check March 2026 specifically
            target_month = target_date[:7]
            if target_month in date_counts:
                avg_count