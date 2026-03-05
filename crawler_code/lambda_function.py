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
    
    def extract_post_links(self, html):
        """Extract all blog post links from the listing page"""
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        # Find all article links
        articles = soup.find_all('article') or soup.find_all('div', class_=re.compile(r'post|article|entry'))
        
        for article in articles:
            link_tag = article.find('a', href=True)
            if link_tag:
                href = link_tag['href']
                full_url = urljoin(self.base_url, href)
                # Updated to handle both production and staging domains
                if '/blogs/desktop-and-application-streaming/' in full_url and full_url != self.base_url:
                    links.append(full_url)
        
        # Alternative: find all links that match the blog pattern
        if not links:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                if '/blogs/desktop-and-application-streaming/' in href and href != self.base_url:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in links and full_url.count('/') > 5:
                        links.append(full_url)
        
        # ENHANCED: Look for links in common blog list structures
        # Check for list items, card structures, and grid layouts
        post_containers = soup.find_all(['li', 'div'], class_=re.compile(r'(post|blog|article|card|item)[-_]?(list|grid|container)?', re.IGNORECASE))
        for container in post_containers:
            link_tag = container.find('a', href=True)
            if link_tag:
                href = link_tag['href']
                if '/blogs/desktop-and-application-streaming/' in href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in links and full_url != self.base_url and full_url.count('/') > 5:
                        # Ensure it's a valid blog post URL (not category/tag/page)
                        if not any(x in full_url for x in ['/category/', '/tag/', '/page/', '/author/']):
                            links.append(full_url)
        
        print(f"  Extracted {len(set(links))} unique post links")
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
        
        # ENHANCED: Look for various pagination patterns
        # Method 1: Look for "Next" or "Older" links
        pagination_texts = ['next', 'older', 'previous posts', 'more posts', '→', '»']
        for text in pagination_texts:
            next_link = soup.find('a', string=re.compile(re.escape(text), re.IGNORECASE))
            if next_link and next_link.get('href'):
                href = next_link['href']
                if '/blogs/desktop-and-application-streaming/' in href:
                    return urljoin(self.base_url, href)
        
        # Method 2: Look for page/N/ pattern in links
        all_links = soup.find_all('a', href=re.compile(r'/page/\d+/'))
        if all_links:
            for link in all_links:
                href = link.get('href')
                if '/blogs/desktop-and-application-streaming/' in href:
                    return urljoin(self.base_url, href)
        
        # Method 3: Look for pagination nav elements
        pagination_nav = soup.find(['nav', 'div'], class_=re.compile(r'paginat', re.IGNORECASE))
        if pagination_nav:
            next_link = pagination_nav.find('a', class_=re.compile(r'next', re.IGNORECASE))
            if next_link and next_link.get('href'):
                href = next_link['href']
                return urljoin(self.base_url, href)
        
        return None

    def extract_post_metadata(self, url, html):
        """Extract metadata from a blog post"""
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
        
        # ENHANCED: Extract authors - try multiple methods with improved patterns
        
        # Method 1: Look for "by [Author]" pattern in the page text (improved regex)
        page_text = soup.get_text()
        by_match = re.search(r'\bby\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4})(?:\s+(?:on|and|,))', page_text)
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
        
        # Method 4: Look for "About the Author" section
        if not metadata['authors']:
            about_author = soup.find(string=re.compile(r'About the Author', re.IGNORECASE))
            if about_author:
                parent = about_author.find_parent()
                if parent:
                    next_elem = parent.find_next_sibling()
                    if not next_elem:
                        next_elem = parent.find_next(['p', 'table'])
                    
                    if next_elem:
                        text = next_elem.get_text()
                        name_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+(?:is|has|works|serves)', text)
                        if name_match:
                            metadata['authors'] = name_match.group(1).strip()
        
        # ENHANCED: Extract published date with improved parsing
        date_tag = soup.find('time', {'datetime': True})
        if date_tag:
            metadata['date_published'] = date_tag.get('datetime', '')
        else:
            # Try multiple meta tag patterns
            date_meta = (soup.find('meta', {'property': 'article:published_time'}) or
                        soup.find('meta', {'name': 'date'}) or
                        soup.find('meta', {'name': 'publish_date'}) or
                        soup.find('meta', {'property': 'og:published_time'}))
            if date_meta:
                metadata['date_published'] = date_meta.get('content', '')
            else:
                # ENHANCED: Look for date patterns in the page text
                # Pattern: "March 2, 2026" or "2026-03-02" or "Mar 2, 2026"
                date_patterns = [
                    r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
                    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}',
                    r'\d{4}-\d{2}-\d{2}',
                    r'\d{1,2}/\d{1,2}/\d{4}'
                ]
                
                for pattern in date_patterns:
                    date_match = re.search(pattern, page_text)
                    if date_match:
                        try:
                            date_str = date_match.group(0)
                            # Try to parse and normalize the date
                            from dateutil import parser
                            parsed_date = parser.parse(date_str)
                            metadata['date_published'] = parsed_date.isoformat()
                            print(f"  Extracted date from text: {date_str} -> {metadata['date_published']}")
                            break
                        except:
                            # If parsing fails, just use the string as-is
                            metadata['date_published'] = date_match.group(0)
                            break
        
        # Extract updated date
        updated_tag = soup.find('time', {'class': re.compile(r'updated|modified', re.IGNORECASE)})
        if updated_tag:
            metadata['date_updated'] = updated_tag.get('datetime', updated_tag.get_text(strip=True))
        else:
            updated_meta = soup.find('meta', {'property': 'article:modified_time'})
            if updated_meta:
                metadata['date_updated'] = updated_meta.get('content', '')
        
        # ENHANCED: Extract tags with additional methods
        tags_section = soup.find('div', class_=re.compile(r'tags|categories', re.IGNORECASE))
        if tags_section:
            tag_links = tags_section.find_all('a')
            metadata['tags'] = ', '.join([tag.get_text(strip=True) for tag in tag_links])
        else:
            tag_meta = soup.find('meta', {'property': 'article:tag'}) or soup.find('meta', {'name': 'keywords'})
            if tag_meta:
                metadata['tags'] = tag_meta.get('content', '')
        
        # ENHANCED: Look for tags in common tag container patterns
        if not metadata['tags']:
            tag_containers = soup.find_all(['div', 'section', 'ul'], class_=re.compile(r'tag|label|topic|keyword', re.IGNORECASE))
            for container in tag_containers:
                tag_links = container.find_all('a')
                if tag_links:
                    metadata['tags'] = ', '.join([tag.get_text(strip=True) for tag in tag_links])
                    break
        
        # ENHANCED: Extract post content (first 3000 characters for summary generation)
        # Look for main content area with improved selector
        content_area = (
            soup.find('article') or 
            soup.find('div', class_=re.compile(r'content|post-body|entry-content|post-content|article-body', re.IGNORECASE)) or
            soup.find('main') or
            soup.find('div', id=re.compile(r'content|post|article', re.IGNORECASE))
        )
        
        if content_area:
            # Remove script, style, navigation, and other non-content elements
            for element in content_area.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']):
                element.decompose()
            
            # Get text content
            content_text = content_area.get_text(separator=' ', strip=True)
            # Limit to first 3000 characters
            metadata['content'] = content_text[:3000]
        else:
            # Fallback: get all paragraph text if no content area found
            paragraphs = soup.find_all('p')
            if paragraphs:
                content_text = ' '.join([p.get_text(strip=True) for p in paragraphs[:10]])
                metadata['content'] = content_text[:3000]
        
        # Set default author if none found
        if not metadata['authors'] or metadata['authors'].strip() == '':
            metadata['authors'] = 'Multiple Authors'
        
        # Log extracted metadata for debugging
        print(f"  Title: {metadata['title'][:60]}...")
        print(f"  Authors: {metadata['authors']}")
        print(f"  Date: {metadata['date_published']}")
        print(f"  Content length: {len(metadata['content'])} chars")
        
        return metadata
    
    def