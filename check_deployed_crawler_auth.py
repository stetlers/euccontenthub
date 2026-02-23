#!/usr/bin/env python3
"""Check if Authorization header is in deployed app.js"""

import boto3

s3 = boto3.client('s3', region_name='us-east-1')
bucket = 'aws-blog-viewer-staging-031421429609'
key = 'app.js'

# Get the file
response = s3.get_object(Bucket=bucket, Key=key)
content = response['Body'].read().decode('utf-8')

# Check for Authorization header in handleCrawl
if "Authorization" in content and "Bearer" in content:
    print("✅ Authorization header IS in the deployed file")
    
    # Find the handleCrawl function
    start = content.find('async function handleCrawl()')
    if start != -1:
        # Find the fetch call
        fetch_start = content.find('fetch(`${API_ENDPOINT}/crawl`', start)
        if fetch_start != -1:
            snippet = content[fetch_start:fetch_start+300]
            print("\nFetch call snippet:")
            print(snippet)
else:
    print("❌ Authorization header NOT in the deployed file")
    print("\nSearching for handleCrawl...")
    start = content.find('function handleCrawl()')
    if start == -1:
        start = content.find('handleCrawl')
    if start != -1:
        snippet = content[start:start+500]
        print(snippet)
