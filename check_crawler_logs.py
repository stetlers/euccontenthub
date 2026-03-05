```python
"""
Check crawler Lambda logs from the most recent invocation
Enhanced to investigate missing Amazon WorkSpaces blog post detection
Includes comprehensive analysis of date filtering, URL patterns, and stage comparison
"""
import boto3
from datetime import datetime, timedelta
import re
import json

logs = boto3.client('logs', region_name='us-east-1')

print("=" * 80)
print("CRAWLER LAMBDA LOGS INVESTIGATION")
print("=" * 80)

# Target blog post URL to investigate
TARGET_URL = "https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/"
TARGET_DATE = "2026-03-02"
TARGET_TITLE_KEYWORDS = ["workspaces", "graphics", "g6"]
TARGET_CATEGORY = "desktop-and-application-streaming"

def extract_date_from_message(message):
    """Extract and parse date information from log messages"""
    # Common date formats in logs
    date_patterns = [
        r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
        r'(\d{2}/\d{2}/\d{4})',  # MM/DD/YYYY
        r'date[:\s]+["\']?(\d{4}-\d{2}-\d{2})',  # date: YYYY-MM-DD
        r'published[:\s]+["\']?(\d{4}-\d{2}-\d{2})',  # published: YYYY-MM-DD
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, message)
        if match:
            return match.group(1)
    return None

def extract_url_from_message(message):
    """Extract URLs from log messages"""
    url_match = re.search(r'https?://[^\s\'"]+', message)
    if url_match:
        return url_match.group(0).rstrip(',;')
    return None

def analyze_date_filtering(events):
    """Analyze date filtering logic and identify cutoff dates"""
    date_filters = []
    cutoff_dates = []
    
    for event in events:
        message = event["message"].strip()
        
        # Look for date filtering logic
        if any(keyword in message.lower() for keyword in ['date filter', 'cutoff', 'before', 'after', 'date range']):
            date_filters.append(message)
            extracted_date = extract_date_from_message(message)
            if extracted_date:
                cutoff_dates.append(extracted_date)
        
        # Look for comparison operators with dates
        if re.search(r'(>|<|>=|<=|before|after|since)\s*\d{4}-\d{2}-\d{2}', message):
            date_filters.append(message)
    
    return date_filters, cutoff_dates

def analyze_url_patterns(events):
    """Analyze URL pattern matching and category filtering"""
    url_patterns = []
    category_filters = []
    matched_urls = []
    rejected_urls = []
    
    for event in events:
        message = event["message"].strip()
        
        # URL pattern definitions
        if 'pattern' in message.lower() or 'regex' in message.lower() or 'url match' in message.lower():
            url_patterns.append(message)
        
        # Category filtering
        if 'category' in message.lower() and ('filter' in message.lower() or 'match' in message.lower()):
            category_filters.append(message)
        
        # URLs that were matched/accepted
        if any(keyword in message.lower() for keyword in ['matched', 'accepted', 'processing', 'crawling']):
            url = extract_url_from_message(message)
            if url:
                matched_urls.append((message, url))
        
        # URLs that were rejected/filtered
        if any(keyword in message.lower() for keyword in ['rejected', 'filtered', 'skipped', 'excluded', 'ignored']):
            url = extract_url_from_message(message)
            if url:
                rejected_urls.append((message, url))
    
    return url_patterns, category_filters, matched_urls, rejected_urls

def check_staging_vs_production(events):
    """Compare staging and production behavior"""
    staging_refs = []
    production_refs = []
    env_config = []
    
    for event in events:
        message = event["message"].strip()
        
        if 'staging' in message.lower():
            staging_refs.append(message)
        
        if 'production' in message.lower() or 'prod' in message.lower():
            production_refs.append(message)
        
        if any(keyword in message.lower() for keyword in ['environment', 'config', 'stage']):
            env_config.append(message)
    
    return staging_refs, production_refs, env_config

def analyze_log_events(events):
    """Comprehensive analysis of log events for crawler behavior"""
    print(f"\nAnalyzing {len(events)} log events")
    print(f"Time range: {datetime.fromtimestamp(events[0]['timestamp'] / 1000)} to {datetime.fromtimestamp(events[-1]['timestamp'] / 1000)}")
    print("=" * 80)
    
    # Tracking variables
    found_target_url = False
    found_target_category = False
    found_target_keywords = False
    crawl_errors = []
    processed_urls = []
    all_urls = []
    
    # Detailed analysis
    date_filters, cutoff_dates = analyze_date_filtering(events)
    url_patterns, category_filters, matched_urls, rejected_urls = analyze_url_patterns(events)
    staging_refs, production_refs, env_config = check_staging_vs_production(events)
    
    print("\n📋 LOG MESSAGES:")
    print("-" * 80)
    for event in events:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event["message"].strip()
        
        # Highlight important messages
        prefix = ""
        if "error" in message.lower() or "exception" in message.lower():
            prefix = "❌ "
            crawl_errors.append(message)
        elif "warning" in message.lower():
            prefix = "⚠️  "
        elif any(kw in message.lower() for kw in TARGET_TITLE_KEYWORDS):
            prefix = "🎯 "
            found_target_keywords = True
        elif TARGET_CATEGORY in message.lower():
            prefix = "📂 "
            found_target_category = True
        
        print(f'{prefix}{timestamp.strftime("%H:%M:%S")} | {message}')
        
        # Track URLs
        url = extract_url_from_message(message)
        if url:
            all_urls.append(url)
            if TARGET_URL in url or all(kw in url.lower() for kw in ['workspaces', 'graphics', 'g6']):
                found_target_url = True
            if "processing" in message.lower() or "crawling" in message.lower():
                processed_urls.append(url)
    
    # Print comprehensive investigation summary
    print("\n" + "=" * 80)
    print("🔍 INVESTIGATION SUMMARY")
    print("=" * 80)
    print(f"\n📌 TARGET INFORMATION:")
    print(f"   URL: {TARGET_URL}")
    print(f"   Date: {TARGET_DATE}")
    print(f"   Category: {TARGET_CATEGORY}")
    print(f"   Keywords: {', '.join(TARGET_TITLE_KEYWORDS)}")
    
    print(f"\n✅ DETECTION STATUS:")
    print(f"   Target URL found: {found_target_url}")
    print(f"   Target category found: {found_target_category}")
    print(f"   Target keywords found: {found_target_keywords}")
    print(f"   Total unique URLs detected: {len(set(all_urls))}")
    print(f"   Total URLs processed: {len(processed_urls)}")
    print(f"   Total errors: {len(crawl_errors)}")
    
    # Date filtering analysis
    print(f"\n📅 DATE FILTERING ANALYSIS:")
    if date_filters:
        print(f"   Found {len(date_filters)} date filter references")
        for df in date_filters[:5]:
            print(f"   → {df}")
        if cutoff_dates:
            print(f"\n   Detected cutoff dates: {', '.join(set(cutoff_dates))}")
            print(f"   Target date ({TARGET_DATE}) comparison:")
            for cutoff in set(cutoff_dates):
                try:
                    target = datetime.strptime(TARGET_DATE, '%Y-%m-%d')
                    cutoff_dt = datetime.strptime(cutoff, '%Y-%m-%d')
                    if target > cutoff_dt:
                        print(f"   ⚠️  Target is AFTER {cutoff} - may be filtered out")
                    else:
                        print(f"   ✓ Target is BEFORE {cutoff} - should pass filter")
                except:
                    pass
    else:
        print("   ⚠️  No explicit date filtering detected in logs")
    
    # URL pattern analysis
    print(f"\n🔗 URL PATTERN ANALYSIS:")
    print(f"   URL patterns defined: {len(url_patterns)}")
    if url_patterns:
        for pattern in url_patterns[:3]:
            print(f"   → {pattern}")
    print(f"   Category filters: {len(category_filters)}")
    if category_filters:
        for cf in category_filters[:3]:
            print(f"   → {cf}")
    print(f"   Matched URLs: {len(matched_urls)}")
    print(f"   Rejected URLs: {len(rejected_urls)}")
    
    if rejected_urls:
        print(f"\n   Recently rejected URLs (showing first 5):")
        for msg, url in rejected_urls[:5]:
            print(f"   ✗ {url}")
            print(f"     Reason: {msg[:100]}...")
    
    # Environment analysis
    print(f"\n🌍 ENVIRONMENT ANALYSIS:")
    print(f"   Staging references: {len(staging_refs)}")
    print(f"   Production references: {len(production_refs)}")
    if env_config:
        print(f"   Configuration entries found: {len(env_config)}")
        for config in env_config[:3]:
            print(f"   → {config}")
    
    # Errors
    if crawl_errors:
        print(f"\n❌ ERRORS DETECTED ({len(crawl_errors)}):")
        for error in crawl_errors[:5]:
            print(f"   • {error}")
    
    # Root cause analysis
    print("\n" + "=" * 80)
    print("🔬 ROOT CAUSE ANALYSIS")
    print("=" * 80)
    
    if not found_target_url and not found_target_keywords and not found_target_category:
        print("\n⚠️  CRITICAL: No trace of target blog post found in logs")
        print("\nPossible causes:")
        print("   1. Date filter excluding March 2026 posts (future date)")
        print("   2. Blog post not yet published on staging.awseuccontent.com")
        print("   3. RSS feed not including this category/post")
        print("   4. URL pattern not matching the blog post URL")
        print("   5. Crawler configured to skip 'desktop-and-application-streaming' category")
    elif found_target_category or found_target_keywords:
        print("\n⚠️  PARTIAL: Target category/keywords found but URL not processed")
        print("\nPossible causes:")
        print("   1. Post detected but filtered out by date")
        print("   2. Post detected but skipped due to content filters")
        print("   3. RSS feed includes category but not this specific post")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("💡 RECOMMENDATIONS")
    print("=" * 80)
    
    recommendations = []
    
    if not found_target_category:
        recommendations.append("Check if 'desktop-and-application-streaming' is in the crawler's category whitelist")
        recommendations.append("Verify the RSS feed URL includes this blog category")
    
    if cutoff_dates and TARGET_DATE > max(cutoff_dates):
        recommendations.append(f"⚠️  CRITICAL: Target date ({TARGET_DATE}) is after detected cutoff dates")
        recommendations.append("Update date filter configuration to include dates through March 2026")
        recommendations.append("Check if crawler has a hardcoded date limit")
    
    if not found_target_url:
        recommendations.append("Verify blog post exists at staging.awseuccontent.com")
        recommendations.append("Check if post URL matches crawler's URL pattern regex")
        recommendations.append("Test crawler with explicit URL parameter if supported")
    
    if not staging_refs and not production_refs:
        recommendations.append("Verify crawler is running against correct environment (staging vs production)")
    
    recommendations.append("Review crawler source code for date filtering logic")
    recommendations.append("Check DynamoDB table for existing entries that might cause deduplication")
    recommendations.append("Compare staging crawler config with production config")
    
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec}")
    
    print("\n" + "=" * 80)
    print("🔧 NEXT STEPS")
    print("=" * 80)
    print("   1. Check crawler Lambda environment variables for date filters")
    print("   2. Review crawler source code date comparison logic")
    print("   3. Verify staging blog post publication status")
    print("   4. Test RSS feed manually for the target category")
    print("   5. Check DynamoDB for duplicate detection issues")
    print("   6. Compare with production crawler logs for same time period")
    print("   7. Run crawler in debug mode with verbose logging")
    print("=" * 80)

try:
    # Try last 5 minutes first
    print("\n🔍 Checking logs from last 5 minutes...")
    response = logs.filter_log_events(
        logGroupName='/aws/lambda/aws-blog-crawler',
        startTime=int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)
    )
    
    if response['events']:
        analyze_log_events(response['events'])
    else:
        print("   No logs found in last 5 minutes")
        print("\n🔍 Checking logs from last 30 minutes...")
        
        response = logs.filter_log_events(
            logGroupName='/aws/lambda/aws-blog-crawler',
            startTime=int((datetime.now() - timedelta(minutes=30)).timestamp() * 1000)
        )
        
        if response['events']:
            analyze_log_events(response['events'][-200:])  # Analyze last 200 events
        else:
            print("   No logs found in last 30 minutes")
            print("\n🔍 Checking logs from last 24 hours...")
            
            response = logs.filter_log_events(
                logGroupName='/aws/lambda/aws-blog-crawler',
                startTime=int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)
            )
            
            if response['events']:
                print(f"   Found {len(response['events'])} events in last 24 hours")
                analyze_log_events(response['events'][-200:])  # Analyze last 200 events
            else:
                print("\n❌ No logs found in last 24 hours")
                print("\n🔧 TROUBLESHOOTING:")
                print("   1. Verify Lambda function name is 'aws-blog-crawler'")
                print("   2. Check if crawler has been invoked recently (CloudWatch Events/EventBridge)")
                print("   3. Verify IAM permissions for logs:FilterLogEvents")
                print("   4.