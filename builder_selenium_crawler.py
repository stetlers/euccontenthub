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

# CloudWatch Logs setup for detailed crawler diagnostics
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
        logger.info(f"Attempting to load URL: {url}")
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        logger.info(f"Page loaded successfully: {url}")
        
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
                        logger.info(f"Found author using selector {selector}: {authors}")
                        break
                except NoSuchElementException:
                    continue
        except Exception as e:
            logger.warning(f"Could not extract author from {url}: {e}")
        
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
                        logger.info(f"Found content using selector {selector}: {len(content)} chars")
                        break
                except NoSuchElementException:
                    continue
            
            # If no content found, try getting all text from body
            if not content or len(content) < 100:
                body = driver.find_element(By.TAG_NAME, "body")
                content = body.text.strip()
                logger.info(f"Using body text as fallback: {len(content)} chars")
        except Exception as e:
            logger.warning(f"Could not extract content from {url}: {e}")
            content = "Content extraction failed. Visit the full article on Builder.AWS."
        
        # Limit content to first 3000 characters (matching AWS Blog crawler)
        if len(content) > 3000:
            content = content[:3000]
            logger.info(f"Content truncated to 3000 chars")
        
        return {
            'authors': authors,
            'content': content
        }
        
    except TimeoutException:
        logger.error(f"Page load timeout for {url}")
        return None
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {e}", exc_info=True)
        return None


def update_post_in_dynamodb(post_id, authors, content):
    """Update a post in DynamoDB with real authors and content"""
    try:
        logger.info(f"Updating DynamoDB for post_id: {post_id}")
        table.update_item(
            Key={'post_id': post_id},
            UpdateExpression='SET authors = :authors, content = :content, last_crawled = :last_crawled',
            ExpressionAttributeValues={
                ':authors': authors,
                ':content': content,
                ':last_crawled': datetime.utcnow().isoformat()
            }
        )
        logger.info(f"Successfully updated DynamoDB for post_id: {post_id}")
        return True
    except Exception as e:
        logger.error(f"Error updating DynamoDB for {post_id}: {e}", exc_info=True)
        return False


def verify_dynamodb_write(post_id):
    """
    Verify that a post was correctly written to DynamoDB
    
    Args:
        post_id: The post ID to verify
        
    Returns:
        dict: The item from DynamoDB or None if not found
    """
    try:
        logger.info(f"Verifying DynamoDB write for post_id: {post_id}")
        response = table.get_item(Key={'post_id': post_id})
        if 'Item' in response:
            item = response['Item']
            logger.info(f"Verified post {post_id} in DynamoDB - authors: {item.get('authors', 'N/A')}, "
                       f"content_length: {len(item.get('content', ''))}, "
                       f"last_crawled: {item.get('last_crawled', 'N/A')}")
            return item
        else:
            logger.warning(f"Post {post_id} not found in DynamoDB after write attempt")
            return None
    except Exception as e:
        logger.error(f"Error verifying DynamoDB write for {post_id}: {e}", exc_info=True)
        return None


def get_posts_to_crawl(post_ids=None, date_filter=None):
    """
    Get posts to crawl from DynamoDB
    
    Args:
        post_ids: List of specific post IDs to crawl (optional)
        date_filter: Date string (YYYY-MM-DD) to filter posts from that date onward (optional)
        
    Returns:
        list: List of dicts with {'post_id': str, 'url': str, 'title': str, 'published_date': str}
    """
    if post_ids:
        # Fetch specific posts by ID
        logger.info(f"Fetching specific posts: {post_ids}")
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
                    logger.info(f"Found post: {post_id} - {item.get('title', 'N/A')}")
                else:
                    logger.warning(f"Post {post_id} not found in DynamoDB")
            except Exception as e:
                logger.error(f"Error fetching post {post_id}: {e}", exc_info=True)
        return posts
    else:
        # Scan for all EUC-related posts from Builder.AWS AND AWS Blogs
        logger.info("Scanning DynamoDB for all EUC-related posts")
        try:
            response = table.scan()
            logger.info(f"DynamoDB scan returned {len(response.get('Items', []))} total items")
            
            posts = []
            for item in response.get('Items', []):
                url = item.get('url', '')
                title = item.get('title', '')
                source = item.get('source', '')
                published_date = item.get('published_date', '')
                post_id = item.get('post_id')
                text = f"{url} {title}".lower()
                
                # Apply date filter if specified
                if date_filter and published_date:
                    try:
                        # Parse dates for comparison (YYYY-MM-DD format)
                        post_date = published_date.split('T')[0] if 'T' in published_date else published_date
                        if post_date < date_filter:
                            continue
                    except Exception as e:
                        logger.warning(f"Could not parse date for post {post_id}: {e}")
                
                # Check if from Builder.AWS or AWS Blogs
                is_builder = 'builder.aws.com' in source or 'builder.aws.com' in url
                is_aws_blog = 'aws.amazon.com/blogs' in url
                
                # EUC-related keywords for filtering - EXPANDED for better detection
                euc_keywords = [
                    'euc', 'end-user-computing', 'end user computing',
                    'workspaces', 'appstream', 'workspace',
                    'end user', 'desktop', 'virtual desktop',
                    'vdi', 'daas', 'desktop-and-application-streaming',
                    'application streaming', 'graphics', 'bundle',
                    'graphics bundle', 'graphics.g4dn', 'g4dn', 'gpu',
                    'workspaces graphics', 'amazon workspaces'
                ]
                
                # Include if:
                # 1. From Builder.AWS AND EUC-related
                # 2. From AWS Blogs desktop-and-application-streaming category (always EUC)
                # 3. From AWS Blogs AND contains EUC keywords
                is_euc_related = any(keyword in text for keyword in euc_keywords)
                is_das_category = '/desktop-and-application-streaming/' in url
                
                if (is_builder and is_euc_related) or (is_aws_blog and (is_das_category or is_euc_related)):
                    posts.append({
                        'post_id': post_id,
                        'url': url,
                        'title': title,
                        'published_date': published_date
                    })
                    logger.info(f"Matched post: {post_id} - {title} ({published_date})")
                    logger.info(f"  Source: {source}, URL: {url}")
                    logger.info(f"  Match reason: is_builder={is_builder}, is_euc={is_euc_related}, "
                               f"is_das_category={is_das_category}")
            
            logger.info(f"Found {len(posts)} EUC-related posts to crawl")
            return posts
        except Exception as e:
            logger.error(f"Error scanning DynamoDB: {e}", exc_info=True)
            return []


def diagnose_missing_post(url_pattern=None, title_pattern=None, date_range=None):
    """
    Diagnostic function to investigate why a specific post might not be detected
    
    Args:
        url_pattern: Partial URL to search for (e.g., 'amazon-workspaces-graphics')
        title_pattern: Partial title to search for (e.g., 'Graphics bundles')
        date_range: Tuple of (start_date, end_date) in YYYY-MM-DD format
        
    Returns:
        list: Matching posts with diagnostic information
    """
    logger.info("=" * 80)
    logger.info("DIAGNOSTIC MODE: Searching for missing post")
    logger.info(f"URL pattern: {url_pattern}")
    logger.info(f"Title pattern: {title_pattern}")
    logger.info(f"Date range: {date_range}")
    logger.info("=" * 80)
    
    try:
        response = table.scan()
        all_items = response.get('Items', [])
        logger.info(f"Total items in DynamoDB: {len(all_items)}")
        
        matching_posts = []
        for item in all_items:
            url = item.get('url', '')
            title = item.get('title', '')
            published_date = item.get('published_date', '')
            source = item.get('source', '')
            post_id = item.get('post_id')
            
            # Check URL pattern
            url_match = url_pattern and url_pattern.lower() in url.lower()
            
            # Check title pattern
            title_match = title_pattern and title_pattern.lower() in title.lower()
            
            # Check date range
            date_match = True
            if date_range and published_date:
                try:
                    post_date = published_date.split('T')[0] if 'T' in published_date else published_date
                    date_match = date_range[0] <= post_date <= date_range[1]
                except:
                    date_match = False
            
            if url_match or title_match or (date_range and date_match):
                matching_posts.append(item)
                logger.info("=" * 80)
                logger.info(f"FOUND MATCHING POST:")
                logger.info(f"  Post ID: {post_id}")
                logger.info(f"  Title: {title}")
                logger.info(f"  URL: {url}")
                logger.info(f"  Source: {source}")
                logger.info(f"  Published: {published_date}")
                logger.info(f"  URL Match: {url_match}")
                logger.info(f"  Title Match: {title_match}")
                logger.info(f"  Date Match: {date_match}")
                
                # Check filtering logic
                text = f"{url} {title}".lower()
                is_builder = 'builder.aws.com' in source or 'builder.aws.com' in url
                is_aws_blog = 'aws.amazon.com/blogs' in url
                is_das_category = '/desktop-and-application-streaming/' in url
                
                euc_keywords = [
                    'euc', 'end-user-computing', 'end user computing',
                    'workspaces', 'appstream', 'workspace',
                    'end user', 'desktop', 'virtual desktop',
                    'vdi', 'daas', 'desktop-and-application-streaming',
                    'application streaming', 'graphics', 'bundle',
                    'graphics bundle', 'graphics.g4dn', 'g4dn', 'gpu',
                    'workspaces graphics', 'amazon workspaces'
                ]
                
                matched_