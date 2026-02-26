#!/usr/bin/env python3
"""
Enable CORS for KB Editor endpoints on API Gateway staging stage
"""

import boto3
import json

# Configuration
API_ID = 'xox05733ce'
STAGE_NAME = 'staging'
REGION = 'us-east-1'

# Initialize API Gateway client
apigateway = boto3.client('apigateway', region_name=REGION)

def enable_cors_for_resource(resource_id, resource_path):
    """Enable CORS for a specific resource"""
    
    print(f"\n📍 Configuring CORS for: {resource_path}")
    
    try:
        # Check if OPTIONS method exists
        try:
            apigateway.get_method(
                restApiId=API_ID,
                resourceId=resource_id,
                httpMethod='OPTIONS'
            )
            print(f"  ℹ️  OPTIONS method already exists")
        except apigateway.exceptions.NotFoundException:
            # Create OPTIONS method
            print(f"  ➕ Creating OPTIONS method...")
            apigateway.put_method(
                restApiId=API_ID,
                resourceId=resource_id,
                httpMethod='OPTIONS',
                authorizationType='NONE'
            )
            print(f"  ✅ OPTIONS method created")
        
        # Set up mock integration for OPTIONS
        print(f"  🔧 Setting up mock integration...")
        apigateway.put_integration(
            restApiId=API_ID,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            type='MOCK',
            requestTemplates={
                'application/json': '{"statusCode": 200}'
            }
        )
        
        # Set up method response for OPTIONS
        print(f"  🔧 Setting up method response...")
        try:
            apigateway.put_method_response(
                restApiId=API_ID,
                resourceId=resource_id,
                httpMethod='OPTIONS',
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Headers': True,
                    'method.response.header.Access-Control-Allow-Methods': True,
                    'method.response.header.Access-Control-Allow-Origin': True
                }
            )
        except:
            pass  # May already exist
        
        # Set up integration response for OPTIONS
        print(f"  🔧 Setting up integration response...")
        try:
            apigateway.put_integration_response(
                restApiId=API_ID,
                resourceId=resource_id,
                httpMethod='OPTIONS',
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                    'method.response.header.Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'",
                    'method.response.header.Access-Control-Allow-Origin': "'*'"
                }
            )
        except:
            pass  # May already exist
        
        print(f"  ✅ CORS configured for {resource_path}")
        
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")

def main():
    print("=" * 70)
    print("Enable CORS for KB Editor Endpoints - API Gateway Staging")
    print("=" * 70)
    
    # Get all resources
    print("\n📋 Fetching API resources...")
    resources = apigateway.get_resources(restApiId=API_ID)
    
    # Find KB editor resources
    kb_resources = []
    for resource in resources['items']:
        path = resource.get('path', '')
        if '/kb-' in path or path == '/kb-documents':
            kb_resources.append(resource)
            print(f"  Found: {path} (ID: {resource['id']})")
    
    if not kb_resources:
        print("\n⚠️  No KB editor resources found!")
        print("   Creating resources...")
        
        # Get root resource
        root_resource = next(r for r in resources['items'] if r['path'] == '/')
        
        # Create /kb-documents resource
        print("\n  Creating /kb-documents...")
        kb_docs_resource = apigateway.create_resource(
            restApiId=API_ID,
            parentId=root_resource['id'],
            pathPart='kb-documents'
        )
        kb_resources.append(kb_docs_resource)
        print(f"  ✅ Created /kb-documents (ID: {kb_docs_resource['id']})")
    
    # Enable CORS for each resource
    print("\n🔧 Enabling CORS...")
    for resource in kb_resources:
        enable_cors_for_resource(resource['id'], resource['path'])
    
    # Deploy to staging
    print("\n🚀 Deploying changes to staging...")
    try:
        apigateway.create_deployment(
            restApiId=API_ID,
            stageName=STAGE_NAME,
            description='Enable CORS for KB editor endpoints'
        )
        print("  ✅ Deployment complete")
    except Exception as e:
        print(f"  ❌ Deployment error: {str(e)}")
    
    print("\n" + "=" * 70)
    print("✅ CORS Configuration Complete!")
    print("=" * 70)
    print("\n🔗 Test the endpoint:")
    print(f"   curl -X OPTIONS https://{API_ID}.execute-api.{REGION}.amazonaws.com/{STAGE_NAME}/kb-documents")
    print("\n💡 The KB editor should now work without CORS errors")

if __name__ == '__main__':
    main()
