#!/usr/bin/env python3
"""
Fix the missing production alias for enhanced-crawler Lambda
"""
import boto3

lambda_client = boto3.client('lambda', region_name='us-east-1')

print("="*80)
print("FIXING ENHANCED CRAWLER PRODUCTION ALIAS")
print("="*80)

function_name = 'enhanced-crawler'

# 1. Get current function info
print(f"\n1. Checking {function_name}...")
try:
    response = lambda_client.get_function(FunctionName=function_name)
    latest_version = response['Configuration']['Version']
    print(f"   Latest version: {latest_version}")
except Exception as e:
    print(f"   ERROR: {e}")
    exit(1)

# 2. List all versions
print(f"\n2. Listing versions...")
try:
    response = lambda_client.list_versions_by_function(FunctionName=function_name)
    versions = [v for v in response['Versions'] if v['Version'] != '$LATEST']
    print(f"   Found {len(versions)} published versions")
    
    # Show recent versions
    for v in versions[-5:]:
        print(f"   - Version {v['Version']}: {v.get('Description', 'No description')}")
except Exception as e:
    print(f"   ERROR: {e}")
    exit(1)

# 3. Check if production alias exists
print(f"\n3. Checking for production alias...")
try:
    response = lambda_client.get_alias(
        FunctionName=function_name,
        Name='production'
    )
    print(f"   ✓ Production alias exists: points to version {response['FunctionVersion']}")
    current_version = response['FunctionVersion']
    alias_exists = True
except lambda_client.exceptions.ResourceNotFoundException:
    print(f"   ✗ Production alias does NOT exist")
    current_version = None
    alias_exists = False
except Exception as e:
    print(f"   ERROR: {e}")
    exit(1)

# 4. Determine which version to use
if versions:
    latest_published = versions[-1]['Version']
    print(f"\n4. Latest published version: {latest_published}")
else:
    print(f"\n4. ERROR: No published versions found!")
    print(f"   You need to publish a version first:")
    print(f"   aws lambda publish-version --function-name {function_name}")
    exit(1)

# 5. Create or update alias
print(f"\n5. Setting production alias to version {latest_published}...")
try:
    if alias_exists:
        response = lambda_client.update_alias(
            FunctionName=function_name,
            Name='production',
            FunctionVersion=latest_published
        )
        print(f"   ✓ Updated production alias: {current_version} → {latest_published}")
    else:
        response = lambda_client.create_alias(
            FunctionName=function_name,
            Name='production',
            FunctionVersion=latest_published,
            Description='Production alias for enhanced crawler'
        )
        print(f"   ✓ Created production alias → version {latest_published}")
except Exception as e:
    print(f"   ERROR: {e}")
    exit(1)

# 6. Verify
print(f"\n6. Verifying...")
try:
    response = lambda_client.get_alias(
        FunctionName=function_name,
        Name='production'
    )
    print(f"   ✓ Production alias verified: {function_name}:production → v{response['FunctionVersion']}")
except Exception as e:
    print(f"   ERROR: {e}")
    exit(1)

print("\n" + "="*80)
print("SUCCESS!")
print("="*80)
print(f"\nThe enhanced-crawler now has a production alias pointing to v{latest_published}")
print("\nNext steps:")
print("1. Test the crawler by clicking 'Start Crawl' on the website")
print("2. Monitor ECS tasks to ensure they start")
print("3. Check that summaries/labels are restored")
