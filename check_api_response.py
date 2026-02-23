#!/usr/bin/env python3
"""
Check what the API is actually returning
"""
import requests
import json

API_ENDPOINT = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod'

print("="*80)
print("CHECKING API RESPONSE")
print("="*80)

print(f"\nFetching posts from API: {API_ENDPOINT}/posts")

try:
    response = requests.get(f"{API_ENDPOINT}/posts")
    
    if response.status_code == 200:
        data = response.json()
        posts = data.get('posts', [])
        
        print(f"\n✓ API returned {len(posts)} posts")
        
        # Filter Builder posts
        builder_posts = [p for p in posts if p.get('post_id', '').startswith('builder-')]
        print(f"  Builder.AWS posts: {len(builder_posts)}")
        
        # Check for missing summaries/labels
        missing_summary = [p for p in builder_posts if not p.get('summary', '').strip()]
        missing_label = [p for p in builder_posts if not p.get('label', '').strip()]
        
        print(f"\n  Posts WITH summaries: {len(builder_posts) - len(missing_summary)}")
        print(f"  Posts WITHOUT summaries: {len(missing_summary)}")
        print(f"  Posts WITH labels: {len(builder_posts) - len(missing_label)}")
        print(f"  Posts WITHOUT labels: {len(missing_label)}")
        
        if missing_summary:
            print(f"\n" + "="*80)
            print(f"POSTS MISSING SUMMARIES (from API):")
            print("="*80)
            for post in missing_summary[:10]:
                print(f"\n  {post.get('title', 'N/A')[:70]}")
                print(f"    ID: {post.get('post_id', 'N/A')}")
                print(f"    Authors: {post.get('authors', 'N/A')}")
                print(f"    Summary: '{post.get('summary', '')}'")
        
        if missing_label:
            print(f"\n" + "="*80)
            print(f"POSTS MISSING LABELS (from API):")
            print("="*80)
            for post in missing_label[:10]:
                print(f"\n  {post.get('title', 'N/A')[:70]}")
                print(f"    ID: {post.get('post_id', 'N/A')}")
                print(f"    Label: '{post.get('label', '')}'")
        
        # Show a few sample posts
        print(f"\n" + "="*80)
        print("SAMPLE BUILDER POSTS (first 3):")
        print("="*80)
        for i, post in enumerate(builder_posts[:3], 1):
            print(f"\n{i}. {post.get('title', 'N/A')[:60]}")
            print(f"   ID: {post.get('post_id', 'N/A')}")
            print(f"   Authors: {post.get('authors', 'N/A')}")
            print(f"   Summary: {post.get('summary', 'N/A')[:80]}...")
            print(f"   Label: {post.get('label', 'N/A')}")
        
    else:
        print(f"\n✗ API returned status code: {response.status_code}")
        print(f"  Response: {response.text[:200]}")
        
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("DIAGNOSIS")
print("="*80)
print("\nIf API shows missing summaries but DynamoDB doesn't:")
print("  → API Lambda may be caching old data")
print("  → Try restarting the API Lambda")
print("\nIf both show complete data but website doesn't:")
print("  → CloudFront cache needs invalidation")
print("  → Browser cache needs clearing")
