import boto3
import json

lambda_client = boto3.client('lambda', region_name='us-east-1')

# Lambda functions that need staging configuration
LAMBDA_FUNCTIONS = [
    'aws-blog-api',
    'aws-blog-crawler',
    'aws-blog-builder-selenium-crawler',
    'aws-blog-summary-generator',
    'aws-blog-classifier',
    'aws-blog-chat-assistant'
]

def configure_lambda_for_staging(function_name):
    """Add environment variables to Lambda for staging table support"""
    
    print(f"\nConfiguring {function_name}...")
    
    try:
        # Get current configuration
        response = lambda_client.get_function_configuration(
            FunctionName=function_name
        )
        
        # Get existing environment variables
        current_env = response.get('Environment', {}).get('Variables', {})
        
        # Add staging table configuration
        # The Lambda code will need to check ENVIRONMENT and append suffix
        current_env['POSTS_TABLE'] = 'aws-blog-posts'
        current_env['PROFILES_TABLE'] = 'euc-user-profiles'
        current_env['TABLE_SUFFIX'] = ''  # Will be set to '-staging' for staging alias
        
        # Update Lambda configuration
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={'Variables': current_env}
        )
        
        print(f"  ✅ Updated {function_name} environment variables")
        
    except Exception as e:
        print(f"  ❌ Error configuring {function_name}: {str(e)}")

def set_staging_alias_env(function_name):
    """Configure the staging alias to use staging tables"""
    
    print(f"\nConfiguring staging alias for {function_name}...")
    
    try:
        # Update the staging alias environment to use staging tables
        # Note: Alias-specific environment variables require updating the function
        # and then the alias points to that version
        
        # For now, we'll document that staging alias uses $LATEST
        # and we need to update the Lambda code to check an ENVIRONMENT variable
        
        print(f"  ℹ️  Staging alias uses $LATEST - update code to check ENVIRONMENT variable")
        print(f"  ℹ️  Set ENVIRONMENT=staging in API Gateway stage variables")
        
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")

if __name__ == '__main__':
    print("=" * 70)
    print("Configuring Lambda Functions for Staging Support")
    print("=" * 70)
    
    for function in LAMBDA_FUNCTIONS:
        configure_lambda_for_staging(function)
    
    print("\n" + "=" * 70)
    print("Next Steps:")
    print("=" * 70)
    print("1. Update Lambda code to use environment variables for table names:")
    print("   TABLE_SUFFIX = os.environ.get('TABLE_SUFFIX', '')")
    print("   posts_table = dynamodb.Table(f'aws-blog-posts{TABLE_SUFFIX}')")
    print("")
    print("2. Set API Gateway stage variable for staging:")
    print("   ENVIRONMENT=staging")
    print("   TABLE_SUFFIX=-staging")
    print("")
    print("3. Lambda code should read stage variable from event context")
    print("=" * 70)
