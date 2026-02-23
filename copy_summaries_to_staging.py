"""
Copy summaries and labels from production to staging
Only updates posts that exist in both tables
"""

import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

prod_table = dynamodb.Table('aws-blog-posts')
staging_table = dynamodb.Table('aws-blog-posts-staging')

def copy_summaries():
    """Copy summaries and labels from production to staging"""
    
    print("Scanning production table for posts with summaries...")
    
    # Scan production table
    response = prod_table.scan()
    prod_posts = response.get('Items', [])
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = prod_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        prod_posts.extend(response.get('Items', []))
    
    print(f"Found {len(prod_posts)} posts in production")
    
    posts_updated = 0
    posts_skipped = 0
    posts_not_in_staging = 0
    
    for prod_post in prod_posts:
        post_id = prod_post['post_id']
        
        # Check if post exists in staging
        try:
            staging_response = staging_table.get_item(Key={'post_id': post_id})
            if 'Item' not in staging_response:
                posts_not_in_staging += 1
                continue
        except Exception as e:
            print(f"Error checking staging for {post_id}: {e}")
            posts_skipped += 1
            continue
        
        # Get summary and label from production
        summary = prod_post.get('summary', '')
        label = prod_post.get('label', '')
        label_confidence = prod_post.get('label_confidence', 0)
        label_generated = prod_post.get('label_generated', '')
        
        # Skip if no summary in production
        if not summary or summary == '':
            posts_skipped += 1
            continue
        
        # Update staging with summary and label
        try:
            update_expression = 'SET summary = :summary, label = :label, label_confidence = :conf, label_generated = :gen'
            expression_values = {
                ':summary': summary,
                ':label': label,
                ':conf': label_confidence,
                ':gen': label_generated
            }
            
            staging_table.update_item(
                Key={'post_id': post_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            posts_updated += 1
            if posts_updated % 50 == 0:
                print(f"  Updated {posts_updated} posts...")
                
        except Exception as e:
            print(f"Error updating {post_id}: {e}")
            posts_skipped += 1
    
    print(f"\n{'='*60}")
    print(f"Summary Copy Complete:")
    print(f"  Posts updated: {posts_updated}")
    print(f"  Posts skipped (no summary): {posts_skipped}")
    print(f"  Posts not in staging: {posts_not_in_staging}")
    print(f"{'='*60}")
    
    return {
        'posts_updated': posts_updated,
        'posts_skipped': posts_skipped,
        'posts_not_in_staging': posts_not_in_staging
    }

if __name__ == '__main__':
    copy_summaries()
