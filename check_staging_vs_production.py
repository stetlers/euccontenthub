"""
Check staging vs production post counts and recent posts
"""

import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

def check_table(table_name):
    """Check table stats"""
    print(f"\n{'='*80}")
    print(f"Table: {table_name}")
    print(f"{'='*80}")
    
    table = dynamodb.Table(table_name)
    
    # Scan to get all posts
    response = table.scan()
    items = response.get('Items', [])
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))
    
    print(f"\nTotal posts: {len(items)}")
    
    # Count by source
    aws_blog_count = sum(1 for item in items if item.get('source') == 'aws.amazon.com')
    builder_count = sum(1 for item in items if item.get('source') == 'builder.aws.com')
    
    print(f"  AWS Blog: {aws_blog_count}")
    print(f"  Builder.AWS: {builder_count}")
    
    # Get most recent posts
    posts_with_dates = [(item, item.get('date_published', '')) for item in items if item.get('date_published')]
    posts_with_dates.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\nMost recent 5 posts:")
    for i, (post, date) in enumerate(posts_with_dates[:5], 1):
        title = post.get('title', 'No title')[:60]
        source = post.get('source', 'Unknown')
        print(f"  {i}. [{date}] {title}... ({source})")
    
    # Check posts with summaries
    posts_with_summaries = sum(1 for item in items if item.get('summary'))
    print(f"\nPosts with summaries: {posts_with_summaries} ({posts_with_summaries/len(items)*100:.1f}%)")
    
    # Check posts with labels
    posts_with_labels = sum(1 for item in items if item.get('label'))
    print(f"Posts with labels: {posts_with_labels} ({posts_with_labels/len(items)*100:.1f}%)")
    
    return len(items), aws_blog_count, builder_count


if __name__ == '__main__':
    print("\n" + "="*80)
    print("STAGING VS PRODUCTION COMPARISON")
    print("="*80)
    
    # Check production
    prod_total, prod_aws, prod_builder = check_table('aws-blog-posts')
    
    # Check staging
    staging_total, staging_aws, staging_builder = check_table('aws-blog-posts-staging')
    
    # Compare
    print(f"\n{'='*80}")
    print("COMPARISON")
    print(f"{'='*80}")
    print(f"\nTotal posts:")
    print(f"  Production: {prod_total}")
    print(f"  Staging: {staging_total}")
    print(f"  Difference: {prod_total - staging_total} posts")
    
    print(f"\nAWS Blog posts:")
    print(f"  Production: {prod_aws}")
    print(f"  Staging: {staging_aws}")
    print(f"  Difference: {prod_aws - staging_aws} posts")
    
    print(f"\nBuilder.AWS posts:")
    print(f"  Production: {prod_builder}")
    print(f"  Staging: {staging_builder}")
    print(f"  Difference: {prod_builder - staging_builder} posts")
    
    if prod_total > staging_total:
        print(f"\n⚠️  WARNING: Production has {prod_total - staging_total} more posts than staging")
        print(f"   This suggests the staging crawler may not be working correctly")
    elif staging_total > prod_total:
        print(f"\n⚠️  WARNING: Staging has {staging_total - prod_total} more posts than production")
        print(f"   This is unusual and should be investigated")
    else:
        print(f"\n✅ Production and staging have the same number of posts")
