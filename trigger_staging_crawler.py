```python
"""
Trigger staging crawler via API with specific URL targeting and diagnostics
"""

import json
import urllib.request
import sys
import time
from datetime import datetime

STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/crawl'
LOGS_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/logs'
STATUS_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/status'

# Specific blog post URL that needs to be crawled
TARGET_BLOG_POST = 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-launches-graphics-g6-gr6-and-g6f-bundles/'

def check_url_accessibility(url):
    """Verify the blog post URL is accessible before crawling"""
    print(f"\n🔍 Checking URL accessibility: {url}")
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; AWS-Crawler-Diagnostic/1.0)'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            status = response.status
            content_length = response.headers.get('Content-Length', 'Unknown')
            content_type = response.headers.get('Content-Type', 'Unknown')
            
            print(f"✅ URL is accessible")
            print(f"   Status: {status}")
            print(f"   Content-Type: {content_type}")
            print(f"   Content-Length: {content_length} bytes")
            return True
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP ERROR {e.code}: {e.reason}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def fetch_crawler_logs(job_id=None, limit=50):
    """Fetch recent crawler logs for diagnostics"""
    print(f"\n📋 Fetching crawler logs (limit: {limit})...")
    try:
        params = f"?limit={limit}"
        if job_id:
            params += f"&job_id={job_id}"
        
        req = urllib.request.Request(
            f"{LOGS_API}{params}",
            headers={'User-Agent': 'AWS-Staging-Crawler-Trigger/1.0'}
        )
        
        with urllib.request.urlopen(req, timeout=15) as response:
            logs = json.loads(response.read().decode('utf-8'))
        
        print(f"✅ Retrieved {len(logs.get('logs', []))} log entries")
        
        # Display relevant log entries
        for log_entry in logs.get('logs', [])[:10]:
            timestamp = log_entry.get('timestamp', 'N/A')
            level = log_entry.get('level', 'INFO')
            message = log_entry.get('message', '')
            print(f"   [{timestamp}] {level}: {message}")
        
        return logs
    except Exception as e:
        print(f"⚠️  Could not fetch logs: {e}")
        return None

def check_crawler_filters():
    """Examine crawler filtering logic via status endpoint"""
    print(f"\n🔧 Checking crawler filter configuration...")
    try:
        req = urllib.request.Request(
            f"{STATUS_API}/filters",
            headers={'User-Agent': 'AWS-Staging-Crawler-Trigger/1.0'}
        )
        
        with urllib.request.urlopen(req, timeout=15) as response:
            filters = json.loads(response.read().decode('utf-8'))
        
        print(f"✅ Filter configuration retrieved")
        print(f"\n   Active filters:")
        print(json.dumps(filters, indent=4))
        
        # Check if target URL matches any exclude patterns
        exclude_patterns = filters.get('exclude_patterns', [])
        for pattern in exclude_patterns:
            if pattern in TARGET_BLOG_POST:
                print(f"\n⚠️  WARNING: Target URL matches exclude pattern: {pattern}")
        
        return filters
    except Exception as e:
        print(f"⚠️  Could not fetch filter config: {e}")
        return None

def verify_dynamodb_writes(job_id):
    """Poll status endpoint to verify DynamoDB writes are occurring"""
    print(f"\n💾 Verifying DynamoDB writes for job {job_id}...")
    try:
        for attempt in range(3):
            time.sleep(2)  # Wait between checks
            
            req = urllib.request.Request(
                f"{STATUS_API}?job_id={job_id}",
                headers={'User-Agent': 'AWS-Staging-Crawler-Trigger/1.0'}
            )
            
            with urllib.request.urlopen(req, timeout=15) as response:
                status = json.loads(response.read().decode('utf-8'))
            
            items_written = status.get('items_written', 0)
            crawl_status = status.get('status', 'unknown')
            
            print(f"   Attempt {attempt + 1}: Status={crawl_status}, Items written={items_written}")
            
            if items_written > 0:
                print(f"✅ DynamoDB writes confirmed: {items_written} items")
                return True
        
        print(f"⚠️  No DynamoDB writes detected after 3 attempts")
        return False
    except Exception as e:
        print(f"⚠️  Could not verify DynamoDB writes: {e}")
        return False

def trigger_crawler():
    """Trigger the staging crawler with enhanced diagnostics"""
    print("=" * 80)
    print("AWS STAGING CRAWLER DIAGNOSTIC TRIGGER")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    print(f"\nAPI: {STAGING_API}")
    print(f"Target URL: {TARGET_BLOG_POST}")
    
    # Step 1: Check URL accessibility
    if not check_url_accessibility(TARGET_BLOG_POST):
        print("\n⚠️  Target URL is not accessible. Proceeding anyway for diagnostic purposes...")
    
    # Step 2: Check crawler filters
    check_crawler_filters()
    
    # Step 3: Fetch recent logs before triggering
    print(f"\n" + "=" * 80)
    print("LOGS BEFORE CRAWL TRIGGER")
    print("=" * 80)
    fetch_crawler_logs()
    
    # Step 4: Trigger the crawler
    print(f"\n" + "=" * 80)
    print("TRIGGERING CRAWLER")
    print("=" * 80)
    
    # Prepare payload with target URL and crawler options
    # Include force_refresh to ensure the specific URL is re-crawled
    # Add verbose logging flag for enhanced diagnostics
    payload = {
        'target_urls': [TARGET_BLOG_POST],
        'force_refresh': True,
        'crawl_depth': 1,
        'include_patterns': [
            '/blogs/desktop-and-application-streaming/*'
        ],
        'verbose_logging': True,  # Enhanced logging for diagnostics
        'verify_writes': True,    # Verify DynamoDB writes
        'metadata': {
            'trigger_reason': 'Missing blog post from March 2, 2026',
            'trigger_time': datetime.now().isoformat(),
            'diagnostic_mode': True
        }
    }
    
    try:
        req = urllib.request.Request(
            STAGING_API,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'AWS-Staging-Crawler-Trigger/1.0'
            },
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        print("✅ Crawler triggered successfully")
        print(f"\nRequest Payload:")
        print(json.dumps(payload, indent=2))
        print(f"\nResponse:")
        print(json.dumps(data, indent=2))
        
        # Extract job/crawl ID from response
        job_id = data.get('crawl_id') or data.get('job_id')
        
        # Check if the response indicates successful queuing
        if job_id:
            print(f"\n✓ Crawl job queued successfully")
            print(f"Job ID: {job_id}")
            print(f"Monitor at: staging.awseuccontent.com")
            
            # Step 5: Wait and verify DynamoDB writes
            print(f"\n" + "=" * 80)
            print("VERIFYING DYNAMODB WRITES")
            print("=" * 80)
            verify_dynamodb_writes(job_id)
            
            # Step 6: Fetch logs after crawl trigger
            print(f"\n" + "=" * 80)
            print("LOGS AFTER CRAWL TRIGGER")
            print("=" * 80)
            fetch_crawler_logs(job_id=job_id, limit=20)
            
            # Final diagnostic summary
            print(f"\n" + "=" * 80)
            print("DIAGNOSTIC SUMMARY")
            print("=" * 80)
            print(f"✓ Crawler triggered for: {TARGET_BLOG_POST}")
            print(f"✓ Job ID: {job_id}")
            print(f"✓ Check logs for filtering issues")
            print(f"✓ Verify DynamoDB table has new entries")
            print(f"✓ Review CloudWatch logs for detailed execution trace")
            print(f"\nNext steps:")
            print(f"  1. Check CloudWatch Logs for Lambda execution details")
            print(f"  2. Verify DynamoDB table for new/updated items")
            print(f"  3. Review S3 bucket for crawled content")
            print(f"  4. Check IAM permissions if writes are failing")
            print("=" * 80)
        else:
            print("\n⚠️  No job ID returned - check response for errors")
        
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP ERROR {e.code}: {e.reason}")
        try:
            error_body = e.read().decode('utf-8')
            print(f"Error details: {error_body}")
        except:
            pass
        sys.exit(1)
        
    except urllib.error.URLError as e:
        print(f"❌ URL ERROR: {e.reason}")
        print("Check network connectivity and API endpoint availability")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    trigger_crawler()
```