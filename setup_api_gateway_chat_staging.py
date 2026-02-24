#!/usr/bin/env python3
"""
Setup API Gateway for Chat Lambda - Staging

This script creates an API Gateway endpoint for the chat Lambda function.
We'll integrate with the existing API Gateway (xox05733ce) used by the main API.
"""

import boto3
import json
import time
from datetime import datetime

# Load configuration
with open('kb-config-staging.json') as f:
    config = json.load(f)

REGION = config['region']
ACCOUNT_ID = config['account_id']
LAMBDA_NAME = config['chat_lambda_name']
LAMBDA_ARN = config['chat_lambda_arn']
ENVIRONMENT = 'staging'

# Existing API Gateway ID (from AGENTS.md)
API_GATEWAY_ID = 'xox05733ce'
STAGE_NAME = 'staging'

# Initialize AWS clients
apigateway = boto3.client('apigateway', region_name=REGION)
lambda_client = boto3.client('lambda', region_name=REGION)

def print_step(step_num, description):
    """Print formatted step header"""
    print(f"\n{'='*80}")
    print(f"STEP {step_num}: {description}")
    print(f"{'='*80}\n")

def get_root_resource_id():
    """Get the root resource ID of the API Gateway"""
    print_step(1, "Getting API Gateway Root Resource")
    
    try:
        response = apigateway.get_resources(
            restApiId=API_GATEWAY_ID,
            limit=500
        )
        
        for resource in response['items']:
            if resource['path'] == '/':
                root_id = resource['id']
                print(f"✓ Found root resource: {root_id}")
                return root_id
        
        raise Exception("Root resource not found")
        
    except Exception as e:
        print(f"✗ Error getting root resource: {str(e)}")
        raise

def create_chat_resource(parent_id):
    """Create /chat resource"""
    print_step(2, "Creating /chat Resource")
    
    try:
        # Check if /chat already exists
        response = apigateway.get_resources(
            restApiId=API_GATEWAY_ID,
            limit=500
        )
        
        for resource in response['items']:
            if resource['path'] == '/chat':
                print(f"✓ /chat resource already exists: {resource['id']}")
                return resource['id']
        
        # Create /chat resource
        response = apigateway.create_resource(
            restApiId=API_GATEWAY_ID,
            parentId=parent_id,
            pathPart='chat'
        )
        
        resource_id = response['id']
        print(f"✓ Created /chat resource: {resource_id}")
        return resource_id
        
    except Exception as e:
        print(f"✗ Error creating resource: {str(e)}")
        raise

def create_options_method(resource_id):
    """Create OPTIONS method for CORS preflight"""
    print_step(3, "Creating OPTIONS Method (CORS)")
    
    try:
        # Check if OPTIONS method exists
        try:
            apigateway.get_method(
                restApiId=API_GATEWAY_ID,
                resourceId=resource_id,
                httpMethod='OPTIONS'
            )
            print(f"✓ OPTIONS method already exists")
            return
        except apigateway.exceptions.NotFoundException:
            pass
        
        # Create OPTIONS method
        apigateway.put_method(
            restApiId=API_GATEWAY_ID,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            authorizationType='NONE'
        )
        print(f"✓ Created OPTIONS method")
        
        # Create mock integration
        apigateway.put_integration(
            restApiId=API_GATEWAY_ID,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            type='MOCK',
            requestTemplates={
                'application/json': '{"statusCode": 200}'
            }
        )
        print(f"✓ Created mock integration")
        
        # Create method response
        apigateway.put_method_response(
            restApiId=API_GATEWAY_ID,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': True,
                'method.response.header.Access-Control-Allow-Methods': True,
                'method.response.header.Access-Control-Allow-Origin': True
            }
        )
        print(f"✓ Created method response")
        
        # Create integration response
        apigateway.put_integration_response(
            restApiId=API_GATEWAY_ID,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': "'Content-Type,Authorization'",
                'method.response.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
                'method.response.header.Access-Control-Allow-Origin': "'*'"
            }
        )
        print(f"✓ Created integration response")
        
    except Exception as e:
        print(f"✗ Error creating OPTIONS method: {str(e)}")
        raise

def create_post_method(resource_id):
    """Create POST method for chat endpoint"""
    print_step(4, "Creating POST Method")
    
    try:
        # Check if POST method exists
        try:
            apigateway.get_method(
                restApiId=API_GATEWAY_ID,
                resourceId=resource_id,
                httpMethod='POST'
            )
            print(f"✓ POST method already exists")
            return
        except apigateway.exceptions.NotFoundException:
            pass
        
        # Create POST method
        apigateway.put_method(
            restApiId=API_GATEWAY_ID,
            resourceId=resource_id,
            httpMethod='POST',
            authorizationType='NONE'  # No auth for staging testing
        )
        print(f"✓ Created POST method")
        
        # Create Lambda integration
        lambda_uri = f"arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{LAMBDA_ARN}/invocations"
        
        apigateway.put_integration(
            restApiId=API_GATEWAY_ID,
            resourceId=resource_id,
            httpMethod='POST',
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=lambda_uri
        )
        print(f"✓ Created Lambda integration")
        
    except Exception as e:
        print(f"✗ Error creating POST method: {str(e)}")
        raise

def add_lambda_permission():
    """Add permission for API Gateway to invoke Lambda"""
    print_step(5, "Adding Lambda Permission")
    
    try:
        # Create statement ID
        statement_id = f'apigateway-{STAGE_NAME}-invoke'
        
        # Check if permission exists
        try:
            policy = lambda_client.get_policy(FunctionName=LAMBDA_NAME)
            policy_doc = json.loads(policy['Policy'])
            
            for statement in policy_doc['Statement']:
                if statement.get('Sid') == statement_id:
                    print(f"✓ Permission already exists: {statement_id}")
                    return
        except lambda_client.exceptions.ResourceNotFoundException:
            pass
        
        # Add permission
        source_arn = f"arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{API_GATEWAY_ID}/{STAGE_NAME}/POST/chat"
        
        lambda_client.add_permission(
            FunctionName=LAMBDA_NAME,
            StatementId=statement_id,
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=source_arn
        )
        print(f"✓ Added permission: {statement_id}")
        print(f"  Source ARN: {source_arn}")
        
    except lambda_client.exceptions.ResourceConflictException:
        print(f"✓ Permission already exists")
    except Exception as e:
        print(f"✗ Error adding permission: {str(e)}")
        raise

def deploy_api():
    """Deploy API to staging stage"""
    print_step(6, "Deploying API to Staging")
    
    try:
        response = apigateway.create_deployment(
            restApiId=API_GATEWAY_ID,
            stageName=STAGE_NAME,
            description=f'Deploy chat endpoint - {datetime.now().isoformat()}'
        )
        
        deployment_id = response['id']
        print(f"✓ Created deployment: {deployment_id}")
        
        # Get stage URL
        api_url = f"https://{API_GATEWAY_ID}.execute-api.{REGION}.amazonaws.com/{STAGE_NAME}/chat"
        print(f"✓ Chat endpoint: {api_url}")
        
        return api_url
        
    except Exception as e:
        print(f"✗ Error deploying API: {str(e)}")
        raise

def verify_stage_variables():
    """Verify staging stage has correct variables"""
    print_step(7, "Verifying Stage Variables")
    
    try:
        response = apigateway.get_stage(
            restApiId=API_GATEWAY_ID,
            stageName=STAGE_NAME
        )
        
        variables = response.get('variables', {})
        print(f"Current stage variables:")
        for key, value in variables.items():
            print(f"  {key}: {value}")
        
        # Check for TABLE_SUFFIX
        if 'TABLE_SUFFIX' in variables:
            print(f"✓ TABLE_SUFFIX is set: {variables['TABLE_SUFFIX']}")
        else:
            print(f"⚠️  TABLE_SUFFIX not set (may need to be added for main API)")
        
    except Exception as e:
        print(f"✗ Error verifying stage: {str(e)}")
        raise

def main():
    """Main setup function"""
    print(f"\n{'#'*80}")
    print(f"# API Gateway Chat Endpoint Setup - {ENVIRONMENT.upper()}")
    print(f"# Region: {REGION}")
    print(f"# API Gateway: {API_GATEWAY_ID}")
    print(f"# Stage: {STAGE_NAME}")
    print(f"# Lambda: {LAMBDA_NAME}")
    print(f"# Timestamp: {datetime.now().isoformat()}")
    print(f"{'#'*80}\n")
    
    try:
        # Step 1: Get root resource
        root_id = get_root_resource_id()
        
        # Step 2: Create /chat resource
        chat_resource_id = create_chat_resource(root_id)
        
        # Step 3: Create OPTIONS method (CORS)
        create_options_method(chat_resource_id)
        
        # Step 4: Create POST method
        create_post_method(chat_resource_id)
        
        # Step 5: Add Lambda permission
        add_lambda_permission()
        
        # Step 6: Deploy API
        api_url = deploy_api()
        
        # Step 7: Verify stage variables
        verify_stage_variables()
        
        # Summary
        print(f"\n{'='*80}")
        print("SETUP COMPLETE!")
        print(f"{'='*80}\n")
        
        print("API Gateway Configuration:")
        print(f"  API ID: {API_GATEWAY_ID}")
        print(f"  Stage: {STAGE_NAME}")
        print(f"  Chat Endpoint: {api_url}")
        
        print("\nNext Steps:")
        print("  1. Test endpoint: python test_api_gateway_chat.py")
        print("  2. Update frontend to use new endpoint")
        print("  3. Compare with old chat Lambda")
        
        # Update configuration
        config['api_gateway_id'] = API_GATEWAY_ID
        config['api_gateway_stage'] = STAGE_NAME
        config['chat_api_url'] = api_url
        config['chat_api_deployed_at'] = datetime.now().isoformat()
        
        with open('kb-config-staging.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n✓ Configuration updated: kb-config-staging.json")
        
    except Exception as e:
        print(f"\n{'='*80}")
        print("SETUP FAILED!")
        print(f"{'='*80}\n")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
