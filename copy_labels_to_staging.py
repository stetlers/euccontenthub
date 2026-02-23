#!/usr/bin/env python3
"""
Copy labels from production to staging for posts that exist in both tables.
This is a temporary fix while we debug the classifier Lambda.
"""
import boto3
from decimal import Decimal

def copy_labels():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    prod_table = dynamodb.Table('aws-blog-posts')
    staging_table = dynamodb.Table('aws-blog-posts-staging')
    
    print("Scanning production table for posts with labels...")
    
    # Get all posts from production that have labels
    response = prod_table.scan(
        FilterExpression='attribute_exists(label) AND label <> :empty',
        ExpressionAttributeValues={':empty': ''}
    )
    
    prod_posts = response.get('Items', [])
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = prod_table.scan(
            ExclusiveStartKey=response['LastEvaluatedKey'],
            FilterExpression='attribute_exists(label) AND label <> :empty',
            ExpressionAttributeValues={':empty': ''}
        )
        prod_posts.extend(response.get('Items', []))
    
    print(f"Found {len(prod_posts)} posts with labels in production")
    
    # Copy labels to staging
    copied = 0
    skipped = 0
    errors = 0
    
    for post in prod_posts:
        post_id = post['post_id']
        label = post.get('label', '')
        label_confidence = post.get('label_confidence', 0)
        label_generated = post.get('label_generated', '')
        
        if not label:
            continue
        
        try:
            # Check if post exists in staging
            staging_response = staging_table.get_item(Key={'post_id': post_id})
            
            if 'Item' not in staging_response:
                skipped += 1
                continue
            
            staging_post = staging_response['Item']
            
            # Only copy if staging post doesn't have a label
            if staging_post.get('label') and staging_post.get('label') != '':
                skipped += 1
                continue
            
            # Copy label to staging
            staging_table.update_item(
                Key={'post_id': post_id},
                UpdateExpression='SET label = :label, label_confidence = :confidence, label_generated = :generated',
                ExpressionAttributeValues={
                    ':label': label,
                    ':confidence': Decimal(str(label_confidence)) if isinstance(label_confidence, (int, float)) else label_confidence,
                    ':generated': label_generated
                }
            )
            
            copied += 1
            if copied % 10 == 0:
                print(f"  Copied {copied} labels...")
            
        except Exception as e:
            print(f"  Error copying label for {post_id}: {e}")
            errors += 1
    
    print(f"\n{'='*60}")
    print(f"Label Copy Complete")
    print(f"{'='*60}")
    print(f"Copied: {copied}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")

if __name__ == '__main__':
    copy_labels()
