#!/usr/bin/env python3
"""Check what's actually deployed to S3"""

import boto3

s3 = boto3.client('s3', region_name='us-east-1')
bucket = 'aws-blog-viewer-staging-031421429609'
key = 'app.js'

# Get the file
response = s3.get_object(Bucket=bucket, Key=key)
content = response['Body'].read().decode('utf-8')

# Check if auth check is in the file
if 'Check authentication first' in content and 'window.authManager.isAuthenticated()' in content:
    print("✅ Auth check IS in the deployed file")
    
    # Find the handleCrawl function
    start = content.find('async function handleCrawl()')
    if start != -1:
        end = content.find('\n\nasync function', start + 1)
        if end == -1:
            end = start + 500
        snippet = content[start:end]
        print("\nhandleCrawl function snippet:")
        print(snippet[:400])
else:
    print("❌ Auth check NOT in the deployed file")
    print("\nSearching for handleCrawl...")
    start = content.find('function handleCrawl()')
    if start == -1:
        start = content.find('handleCrawl')
    if start != -1:
        snippet = content[start:start+300]
        print(snippet)
