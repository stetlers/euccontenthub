```python
"""
Check detailed status of Builder.AWS posts in staging and diagnose missing Amazon WorkSpaces blog post
"""
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("Checking Builder.AWS posts status in staging...")
print("=" * 80)

try:
    response = table.scan(
        FilterExpression='#src = :builder',
        ExpressionAttributeNames={'#src': 'source'},
        ExpressionAttributeValues={':builder': 'builder.aws.com'}
    )

    posts = response['Items']

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='#src = :builder',
            ExpressionAttributeNames={'#src': 'source'},
            ExpressionAttributeValues={':builder': 'builder.aws.com'},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        posts.extend(response['Items'])

    print(f"Total posts: {len(posts)}\n")

    # Categorize posts
    with_real_authors = [p for p in posts if p.get('authors') != 'AWS Builder Community']
    with_summaries = [p for p in posts if p.get('summary')]
    with_labels = [p for p in posts if p.get('label')]

    print("STATUS BREAKDOWN:")
    print("-" * 80)
    print(f"✓ Posts with real authors: {len(with_real_authors)}/{len(posts)}")
    print(f"✓ Posts with summaries: {len(with_summaries)}/{len(posts)}")
    print(f"✓ Posts with labels: {len(with_labels)}/{len(posts)}")

    if with_real_authors:
        print(f"\nSample posts with real authors:")
        for post in with_real_authors[:5]:
            print(f"  • {post.get('title', 'No title')[:60]}")
            print(f"    Author: {post.get('authors')}")
            print(f"    Summary: {'Yes' if post.get('summary') else 'No'}")
            print(f"    Label: {post.get('label', 'None')}")

    if with_summaries:
        print(f"\nSample posts with summaries:")
        for post in with_summaries[:3]:
            print(f"  • {post.get('title', 'No title')[:60]}")
            print(f"    Summary: {post.get('summary', '')[:100]}...")

    # DIAGNOSTIC: Check for Amazon WorkSpaces Graphics G6 blog post from March 2, 2026
    print("\n" + "=" * 80)
    print("DIAGNOSTIC: Checking for Amazon WorkSpaces Graphics G6 blog post...")
    print("-" * 80)
    
    # Search for WorkSpaces-related posts
    workspaces_keywords = ['workspaces', 'graphics', 'g6', 'gr6', 'g6f', 'bundle']
    workspaces_posts = []
    
    for post in posts:
        title = (post.get('title') or '').lower()
        content = (post.get('content') or '').lower()
        if any(keyword in title or keyword in content for keyword in workspaces_keywords):
            workspaces_posts.append(post)
    
    print(f"Found {len(workspaces_posts)} WorkSpaces-related posts in staging")
    
    # Check for posts from March 2026
    target_date = datetime(2026, 3, 2, tzinfo=timezone.utc)
    march_2026_posts = []
    
    for post in posts:
        post_date_str = post.get('published_date') or post.get('date')
        if post_date_str:
            try:
                # Handle various date formats
                for date_format in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S.%fZ']:
                    try:
                        post_date = datetime.strptime(post_date_str.split('+')[0].split('Z')[0], date_format)
                        if post_date.year == 2026 and post_date.month == 3:
                            march_2026_posts.append(post)
                        break
                    except ValueError:
                        continue
            except Exception as e:
                pass
    
    print(f"Found {len(march_2026_posts)} posts from March 2026")
    
    # Check specifically for the Graphics G6 post
    g6_post_found = False
    for post in workspaces_posts:
        title = (post.get('title') or '').lower()
        post_date_str = post.get('published_date') or post.get('date')
        
        if 'graphics' in title and any(x in title for x in ['g6', 'gr6', 'g6f']):
            print(f"\n✓ Found potential match:")
            print(f"  Title: {post.get('title')}")
            print(f"  Date: {post_date_str}")
            print(f"  URL: {post.get('url')}")
            print(f"  Source: {post.get('source')}")
            g6_post_found = True
    
    if not g6_post_found:
        print("\n✗ Amazon WorkSpaces Graphics G6 blog post NOT FOUND in staging")
        print("\nPossible issues to investigate:")
        print("  1. Date filtering: Check if crawler is filtering out posts from 2026")
        print("  2. URL patterns: Verify crawler is matching the correct URL pattern")
        print("  3. Source detection: Ensure post source is correctly identified")
        print("  4. Scraping logic: Check if content extraction is working")
        print("  5. Storage: Verify posts are being written to DynamoDB")
        
    # Check all Amazon WorkSpaces posts regardless of date
    print("\n" + "-" * 80)
    print("All WorkSpaces-related posts in staging:")
    if workspaces_posts:
        for post in sorted(workspaces_posts, key=lambda x: x.get('published_date', x.get('date', '')), reverse=True)[:10]:
            print(f"\n  • {post.get('title', 'No title')}")
            print(f"    Date: {post.get('published_date', post.get('date', 'Unknown'))}")
            print(f"    URL: {post.get('url', 'No URL')}")
    else:
        print("  No WorkSpaces-related posts found")

    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    if len(with_real_authors) < len(posts):
        print(f"  • {len(posts) - len(with_real_authors)} posts still need real authors")
        print("  • Run crawler again to process remaining posts")
    if len(with_summaries) < len(with_real_authors):
        print(f"  • {len(with_real_authors) - len(with_summaries)} posts with authors need summaries")
        print("  • Check summary generator logs")
    if len(with_labels) < len(with_summaries):
        print(f"  • {len(with_summaries) - len(with_labels)} posts with summaries need labels")
        print("  • Check classifier logs")
    
    if not g6_post_found:
        print("\nCRAWLER DEBUGGING:")
        print("  • Review crawler logs for March 2, 2026 execution")
        print("  • Check date range filters in crawler configuration")
        print("  • Verify URL pattern matching logic includes WorkSpaces posts")
        print("  • Test scraping logic on target URL manually")
        print("  • Confirm DynamoDB write permissions and error logs")
        print("  • Check if staging.awseuccontent.com RSS/feed includes the post")

except ClientError as e:
    print(f"✗ DynamoDB Error: {e.response['Error']['Message']}")
    print("  Check AWS credentials and table permissions")
except Exception as e:
    print(f"✗ Unexpected Error: {str(e)}")
    print("  Review script configuration and dependencies")
```