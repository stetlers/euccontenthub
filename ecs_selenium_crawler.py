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


def check_staging_table_for_post(url, title_keywords=None):
    """
    Check staging DynamoDB table for any data related to the post
    
    Args:
        url: URL to search for
        title_keywords: Optional keywords from title to search for
    
    Returns:
        dict: Information about any found records
    """
    print(f"  DEBUG: Checking staging table for post: {url}")
    log_to_cloudwatch(f"Checking staging table for post: {url}", 'DEBUG')
    
    results = {
        'found': False,
        'records': [],
        'partial_matches': []
    }
    
    try:
        staging_table_name = TABLE_NAME.replace('-production', '-staging') if 'production' in TABLE_NAME else f"{TABLE_NAME}-staging"
        staging_table = dynamodb.Table(staging_table_name)
        
        # Try to find exact URL match
        try:
            response = staging_table.scan(
                FilterExpression='contains(#url, :url)',
                ExpressionAttributeNames={'#url': 'url'},
                ExpressionAttributeValues={':url': url}
            )
            
            if response.get('Items'):
                results['found'] = True
                results['records'] = response['Items']
                print(f"  INFO: Found {len(response['Items'])} records in staging table with URL: {url}")
                log_to_cloudwatch(f"Found {len(response['Items'])} records in staging table with URL: {url}", 'INFO')
        except Exception as e:
            print(f"  WARNING: Error scanning staging table by URL: {e}")
            log_to_cloudwatch(f"Error scanning staging table by URL: {e}", 'WARNING')
        
        # If title keywords provided, search by title
        if title_keywords and not results['found']:
            try:
                for keyword in title_keywords:
                    if len(keyword) < 4:  # Skip very short keywords
                        continue
                    
                    response = staging_table.scan(
                        FilterExpression='contains(title, :keyword)',
                        ExpressionAttributeValues={':keyword': keyword}
                    )
                    
                    if response.get('Items'):
                        results['partial_matches'].extend(response['Items'])
                        print(f"  INFO: Found {len(response['Items'])} partial matches in staging table with keyword: {keyword}")
                        log_to_cloudwatch(f"Found {len(response['Items'])} partial matches with keyword: {keyword}", 'INFO')
            except Exception as e:
                print(f"  WARNING: Error scanning staging table by title: {e}")
                log_to_cloudwatch(f"Error scanning staging table by title: {e}", 'WARNING')
        
    except Exception as e:
        print(f"  ERROR: Error accessing staging table: {e}")
        log_to_cloudwatch(f"Error accessing staging table: {e}", 'ERROR')
    
    return results


def check_filtering_criteria(metadata, url):
    """
    Verify if the post meets all filtering criteria that might cause it to be excluded
    
    Args:
        metadata: Post metadata dictionary
        url: Post URL
    
    Returns:
        dict: Analysis of filtering criteria with pass/fail status
    """
    print(f"  DEBUG: Checking filtering criteria for: {url}")
    log_to_cloudwatch(f"Checking filtering criteria for: {url}", 'DEBUG')
    
    criteria = {
        'has_publication_date': False,
        'date_parseable': False,
        'date_within_range': False,
        'has_title': False,
        'has_content': False,
        'url_valid': False,
        'meets_all_criteria': False,
        'failures': []
    }
    
    # Check publication date
    if metadata.get('publication_date'):
        criteria['has_publication_date'] = True
        print(f"  DEBUG: ✓ Has publication date: {metadata['publication_date']}")
        
        # Try to parse date
        try:
            parsed_date = date_parser.parse(metadata['publication_date'])
            criteria['date_parseable'] = True
            print(f"  DEBUG: ✓ Date is parseable: {parsed_date}")
            log_to_cloudwatch(f"Parsed date: {parsed_date} from {metadata['publication_date']}", 'DEBUG')
            
            # Check if date is reasonable (not in far future or too old)
            now = datetime.now(timezone.utc)
            if parsed_date <= now and parsed_date.year >= 2006:  # AWS founded in 2006
                criteria['date_within_range'] = True
                print(f"  DEBUG: ✓ Date is within valid range")
            else:
                criteria['failures'].append(f"Date out of range: {parsed_date}")
                print(f"  DEBUG: ✗ Date out of range: {parsed_date}")
                log_to_cloudwatch(f"Date out of range: {parsed_date}", 'WARNING')
        except Exception as e:
            criteria['failures'].append(f"Date parsing error: {e}")
            print(f"  DEBUG: ✗ Could not parse date: {e}")
            log_to_cloudwatch(f"Date parsing error for '{metadata['publication_date']}': {e}", 'WARNING')
    else:
        criteria['failures'].append("No publication date found")
        print(f"  DEBUG: ✗ No publication date found")
        log_to_cloudwatch(f"No publication date found for {url}", 'WARNING')
    
    # Check title
    if metadata.get('title') and len(metadata['title'].strip()) > 5:
        criteria['has_title'] = True
        print(f"  DEBUG: ✓ Has valid title: {metadata['title'][:50]}...")
    else:
        criteria['failures'].append(f"Invalid title: {metadata.get('title')}")
        print(f"  DEBUG: ✗ Invalid or missing title")
    
    # Check content (assuming metadata contains content info)
    if metadata.get('description') or metadata.get('schema_metadata'):
        criteria['has_content'] = True
        print(f"  DEBUG: ✓ Has content/description")
    else:
        criteria['failures'].append("No content or description found")
        print(f"  DEBUG: ✗ No content or description found")
    
    # Check URL validity
    if url and (url.startswith('http://') or url.startswith('https://')):
        criteria['url_valid'] = True
        print(f"  DEBUG: ✓ URL is valid")
    else:
        criteria['failures'].append(f"Invalid URL: {url}")
        print(f"  DEBUG: ✗ Invalid URL")
    
    # Overall check
    criteria['meets_all_criteria'] = all([
        criteria['has_publication_date'],
        criteria['date_parseable'],
        criteria['date_within_range'],
        criteria['has_title'],
        criteria['url_valid']
    ])
    
    if criteria['meets_all_criteria']:
        print(f"  INFO: ✓ Post meets all filtering criteria")
        log_to_cloudwatch(f"Post meets all filtering criteria: {url}", 'INFO')
    else:
        print(f"  WARNING: ✗ Post fails filtering criteria: {', '.join(criteria['failures'])}")
        log_to_cloudwatch(f"Post fails filtering criteria: {url} - {', '.join(criteria['failures'])}", 'WARNING')
    
    return criteria


def extract_aws_blog_metadata(driver, url):
    """
    Extract comprehensive metadata from AWS blog post for debugging
    Enhanced to better detect staging posts and various date formats
    
    Returns:
        dict: Complete metadata including publication date, author, categories, etc.
    """
    print(f"  DEBUG: Extracting comprehensive metadata from: {url}")
    log_to_cloudwatch(f"Extracting comprehensive metadata from: {url}", 'INFO')