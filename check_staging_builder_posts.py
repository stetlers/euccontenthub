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

# Check staging crawler configuration and RSS feed
print("\nChecking staging crawler configuration...\n")
print("=" * 80)
try:
    # Check if staging crawler is configured to scrape desktop-and-application-streaming blog
    ssm = boto3.client('ssm', region_name='us-east-1')
    
    try:
        crawler_config = ssm.get_parameter(Name='/staging/crawler/blog-sources', WithDecryption=True)
        config_value = crawler_config['Parameter']['Value']
        
        print("✓ Crawler configuration retrieved")
        
        # Check if desktop-and-application-streaming is in the sources
        if 'desktop-and-application-streaming' in config_value:
            print("✓ Desktop and Application Streaming blog IS configured in crawler sources")
        else:
            print("✗ Desktop and Application Streaming blog NOT found in crawler sources!")
            print("  This may explain why posts are not being detected.")
        
        print(f"\nCrawler sources configuration:\n{config_value}\n")
        
    except ssm.exceptions.ParameterNotFound:
        print("⚠ Crawler configuration parameter not found in SSM")
        print("  Parameter: /staging/crawler/blog-sources")
    
    # Check staging RSS feed directly
    print("\nVerifying RSS feed accessibility at staging.awseuccontent.com...")
    print("=" * 80)
    
    import urllib.request
    import xml.etree.ElementTree as ET
    
    staging_rss_url = 'https://staging.awseuccontent.com/blogs/desktop-and-application-streaming/feed/'
    
    try:
        req = urllib.request.Request(staging_rss_url, headers={'User-Agent': 'AWS-Staging-Crawler-Check/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            rss_content = response.read()
            
        print(f"✓ RSS feed is accessible at {staging_rss_url}")
        print(f"  HTTP Status: {response.status}")
        
        # Parse RSS to check if the target post is present
        root = ET.fromstring(rss_content)
        
        # Find all items in the RSS feed
        items = root.findall('.//item')
        print(f"\n  Total items in RSS feed: {len(items)}")
        
        # Look for the specific post
        target_found = False
        for item in items:
            title_elem = item.find('title')
            link_elem = item.find('link')
            pubDate_elem = item.find('pubDate')
            
            if title_elem is not None and 'Amazon WorkSpaces launches Graphics G6' in title_elem.text:
                target_found = True
                print(f"\n✓ TARGET POST FOUND IN RSS FEED!")
                print(f"  Title: {title_elem.text}")
                print(f"  Link: {link_elem.text if link_elem is not None else 'N/A'}")
                print(f"  Pub Date: {pubDate_elem.text if pubDate_elem is not None else 'N/A'}")
                
                # Check if link matches expected URL
                if link_elem is not None and target_url not in link_elem.text:
                    print(f"\n⚠ WARNING: RSS feed URL differs from expected URL!")
                    print(f"  Expected: {target_url}")
                    print(f"  In RSS: {link_elem.text}")
                break
        
        if not target_found:
            print(f"\n✗ TARGET POST NOT FOUND IN RSS FEED!")
            print(f"  This indicates the post may not be published on staging.awseuccontent.com yet")
            print(f"  or the RSS feed has not been updated.")
            
        # Show most recent 5 posts from RSS feed
        print("\nMost recent posts in RSS feed (first 5):")
        print("-" * 80)
        for i, item in enumerate(items[:5], 1):
            title_elem = item.find('title')
            link_elem = item.find('link')
            pubDate_elem = item.find('pubDate')
            
            print(f"{i}. {title_elem.text if title_elem is not None else 'No title'}")
            print(f"   Link: {link_elem.text if link_elem is not None else 'N/A'}")
            print(f"   Date: {pubDate_elem.text if pubDate_elem is not None else 'N/A'}")
            print()
            
    except urllib.error.HTTPError as e:
        print(f"✗ HTTP Error accessing RSS feed: {e.code} {e.reason}")
        print(f"  URL: {staging_rss_url}")
        print(f"  This may indicate the blog category doesn't exist on staging or is not accessible")
    except urllib.error.URLError as e:
        print(f"✗ URL Error accessing RSS feed: {str(e)}")
    except ET.ParseError as e:
        print(f"✗ Error parsing RSS XML: {str(e)}")
    except Exception as e:
        print(f"✗ Unexpected error checking RSS feed: {str(e)}")
        
except Exception as e:
    print(f"✗ Error during staging crawler checks: {str(e)}\n")

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

# Provide diagnostic summary and recommendations
print("\n" + "=" * 80)
print("DIAGNOSTIC SUMMARY & RECOMMENDATIONS")
print("=" * 80)
print("\nIf the blog post is not being detected, check the following:")
print("1. Verify the post is published on staging.awseuccontent.com")
print("2. Confirm the RSS feed includes the post (checked above)")
print("3. Ensure the crawler configuration includes desktop-and-application-streaming")
print("4. Check CloudWatch Logs for the staging crawler Lambda function")
print("5. Verify the crawler schedule is running (check EventBridge rules)")
print("6. Confirm the post date (March 2, 2026) is not filtered out as future-dated")
print("7. Check if there are any errors in the crawler's error logs")
print("\nNext steps:")
print("- If RSS feed doesn't contain the post: Contact content team about staging publication")
print("- If RSS contains post but crawler config missing: Update SSM parameter")
print("- If both are correct: Check crawler Lambda logs for processing errors")
print()
```