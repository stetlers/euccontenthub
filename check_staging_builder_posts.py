```python
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

# Check for the specific Amazon WorkSpaces blog post from March 2, 2026
print("Checking for Amazon WorkSpaces Graphics blog post...\n")
target_url = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'

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
        print(f"  Expected date: March 2, 2026")
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
    
except Exception as e:
    print(f"Error scanning desktop-and-application-streaming posts: {str(e)}\n")

# Get Builder.AWS posts
print("\nChecking Builder.AWS posts in staging...\n")
try:
    response = table.scan(
        FilterExpression='#src = :builder',
        ExpressionAttributeNames={'#src': 'source'},
        ExpressionAttributeValues={':builder': 'builder.aws.com'}
    )

    builder_posts = response['Items']

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='#src = :builder',
            ExpressionAttributeNames={'#src': 'source'},
            ExpressionAttributeValues={':builder': 'builder.aws.com'},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        builder_posts.extend(response['Items'])

    print(f"Total Builder.AWS posts: {len(builder_posts)}\n")

    # Check for issues
    missing_authors = [p for p in builder_posts if p.get('authors') == 'AWS Builder Community']
    missing_summaries = [p for p in builder_posts if not p.get('summary') or p.get('summary') == '']

    print("CRITICAL ISSUES:")
    print("=" * 80)
    print(f"Posts with generic 'AWS Builder Community' author: {len(missing_authors)}")
    print(f"Posts without summaries: {len(missing_summaries)}")

    print("\nSample posts with generic author (first 5):")
    for i, post in enumerate(missing_authors[:5], 1):
        print(f"{i}. {post.get('title', 'No title')[:60]}...")
        print(f"   Author: {post.get('authors')}")
        print(f"   Last crawled: {post.get('last_crawled', 'Never')}")
        print(f"   Has summary: {'Yes' if post.get('summary') else 'No'}")
        print()

except Exception as e:
    print(f"Error scanning Builder.AWS posts: {str(e)}\n")
```