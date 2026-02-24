#!/usr/bin/env python3
"""
Deploy Frontend with KB-Powered Chat to Staging

This script deploys the frontend with the new KB-powered chat widget to staging.
"""

import boto3
import os
import mimetypes
from datetime import datetime

# Configuration
REGION = 'us-east-1'
STAGING_BUCKET = 'aws-blog-viewer-staging-031421429609'
STAGING_DISTRIBUTION_ID = 'E1IB9VDMV64CQA'
STAGING_API_ENDPOINT = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'

# Initialize AWS clients
s3 = boto3.client('s3', region_name=REGION)
cloudfront = boto3.client('cloudfront', region_name=REGION)

def print_step(step_num, description):
    """Print formatted step header"""
    print(f"\n{'='*80}")
    print(f"STEP {step_num}: {description}")
    print(f"{'='*80}\n")

def get_content_type(filename):
    """Get content type for file"""
    content_type, _ = mimetypes.guess_type(filename)
    return content_type or 'application/octet-stream'

def upload_file(local_path, s3_key):
    """Upload a file to S3"""
    try:
        content_type = get_content_type(local_path)
        
        with open(local_path, 'rb') as f:
            s3.put_object(
                Bucket=STAGING_BUCKET,
                Key=s3_key,
                Body=f,
                ContentType=content_type,
                CacheControl='no-cache, no-store, must-revalidate'
            )
        
        print(f"✓ Uploaded: {s3_key}")
        return True
        
    except Exception as e:
        print(f"✗ Error uploading {s3_key}: {str(e)}")
        return False

def update_chat_endpoint_in_file(content, endpoint):
    """Update chat API endpoint in JavaScript file"""
    # Replace the endpoint
    updated = content.replace(
        "const CHAT_API_ENDPOINT = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging';",
        f"const CHAT_API_ENDPOINT = '{endpoint}';"
    )
    return updated

def deploy_frontend():
    """Deploy frontend files to S3"""
    print_step(1, "Deploying Frontend Files to Staging")
    
    frontend_dir = 'frontend'
    files_to_upload = [
        ('index.html', 'index.html'),
        ('app.js', 'app.js'),
        ('auth.js', 'auth.js'),
        ('profile.js', 'profile.js'),
        ('chat-widget-kb.js', 'chat-widget.js'),  # Deploy KB version as chat-widget.js
        ('chat-widget-kb-styles.css', 'chat-widget-kb-styles.css'),
        ('styles.css', 'styles.css'),
        ('styles-refined.css', 'styles-refined.css'),
        ('service-name-detector.js', 'service-name-detector.js'),
        ('euc-service-name-mapping.json', 'euc-service-name-mapping.json')
    ]
    
    success_count = 0
    
    for local_file, s3_key in files_to_upload:
        local_path = os.path.join(frontend_dir, local_file)
        
        if not os.path.exists(local_path):
            print(f"⚠️  File not found: {local_path}")
            continue
        
        # Read file content
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update endpoint if it's the chat widget
        if local_file == 'chat-widget-kb.js':
            content = update_chat_endpoint_in_file(content, STAGING_API_ENDPOINT)
        
        # Write to temp file
        temp_path = f'temp_{local_file}'
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Upload
        if upload_file(temp_path, s3_key):
            success_count += 1
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    print(f"\n✓ Uploaded {success_count}/{len(files_to_upload)} files")
    return success_count > 0

def update_index_html():
    """Update index.html to include KB styles"""
    print_step(2, "Updating index.html for KB Chat")
    
    try:
        # Read current index.html
        with open('frontend/index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if KB styles are already included
        if 'chat-widget-kb-styles.css' in content:
            print("✓ KB styles already included in index.html")
        else:
            # Add KB styles after main styles
            content = content.replace(
                '<link rel="stylesheet" href="styles-refined.css">',
                '<link rel="stylesheet" href="styles-refined.css">\n    <link rel="stylesheet" href="chat-widget-kb-styles.css">'
            )
            
            # Write back
            with open('frontend/index.html', 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✓ Added KB styles to index.html")
        
        # Upload updated index.html
        upload_file('frontend/index.html', 'index.html')
        
        return True
        
    except Exception as e:
        print(f"✗ Error updating index.html: {str(e)}")
        return False

def invalidate_cloudfront():
    """Invalidate CloudFront cache"""
    print_step(3, "Invalidating CloudFront Cache")
    
    try:
        response = cloudfront.create_invalidation(
            DistributionId=STAGING_DISTRIBUTION_ID,
            InvalidationBatch={
                'Paths': {
                    'Quantity': 1,
                    'Items': ['/*']
                },
                'CallerReference': f'deploy-kb-chat-{datetime.now().timestamp()}'
            }
        )
        
        invalidation_id = response['Invalidation']['Id']
        print(f"✓ Created invalidation: {invalidation_id}")
        print(f"  Status: {response['Invalidation']['Status']}")
        
        return invalidation_id
        
    except Exception as e:
        print(f"✗ Error creating invalidation: {str(e)}")
        return None

def main():
    """Main deployment function"""
    print(f"\n{'#'*80}")
    print(f"# Frontend Deployment with KB-Powered Chat - STAGING")
    print(f"# Bucket: {STAGING_BUCKET}")
    print(f"# Distribution: {STAGING_DISTRIBUTION_ID}")
    print(f"# API Endpoint: {STAGING_API_ENDPOINT}")
    print(f"# Timestamp: {datetime.now().isoformat()}")
    print(f"{'#'*80}\n")
    
    try:
        # Step 1: Deploy frontend files
        if not deploy_frontend():
            raise Exception("Failed to deploy frontend files")
        
        # Step 2: Update index.html
        if not update_index_html():
            raise Exception("Failed to update index.html")
        
        # Step 3: Invalidate CloudFront
        invalidation_id = invalidate_cloudfront()
        
        # Summary
        print(f"\n{'='*80}")
        print("DEPLOYMENT COMPLETE!")
        print(f"{'='*80}\n")
        
        print("Deployment Summary:")
        print(f"  Environment: Staging")
        print(f"  S3 Bucket: {STAGING_BUCKET}")
        print(f"  CloudFront: {STAGING_DISTRIBUTION_ID}")
        print(f"  Invalidation: {invalidation_id}")
        print(f"  Staging URL: https://staging.awseuccontent.com")
        
        print("\nChanges Deployed:")
        print("  ✓ KB-powered chat widget (chat-widget-kb.js)")
        print("  ✓ KB-specific styles (chat-widget-kb-styles.css)")
        print("  ✓ Updated API endpoint to staging")
        print("  ✓ Citations display support")
        print("  ✓ Character counter")
        
        print("\nNext Steps:")
        print("  1. Wait 2-3 minutes for CloudFront invalidation")
        print("  2. Visit https://staging.awseuccontent.com")
        print("  3. Test chat widget with KB-powered responses")
        print("  4. Verify citations are displayed")
        print("  5. Compare with production chat")
        
        print("\nTest Queries:")
        print("  • What is EUC?")
        print("  • What happened to WorkSpaces?")
        print("  • What is AppStream 2.0?")
        print("  • How can I provide remote access to my employees?")
        
    except Exception as e:
        print(f"\n{'='*80}")
        print("DEPLOYMENT FAILED!")
        print(f"{'='*80}\n")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
