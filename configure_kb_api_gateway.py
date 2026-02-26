#!/usr/bin/env python3
"""
Configure API Gateway resources for KB Editor endpoints
Creates resources, methods, and integrations for KB editor API
"""

import boto3
import json
import time

# Configuration
API_ID = 'xox05733ce'
REGION = 'us-east-1'
LAMBDA_ARN = 'arn:aws:lambda:us-east-1:031421429609:function:aws-blog-api'
ACCOUNT_ID = '031421429609'

# Initialize clients
apigateway = boto3.client('apigateway', region_name=REGION)
lambda_client = boto3.client('lambda', region_name=REGION)

def get_root_resource_id():
    """Get the root resource ID"""
    response = apigateway.get_resources(restApiId=API_ID)
    for item in response['items']:
        if item['path'] == '/':
            return item['id']
    raise Exception("Root resource not found")

def create_resource_if_not_exists(parent_id, path_part):
    """Create a resource if it doesn't exist"""
    # Check if resource already exists
    response = apigateway.get_resources(restApiId=API_ID)
    for item in response['items']:
        if item.get('pathPart') == path_part and item.get('parentId') == parent_id:
            print(f"  ℹ️  Resource /{path_part} already exists (ID: {item['id']})")
            return item['id']
    
    # Create new resource
    response = apigateway.create_resource(
        restApiId=API_ID,
        parentId=parent_id,
        pathPart=path_part
    )
    print(f"  ✅ Created resource /{path_part} (ID: {response['id']})")
    return response['id']

def create_method_if_not_exists(resource_id, http_method, authorization_type='NONE'):
    """Create a method if it doesn't exist"""
    try:
        apigateway.get_method(
            restApiId=API_ID,
            resourceId=resource_id,
            httpMethod=http_method
        )
        print(f"    ℹ️  Method {http_method} already exists")
        return False
    except apigateway.exceptions.NotFoundException:
        # Method doesn't exist, create it
        apigateway.put_method(
            restApiId=API_ID,
            resourceId=resource_id,
            httpMethod=http_method,
            authorizationType=authorization_type,
            apiKeyRequired=False
        )
        print(f"    ✅ Created method {http_method}")
        return True

def create_lambda_integration(resource_id, http_method, stage='staging'):
    """Create Lambda integration for a method"""
    lambda_uri = f'arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{LAMBDA_ARN}:${{stageVariables.lambdaAlias}}/invocations'
    
    try:
        apigateway.put_integration(
            restApiId=API_ID,
            resourceId=resource_id,
            httpMethod=http_method,
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=lambda_uri
        )
        print(f"    ✅ Created Lambda integration for {http_method}")
    except Exception as e:
        print(f"    ⚠️  Integration may already exist: {str(e)}")

def create_options_method(resource_id):
    """Create OPTIONS method for CORS"""
    try:
        # Create OPTIONS method
        apigateway.put_method(
            restApiId=API_ID,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            authorizationType='NONE',
            apiKeyRequired=False
        )
        
        # Create mock integration
        apigateway.put_integration(
            restApiId=API_ID,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            type='MOCK',
            requestTemplates={
                'application/json': '{"statusCode": 200}'
            }
        )
        
        # Create method response
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
        
        # Create integration response
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
        
        print(f"    ✅ Created OPTIONS method with CORS")
    except Exception as e:
        print(f"    ⚠️  OPTIONS method may already exist: {str(e)}")

def add_lambda_permission(resource_path, http_method):
    """Add permission for API Gateway to invoke Lambda"""
    statement_id = f'apigateway-kb-{resource_path.replace("/", "-").replace("{", "").replace("}", "")}-{http_method}-staging'
    source_arn = f'arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{API_ID}/staging/{http_method}{resource_path}'
    
    try:
        lambda_client.add_permission(
            FunctionName='aws-blog-api',
            StatementId=statement_id,
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=source_arn
        )
        print(f"    ✅ Added Lambda permission for {http_method} {resource_path}")
    except lambda_client.exceptions.ResourceConflictException:
        print(f"    ℹ️  Lambda permission already exists")
    except Exception as e:
        print(f"    ⚠️  Error adding permission: {str(e)}")

def deploy_api(stage='staging'):
    """Deploy API to stage"""
    response = apigateway.create_deployment(
        restApiId=API_ID,
        stageName=stage,
        description=f'KB Editor API deployment - {time.strftime("%Y-%m-%d %H:%M:%S")}'
    )
    print(f"\n✅ Deployed API to {stage} stage (Deployment ID: {response['id']})")

def main():
    print("=" * 70)
    print("KB Editor API Gateway Configuration")
    print("=" * 70)
    print(f"API ID: {API_ID}")
    print(f"Region: {REGION}")
    print()
    
    try:
        # Get root resource
        root_id = get_root_resource_id()
        print(f"Root resource ID: {root_id}\n")
        
        # 1. Create /kb-document resource
        print("1. Creating /kb-document resource...")
        kb_document_id = create_resource_if_not_exists(root_id, 'kb-document')
        
        # 2. Create /kb-document/{id} resource
        print("\n2. Creating /kb-document/{id} resource...")
        kb_document_id_id = create_resource_if_not_exists(kb_document_id, '{id}')
        
        # 3. Add GET method to /kb-document/{id}
        print("\n3. Configuring GET /kb-document/{id}...")
        create_method_if_not_exists(kb_document_id_id, 'GET')
        create_lambda_integration(kb_document_id_id, 'GET')
        add_lambda_permission('/kb-document/{id}', 'GET')
        
        # 4. Add PUT method to /kb-document/{id}
        print("\n4. Configuring PUT /kb-document/{id}...")
        create_method_if_not_exists(kb_document_id_id, 'PUT')
        create_lambda_integration(kb_document_id_id, 'PUT')
        add_lambda_permission('/kb-document/{id}', 'PUT')
        
        # 5. Add OPTIONS method to /kb-document/{id}
        print("\n5. Configuring OPTIONS /kb-document/{id} (CORS)...")
        create_options_method(kb_document_id_id)
        
        # 6. Create /kb-ingestion-status resource
        print("\n6. Creating /kb-ingestion-status resource...")
        kb_ingestion_id = create_resource_if_not_exists(root_id, 'kb-ingestion-status')
        
        # 7. Create /kb-ingestion-status/{job_id} resource
        print("\n7. Creating /kb-ingestion-status/{job_id} resource...")
        kb_ingestion_job_id = create_resource_if_not_exists(kb_ingestion_id, '{job_id}')
        
        # 8. Add GET method to /kb-ingestion-status/{job_id}
        print("\n8. Configuring GET /kb-ingestion-status/{job_id}...")
        create_method_if_not_exists(kb_ingestion_job_id, 'GET')
        create_lambda_integration(kb_ingestion_job_id, 'GET')
        add_lambda_permission('/kb-ingestion-status/{job_id}', 'GET')
        
        # 9. Add OPTIONS method to /kb-ingestion-status/{job_id}
        print("\n9. Configuring OPTIONS /kb-ingestion-status/{job_id} (CORS)...")
        create_options_method(kb_ingestion_job_id)
        
        # 10. Deploy API
        print("\n10. Deploying API to staging...")
        deploy_api('staging')
        
        print("\n" + "=" * 70)
        print("✅ API Gateway configuration complete!")
        print("=" * 70)
        print(f"🔗 Test endpoint: https://{API_ID}.execute-api.{REGION}.amazonaws.com/staging")
        print("\n💡 Next step: Fix S3 permissions for Lambda")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
