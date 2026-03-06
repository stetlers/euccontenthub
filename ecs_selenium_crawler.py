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
from datetime import datetime, timezone
from dateutil import parser as date_parser
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

# CloudWatch Logs client for detailed logging
logs_client = boto3.client('logs', region_name='us-east-1')
LOG_GROUP_NAME = '/ecs/selenium-crawler'


def log_to_cloudwatch(message, level='INFO'):
    """Send detailed logs to CloudWatch for investigation"""
    try:
        timestamp = int(time.time() * 1000)
        log_stream_name = f"crawler-{datetime.now().strftime('%Y-%m-%d')}"
        
        # Create log stream if it doesn't exist
        try:
            logs_client.create_log_stream(
                logGroupName=LOG_GROUP_NAME,
                logStreamName=log_stream_name
            )
        except logs_client.exceptions.ResourceAlreadyExistsException:
            pass
        
        # Put log event
        logs_client.put_log_events(
            logGroupName=LOG_GROUP_NAME,
            logStreamName=log_stream_name,
            logEvents=[
                {
                    'timestamp': timestamp,
                    'message': f"[{level}] {message}"
                }
            ]
        )
    except Exception as e:
        print(f"Warning: Could not log to CloudWatch: {e}")


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
    if not url:
        print(f"  DEBUG: URL is None or empty")
        log_to_cloudwatch(f"URL check: URL is None or empty", 'DEBUG')
        return False
    
    # Check for AWS blog patterns - including both production and staging
    aws_blog_patterns = [
        'aws.amazon.com/blogs/',
        'staging.awseuccontent.com'
    ]
    
    is_aws_blog = any(pattern in url for pattern in aws_blog_patterns)
    
    # Log URL classification
    if is_aws_blog:
        print(f"  DEBUG: URL classified as AWS blog: {url}")
        log_to_cloudwatch(f"URL classified as AWS blog: {url}", 'DEBUG')
    else:
        print(f"  DEBUG: URL classified as non-AWS blog: {url}")
        log_to_cloudwatch(f"URL classified as non-AWS blog: {url}", 'DEBUG')
    
    return is_aws_blog


def extract_aws_blog_content(driver, url, max_retries=3):
    """
    Extract author and content from an AWS blog post
    
    Returns:
        dict: {'authors': str, 'content': str} or None if extraction fails
    """
    print(f"  DEBUG: Starting AWS blog content extraction for: {url}")
    log_to_cloudwatch(f"Starting AWS blog content extraction for: {url}", 'INFO')
    
    for attempt in range(max_retries):
        try:
            print(f"  DEBUG: Attempt {attempt + 1}/{max_retries}: Loading {url}")
            log_to_cloudwatch(f"Attempt {attempt + 1}/{max_retries}: Loading {url}", 'DEBUG')
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Give JavaScript time to render
            time.sleep(2)
            
            # Check page title and URL for debugging
            page_title = driver.title
            current_url = driver.current_url
            print(f"  DEBUG: Page title: {page_title}")
            print(f"  DEBUG: Current URL: {current_url}")
            log_to_cloudwatch(f"Page title: {page_title}, Current URL: {current_url}", 'DEBUG')
            
            # Check for 404 or error pages
            if "404" in page_title.lower() or "not found" in page_title.lower():
                print(f"  WARNING: Page appears to be 404")
                log_to_cloudwatch(f"Page appears to be 404: {url}", 'WARNING')
            
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
                    "//div[@class='author']",
                    "//div[contains(@class, 'byline')]//a",
                    "//div[contains(@class, 'post-author')]"
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
                            print(f"  DEBUG: Found author with selector: {selector} - '{authors}'")
                            log_to_cloudwatch(f"Found author: {authors} with selector: {selector}", 'DEBUG')
                            break
                    except NoSuchElementException:
                        continue
                
                if authors == "AWS":
                    print(f"  WARNING: Could not find specific author, using default")
                    log_to_cloudwatch(f"Could not find specific author for {url}, using default", 'WARNING')
                    
            except Exception as e:
                print(f"  WARNING: Could not extract author: {e}")
                log_to_cloudwatch(f"Could not extract author: {e}", 'WARNING')
            
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
                    "//main",
                    "//div[contains(@class, 'post-content')]",
                    "//div[@id='content']",
                    "//section[contains(@class, 'content')]"
                ]
                
                for selector in content_selectors:
                    try:
                        content_elem = driver.find_element(By.XPATH, selector)
                        content = content_elem.text.strip()
                        if content and len(content) > 100:  # Ensure we got substantial content
                            print(f"  DEBUG: Found content with selector: {selector} (length: {len(content)})")
                            log_to_cloudwatch(f"Found content with selector: {selector} (length: {len(content)})", 'DEBUG')
                            break
                    except NoSuchElementException:
                        continue
                
                # If no content found, try getting all text from body
                if not content or len(content) < 100:
                    print(f"  WARNING: Content too short, trying body text")
                    log_to_cloudwatch(f"Content too short, trying body text for {url}", 'WARNING')
                    body = driver.find_element(By.TAG_NAME, "body")
                    content = body.text.strip()
                    print(f"  DEBUG: Body text length: {len(content)}")
                    log_to_cloudwatch(f"Body text length: {len(content)}", 'DEBUG')
                    
            except Exception as e:
                print(f"  WARNING: Could not extract content: {e}")
                log_to_cloudwatch(f"Could not extract content: {e}", 'WARNING')
                content = "Content extraction failed. Visit the full article on AWS Blog."
            
            # Validate content quality
            if len(content) < 100:
                print(f"  WARNING: Content extraction may have failed (length: {len(content)})")
                log_to_cloudwatch(f"Content extraction may have failed (length: {len(content)}) for {url}", 'WARNING')
                try:
                    page_source_preview = driver.page_source[:1000]
                    print(f"  DEBUG: Page source preview: {page_source_preview}")
                    log_to_cloudwatch(f"Page source preview: {page_source_preview}", 'DEBUG')
                except Exception as e:
                    print(f"  DEBUG: Could not retrieve page source: {e}")
            
            # Limit content to first 3000 characters
            if len(content) > 3000:
                content = content[:3000]
            
            return {
                'authors': authors,
                'content': content
            }
            
        except TimeoutException:
            print(f"  WARNING: Timeout on attempt {attempt + 1}")
            log_to_cloudwatch(f"Timeout on attempt {attempt + 1} for {url}", 'WARNING')
            if attempt < max_retries - 1:
                print(f"  Retrying after timeout...")
                time.sleep(2)
            else:
                print(f"  ERROR: FAILED after {max_retries} timeout attempts")
                log_to_cloudwatch(f"FAILED after {max_retries} timeout attempts for {url}", 'ERROR')
                return None
                
        except Exception as e:
            print(f"  ERROR: Error on attempt {attempt + 1}: {e}")
            log_to_cloudwatch(f"Error on attempt {attempt + 1} for {url}: {e}", 'ERROR')
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                print(f"  ERROR: FAILED after {max_retries} attempts")
                log_to_cloudwatch(f"FAILED after {max_retries} attempts for {url}", 'ERROR')
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
            log_to_cloudwatch(f"Attempt {attempt + 1}/{max_retries}: Loading {url}", 'INFO')
            driver.get(url)
            
            # Wait for page to load - increased timeout for dynamic content
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Give JavaScript time to render - increased for dynamic content
            time.sleep(4)
            
            # Additional wait for content to be loaded (check for specific elements)
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: len(d.find_elements(By.TAG_NAME, "p")) > 0 or 
                             len(d.find_elements(By.TAG_NAME, "article")) > 0
                )
                print(f"  Content elements detected on page")
                log_to_cloudwatch(f"Content elements detected on page: {url}", 'DEBUG')
            except TimeoutException:
                print(f"  Warning: Content elements not detected within timeout, proceeding anyway")
                log_to_cloudwatch(f"Content elements not detected within timeout for {url}", 'WARNING')
            
            # Debug: Check if page loaded correctly
            page_title = driver.title
            print(f"  Page title: {page_title}")
            current_url = driver.current_url
            print(f"  Current URL: {current_url}")
            log_to_cloudwatch(f"Page title: {page_title}, Current URL: {current_url}", 'DEBUG')
            
            # Check for common error indicators
            if "404" in page_title.lower() or "not found" in page_title.lower():
                print(f"  Warning: Page appears to be a 404 error")
                log_to_cloudwatch(f"Page appears to be 404: {url}", 'WARNING')
                # Check if URL was redirected
                if current_url != url:
                    print(f"  Warning: URL was redirected from {url} to {current_url}")
                    log_to_cloudwatch(f"URL redirected from {url} to {current_url}", 'WARNING')
            
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
                    "//div[contains(@class, 'post-author')]//span",
                    "//div[contains(@class, 'contributor')]//span",
                    "//a[contains(@href, '/contributors/')]",
                    "//div[contains(@class, 'metadata')]//a"
                ]