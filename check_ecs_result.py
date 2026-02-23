import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

test_post_id = 'builder-building-a-simple-content-summarizer-with-amazon-bedrock'

print(f"Checking post: {test_post_id}")
print("=" * 80)

response = table.get_item(Key={'post_id': test_post_id})

if 'Item' in response:
    post = response['Item']
    print(f"Title: {post.get('title')}")
    print(f"Author: {post.get('authors')}")
    print(f"URL: {post.get('url')}")
    print(f"Last crawled: {post.get('last_crawled', 'Never')}")
    print(f"Has content: {'Yes' if post.get('content') else 'No'}")
    print(f"Content length: {len(post.get('content', ''))} chars")
    print(f"Has summary: {'Yes' if post.get('summary') else 'No'}")
    
    print("\n" + "=" * 80)
    if post.get('authors') != 'AWS Builder Community':
        print("✅ SUCCESS! Real author extracted!")
        print(f"   Author: {post.get('authors')}")
    else:
        print("❌ FAILED: Still showing generic author")
        print("   Check CloudWatch logs for errors")
else:
    print("❌ Post not found in table")
