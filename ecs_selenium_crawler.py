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

# CloudWatch Logs for enhanced debugging
logs_client = boto3.client('logs', region_name='us-east-1')
LOG_GROUP_NAME = f'/ecs/selenium-crawler-{ENVIRONMENT}'


def log_to_cloudwatch(message, level='INFO'):
    """
    Enhanced logging to CloudWatch for debugging
    
    Args:
        message: Log message
        level: Log level (INFO, WARNING, ERROR, DEBUG)
    """
    timestamp = int(time.time() * 1000)
    log_message = f"[{level}] [{datetime.utcnow().isoformat()}] {message}"
    
    # Print to stdout (captured by ECS)
    print(log_message)
    
    # Also send to CloudWatch for centralized logging
    try:
        logs_client.put_log_events(
            logGroupName=LOG_GROUP_NAME,
            logStreamName=f'crawler-{datetime.utcnow().strftime("%Y-%m-%d")}',
            logEvents=[
                {
                    'timestamp': timestamp,
                    'message': log_message
                }
            ]
        )
    except Exception as e:
        # Don't fail the crawler if CloudWatch logging fails
        print(f"WARNING: Could not write to CloudWatch: {e}")


def setup_driver():
    """Set up Chrome driver with headless options for ECS"""
    log_to_cloudwatch("Setting up Chrome driver", "DEBUG")
    
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
    
    log_to_cloudwatch("Chrome driver initialized successfully", "DEBUG")
    return driver


def is_aws_blog_post(url):
    """
    Check if URL is an AWS blog post (not Builder.AWS)
    
    Returns:
        bool: True if it's an AWS blog post
    """
    return url and 'aws.amazon.com/blogs/' in url


def verify_url_accessible(driver, url):
    """
    Verify that a URL is accessible and returns a valid page
    
    Returns:
        dict: {'accessible': bool, 'status_code': int, 'error': str}
    """
    log_to_cloudwatch(f"Verifying URL accessibility: {url}", "DEBUG")
    
    try:
        driver.get(url)
        time.sleep(2)  # Wait for page to load
        
        # Check if we got a valid page (not 404 or error page)
        page_title = driver.title
        page_source = driver.page_source
        
        # Check for common error indicators
        error_indicators = [
            '404',
            'page not found',
            'not found',
            'error',
            'access denied'
        ]
        
        page_text_lower = page_source.lower()
        has_error = any(indicator in page_text_lower for indicator in error_indicators)
        
        if has_error:
            log_to_cloudwatch(f"URL appears to have an error: {page_title}", "WARNING")
            return {
                'accessible': False,
                'status_code': 404,
                'error': f"Page contains error indicators. Title: {page_title}"
            }
        
        log_to_cloudwatch(f"URL is accessible. Title: {page_title}", "DEBUG")
        return {
            'accessible': True,
            'status_code': 200,
            'error': None
        }
        
    except TimeoutException:
        log_to_cloudwatch(f"Timeout accessing URL: {url}", "ERROR")
        return {
            'accessible': False,
            'status_code': 0,
            'error': "Timeout accessing URL"
        }
    except Exception as e:
        log_to_cloudwatch(f"Error accessing URL: {url} - {str(e)}", "ERROR")
        return {
            'accessible': False,
            'status_code': 0,
            'error': str(e)
        }


def extract_aws_blog_content(driver, url, max_retries=3):
    """
    Extract author and content from an AWS blog post
    
    Returns:
        dict: {'authors': str, 'content': str} or None if extraction fails
    """
    log_to_cloudwatch(f"Extracting AWS blog content from: {url}", "DEBUG")
    
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
                            log_to_cloudwatch(f"Found author with selector: {selector} - Author: {authors}", "DEBUG")
                            break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                log_to_cloudwatch(f"Could not extract author: {str(e)}", "WARNING")
            
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
                            log_to_cloudwatch(f"Found content with selector: {selector} - Length: {len(content)}", "DEBUG")
                            break
                    except NoSuchElementException:
                        continue
                
                # If no content found, try getting all text from body
                if not content or len(content) < 100:
                    body = driver.find_element(By.TAG_NAME, "body")
                    content = body.text.strip()
                    log_to_cloudwatch(f"Using body content - Length: {len(content)}", "DEBUG")
            except Exception as e:
                log_to_cloudwatch(f"Could not extract content: {str(e)}", "ERROR")
                content = "Content extraction failed. Visit the full article on AWS Blog."
            
            # Limit content to first 3000 characters
            if len(content) > 3000:
                content = content[:3000]
            
            log_to_cloudwatch(f"Successfully extracted AWS blog content - Author: {authors}, Content length: {len(content)}", "INFO")
            return {
                'authors': authors,
                'content': content
            }
            
        except TimeoutException:
            if attempt < max_retries - 1:
                log_to_cloudwatch(f"Timeout on attempt {attempt + 1}, retrying...", "WARNING")
                time.sleep(2)
            else:
                log_to_cloudwatch(f"Failed after {max_retries} attempts", "ERROR")
                return None
                
        except Exception as e:
            log_to_cloudwatch(f"Error extracting content (attempt {attempt + 1}): {str(e)}", "ERROR")
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
    log_to_cloudwatch(f"Extracting Builder.AWS content from: {url}", "DEBUG")
    
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
            authors = "AWS Builder Community"  # Default
            try:
                # Try multiple selectors for author
                # Builder.AWS uses CSS modules with dynamic class names like _profile-name_xxxxx
                author_selectors = [
                    "//span[contains(@class, 'profile-name')]//span[contains(@class, 'ellipse-text')]",
                    "//span[contains(@class, 'profile-name')]",
                    "//span[contains(@class, '_profile-name')]",
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
                            log_to_cloudwatch(f"Found author with selector: {selector} - Author: {authors}", "DEBUG")
                            break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                log_to_cloudwatch(f"Could not extract author: {str(e)}", "WARNING")
            
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
                            log_to_cloudwatch(f"Found content with selector: {selector} - Length: {len(content)}", "DEBUG")
                            break
                    except NoSuchElementException:
                        continue
                
                # If no content found, try getting all text from body
                if not content or len(content) < 100:
                    body = driver.find_element(By.TAG_NAME, "body")
                    content = body.text.strip()
                    log_to_cloudwatch(f"Using body content - Length: {len(content)}", "DEBUG")
            except Exception as e:
                log_to_cloudwatch(f"Could not extract content: {str(e)}", "ERROR")
                content = "Content extraction failed. Visit the full article on Builder.AWS."
            
            # Limit content to first 3000 characters (matching AWS Blog crawler)
            if len(content) > 3000:
                content = content[:3000]
            
            log_to_cloudwatch(f"Successfully extracted Builder.AWS content - Author: {authors}, Content length: {len(content)}", "INFO")
            return {
                'authors': authors,
                'content': content
            }
            
        except TimeoutException:
            if attempt < max_retries - 1:
                log_to_cloudwatch(f"Timeout on attempt {attempt + 1}, retrying...", "WARNING")
                time.sleep(2)
            else:
                log_to_cloudwatch(f"Failed after {max_retries} attempts", "ERROR")
                return None
                
        except Exception as e:
            log_to_cloudwatch(f"Error extracting content (attempt {attempt + 1}): {str(e)}", "ERROR")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return None
    
    return None


def update_post_in_dynamodb(post_id, authors, content):
    """
    Update a post in DynamoDB with real authors and content
    
    Includes enhanced logging for debugging DynamoDB write issues
    """
    log_to_cloudwatch(f"Updating DynamoDB for post_id: {post_id}", "DEBUG")
    log_to_cloudwatch(f"Table: {TABLE_NAME}, Authors: {authors}, Content length: {len(content)}", "DEBUG")
    
    try:
        response = table.update_item(
            Key={'post_id': post_id},
            UpdateExpression='SET authors = :authors, content = :content, last_crawled = :last_crawled',
            ExpressionAttributeValues={
                ':authors': authors,
                ':content': content,
                ':last_crawled': datetime.utcnow().isoformat()
            },
            ReturnValues='ALL_NEW'
        )
        
        log_to_cloudwatch(f"Successfully updated DynamoDB for post_id: {post_