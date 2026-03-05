```python
"""
Builder.AWS Selenium Crawler
Fetches real author names and content from Builder.AWS pages using Selenium/Chrome
"""

import json
import os
import time
import boto3
from datetime import datetime, timedelta
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


def get_posts_to_crawl(post_ids=None, debug_mode=False):
    """
    Get posts to crawl from DynamoDB
    
    Args:
        post_ids: List of specific post IDs to crawl (optional)
        debug_mode: If True, print detailed filtering information
        
    Returns:
        list: List of dicts with {'post_id': str, 'url': str, 'title': str, 'published_date': str}
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
                        'published_date': item.get('published_date', '')
                    })
            except Exception as e:
                print(f"  Error fetching post {post_id}: {e}")
        return posts
    else:
        # Scan for all EUC-related posts from Builder.AWS AND AWS Blogs
        # FIXED: Enhanced date filtering and URL pattern matching for March 2026 posts
        try:
            response = table.scan()
            
            posts = []
            filtered_out_count = 0
            
            # Calculate date threshold (posts from last 180 days to catch recent additions)
            date_threshold = datetime.utcnow() - timedelta(days=180)
            
            if debug_mode:
                print(f"\n=== DEBUG: Scanning DynamoDB for posts ===")
                print(f"Date threshold: {date_threshold.isoformat()}")
                print(f"Total items in table: {len(response.get('Items', []))}\n")
            
            for item in response.get('Items', []):
                url = item.get('url', '')
                title = item.get('title', '')
                source = item.get('source', '')
                published_date = item.get('published_date', '')
                post_id = item.get('post_id', '')
                
                if debug_mode:
                    print(f"Analyzing: {post_id}")
                    print(f"  URL: {url}")
                    print(f"  Title: {title}")
                    print(f"  Published: {published_date}")
                
                # Check if from Builder.AWS or AWS Blogs
                is_builder = 'builder.aws.com' in source or 'builder.aws.com' in url
                is_aws_blog = 'aws.amazon.com/blogs' in url
                
                if debug_mode:
                    print(f"  is_builder: {is_builder}, is_aws_blog: {is_aws_blog}")
                
                # Parse published date for filtering
                is_recent = False
                try:
                    if published_date:
                        # Handle both ISO format and date-only format
                        if 'T' in published_date:
                            pub_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                        else:
                            pub_date = datetime.strptime(published_date, '%Y-%m-%d')
                        
                        is_recent = pub_date >= date_threshold
                        
                        if debug_mode:
                            print(f"  Parsed date: {pub_date.isoformat()}, is_recent: {is_recent}")
                except Exception as e:
                    if debug_mode:
                        print(f"  Date parse error: {e}, defaulting to is_recent=True")
                    # If date parsing fails, include the post (don't filter out)
                    is_recent = True
                
                # Create searchable text from URL and title (lowercase for case-insensitive matching)
                text = f"{url} {title}".lower()
                
                # ENHANCED EUC-related keywords for filtering (added Graphics G6, Gr6, G6f)
                euc_keywords = [
                    'euc', 'end-user-computing', 'end user computing',
                    'workspaces', 'appstream', 'workspace',
                    'end user', 'desktop', 'virtual desktop',
                    'vdi', 'daas', 'desktop-and-application-streaming',
                    'application streaming', 'graphics', 'bundle',
                    'g6', 'gr6', 'g6f',  # NEW: Graphics bundle types
                    'graphics.g6', 'graphicspro.g6',  # NEW: Bundle name patterns
                    'graphics g6', 'graphics gr6', 'graphics g6f'  # NEW: Spaced variants
                ]
                
                # Check if EUC-related
                is_euc_related = any(keyword in text for keyword in euc_keywords)
                
                # FIXED: Check for desktop-and-application-streaming category
                # This is a reliable indicator of EUC content from AWS Blogs
                is_das_category = '/desktop-and-application-streaming/' in url
                
                if debug_mode:
                    print(f"  is_euc_related: {is_euc_related}, is_das_category: {is_das_category}")
                
                # ENHANCED INCLUSION LOGIC:
                # 1. From Builder.AWS AND EUC-related AND recent
                # 2. From AWS Blogs desktop-and-application-streaming category (always EUC) AND recent
                # 3. From AWS Blogs AND contains EUC keywords AND recent
                should_include = False
                inclusion_reason = ""
                
                if is_builder and is_euc_related and is_recent:
                    should_include = True
                    inclusion_reason = "Builder.AWS + EUC + Recent"
                elif is_aws_blog and is_das_category and is_recent:
                    should_include = True
                    inclusion_reason = "AWS Blog DAS Category + Recent"
                elif is_aws_blog and is_euc_related and is_recent:
                    should_include = True
                    inclusion_reason = "AWS Blog + EUC Keywords + Recent"
                
                if debug_mode:
                    print(f"  should_include: {should_include} ({inclusion_reason if should_include else 'filtered out'})")
                
                if should_include:
                    posts.append({
                        'post_id': post_id,
                        'url': url,
                        'title': title,
                        'published_date': published_date
                    })
                    if debug_mode:
                        print(f"  ✓ INCLUDED\n")
                else:
                    filtered_out_count += 1
                    if debug_mode:
                        print(f"  ✗ FILTERED OUT\n")
            
            if debug_mode:
                print(f"=== DEBUG SUMMARY ===")
                print(f"Total items scanned: {len(response.get('Items', []))}")
                print(f"Posts included: {len(posts)}")
                print(f"Posts filtered out: {filtered_out_count}")
                print(f"======================\n")
            
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
    - debug (optional): Enable debug mode for detailed filtering information
    
    If post_ids provided: Crawl ONLY those specific posts
    If post_ids not provided: Crawl ALL EUC posts from Builder.AWS and AWS Blogs
    
    Note: This crawler now handles BOTH Builder.AWS and AWS Blog posts to ensure
    complete coverage of EUC content including desktop-and-application-streaming category.
    
    ENHANCED: Improved date filtering and URL pattern matching to catch March 2026 posts
    about Graphics G6, Gr6, and G6f bundles.
    """
    
    # Get parameters from event
    post_ids = event.get('post_ids', []) if event else []
    table_name = event.get('table_name', TABLE_NAME) if event else TABLE_NAME
    debug_mode = event.get('debug', False) if event else False
    
    # Update global table reference if custom table name provided
    global table
    if table_name != TABLE_NAME:
        table = dynamodb.Table(table_name)
    
    print(f"Starting Builder.AWS Selenium Crawler (Enhanced for AWS Blogs + Graphics G6/Gr6/G6f)")
    print(f"DynamoDB Table: {table_name}")
    print(f"Debug Mode: {debug_mode}")
    
    if post_ids:
        print(f"Crawling {len(post_ids)} specific posts: {post_ids}")
    else:
        print("Crawling all EUC posts from Builder.AWS and AWS Blogs (last 180 days)")
    
    # Get posts to crawl
    posts = get_posts_to_crawl(post_ids, debug_mode)
    
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
    
    # Print sample of posts if debug mode
    if debug_mode and posts:
        print("\n=== First 5 posts to be crawled ===")
        for post in posts[:5]:
            print(f"  {post['post_id']}: {post['title']} ({post['published_date']})")
            print(f"    URL: {post['url']}")
        print("===================================\n")
    
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
            title = post.get('title', 'No title')
            
            print(f"[{idx}/{len(posts)}] Processing: {title}")
            print(f"  URL: {url}")
            
            # Extract content
            result = extract_page_content(driver, url)
            
            if result:
                # Update DynamoDB
                if update_post