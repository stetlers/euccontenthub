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


def verify_url_accessibility(driver, url):
    """
    Verify that a URL is accessible and returns valid content
    
    Returns:
        dict: {'accessible': bool, 'status_message': str, 'redirected_url': str}
    """
    print(f"  DEBUG: Verifying URL accessibility: {url}")
    log_to_cloudwatch(f"Verifying URL accessibility: {url}", 'DEBUG')
    
    try:
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        time.sleep(2)
        
        page_title = driver.title
        current_url = driver.current_url
        
        print(f"  DEBUG: Page loaded - Title: '{page_title}', URL: '{current_url}'")
        log_to_cloudwatch(f"Page loaded - Title: '{page_title}', URL: '{current_url}'", 'DEBUG')
        
        # Check for error indicators
        error_indicators = ['404', 'not found', 'page not found', 'error']
        is_error = any(indicator in page_title.lower() for indicator in error_indicators)
        
        if is_error:
            print(f"  WARNING: Page appears to be an error page (title: '{page_title}')")
            log_to_cloudwatch(f"Error page detected - Title: '{page_title}', URL: {url}", 'WARNING')
            return {
                'accessible': False,
                'status_message': f"Error page detected (title: '{page_title}')",
                'redirected_url': current_url
            }
        
        # Check if URL was redirected
        if current_url != url:
            print(f"  INFO: URL was redirected from {url} to {current_url}")
            log_to_cloudwatch(f"URL redirected from {url} to {current_url}", 'INFO')
        
        # Check if page has content
        body = driver.find_element(By.TAG_NAME, "body")
        body_text = body.text.strip()
        
        if len(body_text) < 50:
            print(f"  WARNING: Page has minimal content (length: {len(body_text)})")
            log_to_cloudwatch(f"Minimal content detected (length: {len(body_text)}) for {url}", 'WARNING')
            return {
                'accessible': True,
                'status_message': f"Page accessible but has minimal content (length: {len(body_text)})",
                'redirected_url': current_url
            }
        
        print(f"  DEBUG: URL is accessible with content (length: {len(body_text)})")
        log_to_cloudwatch(f"URL is accessible with content (length: {len(body_text)})", 'DEBUG')
        
        return {
            'accessible': True,
            'status_message': 'Page accessible with content',
            'redirected_url': current_url
        }
        
    except TimeoutException:
        print(f"  ERROR: Timeout while accessing URL: {url}")
        log_to_cloudwatch(f"Timeout while accessing URL: {url}", 'ERROR')
        return {
            'accessible': False,
            'status_message': 'Timeout while loading page',
            'redirected_url': None
        }
    except Exception as e:
        print(f"  ERROR: Exception while verifying URL accessibility: {e}")
        log_to_cloudwatch(f"Exception while verifying URL accessibility for {url}: {e}", 'ERROR')
        return {
            'accessible': False,
            'status_message': f'Exception: {str(e)}',
            'redirected_url': None
        }


def extract_aws_blog_metadata(driver, url):
    """
    Extract comprehensive metadata from AWS blog post for debugging
    Enhanced to better detect staging posts and various date formats
    
    Returns:
        dict: Complete metadata including publication date, author, categories, etc.
    """
    print(f"  DEBUG: Extracting comprehensive metadata from: {url}")
    log_to_cloudwatch(f"Extracting comprehensive metadata from: {url}", 'INFO')
    
    metadata = {
        'url': url,
        'title': None,
        'publication_date': None,
        'modified_date': None,
        'author': None,
        'categories': [],
        'tags': [],
        'description': None,
        'og_metadata': {},
        'twitter_metadata': {},
        'schema_metadata': {}
    }
    
    try:
        # Extract page title
        metadata['title'] = driver.title
        print(f"  DEBUG: Title: {metadata['title']}")
        
        # Extract meta tags
        meta_tags = driver.find_elements(By.TAG_NAME, "meta")
        for meta in meta_tags:
            name = meta.get_attribute('name') or meta.get_attribute('property')
            content = meta.get_attribute('content')
            
            if not name or not content:
                continue
            
            # Publication date - expanded to catch more date formats including staging
            if name in ['article:published_time', 'datePublished', 'date', 'publish-date', 'pubdate', 
                       'publication-date', 'publishdate', 'DC.date.issued', 'sailthru.date']:
                metadata['publication_date'] = content
                print(f"  DEBUG: Found publication date: {content} (from {name})")
                log_to_cloudwatch(f"Publication date found: {content} (from {name})", 'DEBUG')
            
            # Modified date
            if name in ['article:modified_time', 'dateModified', 'lastmod', 'last-modified']:
                metadata['modified_date'] = content
                print(f"  DEBUG: Found modified date: {content} (from {name})")
            
            # Author
            if name in ['author', 'article:author', 'DC.creator']:
                metadata['author'] = content
                print(f"  DEBUG: Found author: {content} (from {name})")
            
            # Description
            if name in ['description', 'og:description', 'twitter:description']:
                metadata['description'] = content
            
            # Open Graph metadata
            if name and name.startswith('og:'):
                metadata['og_metadata'][name] = content
            
            # Twitter metadata
            if name and name.startswith('twitter:'):
                metadata['twitter_metadata'][name] = content
        
        # Extract structured data (JSON-LD)
        try:
            script_tags = driver.find_elements(By.XPATH, "//script[@type='application/ld+json']")
            for script in script_tags:
                try:
                    json_data = json.loads(script.get_attribute('innerHTML'))
                    if isinstance(json_data, dict):
                        if json_data.get('@type') in ['BlogPosting', 'Article', 'NewsArticle', 'TechArticle']:
                            metadata['schema_metadata'] = json_data
                            if 'datePublished' in json_data and not metadata['publication_date']:
                                metadata['publication_date'] = json_data['datePublished']
                                print(f"  DEBUG: Found publication date from schema: {json_data['datePublished']}")
                                log_to_cloudwatch(f"Publication date from schema: {json_data['datePublished']}", 'DEBUG')
                            if 'author' in json_data and not metadata['author']:
                                author_data = json_data['author']
                                if isinstance(author_data, dict):
                                    metadata['author'] = author_data.get('name', 'AWS')
                                elif isinstance(author_data, str):
                                    metadata['author'] = author_data
                                print(f"  DEBUG: Found author from schema: {metadata['author']}")
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            print(f"  WARNING: Could not extract structured data: {e}")
        
        # Try to find publication date in page content if not found in meta
        # Enhanced selectors to capture staging and various AWS blog formats
        if not metadata['publication_date']:
            date_selectors = [
                # Standard AWS blog selectors
                "//time[@datetime]",
                "//span[contains(@class, 'date')]",
                "//div[contains(@class, 'date')]",
                "//span[contains(@class, 'published')]",
                "//div[contains(@class, 'post-date')]",
                "//div[contains(@class, 'blog-post-meta')]//time",
                "//div[contains(@class, 'meta-date')]",
                "//span[contains(@class, 'entry-date')]",
                "//div[contains(@class, 'entry-meta')]//time",
                "//article//time",
                # Staging-specific selectors
                "//div[contains(@class, 'post-metadata')]//time",
                "//div[contains(@class, 'article-metadata')]//span[contains(@class, 'date')]",
                "//div[contains(@class, 'post-meta')]//time",
                "//div[contains(@class, 'byline')]//time",
                # Additional generic selectors
                "//header//time",
                "//main//time",
                "//span[contains(@class, 'post-published')]",
                "//div[contains(@id, 'post-date')]",
                "//div[contains(@id, 'publish-date')]",
                # Try data attributes
                "//*[@data-date]",
                "//*[@data-published]",
                "//*[@data-publish-date]"
            ]
            
            for selector in date_selectors:
                try:
                    date_elem = driver.find_element(By.XPATH, selector)
                    # Try datetime attribute first
                    datetime_attr = date_elem.get_attribute('datetime')
                    if datetime_attr:
                        metadata['publication_date'] = datetime_attr
                        print(f"  DEBUG: Found publication date in page: {datetime_attr} (selector: {selector})")
                        log_to_cloudwatch(f"Publication date found in page: {datetime_attr} (selector: {selector})", 'DEBUG')
                        break
                    # Try data-date attribute
                    data_date = date_elem.get_attribute('data-date') or date_elem.get_attribute('data-published')
                    if data_date:
                        metadata['publication_date'] = data_date
                        print(f"  DEBUG: Found publication date in data attribute: {data_date} (selector: {selector})")
                        log_to_cloudwatch(f"Publication date found in data attribute: {data_date} (selector: {selector})", 'DEBUG')
                        break
                    # Fallback to text content
                    date_text = date_elem.text.strip()
                    if date_text and len(date_text) > 5:  # Basic validation
                        metadata['publication_date'] = date_text
                        print(f"  DEBUG: Found publication date text: {date_text} (selector: {selector})")
                        log_to_cloudwatch(f"Publication date text found: {date_text} (selector: {selector})", 'DEBUG')
                        break
                except NoSuchElementException:
                    continue
        
        # If still no date found, log page source excerpt for debugging
        if not metadata['publication_date']:
            print(f"  WARNING: No publication date found for {url}")
            log_to_cloudwatch(f"No publication date found for {url}", 'WARNING')
            try:
                # Get page source snippet that might contain date
                page_source =