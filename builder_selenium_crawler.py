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
            
            for item in response.get('Items', []):
                all_posts_count += 1
                url = item.get('url', '')
                title = item.get('title', '')
                source = item.get('source', '')
                published_date = item.get('published_date', '')
                post_id = item.get('post_id', '')
                text = f"{url} {title}".lower()
                
                # FIX: Enhanced date filtering with better error handling and diagnostics
                if cutoff_date and published_date:
                    try:
                        # Parse published_date - handle both YYYY-MM-DD and ISO format
                        if 'T' in published_date:
                            post_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                        else:
                            post_date = datetime.strptime(published_date, '%Y-%m-%d')
                        
                        if post_date < cutoff_date:
                            skipped_by_date += 1
                            continue  # Skip posts older than cutoff
                    except (ValueError, TypeError) as e:
                        # FIX: Track date parsing errors for diagnostics
                        date_parse_errors.append({
                            'post_id': post_id,
                            'published_date': published_date,
                            'error': str(e)
                        })
                        print(f"  Warning: Could not parse date for {post_id}: {published_date} - {e}")
                        # Include the post to be safe when date parsing fails
                
                # Check if from Builder.AWS or AWS Blogs
                is_builder = 'builder.aws.com' in source or 'builder.aws.com' in url
                is_aws_blog = 'aws.amazon.com/blogs' in url
                
                # FIX: Expanded and refined EUC-related keywords for better detection
                # Added more variations and corrected case-sensitivity issues
                euc_keywords = [
                    'euc', 'end-user-computing', 'end user computing',
                    'workspaces', 'appstream', 'workspace',
                    'end user', 'desktop', 'virtual desktop',
                    'vdi', 'daas', 'desktop-and-application-streaming',
                    'application streaming', 'graphics', 'bundle',
                    'workspaces graphics', 'graphics bundle', 'g6 bundle',
                    'g6.xlarge', 'g6.2xlarge', 'graphics workspaces',
                    'g6 bundles', 'graphics.g6',  # FIX: Added for March 2 post detection
                    'workspaces web', 'workspace web',  # Additional coverage
                    'amazon workspaces', 'aws workspaces'  # Full names
                ]
                
                # FIX: Enhanced detection logic with URL path checking
                # Include if:
                # 1. From Builder.AWS AND EUC-related
                # 2. From AWS Blogs desktop-and-application-streaming category (always EUC)
                # 3. From AWS Blogs AND contains EUC keywords
                # 4. FIX: Check URL path components for better detection
                is_euc_related = any(keyword in text for keyword in euc_keywords)
                is_das_category = '/desktop-and-application-streaming/' in url
                
                # FIX: Additional URL path checking for posts that might be missed
                url_path_keywords = ['workspaces', 'appstream', 'euc', 'end-user']
                has_euc_in_path = any(keyword in url.lower() for keyword in url_path_keywords)
                
                # FIX: Relaxed filtering - include if ANY of these conditions are true
                should_include = False
                if is_builder and is_euc_related:
                    should_include = True
                elif is_aws_blog and is_das_category:
                    should_include = True
                elif is_aws_blog and is_euc_related:
                    should_include = True
                elif is_aws_blog and has_euc_in_path:
                    should_include = True  # FIX: Include AWS blog posts with EUC in URL path
                
                if should_include:
                    posts.append({
                        'post_id': post_id,
                        'url': url,
                        'published_date': published_date,
                        'title': title
                    })
                else:
                    skipped_by_keywords += 1
            
            # FIX: Enhanced diagnostic logging
            print(f"\n=== CRAWLING DIAGNOSTICS ===")
            print(f"Total posts in DynamoDB: {all_posts_count}")
            print(f"Posts skipped by date filter: {skipped_by_date}")
            print(f"Posts skipped by keyword filter: {skipped_by_keywords}")
            print(f"Posts selected for crawling: {len(posts)}")
            
            if date_parse_errors:
                print(f"\nDate parsing errors ({len(date_parse_errors)}):")
                for error in date_parse_errors[:5]:  # Show first 5
                    print(f"  - {error['post_id']}: {error['published_date']} ({error['error']})")
                if len(date_parse_errors) > 5:
                    print(f"  ... and {len(date_parse_errors) - 5} more")
            
            # FIX: Group posts by date and show distribution
            if posts:
                print(f"\n=== POSTS BY DATE ===")
                date_counts = {}
                for post in posts:
                    date = post.get('published_date', 'unknown')
                    # Extract just the date part if ISO format
                    if 'T' in date:
                        date = date.split('T')[0]
                    date_counts[date] = date_counts.get(date, 0) + 1
                
                # Show last 10 dates
                for date in sorted(date_counts.keys(), reverse=True)[:10]:
                    print(f"  {date}: {date_counts[date]} post(s)")
                    # FIX: Show titles for recent posts (within last 7 days)
                    try:
                        post_date = datetime.strptime(date, '%Y-%m-%d')
                        days_ago = (datetime.utcnow() - post_date).days
                        if days_ago <= 7:
                            for post in posts:
                                post_published = post.get('published_date', '')
                                if 'T' in post_published:
                                    post_published = post_published.split('T')[0]
                                if post_published == date:
                                    print(f"    → {post['title'][:70]}...")
                    except ValueError:
                        pass
                
                if len(date_counts) > 10:
                    print(f"  ... and {len(date_counts) - 10} more dates")
            
            print(f"=== END DIAGNOSTICS ===\n")
            
            return posts
        except Exception as e:
            print(f"  Error scanning DynamoDB: {e}")
            import traceback
            print(f"  Traceback: {traceback.format_exc()}")
            return []


def lambda_handler(event, context):
    """
    Lambda handler for Builder.AWS Selenium crawler
    
    Event parameters:
    - post_ids (optional): List of post IDs to crawl (e.g., ['builder-post-1', 'builder-post-2'])
    - table_name (optional): DynamoDB table name
    - date_filter_days (optional): Only crawl posts from last N days (e.g., 90 for last 90 days)
    
    If post_ids provided: Crawl ONLY those specific posts
    If post_ids not provided: Crawl ALL EUC posts from Builder.AWS and AWS Blogs
    
    Date filtering: Use date_filter_days to limit crawling to recent posts only.
    This helps with:
    - Reducing unnecessary crawling of old posts
    - Ensuring new posts are detected and crawled
    - Diagnosing date-related filtering issues
    
    Note: This crawler now handles BOTH Builder.AWS and AWS Blog posts to ensure
    complete coverage of EUC content including desktop-and-application-streaming category.
    
    FIX: Enhanced diagnostic logging and date filtering to address issue with 
    March 2, 2026 WorkSpaces Graphics G6 bundles post not appearing in results.
    Improvements include:
    - Better date parsing (handles both YYYY-MM-DD and ISO formats)
    - Expanded keyword detection (added 'g6 bundles', 'graphics.g6')
    - URL path checking for additional detection coverage
    - Comprehensive diagnostic output showing filtering decisions
    - Detailed date distribution with recent post titles
    """
    