"""
Builder.AWS Selenium Crawler
Crawls builder.aws.com using Selenium to extract full content including authors
Run this locally to populate builder.aws.com posts
"""

import os
import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime
import boto3
import requests

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
except ImportError:
    print("Selenium not installed. Installing...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "selenium"])
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException


class BuilderSeleniumCrawler:
    """Crawler for builder.aws.com using Selenium"""
    
    def __init__(self, table_name='aws-blog-posts', region='us-east-1'):
        self.table_name = table_name
        self.region = region
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
        self.driver = None
        self.posts_processed = 0
        self.posts_created = 0
        self.posts_updated = 0
        self.posts_skipped = 0
        self.total_urls = 0
    
    def setup_driver(self):
        """Setup Chrome driver with headless options"""
        print("Setting up Chrome driver...")
        
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        # --single-process + --no-zygote are MANDATORY on AWS Lambda: the sandbox
        # blocks the clone()/fork() + PID-namespace operations Chrome's normal
        # multi-process (zygote) model needs, so without these Chrome fails to
        # launch ("disconnected: Unable to receive message from renderer" at
        # startup — verified 2026-06-23). They are NOT the cause of the mid-crawl
        # renderer crashes; memory pressure is (see the 20-post restart below).
        chrome_options.add_argument('--single-process')
        chrome_options.add_argument('--no-zygote')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        # Additional stability options for Lambda
        chrome_options.add_argument('--disable-dev-tools')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--disable-accelerated-2d-canvas')
        chrome_options.add_argument('--disable-background-networking')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-breakpad')
        chrome_options.add_argument('--disable-component-extensions-with-background-pages')
        chrome_options.add_argument('--disable-features=TranslateUI,BlinkGenPropertyTrees')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--enable-features=NetworkService,NetworkServiceInProcess')
        chrome_options.add_argument('--force-color-profile=srgb')
        chrome_options.add_argument('--hide-scrollbars')
        chrome_options.add_argument('--metrics-recording-only')
        chrome_options.add_argument('--mute-audio')

        # Block images / media / fonts / plugins. We only extract text (<h1>,
        # article body, author), so rendering media is pure cost: it's what
        # spiked the single-process renderer's memory on heavy builder.aws pages
        # and caused per-page "poison pill" crashes (~17% of pages, even with
        # restarts + about:blank). Disabling these slashes per-page memory.
        # content_settings value 2 = block. '--blink-settings=imagesEnabled=false'
        # is a second, lower-level belt-and-suspenders for image decoding.
        chrome_options.add_argument('--blink-settings=imagesEnabled=false')
        chrome_prefs = {
            'profile.managed_default_content_settings.images': 2,
            'profile.managed_default_content_settings.stylesheets': 1,  # keep CSS (layout/selectors)
            'profile.managed_default_content_settings.plugins': 2,
            'profile.managed_default_content_settings.popups': 2,
            'profile.managed_default_content_settings.media_stream': 2,
        }
        chrome_options.add_experimental_option('prefs', chrome_prefs)

        # Set Chrome binary location (for Lambda container)
        chrome_options.binary_location = '/usr/local/bin/chrome'
        
        # Create service with explicit ChromeDriver path
        service = Service(executable_path='/usr/local/bin/chromedriver')
        
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✓ Chrome driver ready")
    
    def close_driver(self):
        """Close the Chrome driver"""
        if self.driver:
            self.driver.quit()
            print("✓ Chrome driver closed")
    
    def get_article_sitemaps(self):
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
            
            print(f"Found {len(article_sitemaps)} article sitemaps")
            return article_sitemaps
            
        except Exception as e:
            print(f"Error fetching sitemap index: {e}")
            return []
    
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
    
    def extract_title_from_slug(self, url):
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
    
    def extract_page_content(self, url, retry_count=0, max_retries=3):
        """
        Extract content from a page using Selenium
        Includes retry logic for Chrome crashes
        """
        try:
            print(f"  Loading page... (attempt {retry_count + 1}/{max_retries + 1})")
            
            # Check if driver is still alive
            try:
                _ = self.driver.current_url
            except Exception as e:
                print(f"  ⚠️  Driver disconnected, recreating...")
                self.close_driver()
                self.setup_driver()
            
            self.driver.get(url)
            
            # Wait for content to load (wait for title or main content)
            wait = WebDriverWait(self.driver, 10)
            
            # Try to wait for the main content area
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
            except TimeoutException:
                print(f"  ⚠️  Timeout waiting for content")
                return None
            
            # Give it a bit more time for dynamic content
            time.sleep(1)
            
            metadata = {
                'url': url,
                'title': '',
                'authors': '',
                'date_published': '',
                'content': '',
                'source': 'builder.aws.com'
            }
            
            # Extract title from the rendered <h1>. Guard against the SPA shell
            # name leaking through (the "AWS Builder Center" incident): if the h1
            # is missing or is just the site name, fall back to the slug title.
            shell_titles = {'aws builder center', 'builder.aws', 'builder.aws.com'}
            try:
                title_elem = self.driver.find_element(By.TAG_NAME, "h1")
                h1_text = title_elem.text.strip()
                if not h1_text or h1_text.lower() in shell_titles:
                    metadata['title'] = self.extract_title_from_slug(url)
                    print(f"  ⚠️  h1 was shell/empty ('{h1_text}'), using slug-based title")
                else:
                    metadata['title'] = h1_text
            except NoSuchElementException:
                # Fallback to slug-based title
                metadata['title'] = self.extract_title_from_slug(url)
                print(f"  ⚠️  No h1 found, using slug-based title")
            
            # Extract author - try multiple selectors
            author_found = False
            
            # Method 1: Look for profile div (builder.aws.com specific)
            try:
                profile_div = self.driver.find_element(By.CSS_SELECTOR, "[class*='_profile_']")
                # Get the first line of text (author name)
                author_text = profile_div.text.split('\n')[0].strip()
                if author_text and author_text != 'Follow' and author_text != 'AWS Employee':
                    metadata['authors'] = author_text
                    author_found = True
            except NoSuchElementException:
                pass
            
            # Method 2: Look for author in visible text near title
            if not author_found:
                try:
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text
                    # Look for pattern: "Name\nFollow\nAWS Employee"
                    import re
                    # Find text between title and "Follow"
                    title_text = metadata.get('title', '')
                    if title_text in body_text:
                        after_title = body_text.split(title_text, 1)[1]
                        # Get first few lines
                        lines = [l.strip() for l in after_title.split('\n') if l.strip()]
                        # Author is typically the first line before "Follow"
                        for i, line in enumerate(lines[:5]):
                            if line == 'Follow' and i > 0:
                                potential_author = lines[i-1]
                                # Check if it looks like a name (2-4 words, capitalized)
                                words = potential_author.split()
                                if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
                                    metadata['authors'] = potential_author
                                    author_found = True
                                    break
                except:
                    pass
            
            # Method 3: Look for author link or text
            if not author_found:
                try:
                    author_elem = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='author'], .author, [class*='author']")
                    metadata['authors'] = author_elem.text.strip()
                    author_found = True
                except NoSuchElementException:
                    pass
            
            if not author_found:
                print(f"  ⚠️  No author found")
                return None  # Skip posts without authors
            
            # Extract date
            try:
                time_elem = self.driver.find_element(By.TAG_NAME, "time")
                metadata['date_published'] = time_elem.get_attribute('datetime') or time_elem.text
            except NoSuchElementException:
                # Use current date as fallback
                metadata['date_published'] = datetime.utcnow().isoformat()
                print(f"  ⚠️  No date found, using current date")
            
            # Extract content
            try:
                article_elem = self.driver.find_element(By.TAG_NAME, "article")
                metadata['content'] = article_elem.text[:3000]  # First 3000 chars
            except NoSuchElementException:
                try:
                    main_elem = self.driver.find_element(By.TAG_NAME, "main")
                    metadata['content'] = main_elem.text[:3000]
                except NoSuchElementException:
                    metadata['content'] = f"Learn more about {metadata['title']}. Visit the full article on Builder.AWS."
                    print(f"  ⚠️  No content found, using placeholder")
            
            return metadata
            
        except Exception as e:
            error_msg = str(e)
            print(f"  ✗ Error extracting content: {error_msg}")
            
            # Check if it's a Chrome crash/disconnect error
            if 'disconnected' in error_msg.lower() or 'not connected' in error_msg.lower():
                if retry_count < max_retries:
                    print(f"  🔄 Chrome crashed, retrying...")
                    time.sleep(2)  # Wait before retry
                    return self.extract_page_content(url, retry_count + 1, max_retries)
                else:
                    print(f"  ❌ Max retries reached, skipping this post")
            
            return None
    
    def save_to_dynamodb(self, metadata):
        """Save a post to DynamoDB, regenerating AI fields only on a real change.

        Change detection mirrors the multi-source / Playwright crawlers: the
        sitemap lastmod (metadata['date_updated']) is compared against the stored
        date_updated.

          - New post, or lastmod differs (a genuine publisher revision): refresh
            all fields and blank summary/label so the summary/classifier Lambdas
            regenerate them.
          - Unchanged (the overwhelmingly common case): touch only last_crawled
            and refresh title/content/authors via plain SET (the rendered scrape
            is trustworthy here, unlike the requests fallback), but DO NOT blank
            summary/label.

        This stops a full Bedrock re-summarize/re-classify storm on every weekly
        crawl - Builder content changes rarely, so we only pay for it then.
        """
        try:
            post_id = metadata['url'].split('/')[-1] if not metadata['url'].endswith('/') else metadata['url'].split('/')[-2]
            post_id = f"builder-{post_id}"

            new_date = metadata.get('date_updated', '')

            # Decide new / genuinely-changed by comparing sitemap lastmod against
            # what's stored. A missing/unreadable record is treated as changed
            # (safe: regenerate rather than keep stale data).
            content_changed = False
            try:
                response = self.table.get_item(Key={'post_id': post_id})
                if 'Item' in response:
                    self.posts_updated += 1
                    old_date = response['Item'].get('date_updated', '')
                    if not old_date or old_date != new_date:
                        content_changed = True
                        print(f"  Article changed (lastmod {old_date or '(none)'} -> {new_date}) - regenerating")
                    else:
                        print(f"  Article unchanged (lastmod: {new_date}) - preserving summary/label")
                else:
                    self.posts_created += 1
                    content_changed = True
                    print(f"  New article - generating summary/label")
            except Exception as e:
                self.posts_created += 1
                content_changed = True
                print(f"  get_item failed for {post_id}, treating as changed: {e}")

            common_values = {
                ':url': metadata['url'],
                ':title': metadata['title'],
                ':authors': metadata['authors'],
                ':date_published': metadata['date_published'],
                ':date_updated': new_date,
                ':tags': 'End User Computing, Builder.AWS',
                ':content': metadata['content'],
                ':last_crawled': datetime.utcnow().isoformat(),
                ':source': metadata['source'],
            }

            if content_changed:
                # New post or genuine revision: refresh everything and blank the
                # AI-generated fields so the summary/classifier Lambdas regenerate.
                self.table.update_item(
                    Key={'post_id': post_id},
                    UpdateExpression='''
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
                    ''',
                    ExpressionAttributeNames={'#url': 'url', '#source': 'source'},
                    ExpressionAttributeValues={
                        **common_values,
                        ':empty': '',
                        ':zero': 0,
                    }
                )
            else:
                # Unchanged: refresh the cheap scraped fields and last_crawled, but
                # leave summary/label/label_confidence/label_generated intact so we
                # don't trigger a needless Bedrock regeneration storm.
                self.table.update_item(
                    Key={'post_id': post_id},
                    UpdateExpression='''
                        SET #url = :url,
                            title = :title,
                            authors = :authors,
                            date_published = :date_published,
                            date_updated = :date_updated,
                            tags = :tags,
                            content = :content,
                            last_crawled = :last_crawled,
                            #source = :source
                    ''',
                    ExpressionAttributeNames={'#url': 'url', '#source': 'source'},
                    ExpressionAttributeValues=common_values
                )

            self.posts_processed += 1
            return True

        except Exception as e:
            print(f"  ✗ Error saving to DynamoDB: {e}")
            return False
    
    def crawl_all_posts(self, max_posts=None, skip=0):
        """Crawl EUC-related posts.

        Args:
            max_posts: process at most this many posts (after skip). None = all.
            skip: skip this many posts before processing. Together with max_posts
                this enables batching across invocations to stay under the Lambda
                900s/10GB ceiling: invoke repeatedly with skip=0, skip=max_posts,
                skip=2*max_posts, ... until total_urls is exhausted. The URL list
                is sorted deterministically so the window is stable between runs.
        """
        print("="*80)
        print("Builder.AWS Selenium Crawler")
        print("="*80)
        
        # Setup Selenium
        self.setup_driver()
        
        try:
            # Get sitemaps
            sitemaps = self.get_article_sitemaps()
            
            if not sitemaps:
                print("No sitemaps found")
                return
            
            # Collect all EUC-related URLs
            all_urls = []
            
            for sitemap_url in sitemaps:
                print(f"\nProcessing sitemap: {sitemap_url}")
                
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
                            title = self.extract_title_from_slug(url)
                            
                            if self.is_euc_related(url, title):
                                date = lastmod.text if lastmod is not None else ''
                                all_urls.append((url, date))
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"  Error processing sitemap: {e}")
                    continue
            
            # Stable ordering so skip/max_posts windows are reproducible across
            # invocations (sitemap order is not guaranteed stable).
            all_urls.sort(key=lambda u: u[0])
            self.total_urls = len(all_urls)

            print(f"\n{'='*80}")
            print(f"Found {self.total_urls} EUC-related posts")
            print(f"{'='*80}\n")

            # Apply batching window: skip first, then cap at max_posts.
            if skip:
                all_urls = all_urls[skip:]
                print(f"Skipping first {skip} posts (batching)\n")
            if max_posts:
                all_urls = all_urls[:max_posts]
                print(f"Processing up to {max_posts} posts this batch\n")
            
            # Process each URL
            for idx, (url, lastmod) in enumerate(all_urls, 1):
                print(f"[{idx}/{len(all_urls)}] {url}")
                
                # Restart Chrome every 20 posts to keep memory well under the
                # 10GB ceiling. builder.aws SPA pages leave significant residue;
                # at the old cadence of 50 (and batch=40, so it never fired)
                # memory climbed to the ceiling and tipped Chrome into renderer
                # crashes. 20 keeps a comfortable margin.
                if idx > 1 and idx % 20 == 0:
                    print(f"  🔄 Restarting Chrome (processed {idx} posts)...")
                    self.close_driver()
                    time.sleep(2)
                    self.setup_driver()
                
                metadata = self.extract_page_content(url)
                
                if metadata:
                    # Use sitemap date if page date not found
                    if not metadata['date_published'] and lastmod:
                        metadata['date_published'] = lastmod

                    # Raw sitemap lastmod is the change-detection signal in
                    # save_to_dynamodb (stored unparsed to match the value the
                    # multi-source crawler writes, so unchanged posts compare equal).
                    metadata['date_updated'] = lastmod or ''

                    if self.save_to_dynamodb(metadata):
                        print(f"  ✓ Saved: {metadata['title'][:60]}... by {metadata['authors']}")
                    else:
                        print(f"  ✗ Failed to save")
                else:
                    print(f"  ⊘ Skipped (no author or failed to extract)")
                    self.posts_skipped += 1

                # Release the heavy SPA page's memory before the next navigation.
                # Under --single-process (mandatory on Lambda) the renderer shares
                # the browser process, so unreleased page memory accumulates until
                # a crash. Navigating to about:blank lets Chrome reclaim it; cheap
                # insurance between the 20-post hard restarts.
                try:
                    if self.driver:
                        self.driver.get("about:blank")
                except Exception:
                    pass
                
                # Be nice to the server
                time.sleep(1)
            
        finally:
            self.close_driver()
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"Crawl Summary:")
        print(f"  Posts processed: {self.posts_processed}")
        print(f"  Posts created: {self.posts_created}")
        print(f"  Posts updated: {self.posts_updated}")
        print(f"  Posts skipped: {self.posts_skipped}")
        print(f"{'='*80}")


def resolve_table_name(event=None):
    """Resolve the target DynamoDB table per invocation.

    Precedence (mirrors the zip Playwright crawler's resolve_table_name so the
    two crawlers agree on what 'staging' means and a staging run never writes to
    the prod table):
      1. event['table_name'] - explicit override (tests / direct invokes)
      2. event['environment'] == 'staging' -> '<base>-staging'
      3. the DYNAMODB_TABLE_NAME env var (default 'aws-blog-posts')

    With the per-env function pattern, the staging function simply sets
    DYNAMODB_TABLE_NAME=aws-blog-posts-staging and this returns it. The event
    overrides exist so the prod function can still be pointed at staging for a
    one-off validation run without redeploying.
    """
    base = os.environ.get('DYNAMODB_TABLE_NAME', 'aws-blog-posts')
    if base.endswith('-staging'):
        base = base[:-len('-staging')]

    if event and isinstance(event, dict):
        explicit = event.get('table_name')
        if explicit:
            return explicit
        if event.get('environment') == 'staging':
            return f'{base}-staging'
    return os.environ.get('DYNAMODB_TABLE_NAME', 'aws-blog-posts')


def lambda_handler(event, context):
    """
    Lambda handler for ECS/Fargate execution
    Triggers summary generation after crawl completes
    """
    max_posts = event.get('max_posts') if event else None
    skip = event.get('skip', 0) if event else 0

    table_name = resolve_table_name(event)
    print(f"Target table: {table_name} (skip={skip}, max_posts={max_posts})")

    crawler = BuilderSeleniumCrawler(table_name=table_name)
    crawler.crawl_all_posts(max_posts=max_posts, skip=skip)

    # next_skip lets a driver/poller walk batches: keep invoking with
    # skip=next_skip until next_skip >= total_urls.
    next_skip = skip + (max_posts or crawler.total_urls)
    done = next_skip >= crawler.total_urls
    
    # Trigger summary generation for new posts
    if crawler.posts_created > 0:
        print(f"\n{'='*80}")
        print(f"Triggering summary generation for {crawler.posts_created} new posts...")
        print(f"{'='*80}")
        
        try:
            import boto3
            lambda_client = boto3.client('lambda')
            
            response = lambda_client.invoke(
                FunctionName='aws-blog-summary-generator',
                InvocationType='Event',  # Async
                Payload=json.dumps({
                    'source': 'builder.aws',
                    'regenerate': False
                })
            )
            print(f"✓ Summary Lambda invoked (Status: {response['StatusCode']})")
        except Exception as e:
            print(f"⚠️  Could not invoke summary Lambda: {e}")
    
    return {
        'statusCode': 200,
        'body': {
            'message': 'Builder.AWS crawl completed',
            'posts_processed': crawler.posts_processed,
            'posts_created': crawler.posts_created,
            'posts_updated': crawler.posts_updated,
            'posts_skipped': crawler.posts_skipped,
            'total_urls': crawler.total_urls,
            'skip': skip,
            'next_skip': next_skip,
            'done': done
        }
    }


if __name__ == '__main__':
    import sys
    
    # Check for test mode
    max_posts = None
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        max_posts = 5
        print("TEST MODE: Processing only 5 posts\n")
    
    crawler = BuilderSeleniumCrawler()
    crawler.crawl_all_posts(max_posts=max_posts)
