"""
Fix summary Lambda handler configuration
"""
import boto3

lambda_client = boto3.client('lambda', region_name='us-east-1')

print("Checking current handler configuration...")

response = lambda_client.get_function_configuration(
    FunctionName='aws-blog-summary-generator'
)

current_handler = response['Handler']
print(f"Current handler: {current_handler}")

if current_handler != 'lambda_function.lambda_handler':
    print(f"\nUpdating handler to: lambda_function.lambda_handler")
    
    lambda_client.update_function_configuration(
        FunctionName='aws-blog-summary-generator',
        Handler='lambda_function.lambda_handler'
    )
    
    print("✓ Handler updated!")
else:
    print("✓ Handler is already correct")
