```python
"""
Builder.AWS Selenium Crawler
Fetches real author names and content from Builder.AWS pages using Selenium/Chrome
"""

import json
import os
import time
import boto3
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# DynamoDB setup
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'aws-blog-posts')
table = dynamodb.Table(TABLE_NAME)

# Lambda client for invoking summary generator
lambda_client = boto3.client('lambda', region_name='us-east-1')


def setup_driver():
    """Set up Chrome driver with headless options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def extract_page_content(driver, url):
    """
    Extract author and content from a Builder.AWS page
    
    Returns:
        dict: {'authors': str, 'content': str} or None if extraction fails
    """
    try:
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Give JavaScript time to render
        time.sleep(2)
        
        # Extract author name
        authors = "AWS Builder Community"  # Default
        try:
            # Try multiple selectors for author
            author_selectors = [
                "//meta[@name='author']",
                "//span[contains(@class, 'author')]",
                "//div[contains(@class, 'author')]",
                "//a[contains(@class, 'author')]"
            ]
            
            for selector in author_selectors:
                try:
                    if selector.startswith("//meta"):
                        author_elem = driver.find_element(By.XPATH, selector)
                        authors = author_elem.get_attribute('content')
                    else:
                        author_elem = driver.find_element(By.XPATH, selector)
                        authors = author_elem.text.strip()
                    
                    if authors and authors != "AWS Builder Community":
                        break
                except NoSuchElementException:
                    continue
        except Exception as e:
            print(f"  Warning: Could not extract author: {e}")
        
        # Extract content
        content = ""
        try:
            # Try multiple selectors for main content
            content_selectors = [
                "//article",
                "//main",
                "//div[contains(@class, 'content')]",
                "//div[contains(@class, 'post')]",
                "//div[contains(@class, 'article')]"
            ]
            
            for selector in content_selectors:
                try:
                    content_elem = driver.find_element(By.XPATH, selector)
                    content = content_elem.text.strip()
                    if content and len(content) > 100:  # Ensure we got substantial content
                        break
                except NoSuchElementException:
                    continue
            
            # If no content found, try getting all text from body
            if not content or len(content) < 100:
                body = driver.find_element(By.TAG_NAME, "body")
                content = body.text.strip()
        except Exception as e:
            print(f"  Warning: Could not extract content: {e}")
            content = "Content extraction failed. Visit the full article on Builder.AWS."
        
        # Limit content to first 3000 characters (matching AWS Blog crawler)
        if len(content) > 3000:
            content = content[:3000]
        
        return {
            'authors': authors,
            'content': content
        }
        
    except TimeoutException:
        print(f"  Error: Page load timeout for {url}")
        return None
    except Exception as e:
        print(f"  Error extracting content from {url}: {e}")
        return None


def update_post_in_dynamodb(post_id, authors, content):
    """Update a post in DynamoDB with real authors and content"""
    try:
        table.update_item(
            Key={'post_id': post_id},
            UpdateExpression='SET authors = :authors, content = :content, last_crawled = :last_crawled',
            ExpressionAttributeValues={
                ':authors': authors,
                ':content': content,
                ':last_crawled': datetime.utcnow().isoformat()
            }
        )
        return True
    except Exception as e:
        print(f"  Error updating DynamoDB for {post_id}: {e}")
        return False


def get_posts_to_crawl(post_ids=None):
    """
    Get posts to crawl from DynamoDB
    
    Args:
        post_ids: List of specific post IDs to crawl (optional)
        
    Returns:
        list: List of dicts with {'post_id': str, 'url': str}
    """
    if post_ids:
        # Fetch specific posts by ID
        posts = []
        for post_id in post_ids:
            try:
                response = table.get_item(Key={'post_id': post_id})
                if 'Item' in response:
                    item = response['Item']
                    posts.append({
                        'post_id': post_id,
                        'url': item.get('url', '')
                    })
            except Exception as e:
                print(f"  Error fetching post {post_id}: {e}")
        return posts
    else:
        # Scan for all EUC-related posts from Builder.AWS AND AWS Blogs
        # Modified to handle both domains for complete EUC coverage
        try:
            response = table.scan()
            
            posts = []
            for item in response.get('Items', []):
                url = item.get('url', '')
                title = item.get('title', '')
                source = item.get('source', '')
                
                # Normalize URL for staging environment detection
                # Fix: Handle staging.awseuccontent.com domain which is used for staging crawler
                normalized_url = url.lower()
                normalized_source = source.lower()
                
                text = f"{normalized_url} {title}".lower()
                
                # Check if from Builder.AWS or AWS Blogs (including staging domain)
                is_builder = (
                    'builder.aws.com' in normalized_source or 
                    'builder.aws.com' in normalized_url or
                    'staging.awseuccontent.com' in normalized_url or
                    'staging.awseuccontent.com' in normalized_source
                )
                is_aws_blog = 'aws.amazon.com/blogs' in normalized_url
                
                # EUC-related keywords for filtering
                # Fix: Enhanced keywords to catch WorkSpaces Graphics bundles
                euc_keywords = [
                    'euc', 'end-user-computing', 'end user computing',
                    'workspaces', 'appstream', 'workspace',
                    'end user', 'desktop', 'virtual desktop',
                    'vdi', 'daas', 'desktop-and-application-streaming',
                    'application streaming', 'graphics', 'bundle',
                    'g6', 'gr6', 'g6f',  # Graphics bundle types
                    'graphics g6', 'workspaces graphics'  # Specific bundle mentions
                ]
                
                # Include if:
                # 1. From Builder.AWS (including staging) AND EUC-related
                # 2. From AWS Blogs desktop-and-application-streaming category (always EUC)
                # 3. From AWS Blogs AND contains EUC keywords
                is_euc_related = any(keyword in text for keyword in euc_keywords)
                is_das_category = '/desktop-and-application-streaming/' in normalized_url
                
                if (is_builder and is_euc_related) or (is_aws_blog and (is_das_category or is_euc_related)):
                    print(f"  Found EUC post: {title[:60]}... (source: {source})")
                    posts.append({
                        'post_id': item.get('post_id'),
                        'url': url
                    })
            
            return posts
        except Exception as e:
            print(f"  Error scanning DynamoDB: {e}")
            return []


def lambda_handler(event, context):
    """
    Lambda handler for Builder.AWS Selenium crawler
    
    Event parameters:
    - post_ids (optional): List of post IDs to crawl (e.g., ['builder-post-1', 'builder-post-2'])
    - table_name (optional): DynamoDB table name
    
    If post_ids provided: Crawl ONLY those specific posts
    If post_ids not provided: Crawl ALL EUC posts from Builder.AWS and AWS Blogs
    
    Note: This crawler now handles BOTH Builder.AWS and AWS Blog posts to ensure
    complete coverage of EUC content including desktop-and-application-streaming category.
    Enhanced to handle staging.awseuccontent.com domain for staging environment testing.
    """
    
    # Get parameters from event
    post_ids = event.get('post_ids', []) if event else []
    table_name = event.get('table_name', TABLE_NAME) if event else TABLE_NAME
    
    # Update global table reference if custom table name provided
    global table
    if table_name != TABLE_NAME:
        table = dynamodb.Table(table_name)
    
    print(f"Starting Builder.AWS Selenium Crawler (Enhanced for AWS Blogs + Staging)")
    print(f"DynamoDB Table: {table_name}")
    
    if post_ids:
        print(f"Crawling {len(post_ids)} specific posts: {post_ids}")
    else:
        print("Crawling all EUC posts from Builder.AWS (including staging.awseuccontent.com) and AWS Blogs")
    
    # Get posts to crawl
    posts = get_posts_to_crawl(post_ids)
    
    if not posts:
        print("No posts to crawl")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'No posts to crawl',
                'posts_processed': 0
            })
        }
    
    print(f"Found {len(posts)} posts to crawl")
    
    # Set up Selenium driver
    driver = None
    posts_processed = 0
    posts_updated = 0
    posts_failed = 0
    
    try:
        driver = setup_driver()
        
        # Process each post
        for idx, post in enumerate(posts, 1):
            post_id = post['post_id']
            url = post['url']
            
            print(f"[{idx}/{len(posts)}] Processing: {url}")
            
            # Extract content
            result = extract_page_content(driver, url)
            
            if result:
                # Update DynamoDB
                if update_post_in_dynamodb(post_id, result['authors'], result['content']):
                    print(f"  ✓ Updated: {result['authors']}")
                    posts_updated += 1
                else:
                    print(f"  ✗ Failed to update DynamoDB")
                    posts_failed += 1
            else:
                print(f"  ✗ Failed to extract content")
                posts_failed += 1
            
            posts_processed += 1
            
            # Small delay between requests
            time.sleep(1)
    
    finally:
        if driver:
            driver.quit()
    
    # Invoke summary generator for the posts we just updated
    if posts_updated > 0:
        print(f"\n{posts_updated} posts updated - invoking summary generator")
        
        try:
            # Determine which alias to use based on environment
            environment = os.environ.get('ENVIRONMENT', 'production')
            function_name = f"aws-blog-summary-generator:{environment}"
            
            # Calculate number of batches needed (5 posts per batch)
            batch_size = 5
            num_batches = (posts_updated + batch_size - 1) // batch_size
            
            for i in range(num_batches):
                lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='Event',  # Async invocation
                    Payload=json.dumps({
                        'batch_size': batch_size,
                        'force': False
                    })
                )
                print(f"  Invoked summary batch {i+1}/{num_batches} ({function_name})")
                time.sleep(2)  # 2-second delay between batches
        except Exception as e:
            print(f"  Warning: Could not invoke summary Lambda: {e}")
    
    # Return results
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Selenium crawler completed',
            'posts_processed': posts_processed,
            'posts_updated': posts_updated,
            'posts_failed': posts_failed,
            'summary_generator_invoked': posts_updated > 0
        })
    }


if __name__ == '__main__':
    # For local testing
    test_event = {
        'post_ids': [],  # Empty = crawl all
        'table_name': 'aws-blog-posts-staging'
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
```