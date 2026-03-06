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
                print(f"[DEBUG] Response content length: {len(response.text)} bytes")
                return response.text
            except requests.RequestException as e:
                print(f"[ERROR] Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    print(f"[ERROR] Failed to fetch {url} after {retries} attempts")
                    return None
    
    def extract_post_links(self, html):
        """
        Extract all blog post links from the listing page
        BUGFIX: Enhanced extraction logic to capture posts with various URL structures,
        including 2026+ posts and WorkSpaces Graphics G6 announcements
        """
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        print(f"[DEBUG] Starting post link extraction from listing page")
        print(f"[DEBUG] HTML content length: {len(html)} bytes")
        
        # Method 1: Find all article links
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
        
        # Method 2: Alternative extraction for links matching blog pattern
        if not links:
            print(f"[DEBUG] No links found in articles, trying alternative extraction")
            all_links = soup.find_all('a', href=True)
            print(f"[DEBUG] Total <a> tags with href found: {len(all_links)}")
            for link in all_links:
                href = link['href']
                if '/blogs/desktop-and-application-streaming/' in href and href != self.base_url:
                    full_url = urljoin(self.base_url, href)
                    path_check = full_url.replace(self.base_url, '').strip('/')
                    segments = [s for s in path_check.split('/') if s]
                    # BUGFIX: Reduced segment requirement from 5 to 3 for various URL structures
                    if len(segments) >= 3 and full_url not in links:
                        has_date = re.search(r'/\d{4}/\d{2}/', full_url)
                        has_slug = re.search(r'/[a-z0-9\-]+/?$', full_url)
                        if has_date or has_slug:
                            links.append(full_url)
                            print(f"[DEBUG] Added post via path validation: {full_url}")
        
        # Method 3: BUGFIX - Enhanced extraction for date-patterned URLs (including 2026+)
        print(f"[DEBUG] Scanning for posts with date patterns in URL (including 2026+)")
        all_date_links = soup.find_all('a', href=re.compile(r'/blogs/desktop-and-application-streaming/\d{4}/\d{2}/'))
        print(f"[DEBUG] Found {len(all_date_links)} links with date patterns")
        for link in all_date_links:
            href = link.get('href')
            if href:
                full_url = urljoin(self.base_url, href)
                if full_url not in links and full_url != self.base_url:
                    # Ensure it's not a date archive page
                    if not re.search(r'/\d{4}/\d{2}/\d{2}/?$', full_url) and not re.search(r'/\d{4}/\d{2}/?$', full_url):
                        links.append(full_url)
                        # BUGFIX: Log 2026+ posts explicitly
                        if '/2026/' in full_url:
                            print(f"[DEBUG] !!! 2026 POST FOUND VIA DATE PATTERN !!! : {full_url}")
                        else:
                            print(f"[DEBUG] Added post via date pattern: {full_url}")
        
        # Method 4: BUGFIX - Comprehensive scan for all blog links
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
                        # BUGFIX: Log 2026+ posts explicitly
                        if '/2026/' in full_url:
                            print(f"[DEBUG] !!! 2026 POST FOUND VIA COMPREHENSIVE SCAN !!! : {full_url}")
                        else:
                            print(f"[DEBUG] Added post via comprehensive scan: {full_url}")
        
        # Method 5: BUGFIX - Special handling for specific target post (WorkSpaces Graphics G6)
        target_post_patterns = [
            re.compile(r'amazon.*workspaces.*graphics.*g6', re.IGNORECASE),
            re.compile(r'workspaces.*g6.*bundles', re.IGNORECASE),
            re.compile(r'graphics.*g6.*gr6.*g6f', re.IGNORECASE),
        ]
        print(f"[DEBUG] Checking for target post patterns: 'Amazon WorkSpaces Graphics G6'")
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True)
            href = link.get('href')
            title_attr = link.get('title', '')
            
            for pattern in target_post_patterns:
                if pattern.search(link_text) or pattern.search(href) or pattern.search(title_attr):
                    full_url = urljoin(self.base_url, href)
                    if full_url not in links and '/blogs/desktop-and-application-streaming/' in full_url:
                        links.append(full_url)
                        print(f"[DEBUG] !!! FOUND TARGET POST (WorkSpaces G6) !!! : {full_url}")
                        print(f"[DEBUG] Link text: {link_text}")
                        print(f"[DEBUG] Link href: {href}")
                        print(f"[DEBUG] Link title: {title_attr}")
                        break
        
        # Method 6: BUGFIX - Look in RSS/Sitemap-like structures if present
        print(f"[DEBUG] Checking for RSS/Sitemap links")
        rss_links = soup.find_all('link', {'type': 'application/rss+xml'})
        for rss_link in rss_links:
            rss_href = rss_link.get('href')
            if rss_href:
                print(f"[DEBUG] Found RSS feed: {rss_href}")
        
        # Debug logging for all environments
        print(f"[DEBUG] ===== EXTRACTION SUMMARY =====")
        print(f"[DEBUG] Total extracted {len(links)} unique post links from listing page")
        print(f"[DEBUG] Environment: {os.environ.get('ENVIRONMENT', 'production')}")
        print(f"[DEBUG] Base URL: {self.base_url}")
        
        # Enhanced logging for staging and debug
        if os.environ.get('ENVIRONMENT') == 'staging' or os.environ.get('DEBUG_MODE') == 'true':
            print(f"[DEBUG] FULL LINK LIST:")
            for i, link in enumerate(links, 1):
                print(f"[DEBUG]   {i}. {link}")
                # Check if this is a 2026 post
                if '/2026/' in link:
                    print(f"[DEBUG]      ^^ 2026 POST DETECTED ^^")
        
        # BUGFIX: Count and report 2026+ posts
        future_posts = [link for link in links if '/2026/' in link]
        if future_posts:
            print(f"[DEBUG] !!! FOUND {len(future_posts)} POST(S) FROM 2026+ !!!")
            for fp in future_posts:
                print(f"[DEBUG]   - {fp}")
        
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
            print(f"[DEBUG] parse_date_string: Empty date string provided")
            return None
        
        # List of date format patterns to try
        date_formats = [
            '%Y-%m-%dT%H:%M:%SZ',           # ISO 8601 with Z
            '%Y-%m-%dT%H:%M:%S%z',          # ISO 8601 with timezone
            '%Y-%m-%dT%H:%M:%S.%fZ',        # ISO 8601 with milliseconds
            '%Y-%m-%dT%H:%M:%S.%f%z',       # ISO 8601 with milliseconds and timezone
            '%Y-%m-%d',                      # Simple date
            '%B %d, %Y',                     # March 2, 2026
            '%b %d, %Y',                     # Mar 2, 2026
            '%d %B %Y',                      # 2 March 2026
            '%d %b %Y',                      # 2 Mar 2026
            '%m/%d/%Y',                      # 03/02/2026
            '%Y/%m/%d',                      # 2026/03/02
            '%Y-%m-%d %H:%M:%S',            # 2026-03-02 10:30:00
            '%a, %d %b %Y %H:%M:%S %z',     # Mon, 02 Mar 2026 10:30:00 +