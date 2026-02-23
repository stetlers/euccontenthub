"""
Check a specific post to see if it has a label
"""
import boto3
import json

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

post_id = 'builder-building-a-simple-content-summarizer-with-amazon-bedrock'

print(f"Checking post: {post_id}")
print("=" * 80)

response = table.get_item(Key={'post_id': post_id})

if 'Item' in response:
    post = response['Item']
    print(f"\nTitle: {post.get('title')}")
    print(f"Source: {post.get('source')}")
    print(f"Author: {post.get('authors')}")
    print(f"Has summary: {'Yes' if post.get('summary') else 'No'}")
    print(f"Has label: {'Yes' if post.get('label') else 'No'}")
    
    if post.get('label'):
        print(f"\nLabel: {post.get('label')}")
        print(f"Confidence: {post.get('label_confidence')}")
        print(f"Generated: {post.get('label_generated')}")
    
    if post.get('summary'):
        print(f"\nSummary: {post.get('summary')[:200]}...")
else:
    print("\nPost not found!")
