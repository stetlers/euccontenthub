```python
import boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

# Check for the specific Amazon WorkSpaces blog post from March 2, 2026
print("=" * 80)
print("DIAGNOSING AMAZON WORKSPACES GRAPHICS G6 BLOG POST ISSUE")
print("=" * 80)
print()

target_url = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'
target_date = '2026-03-02'
target_keywords = ['Graphics G6', 'Gr6', 'G6f', 'WorkSpaces']

print(f"Target URL: {target_url}")
print(f"Expected Date: {target_date}")
print(f"Keywords: {', '.join(target_keywords)}")
print()

# Step 1: Check if the specific post exists
print("STEP 1: Checking for exact URL match in database...")
print("-" * 80)
try:
    response = table.get_item(Key={'url': target_url})
    
    if 'Item' in response:
        post = response['Item']
        print("✓ POST FOUND in staging database!")
        print(f"  Title: {post.get('title', 'N/A')}")
        print(f"  Source: {post.get('source', 'N/A')}")
        print(f"  Date: {post.get('date', 'N/A')}")
        print(f"  Authors: {post.get('authors', 'N/A')}")
        print(f"  Summary: {post.get('summary', 'N/A')[:100]}...")
        print(f"  Last crawled: {post.get('last_crawled', 'Never')}")
        print()
    else:
        print("✗ POST NOT FOUND in staging database!")
        print("  This indicates the crawler did not pick up this post.")
        print()
except Exception as e:
    print(f"✗ Error checking for specific post: {str(e)}")
    print()

# Step 2: Check for similar URLs or variations
print("STEP 2: Checking for URL variations or similar posts...")
print("-" * 80)
try:
    # Check for any posts containing key URL components
    response = table.scan(
        FilterExpression='contains(#url, :url_part)',
        ExpressionAttributeNames={'#url': 'url'},
        ExpressionAttributeValues={':url_part': 'workspaces-launches-graphics'}
    )
    
    similar_posts = response['Items']
    
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='contains(#url, :url_part)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={':url_part': 'workspaces-launches-graphics'},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        similar_posts.extend(response['Items'])
    
    if similar_posts:
        print(f"✓ Found {len(similar_posts)} post(s) with similar URL patterns:")
        for post in similar_posts:
            print(f"  - {post.get('url', 'N/A')}")
            print(f"    Date: {post.get('date', 'N/A')}, Title: {post.get('title', 'N/A')[:60]}...")
        print()
    else:
        print("✗ No posts found with similar URL patterns")
        print("  The crawler may not be reaching this post at all.")
        print()
except Exception as e:
    print(f"Error checking for similar URLs: {str(e)}")
    print()

# Step 3: Check all posts from the blog category around the target date
print("STEP 3: Checking all Desktop and Application Streaming posts near March 2, 2026...")
print("-" * 80)
try:
    response = table.scan(
        FilterExpression='contains(#url, :blog_path)',
        ExpressionAttributeNames={'#url': 'url'},
        ExpressionAttributeValues={':blog_path': 'aws.amazon.com/blogs/desktop-and-application-streaming/'}
    )
    
    das_posts = response['Items']
    
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='contains(#url, :blog_path)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={':blog_path': 'aws.amazon.com/blogs/desktop-and-application-streaming/'},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        das_posts.extend(response['Items'])
    
    print(f"Total Desktop and Application Streaming posts: {len(das_posts)}")
    
    # Sort by date
    das_posts.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    # Filter posts near target date (within 30 days)
    target_dt = datetime.strptime(target_date, '%Y-%m-%d')
    nearby_posts = []
    
    for post in das_posts:
        post_date_str = post.get('date', '')
        if post_date_str:
            try:
                post_dt = datetime.strptime(post_date_str, '%Y-%m-%d')
                days_diff = abs((post_dt - target_dt).days)
                if days_diff <= 30:
                    nearby_posts.append((post, days_diff))
            except ValueError:
                continue
    
    if nearby_posts:
        print(f"\nPosts within 30 days of {target_date}:")
        nearby_posts.sort(key=lambda x: x[1])
        for post, days_diff in nearby_posts[:15]:
            print(f"  - Date: {post.get('date', 'N/A')} ({days_diff} days from target)")
            print(f"    Title: {post.get('title', 'N/A')[:65]}...")
            print(f"    URL: {post.get('url', 'N/A')[:75]}...")
            print()
    else:
        print(f"\n✗ No posts found within 30 days of {target_date}")
        print("  This suggests a date filtering issue in the crawler.")
        print()
    
    # Show most recent posts to check if crawler is working at all
    print("\nMost recent posts in database (to verify crawler is running):")
    print("-" * 80)
    for i, post in enumerate(das_posts[:10], 1):
        print(f"{i}. {post.get('title', 'No title')[:65]}...")
        print(f"   Date: {post.get('date', 'N/A')}")
        print(f"   URL: {post.get('url', 'N/A')[:75]}...")
        print(f"   Last crawled: {post.get('last_crawled', 'Never')}")
        print()
    
except Exception as e:
    print(f"Error scanning desktop-and-application-streaming posts: {str(e)}")
    print()

# Step 4: Check for posts matching keywords in title
print("STEP 4: Checking for posts matching target keywords...")
print("-" * 80)
try:
    keyword_posts = []
    
    for keyword in target_keywords:
        response = table.scan(
            FilterExpression='contains(#title, :keyword)',
            ExpressionAttributeNames={'#title': 'title'},
            ExpressionAttributeValues={':keyword': keyword}
        )
        
        posts = response['Items']
        
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression='contains(#title, :keyword)',
                ExpressionAttributeNames={'#title': 'title'},
                ExpressionAttributeValues={':keyword': keyword},
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            posts.extend(response['Items'])
        
        keyword_posts.extend(posts)
    
    # Remove duplicates
    unique_posts = {post['url']: post for post in keyword_posts}.values()
    
    if unique_posts:
        print(f"✓ Found {len(unique_posts)} post(s) matching keywords:")
        for post in unique_posts:
            print(f"  - {post.get('title', 'N/A')[:65]}...")
            print(f"    Date: {post.get('date', 'N/A')}, URL: {post.get('url', 'N/A')[:70]}...")
            print()
    else:
        print("✗ No posts found matching target keywords")
        print("  The post title may be different or not yet scraped.")
        print()
except Exception as e:
    print(f"Error checking for keyword matches: {str(e)}")
    print()

# Step 5: Analyze date distribution to detect filtering issues
print("STEP 5: Analyzing date distribution to detect filtering issues...")
print("-" * 80)
try:
    response = table.scan(
        FilterExpression='contains(#url, :blog_path)',
        ExpressionAttributeNames={'#url': 'url'},
        ExpressionAttributeValues={':blog_path': 'aws.amazon.com/blogs/desktop-and-application-streaming/'}
    )
    
    all_posts = response['Items']
    
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='contains(#url, :blog_path)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={':blog_path': 'aws.amazon.com/blogs/desktop-and-application-streaming/'},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        all_posts.extend(response['Items'])
    
    # Group by year-month
    date_counts = {}
    for post in all_posts:
        date_str = post.get('date', '')
        if date_str:
            try:
                ym = date_str[:7]  # YYYY-MM
                date_counts[ym] = date_counts.get(ym, 0) + 1
            except:
                pass
    
    # Sort and display
    sorted_dates = sorted(date_counts.items(), reverse=True)
    
    print("Post counts by month (most recent first):")
    for date_month, count in sorted_dates[:12]:
        indicator = " <-- TARGET MONTH" if date_month == target_date[:7] else ""
        print(f"  {date_month}: {count} posts{indicator}")
    
    # Check if target month has any posts
    if target_date[:7] not in date_counts:
        print(f"\n✗ CRITICAL: No posts found for {target_date[:7]}")
        print("  The crawler may have a date cutoff preventing newer posts.")
    print()
    
except Exception as e:
    print(f"Error analyzing date distribution: {str(e)}")
    print()

# Step 6: Check Builder.AWS posts (existing functionality)
print("=" * 80)
print("BUILDER.AWS POSTS ANALYSIS (EXISTING FUNCTIONALITY)")
print("=" * 80)
print()

try:
    response = table.scan(
        FilterExpression='#src = :builder',
        ExpressionAttributeNames={'#src': 'source'},
        ExpressionAttributeValues={':builder': 'builder.aws.com'}
    )

    builder_posts = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='#src = :builder',
            ExpressionAttributeNames={'#src': 'source'},
            ExpressionAttributeValues={':builder': 'builder.aws.com'},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        builder_posts.extend(response['Items'])

    print(f"Total Builder.AWS posts: {len(builder_posts)}\n")

    missing_authors = [p for p in builder_posts if p.get('authors') == 'AWS Builder Community']
    missing_summaries = [p for p in builder_posts if not p.get('summary') or p.get('summary') == '']

    print("CRITICAL ISSUES:")
    print("-" * 80)
    print(f"Posts with generic 'AWS Builder Community' author: {len(missing_authors)}")
    print(f"Posts without summaries: {len(missing_summaries)}")
    print()

    if missing_authors:
        print("Sample posts with generic author (first 5):")
        for i, post in enumerate(missing_authors[:5], 1):
            print(f"{i}. {post.get('title', 'No title')[:60]}...")
            print(f"   Author: {post.get('authors')}")
            print(f"   Last crawled: {post.get('last_crawled', 'Never')}")
            print(f"   Has summary: {'Yes' if post.get('summary') else 'No'}")
            print()

except Exception as e:
    print(f"Error scanning Builder.AWS posts: {str(e)}")
    print()

# Summary and recommendations
print("=" * 80)
print("DIAGNOSTIC SUMMARY AND RECOMMENDATIONS")
print("=" * 80)
print()
print("Based on the analysis above, check the following in the crawler:")
print()
print("1. DATE FILTERING: Verify the crawler is not filtering out posts from 2026")
print("   - Check for hardcoded date limits or 'future date' filters")
print("   - Review date parsing logic for correctness")
print()
print("2. URL PATTERN MATCHING: Ensure the crawler includes this blog category")
print("   - Verify 'desktop-and-application-streaming' is in the crawl list")
print("   - Check for URL exclusion patterns that might block this post")
print()
print("3. PAGINATION: Verify the crawler fetches all pages of the blog")
print("   - Check if there's a page limit that stops before reaching this post")
print("   - Review pagination logic in the blog scraper")
print()
print("4. CONTENT PARSING: Ensure the HTML parser handles this post's structure")
print("   - Test the parser on the specific blog post URL")
print("   - Check for changes in the blog's HTML structure")
print()
print("5. STORAGE LOGIC: Verify posts are being written to DynamoDB correctly")
print("   - Check for errors in the database write operations")
print("   - Review any deduplication logic that might skip this post")
print()
print("Next steps:")
print("  - Review crawler logs for errors or warnings")
print("  - Run the crawler manually with verbose logging")
print("  - Test the specific URL directly in the scraper")
print("=" * 80)
```