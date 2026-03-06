```python
"""
Builder.AWS Playwright Crawler Lambda Function
Uses Playwright with AWS Lambda support for better compatibility
"""

import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import boto3
import requests

# Playwright imports
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("WARNING: Playwright not available")

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'aws-blog-posts')

# Debug mode - set via environment variable or event parameter
DEBUG_MODE = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'


def debug_print(message):
    """Print debug messages when DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")


def get_article_sitemaps():
    """Get list of article sitemap URLs"""
    # Support both production and staging environments
    base_domain = os.environ.get('BASE_DOMAIN', 'builder.aws.com')
    sitemap_index_url = f'https://{base_domain}/sitemaps/sitemap.xml'
    
    debug_print(f"Fetching sitemap index from: {sitemap_index_url}")
    
    try:
        response = requests.get(sitemap_index_url, timeout=30)
        response.raise_for_status()
        
        root = ET.fromstring(response.text)
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        article_sitemaps = []
        for url_elem in root.findall('.//ns:url', namespace):
            loc = url_elem.find('ns:loc', namespace)
            if loc is not None and '/sitemaps/articles/' in loc.text:
                article_sitemaps.append(loc.text)
        
        debug_print(f"Found {len(article_sitemaps)} article sitemaps")
        return article_sitemaps
        
    except Exception as e:
        print(f"Error fetching sitemap index: {e}")
        return []


def is_euc_related(url, title):
    """Check if content is EUC-related"""
    text = f"{url} {title}".lower()
    keywords = [
        'euc', 'end-user-computing', 'end user computing',
        'workspaces', 'appstream', 'workspace',
        'end user', 'desktop', 'virtual desktop',
        'vdi', 'daas', 'graphics'
    ]
    is_related = any(keyword in text for keyword in keywords)
    debug_print(f"EUC check for '{title}': {is_related}")
    return is_related


def extract_title_from_slug(url):
    """Extract title from URL slug as fallback"""
    slug = url.rstrip('/').split('/')[-1]
    words = slug.split('-')
    
    title_words = []
    for i, word in enumerate(words):
        if word.isupper() and len(word) <= 4:
            title_words.append(word)
        elif word.lower() in ['ai', 'ml', 'api', 'aws', 'iam', 'ec2', 's3', 'vpc', 'euc', 'vdi']:
            title_words.append(word.upper())
        elif word.lower() == 'appstream':
            title_words.append('AppStream')
        elif word.lower() == 'workspaces':
            title_words.append('WorkSpaces')
        elif word.lower() == 'daas':
            title_words.append('DaaS')
        elif word.isdigit() and i + 1 < len(words) and words[i + 1] == '0':
            title_words.append(word + '.0')
            words[i + 1] = ''
        elif word == '':
            continue
        else:
            title_words.append(word.capitalize())
    
    return ' '.join(title_words)


def parse_date(date_string):
    """Parse date string and return ISO format, handling various formats"""
    if not date_string:
        return None
    
    try:
        # Try parsing ISO format with timezone
        if 'T' in date_string:
            if '+' in date_string or date_string.endswith('Z'):
                dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(date_string)
            return dt.isoformat()
        
        # Try parsing date-only format
        dt = datetime.strptime(date_string.split('T')[0], '%Y-%m-%d')
        return dt.isoformat()
    except Exception as e:
        debug_print(f"Date parsing error for '{date_string}': {e}")
        return date_string


def extract_page_content(page, url):
    """Extract content from a page using Playwright"""
    try:
        debug_print(f"Loading page: {url}")
        print(f"  Loading: {url}")
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        
        # Wait for h1 to appear
        try:
            page.wait_for_selector('h1', timeout=10000)
        except:
            print(f"  Timeout waiting for content")
            debug_print(f"Timeout waiting for h1 selector on {url}")
            return None
        
        # Brief wait for dynamic content
        time.sleep(1)
        
        metadata = {
            'url': url,
            'title': '',
            'authors': '',
            'date_published': '',
            'content': '',
            'source': 'builder.aws.com'
        }
        
        # Extract title
        try:
            title_elem = page.query_selector('h1')
            if title_elem:
                metadata['title'] = title_elem.inner_text().strip()
                debug_print(f"Extracted title: {metadata['title']}")
        except Exception as e:
            debug_print(f"Error extracting title: {e}")
        
        if not metadata['title']:
            metadata['title'] = extract_title_from_slug(url)
            debug_print(f"Using slug-based title: {metadata['title']}")
        
        # Extract author - look for profile div
        author_found = False
        try:
            profile_div = page.query_selector("[class*='_profile_']")
            if profile_div:
                author_text = profile_div.inner_text().split('\n')[0].strip()
                if author_text and author_text != 'Follow' and author_text != 'AWS Employee':
                    metadata['authors'] = author_text
                    author_found = True
                    debug_print(f"Found author from profile: {author_text}")
        except Exception as e:
            debug_print(f"Error extracting author from profile: {e}")
        
        # Fallback: Look for author in visible text
        if not author_found:
            try:
                body_text = page.inner_text('body')
                title_text = metadata.get('title', '')
                if title_text in body_text:
                    after_title = body_text.split(title_text, 1)[1]
                    lines = [l.strip() for l in after_title.split('\n') if l.strip()]
                    for i, line in enumerate(lines[:5]):
                        if line == 'Follow' and i > 0:
                            potential_author = lines[i-1]
                            words = potential_author.split()
                            if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
                                metadata['authors'] = potential_author
                                author_found = True
                                debug_print(f"Found author from body text: {potential_author}")
                                break
            except Exception as e:
                debug_print(f"Error extracting author from body: {e}")
        
        if not author_found:
            print(f"  No author found, skipping")
            debug_print(f"No author found for {url}, skipping")
            return None
        
        # Extract date - try multiple methods
        date_found = False
        try:
            time_elem = page.query_selector('time')
            if time_elem:
                date_value = time_elem.get_attribute('datetime') or time_elem.inner_text()
                if date_value:
                    metadata['date_published'] = parse_date(date_value)
                    date_found = True
                    debug_print(f"Found date from time element: {metadata['date_published']}")
        except Exception as e:
            debug_print(f"Error extracting date from time element: {e}")
        
        # Fallback: Look for date patterns in meta tags
        if not date_found:
            try:
                meta_selectors = [
                    'meta[property="article:published_time"]',
                    'meta[name="publish-date"]',
                    'meta[name="date"]'
                ]
                for selector in meta_selectors:
                    meta_elem = page.query_selector(selector)
                    if meta_elem:
                        date_value = meta_elem.get_attribute('content')
                        if date_value:
                            metadata['date_published'] = parse_date(date_value)
                            date_found = True
                            debug_print(f"Found date from meta tag {selector}: {metadata['date_published']}")
                            break
            except Exception as e:
                debug_print(f"Error extracting date from meta tags: {e}")
        
        if not date_found:
            metadata['date_published'] = datetime.now(timezone.utc).isoformat()
            debug_print(f"Using current date as fallback: {metadata['date_published']}")
        
        # Extract content
        try:
            article_elem = page.query_selector('article')
            if article_elem:
                metadata['content'] = article_elem.inner_text()[:3000]
                debug_print(f"Extracted {len(metadata['content'])} chars from article")
        except Exception as e:
            debug_print(f"Error extracting content from article: {e}")
        
        if not metadata['content']:
            try:
                main_elem = page.query_selector('main')
                if main_elem:
                    metadata['content'] = main_elem.inner_text()[:3000]
                    debug_print(f"Extracted {len(metadata['content'])} chars from main")
            except Exception as e:
                debug_print(f"Error extracting content from main: {e}")
        
        if not metadata['content']:
            metadata['content'] = f"Learn more about {metadata['title']}. Visit the full article on Builder.AWS."
            debug_print("Using fallback content")
        
        return metadata
        
    except Exception as e:
        print(f"  Error extracting content: {e}")
        debug_print(f"Error in extract_page_content for {url}: {e}")
        import traceback
        debug_print(traceback.format_exc())
        return None


def save_to_dynamodb(table, metadata):
    """Save a post to DynamoDB"""
    try:
        post_id = metadata['url'].split('/')[-1] if not metadata['url'].endswith('/') else metadata['url'].split('/')[-2]
        post_id = f"builder-{post_id}"
        
        debug_print(f"Saving to DynamoDB with post_id: {post_id}")
        
        table.update_item(
            Key={'post_id': post_id},
            UpdateExpression='''
                SET #url = :url,
                    title = :title,
                    authors = :authors,
                    date_published = :date_published,
                    tags = :tags,
                    content = :content,
                    last_crawled = :last_crawled,
                    summary = :empty,
                    label = :empty,
                    label_confidence = :zero,
                    label_generated = :empty,
                    #source = :source
            ''',
            ExpressionAttributeNames={
                '#url': 'url',
                '#source': 'source'
            },
            ExpressionAttributeValues={
                ':url': metadata['url'],
                ':title': metadata['title'],
                ':authors': metadata['authors'],
                ':date_published': metadata['date_published'],
                ':tags': 'End User Computing, Builder.AWS',
                ':content': metadata['content'],
                ':last_crawled': datetime.now(timezone.utc).isoformat(),
                ':empty': '',
                ':zero': 0,
                ':source': metadata['source']
            }
        )
        
        debug_print(f"Successfully saved post_id: {post_id}")
        return True
        
    except Exception as e:
        print(f"  Error saving to DynamoDB: {e}")
        debug_print(f"Error in save_to_dynamodb: {e}")
        import traceback
        debug_print(traceback.format_exc())
        return False


def lambda_handler(event, context):
    """
    Lambda handler for Builder.AWS crawler with Playwright
    
    Parameters:
    - max_posts (optional): Limit number of posts to process
    - debug (optional): Enable debug mode for verbose logging
    - target_url (optional): Process only a specific URL for debugging
    """
    
    global DEBUG_MODE
    
    if not PLAYWRIGHT_AVAILABLE:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Playwright not available'})
        }
    
    # Enable debug mode if requested via event
    if event and event.get('debug'):
        DEBUG_MODE = True
        debug_print("Debug mode enabled via event parameter")
    
    print("Starting Builder.AWS Playwright Crawler")
    debug_print(f"Environment: TABLE_NAME={TABLE_NAME}")
    debug_print(f"Event parameters: {json.dumps(event) if event else 'None'}")
    
    max_posts = event.get('max_posts') if event else None
    target_url = event.get('target_url') if event else None
    table = dynamodb.Table(TABLE_NAME)
    
    posts_processed = 0
    posts_updated = 0
    posts_skipped = 0
    
    try:
        # If target_url is provided, process only that URL
        if target_url:
            debug_print(f"Processing single target URL: {target_url}")
            all_urls = [(target_url, '')]
        else:
            # Get sitemaps
            sitemaps = get_article_sitemaps()
            print(f"Found {len(sitemaps)} article sitemaps")
            
            if not sitemaps:
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': 'No sitemaps found'})
                }
            
            # Collect EUC-related URLs
            all_urls = []
            
            for sitemap_url in sitemaps:
                try:
                    debug_print(f"Processing sitemap: {sitemap_url}")
                    response = requests.get(sitemap_url, timeout=30)
                    response.raise_for_status()
                    
                    root = ET.fromstring(response.text)
                    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                    
                    url_count = 0
                    for url_elem in root.findall('.//ns:url', namespace):
                        loc = url_elem.find('ns:loc', namespace)
                        lastmod = url_elem.find('ns:lastmod', namespace)
                        
                        if loc is not None:
                            url = loc.text
                            title = extract_title_from_slug(url)
                            
                            if is_euc_related(url, title):
                                date = lastmod.text if lastmod is not None else ''
                                all_urls.append((url,