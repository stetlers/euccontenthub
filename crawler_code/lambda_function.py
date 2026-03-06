```python
"""
AWS Blog Crawler Lambda Function
Crawls all posts from AWS Desktop and Application Streaming blog
and Builder.AWS.com, storing data in DynamoDB.
"""

import json
import os
import time
from datetime import datetime, timezone
from urllib.parse import urljoin
import re
import xml.etree.ElementTree as ET

import boto3
import requests
from bs4 import BeautifulSoup

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Environment detection for staging support
def get_table_suffix():
    """
    Determine table suffix based on environment.
    Returns '-staging' for staging environment, empty string for production.
    """
    environment = os.environ.get('ENVIRONMENT', 'production')
    return '-staging' if environment == 'staging' else ''

def get_base_domain():
    """
    Determine base domain based on environment.
    Returns staging domain for staging environment, production domain otherwise.
    """
    environment = os.environ.get('ENVIRONMENT', 'production')
    if environment == 'staging':
        return 'staging.awseuccontent.com'
    return 'aws.amazon.com'

# Get table name with environment suffix
TABLE_SUFFIX = get_table_suffix()
TABLE_NAME = f"aws-blog-posts{TABLE_SUFFIX}"
BASE_DOMAIN = get_base_domain()

print(f"Environment: {os.environ.get('ENVIRONMENT', 'production')}")
print(f"Using table: {TABLE_NAME}")
print(f"Using domain: {BASE_DOMAIN}")


class AWSBlogCrawler:
    def __init__(self, base_url, table_name):
        self.base_url = base_url
        self.table_name = table_name
        self.table = dynamodb.Table(table_name)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.posts_processed = 0
        self.posts_updated = 0
        self.posts_created = 0
        self.posts_needing_summaries = 0
        self.posts_needing_classification = 0
        self.target_post_found = False
        self.target_post_url = None
        self.target_post_details = {}
        self.filtering_log = []
    
    def get_page(self, url, retries=3):
        """Fetch a page with retry logic"""
        for attempt in range(retries):
            try:
                print(f"[DEBUG] Fetching URL (attempt {attempt + 1}): {url}")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                print(f"[DEBUG] Successfully fetched {url} - Status: {response.status_code}")
                print(f"[DEBUG] Response content length: {len(response.text)} bytes")
                
                # BUGFIX: Log response for March 2, 2026 target post
                if '/2026/03/02/' in url or ('workspaces' in url.lower() and 'g6' in url.lower()):
                    print(f"[DEBUG] *** TARGET POST RESPONSE RECEIVED ***")
                    print(f"[DEBUG] URL: {url}")
                    print(f"[DEBUG] Status: {response.status_code}")
                    print(f"[DEBUG] Content-Type: {response.headers.get('Content-Type')}")
                    print(f"[DEBUG] Content-Length: {response.headers.get('Content-Length')}")
                
                return response.text
            except requests.RequestException as e:
                print(f"[ERROR] Attempt {attempt + 1} failed for {url}: {e}")
                
                # BUGFIX: Enhanced error logging for target post
                if '/2026/03/02/' in url:
                    print(f"[ERROR] *** FAILED TO FETCH TARGET POST (March 2, 2026) ***")
                    print(f"[ERROR] Exception type: {type(e).__name__}")
                    print(f"[ERROR] Exception details: {str(e)}")
                
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    print(f"[ERROR] Failed to fetch {url} after {retries} attempts")
                    return None
    
    def check_staging_table(self, post_url):
        """
        BUGFIX: Check if post exists in DynamoDB staging table
        Returns post data if found, None otherwise
        """
        try:
            # Generate post_id from URL (same logic as save_post)
            post_id = post_url.split('/')[-2] if post_url.endswith('/') else post_url.split('/')[-1]
            
            print(f"[DEBUG] Checking staging table for post_id: {post_id}")
            print(f"[DEBUG] Table name: {self.table_name}")
            
            response = self.table.get_item(Key={'post_id': post_id})
            
            if 'Item' in response:
                item = response['Item']
                print(f"[DEBUG] *** POST FOUND IN STAGING TABLE ***")
                print(f"[DEBUG] post_id: {item.get('post_id')}")
                print(f"[DEBUG] title: {item.get('title')}")
                print(f"[DEBUG] published_date: {item.get('published_date')}")
                print(f"[DEBUG] url: {item.get('url')}")
                print(f"[DEBUG] author: {item.get('author')}")
                print(f"[DEBUG] tags: {item.get('tags')}")
                return item
            else:
                print(f"[DEBUG] Post not found in staging table: {post_id}")
                return None
                
        except Exception as e:
            print(f"[ERROR] Error checking staging table: {e}")
            return None
    
    def log_filtering_decision(self, url, reason, passed=False):
        """
        BUGFIX: Log filtering decisions for debugging
        """
        decision = {
            'url': url,
            'reason': reason,
            'passed': passed,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.filtering_log.append(decision)
        
        status = "PASSED" if passed else "FILTERED OUT"
        print(f"[FILTER] {status}: {url}")
        print(f"[FILTER] Reason: {reason}")
        
        # BUGFIX: Enhanced logging for target post
        if '/2026/03/02/' in url or ('workspaces' in url.lower() and 'g6' in url.lower()):
            print(f"[FILTER] *** FILTERING DECISION FOR TARGET POST ***")
            print(f"[FILTER] Status: {status}")
            print(f"[FILTER] Reason: {reason}")
    
    def extract_post_links(self, html):
        """
        Extract all blog post links from the listing page
        BUGFIX: Enhanced extraction logic to capture posts with various URL structures,
        including 2026+ posts and WorkSpaces Graphics G6 announcements on staging
        """
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        print(f"[DEBUG] ===== STARTING POST LINK EXTRACTION =====")
        print(f"[DEBUG] Starting post link extraction from listing page")
        print(f"[DEBUG] HTML content length: {len(html)} bytes")
        print(f"[DEBUG] Base URL: {self.base_url}")
        
        # BUGFIX: Check if we're accessing the correct URL pattern for staging
        if os.environ.get('ENVIRONMENT') == 'staging':
            print(f"[DEBUG] *** STAGING ENVIRONMENT DETECTED ***")
            print(f"[DEBUG] Ensuring crawler uses staging.awseuccontent.com domain")
            print(f"[DEBUG] Expected base URL: https://staging.awseuccontent.com/blogs/desktop-and-application-streaming")
        
        # BUGFIX: Verify HTML contains blog content
        blog_indicators = [
            'desktop-and-application-streaming',
            'blog-post',
            'article',
            'entry-title',
            'workspaces'
        ]
        html_lower = html.lower()
        found_indicators = [ind for ind in blog_indicators if ind in html_lower]
        print(f"[DEBUG] Found blog indicators in HTML: {found_indicators}")
        if not found_indicators:
            print(f"[WARNING] HTML may not contain expected blog structure")
        
        # BUGFIX: Check for March 2, 2026 date pattern in raw HTML
        if '2026/03/02' in html or '2026-03-02' in html or 'march 2, 2026' in html_lower or 'march 02, 2026' in html_lower:
            print(f"[DEBUG] *** MARCH 2, 2026 DATE PATTERN FOUND IN HTML ***")
        
        # BUGFIX: Check for WorkSpaces G6 content in raw HTML
        if 'workspaces' in html_lower and ('g6' in html_lower or 'graphics g6' in html_lower):
            print(f"[DEBUG] *** WORKSPACES G6 CONTENT FOUND IN HTML ***")
        
        # Method 1: Find all article links
        articles = soup.find_all('article') or soup.find_all('div', class_=re.compile(r'post|article|entry'))
        print(f"[DEBUG] Method 1: Found {len(articles)} article containers")
        
        for idx, article in enumerate(articles):
            link_tag = article.find('a', href=True)
            if link_tag:
                href = link_tag['href']
                full_url = urljoin(self.base_url, href)
                # BUGFIX: Updated to handle both production and staging domains
                if '/blogs/desktop-and-application-streaming/' in full_url and full_url != self.base_url:
                    if full_url not in links:
                        links.append(full_url)
                        print(f"[DEBUG] Method 1: Found post from article container #{idx + 1}: {full_url}")
                        # BUGFIX: Log specific target post if found
                        if '/2026/03/02/' in full_url:
                            print(f"[DEBUG] !!! METHOD 1: MARCH 2, 2026 TARGET POST FOUND: {full_url} !!!")
                            self.target_post_found = True
                            self.target_post_url = full_url
                        elif 'workspaces' in full_url.lower() and 'g6' in full_url.lower():
                            print(f"[DEBUG] !!! METHOD 1: WorkSpaces G6 POST CANDIDATE: {full_url} !!!")
        
        # Method 2: Alternative extraction for links matching blog pattern
        print(f"[DEBUG] Method 2: Extracting from all <a> tags")
        all_links = soup.find_all('a', href=True)
        print(f"[DEBUG] Method 2: Total <a> tags with href found: {len(all_links)}")
        
        for link in all_links:
            href = link['href']
            if '/blogs/desktop-and-application-streaming/' in href and href != self.base_url:
                full_url = urljoin(self.base_url, href)
                path_check = full_url.replace(self.base_url, '').strip('/')
                segments = [s for s in path_check.split('/') if s]
                # BUGFIX: Reduced segment requirement from 5 to 2 for various URL structures
                # This allows capturing posts with different URL patterns on staging
                if len(segments) >= 2 and full_url not in links:
                    has_date = re.search(r'/\d{4}/\d{2}/', full_url)
                    has_slug = re.search(r'/[a-z0-9\-]+/?$', full_url)
                    
                    # BUGFIX: More lenient validation - accept if it looks like a post URL
                    if has_date or has_slug or len(segments) >= 3:
                        links.append(full_url)
                        self.log_filtering_decision(full_url, "Passed path validation (2+ segments, date or slug pattern)", passed=True)
                        
                        # BUGFIX: Log specific target post if found
                        if '/2026/03/02/' in full_url:
                            print(f"[DEBUG] !!! METHOD 2: MARCH 2, 2026 TARGET POST FOUND VIA PATH VALIDATION: {full_url} !!!")
                            self.target_post_found = True
                            self.target_post_url = full_url
                    else:
                        self.log_filtering_decision(full_url, "Failed path validation (insufficient segments)", passed=False)
        
        # Method 3: BUGFIX - Enhanced extraction for date-patterned URLs (including 2026+)
        print(f"[DEBUG] Method 3: Scanning for posts with date patterns in URL (including 2026+)")
        all_date_links = soup.find_all('a', href=re.compile(r'/blogs/desktop-and-application-streaming/\d{4}/\d{2}/'))
        print(f"[DEBUG] Method 3: Found {len(all_date_links)} links with date patterns")
        
        for link in all_date_links:
            href = link.get('href')
            if href:
                full_url = urljoin(self.base_url, href)
                if full_url not in links and full_url != self.base_url:
                    # BUGFIX: More lenient archive detection - only exclude obvious archive pages
                    is_archive = re.search(r'/\d{4}/\d{2}/\d{2}/?$', full_url) or re.search(r'/\d{4}/\d{2}/?$', full_url)
                    
                    if not is_archive:
                        links.append(full_url)
                        self.log_filtering_decision(full_url, "Passed date pattern validation (not archive page)", passed=True)
                        
                        # BUGFIX: Log 2026+ posts explicitly
                        if '/2026/' in full_url:
                            print(f"[DEBUG] !!! METHOD 3: 2026 POST FOUND VIA DATE PATTERN !!! : {full_url}")
                            # BUGFIX: Check if this is the specific March 2, 2026 post
                            if '/2026/03/02/' in full_url:
                                print(f"[DEBUG] !!! METHOD 3: MARCH 2, 2026 TARGET POST FOUND !!! : {full_url}")
                                self.target_post_found = True
                                self.target_post_url = full_url
                    else:
                        self.log_filtering_decision(full_url, "Filtered out as archive page", passed=False)
        
        # Method 4: BUGFIX - Comprehensive scan for all blog links
        print(f"[DEBUG] Method 4: Running comprehensive scan for all blog links")
        all_blog_links = soup.find_all('a', href=re.compile(r'/blogs/desktop-and-application-streaming/'))
        print(f"[DEBUG] Method 4: Found {len(all_blog_links)} total links with blog path")
        
        for link in all_blog_links:
            href = link.get('href')
            if href:
                full_url = urljoin(self.base_url, href)
                # BUGFIX: More lenient exclusion logic
                is_archive = re.search(r'/\d{4}/\d{2}/\d{2}/?$', full_url) or re.search(r'/\d{4}/\d{2}/?$', full_url) or re.search(r'/\d{4}/?$', full_url)
                is_category = re.search(r'/(category|tag|author)/', full_url)
                is_base = full_url.rstrip('/