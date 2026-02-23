#!/usr/bin/env python3
"""
Check if the test post got its summary
"""
import boto3
import time

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts')

post_id = 'builder-manage-your-entra-id-joined-amazon-workspaces-personal-settings'

print("="*80)
print("CHECKING TEST POST")
print("="*80)

print(f"\nPost ID: {post_id}")
print("\nWaiting 10 seconds for summary generation...")
time.sleep(10)

try:
    response = table.get_item(Key={'post_id': post_id})
    
    if 'Item' in response:
        post = response['Item']
        
        print(f"\nPost found!")
        print(f"  Title: {post.get('title', 'N/A')}")
        print(f"  Authors: {post.get('authors', 'N/A')}")
        print(f"  Summary: {post.get('summary', 'N/A')[:100]}...")
        print(f"  Label: {post.get('label', 'N/A')}")
        print(f"  Label Confidence: {post.get('label_confidence', 'N/A')}")
        
        if post.get('summary'):
            print(f"\n✓ Summary exists!")
        else:
            print(f"\n✗ No summary yet (may still be generating)")
        
        if post.get('label'):
            print(f"✓ Label exists!")
        else:
            print(f"✗ No label yet (may still be generating)")
    else:
        print(f"\nPost not found!")
        
except Exception as e:
    print(f"\nERROR: {e}")
