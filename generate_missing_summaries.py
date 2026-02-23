#!/usr/bin/env python3
"""
Generate summaries for the 8 posts that are missing them
"""
import boto3
import json

lambda_client = boto3.client('lambda', region_name='us-east-1')

# Posts that need summaries
missing_posts = [
    'builder-automating-desktop-cleanup-with-a-powershell-script-built-faster-with-kiro',
    'builder-automating-desktop-organization-with-aws-kiro-a-lazy-developer-s-solution',
    'builder-i-hate-cleaning-my-desktop-so-i-built-this-automation-with-kiro',
    'builder-customizing-ublock-origin-lite-preferences-with-group-policy-on-domain-joined-windows-amazon-workspaces-and-appstream-2-0-instances',
    'builder-configuring-workspace-personal-and-workspaces-pools-saml-authentication-with-auth0',
    'builder-configuring-amazon-workspaces-pools-with-okta',
    'builder-getting-started-with-valkey-using-javascript',
    'builder-building-multi-region-disaster-recovery-for-amazon-appstream2-0'
]

print("="*80)
print("GENERATING SUMMARIES FOR 8 POSTS")
print("="*80)

print(f"\nInvoking summary generator for {len(missing_posts)} posts...")

for i, post_id in enumerate(missing_posts, 1):
    print(f"\n[{i}/{len(missing_posts)}] {post_id}")
    
    try:
        response = lambda_client.invoke(
            FunctionName='aws-blog-summary-generator:production',
            InvocationType='Event',  # Async
            Payload=json.dumps({
                'post_id': post_id,
                'table_name': 'aws-blog-posts',
                'environment': 'production'
            })
        )
        
        print(f"  ✓ Invoked summary generator")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")

print("\n" + "="*80)
print("SUMMARY GENERATION STARTED")
print("="*80)
print(f"\nInvoked summary generator for {len(missing_posts)} posts.")
print(f"Each invocation will:")
print(f"  1. Generate AI summary")
print(f"  2. Auto-invoke classifier for label")
print(f"\nWait 2-3 minutes, then check the website.")
print(f"\nTo monitor progress:")
print(f"  python check_api_response.py")
