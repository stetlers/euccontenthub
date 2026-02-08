import boto3
from decimal import Decimal
import json

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

def copy_posts_to_staging(limit=50):
    """Copy the most recent posts from production to staging"""
    prod_table = dynamodb.Table('aws-blog-posts')
    staging_table = dynamodb.Table('aws-blog-posts-staging')
    
    print(f"Copying up to {limit} posts from production to staging...")
    
    # Scan production table
    response = prod_table.scan(Limit=limit)
    items = response['Items']
    
    # Copy items to staging
    count = 0
    for item in items:
        staging_table.put_item(Item=item)
        count += 1
        if count % 10 == 0:
            print(f"  Copied {count} posts...")
    
    print(f"✅ Copied {count} posts to staging table")
    return count

def copy_profiles_to_staging(limit=10):
    """Copy sample user profiles from production to staging"""
    prod_table = dynamodb.Table('euc-user-profiles')
    staging_table = dynamodb.Table('euc-user-profiles-staging')
    
    print(f"Copying up to {limit} user profiles from production to staging...")
    
    # Scan production table
    response = prod_table.scan(Limit=limit)
    items = response['Items']
    
    # Copy items to staging
    count = 0
    for item in items:
        staging_table.put_item(Item=item)
        count += 1
    
    print(f"✅ Copied {count} user profiles to staging table")
    return count

if __name__ == '__main__':
    print("=" * 60)
    print("Copying Production Data to Staging Tables")
    print("=" * 60)
    
    posts_copied = copy_posts_to_staging(limit=50)
    profiles_copied = copy_profiles_to_staging(limit=10)
    
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Posts copied: {posts_copied}")
    print(f"  Profiles copied: {profiles_copied}")
    print("=" * 60)
