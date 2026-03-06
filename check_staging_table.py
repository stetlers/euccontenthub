```python
#!/usr/bin/env python3
"""Check what's in the staging table and debug crawler issues"""

import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
import json
import sys
import requests
from urllib.parse import urlparse

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')
logs_client = boto3.client('logs', region_name='us-east-1')

def check_specific_post(search_title):
    """Search for a specific post by title substring"""
    try:
        response = table.scan(
            FilterExpression='contains(title, :title)',
            ExpressionAttributeValues={':title': search_title}
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Error searching for specific post: {e}")
        return []

def check_recent_posts(days=7):
    """Check for posts published in the last N days"""
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    try:
        response = table.scan(
            FilterExpression='date_published >= :cutoff',
            ExpressionAttributeValues={':cutoff': cutoff_date}
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Error checking recent posts: {e}")
        return []

def check_posts_by_date(target_date):
    """Check for posts published on a specific date"""
    try:
        response = table.scan(
            FilterExpression='date_published = :date',
            ExpressionAttributeValues={':date': target_date}
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Error checking posts by date: {e}")
        return []

def check_posts_by_date_range(start_date, end_date):
    """Check for posts published within a date range"""
    try:
        response = table.scan(
            FilterExpression='date_published BETWEEN :start AND :end',
            ExpressionAttributeValues={
                ':start': start_date,
                ':end': end_date
            }
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Error checking posts by date range: {e}")
        return []

def check_posts_by_url_pattern(url_pattern):
    """Search for posts by URL pattern"""
    try:
        response = table.scan(
            FilterExpression='contains(#url, :pattern)',
            ExpressionAttributeNames={'#url': 'url'},
            ExpressionAttributeValues={':pattern': url_pattern}
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Error searching by URL pattern: {e}")
        return []

def check_posts_by_source(source_pattern):
    """Search for posts by source pattern"""
    try:
        response = table.scan(
            FilterExpression='contains(#source, :pattern)',
            ExpressionAttributeNames={'#source': 'source'},
            ExpressionAttributeValues={':pattern': source_pattern}
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Error searching by source pattern: {e}")
        return []

def verify_url_accessibility(url):
    """Verify if a URL is accessible via HTTP request"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; AWS Blog Crawler Debug/1.0)'
        }
        response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        return {
            'accessible': response.status_code == 200,
            'status_code': response.status_code,
            'final_url': response.url,
            'headers': dict(response.headers)
        }
    except requests.RequestException as e:
        return {
            'accessible': False,
            'error': str(e)
        }

def check_staging_domain_posts():
    """Check for posts from staging.awseuccontent.com domain"""
    try:
        response = table.scan(
            FilterExpression='contains(#source, :domain) OR contains(#url, :domain)',
            ExpressionAttributeNames={
                '#source': 'source',
                '#url': 'url'
            },
            ExpressionAttributeValues={':domain': 'staging.awseuccontent.com'}
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Error checking staging domain posts: {e}")
        return []

def analyze_date_distribution(all_posts):
    """Analyze the distribution of posts by date to identify gaps"""
    date_counts = {}
    for post in all_posts:
        date = post.get('date_published', 'Unknown')
        date_counts[date] = date_counts.get(date, 0) + 1
    
    return dict(sorted(date_counts.items(), reverse=True))

def check_crawler_metadata():
    """Check for crawler metadata or state information"""
    try:
        # Look for any metadata entries (if crawler stores state)
        response = table.scan(
            FilterExpression='attribute_exists(crawler_run_timestamp) OR attribute_exists(last_crawled)',
            Limit=10
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Note: No crawler metadata found (this may be expected): {e}")
        return []

def check_all_attributes(all_posts):
    """Analyze all attributes present in posts to understand data structure"""
    all_attributes = set()
    attribute_examples = {}
    
    for post in all_posts[:100]:  # Sample first 100 posts
        for key, value in post.items():
            all_attributes.add(key)
            if key not in attribute_examples:
                attribute_examples[key] = str(value)[:100]
    
    return sorted(list(all_attributes)), attribute_examples

def check_url_in_all_fields(target_keyword):
    """Search for a keyword across all text fields in posts"""
    try:
        response = table.scan()
        all_posts = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            all_posts.extend(response.get('Items', []))
        
        matches = []
        for post in all_posts:
            # Search in all string fields
            for key, value in post.items():
                if isinstance(value, str) and target_keyword.lower() in value.lower():
                    matches.append(post)
                    break
        
        return matches
    except ClientError as e:
        print(f"Error in comprehensive search: {e}")
        return []

def analyze_source_patterns(all_posts):
    """Analyze source URL patterns to identify crawler coverage"""
    source_domains = {}
    for post in all_posts:
        source = post.get('source', 'Unknown')
        url = post.get('url', '')
        
        # Extract domain from source or URL
        domain = 'Unknown'
        if source != 'Unknown':
            if '://' in source:
                domain = source.split('://')[1].split('/')[0]
            else:
                domain = source.split('/')[0]
        elif url:
            if '://' in url:
                domain = url.split('://')[1].split('/')[0]
        
        source_domains[domain] = source_domains.get(domain, 0) + 1
    
    return dict(sorted(source_domains.items(), key=lambda x: x[1], reverse=True))

def check_for_exact_url(url_fragment):
    """Check if any post contains exact URL fragment"""
    try:
        response = table.scan()
        all_posts = response.get('Items', [])
        
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            all_posts.extend(response.get('Items', []))
        
        matches = []
        for post in all_posts:
            url = post.get('url', '')
            if url_fragment in url:
                matches.append(post)
        
        return matches
    except ClientError as e:
        print(f"Error checking for exact URL: {e}")
        return []

def analyze_date_filtering_logic(all_posts):
    """Analyze potential date filtering issues in crawler"""
    current_date = datetime.now()
    
    # Group posts by relationship to current date
    past_posts = []
    future_posts = []
    invalid_dates = []
    
    for post in all_posts:
        date_str = post.get('date_published', '')
        if not date_str or date_str == 'Unknown':
            invalid_dates.append(post)
            continue
        
        try:
            post_date = datetime.strptime(date_str, '%Y-%m-%d')
            if post_date > current_date:
                future_posts.append((post_date, post))
            else:
                past_posts.append((post_date, post))
        except ValueError:
            invalid_dates.append(post)
    
    return {
        'past_posts_count': len(past_posts),
        'future_posts_count': len(future_posts),
        'invalid_dates_count': len(invalid_dates),
        'latest_past_date': max([d for d, _ in past_posts]) if past_posts else None,
        'earliest_future_date': min([d for d, _ in future_posts]) if future_posts else None,
        'future_posts': sorted(future_posts, key=lambda x: x[0])
    }

def get_crawler_logs(log_group_name='/aws/lambda/blog-crawler', hours=24):
    """Retrieve recent crawler logs from CloudWatch"""
    try:
        start_time = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)
        end_time = int(datetime.now().timestamp() * 1000)
        
        # Get log streams
        log_streams_response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        all_events = []
        for stream in log_streams_response.get('logStreams', []):
            stream_name = stream['logStreamName']
            try:
                events_response = logs_client.get_log_events(
                    logGroupName=log_group_name,
                    logStreamName=stream_name,
                    startTime=start_time,
                    endTime=end_time,
                    limit=1000
                )
                all_events.extend(events_response.get('events', []))
            except ClientError as e:
                print(f"  Warning: Could not read stream {stream_name}: {e}")
        
        return all_events
    except ClientError as e:
        print(f"Error retrieving crawler logs: {e}")
        return []

def analyze_crawler_logs_for_post(log_events, keywords):
    """Analyze crawler logs for mentions of specific post or filtering decisions"""
    relevant_logs = []
    filtering_decisions = []
    errors = []
    
    for event in log_events:
        message = event.get('message', '')
        timestamp = datetime.fromtimestamp(event.get('timestamp', 0) / 1000)
        
        # Check for keywords related to the missing post
        if any(keyword.lower() in message.lower() for keyword in keywords):
            relevant_logs.append({
                'timestamp': timestamp,
                'message': message
            })
        
        # Check for filtering decisions
        if any(phrase in message.lower() for phrase in ['filtered', 'skipped', 'excluding', 'ignoring']):
            filtering_decisions.append({
                'timestamp': timestamp,
                'message': message
            })
        
        # Check for errors
        if any(phrase in message.lower() for phrase in ['error', 'exception', 'failed', 'warning']):
            errors.append({
                'timestamp': timestamp,
                'message': message
            })
    
    return {
        'relevant_logs': relevant_logs,
        'filtering_decisions': filtering_decisions,
        'errors': errors
    }

def check_crawler_configuration():
    """Check crawler Lambda function configuration"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Try common crawler function names
    function_names = [
        'blog-crawler',
        'aws-blog-crawler',
        'staging-blog-crawler',
        'blog-posts-crawler'
    ]
    
    for function_name in function_names:
        try:
            response = lambda_client.get_function(FunctionName=function_name)
            config = response.get('Configuration', {})
            env_vars = config.get('Environment', {}).get('Variables', {})
            
            return {
                'function_name': function_name,
                'runtime': config.get('Runtime'),
                'timeout': config.get('Timeout'),
                'memory': config.get('MemorySize'),
                'last_modified': config.get('LastModified'),
                'environment_variables': env_vars,
                'found': True
            }
        except ClientError:
            continue
    
    return {'found': False, 'message': 'Could not find crawler Lambda function'}

def verify_staging_url_direct_access():
    """Directly test access to staging.awseuccontent.com blog feed"""
    staging_urls = [
        'https://staging.awseuccontent.com/blogs/aws/feed/',
        'https://staging.awseuccontent.com/blog/feed/',
        'https://staging.awseuccontent.com/feed/',
    ]
    
    results = []
    for url in staging_urls:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; AWS Blog Crawler Debug/1.0)'
            }
            response = requests.get(url, headers=headers, timeout=15)
            results.append({
                'url': url,
                'status_code': response.status_code,
                'accessible': response.status_code == 200,
                'content_type': response.headers.get('Content-Type', 'Unknown'),
                'content_length': len(response.content),
                'contains_workspaces': 'workspaces' in response.text.lower()
            })
        except requests.RequestException as e:
            results.append({
                'url': url,
                'accessible': False,
                'error': str(e)
            })
    
    return results

def check_partial_data_by_fields(all_posts, target_date):
    """Check for posts with partial data matching target date"""
    partial_matches = []
    
    for post in all_posts:
        date_published = post.get('date_published', '')
        
        # Check if date matches
        if date_published == target_date:
            # Check for missing or incomplete fields
            missing_fields = []
            if not post.get('title') or post.get('title') == '':
                missing_fields.append('title')
            if not post.get('url') or post.get('url') == '':
                missing_fields.append('url')
            if not post.get('content') or post.get('content') == '':
                missing_fields.append('content')
            if not post.get('source') or post.get('source') == '':
                missing_fields.append('source')
            
            if missing_fields or len(post.keys()) < 5:  # Typical post should have more fields
                partial_matches.append({
                    'post': post,
                    'missing_fields': missing_fields,
                    'total_fields': len(post.keys())
                })
    
    return partial_matches

try:
    # Get total count
    response = table.scan(Select='COUNT')