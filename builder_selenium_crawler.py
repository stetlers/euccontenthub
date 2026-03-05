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
        list: List of dicts with {'post_id': str, 'url': str, 'title': str, 'date': str}
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
                        'url': item.get('url', ''),
                        'title': item.get('title', ''),
                        'date': item.get('date', '')
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
                date_str = item.get('date', '')
                text = f"{url} {title}".lower()
                
                # Debug logging for date filtering
                # Commenting this out for production, but useful for debugging
                # print(f"DEBUG: Checking post: {title[:50]}... | Date: {date_str} | URL: {url}")
                
                # Check if from Builder.AWS or AWS Blogs
                is_builder = 'builder.aws.com' in source or 'builder.aws.com' in url
                is_aws_blog = 'aws.amazon.com/blogs' in url
                
                # EUC-related keywords for filtering
                # FIXED: Added more variations including 'g6' and 'graphics' to catch posts like
                # "Amazon WorkSpaces Graphics G6 bundles"
                euc_keywords = [
                    'euc', 'end-user-computing', 'end user computing',
                    'workspaces', 'appstream', 'workspace',
                    'end user', 'desktop', 'virtual desktop',
                    'vdi', 'daas', 'desktop-and-application-streaming',
                    'application streaming', 'graphics', 'bundle',
                    'g4dn', 'g5', 'g6',  # Graphics bundle types
                    'graphicspro', 'graphics.g4dn', 'graphics pro'
                ]
                
                # Include if:
                # 1. From Builder.AWS AND EUC-related
                # 2. From AWS Blogs desktop-and-application-streaming category (always EUC)
                # 3. From AWS Blogs AND contains EUC keywords
                is_euc_related = any(keyword in text for keyword in euc_keywords)
                is_das_category = '/desktop-and-application-streaming/' in url
                
                # FIXED: Production behavior comparison - ensure we're not over-filtering
                # Production includes posts from desktop-and-application-streaming without additional keyword checks
                should_include = False
                reason = ""
                
                if is_builder and is_euc_related:
                    should_include = True
                    reason = "Builder.AWS + EUC keywords"
                elif is_aws_blog and is_das_category:
                    should_include = True
                    reason = "AWS Blog + DAS category"
                elif is_aws_blog and is_euc_related:
                    should_include = True
                    reason = "AWS Blog + EUC keywords"
                
                if should_include:
                    # Debug logging for included posts
                    # print(f"DEBUG: INCLUDED - {title[:50]}... | Reason: {reason}")
                    posts.append({
                        'post_id': item.get('post_id'),
                        'url': url,
                        'title': title,
                        'date': date_str
                    })
                # else:
                    # Debug logging for excluded posts
                    # print(f"DEBUG: EXCLUDED - {title[:50]}... | Builder: {is_builder} | AWS Blog: {is_aws_blog} | EUC: {is_euc_related} | DAS: {is_das_category}")
            
            # FIXED: Sort posts by date (newest first) to help with debugging
            # This ensures recent posts like the March 2, 2026 post are prioritized
            posts_with_dates = [p for p in posts if p.get('date')]
            posts_without_dates = [p for p in posts if not p.get('date')]
            
            # Sort posts with dates by date descending (newest first)
            posts_with_dates.sort(key=lambda x: x['date'], reverse=True)
            
            # Combine: dated posts first, then undated posts
            sorted_posts = posts_with_dates + posts_without_dates
            
            print(f"DEBUG: Total posts found: {len(sorted_posts)}")
            if sorted_posts:
                print(f"DEBUG: Newest post date: {sorted_posts[0].get('date', 'N/A')}")
                print(f"DEBUG: Oldest post date: {posts_with_dates[-1].get('date', 'N/A') if posts_with_dates else 'N/A'}")
                # Print first 5 posts for verification
                print("DEBUG: First 5 posts to crawl:")
                for i, post in enumerate(sorted_posts[:5], 1):
                    print(f"  {i}. {post.get('date', 'N/A')} - {post.get('title', '')[:60]}...")
            
            return sorted_posts
        except Exception as e:
            print(f"  Error scanning DynamoDB: {e}")
            return []


def lambda_handler(event, context):
    """
    Lambda handler for Builder.AWS Selenium crawler
    
    Event parameters:
    - post_ids (optional): List of post IDs to crawl (e.g., ['builder-post-1', 'builder-post-2'])
    - table_name (optional): DynamoDB table name
    - debug (optional): Enable debug logging (default: False)
    
    If post_ids provided: Crawl ONLY those specific posts
    If post_ids not provided: Crawl ALL EUC posts from Builder.AWS and AWS Blogs
    
    Note: This crawler now handles BOTH Builder.AWS and AWS Blog posts to ensure
    complete coverage of EUC content including desktop-and-application-streaming category.
    
    FIXED: Enhanced keyword matching to include graphics bundle types (G4DN, G5, G6)
    FIXED: Improved date sorting to prioritize recent posts for debugging
    FIXED: Added debug logging to track post filtering and detection
    """
    
    # Get parameters from event
    post_ids = event.get('post_ids', []) if event else []
    table_name = event.get('table_name', TABLE_NAME) if event else TABLE_NAME
    debug_mode = event.get('debug', False) if event else False
    
    # Update global table reference if custom table name provided
    global table
    if table_name != TABLE_NAME:
        table = dynamodb.Table(table_name)
    
    print(f"Starting Builder.AWS Selenium Crawler (Enhanced for AWS Blogs)")
    print(f"DynamoDB Table: {table_name}")
    print(f"Debug Mode: {debug_mode}")
    
    if post_ids:
        print(f"Crawling {len(post_ids)} specific posts: {post_ids}")
    else:
        print("Crawling all EUC posts from Builder.AWS and AWS Blogs")
    
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
    
    # FIXED: In debug mode, show which specific posts we're about to crawl
    if debug_mode and posts:
        print("\nDEBUG: Posts selected for crawling:")
        for idx, post in enumerate(posts[:10], 1):  # Show first 10
            print(f"  {idx}. [{post.get('date', 'N/A')}] {post.get('title', '')[:70]}...")
        if len(posts) > 10:
            print(f"  ... and {len(posts) - 10} more posts")
    
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
            title = post.get('title', 'Unknown')
            date = post.get('date', 'N/A')
            
            print(f"[{idx}/{len(posts)}] Processing [{date}]: {title[:60]}...")
            print(f"  URL: {url}")
            
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
            
            # Calculate number of batches needed (5 posts per