"""
Builder.AWS Playwright Crawler Lambda Function
Uses Playwright with AWS Lambda support for better compatibility
"""

import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime
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


def get_article_sitemaps():
    """Get list of article sitemap URLs"""
    sitemap_index_url = 'https://builder.aws.com/sitemaps/sitemap.xml'
    
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
        'vdi', 'daas'
    ]
    return any(keyword in text for keyword in keywords)


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


def extract_page_content(page, url):
    """Extract content from a page using Playwright"""
    try:
        print(f"  Loading: {url}")
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        
        # Wait for h1 to appear
        try:
            page.wait_for_selector('h1', timeout=10000)
        except:
            print(f"  Timeout waiting for content")
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
        except:
            pass
        
        if not metadata['title']:
            metadata['title'] = extract_title_from_slug(url)
        
        # Extract author - look for profile div
        author_found = False
        try:
            profile_div = page.query_selector("[class*='_profile_']")
            if profile_div:
                author_text = profile_div.inner_text().split('\n')[0].strip()
                if author_text and author_text != 'Follow' and author_text != 'AWS Employee':
                    metadata['authors'] = author_text
                    author_found = True
        except:
            pass
        
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
                                break
            except:
                pass
        
        if not author_found:
            print(f"  No author found, skipping")
            return None
        
        # Extract date
        try:
            time_elem = page.query_selector('time')
            if time_elem:
                metadata['date_published'] = time_elem.get_attribute('datetime') or time_elem.inner_text()
        except:
            pass
        
        if not metadata['date_published']:
            metadata['date_published'] = datetime.utcnow().isoformat()
        
        # Extract content
        try:
            article_elem = page.query_selector('article')
            if article_elem:
                metadata['content'] = article_elem.inner_text()[:3000]
        except:
            pass
        
        if not metadata['content']:
            try:
                main_elem = page.query_selector('main')
                if main_elem:
                    metadata['content'] = main_elem.inner_text()[:3000]
            except:
                pass
        
        if not metadata['content']:
            metadata['content'] = f"Learn more about {metadata['title']}. Visit the full article on Builder.AWS."
        
        return metadata
        
    except Exception as e:
        print(f"  Error extracting content: {e}")
        return None


def save_to_dynamodb(table, metadata):
    """Save a post to DynamoDB"""
    try:
        post_id = metadata['url'].split('/')[-1] if not metadata['url'].endswith('/') else metadata['url'].split('/')[-2]
        post_id = f"builder-{post_id}"
        
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
                ':last_crawled': datetime.utcnow().isoformat(),
                ':empty': '',
                ':zero': 0,
                ':source': metadata['source']
            }
        )
        
        return True
        
    except Exception as e:
        print(f"  Error saving to DynamoDB: {e}")
        return False


def lambda_handler(event, context):
    """
    Lambda handler for Builder.AWS crawler with Playwright
    
    Parameters:
    - max_posts (optional): Limit number of posts to process
    """
    
    if not PLAYWRIGHT_AVAILABLE:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Playwright not available'})
        }
    
    print("Starting Builder.AWS Playwright Crawler")
    
    max_posts = event.get('max_posts') if event else None
    table = dynamodb.Table(TABLE_NAME)
    
    posts_processed = 0
    posts_updated = 0
    posts_skipped = 0
    
    try:
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
                response = requests.get(sitemap_url, timeout=30)
                response.raise_for_status()
                
                root = ET.fromstring(response.text)
                namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                
                for url_elem in root.findall('.//ns:url', namespace):
                    loc = url_elem.find('ns:loc', namespace)
                    lastmod = url_elem.find('ns:lastmod', namespace)
                    
                    if loc is not None:
                        url = loc.text
                        title = extract_title_from_slug(url)
                        
                        if is_euc_related(url, title):
                            date = lastmod.text if lastmod is not None else ''
                            all_urls.append((url, date))
                
                time.sleep(0.3)
                
            except Exception as e:
                print(f"Error processing sitemap {sitemap_url}: {e}")
                continue
        
        print(f"Found {len(all_urls)} EUC-related posts")
        
        # Limit if requested
        if max_posts:
            all_urls = all_urls[:max_posts]
            print(f"Limiting to {max_posts} posts")
        
        # Use Playwright to process URLs
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            )
            
            page = browser.new_page()
            
            # Process each URL
            for idx, (url, lastmod) in enumerate(all_urls, 1):
                print(f"[{idx}/{len(all_urls)}] {url}")
                
                metadata = extract_page_content(page, url)
                
                if metadata:
                    if not metadata['date_published'] and lastmod:
                        metadata['date_published'] = lastmod
                    
                    if save_to_dynamodb(table, metadata):
                        print(f"  Saved: {metadata['title'][:50]}... by {metadata['authors']}")
                        posts_processed += 1
                        posts_updated += 1
                    else:
                        print(f"  Failed to save")
                else:
                    print(f"  Skipped")
                    posts_skipped += 1
                
                time.sleep(0.5)
            
            browser.close()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Builder.AWS crawl completed',
                'posts_processed': posts_processed,
                'posts_updated': posts_updated,
                'posts_skipped': posts_skipped
            })
        }
        
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
