#!/usr/bin/env python3
"""
Check the specific posts that are missing summaries in the API
"""
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts')

# Posts missing summaries from API
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
print("CHECKING SPECIFIC POSTS IN DYNAMODB")
print("="*80)

for post_id in missing_posts:
    print(f"\n{post_id}:")
    
    try:
        response = table.get_item(Key={'post_id': post_id})
        
        if 'Item' in response:
            post = response['Item']
            summary = post.get('summary', '')
            label = post.get('label', '')
            
            print(f"  ✓ Found in DynamoDB")
            print(f"  Summary: {'YES' if summary.strip() else 'NO'} ({len(summary)} chars)")
            print(f"  Label: {'YES' if label.strip() else 'NO'} ('{label}')")
            
            if not summary.strip():
                print(f"  → Needs summary generation")
        else:
            print(f"  ✗ NOT FOUND in DynamoDB")
            
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n" + "="*80)
print("SOLUTION")
print("="*80)
print("\nThese posts exist but don't have summaries/labels.")
print("They need to be processed by the summary generator.")
print("\nRun: python generate_missing_summaries.py")
