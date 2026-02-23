#!/usr/bin/env python3
"""Force upload styles-refined.css with no-cache headers"""

import boto3

s3 = boto3.client('s3', region_name='us-east-1')
cloudfront = boto3.client('cloudfront', region_name='us-east-1')

bucket = 'aws-blog-viewer-staging-031421429609'
distribution_id = 'E1IB9VDMV64CQA'

print("Uploading styles-refined.css with no-cache headers...")
s3.upload_file(
    'frontend/styles-refined.css',
    bucket,
    'styles-refined.css',
    ExtraArgs={
        'ContentType': 'text/css',
        'CacheControl': 'no-cache, no-store, must-revalidate'
    }
)
print("✅ Uploaded")

print("\nCreating CloudFront invalidation...")
import time
response = cloudfront.create_invalidation(
    DistributionId=distribution_id,
    InvalidationBatch={
        'Paths': {
            'Quantity': 1,
            'Items': ['/styles-refined.css']
        },
        'CallerReference': str(time.time())
    }
)
print(f"✅ Invalidation created: {response['Invalidation']['Id']}")
print("\n💡 Wait 1-2 minutes, then hard refresh (Ctrl+Shift+R)")
