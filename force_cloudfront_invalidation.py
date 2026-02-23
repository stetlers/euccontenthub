#!/usr/bin/env python3
"""Force CloudFront invalidation for staging"""

import boto3
import time

cloudfront = boto3.client('cloudfront', region_name='us-east-1')
distribution_id = 'E1IB9VDMV64CQA'  # Staging

print("Creating CloudFront invalidation for staging...")
print(f"Distribution: {distribution_id}")

try:
    response = cloudfront.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            'Paths': {
                'Quantity': 3,
                'Items': ['/*', '/app.js', '/index.html']
            },
            'CallerReference': f'force-invalidation-{time.time()}'
        }
    )
    
    invalidation_id = response['Invalidation']['Id']
    status = response['Invalidation']['Status']
    
    print(f"✅ Invalidation created: {invalidation_id}")
    print(f"   Status: {status}")
    print(f"\n⏳ This will take 5-15 minutes to fully propagate")
    print(f"\n💡 To check status:")
    print(f"   aws cloudfront get-invalidation --distribution-id {distribution_id} --id {invalidation_id}")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
