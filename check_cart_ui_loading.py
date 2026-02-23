import boto3

# Check if files are actually in S3
s3 = boto3.client('s3', region_name='us-east-1')
bucket = 'aws-blog-viewer-staging-031421429609'

files_to_check = ['cart-ui.js', 'cart.css', 'app-staging.js', 'index-staging.html']

print("Checking S3 bucket for cart UI files...")
print("=" * 60)

for filename in files_to_check:
    try:
        response = s3.head_object(Bucket=bucket, Key=filename)
        size = response['ContentLength']
        last_modified = response['LastModified']
        content_type = response.get('ContentType', 'unknown')
        
        print(f"✅ {filename}")
        print(f"   Size: {size} bytes")
        print(f"   Last Modified: {last_modified}")
        print(f"   Content-Type: {content_type}")
        print()
    except Exception as e:
        print(f"❌ {filename} - NOT FOUND")
        print(f"   Error: {e}")
        print()

print("=" * 60)
print("\nChecking CloudFront invalidations...")

cloudfront = boto3.client('cloudfront', region_name='us-east-1')
distribution_id = 'E1IB9VDMV64CQA'

try:
    response = cloudfront.list_invalidations(DistributionId=distribution_id, MaxItems='5')
    invalidations = response.get('InvalidationList', {}).get('Items', [])
    
    if invalidations:
        print(f"\nRecent invalidations for {distribution_id}:")
        for inv in invalidations[:3]:
            print(f"  - ID: {inv['Id']}")
            print(f"    Status: {inv['Status']}")
            print(f"    Created: {inv['CreateTime']}")
            print()
    else:
        print("No recent invalidations found")
except Exception as e:
    print(f"Error checking invalidations: {e}")
