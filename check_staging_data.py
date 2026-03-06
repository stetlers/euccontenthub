```python
"""
Check what data exists in staging DynamoDB tables and debug specific blog post detection
"""

import boto3
from decimal import Decimal
from datetime import datetime

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
    'keywords': ['WorkSpaces', 'Graphics', 'G6', 'Gr6', 'G6f', 'bundles']
}

print("=" * 80)
print("STAGING DATA CHECK & CRAWLER DEBUG")
print("=" * 80)

# Check posts table
print("\n📊 AWS Blog Posts (Staging)")
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
            for post in all_posts:
                title = post.get('title', '').lower()
                if any(keyword.lower() in title for keyword in TARGET_POST['keywords']):
                    print(f"\n   Partial match found: {post.get('title')}")
                    print(f"   Date: {post.get('date_published')}")
                    print(f"   URL: {post.get('url')}")
        
        # Search by date
        print(f"\n🗓️  Searching for posts with date matching '{TARGET_POST['date']}'...")
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
        else:
            print("   ❌ No posts found with matching date")
        
        # Analyze date range in database
        print("\n📅 DATE RANGE ANALYSIS")
        print("-" * 80)
        dates = []
        for post in all_posts:
            date_str = post.get('date_published', '')
            if date_str:
                try:
                    # Try to parse various date formats
                    if 'T' in str(date_str):
                        date_obj = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
                    elif '-' in str(date_str) and len(str(date_str).split('-')[0]) == 4:
                        date_obj = datetime.strptime(str(date_str).split('T')[0], '%Y-%m-%d')
                    else:
                        continue
                    dates.append(date_obj)
                except:
                    pass
        
        if dates:
            min_date = min(dates)
            max_date = max(dates)
            print(f"Earliest post: {min_date.strftime('%Y-%m-%d')}")
            print(f"Latest post: {max_date.strftime('%Y-%m-%d')}")
            print(f"Target date: 2026-03-02")
            
            # Check if target date is in range
            target_date = datetime(2026, 3, 2)
            if target_date < min_date:
                print(f"\n⚠️  TARGET DATE IS BEFORE EARLIEST POST (Gap: {(min_date - target_date).days} days)")
                print("   Possible issue: Date filtering is excluding older posts")
            elif target_date > max_date:
                print(f"\n⚠️  TARGET DATE IS AFTER LATEST POST (Gap: {(target_date - max_date).days} days)")
                print("   Possible issue: Crawler hasn't processed posts from March 2026")
            else:
                print(f"\n✅ Target date is within range")
        
        # Display target post details if found
        if found_target and target_post_data:
            print("\n✅ TARGET POST FOUND IN DATABASE!")
            print("-" * 80)
            print(f"Title: {target_post_data.get('title')}")
            print(f"URL: {target_post_data.get('url')}")
            print(f"Date: {target_post_data.get('date_published')}")
            print(f"Source: {target_post_data.get('source')}")
            print(f"Summary: {target_post_data.get('summary', 'N/A')[:100]}...")
            print(f"Label: {target_post_data.get('label', 'N/A')}")
            print(f"Content length: {len(target_post_data.get('content', ''))} chars")
            print(f"\n✅ Post exists in database - issue may be with frontend filtering or display")
        else:
            print("\n❌ TARGET POST NOT FOUND IN DATABASE!")
            print("-" * 80)
            print("Possible causes:")
            print("1. 🕷️  CRAWLER ISSUE: Post not being crawled from source")
            print("   - Check if staging.awseuccontent.com crawler is configured correctly")
            print("   - Verify crawler date range filters")
            print("   - Check crawler URL patterns/sources")
            print("\n2. 🔍 CONTENT DETECTION: Post exists but not matching criteria")
            print("   - Check if post title format differs slightly")
            print("   - Verify post is on the expected source page")
            print("\n3. ⏰ DATE FILTERING: Post date outside crawler date range")
            print(f"   - Post date: March 2, 2026")
            print(f"   - Check crawler date filters in code")
            print("\n4. 💾 DATABASE STORAGE: Post crawled but not stored")
            print("   - Check crawler logs for errors")
            print("   - Verify DynamoDB write permissions")
        
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
        print("\n⚠️  No posts found in staging table!")
        print("   This is why the staging site appears empty.")
        print("\n❌ CRAWLER NOT RUNNING OR FAILING")
        print("   Action required: Run crawler or check crawler logs")
        
except Exception as e:
    print(f"❌ Error reading posts table: {e}")
    import traceback
    traceback.print_exc()

# Check profiles table
print("\n\n👤 User Profiles (Staging)")
print("-" * 80)

try:
    response = profiles_table.scan(
        Select='COUNT'
    )
    profile_count = response['Count']
    print(f"Total profiles: {profile_count}")
    
    if profile_count > 0:
        # Get sample profiles
        response = profiles_table.scan(Limit=5)
        profiles = response.get('Items', [])
        
        print(f"\nSample profiles:")
        for i, profile in enumerate(profiles, 1):
            print(f"\n{i}. {profile.get('display_name', 'No name')}")
            print(f"   Email: {profile.get('email', 'No email')}")
            print(f"   Bookmarks: {len(profile.get('bookmarks', []))}")
            print(f"   Created: {profile.get('created_at', 'No date')}")
    else:
        print("\n⚠️  No profiles found in staging table!")
        
except Exception as e:
    print(f"❌ Error reading profiles table: {e}")

# Summary and recommendations
print("\n" + "=" * 80)
print("DIAGNOSTIC SUMMARY")
print("=" * 80)

if post_count == 0:
    print("\n⚠️  STAGING TABLES ARE EMPTY!")
    print("\nThis explains why the staging site shows no content.")
    print("\nTo fix this, you need to:")
    print("1. Copy data from production to staging:")
    print("   python copy_data_to_staging.py")
    print("\n2. Or run the crawler in staging to populate data:")
    print("   - Visit https://staging.awseuccontent.com")
    print("   - Click the 'Crawl for New Posts' button")
    print("\n3. Check crawler configuration and logs")
else:
    print(f"\n📊 Database Status: {post_count} posts and {profile_count} profiles")
    
    if not found_target:
        print(f"\n❌ Target post NOT FOUND")
        print("\n🔧 RECOMMENDED DEBUG STEPS:")
        print("\n1. Check crawler source configuration:")
        print("   - Verify staging crawler is monitoring correct RSS/blog feeds")
        print("   - Check if AWS What's New or AWS Blog is in sources")
        print("\n2. Check crawler date filters:")
        print("   - Look for date range filters in crawler code")
        print("   - Verify March 2026 is not filtered out")
        print("\n3. Manual test:")
        print("   - Trigger crawler manually from staging admin panel")
        print("   - Monitor crawler logs for errors or skipped posts")
        print("\n4. Check source URL patterns:")
        print("   - Verify crawler regex/patterns match target post URL")
        print("   - Test with similar WorkSpaces posts")
        print("\n5. Database permissions:")
        print("   - Verify staging Lambda has write access to DynamoDB")
        print("   - Check CloudWatch logs for permission errors")
    else:
        print(f"\n✅ Target post FOUND in database")
        print("\n   Issue is likely on frontend/display side, not crawler")
        print("   Check frontend filtering, date parsing, or rendering logic")

print("\n" + "=" * 80)
```