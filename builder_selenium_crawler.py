```python
"""
Builder.AWS Selenium Crawler
Fetches real author names and content from Builder.AWS pages using Selenium/Chrome
"""

import json
import os
import time
import boto3
from datetime import datetime, timedelta, timezone
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

# Staging table setup for diagnostic purposes
STAGING_TABLE_NAME = os.environ.get('STAGING_TABLE_NAME', 'aws-blog-posts-staging')
staging_table = dynamodb.Table(STAGING_TABLE_NAME)

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


def check_staging_table_for_post(target_date='2026-03-02', keywords=None):
    """
    Check staging table for posts matching criteria
    
    Args:
        target_date: Date string to search for (YYYY-MM-DD format)
        keywords: List of keywords to search for in title/content
        
    Returns:
        list: List of matching posts from staging table
    """
    if keywords is None:
        keywords = ['workspaces', 'graphics', 'g6', 'gr6', 'g6f', 'bundle']
    
    try:
        print(f"\n=== CHECKING STAGING TABLE: {STAGING_TABLE_NAME} ===")
        response = staging_table.scan()
        
        matching_posts = []
        for item in response.get('Items', []):
            url = item.get('url', '')
            title = item.get('title', '')
            published_date = item.get('published_date', '')
            post_id = item.get('post_id', '')
            text = f"{url} {title}".lower()
            
            # Check if matches our target criteria
            date_match = target_date in published_date
            keyword_match = any(keyword in text for keyword in keywords)
            
            if date_match or keyword_match:
                matching_posts.append({
                    'post_id': post_id,
                    'title': title,
                    'url': url,
                    'published_date': published_date,
                    'date_match': date_match,
                    'keyword_match': keyword_match,
                    'matched_keywords': [kw for kw in keywords if kw in text]
                })
        
        print(f"  Found {len(matching_posts)} matching posts in staging table")
        for post in matching_posts:
            print(f"\n  Post: {post['title']}")
            print(f"    ID: {post['post_id']}")
            print(f"    Date: {post['published_date']}")
            print(f"    URL: {post['url']}")
            print(f"    Date Match: {post['date_match']}")
            print(f"    Keyword Match: {post['keyword_match']}")
            print(f"    Matched Keywords: {post['matched_keywords']}")
        
        return matching_posts
        
    except Exception as e:
        print(f"  Error checking staging table: {e}")
        return []


def get_posts_to_crawl(post_ids=None, date_filter_days=None, enable_diagnostics=True):
    """
    Get posts to crawl from DynamoDB with enhanced diagnostics
    
    Args:
        post_ids: List of specific post IDs to crawl (optional)
        date_filter_days: Only crawl posts from the last N days (optional)
        enable_diagnostics: Enable detailed diagnostic logging (default: True)
        
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
        try:
            response = table.scan()
            
            posts = []
            cutoff_date = None
            
            # Calculate cutoff date if date filter is enabled
            if date_filter_days:
                cutoff_date = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=date_filter_days)
                print(f"  Date filter enabled: including posts from {cutoff_date.strftime('%Y-%m-%d')} onwards")
            
            # DIAGNOSTIC: Track all posts and diagnostics for debugging
            all_posts_count = 0
            skipped_by_date = 0
            skipped_by_keywords = 0
            date_parse_errors = []
            included_by_reason = {
                'builder_euc': 0,
                'aws_blog_das_category': 0,
                'aws_blog_euc_keywords': 0,
                'aws_blog_euc_in_path': 0,
                'staging_euc': 0
            }
            
            # DIAGNOSTIC: Track the specific March 2, 2026 post for debugging
            target_post_found = False
            target_post_details = None
            
            # Enhanced EUC-related keywords including all WorkSpaces Graphics bundle variations
            euc_keywords = [
                'euc', 'end-user-computing', 'end user computing',
                'workspaces', 'appstream', 'workspace',
                'end user', 'desktop', 'virtual desktop',
                'vdi', 'daas', 'desktop-and-application-streaming',
                'application streaming', 'graphics', 'bundle',
                'workspaces graphics', 'graphics bundle', 'g6 bundle',
                'g6.xlarge', 'g6.2xlarge', 'graphics workspaces',
                'g6 bundles', 'graphics.g6', 'gr6', 'g6f',
                'graphics g6', 'gr6 bundle', 'g6f bundle',
                'workspaces web', 'workspace web',
                'amazon workspaces', 'aws workspaces',
                'launches graphics', 'launch graphics',
                'workspaces launch', 'graphics launch',
                'g6,', 'gr6,', 'g6f,',
                ' g6 ', ' gr6 ', ' g6f ',
                'g6, gr6', 'gr6, and g6f', 'g6, gr6, and g6f',
                'workspaces graphics g6', 'amazon workspaces graphics',
                'workspaces family', 'bundles for', 'graphics bundles'
            ]
            
            for item in response.get('Items', []):
                all_posts_count += 1
                url = item.get('url', '')
                title = item.get('title', '')
                source = item.get('source', '')
                published_date = item.get('published_date', '')
                post_id = item.get('post_id', '')
                text = f"{url} {title}".lower()
                
                # Enhanced detection for the March 2, 2026 WorkSpaces Graphics post
                is_target_post = (
                    ('2026-03-02' in published_date) or
                    ('2026-03-2' in published_date) or
                    ('march 2, 2026' in published_date.lower()) or
                    ('03/02/2026' in published_date) or
                    (('workspaces' in title.lower() or 'workspace' in title.lower()) and 
                     'graphics' in title.lower() and 
                     ('g6' in title.lower() or 'gr6' in title.lower() or 'g6f' in title.lower())) or
                    ('amazon workspaces graphics g6' in text) or
                    ('workspaces graphics g6, gr6, and g6f bundles' in text) or
                    ('workspaces graphics' in text and ('g6' in text or 'gr6' in text or 'g6f' in text))
                )
                
                if is_target_post and enable_diagnostics:
                    target_post_found = True
                    target_post_details = {
                        'post_id': post_id,
                        'url': url,
                        'title': title,
                        'published_date': published_date,
                        'source': source
                    }
                    print(f"\n{'='*80}")
                    print(f">>> DIAGNOSTIC: FOUND TARGET POST (March 2, 2026 WorkSpaces Graphics)")
                    print(f"{'='*80}")
                    print(f"    Post ID: {post_id}")
                    print(f"    Title: {title}")
                    print(f"    URL: {url}")
                    print(f"    Published: {published_date}")
                    print(f"    Source: {source}")
                
                # Enhanced date filtering with better error handling and timezone awareness
                if cutoff_date and published_date:
                    try:
                        post_date = None
                        
                        if 'T' in published_date:
                            # ISO format with potential timezone
                            try:
                                post_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                            except ValueError:
                                post_date = datetime.fromisoformat(published_date.split('+')[0].split('Z')[0])
                                post_date = post_date.replace(tzinfo=timezone.utc)
                        else:
                            # Simple date format YYYY-MM-DD
                            post_date = datetime.strptime(published_date, '%Y-%m-%d')
                            post_date = post_date.replace(tzinfo=timezone.utc)
                        
                        # Ensure cutoff_date is timezone-aware for comparison
                        if cutoff_date.tzinfo is None:
                            cutoff_date = cutoff_date.replace(tzinfo=timezone.utc)
                        
                        # Include future dates (like 2026) - only filter out dates BEFORE cutoff
                        if post_date < cutoff_date:
                            if is_target_post and enable_diagnostics:
                                print(f"    >>> DIAGNOSTIC: Target post FILTERED OUT by date")
                                print(f"        Post date: {post_date}")
                                print(f"        Cutoff date: {cutoff_date}")
                                print(f"        Decision: SKIPPED")
                            skipped_by_date += 1
                            continue
                        elif is_target_post and enable_diagnostics:
                            print(f"    >>> DIAGNOSTIC: Target post PASSED date filter")
                            print(f"        Post date: {post_date}")
                            print(f"        Cutoff date: {cut