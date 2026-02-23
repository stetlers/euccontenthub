"""
Check what data exists in staging DynamoDB tables
"""

import boto3
from decimal import Decimal

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# Staging tables
posts_table = dynamodb.Table('aws-blog-posts-staging')
profiles_table = dynamodb.Table('euc-user-profiles-staging')

print("=" * 80)
print("STAGING DATA CHECK")
print("=" * 80)

# Check posts table
print("\n📊 AWS Blog Posts (Staging)")
print("-" * 80)

try:
    response = posts_table.scan(
        Select='COUNT'
    )
    post_count = response['Count']
    print(f"Total posts: {post_count}")
    
    if post_count > 0:
        # Get a few sample posts
        response = posts_table.scan(Limit=5)
        posts = response.get('Items', [])
        
        print(f"\nSample posts:")
        for i, post in enumerate(posts, 1):
            print(f"\n{i}. {post.get('title', 'No title')}")
            print(f"   URL: {post.get('url', 'No URL')}")
            print(f"   Date: {post.get('date_published', 'No date')}")
            print(f"   Source: {post.get('source', 'No source')}")
            print(f"   Has summary: {'Yes' if post.get('summary') else 'No'}")
            print(f"   Has label: {'Yes' if post.get('label') else 'No'}")
    else:
        print("\n⚠️  No posts found in staging table!")
        print("   This is why the staging site appears empty.")
        
except Exception as e:
    print(f"❌ Error reading posts table: {e}")

# Check profiles table
print("\n\n👤 User Profiles (Staging)")
print("-" * 80)

try:
    response = profiles_table.scan(
        Select='COUNT'
    )
    profile_count = response['Count']
    print(f"Total profiles: {profile_count}")
    
    if profile_count > 0:
        # Get sample profiles
        response = profiles_table.scan(Limit=5)
        profiles = response.get('Items', [])
        
        print(f"\nSample profiles:")
        for i, profile in enumerate(profiles, 1):
            print(f"\n{i}. {profile.get('display_name', 'No name')}")
            print(f"   Email: {profile.get('email', 'No email')}")
            print(f"   Bookmarks: {len(profile.get('bookmarks', []))}")
            print(f"   Created: {profile.get('created_at', 'No date')}")
    else:
        print("\n⚠️  No profiles found in staging table!")
        
except Exception as e:
    print(f"❌ Error reading profiles table: {e}")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

if post_count == 0:
    print("\n⚠️  STAGING TABLES ARE EMPTY!")
    print("\nThis explains why the staging site shows no content.")
    print("\nTo fix this, you need to:")
    print("1. Copy data from production to staging:")
    print("   python copy_data_to_staging.py")
    print("\n2. Or run the crawler in staging to populate data:")
    print("   - Visit https://staging.awseuccontent.com")
    print("   - Click the 'Crawl for New Posts' button")
else:
    print(f"\n✅ Staging has {post_count} posts and {profile_count} profiles")
    print("   Data looks good!")

print("\n" + "=" * 80)
