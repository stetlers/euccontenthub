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

# Get table name with environment suffix
TABLE_SUFFIX = get_table_suffix()
TABLE_NAME = f"aws-blog-posts{TABLE_SUFFIX}"

print(f"Environment: {os.environ.get('ENVIRONMENT', 'production')}")
print(f"Using table: {TABLE_NAME}")


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
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                print(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    print(f"Failed to fetch {url} after {retries} attempts")
                    return None
    
    def extract_post_links_from_rss(self):
        """
        Extract all blog post links from RSS feed.
        This is more reliable than scraping HTML as RSS feeds are structured.
        
        FIX: Enhanced RSS parsing to capture all posts including recent ones.
        Added additional namespace handling and improved link extraction.
        """
        rss_url = f"{self.base_url}feed/"
        print(f"Fetching RSS feed: {rss_url}")
        
        try:
            response = self.session.get(rss_url, timeout=30)
            response.raise_for_status()
            
            print(f"RSS feed response status: {response.status_code}")
            print(f"RSS feed content length: {len(response.text)}")
            
            # Parse RSS/Atom feed
            root = ET.fromstring(response.text)
            
            links = []
            post_dates = {}  # Track dates for debugging
            
            # Try RSS 2.0 format first
            for item in root.findall('.//item'):
                link_elem = item.find('link')
                if link_elem is not None and link_elem.text:
                    url = link_elem.text.strip()
                    if '/blogs/desktop-and-application-streaming/' in url:
                        links.append(url)
                        # Extract date for debugging
                        pub_date = item.find('pubDate')
                        if pub_date is not None and pub_date.text:
                            post_dates[url] = pub_date.text
            
            # Try Atom format if no RSS items found
            if not links:
                namespace = {'atom': 'http://www.w3.org/2005/Atom'}
                for entry in root.findall('.//atom:entry', namespace):
                    link_elem = entry.find('atom:link[@rel="alternate"]', namespace)
                    if link_elem is not None:
                        url = link_elem.get('href', '').strip()
                        if url and '/blogs/desktop-and-application-streaming/' in url:
                            links.append(url)
                            # Extract date for debugging
                            pub_date = entry.find('atom:published', namespace)
                            if pub_date is not None and pub_date.text:
                                post_dates[url] = pub_date.text
            
            # FIX: Additional fallback - check all namespaces
            if not links:
                print("Trying generic XML parsing without namespace...")
                for entry in root.iter():
                    if entry.tag.endswith('entry') or entry.tag.endswith('item'):
                        for child in entry:
                            if child.tag.endswith('link'):
                                url = child.text or child.get('href', '')
                                if url and '/blogs/desktop-and-application-streaming/' in url:
                                    links.append(url.strip())
            
            print(f"Found {len(links)} posts in RSS feed")
            
            # FIX: Debug output for date analysis
            if post_dates:
                print(f"Post dates from RSS feed:")
                for url, date in sorted(post_dates.items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"  {date}: {url}")
            
            return list(set(links))
            
        except Exception as e:
            print(f"Error fetching RSS feed: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return []
    
    def extract_post_links(self, html):
        """
        Extract all blog post links from the listing page
        
        FIX: Enhanced HTML parsing with multiple detection strategies
        to ensure new posts are captured even if RSS feed is delayed.
        """
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        # FIX: Strategy 1 - Find all article links with enhanced selectors
        articles = (
            soup.find_all('article') or 
            soup.find_all('div', class_=re.compile(r'post|article|entry|blog-post', re.IGNORECASE))
        )
        
        for article in articles:
            link_tag = article.find('a', href=True)
            if link_tag:
                href = link_tag['href']
                full_url = urljoin(self.base_url, href)
                if '/blogs/desktop-and-application-streaming/' in full_url and full_url != self.base_url:
                    links.append(full_url)
                    # FIX: Debug logging for new post detection
                    date_elem = article.find('time')
                    if date_elem:
                        print(f"  Found post: {full_url} (date: {date_elem.get('datetime', date_elem.get_text())})")
        
        # FIX: Strategy 2 - Find all links that match the blog pattern with stricter validation
        if not links:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                if '/blogs/desktop-and-application-streaming/' in href and href != self.base_url:
                    full_url = urljoin(self.base_url, href)
                    # FIX: Ensure it's a real post URL (has enough path segments)
                    if full_url not in links and full_url.count('/') > 5:
                        # Additional validation: must end with / or alphanumeric
                        if full_url.endswith('/') or re.search(r'[a-zA-Z0-9]$', full_url):
                            links.append(full_url)
        
        # FIX: Strategy 3 - Look for h2/h3 titles that link to posts
        title_links = soup.find_all(['h2', 'h3'], class_=re.compile(r'title|heading', re.IGNORECASE))
        for title in title_links:
            link_tag = title.find('a', href=True)
            if link_tag:
                href = link_tag['href']
                full_url = urljoin(self.base_url, href)
                if '/blogs/desktop-and-application-streaming/' in full_url and full_url not in links:
                    links.append(full_url)
        
        print(f"Extracted {len(links)} post links from HTML")
        return list(set(links))
    
    def find_next_page(self, html):
        """Find the next page link for pagination"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for "Older posts" link specifically
        next_link = soup.find('a', string=re.compile(r'.*Older posts.*', re.IGNORECASE))
        if next_link and next_link.get('href'):
            href = next_link['href']
            if '/blogs/desktop-and-application-streaming/' in href:
                return urljoin(self.base_url, href)
        
        # Alternative: look for page/N/ pattern in links
        all_links = soup.find_all('a', href=re.compile(r'/page/\d+/'))
        if all_links:
            for link in all_links:
                href = link.get('href')
                if '/blogs/desktop-and-application-streaming/' in href:
                    return urljoin(self.base_url, href)
        
        return None

    def extract_post_metadata(self, url, html):
        """
        Extract metadata from a blog post
        
        FIX: Enhanced date extraction with multiple fallback methods
        to ensure published dates are always captured correctly.
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
        
        # Extract authors - try multiple methods
        
        # Method 1: Look for "by [Author]" pattern in the page text
        page_text = soup.get_text()
        by_match = re.search(r'\bby\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s+on\s+\d', page_text)
        if by_match:
            metadata['authors'] = by_match.group(1).strip()
        
        # Method 2: Check author div/section
        if not metadata['authors']:
            author_section = soup.find('div', class_=re.compile(r'author|byline', re.IGNORECASE))
            if author_section:
                authors = author_section.find_all('a') or [author_section]
                metadata['authors'] = ', '.join([a.get_text(strip=True) for a in authors if a.get_text(strip=True)])
        
        # Method 3: Check meta tags
        if not metadata['authors']:
            author_meta = soup.find('meta', {'name': 'author'}) or soup.find('meta', {'property': 'article:author'})
            if author_meta:
                metadata['authors'] = author_meta.get('content', '')
        
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
        
        # FIX: Enhanced published date extraction with multiple strategies
        # Strategy 1: Look for time tag with datetime attribute
        date_tag = soup.find('time', {'datetime': True})
        if date_tag:
            metadata['date_published'] = date_tag.get('datetime', '')
            print(f"  Found date via <time> tag: {metadata['date_published']}")
        
        # FIX: Strategy 2: Check multiple meta tag variations
        if not metadata['date_published']:
            date_meta = (
                soup.find('meta', {'property': 'article:published_time'}) or
                soup.find('meta', {'name': 'date'}) or
                soup.find('meta', {'name': 'publish_date'}) or
                soup.find('meta', {'name': 'publication_date'}) or
                soup.find('meta', {'property': 'og:published_time'})
            )
            if date_meta:
                metadata['date_published'] = date_meta.get('content', '')
                print(f"  Found date via meta tag: {metadata['date_published']}")
        
        # FIX: Strategy 3: Parse text for "on [Date]" pattern (common in AWS blogs)
        if not metadata['date_published']:
            # Match patterns like "on March 2, 2026" or "on 2 Mar 2026"
            date_pattern = re.search(
                r'\bon\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+[A-Z][a-z]+\s+\d{4})',
                page_text
            )
            if date_pattern:
                date_str = date_pattern.group(1)
                # Try to parse and convert to ISO format
                try:
                    from dateutil import parser
                    parsed_date = parser.parse(date_str)
                    metadata['date_published'] = parsed_date.isoformat()
                    print(f"  Found date via text parsing: {date_str} -> {metadata['date_published']}")
                except:
                    # Keep the original string if parsing fails
                    metadata['date_published'] = date_str
                    print(f"  Found date via text parsing (unparsed): {date_str}")
        
        # FIX: Strategy 4: Look in structured data (JSON-LD)
        if not metadata['date_published']:
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        if 'datePublished' in data:
                            metadata['date_published'] = data['datePublished']
                            print(f"  Found date via JSON-LD: {metadata['date_published']}")
                            break
                        elif '@graph' in data:
                            for item in data['@graph']:
                                if 'datePublished' in item:
                                    metadata['date_published'] = item['datePublished']
                                    print(f"  Found date via JSON-LD @graph: {metadata['date_published']}")