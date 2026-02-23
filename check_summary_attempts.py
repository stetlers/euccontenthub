import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts')

# Get one of the posts without summary to see all its fields
post_id = 'builder-building-multi-region-disaster-recovery-for-amazon-appstream2-0'

response = table.get_item(Key={'post_id': post_id})
post = response.get('Item', {})

print(f"Full post data for: {post.get('title', 'N/A')}\n")
print("=" * 80)

# Print all fields
for key in sorted(post.keys()):
    value = post[key]
    if isinstance(value, str) and len(value) > 100:
        print(f"{key}: {value[:100]}... ({len(value)} chars)")
    else:
        print(f"{key}: {value}")

print("\n" + "=" * 80)
print("\nKEY OBSERVATIONS:")
print("-" * 80)

if 'summary' not in post:
    print("❌ 'summary' field does NOT exist")
elif post.get('summary') == '':
    print("❌ 'summary' field exists but is EMPTY")

if 'summary_generated' in post:
    print(f"✓ 'summary_generated' field exists: {post['summary_generated']}")
else:
    print("❌ 'summary_generated' field does NOT exist")

if 'label' not in post:
    print("❌ 'label' field does NOT exist")
elif post.get('label') == '':
    print("❌ 'label' field exists but is EMPTY")

print(f"\nLast crawled: {post.get('last_crawled', 'Never')}")
print(f"Content length: {len(post.get('content', ''))} characters")
