"""
Check classifier Lambda aliases
"""
import boto3

lambda_client = boto3.client('lambda', region_name='us-east-1')

print("Checking classifier Lambda aliases...")
print("=" * 80)

try:
    response = lambda_client.list_aliases(FunctionName='aws-blog-classifier')
    aliases = response['Aliases']
    
    if aliases:
        print(f"\nFound {len(aliases)} aliases:")
        for alias in aliases:
            print(f"  • {alias['Name']}: version {alias['FunctionVersion']}")
    else:
        print("\nNo aliases found!")
        print("Need to create 'staging' alias")
except Exception as e:
    print(f"\nError: {e}")
