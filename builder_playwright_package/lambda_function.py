"""
Builder.AWS Playwright Crawler Lambda Function
Uses Playwright with AWS Lambda support for better compatibility
"""

import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import Decimal
import boto3
import requests

from euc_filter import filter_post

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

# builder.aws.com is a client-side-rendered SPA. When the requests-based fallback
# fetches a page (no JS), it gets the unrendered shell whose <title> is the site
# name, not the article. Treat these as "no real content extracted" so we skip
# the row instead of poisoning title/content with the shell name (the 2026-06-17
# incident wrote 21 posts titled "AWS Builder Center"). Compared case-insensitively
# after stripping whitespace.
SPA_SHELL_TITLES = {
    'aws builder center',
    'builder.aws',
    'builder.aws.com',
}


def resolve_table_name(event=None):
    """Resolve the target DynamoDB table per invocation.

    Precedence (mirrors the multi-source crawler's get_table_suffix so the two
    crawlers agree on which table 'staging' means):
      1. event['table_name'] — explicit override (used by tests / direct invokes)
      2. event['environment'] == 'staging' -> '<base>-staging'
      3. the DYNAMODB_TABLE_NAME env var (default 'aws-blog-posts')

    This is what lets the staging site's "Refresh Posts" button target the
    staging table instead of prod: trigger_crawler passes environment='staging'.
    """
    base = os.environ.get('DYNAMODB_TABLE_NAME', 'aws-blog-posts')
    # Strip any existing suffix so we derive consistently from the base name.
    if base.endswith('-staging'):
        base = base[:-len('-staging')]

    if event and isinstance(event, dict):
        explicit = event.get('table_name')
        if explicit:
            return explicit
        if event.get('environment') == 'staging':
            return f'{base}-staging'
    return os.environ.get('DYNAMODB_TABLE_NAME', 'aws-blog-posts')

# Debug mode - set via environment variable or event parameter
DEBUG_MODE = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'


def debug_print(message):
    """Print debug messages when DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")


def get_article_sitemaps():
    """Get list of article sitemap URLs"""
    # Support both production and staging environments
    base_domain = os.environ.get('BASE_DOMAIN', 'builder.aws.com')
    sitemap_index_url = f'https://{base_domain}/sitemaps/sitemap.xml'

    debug_print(f"Fetching sitemap index from: {sitemap_index_url}")
    
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
        
        debug_print(f"Found {len(article_sitemaps)} article sitemaps")
        return article_sitemaps
        
    except Exception as e:
        print(f"Error fetching sitemap index: {e}")
        return []


def is_euc_related(url, title):
    """Check if content is EUC-related using the shared euc_filter module."""
    result = filter_post(url, title)
    debug_print(f"EUC check for '{title}': {result.accepted}")
    return result


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


def parse_date(date_string):
    """Parse date string and return ISO format, handling various formats"""
    if not date_string:
        return None
    
    try:
        # Try parsing ISO format with timezone
        if 'T' in date_string:
            if '+' in date_string or date_string.endswith('Z'):
                dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(date_string)
            return dt.isoformat()
        
        # Try parsing date-only format
        dt = datetime.strptime(date_string.split('T')[0], '%Y-%m-%d')
        return dt.isoformat()
    except Exception as e:
        debug_print(f"Date parsing error for '{date_string}': {e}")
        return date_string


def extract_page_content(page, url):
    """Extract content from a page using Playwright"""
    try:
        debug_print(f"Loading page: {url}")
        print(f"  Loading: {url}")
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        
        # Wait for h1 to appear
        try:
            page.wait_for_selector('h1', timeout=10000)
        except:
            print(f"  Timeout waiting for content")
            debug_print(f"Timeout waiting for h1 selector on {url}")
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
                debug_print(f"Extracted title: {metadata['title']}")
        except Exception as e:
            debug_print(f"Error extracting title: {e}")
        
        if not metadata['title']:
            metadata['title'] = extract_title_from_slug(url)
            debug_print(f"Using slug-based title: {metadata['title']}")
        
        # Extract author - look for profile div
        author_found = False
        try:
            profile_div = page.query_selector("[class*='_profile_']")
            if profile_div:
                author_text = profile_div.inner_text().split('\n')[0].strip()
                if author_text and author_text != 'Follow' and author_text != 'AWS Employee':
                    metadata['authors'] = author_text
                    author_found = True
                    debug_print(f"Found author from profile: {author_text}")
        except Exception as e:
            debug_print(f"Error extracting author from profile: {e}")
        
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
                                debug_print(f"Found author from body text: {potential_author}")
                                break
            except Exception as e:
                debug_print(f"Error extracting author from body: {e}")
        
        if not author_found:
            metadata['authors'] = 'Unknown Author'
            metadata['author_needs_review'] = True
            print(f"  ⚠ No author found — saving with 'Unknown Author' for manual review")
            debug_print(f"No author found for {url}, flagging for manual review")
        
        # Extract date - try multiple methods
        date_found = False
        try:
            time_elem = page.query_selector('time')
            if time_elem:
                date_value = time_elem.get_attribute('datetime') or time_elem.inner_text()
                if date_value:
                    metadata['date_published'] = parse_date(date_value)
                    date_found = True
                    debug_print(f"Found date from time element: {metadata['date_published']}")
        except Exception as e:
            debug_print(f"Error extracting date from time element: {e}")
        
        # Fallback: Look for date patterns in meta tags
        if not date_found:
            try:
                meta_selectors = [
                    'meta[property="article:published_time"]',
                    'meta[name="publish-date"]',
                    'meta[name="date"]'
                ]
                for selector in meta_selectors:
                    meta_elem = page.query_selector(selector)
                    if meta_elem:
                        date_value = meta_elem.get_attribute('content')
                        if date_value:
                            metadata['date_published'] = parse_date(date_value)
                            date_found = True
                            debug_print(f"Found date from meta tag {selector}: {metadata['date_published']}")
                            break
            except Exception as e:
                debug_print(f"Error extracting date from meta tags: {e}")
        
        if not date_found:
            metadata['date_published'] = datetime.now(timezone.utc).isoformat()
            debug_print(f"Using current date as fallback: {metadata['date_published']}")
        
        # Extract content
        try:
            article_elem = page.query_selector('article')
            if article_elem:
                metadata['content'] = article_elem.inner_text()[:3000]
                debug_print(f"Extracted {len(metadata['content'])} chars from article")
        except Exception as e:
            debug_print(f"Error extracting content from article: {e}")
        
        if not metadata['content']:
            try:
                main_elem = page.query_selector('main')
                if main_elem:
                    metadata['content'] = main_elem.inner_text()[:3000]
                    debug_print(f"Extracted {len(metadata['content'])} chars from main")
            except Exception as e:
                debug_print(f"Error extracting content from main: {e}")
        
        if not metadata['content']:
            metadata['content'] = f"Learn more about {metadata['title']}. Visit the full article on Builder.AWS."
            debug_print("Using fallback content")
        
        return metadata
        
    except Exception as e:
        print(f"  Error extracting content: {e}")
        debug_print(f"Error in extract_page_content for {url}: {e}")
        import traceback
        debug_print(traceback.format_exc())
        return None


def extract_page_content_requests(url, sitemap_date=''):
    """Extract content from a Builder.AWS page using requests (no JS rendering).
    
    Falls back to slug-based title and basic HTML parsing for content.
    Author extraction is limited without JS — flags for later review.
    """
    try:
        debug_print(f"Fetching (requests): {url}")
        resp = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        resp.raise_for_status()
        html = resp.text
        
        metadata = {
            'url': url,
            'title': '',
            'authors': 'Unknown Author',
            'date_published': '',
            'content': '',
            'source': 'builder.aws.com',
            'author_needs_review': True,
        }
        
        # Extract title from <title> tag or <h1>
        import re
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if title_match:
            raw_title = title_match.group(1).strip()
            # Remove common suffixes like " | Builder.AWS"
            raw_title = re.split(r'\s*[\|–—-]\s*(Builder|AWS)', raw_title)[0].strip()
            if raw_title:
                metadata['title'] = raw_title
        
        if not metadata['title']:
            metadata['title'] = extract_title_from_slug(url)
        
        # Extract date from sitemap lastmod or meta tags
        if sitemap_date:
            metadata['date_published'] = parse_date(sitemap_date)
        else:
            date_match = re.search(
                r'<meta[^>]*(?:property="article:published_time"|name="publish-date")[^>]*content="([^"]+)"',
                html, re.IGNORECASE
            )
            if date_match:
                metadata['date_published'] = parse_date(date_match.group(1))
            else:
                metadata['date_published'] = datetime.now(timezone.utc).isoformat()
        
        # Extract author from meta tag
        author_match = re.search(r'<meta[^>]*name="author"[^>]*content="([^"]+)"', html, re.IGNORECASE)
        if author_match and author_match.group(1).strip():
            metadata['authors'] = author_match.group(1).strip()
            metadata['author_needs_review'] = False
        
        # Extract content — try <article>, then <main>, then strip all tags from body
        content = ''
        for tag in ['article', 'main']:
            pattern = re.compile(rf'<{tag}[^>]*>(.*?)</{tag}>', re.DOTALL | re.IGNORECASE)
            match = pattern.search(html)
            if match:
                # Strip HTML tags to get text
                raw = re.sub(r'<[^>]+>', ' ', match.group(1))
                raw = re.sub(r'\s+', ' ', raw).strip()
                if len(raw) > 100:
                    content = raw
                    break
        
        if not content:
            # Last resort: strip all tags
            raw = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            raw = re.sub(r'<style[^>]*>.*?</style>', '', raw, flags=re.DOTALL | re.IGNORECASE)
            raw = re.sub(r'<[^>]+>', ' ', raw)
            raw = re.sub(r'\s+', ' ', raw).strip()
            content = raw
        
        metadata['content'] = content[:3000]

        # Guard against persisting an unrendered SPA shell. The requests fallback
        # can't execute the page's JS, so if the page never hydrated we end up with
        # the site-shell title (and the same string as "content"). Detect that and
        # skip the row (return None -> the handler counts it as skipped) rather than
        # overwriting a good record with "AWS Builder Center". A slug-derived title
        # is acceptable; a shell title or title==content is not.
        title_norm = metadata['title'].strip().lower()
        content_norm = metadata['content'].strip().lower()
        if title_norm in SPA_SHELL_TITLES or content_norm in SPA_SHELL_TITLES:
            print(f"  Skipping {url}: requests fallback got only the SPA shell "
                  f"(title='{metadata['title']}') — no rendered content")
            return None
        if title_norm and title_norm == content_norm:
            print(f"  Skipping {url}: title equals content "
                  f"('{metadata['title'][:40]}') — page did not render")
            return None
        if len(metadata['content']) < 100:
            print(f"  Skipping {url}: content too short "
                  f"({len(metadata['content'])} chars) — page did not render")
            return None

        debug_print(f"Extracted title='{metadata['title']}', content_len={len(metadata['content'])}")
        return metadata
        
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        debug_print(f"Error in extract_page_content_requests: {e}")
        return None


def save_to_dynamodb(table, metadata):
    """Save a post to DynamoDB, regenerating AI fields only on a real change.

    Change detection mirrors the multi-source crawler (BuilderAWSCrawler): the
    sitemap's lastmod (``metadata['date_updated']``) is compared against the
    stored ``date_updated``.

      - New post, or lastmod differs (a genuine publisher revision): refresh all
        fields and blank ``summary``/``label`` so the summary/classifier Lambdas
        regenerate them.
      - Unchanged (the overwhelmingly common case): touch only ``last_crawled``
        and the cheap keyword-filter fields; preserve ``summary``, ``label``,
        ``authors``, and ``content`` untouched.

    This is what stops a full Bedrock re-summarize/re-classify storm on every
    crawl — Builder content changes very rarely, so we only pay for it then.
    """
    try:
        post_id = metadata['url'].split('/')[-1] if not metadata['url'].endswith('/') else metadata['url'].split('/')[-2]
        post_id = f"builder-{post_id}"

        debug_print(f"Saving to DynamoDB with post_id: {post_id}")

        # Decide whether this is new / genuinely changed by comparing the sitemap
        # lastmod against what's stored. A missing or unreadable record is treated
        # as changed (safe: regenerate rather than silently keep stale data).
        new_date = metadata.get('date_updated', '')
        content_changed = False
        try:
            response = table.get_item(Key={'post_id': post_id})
            if 'Item' in response:
                old_date = response['Item'].get('date_updated', '')
                if not old_date or old_date != new_date:
                    content_changed = True
                    print(f"  Article changed (lastmod {old_date or '(none)'} -> {new_date}) - regenerating")
                else:
                    print(f"  Article unchanged (lastmod: {new_date}) - preserving summary/label/authors")
            else:
                content_changed = True
                print(f"  New article - generating summary/label")
        except Exception as e:
            content_changed = True
            debug_print(f"get_item failed for {post_id}, treating as changed: {e}")

        # Build filter field values — keyword-only at crawl time, AI scoring happens in summary_lambda.
        # These are cheap (no Bedrock) so they are refreshed on every run, changed or not.
        filter_values = {
            ':ai_validation_result': metadata.get('ai_validation_result', 'pending'),
            ':ai_validation_explanation': metadata.get('ai_validation_explanation', ''),
            ':filter_stage': metadata.get('filter_stage', 'keyword'),
            ':filter_reason': metadata.get('filter_reason', ''),
        }
        filter_expression_parts = '''
                    ai_validation_result = :ai_validation_result,
                    ai_validation_explanation = :ai_validation_explanation,
                    filter_stage = :filter_stage,
                    filter_reason = :filter_reason'''

        if content_changed:
            # New post or genuine revision: refresh everything and blank the
            # AI-generated fields so the summary/classifier Lambdas regenerate.
            author_review = metadata.get('author_needs_review', False)
            review_expression = ',\n                    author_needs_review = :author_needs_review' if author_review else ''
            review_values = {':author_needs_review': True} if author_review else {}

            # Never downgrade a real author to the 'Unknown Author' placeholder: if
            # this run's scrape didn't find an author (author_needs_review), keep any
            # author already stored via if_not_exists. A genuinely-scraped author
            # still overwrites. (Staging showed a real name lost to a scrape miss on
            # an otherwise-legitimate regeneration — this prevents that.)
            authors_assignment = (
                'authors = if_not_exists(authors, :authors)' if author_review
                else 'authors = :authors'
            )

            table.update_item(
                Key={'post_id': post_id},
                UpdateExpression=f'''
                    SET #url = :url,
                        title = :title,
                        {authors_assignment},
                        date_published = :date_published,
                        date_updated = :date_updated,
                        tags = :tags,
                        content = :content,
                        last_crawled = :last_crawled,
                        summary = :empty,
                        label = :empty,
                        label_confidence = :zero,
                        label_generated = :empty,
                        #source = :source,{filter_expression_parts}{review_expression}
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
                    ':date_updated': new_date,
                    ':tags': 'End User Computing, Builder.AWS',
                    ':content': metadata['content'],
                    ':last_crawled': datetime.now(timezone.utc).isoformat(),
                    ':empty': '',
                    ':zero': 0,
                    ':source': metadata['source'],
                    **filter_values,
                    **review_values,
                }
            )
        else:
            # Unchanged: do NOT overwrite summary, label, authors, content, title,
            # or dates — leave the existing article in place. Only bump
            # last_crawled and the keyword-filter fields. if_not_exists backfills
            # any field a malformed row happens to be missing, without clobbering
            # good data (and re-scraped values that could be noisy/corrupt never
            # replace what's already stored).
            table.update_item(
                Key={'post_id': post_id},
                UpdateExpression=f'''
                    SET last_crawled = :last_crawled,
                        #url = if_not_exists(#url, :url),
                        title = if_not_exists(title, :title),
                        authors = if_not_exists(authors, :authors),
                        content = if_not_exists(content, :content),
                        date_published = if_not_exists(date_published, :date_published),
                        date_updated = if_not_exists(date_updated, :date_updated),
                        tags = if_not_exists(tags, :tags),
                        #source = if_not_exists(#source, :source),{filter_expression_parts}
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
                    ':date_updated': new_date,
                    ':tags': 'End User Computing, Builder.AWS',
                    ':content': metadata['content'],
                    ':last_crawled': datetime.now(timezone.utc).isoformat(),
                    ':source': metadata['source'],
                    **filter_values,
                }
            )

        debug_print(f"Successfully saved post_id: {post_id}")
        return True

    except Exception as e:
        print(f"  Error saving to DynamoDB: {e}")
        debug_print(f"Error in save_to_dynamodb: {e}")
        import traceback
        debug_print(traceback.format_exc())
        return False


def lambda_handler(event, context):
    """
    Lambda handler for Builder.AWS crawler with Playwright
    
    Parameters:
    - max_posts (optional): Limit number of posts to process
    - debug (optional): Enable debug mode for verbose logging
    - target_url (optional): Process only a specific URL for debugging
    - environment (optional): 'staging' or 'production' — selects the table
    - table_name (optional): explicit table override (wins over environment)
    """

    global DEBUG_MODE

    if not PLAYWRIGHT_AVAILABLE:
        print("Playwright not available, using requests-based fallback")

    # Enable debug mode if requested via event
    if event and event.get('debug'):
        DEBUG_MODE = True
        debug_print("Debug mode enabled via event parameter")

    # Resolve the target table per invocation so a staging crawl never writes to
    # the production table (see resolve_table_name).
    table_name = resolve_table_name(event)
    print("Starting Builder.AWS Playwright Crawler")
    print(f"Target table: {table_name}")
    debug_print(f"Event parameters: {json.dumps(event) if event else 'None'}")

    max_posts = event.get('max_posts') if event else None
    target_url = event.get('target_url') if event else None
    table = dynamodb.Table(table_name)
    
    posts_processed = 0
    posts_updated = 0
    posts_skipped = 0
    # EUC filter tracking counters
    posts_accepted = 0
    posts_keyword_rejected = 0
    
    try:
        # If target_url is provided, process only that URL
        if target_url:
            debug_print(f"Processing single target URL: {target_url}")
            all_urls = [(target_url, '', None)]
        else:
            # Get sitemaps
            sitemaps = get_article_sitemaps()
            print(f"Found {len(sitemaps)} article sitemaps")
            
            if not sitemaps:
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': 'No sitemaps found'})
                }
            
            # Collect EUC-related URLs using two-stage filter
            all_urls = []
            
            for sitemap_url in sitemaps:
                try:
                    debug_print(f"Processing sitemap: {sitemap_url}")
                    response = requests.get(sitemap_url, timeout=30)
                    response.raise_for_status()
                    
                    root = ET.fromstring(response.text)
                    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                    
                    url_count = 0
                    for url_elem in root.findall('.//ns:url', namespace):
                        loc = url_elem.find('ns:loc', namespace)
                        lastmod = url_elem.find('ns:lastmod', namespace)
                        
                        if loc is not None:
                            url = loc.text
                            title = extract_title_from_slug(url)
                            
                            result = is_euc_related(url, title)
                            if result.accepted:
                                date = lastmod.text if lastmod is not None else ''
                                all_urls.append((url, date, result))
                                url_count += 1
                                posts_accepted += 1
                            else:
                                # Log keyword rejection details
                                posts_keyword_rejected += 1
                                print(f"  ✗ Keyword rejected: {url} | {title} | Reason: {result.reason}")
                    
                    debug_print(f"Found {url_count} EUC-related URLs in sitemap")
                    
                except Exception as e:
                    print(f"Error processing sitemap {sitemap_url}: {e}")
                    continue
        
        print(f"\nFound {len(all_urls)} EUC-related URLs to process")
        
        if max_posts:
            all_urls = all_urls[:max_posts]
            print(f"Limited to {max_posts} posts")
        
        # Process each URL — use Playwright if available, otherwise requests
        if PLAYWRIGHT_AVAILABLE:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                for idx, (url, date, filter_result) in enumerate(all_urls, 1):
                    print(f"\n[{idx}/{len(all_urls)}] Processing: {url}")
                    
                    metadata = extract_page_content(page, url)

                    if metadata:
                        # Raw sitemap lastmod — the change-detection signal in
                        # save_to_dynamodb. Stored unparsed to match the value the
                        # multi-source crawler writes, so unchanged posts compare equal.
                        metadata['date_updated'] = date
                        if filter_result is not None:
                            metadata['ai_validation_result'] = 'pending'
                            metadata['ai_validation_explanation'] = ''
                            metadata['filter_stage'] = filter_result.stage
                            metadata['filter_reason'] = filter_result.reason
                        
                        if save_to_dynamodb(table, metadata):
                            posts_updated += 1
                            print(f"  ✓ Saved: {metadata['title'][:60]}...")
                        else:
                            print(f"  ✗ Failed to save")
                    else:
                        posts_skipped += 1
                        print(f"  Skipped (no content extracted)")
                    
                    posts_processed += 1
                    time.sleep(1)
                
                browser.close()
        else:
            # Requests-based fallback — no JS rendering
            for idx, (url, date, filter_result) in enumerate(all_urls, 1):
                print(f"\n[{idx}/{len(all_urls)}] Processing (requests): {url}")
                
                metadata = extract_page_content_requests(url, date)

                if metadata:
                    # Raw sitemap lastmod — change-detection signal (see above).
                    metadata['date_updated'] = date
                    if filter_result is not None:
                        metadata['ai_validation_result'] = 'pending'
                        metadata['ai_validation_explanation'] = ''
                        metadata['filter_stage'] = filter_result.stage
                        metadata['filter_reason'] = filter_result.reason
                    
                    if save_to_dynamodb(table, metadata):
                        posts_updated += 1
                        print(f"  ✓ Saved: {metadata['title'][:60]}...")
                    else:
                        print(f"  ✗ Failed to save")
                else:
                    posts_skipped += 1
                    print(f"  Skipped (no content extracted)")
                
                posts_processed += 1
                time.sleep(0.5)
        
        # Log summary counts
        print(f"\n{'='*60}")
        print(f"EUC Filter Summary:")
        print(f"  Posts keyword-accepted: {posts_accepted}")
        print(f"  Posts keyword-rejected: {posts_keyword_rejected}")
        print(f"{'='*60}")
        
        print(f"\nCrawl Summary:")
        print(f"  Posts processed: {posts_processed}")
        print(f"  Posts updated: {posts_updated}")
        print(f"  Posts skipped: {posts_skipped}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Builder.AWS Playwright crawl completed',
                'posts_processed': posts_processed,
                'posts_updated': posts_updated,
                'posts_skipped': posts_skipped,
                'posts_accepted': posts_accepted,
                'posts_keyword_rejected': posts_keyword_rejected
            })
        }
        
    except Exception as e:
        print(f"Error in lambda_handler: {e}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
