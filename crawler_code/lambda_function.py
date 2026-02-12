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
        
        # Extract published date
        date_tag = soup.find('time', {'datetime': True})
        if date_tag:
            metadata['date_published'] = date_tag.get('datetime', '')
        else:
            date_meta = (soup.find('meta', {'property': 'article:published_time'}) or
                        soup.find('meta', {'name': 'date'}) or
                        soup.find('meta', {'name': 'publish_date'}))
            if date_meta:
                metadata['date_published'] = date_meta.get('content', '')
        
        # Extract updated date
        updated_tag = soup.find('time', {'class': re.compile(r'updated|modified', re.IGNORECASE)})
        if updated_tag:
            metadata['date_updated'] = updated_tag.get('datetime', updated_tag.get_text(strip=True))
        else:
            updated_meta = soup.find('meta', {'property': 'article:modified_time'})
            if updated_meta:
                metadata['date_updated'] = updated_meta.get('content', '')
        
        # Extract tags
        tags_section = soup.find('div', class_=re.compile(r'tags|categories', re.IGNORECASE))
        if tags_section:
            tag_links = tags_section.find_all('a')
            metadata['tags'] = ', '.join([tag.get_text(strip=True) for tag in tag_links])
        else:
            tag_meta = soup.find('meta', {'property': 'article:tag'}) or soup.find('meta', {'name': 'keywords'})
            if tag_meta:
                metadata['tags'] = tag_meta.get('content', '')
        
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
        
        # Set default author if none found
        if not metadata['authors'] or metadata['authors'].strip() == '':
            metadata['authors'] = 'Multiple Authors'
        
        return metadata
    
    def save_to_dynamodb(self, metadata):
        """Save a single post to DynamoDB"""
        try:
            # Create a unique ID from the URL
            post_id = metadata['url'].split('/')[-2] if metadata['url'].endswith('/') else metadata['url'].split('/')[-1]
            
            # Check if item exists and if content changed
            content_changed = False
            try:
                response = self.table.get_item(Key={'post_id': post_id})
                if 'Item' in response:
                    self.posts_updated += 1
                    existing_item = response['Item']
                    
                    # Check if content changed
                    old_content = existing_item.get('content', '')
                    new_content = metadata['content']
                    if old_content != new_content:
                        content_changed = True
                        print(f"  Content changed - will regenerate summary")
                else:
                    self.posts_created += 1
                    content_changed = True  # New post needs summary
            except:
                self.posts_created += 1
                content_changed = True  # New post needs summary
            
            # Build update expression based on whether content changed
            if content_changed:
                # Clear summary AND label if content changed so they get regenerated
                update_expression = '''
                    SET #url = :url,
                        title = :title,
                        authors = :authors,
                        date_published = :date_published,
                        date_updated = :date_updated,
                        tags = :tags,
                        content = :content,
                        last_crawled = :last_crawled,
                        summary = :empty,
                        label = :empty,
                        label_confidence = :zero,
                        label_generated = :empty,
                        #source = :source
                '''
                expression_values = {
                    ':url': metadata['url'],
                    ':title': metadata['title'],
                    ':authors': metadata['authors'],
                    ':date_published': metadata['date_published'],
                    ':date_updated': metadata['date_updated'],
                    ':tags': metadata['tags'],
                    ':content': metadata['content'],
                    ':last_crawled': datetime.utcnow().isoformat(),
                    ':empty': '',
                    ':zero': 0,
                    ':source': 'aws-blog'
                }
                self.posts_needing_summaries += 1
                self.posts_needing_classification += 1
            else:
                # Keep existing summary if content unchanged
                update_expression = '''
                    SET #url = :url,
                        title = :title,
                        authors = :authors,
                        date_published = :date_published,
                        date_updated = :date_updated,
                        tags = :tags,
                        content = :content,
                        last_crawled = :last_crawled,
                        #source = :source
                '''
                expression_values = {
                    ':url': metadata['url'],
                    ':title': metadata['title'],
                    ':authors': metadata['authors'],
                    ':date_published': metadata['date_published'],
                    ':date_updated': metadata['date_updated'],
                    ':tags': metadata['tags'],
                    ':content': metadata['content'],
                    ':last_crawled': datetime.utcnow().isoformat(),
                    ':source': 'aws-blog'
                }
            
            # Use update_item to preserve voting fields
            self.table.update_item(
                Key={'post_id': post_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames={
                    '#url': 'url',  # 'url' is a reserved word in DynamoDB
                    '#source': 'source'
                },
                ExpressionAttributeValues=expression_values
            )
            
            self.posts_processed += 1
            return True
            
        except Exception as e:
            print(f"Error saving to DynamoDB: {e}")
            return False
    
    def crawl_all_posts(self, max_pages=None):
        """Crawl all blog posts from all pages"""
        print(f"Starting crawl of {self.base_url}")
        current_url = self.base_url
        page_num = 1
        all_post_urls = set()
        visited_pages = set()
        
        # Step 1: Collect all post URLs from all listing pages
        while current_url and current_url not in visited_pages:
            if max_pages and page_num > max_pages:
                print(f"Reached max pages limit: {max_pages}")
                break
                
            print(f"Fetching listing page {page_num}: {current_url}")
            visited_pages.add(current_url)
            html = self.get_page(current_url)
            
            if not html:
                break
            
            # Extract post links from this page
            post_links = self.extract_post_links(html)
            print(f"Found {len(post_links)} posts on page {page_num}")
            
            # Only add valid blog post URLs
            for link in post_links:
                if link not in visited_pages and '/blogs/desktop-and-application-streaming/' in link:
                    if '/category/' not in link and '/tag/' not in link and link.count('/') > 5:
                        all_post_urls.add(link)
            
            # Find next page
            next_url = self.find_next_page(html)
            if next_url and next_url != current_url and next_url not in visited_pages:
                current_url = next_url
                page_num += 1
                time.sleep(1)
            else:
                print(f"No more pages found. Stopping pagination.")
                break
        
        print(f"\n{'='*60}")
        print(f"Total unique posts found: {len(all_post_urls)}")
        print(f"{'='*60}\n")
        
        # Step 2: Extract metadata from each post and save to DynamoDB
        for idx, post_url in enumerate(sorted(all_post_urls), 1):
            print(f"[{idx}/{len(all_post_urls)}] Processing: {post_url}")
            html = self.get_page(post_url)
            
            if html:
                metadata = self.extract_post_metadata(post_url, html)
                if self.save_to_dynamodb(metadata):
                    print(f"  ✓ Saved: {metadata['title'][:60]}...")
                else:
                    print(f"  ✗ Failed to save")
            else:
                print(f"  ✗ Failed to fetch post")
            
            time.sleep(0.5)
        
        return {
            'total_posts': len(all_post_urls),
            'posts_processed': self.posts_processed,
            'posts_created': self.posts_created,
            'posts_updated': self.posts_updated,
            'posts_needing_summaries': self.posts_needing_summaries
        }


class BuilderAWSCrawler:
    """Crawler for builder.aws.com using sitemap metadata"""
    
    def __init__(self, table_name):
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
        self.changed_post_ids = []  # Track post IDs that changed (for Selenium crawler)
    
    def get_article_sitemaps(self):
        """Get list of article sitemap URLs from sitemap index"""
        sitemap_index_url = 'https://builder.aws.com/sitemaps/sitemap.xml'
        
        try:
            response = self.session.get(sitemap_index_url, timeout=30)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # This is a urlset, not a sitemap index
            # Get all URLs that are article sitemaps
            article_sitemaps = []
            for url_elem in root.findall('.//ns:url', namespace):
                loc = url_elem.find('ns:loc', namespace)
                if loc is not None and '/sitemaps/articles/' in loc.text:
                    article_sitemaps.append(loc.text)
            
            print(f"Found {len(article_sitemaps)} article sitemaps")
            return article_sitemaps
            
        except Exception as e:
            print(f"Error fetching sitemap index: {e}")
            return []
    
    def extract_title_from_slug(self, url):
        """Extract title from URL slug"""
        # Get the last part of the URL (the slug)
        slug = url.rstrip('/').split('/')[-1]
        
        # Convert slug to title
        # "getting-started-setting-up-appstream" → "Getting Started Setting Up AppStream"
        words = slug.split('-')
        
        # Capitalize each word, but handle special cases
        title_words = []
        for i, word in enumerate(words):
            # Keep acronyms uppercase if they're already uppercase
            if word.isupper() and len(word) <= 4:
                title_words.append(word)
            # Special handling for common tech terms (case-insensitive match)
            elif word.lower() in ['ai', 'ml', 'api', 'aws', 'iam', 'ec2', 's3', 'vpc', 'euc', 'vdi']:
                title_words.append(word.upper())
            # Special handling for AppStream (appears as "appstream")
            elif word.lower() == 'appstream':
                title_words.append('AppStream')
            # Special handling for WorkSpaces (appears as "workspaces")
            elif word.lower() == 'workspaces':
                title_words.append('WorkSpaces')
            # Special handling for DaaS (appears as "daas")
            elif word.lower() == 'daas':
                title_words.append('DaaS')
            # Handle version numbers like "2" followed by "0" → "2.0"
            elif word.isdigit() and i + 1 < len(words) and words[i + 1] == '0':
                title_words.append(word + '.0')
                words[i + 1] = ''  # Skip the next word
            elif word == '':
                continue  # Skip empty words (from version number handling)
            else:
                title_words.append(word.capitalize())
        
        return ' '.join(title_words)
    
    def is_euc_related(self, url, title):
        """Check if content is EUC-related"""
        text = f"{url} {title}".lower()
        keywords = [
            'euc', 'end-user-computing', 'end user computing',
            'workspaces', 'appstream', 'workspace',
            'end user', 'desktop', 'virtual desktop',
            'vdi', 'daas'
        ]
        return any(keyword in text for keyword in keywords)
    
    def extract_metadata_from_sitemap(self, url, lastmod):
        """Extract metadata from sitemap URL and lastmod"""
        title = self.extract_title_from_slug(url)
        
        return {
            'url': url,
            'title': title,
            'authors': 'AWS Builder Community',
            'date_published': lastmod,
            'date_updated': lastmod,
            'tags': 'End User Computing, Builder.AWS',
            'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.',
            'source': 'builder.aws.com'
        }
    
    def save_to_dynamodb(self, metadata):
        """Save a single post to DynamoDB"""
        try:
            # Create a unique ID from the URL
            post_id = metadata['url'].split('/')[-1] if not metadata['url'].endswith('/') else metadata['url'].split('/')[-2]
            post_id = f"builder-{post_id}"  # Prefix to avoid conflicts with AWS blog posts
            
            # Check if item exists
            content_changed = False
            try:
                response = self.table.get_item(Key={'post_id': post_id})
                if 'Item' in response:
                    self.posts_updated += 1
                    existing_item = response['Item']
                    
                    # For Builder articles, use lastmod date instead of content for change detection
                    # This prevents false positives from template string variations
                    old_date = existing_item.get('date_updated', '')
                    new_date = metadata['date_updated']
                    if old_date != new_date:
                        content_changed = True
                        print(f"  Article updated (lastmod changed: {old_date} → {new_date})")
                    else:
                        print(f"  Article unchanged (lastmod: {new_date})")
                else:
                    self.posts_created += 1
                    content_changed = True
            except:
                self.posts_created += 1
                content_changed = True
            
            # Build update expression
            if content_changed:
                # Track this post ID for Selenium crawler
                self.changed_post_ids.append(post_id)
                
                update_expression = '''
                    SET #url = :url,
                        title = :title,
                        authors = :authors,
                        date_published = :date_published,
                        date_updated = :date_updated,
                        tags = :tags,
                        content = :content,
                        last_crawled = :last_crawled,
                        summary = :empty,
                        label = :empty,
                        label_confidence = :zero,
                        label_generated = :empty,
                        #source = :source
                '''
                expression_values = {
                    ':url': metadata['url'],
                    ':title': metadata['title'],
                    ':authors': metadata['authors'],
                    ':date_published': metadata['date_published'],
                    ':date_updated': metadata['date_updated'],
                    ':tags': metadata['tags'],
                    ':content': metadata['content'],
                    ':last_crawled': datetime.utcnow().isoformat(),
                    ':empty': '',
                    ':zero': 0,
                    ':source': metadata['source']
                }
                self.posts_needing_summaries += 1
                self.posts_needing_classification += 1
            else:
                # Post unchanged - preserve existing authors, content, and summary
                # Only update metadata fields and use if_not_exists() for critical fields
                update_expression = '''
                    SET #url = :url,
                        title = :title,
                        date_published = if_not_exists(date_published, :date_published),
                        date_updated = :date_updated,
                        tags = :tags,
                        last_crawled = :last_crawled,
                        #source = :source,
                        authors = if_not_exists(authors, :authors),
                        content = if_not_exists(content, :content)
                '''
                # Note: Does NOT touch summary, label, or other AI-generated fields
                # This preserves real author names and content from Selenium crawler
                expression_values = {
                    ':url': metadata['url'],
                    ':title': metadata['title'],
                    ':authors': metadata['authors'],
                    ':date_published': metadata['date_published'],
                    ':date_updated': metadata['date_updated'],
                    ':tags': metadata['tags'],
                    ':content': metadata['content'],
                    ':last_crawled': datetime.utcnow().isoformat(),
                    ':source': metadata['source']
                }
            
            self.table.update_item(
                Key={'post_id': post_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames={
                    '#url': 'url',
                    '#source': 'source'
                },
                ExpressionAttributeValues=expression_values
            )
            
            self.posts_processed += 1
            return True
            
        except Exception as e:
            print(f"Error saving to DynamoDB: {e}")
            return False
    
    def crawl_all_posts(self):
        """Crawl all EUC-related posts from builder.aws.com sitemaps"""
        print("Starting Builder.AWS crawl")
        
        # Get all article sitemaps
        sitemaps = self.get_article_sitemaps()
        
        if not sitemaps:
            print("No sitemaps found")
            return {
                'total_posts': 0,
                'posts_processed': 0,
                'posts_created': 0,
                'posts_updated': 0,
                'posts_needing_summaries': 0
            }
        
        all_posts = []
        
        # Process each sitemap
        for sitemap_url in sitemaps:
            print(f"Processing sitemap: {sitemap_url}")
            
            try:
                response = self.session.get(sitemap_url, timeout=30)
                response.raise_for_status()
                
                root = ET.fromstring(response.text)
                namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                
                # Extract URLs and lastmod dates
                for url_elem in root.findall('.//ns:url', namespace):
                    loc = url_elem.find('ns:loc', namespace)
                    lastmod = url_elem.find('ns:lastmod', namespace)
                    
                    if loc is not None and lastmod is not None:
                        url = loc.text
                        date = lastmod.text
                        
                        # Extract title from URL
                        title = self.extract_title_from_slug(url)
                        
                        # Filter for EUC-related content
                        if self.is_euc_related(url, title):
                            all_posts.append((url, date))
                
                time.sleep(0.5)  # Be nice to the server
                
            except Exception as e:
                print(f"Error processing sitemap {sitemap_url}: {e}")
                continue
        
        print(f"\nFound {len(all_posts)} EUC-related posts")
        
        # Process each post
        for idx, (url, lastmod) in enumerate(all_posts, 1):
            print(f"[{idx}/{len(all_posts)}] Processing: {url}")
            
            metadata = self.extract_metadata_from_sitemap(url, lastmod)
            
            if self.save_to_dynamodb(metadata):
                print(f"  ✓ Saved: {metadata['title'][:60]}...")
            else:
                print(f"  ✗ Failed to save")
            
            time.sleep(0.2)
        
        return {
            'total_posts': len(all_posts),
            'posts_processed': self.posts_processed,
            'posts_created': self.posts_created,
            'posts_updated': self.posts_updated,
            'posts_needing_summaries': self.posts_needing_summaries,
            'posts_needing_classification': self.posts_needing_classification
        }


def lambda_handler(event, context):
    """
    Lambda handler function
    
    Event parameters:
    - max_pages (optional): Limit the number of listing pages to crawl (AWS blog only)
    - table_name (optional): Override the DynamoDB table name
    - source (optional): 'aws-blog', 'builder', or 'all' (default: 'all')
    """
    
    try:
        # Get parameters from event or environment
        max_pages = event.get('max_pages') if event else None
        table_name = event.get('table_name', TABLE_NAME) if event else TABLE_NAME
        source = event.get('source', 'all') if event else 'all'
        
        print(f"Starting Multi-Source Crawler Lambda")
        print(f"DynamoDB Table: {table_name}")
        print(f"Source: {source}")
        if max_pages:
            print(f"Max Pages (AWS Blog): {max_pages}")
        
        all_results = {}
        
        # Crawl AWS Blog
        if source in ['all', 'aws-blog']:
            print(f"\n{'='*60}")
            print("CRAWLING AWS BLOG")
            print(f"{'='*60}")
            blog_url = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/'
            print(f"Target URL: {blog_url}")
            
            crawler = AWSBlogCrawler(blog_url, table_name)
            results = crawler.crawl_all_posts(max_pages=max_pages)
            all_results['aws_blog'] = results
        
        # Crawl Builder.AWS
        if source in ['all', 'builder']:
            print(f"\n{'='*60}")
            print("CRAWLING BUILDER.AWS")
            print(f"{'='*60}")
            
            builder_crawler = BuilderAWSCrawler(table_name)
            builder_results = builder_crawler.crawl_all_posts()
            all_results['builder_aws'] = builder_results
            
            # Invoke Selenium crawler for changed posts (to fetch real authors/content)
            changed_post_ids = builder_crawler.changed_post_ids
            if changed_post_ids:
                print(f"\n{len(changed_post_ids)} Builder.AWS posts changed - invoking Selenium crawler")
                print(f"Changed post IDs: {changed_post_ids[:5]}{'...' if len(changed_post_ids) > 5 else ''}")
                
                try:
                    lambda_client = boto3.client('lambda')
                    
                    # Invoke Selenium crawler with the list of changed post IDs
                    # The Selenium crawler will fetch real authors and content for these posts
                    # and then automatically invoke Summary → Classifier
                    lambda_client.invoke(
                        FunctionName='aws-blog-builder-selenium-crawler',  # No alias - ECS task
                        InvocationType='Event',  # Async invocation
                        Payload=json.dumps({
                            'post_ids': changed_post_ids,
                            'table_name': table_name
                        })
                    )
                    print(f"  ✓ Invoked Selenium crawler for {len(changed_post_ids)} posts")
                    builder_results['selenium_crawler_invoked'] = True
                    builder_results['selenium_post_count'] = len(changed_post_ids)
                except Exception as e:
                    print(f"  Warning: Could not invoke Selenium crawler: {e}")
                    builder_results['selenium_error'] = str(e)
            else:
                print(f"\nNo Builder.AWS posts changed - skipping Selenium crawler")
        
        # Combine results
        results = {
            'total_posts': sum(r.get('total_posts', 0) for r in all_results.values()),
            'posts_processed': sum(r.get('posts_processed', 0) for r in all_results.values()),
            'posts_created': sum(r.get('posts_created', 0) for r in all_results.values()),
            'posts_updated': sum(r.get('posts_updated', 0) for r in all_results.values()),
            'posts_needing_summaries': sum(r.get('posts_needing_summaries', 0) for r in all_results.values()),
            'posts_needing_classification': sum(r.get('posts_needing_classification', 0) for r in all_results.values()),
            'by_source': all_results
        }
        
        # Automatically invoke summary Lambda for AWS Blog posts only
        # (Builder.AWS posts are handled by Selenium crawler → Summary → Classifier chain)
        aws_blog_summaries_needed = all_results.get('aws_blog', {}).get('posts_needing_summaries', 0)
        if aws_blog_summaries_needed > 0:
            print(f"\n{aws_blog_summaries_needed} AWS Blog posts need summary generation")
            print("Invoking summary Lambda...")
            
            try:
                lambda_client = boto3.client('lambda')
                
                # Determine which alias to use based on environment
                environment = os.environ.get('ENVIRONMENT', 'production')
                function_name = f"aws-blog-summary-generator:{environment}"
                
                # Calculate number of batches needed (5 posts per batch to avoid timeouts)
                batch_size = 5
                num_batches = (aws_blog_summaries_needed + batch_size - 1) // batch_size
                
                for i in range(num_batches):
                    lambda_client.invoke(
                        FunctionName=function_name,
                        InvocationType='Event',  # Async invocation
                        Payload=json.dumps({
                            'batch_size': batch_size,
                            'force': False
                        })
                    )
                    print(f"  Invoked summary batch {i+1}/{num_batches} ({function_name})")
                    time.sleep(2)  # 2-second delay between batches
                
                results['summary_batches_invoked'] = num_batches
            except Exception as e:
                print(f"  Warning: Could not invoke summary Lambda: {e}")
                results['summary_error'] = str(e)
        
        # Automatically invoke classifier Lambda for AWS Blog posts only
        # (Builder.AWS posts are handled by Selenium crawler → Summary → Classifier chain)
        aws_blog_classification_needed = all_results.get('aws_blog', {}).get('posts_needing_classification', 0)
        if aws_blog_classification_needed > 0:
            print(f"\n{aws_blog_classification_needed} AWS Blog posts need classification")
            print("Invoking classifier Lambda...")
            
            try:
                lambda_client = boto3.client('lambda')
                
                # Determine which alias to use based on environment
                environment = os.environ.get('ENVIRONMENT', 'production')
                function_name = f"aws-blog-classifier:{environment}"
                
                # Calculate number of batches needed (5 posts per batch to avoid timeouts)
                batch_size = 5
                num_batches = (aws_blog_classification_needed + batch_size - 1) // batch_size
                
                for i in range(num_batches):
                    lambda_client.invoke(
                        FunctionName=function_name,
                        InvocationType='Event',  # Async invocation
                        Payload=json.dumps({
                            'batch_size': batch_size
                        })
                    )
                    print(f"  Invoked classifier batch {i+1}/{num_batches} ({function_name})")
                    time.sleep(2)  # 2-second delay between batches
                
                results['classifier_batches_invoked'] = num_batches
            except Exception as e:
                print(f"  Warning: Could not invoke classifier Lambda: {e}")
                results['classifier_error'] = str(e)
        
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Multi-source crawl completed successfully',
                'results': results
            })
        }
        
        print(f"\n{'='*60}")
        print(f"Multi-Source Crawl Summary:")
        print(f"  Total posts found: {results['total_posts']}")
        print(f"  Posts processed: {results['posts_processed']}")
        print(f"  Posts created: {results['posts_created']}")
        print(f"  Posts updated: {results['posts_updated']}")
        print(f"  Posts needing summaries: {results.get('posts_needing_summaries', 0)}")
        if 'summary_batches_invoked' in results:
            print(f"  Summary batches invoked: {results['summary_batches_invoked']}")
        print(f"  Posts needing classification: {results.get('posts_needing_classification', 0)}")
        if 'classifier_batches_invoked' in results:
            print(f"  Classifier batches invoked: {results['classifier_batches_invoked']}")
        
        # Show breakdown by source
        if 'by_source' in results:
            print(f"\n  By Source:")
            for source_name, source_results in results['by_source'].items():
                print(f"    {source_name}: {source_results.get('total_posts', 0)} posts")
        
        print(f"{'='*60}")
        
        return response
        
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Crawl failed',
                'error': str(e)
            })
        }


# For local testing
if __name__ == '__main__':
    # Test locally with a limited number of pages
    test_event = {
        'max_pages': 2,  # Only crawl first 2 pages for testing
        'table_name': 'aws-blog-posts'
    }
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
