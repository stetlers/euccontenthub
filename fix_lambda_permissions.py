"""
Fix Lambda permissions for KB editor endpoints with alias support
"""
import boto3

lambda_client = boto3.client('lambda', region_name='us-east-1')

# KB editor endpoints that need permissions
endpoints = [
    {
        'path': '/kb-document/{id}',
        'methods': ['GET', 'PUT']
    },
    {
        'path': '/kb-ingestion-status/{job_id}',
        'methods': ['GET']
    }
]

print("\n🔧 Fixing Lambda permissions for KB editor endpoints...")
print("=" * 60)

for endpoint in endpoints:
    path = endpoint['path']
    for method in endpoint['methods']:
        # Create permission for the qualified ARN (with alias)
        statement_id = f'apigateway-kb-{path.replace("/", "-").replace("{", "").replace("}", "")}-{method}-staging-qualified'
        source_arn = f'arn:aws:execute-api:us-east-1:031421429609:xox05733ce/staging/{method}{path}'
        
        print(f"\n{method} {path}")
        print(f"  Statement ID: {statement_id}")
        print(f"  Source ARN: {source_arn}")
        
        try:
            # Remove old permission if it exists
            try:
                lambda_client.remove_permission(
                    FunctionName='aws-blog-api:staging',
                    StatementId=statement_id
                )
                print(f"  ℹ️  Removed old permission")
            except:
                pass
            
            # Add permission for qualified ARN (with alias)
            lambda_client.add_permission(
                FunctionName='aws-blog-api:staging',  # Use qualified ARN with alias
                StatementId=statement_id,
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=source_arn
            )
            print(f"  ✅ Added permission for qualified ARN")
            
        except lambda_client.exceptions.ResourceConflictException:
            print(f"  ℹ️  Permission already exists")
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")

print("\n" + "=" * 60)
print("✅ Lambda permissions updated!")
print("=" * 60)
print("\n💡 Test the endpoint:")
print("curl https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/kb-document/euc-qa-pairs")
