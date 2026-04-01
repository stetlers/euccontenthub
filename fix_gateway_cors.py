"""
Fix CORS on API Gateway Gateway Responses.

When API Gateway itself returns an error (not the Lambda), the response
won't include CORS headers unless we configure Gateway Responses.
This causes browser CORS errors even when the Lambda code is correct.

This script adds Access-Control-Allow-Origin: * to all gateway error responses.
"""
import boto3

apigateway = boto3.client('apigateway', region_name='us-east-1')
API_ID = 'xox05733ce'

# Gateway response types that should include CORS headers
RESPONSE_TYPES = [
    'DEFAULT_4XX',
    'DEFAULT_5XX',
    'MISSING_AUTHENTICATION_TOKEN',
    'UNAUTHORIZED',
    'ACCESS_DENIED',
    'EXPIRED_TOKEN',
    'INTEGRATION_FAILURE',
    'INTEGRATION_TIMEOUT',
    'THROTTLED',
    'BAD_REQUEST_BODY',
    'BAD_REQUEST_PARAMETERS',
    'RESOURCE_NOT_FOUND',
    'REQUEST_TOO_LARGE',
    'WAF_FILTERED',
]

print("Adding CORS headers to API Gateway Gateway Responses...")
print("=" * 60)

for response_type in RESPONSE_TYPES:
    try:
        apigateway.put_gateway_response(
            restApiId=API_ID,
            responseType=response_type,
            responseParameters={
                'gatewayresponse.header.Access-Control-Allow-Origin': "'*'",
                'gatewayresponse.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                'gatewayresponse.header.Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'"
            }
        )
        print(f"  ✅ {response_type}")
    except Exception as e:
        print(f"  ⚠️ {response_type}: {str(e)[:80]}")

# Redeploy to both stages
print("\nDeploying to stages...")
for stage in ['staging', 'prod']:
    try:
        resp = apigateway.create_deployment(
            restApiId=API_ID,
            stageName=stage,
            description=f'Added CORS to gateway responses ({stage})'
        )
        print(f"  ✅ Deployed to {stage} (ID: {resp['id']})")
    except Exception as e:
        print(f"  ⚠️ Deploy to {stage}: {str(e)[:80]}")

print("\n" + "=" * 60)
print("✅ Gateway CORS fix complete!")
print("\nThis ensures CORS headers are present even when API Gateway")
print("returns errors before reaching the Lambda function.")
