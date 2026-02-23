#!/usr/bin/env python3
"""Deploy test auth token page to staging"""

import boto3

s3 = boto3.client('s3', region_name='us-east-1')

print("Uploading test-auth-token.html to staging...")
s3.upload_file(
    'frontend/test-auth-token.html',
    'aws-blog-viewer-staging-031421429609',
    'test-auth-token.html',
    ExtraArgs={'ContentType': 'text/html'}
)
print("✅ Uploaded!")
print("\n🔗 Visit: https://staging.awseuccontent.com/test-auth-token.html")
