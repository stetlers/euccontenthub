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


def get_posts_to_crawl(post_ids=None, date_filter_days=None):
    """
    Get posts to crawl from DynamoDB
    
    Args:
        post_ids: List of specific post IDs to crawl (optional)
        date_filter_days: Only crawl posts from the last N days (optional)
        
    Returns:
        list: List of dicts with {'post_id': str, 'url': str, 'published_date': str}
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
                        'published_date': item.get('published_date', ''),
                        'title': item.get('title', '')
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
            cutoff_date = None
            
            # Calculate cutoff date if date filter is enabled
            if date_filter_days:
                cutoff_date = datetime.utcnow() - timedelta(days=date_filter_days)
                print(f"  Date filter enabled: including posts from {cutoff_date.strftime('%Y-%m-%d')} onwards")
            
            # FIX: Track all posts and diagnostics for debugging
            all_posts_count = 0
            skipped_by_date = 0
            skipped_by_keywords = 0
            date_parse_errors = []
            included_by_reason = {
                'builder_euc': 0,
                'aws_blog_das_category': 0,
                'aws_blog_euc_keywords': 0,
                'aws_blog_euc_in_path': 0
            }
            
            # FIX: Track the specific March 2, 2026 post for debugging
            target_post_found = False
            target_post_details = None
            
            for item in response.get('Items', []):
                all_posts_count += 1
                url = item.get('url', '')
                title = item.get('title', '')
                source = item.get('source', '')
                published_date = item.get('published_date', '')
                post_id = item.get('post_id', '')
                text = f"{url} {title}".lower()
                
                # FIX: Track if this is the target post we're debugging
                is_target_post = (
                    'march 2' in published_date.lower() or 
                    '2026-03-02' in published_date or
                    ('workspaces' in title.lower() and 'graphics' in title.lower() and 'g6' in title.lower())
                )
                
                if is_target_post:
                    target_post_found = True
                    target_post_details = {
                        'post_id': post_id,
                        'url': url,
                        'title': title,
                        'published_date': published_date,
                        'source': source
                    }
                    print(f"\n>>> FOUND TARGET POST: {title}")
                    print(f"    Post ID: {post_id}")
                    print(f"    URL: {url}")
                    print(f"    Published: {published_date}")
                    print(f"    Source: {source}")
                
                # FIX: Enhanced date filtering with better error handling and diagnostics
                if cutoff_date and published_date:
                    try:
                        # Parse published_date - handle both YYYY-MM-DD and ISO format
                        if 'T' in published_date:
                            # ISO format with timezone
                            post_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                        else:
                            # Simple date format
                            post_date = datetime.strptime(published_date, '%Y-%m-%d')
                        
                        # FIX: Make cutoff_date timezone-aware if post_date is timezone-aware
                        if post_date.tzinfo is not None and cutoff_date.tzinfo is None:
                            from datetime import timezone
                            cutoff_date = cutoff_date.replace(tzinfo=timezone.utc)
                        
                        if post_date < cutoff_date:
                            if is_target_post:
                                print(f"    >>> WARNING: Target post skipped by date filter!")
                                print(f"        Post date: {post_date}")
                                print(f"        Cutoff date: {cutoff_date}")
                            skipped_by_date += 1
                            continue  # Skip posts older than cutoff
                        elif is_target_post:
                            print(f"    >>> Target post PASSED date filter")
                            print(f"        Post date: {post_date}")
                            print(f"        Cutoff date: {cutoff_date}")
                    except (ValueError, TypeError) as e:
                        # FIX: Track date parsing errors for diagnostics
                        date_parse_errors.append({
                            'post_id': post_id,
                            'published_date': published_date,
                            'error': str(e)
                        })
                        print(f"  Warning: Could not parse date for {post_id}: {published_date} - {e}")
                        if is_target_post:
                            print(f"    >>> WARNING: Target post had date parsing error!")
                        # Include the post to be safe when date parsing fails
                
                # Check if from Builder.AWS or AWS Blogs
                is_builder = 'builder.aws.com' in source or 'builder.aws.com' in url
                is_aws_blog = 'aws.amazon.com/blogs' in url
                
                # FIX: Check if this is staging environment
                is_staging = 'staging' in url or 'staging' in source
                
                if is_target_post:
                    print(f"    >>> Source checks:")
                    print(f"        is_builder: {is_builder}")
                    print(f"        is_aws_blog: {is_aws_blog}")
                    print(f"        is_staging: {is_staging}")
                
                # FIX: Expanded and refined EUC-related keywords for better detection
                # Added more variations including specific graphics bundle identifiers
                euc_keywords = [
                    'euc', 'end-user-computing', 'end user computing',
                    'workspaces', 'appstream', 'workspace',
                    'end user', 'desktop', 'virtual desktop',
                    'vdi', 'daas', 'desktop-and-application-streaming',
                    'application streaming', 'graphics', 'bundle',
                    'workspaces graphics', 'graphics bundle', 'g6 bundle',
                    'g6.xlarge', 'g6.2xlarge', 'graphics workspaces',
                    'g6 bundles', 'graphics.g6', 'gr6', 'g6f',  # FIX: Added gr6 and g6f for March 2 post
                    'workspaces web', 'workspace web',
                    'amazon workspaces', 'aws workspaces',
                    'launches graphics'  # FIX: Added to catch launch announcements
                ]
                
                # FIX: Enhanced detection logic with URL path checking
                # Include if:
                # 1. From Builder.AWS AND EUC-related
                # 2. From AWS Blogs desktop-and-application-streaming category (always EUC)
                # 3. From AWS Blogs AND contains EUC keywords
                # 4. FIX: Check URL path components for better detection
                is_euc_related = any(keyword in text for keyword in euc_keywords)
                is_das_category = '/desktop-and-application-streaming/' in url
                
                if is_target_post:
                    print(f"    >>> Keyword checks:")
                    print(f"        is_euc_related: {is_euc_related}")
                    print(f"        is_das_category: {is_das_category}")
                    print(f"        text sample: {text[:200]}")
                
                # FIX: Additional URL path checking for posts that might be missed
                url_path_keywords = ['workspaces', 'appstream', 'euc', 'end-user']
                has_euc_in_path = any(keyword in url.lower() for keyword in url_path_keywords)
                
                if is_target_post:
                    print(f"        has_euc_in_path: {has_euc_in_path}")
                
                # FIX: Relaxed filtering - include if ANY of these conditions are true
                should_include = False
                inclusion_reason = None
                
                if is_builder and is_euc_related:
                    should_include = True
                    inclusion_reason = 'builder_euc'
                    included_by_reason['builder_euc'] += 1
                elif is_aws_blog and is_das_category:
                    should_include = True
                    inclusion_reason = 'aws_blog_das_category'
                    included_by_reason['aws_blog_das_category'] += 1
                elif is_aws_blog and is_euc_related:
                    should_include = True
                    inclusion_reason = 'aws_blog_euc_keywords'
                    included_by_reason['aws_blog_euc_keywords'] += 1
                elif is_aws_blog and has_euc_in_path:
                    should_include = True
                    inclusion_reason = 'aws_blog_euc_in_path'
                    included_by_reason['aws_blog_euc_in_path'] += 1
                
                if is_target_post:
                    print(f"    >>> Final decision:")
                    print(f"        should_include: {should_include}")
                    print(f"        inclusion_reason: {inclusion_reason}")
                
                if should_include:
                    posts.append({
                        'post_id': post_id,
                        'url': url,
                        'published_date': published_date,
                        'title': title,
                        'inclusion_reason': inclusion_reason
                    })
                    if is_target_post:
                        print(f"    >>> Target post INCLUDED in results!\