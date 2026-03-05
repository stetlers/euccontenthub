```python
"""
Builder.AWS Selenium Crawler for ECS/Fargate
Fetches real author names and content from Builder.AWS pages using Selenium/Chrome
"""

import json
import os
import sys
import time
import boto3
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Read environment variables
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'aws-blog-posts')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'production')
POST_IDS_STR = os.environ.get('POST_IDS', '')

# Parse post IDs
POST_IDS = [pid.strip() for pid in POST_IDS_STR.split(',') if pid.strip()]

# AWS clients
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table(TABLE_NAME)
lambda_client = boto3.client('lambda', region_name='us-east-1')


def setup_driver():
    """Set up Chrome driver with headless options for ECS"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # Connect to Chrome (running in same container via selenium/standalone-chrome)
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    
    return driver


def is_aws_blog_post(url):
    """
    Check if URL is an AWS blog post (not Builder.AWS)
    
    Returns:
        bool: True if it's an AWS blog post
    """
    return url and 'aws.amazon.com/blogs/' in url


def extract_aws_blog_content(driver, url, max_retries=3):
    """
    Extract author and content from an AWS blog post
    
    Returns:
        dict: {'authors': str, 'content': str} or None if extraction fails
    """
    for attempt in range(max_retries):
        try:
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Give JavaScript time to render
            time.sleep(2)
            
            # Extract author name
            authors = "AWS"  # Default
            try:
                # AWS blog author selectors
                author_selectors = [
                    "//div[contains(@class, 'blog-post-meta')]//a[contains(@href, '/author/')]",
                    "//span[contains(@class, 'author')]",
                    "//div[contains(@class, 'author')]//a",
                    "//a[contains(@rel, 'author')]",
                    "//meta[@name='author']",
                    "//span[@class='author']",
                    "//div[@class='author']"
                ]
                
                for selector in author_selectors:
                    try:
                        if selector.startswith("//meta"):
                            author_elem = driver.find_element(By.XPATH, selector)
                            authors = author_elem.get_attribute('content')
                        else:
                            author_elem = driver.find_element(By.XPATH, selector)
                            authors = author_elem.text.strip()
                        
                        if authors and authors != "AWS":
                            print(f"  Found author with selector: {selector}")
                            break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                print(f"  Warning: Could not extract author: {e}")
            
            # Extract content
            content = ""
            try:
                # AWS blog content selectors
                content_selectors = [
                    "//div[contains(@class, 'blog-post-content')]",
                    "//article[contains(@class, 'blog-post')]",
                    "//div[contains(@class, 'entry-content')]",
                    "//div[@id='main-content']",
                    "//article",
                    "//main"
                ]
                
                for selector in content_selectors:
                    try:
                        content_elem = driver.find_element(By.XPATH, selector)
                        content = content_elem.text.strip()
                        if content and len(content) > 100:  # Ensure we got substantial content
                            print(f"  Found content with selector: {selector}")
                            break
                    except NoSuchElementException:
                        continue
                
                # If no content found, try getting all text from body
                if not content or len(content) < 100:
                    body = driver.find_element(By.TAG_NAME, "body")
                    content = body.text.strip()
            except Exception as e:
                print(f"  Warning: Could not extract content: {e}")
                content = "Content extraction failed. Visit the full article on AWS Blog."
            
            # Limit content to first 3000 characters
            if len(content) > 3000:
                content = content[:3000]
            
            return {
                'authors': authors,
                'content': content
            }
            
        except TimeoutException:
            if attempt < max_retries - 1:
                print(f"  Timeout on attempt {attempt + 1}, retrying...")
                time.sleep(2)
            else:
                print(f"  Failed after {max_retries} attempts")
                return None
                
        except Exception as e:
            print(f"  Error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return None
    
    return None


def extract_page_content(driver, url, max_retries=3):
    """
    Extract author and content from a Builder.AWS page
    
    Returns:
        dict: {'authors': str, 'content': str} or None if extraction fails
    """
    for attempt in range(max_retries):
        try:
            print(f"  Attempt {attempt + 1}/{max_retries}: Loading {url}")
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Give JavaScript time to render - increased for dynamic content
            time.sleep(3)
            
            # Debug: Check if page loaded correctly
            page_title = driver.title
            print(f"  Page title: {page_title}")
            
            # Check for common error indicators
            if "404" in page_title.lower() or "not found" in page_title.lower():
                print(f"  Warning: Page appears to be a 404 error")
            
            # Extract author name
            authors = "AWS Builder Community"  # Default
            try:
                # Try multiple selectors for author
                # Builder.AWS uses CSS modules with dynamic class names like _profile-name_xxxxx
                author_selectors = [
                    "//span[contains(@class, 'profile-name')]//span[contains(@class, 'ellipse-text')]",
                    "//span[contains(@class, 'profile-name')]",
                    "//span[contains(@class, '_profile-name')]",
                    "//div[contains(@class, 'author-name')]",
                    "//div[contains(@class, 'byline')]//span",
                    "//meta[@name='author']",
                    "//span[contains(@class, 'author')]",
                    "//div[contains(@class, 'author')]",
                    "//a[contains(@class, 'author')]",
                    "//span[contains(@data-testid, 'author')]",
                    "//div[contains(@class, 'post-author')]//span"
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
                            print(f"  Found author with selector: {selector} - '{authors}'")
                            break
                    except NoSuchElementException:
                        continue
                
                # If still default, try to find any element with author-related text
                if authors == "AWS Builder Community":
                    try:
                        all_spans = driver.find_elements(By.TAG_NAME, "span")
                        for span in all_spans:
                            span_text = span.text.strip()
                            class_name = span.get_attribute('class') or ''
                            if 'author' in class_name.lower() or 'profile' in class_name.lower():
                                if span_text and len(span_text) > 3 and len(span_text) < 100:
                                    authors = span_text
                                    print(f"  Found author from span search: '{authors}'")
                                    break
                    except Exception as e:
                        print(f"  Warning: Could not search spans for author: {e}")
                        
            except Exception as e:
                print(f"  Warning: Could not extract author: {e}")
            
            # Extract content
            content = ""
            try:
                # Try multiple selectors for main content with more comprehensive search
                content_selectors = [
                    "//article",
                    "//main",
                    "//div[contains(@class, 'content')]",
                    "//div[contains(@class, 'post-content')]",
                    "//div[contains(@class, 'entry-content')]",
                    "//div[contains(@class, 'article-content')]",
                    "//div[contains(@class, 'post')]",
                    "//div[contains(@class, 'article')]",
                    "//div[@role='article']",
                    "//div[contains(@class, 'blog-post')]",
                    "//section[contains(@class, 'content')]"
                ]
                
                for selector in content_selectors:
                    try:
                        content_elem = driver.find_element(By.XPATH, selector)
                        content = content_elem.text.strip()
                        if content and len(content) > 100:  # Ensure we got substantial content
                            print(f"  Found content with selector: {selector} (length: {len(content)})")
                            break
                    except NoSuchElementException:
                        continue
                
                # If no content found, try getting all text from body
                if not content or len(content) < 100:
                    print(f"  No content with selectors, trying body text")
                    body = driver.find_element(By.TAG_NAME, "body")
                    content = body.text.strip()
                    print(f"  Body text length: {len(content)}")
                
                # Additional fallback: try to get all paragraph text
                if not content or len(content) < 100:
                    print(f"  Trying paragraph fallback")
                    paragraphs = driver.find_elements(By.TAG_NAME, "p")
                    content = "\n".join([p.text.strip() for p in paragraphs if p.text.strip()])
                    print(f"  Paragraph text length: {len(content)}")
                    
            except Exception as e:
                print(f"  Warning: Could not extract content: {e}")
                content = "Content extraction failed. Visit the full article on Builder.AWS."
            
            # Debug output for content detection
            if len(content) < 100:
                print(f"  WARNING: Content too short ({len(content)} chars) - may indicate extraction issue")
                # Log page source for debugging (first 500 chars)
                try:
                    page_source_preview = driver.page_source[:500]
                    print(f"  Page source preview: {page_source_preview}")
                except Exception as e:
                    print(f"  Could not get page source: {e}")
            
            # Limit content to first 3000 characters (matching AWS Blog crawler)
            if len(content) > 3000:
                content = content[:3000]
            
            return {
                'authors': authors,
                'content': content
            }
            
        except TimeoutException:
            if attempt < max_retries - 1:
                print(f"  Timeout on attempt {attempt + 1}, retrying...")
                time.sleep(3)
            else:
                print(f"  Failed after {max_retries} attempts due to timeout")
                return None
                
        except Exception as e:
            print(f"  Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                print(f"  Failed after {max_retries} attempts")
                return None
    
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


def get_posts_to_crawl(post_ids):
    """
    Get posts to crawl from DynamoDB
    
    Args:
        post_ids: List of specific post IDs to crawl
        
    Returns:
        list: List of dicts with {'post_id': str, 'url': str, 'title': str, 'date': str}
    """
    posts = []
    for post_id in post_ids:
        try:
            response = table.get_item(Key={'post_id': post_id})
            if 'Item' in response:
                item = response['Item']
                post_data = {
                    'post_id': post_id,
                    'url': item.get('url', ''),
                    'title': item.get('title', 'Unknown'),
                    'date': item.get('date', 'Unknown')
                }
                posts.append(post_data)
                print(f"  Found post: {post_data['title']} (Date: {post_data['date']}, URL: {post_data['url']})")
            else:
                print(f"  Warning: Post {post_id} not found in DynamoDB")
        except Exception as e:
            print(f"  Error fetching post {post_id}: {e}")
    return posts


def invoke_summary_generator(posts_updated):
    """Invoke summary generator Lambda for the posts we just updated"""
    try:
        # Determine which alias to use based on environment
        function_name = f"aws-blog-summary-generator:{ENVIRONMENT}"
        
        # Calculate number of batches needed (5 posts per batch)
        batch_size = 5
        num_batches = (posts_updated + batch_size - 1) // batch_size
        
        for i in range(num_batches):
            lambda_client.