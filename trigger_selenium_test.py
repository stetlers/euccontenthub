#!/usr/bin/env python3
"""
Trigger Selenium Crawler Test

This script:
1. Finds a Builder.AWS post in staging
2. Updates its date_updated to trigger change detection
3. Runs the sitemap crawler
4. Monitors logs to see if Selenium crawler is invoked
"""

import boto3
import json
from datetime import datetime, timezone

# Initialize clients
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')

# Tables
STAGING_TABLE = 'aws-blog-posts-staging'

def find_builder_post():
    """Find a Builder.AWS post in staging"""
    table = dynamodb.Table(STAGING_TABLE)
    
    try:
        # Just scan and filter in Python
        response = table.scan()
        
        for item in response.get('Items', []):
            if item.get('source') == 'builder.aws.com':
                return item
        
        return None
    except Exception as e:
        print(f"Error finding post: {e}")
        return None

def update_post_date(post_id):
    """Update a post's date_updated to trigger change detection"""
    table = dynamodb.Table(STAGING_TABLE)
    
    # Use an OLD date (2020-01-01) so the sitemap's lastmod will be NEWER
    # This will make the crawler think the post was updated
    old_date = "2020-01-01T00:00:00.000Z"
    
    try:
        table.update_item(
            Key={'post_id': post_id},
            UpdateExpression='SET date_updated = :date',
            ExpressionAttributeValues={':date': old_date}
        )
        print(f"✓ Updated {post_id} with date_updated = {old_date}")
        print(f"  (Sitemap's lastmod will be newer, triggering change detection)")
        return True
    except Exception as e:
        print(f"Error updating post: {e}")
        return False

def invoke_crawler():
    """Invoke the sitemap crawler for Builder.AWS"""
    try:
        response = lambda_client.invoke(
            FunctionName='aws-blog-crawler',
            InvocationType='Event',
            Payload=json.dumps({
                'source': 'builder',
                'table_name': STAGING_TABLE
            })
        )
        print(f"✓ Crawler invoked (StatusCode: {response['StatusCode']})")
        return True
    except Exception as e:
        print(f"Error invoking crawler: {e}")
        return False

def main():
    print("="*60)
    print("Selenium Crawler Orchestration Test")
    print("="*60)
    
    # Step 1: Find a Builder.AWS post
    print("\n1. Finding a Builder.AWS post in staging...")
    post = find_builder_post()
    
    if not post:
        print("❌ No Builder.AWS posts found in staging")
        return
    
    post_id = post['post_id']
    post_title = post.get('title', 'Unknown')
    old_date = post.get('date_updated', 'Unknown')
    
    print(f"✓ Found post: {post_id}")
    print(f"  Title: {post_title}")
    print(f"  Current date_updated: {old_date}")
    
    # Step 2: Update the post's date
    print(f"\n2. Updating post date to trigger change detection...")
    if not update_post_date(post_id):
        print("❌ Failed to update post")
        return
    
    # Step 3: Invoke the crawler
    print(f"\n3. Invoking sitemap crawler...")
    if not invoke_crawler():
        print("❌ Failed to invoke crawler")
        return
    
    # Step 4: Instructions for monitoring
    print("\n" + "="*60)
    print("Test Triggered Successfully!")
    print("="*60)
    print("\nNext steps:")
    print("1. Wait 30-60 seconds for crawler to process")
    print("2. Check sitemap crawler logs:")
    print("   aws logs tail /aws/lambda/aws-blog-crawler --follow --region us-east-1")
    print("\n3. Look for these messages:")
    print("   - '1 Builder.AWS posts changed - invoking Selenium crawler'")
    print("   - 'Invoked Selenium crawler for 1 posts'")
    print("\n4. Check Selenium crawler logs:")
    print("   aws logs tail /aws/lambda/aws-blog-builder-selenium-crawler --follow --region us-east-1")
    print("\n5. Verify the post was updated with real author/content")
    print(f"   Post ID to check: {post_id}")

if __name__ == '__main__':
    main()
