```python
"""
AWS Blog Crawler Lambda Function
Crawls all posts from AWS Desktop and Application Streaming blog
and Builder.AWS.com, storing data in DynamoDB.
"""

import json
import os
import time
from datetime import datetime
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
        # Enhanced logging for debugging
        self.discovered_urls = []
        self.filtered_urls = []
        self.failed_urls = []
    
    def get_page(self, url, retries=3):
        """Fetch a page with retry logic and enhanced logging"""
        print(f"[DEBUG] Attempting to fetch URL: {url}")
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=30)
                print(f"[DEBUG] Response status code: {response.status_code}")
                response.raise_for_status()
                print(f"[DEBUG] Successfully fetched {url} (size: {len(response.text)} bytes)")
                return response.text
            except requests.RequestException as e:
                print(f"[ERROR] Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    print(f"[ERROR] Failed to fetch {url} after {retries} attempts")
                    self.failed_urls.append({'url': url, 'error': str(e)})
                    return None
    
    def extract_post_links(self, html):
        """Extract all blog post links from the listing page with enhanced filtering"""
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        print(f"[DEBUG] Starting link extraction from HTML (size: {len(html)} bytes)")
        
        # Find all article links
        articles = soup.find_all('article') or soup.find_all('div', class_=re.compile(r'post|article|entry'))
        print(f"[DEBUG] Found {len(articles)} article elements")
        
        for article in articles:
            link_tag = article.find('a', href=True)
            if link_tag:
                href = link_tag['href']
                full_url = urljoin(self.base_url, href)
                print(f"[DEBUG] Discovered article link: {full_url}")
                self.discovered_urls.append(full_url)
                # Updated to handle both production and staging domains
                if '/blogs/desktop-and-application-streaming/' in full_url and full_url != self.base_url:
                    # Additional filtering: ensure it's not a category/tag/page URL
                    if not any(exclude in full_url for exclude in ['/category/', '/tag/', '/page/', '/author/']):
                        links.append(full_url)
                        print(f"[DEBUG] Link accepted: {full_url}")
                    else:
                        print(f"[DEBUG] Link filtered (category/tag/page): {full_url}")
                        self.filtered_urls.append({'url': full_url, 'reason': 'category/tag/page'})
                else:
                    print(f"[DEBUG] Link filtered (wrong path or base URL): {full_url}")
                    self.filtered_urls.append({'url': full_url, 'reason': 'wrong path'})
        
        # Alternative: find all links that match the blog pattern
        if not links:
            print(f"[DEBUG] No links found via articles, trying alternative method")
            all_links = soup.find_all('a', href=True)
            print(f"[DEBUG] Found {len(all_links)} total links on page")
            for link in all_links:
                href = link['href']
                if '/blogs/desktop-and-application-streaming/' in href and href != self.base_url:
                    full_url = urljoin(self.base_url, href)
                    print(f"[DEBUG] Alternative method discovered: {full_url}")
                    self.discovered_urls.append(full_url)
                    # Enhanced filtering: ensure it's a blog post URL (has enough path segments and not special pages)
                    if (full_url not in links and 
                        full_url.count('/') > 5 and 
                        not any(exclude in full_url for exclude in ['/category/', '/tag/', '/page/', '/author/'])):
                        links.append(full_url)
                        print(f"[DEBUG] Alternative link accepted: {full_url}")
                    else:
                        print(f"[DEBUG] Alternative link filtered: {full_url}")
                        self.filtered_urls.append({'url': full_url, 'reason': 'alternative filter'})
        
        unique_links = list(set(links))
        print(f"[DEBUG] Returning {len(unique_links)} unique links")
        return unique_links
    
    def find_next_page(self, html):
        """Find the next page link for pagination"""
        soup = BeautifulSoup(html, 'html.parser')
        
        print(f"[DEBUG] Looking for next page link")
        
        # Look for "Older posts" link specifically
        next_link = soup.find('a', string=re.compile(r'.*Older posts.*', re.IGNORECASE))
        if next_link and next_link.get('href'):
            href = next_link['href']
            if '/blogs/desktop-and-application-streaming/' in href:
                next_url = urljoin(self.base_url, href)
                print(f"[DEBUG] Found 'Older posts' link: {next_url}")
                return next_url
        
        # Alternative: look for page/N/ pattern in links
        all_links = soup.find_all('a', href=re.compile(r'/page/\d+/'))
        print(f"[DEBUG] Found {len(all_links)} pagination links")
        if all_links:
            for link in all_links:
                href = link.get('href')
                if '/blogs/desktop-and-application-streaming/' in href:
                    next_url = urljoin(self.base_url, href)
                    print(f"[DEBUG] Found pagination link: {next_url}")
                    return next_url
        
        print(f"[DEBUG] No next page link found")
        return None

    def extract_post_metadata(self, url, html):
        """Extract metadata from a blog post with enhanced logging"""
        print(f"[DEBUG] Extracting metadata from {url}")
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
            print(f"[DEBUG] Extracted title: {metadata['title']}")
        else:
            print(f"[WARNING] No title found for {url}")
        
        # Extract authors - try multiple methods
        
        # Method 1: Look for "by [Author]" pattern in the page text
        page_text = soup.get_text()
        by_match = re.search(r'\bby\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s+on\s+\d', page_text)
        if by_match:
            metadata['authors'] = by_match.group(1).strip()
            print(f"[DEBUG] Extracted author (method 1): {metadata['authors']}")
        
        # Method 2: Check author div/section
        if not metadata['authors']:
            author_section = soup.find('div', class_=re.compile(r'author|byline', re.IGNORECASE))
            if author_section:
                authors = author_section.find_all('a') or [author_section]
                metadata['authors'] = ', '.join([a.get_text(strip=True) for a in authors if a.get_text(strip=True)])
                print(f"[DEBUG] Extracted author (method 2): {metadata['authors']}")
        
        # Method 3: Check meta tags
        if not metadata['authors']:
            author_meta = soup.find('meta', {'name': 'author'}) or soup.find('meta', {'property': 'article:author'})
            if author_meta:
                metadata['authors'] = author_meta.get('content', '')
                print(f"[DEBUG] Extracted author (method 3): {metadata['authors']}")
        
        # Method 4: Look for "About the Author" section (not all posts have this)
        if not metadata['authors']:
            about_author = soup.find(string=re.compile(r'About the Author', re.IGNORECASE))
            if about_author:
                parent = about_author.find_parent()
                if parent:
                    # Look for the next paragraph or table after "About the Author"
                    next_elem = parent.find_next_sibling()
                    if not next_elem:
                        next_elem = parent.find_next(['p', 'table'])
                    
                    if next_elem:
                        text = next_elem.get_text()
                        # Pattern: "Name is a Title..." or "Name has been..."
                        name_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+(?:is|has|works|serves)', text)
                        if name_match:
                            metadata['authors'] = name_match.group(1).strip()
                            print(f"[DEBUG] Extracted author (method 4): {metadata['authors']}")
        
        # Extract published date
        date_tag = soup.find('time', {'datetime': True})
        if date_tag:
            metadata['date_published'] = date_tag.get('datetime', '')
            print(f"[DEBUG] Extracted date (datetime attr): {metadata['date_published']}")
        else:
            date_meta = (soup.find('meta', {'property': 'article:published_time'}) or
                        soup.find('meta', {'name': 'date'}) or
                        soup.find('meta', {'name': 'publish_date'}))
            if date_meta:
                metadata['date_published'] = date_meta.get('content', '')
                print(f"[DEBUG] Extracted date (meta tag): {metadata['date_published']}")
            else:
                print(f"[WARNING] No published date found for {url}")
        
        # Extract updated date
        updated_tag = soup.find('time', {'class': re.compile(r'updated|modified', re.IGNORECASE)})
        if updated_tag:
            metadata['date_updated'] = updated_tag.get('datetime', updated_tag.get_text(strip=True))
            print(f"[DEBUG] Extracted updated date: {metadata['date_updated']}")
        else:
            updated_meta = soup.find('meta', {'property': 'article:modified_time'})
            if updated_meta:
                metadata['date_updated'] = updated_meta.get('content', '')
                print(f"[DEBUG] Extracted updated date (meta): {metadata['date_updated']}")
        
        # Extract tags
        tags_section = soup.find('div', class_=re.compile(r'tags|categories', re.IGNORECASE))
        if tags_section:
            tag_links = tags_section.find_all('a')
            metadata['tags'] = ', '.join([tag.get_text(strip=True) for tag in tag_links])
            print(f"[DEBUG] Extracted tags: {metadata['tags']}")
        else:
            tag_meta = soup.find('meta', {'property': 'article:tag'}) or soup.find('meta', {'name': 'keywords'})
            if tag_meta:
                metadata['tags'] = tag_meta.get('content', '')
                print(f"[DEBUG] Extracted tags (meta): {metadata['tags']}")
        
        # Extract post content (first 3000 characters for summary generation)
        # Look for main content area
        content_area = (
            soup.find('article') or 
            soup.find('div', class_=re.compile(r'content|post-body|entry-content', re.IGNORECASE)) or
            soup.find('main')
        )
        
        if content_area:
            # Remove script, style, and navigation elements
            for element in content_area.find_all(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()
            
            # Get text content
            content_text = content_area.get_text(separator=' ', strip=True)
            # Limit to first 3000 characters
            metadata['content'] = content_text[:3000]
            print(f"[DEBUG] Extracted content: {len(metadata['content'])} characters")
        else:
            print(f"[WARNING] No content area found for {url}")
        
        # Set default author if none found
        if not metadata['authors'] or metadata['authors'].strip() == '':
            metadata['authors'] = 'Multiple Authors'
            print(f"[DEBUG] Using default author: Multiple Authors")
        
        return metadata
    
    def save_to_dynamodb(self, metadata):
        """Save a single post to DynamoDB with enhanced logging"""
        try:
            # Create a unique ID from the URL
            post_id = metadata['url'].split('/')[-2] if metadata['url'].endswith('/') else metadata['url'].split('/')[-1]
            
            print(f"[DEBUG] Attempting to save post_id: {post_id}")
            print(f"[DEBUG] Post title: {metadata['title']}")
            print(f"[DEBUG] Post date: {metadata['date_published']}")
            
            # Check if item exists and if content changed
            content_changed = False
            try:
                response = self.table.get_item(Key={'post_id': post_id})
                if 'Item' in response:
                    print(f"[DEBUG] Post exists in DynamoDB, checking