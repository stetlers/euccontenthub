```python
import boto3
from datetime import datetime, timedelta
import time
import requests
from bs4 import BeautifulSoup
import feedparser
import json
import re

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

# Diagnostic counters for root cause analysis
diagnostics = {
    'url_filtering_issues': [],
    'date_parsing_issues': [],
    'storage_issues': [],
    'crawler_logic_issues': [],
    'content_detection_issues': [],
    'metadata_extraction_issues': [],
    'filtering_criteria_issues': []
}

# Check for the specific Amazon WorkSpaces blog post from March 2, 2026
print("="*100)
print("STAGING CRAWLER DIAGNOSTIC REPORT - Amazon WorkSpaces Graphics G6 Post")
print("="*100)
print(f"Target URL: https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/")
print(f"Expected Date: 2026-03-02")
print(f"Diagnostic Time: {datetime.now().isoformat()}")
print("="*100)
print()

target_url = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'
target_date = '2026-03-02'

# DIAGNOSTIC STEP 1: Database Storage Check
print("STEP 1: DATABASE STORAGE VERIFICATION")
print("-" * 80)
post_found_in_db = False
try:
    response = table.get_item(Key={'url': target_url})
    
    if 'Item' in response:
        post = response['Item']
        post_found_in_db = True
        print("✓ POST FOUND in staging database!")
        print(f"  Title: {post.get('title', 'N/A')}")
        print(f"  Source: {post.get('source', 'N/A')}")
        print(f"  Date: {post.get('date', 'N/A')}")
        print(f"  Last crawled: {post.get('last_crawled', 'Never')}")
        print(f"  Storage timestamp: {post.get('timestamp', 'N/A')}")
        print(f"  Tags: {post.get('tags', [])}")
        print(f"  Categories: {post.get('categories', [])}")
        
        # Check for filtering flags
        if post.get('filtered'):
            print(f"  ⚠ FILTERED FLAG: {post.get('filtered')}")
            print(f"  Filter reason: {post.get('filter_reason', 'N/A')}")
            diagnostics['filtering_criteria_issues'].append(f"Post filtered: {post.get('filter_reason', 'Unknown')}")
        
        print("\n✓ STORAGE MECHANISM: Working correctly - post is stored")
        print()
    else:
        print("✗ POST NOT FOUND in staging database!")
        print(f"  Target URL: {target_url}")
        print(f"  Expected date: {target_date}")
        diagnostics['storage_issues'].append("Target post not found in database")
        print("\n✗ STORAGE MECHANISM: Post missing - investigating upstream issues...")
        print()
        
        # DIAGNOSTIC: Verify post exists on the web
        print("  → Verifying post existence on AWS blog website...")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            web_response = requests.get(target_url, headers=headers, timeout=15)
            
            if web_response.status_code == 200:
                soup = BeautifulSoup(web_response.content, 'html.parser')
                
                # Extract comprehensive metadata with multiple fallback strategies
                title_tag = soup.find('h1') or soup.find('title') or soup.find('meta', {'property': 'og:title'})
                
                # Enhanced date extraction with multiple strategies
                date_meta = (
                    soup.find('meta', {'property': 'article:published_time'}) or 
                    soup.find('meta', {'name': 'publishdate'}) or 
                    soup.find('meta', {'name': 'date'}) or
                    soup.find('meta', {'property': 'og:published_time'}) or
                    soup.find('time', {'class': 'published'}) or 
                    soup.find('time', {'datetime': True}) or
                    soup.find('time')
                )
                
                # Check for alternative date patterns in page content
                date_patterns = [
                    r'Published[:\s]+(\d{4}-\d{2}-\d{2})',
                    r'Posted[:\s]+(\d{4}-\d{2}-\d{2})',
                    r'(\d{2}/\d{2}/\d{4})',
                    r'(\w+ \d{1,2},? \d{4})',
                    r'datetime="([^"]+)"',
                    r'"datePublished":\s*"([^"]+)"',
                    r'"publishDate":\s*"([^"]+)"'
                ]
                
                found_dates = []
                page_text = soup.get_text()
                page_html = str(soup)
                for pattern in date_patterns:
                    matches = re.findall(pattern, page_html + page_text)
                    found_dates.extend(matches)
                
                # Check for JSON-LD structured data
                json_ld_scripts = soup.find_all('script', {'type': 'application/ld+json'})
                json_ld_dates = []
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            if 'datePublished' in data:
                                json_ld_dates.append(data['datePublished'])
                            if 'dateCreated' in data:
                                json_ld_dates.append(data['dateCreated'])
                        elif isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict):
                                    if 'datePublished' in item:
                                        json_ld_dates.append(item['datePublished'])
                    except json.JSONDecodeError:
                        pass
                
                if title_tag:
                    extracted_title = title_tag.get_text().strip() if hasattr(title_tag, 'get_text') else title_tag.get('content', '')
                    print(f"    ✓ Post EXISTS on web")
                    print(f"    Title: {extracted_title[:80]}...")
                    
                    all_date_candidates = []
                    
                    if date_meta:
                        date_content = date_meta.get('content') or date_meta.get('datetime') or date_meta.get_text()
                        all_date_candidates.append(('metadata', date_content))
                        print(f"    ✓ Date metadata found: {date_content}")
                    
                    if json_ld_dates:
                        for jld in json_ld_dates:
                            all_date_candidates.append(('json-ld', jld))
                        print(f"    ✓ JSON-LD dates found: {json_ld_dates}")
                    
                    if found_dates:
                        for fd in found_dates[:3]:
                            all_date_candidates.append(('pattern', fd))
                        print(f"    ✓ Pattern-matched dates: {found_dates[:3]}")
                    
                    # Comprehensive date parsing with all candidates
                    parsed_dates = []
                    for source, date_content in all_date_candidates:
                        try:
                            parsed_date = None
                            date_str = str(date_content).strip()
                            
                            # ISO 8601 format with timezone
                            if 'T' in date_str and ('Z' in date_str or '+' in date_str or '-' in date_str[-6:]):
                                parsed_date = datetime.fromisoformat(date_str.replace('Z', '+00:00').split('+')[0].split('-', 3)[:3][0] if date_str.count('-') > 2 else date_str.replace('Z', '+00:00'))
                            # YYYY-MM-DD format
                            elif re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
                                parsed_date = datetime.strptime(date_str[:10], '%Y-%m-%d')
                            # MM/DD/YYYY format
                            elif re.match(r'^\d{2}/\d{2}/\d{4}', date_str):
                                parsed_date = datetime.strptime(date_str[:10], '%m/%d/%Y')
                            # Month DD, YYYY format
                            elif re.match(r'^\w+ \d{1,2},? \d{4}', date_str):
                                # Try multiple month formats
                                for fmt in ['%B %d, %Y', '%b %d, %Y', '%B %d %Y', '%b %d %Y']:
                                    try:
                                        parsed_date = datetime.strptime(date_str.split()[0:3].__str__().replace('[', '').replace(']', '').replace("'", '').replace(',', ' '), fmt)
                                        break
                                    except:
                                        continue
                            
                            if parsed_date:
                                parsed_dates.append({
                                    'source': source,
                                    'original': date_content,
                                    'parsed': parsed_date,
                                    'formatted': parsed_date.strftime('%Y-%m-%d')
                                })
                        except Exception as e:
                            diagnostics['date_parsing_issues'].append(f"Could not parse date '{date_content}' from {source}: {e}")
                    
                    if parsed_dates:
                        print(f"\n    Parsed dates ({len(parsed_dates)} total):")
                        for pd in parsed_dates:
                            match_indicator = "✓✓✓" if pd['formatted'] == target_date else "   "
                            print(f"      {match_indicator} [{pd['source']}] {pd['formatted']} (from: {pd['original']})")
                        
                        # Check if any parsed date matches target
                        matching_dates = [pd for pd in parsed_dates if pd['formatted'] == target_date]
                        if matching_dates:
                            print(f"\n    ✓✓✓ Date MATCHES expected: {target_date}")
                            print(f"        Found in: {', '.join([pd['source'] for pd in matching_dates])}")
                            print("\n    ✗✗ ROOT CAUSE INDICATOR: Post has correct date but NOT stored")
                            print("       → Metadata extraction logic may have issues")
                            print("       → Check crawler's date field selection priority")
                            diagnostics['metadata_extraction_issues'].append(f"Correct date found in {len(matching_dates)} sources but post not stored")
                        else:
                            most_common_date = max(set([pd['formatted'] for pd in parsed_dates]), key=[pd['formatted'] for pd in parsed_dates].count)
                            print(f"\n    ⚠ Date MISMATCH: Expected {target_date}, most common parsed: {most_common_date}")
                            diagnostics['date_parsing_issues'].append(f"Date mismatch: expected {target_date}, found {most_common_date}")
                    else:
                        print(f"\n    ✗ Could not parse any dates from available metadata")
                        if not date_meta and not json_ld_dates:
                            print(f"    ✗✗ ROOT CAUSE: No standard date metadata in HTML")
                            diagnostics['date_parsing_issues'].append("No parseable date metadata in HTML")
                        else:
                            print(f"    ✗✗ ROOT CAUSE: Date metadata exists but parsing failed")
                            diagnostics['metadata_extraction_issues'].append("Date metadata exists but all parsing attempts failed")
                    
                    # Check for additional metadata that crawler might use
                    print(f"\n    Additional metadata check:")
                    author_meta = soup.find('meta', {'name': 'author'}) or soup.find('meta', {'property': 'article:author'})
                    category_meta = soup.find('meta', {'property': 'article:section'}) or soup.find('meta', {'name': 'category'})
                    description_meta = soup.find('meta', {'name': 'description'}) or soup.find('meta', {'property': 'og:description'})
                    
                    if author_meta:
                        print(f"      Author: {author_meta.get('content', 'N/A')}")
                    if category_meta:
                        print(f"      Category: {category_meta.get('content', 'N/A')}")
                    if description_meta:
                        print(f"      Description: {description_meta.get('content', 'N/A')[:60]}...")
                    
                    print("\n    ✗✗ ROOT CAUSE INDICATOR: Post exists on web but NOT in database")
                    print("       → Crawler is NOT detecting/storing this post")
                    print("       → Possible issues:")
                    print("         1. Date extraction logic not handling this date format")
                    print("         2. Date filtering excluding this specific date")
                    print("         3. Metadata extraction selecting wrong date field")
                    print("         4. URL pattern not matching crawler rules")
                    diagnostics['crawler_logic_issues'].append("Post exists on web but not stored in database")
                else:
                    print("    ⚠ Could not extract title from page - possible HTML structure issue")
                    diagnostics['content_detection_issues'].append("Could not parse HTML structure - title tag missing")
                    
            elif web_response.status_code == 404:
                print(f"    ✗ Post returns 404 - Not published or URL incorrect")
                diagnostics['url_filtering_issues'].append("Target URL returns 404")
            else:
                print(f"    ⚠ Unexpected HTTP status: {web_response.status_code}")
                diagnostics['crawler_logic_issues'].append(f"Unexpected HTTP status: {web_response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"    ✗ Request timeout - network or performance issue")
            diagnostics['crawler_logic_issues'].append("Request timeout when fetching post")
        except requests.exceptions.RequestException as e:
            print(f"    ✗ Request failed: {str(e)}")
            diagnostics['crawler_logic_issues'].append(f"Request exception: {str(e)}")
        print()
        
except Exception as e:
    print(f"✗ Database query error: {str(e)}")
    diagnostics['storage_issues'].append(f"Database query failed: {str(e)}")
    print()

# DIAGNOSTIC STEP 2: URL Filtering Analysis
print("\nSTEP 2: URL FILTERING ANALYSIS")
print("-" * 80)
das_posts = []  # Initialize das_posts for later use
try:
    # Check for URL variations and similar posts
    url_components = {
        'base_path': 'aws.amazon.com/blogs/desktop-and-application-streaming/',
        'slug_parts': ['amazon-workspaces', 'launches-graphics', 'g6', 'gr6', 'g6f', 'bundles']
    }
    
    print(f"Checking if blog path '{url_components['base_path']}' is being crawled...")
    
    response = table.scan(
        FilterExpression='contains(