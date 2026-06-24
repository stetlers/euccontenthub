"""
Builder.AWS Selenium Crawler for ECS/Fargate
Fetches real author names and content from Builder.AWS pages using Selenium/Chrome
"""

import json
import os
import sys
import time
import xml.etree.ElementTree as ET
import boto3
import requests
from datetime import datetime
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

# When POST_IDS is empty the crawler runs in DISCOVERY mode: it reads the
# builder.aws sitemap, filters to EUC-related posts, and creates/updates them
# (full title + content), exactly like the Lambda crawler but without the
# single-process Chrome crashes (Fargate runs normal multi-process Chrome).

# SPA shell titles to reject (the "AWS Builder Center" incident): if the
# rendered <h1> is the site name we fall back to the slug-derived title.
SPA_SHELL_TITLES = {'aws builder center', 'builder.aws', 'builder.aws.com'}

SITEMAP_INDEX_URL = 'https://builder.aws.com/sitemaps/sitemap.xml'
SITEMAP_NS = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
EUC_KEYWORDS = [
    'euc', 'end-user-computing', 'end user computing', 'workspaces', 'appstream',
    'workspace', 'end user', 'desktop', 'virtual desktop', 'vdi', 'daas',
]

# AWS clients
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table(TABLE_NAME)
lambda_client = boto3.client('lambda', region_name='us-east-1')


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


def extract_title_from_slug(url):
    """Derive a human-ish title from the URL slug as a fallback."""
    slug = url.rstrip('/').split('/')[-1]
    words = slug.split('-')
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if w.isupper() and len(w) <= 4:
            out.append(w)
        elif lw in ('ai', 'ml', 'api', 'aws', 'iam', 'ec2', 's3', 'vpc', 'euc', 'vdi'):
            out.append(w.upper())
        elif lw == 'appstream':
            out.append('AppStream')
        elif lw == 'workspaces':
            out.append('WorkSpaces')
        elif lw == 'daas':
            out.append('DaaS')
        elif w == '':
            continue
        else:
            out.append(w.capitalize())
    return ' '.join(out)


def is_euc_related(url, title):
    text = f"{url} {title}".lower()
    return any(k in text for k in EUC_KEYWORDS)


def get_article_sitemaps():
    """Return the list of article sitemap URLs from the sitemap index."""
    try:
        resp = requests.get(SITEMAP_INDEX_URL, timeout=30)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        return [loc.text for loc in root.findall('.//ns:url/ns:loc', SITEMAP_NS)
                if loc.text and '/sitemaps/articles/' in loc.text]
    except Exception as e:
        print(f"Error fetching sitemap index: {e}")
        return []


def discover_euc_urls():
    """Discover all EUC-related (url, lastmod) pairs from the builder.aws sitemap.

    Sorted by URL for stable, reproducible ordering across runs.
    """
    urls = []
    for sm in get_article_sitemaps():
        try:
            resp = requests.get(sm, timeout=30)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            for u in root.findall('.//ns:url', SITEMAP_NS):
                loc = u.find('ns:loc', SITEMAP_NS)
                lastmod = u.find('ns:lastmod', SITEMAP_NS)
                if loc is None or not loc.text:
                    continue
                url = loc.text
                if is_euc_related(url, extract_title_from_slug(url)):
                    urls.append((url, lastmod.text if lastmod is not None else ''))
            time.sleep(0.5)
        except Exception as e:
            print(f"  Error processing sitemap {sm}: {e}")
            continue
    # De-dup and sort for stable ordering.
    return sorted(set(urls), key=lambda t: t[0])


def extract_page_content(driver, url, max_retries=3):
    """
    Extract author and content from a Builder.AWS page
    
    Returns:
        dict: {'authors': str, 'content': str} or None if extraction fails
    """
    for attempt in range(max_retries):
        try:
            driver.get(url)

            # Wait for the article heading to render (SPA), not just <body>.
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                )
            except TimeoutException:
                # Fall back to body presence; title will use the slug.
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

            # Give JavaScript time to render
            time.sleep(2)

            # Extract title from rendered <h1>, with shell-title guard + slug fallback.
            title = ''
            try:
                h1_text = driver.find_element(By.TAG_NAME, "h1").text.strip()
                if h1_text and h1_text.lower() not in SPA_SHELL_TITLES:
                    title = h1_text
            except NoSuchElementException:
                pass
            if not title:
                title = extract_title_from_slug(url)
                print(f"  Using slug-based title: {title}")

            # Extract author name
            authors = "AWS Builder Community"  # Default
            try:
                # Try multiple selectors for author
                # Builder.AWS uses CSS modules with dynamic class names like _profile-name_xxxxx
                author_selectors = [
                    "//span[contains(@class, 'profile-name')]//span[contains(@class, 'ellipse-text')]",
                    "//span[contains(@class, 'profile-name')]",
                    "//span[contains(@class, '_profile-name')]",
                    "//meta[@name='author']",
                    "//span[contains(@class, 'author')]",
                    "//div[contains(@class, 'author')]",
                    "//a[contains(@class, 'author')]"
                ]
                
                for selector in author_selectors:
                    try:
                        if selector.startswith("//meta"):
                            author_elem = driver.find_element(By.XPATH, selector)
                            authors = author_elem.get_attribute('content')
                        else:
                            author_elem = driver.find_element(By.XPATH, selector)
                            authors = author_elem.text.strip()
                        
                        if authors and authors != "AWS Builder Community":
                            print(f"  Found author with selector: {selector}")
                            break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                print(f"  Warning: Could not extract author: {e}")
            
            # Extract content
            content = ""
            try:
                # Try multiple selectors for main content
                content_selectors = [
                    "//article",
                    "//main",
                    "//div[contains(@class, 'content')]",
                    "//div[contains(@class, 'post')]",
                    "//div[contains(@class, 'article')]"
                ]
                
                for selector in content_selectors:
                    try:
                        content_elem = driver.find_element(By.XPATH, selector)
                        content = content_elem.text.strip()
                        if content and len(content) > 100:  # Ensure we got substantial content
                            break
                    except NoSuchElementException:
                        continue
                
                # If no content found, try getting all text from body
                if not content or len(content) < 100:
                    body = driver.find_element(By.TAG_NAME, "body")
                    content = body.text.strip()
            except Exception as e:
                print(f"  Warning: Could not extract content: {e}")
                content = "Content extraction failed. Visit the full article on Builder.AWS."
            
            # Limit content to first 3000 characters (matching AWS Blog crawler)
            if len(content) > 3000:
                content = content[:3000]
            
            return {
                'title': title,
                'authors': authors,
                'content': content
            }

        except TimeoutException:
            if attempt < max_retries - 1:
                print(f"  Timeout on attempt {attempt + 1}, retrying...")
                time.sleep(2)
            else:
                print(f"  Failed after {max_retries} attempts")
                return None
                
        except Exception as e:
            print(f"  Error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return None
    
    return None


def update_post_in_dynamodb(post_id, authors, content):
    """Enrichment-only update (legacy POST_IDS mode): authors + content only.

    Does NOT touch title/summary/label - used when crawling a hand-fed list of
    existing posts purely to refresh author/content.
    """
    try:
        table.update_item(
            Key={'post_id': post_id},
            UpdateExpression='SET authors = :authors, content = :content, last_crawled = :last_crawled',
            ExpressionAttributeValues={
                ':authors': authors,
                ':content': content,
                ':last_crawled': datetime.utcnow().isoformat()
            }
        )
        return True
    except Exception as e:
        print(f"  Error updating DynamoDB for {post_id}: {e}")
        return False


def save_to_dynamodb(metadata):
    """Full upsert for DISCOVERY mode: write title/authors/content and run
    date-based change-detection so AI fields (summary/label) are only blanked on
    new or genuinely-revised posts (prevents a Bedrock re-summarize storm).

    metadata: {url, title, authors, content, date_updated (sitemap lastmod)}
    Returns 'created' | 'updated' | False.
    """
    try:
        url = metadata['url']
        post_id = url.split('/')[-1] if not url.endswith('/') else url.split('/')[-2]
        post_id = f"builder-{post_id}"
        new_date = metadata.get('date_updated', '') or ''

        content_changed = False
        existed = False
        try:
            resp = table.get_item(Key={'post_id': post_id})
            if 'Item' in resp:
                existed = True
                old_date = resp['Item'].get('date_updated', '')
                if not old_date or old_date != new_date:
                    content_changed = True
                    print(f"  Article changed (lastmod {old_date or '(none)'} -> {new_date}) - regenerating")
                else:
                    print(f"  Article unchanged (lastmod: {new_date}) - preserving summary/label")
            else:
                content_changed = True
                print(f"  New article - generating summary/label")
        except Exception as e:
            content_changed = True
            print(f"  get_item failed for {post_id}, treating as changed: {e}")

        common = {
            ':url': url,
            ':title': metadata['title'],
            ':authors': metadata['authors'],
            ':date_updated': new_date,
            # The crawler has no page-level publish date, so seed date_published
            # from the sitemap lastmod (same value as date_updated). It is written
            # with if_not_exists so a real publish date set by another source is
            # never overwritten, but a brand-new row always gets a sortable date.
            # (Omitting this is what left 23 prod rows with a null date_published,
            # sinking them to the bottom of the newest-first list - 2026-06-24.)
            ':date_published': metadata.get('date_published') or new_date,
            ':tags': 'End User Computing, Builder.AWS',
            ':content': metadata['content'],
            ':last_crawled': datetime.utcnow().isoformat(),
            ':source': 'builder.aws.com',
        }

        if content_changed:
            table.update_item(
                Key={'post_id': post_id},
                UpdateExpression='''
                    SET #url = :url, title = :title, authors = :authors,
                        date_updated = :date_updated,
                        date_published = if_not_exists(date_published, :date_published),
                        tags = :tags,
                        content = :content, last_crawled = :last_crawled,
                        summary = :empty, label = :empty,
                        label_confidence = :zero, label_generated = :empty,
                        #source = :source
                ''',
                ExpressionAttributeNames={'#url': 'url', '#source': 'source'},
                ExpressionAttributeValues={**common, ':empty': '', ':zero': 0},
            )
        else:
            table.update_item(
                Key={'post_id': post_id},
                UpdateExpression='''
                    SET #url = :url, title = :title, authors = :authors,
                        date_updated = :date_updated,
                        date_published = if_not_exists(date_published, :date_published),
                        tags = :tags,
                        content = :content, last_crawled = :last_crawled,
                        #source = :source
                ''',
                ExpressionAttributeNames={'#url': 'url', '#source': 'source'},
                ExpressionAttributeValues=common,
            )

        # Distinguish outcomes so the caller only triggers summary regeneration
        # for posts whose summary was actually blanked (new or changed):
        #   'created'   - new post, summary blanked
        #   'changed'   - existing post, lastmod differed, summary blanked
        #   'unchanged' - existing post, summary preserved (no regen needed)
        if not existed:
            return 'created'
        return 'changed' if content_changed else 'unchanged'
    except Exception as e:
        print(f"  Error saving {metadata.get('url')}: {e}")
        return False


def get_posts_to_crawl(post_ids):
    """
    Get posts to crawl from DynamoDB
    
    Args:
        post_ids: List of specific post IDs to crawl
        
    Returns:
        list: List of dicts with {'post_id': str, 'url': str}
    """
    posts = []
    for post_id in post_ids:
        try:
            response = table.get_item(Key={'post_id': post_id})
            if 'Item' in response:
                item = response['Item']
                posts.append({
                    'post_id': post_id,
                    'url': item.get('url', '')
                })
        except Exception as e:
            print(f"  Error fetching post {post_id}: {e}")
    return posts


def invoke_summary_generator(posts_updated):
    """Invoke summary generator Lambda for the posts we just updated"""
    try:
        # Determine which alias to use based on environment
        function_name = f"aws-blog-summary-generator:{ENVIRONMENT}"
        
        # Calculate number of batches needed (5 posts per batch)
        batch_size = 5
        num_batches = (posts_updated + batch_size - 1) // batch_size
        
        for i in range(num_batches):
            lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='Event',  # Async invocation
                Payload=json.dumps({
                    'batch_size': batch_size,
                    'force': False,
                    'table_name': TABLE_NAME  # Pass table name for staging support
                })
            )
            print(f"  Invoked summary batch {i+1}/{num_batches} ({function_name})")
            time.sleep(2)  # 2-second delay between batches
        
        return True
    except Exception as e:
        print(f"  Warning: Could not invoke summary Lambda: {e}")
        return False


def main():
    """Main entry point for ECS task"""
    print(f"Starting Builder.AWS Selenium Crawler (ECS)")
    print(f"Environment: {ENVIRONMENT}")
    print(f"DynamoDB Table: {TABLE_NAME}")

    # Two modes:
    #   - DISCOVERY (default, POST_IDS empty): crawl the whole sitemap, full
    #     upsert with title + change-detection. This is the primary mode now.
    #   - ENRICHMENT (POST_IDS set): legacy author/content refresh of a hand-fed
    #     list of existing posts (no title/discovery).
    discovery_mode = not POST_IDS
    if discovery_mode:
        print("Mode: DISCOVERY (full sitemap crawl)")
        url_pairs = discover_euc_urls()
        posts = [{'post_id': None, 'url': u, 'lastmod': lm} for u, lm in url_pairs]
    else:
        print(f"Mode: ENRICHMENT  Post IDs: {POST_IDS}")
        posts = [{**p, 'lastmod': ''} for p in get_posts_to_crawl(POST_IDS)]

    if not posts:
        print("ERROR: No posts found to crawl")
        sys.exit(1)

    print(f"Found {len(posts)} posts to crawl")
    
    # Set up Selenium driver
    driver = None
    posts_processed = 0
    posts_updated = 0
    posts_failed = 0
    
    posts_created = 0
    posts_regenerated = 0  # new + changed; only these need summary regeneration
    try:
        driver = setup_driver()
        print("Chrome driver initialized successfully")

        # Process each post
        for idx, post in enumerate(posts, 1):
            post_id = post['post_id']
            url = post['url']

            print(f"[{idx}/{len(posts)}] Processing: {url}")

            # Periodic Chrome restart keeps memory in check on long discovery
            # runs (Fargate is multi-process so far more stable than Lambda, but
            # this is cheap insurance for the full ~175-post catalog).
            if idx > 1 and idx % 50 == 0:
                print(f"  Restarting Chrome (processed {idx} posts)...")
                try:
                    driver.quit()
                except Exception:
                    pass
                time.sleep(2)
                driver = setup_driver()

            # Extract content (+ title)
            result = extract_page_content(driver, url)

            if result:
                if discovery_mode:
                    result['url'] = url
                    result['date_updated'] = post.get('lastmod', '')
                    outcome = save_to_dynamodb(result)
                    if outcome == 'created':
                        posts_created += 1; posts_updated += 1; posts_regenerated += 1
                        print(f"  + Created: {result['title'][:55]} by {result['authors']}")
                    elif outcome == 'changed':
                        posts_updated += 1; posts_regenerated += 1
                        print(f"  ~ Changed: {result['title'][:55]} by {result['authors']}")
                    elif outcome == 'unchanged':
                        posts_updated += 1
                        print(f"  = Unchanged: {result['title'][:55]} by {result['authors']}")
                    else:
                        posts_failed += 1
                        print(f"  x Failed to save")
                else:
                    if update_post_in_dynamodb(post_id, result['authors'], result['content']):
                        print(f"  ~ Updated: {result['authors']}")
                        posts_updated += 1
                    else:
                        posts_failed += 1
                        print(f"  x Failed to update DynamoDB")
            else:
                print(f"  x Failed to extract content")
                posts_failed += 1

            posts_processed += 1

            # Small delay between requests
            time.sleep(1)
    
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        sys.exit(1)
    
    finally:
        if driver:
            driver.quit()
            print("Chrome driver closed")
    
    # Invoke summary generator ONLY for posts whose summary was blanked
    # (new + changed). In ENRICHMENT mode nothing is blanked, so use the legacy
    # behavior of regenerating for everything updated.
    to_regenerate = posts_regenerated if discovery_mode else posts_updated
    if to_regenerate > 0:
        print(f"\n{to_regenerate} posts need summaries - invoking summary generator")
        invoke_summary_generator(to_regenerate)
    else:
        print("\nNo new/changed posts - skipping summary generator")

    # Print summary
    print(f"\n=== Crawler Summary ===")
    print(f"Mode: {'DISCOVERY' if discovery_mode else 'ENRICHMENT'}")
    print(f"Posts processed: {posts_processed}")
    print(f"Posts created: {posts_created}")
    print(f"Posts regenerated (new+changed): {posts_regenerated}")
    print(f"Posts updated: {posts_updated}")
    print(f"Posts failed: {posts_failed}")
    
    # Exit with appropriate code
    if posts_failed > 0:
        print("Exiting with failure code (some posts failed)")
        sys.exit(1)
    else:
        print("Exiting with success code")
        sys.exit(0)


if __name__ == '__main__':
    main()
