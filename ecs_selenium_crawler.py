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
    else:
        print(f"  DEBUG: URL classified as non-AWS blog: {url}")
    
    return is_aws_blog


def extract_aws_blog_content(driver, url, max_retries=3):
    """
    Extract author and content from an AWS blog post
    
    Returns:
        dict: {'authors': str, 'content': str} or None if extraction fails
    """
    print(f"  DEBUG: Starting AWS blog content extraction for: {url}")
    
    for attempt in range(max_retries):
        try:
            print(f"  DEBUG: Attempt {attempt + 1}/{max_retries}: Loading {url}")
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
            
            # Check for 404 or error pages
            if "404" in page_title.lower() or "not found" in page_title.lower():
                print(f"  WARNING: Page appears to be 404")
            
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
                            break
                    except NoSuchElementException:
                        continue
                
                if authors == "AWS":
                    print(f"  WARNING: Could not find specific author, using default")
                    
            except Exception as e:
                print(f"  WARNING: Could not extract author: {e}")
            
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
                            break
                    except NoSuchElementException:
                        continue
                
                # If no content found, try getting all text from body
                if not content or len(content) < 100:
                    print(f"  WARNING: Content too short, trying body text")
                    body = driver.find_element(By.TAG_NAME, "body")
                    content = body.text.strip()
                    print(f"  DEBUG: Body text length: {len(content)}")
                    
            except Exception as e:
                print(f"  WARNING: Could not extract content: {e}")
                content = "Content extraction failed. Visit the full article on AWS Blog."
            
            # Validate content quality
            if len(content) < 100:
                print(f"  WARNING: Content extraction may have failed (length: {len(content)})")
                try:
                    page_source_preview = driver.page_source[:1000]
                    print(f"  DEBUG: Page source preview: {page_source_preview}")
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
            if attempt < max_retries - 1:
                print(f"  Retrying after timeout...")
                time.sleep(2)
            else:
                print(f"  ERROR: FAILED after {max_retries} timeout attempts")
                return None
                
        except Exception as e:
            print(f"  ERROR: Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                print(f"  ERROR: FAILED after {max_retries} attempts")
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
            except TimeoutException:
                print(f"  Warning: Content elements not detected within timeout, proceeding anyway")
            
            # Debug: Check if page loaded correctly
            page_title = driver.title
            print(f"  Page title: {page_title}")
            current_url = driver.current_url
            print(f"  Current URL: {current_url}")
            
            # Check for common error indicators
            if "404" in page_title.lower() or "not found" in page_title.lower():
                print(f"  Warning: Page appears to be a 404 error")
                # Check if URL was redirected
                if current_url != url:
                    print(f"  Warning: URL was redirected from {url} to {current_url}")
            
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
                            if 'author' in class_name.lower() or 'profile' in class_name.lower() or 'contributor' in class_name.lower():
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
                    "//section[contains(@class, 'content')]",
                    "//div[contains(@class, 'markdown')]",
                    "//div[contains(@class, 'post-body')]"
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
            
            # Limit content to