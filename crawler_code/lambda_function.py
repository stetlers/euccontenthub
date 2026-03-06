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
    
    def get_page(self, url, retries=3):
        """Fetch a page with retry logic"""
        for attempt in range(retries):
            try:
                print(f"[DEBUG] Fetching URL (attempt {attempt + 1}): {url}")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                print(f"[DEBUG] Successfully fetched {url} - Status: {response.status_code}")
                return response.text
            except requests.RequestException as e:
                print(f"[ERROR] Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    print(f"[ERROR] Failed to fetch {url} after {retries} attempts")
                    return None
    
    def extract_post_links(self, html):
        """Extract all blog post links from the listing page"""
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        print(f"[DEBUG] Starting post link extraction from listing page")
        
        # Find all article links
        articles = soup.find_all('article') or soup.find_all('div', class_=re.compile(r'post|article|entry'))
        print(f"[DEBUG] Found {len(articles)} article containers")
        
        for article in articles:
            link_tag = article.find('a', href=True)
            if link_tag:
                href = link_tag['href']
                full_url = urljoin(self.base_url, href)
                # Updated to handle both production and staging domains
                if '/blogs/desktop-and-application-streaming/' in full_url and full_url != self.base_url:
                    links.append(full_url)
                    print(f"[DEBUG] Found post from article container: {full_url}")
        
        # Alternative: find all links that match the blog pattern
        if not links:
            print(f"[DEBUG] No links found in articles, trying alternative extraction")
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                if '/blogs/desktop-and-application-streaming/' in href and href != self.base_url:
                    full_url = urljoin(self.base_url, href)
                    # Enhanced check: must have path segments after blog base path
                    # Check that it's not a category/tag page and has actual content path
                    path_check = full_url.replace(self.base_url, '').strip('/')
                    segments = [s for s in path_check.split('/') if s]
                    # BUGFIX: Reduced from 5 to 3 segments to capture posts with various URL structures
                    # This ensures posts like /blogs/desktop-and-application-streaming/2026/03/new-post/ are detected
                    # Minimum structure: blogs/desktop-and-application-streaming/slug or blogs/desktop-and-application-streaming/year/...
                    if len(segments) >= 3 and full_url not in links:
                        # Additional validation: check if it contains a date pattern (YYYY/MM or YYYY/MM/DD) OR valid slug
                        has_date = re.search(r'/\d{4}/\d{2}/', full_url)
                        has_slug = re.search(r'/[a-z0-9\-]+/?$', full_url)
                        if has_date or has_slug:
                            links.append(full_url)
                            print(f"[DEBUG] Added post via path validation: {full_url}")
        
        # BUGFIX: Enhanced extraction method - look for links with date patterns in href
        # This catches posts that may be formatted differently in the HTML, including 2026 dates
        print(f"[DEBUG] Scanning for posts with date patterns in URL")
        all_date_links = soup.find_all('a', href=re.compile(r'/blogs/desktop-and-application-streaming/\d{4}/\d{2}/'))
        print(f"[DEBUG] Found {len(all_date_links)} links with date patterns")
        for link in all_date_links:
            href = link.get('href')
            if href:
                full_url = urljoin(self.base_url, href)
                if full_url not in links and full_url != self.base_url:
                    # Ensure it's not a date archive page (which would end in /YYYY/MM/ or /YYYY/MM/DD/)
                    if not re.search(r'/\d{4}/\d{2}/\d{2}/?$', full_url) and not re.search(r'/\d{4}/\d{2}/?$', full_url):
                        links.append(full_url)
                        print(f"[DEBUG] Added post via date pattern: {full_url}")
        
        # BUGFIX: Additional comprehensive extraction - look for any link containing blog path with content
        # This is a catch-all to ensure we don't miss posts with non-standard formatting
        print(f"[DEBUG] Running comprehensive scan for all blog links")
        all_blog_links = soup.find_all('a', href=re.compile(r'/blogs/desktop-and-application-streaming/'))
        print(f"[DEBUG] Found {len(all_blog_links)} total links with blog path")
        for link in all_blog_links:
            href = link.get('href')
            if href:
                full_url = urljoin(self.base_url, href)
                # Exclude archive pages, category pages, and base blog URL
                is_archive = re.search(r'/\d{4}/\d{2}/\d{2}/?$', full_url) or re.search(r'/\d{4}/\d{2}/?$', full_url) or re.search(r'/\d{4}/?$', full_url)
                is_category = re.search(r'/(category|tag|author)/', full_url)
                is_base = full_url.rstrip('/') == self.base_url.rstrip('/')
                
                if not is_archive and not is_category and not is_base and full_url not in links:
                    # Must have at least one segment after the base blog path
                    path_after_blog = full_url.split('/blogs/desktop-and-application-streaming/')[-1].strip('/')
                    if path_after_blog and len(path_after_blog) > 0:
                        links.append(full_url)
                        print(f"[DEBUG] Added post via comprehensive scan: {full_url}")
        
        # Debug logging for all environments
        print(f"[DEBUG] Total extracted {len(links)} unique post links from listing page")
        if os.environ.get('ENVIRONMENT') == 'staging':
            print(f"[DEBUG] STAGING MODE - Full link list:")
            for i, link in enumerate(links, 1):
                print(f"[DEBUG]   {i}. {link}")
        
        return list(set(links))
    
    def find_next_page(self, html):
        """Find the next page link for pagination"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for "Older posts" link specifically
        next_link = soup.find('a', string=re.compile(r'.*Older posts.*', re.IGNORECASE))
        if next_link and next_link.get('href'):
            href = next_link['href']
            if '/blogs/desktop-and-application-streaming/' in href:
                full_url = urljoin(self.base_url, href)
                print(f"[DEBUG] Found next page via 'Older posts' link: {full_url}")
                return full_url
        
        # Alternative: look for page/N/ pattern in links
        all_links = soup.find_all('a', href=re.compile(r'/page/\d+/'))
        if all_links:
            for link in all_links:
                href = link.get('href')
                if '/blogs/desktop-and-application-streaming/' in href:
                    full_url = urljoin(self.base_url, href)
                    print(f"[DEBUG] Found next page via page number: {full_url}")
                    return full_url
        
        # Additional pattern: look for pagination navigation
        pagination = soup.find('nav', class_=re.compile(r'pagination|page-nav', re.IGNORECASE))
        if pagination:
            next_links = pagination.find_all('a', string=re.compile(r'next|older|→|»', re.IGNORECASE))
            for link in next_links:
                href = link.get('href')
                if href and '/blogs/desktop-and-application-streaming/' in href:
                    full_url = urljoin(self.base_url, href)
                    print(f"[DEBUG] Found next page via pagination nav: {full_url}")
                    return full_url
        
        print(f"[DEBUG] No next page found - reached end of pagination")
        return None

    def parse_date_string(self, date_str):
        """
        Parse various date string formats into ISO 8601 format.
        Returns None if parsing fails.
        BUGFIX: Enhanced to handle more date formats and future dates (2026+)
        """
        if not date_str:
            return None
        
        # List of date format patterns to try
        date_formats = [
            '%Y-%m-%dT%H:%M:%SZ',           # ISO 8601 with Z
            '%Y-%m-%dT%H:%M:%S%z',          # ISO 8601 with timezone
            '%Y-%m-%dT%H:%M:%S.%fZ',        # ISO 8601 with milliseconds
            '%Y-%m-%d',                      # Simple date
            '%B %d, %Y',                     # March 2, 2026
            '%b %d, %Y',                     # Mar 2, 2026
            '%d %B %Y',                      # 2 March 2026
            '%d %b %Y',                      # 2 Mar 2026
            '%m/%d/%Y',                      # 03/02/2026
            '%Y/%m/%d',                      # 2026/03/02
            '%Y-%m-%d %H:%M:%S',            # 2026-03-02 10:30:00
            '%a, %d %b %Y %H:%M:%S %z',     # Mon, 02 Mar 2026 10:30:00 +0000
            '%a, %d %b %Y %H:%M:%S %Z',     # Mon, 02 Mar 2026 10:30:00 GMT
        ]
        
        # Clean the date string
        date_str = date_str.strip()
        
        # Try each format
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                # Convert to ISO 8601 format with UTC timezone
                iso_date = parsed_date.strftime('%Y-%m-%dT%H:%M:%SZ')
                print(f"[DEBUG] Successfully parsed date '{date_str}' as '{iso_date}' using format '{fmt}'")
                return iso_date
            except ValueError:
                continue
        
        print(f"[WARNING] Could not parse date string: '{date_str}'")
        return None

    def extract_post_metadata(self, url, html):
        """
        Extract metadata from a blog post
        BUGFIX: Enhanced date extraction with comprehensive logging for debugging
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        metadata = {
            'url': url,
            'title': '',
            'authors': '',
            'date_published': '',
            'date_updated': '',
            'tags': '',
            'content': ''
        }
        
        # Extract title
        title_tag = soup.find('h1') or soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text(strip=True)
            metadata['title'] = metadata['title'].split('|')[0].strip()
        
        print(f"[DEBUG] ========== Extracting metadata for: {metadata['title']} ==========")
        print(f"[DEBUG] URL: {url}")
        
        # Extract authors - try multiple methods
        
        # Method 1: Look for "by [Author]" pattern in the page text
        page_text = soup.get_text()
        by_match = re.search(r'\bby\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s+on\s+\d', page_text)
        if by_match:
            metadata['authors'] = by_match.group(1).strip()
            print(f"[DEBUG] Authors extracted via 'by...on' pattern: {metadata['authors']}")
        
        # Method 2: Check author div/section
        if not metadata['authors']:
            author_section = soup.find('div', class_=re.compile(r'author|byline', re.IGNORECASE))
            if author_section:
                authors = author_section.find_all('a') or [author_section]
                metadata['authors'] = ', '.join([a.get_text(strip=True) for a in authors if a.get_text(strip=True)])
                print(f"[DEBUG] Authors extracted from author section: {metadata['authors']}")
        
        # Method 3: Check meta tags
        if not metadata['authors']:
            author_meta = soup.find('meta', {'name': 'author'}) or soup.find('meta', {'property': 'article:author'})
            if author_meta:
                metadata['authors'] = author_meta.get('content', '')
                print(f"[DEBUG] Authors extracted from meta tag: {metadata['authors']}")
        
        # Method 4: Look for "About the Author" section (not all