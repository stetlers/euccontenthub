#!/usr/bin/env python3
"""
Check which crawler Lambda functions exist and their aliases
"""
import boto3

lambda_client = boto3.client('lambda', region_name='us-east-1')

print("="*80)
print("CHECKING CRAWLER LAMBDA FUNCTIONS")
print("="*80)

# Check both possible function names
function_names = ['aws-blog-crawler', 'enhanced-crawler']

for func_name in function_names:
    print(f"\n{func_name}:")
    print("-" * 80)
    
    # Check if function exists
    try:
        response = lambda_client.get_function(FunctionName=func_name)
        print(f"✓ Function exists")
        print(f"  Runtime: {response['Configuration']['Runtime']}")
        print(f"  Handler: {response['Configuration']['Handler']}")
        print(f"  Last Modified: {response['Configuration']['LastModified']}")
        
        # Check for aliases
        try:
            aliases_response = lambda_client.list_aliases(FunctionName=func_name)
            aliases = aliases_response['Aliases']
            
            if aliases:
                print(f"  Aliases:")
                for alias in aliases:
                    print(f"    - {alias['Name']} → v{alias['FunctionVersion']}")
            else:
                print(f"  ✗ No aliases configured")
                
        except Exception as e:
            print(f"  ERROR checking aliases: {e}")
            
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"✗ Function does NOT exist")
    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "="*80)
print("DIAGNOSIS")
print("="*80)
print("\nThe API Lambda invokes: aws-blog-crawler")
print("Check if this function:")
print("1. Exists")
print("2. Has a production alias")
print("3. Points to the correct code version")
