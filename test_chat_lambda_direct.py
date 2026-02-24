#!/usr/bin/env python3
"""
Test Chat Lambda directly via boto3 - Staging
"""

import boto3
import json

# Load configuration
with open('kb-config-staging.json') as f:
    config = json.load(f)

LAMBDA_NAME = 'euc-chat-kb-staging'
REGION = config['region']

lambda_client = boto3.client('lambda', region_name=REGION)

def test_query(message):
    """Test a single query via direct Lambda invocation"""
    print(f"\n{'='*80}")
    print(f"Query: {message}")
    print(f"{'='*80}\n")
    
    payload = {
        'body': json.dumps({
            'message': message
        })
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName=LAMBDA_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        # Read response
        response_payload = json.loads(response['Payload'].read())
        
        print(f"Status Code: {response_payload['statusCode']}")
        
        if response_payload['statusCode'] == 200:
            data = json.loads(response_payload['body'])
            
            print(f"\nResponse ({len(data['response'])} chars):")
            print(data['response'])
            
            print(f"\nRecommendations ({len(data['recommendations'])} posts):")
            for i, rec in enumerate(data['recommendations'], 1):
                print(f"  {i}. {rec['title']}")
                print(f"     Label: {rec['label']}")
            
            print(f"\nCitations ({len(data['citations'])} sources):")
            for i, citation in enumerate(data['citations'], 1):
                print(f"  {i}. Source: {citation['source']}")
                print(f"     Content: {citation['content'][:100]}...")
        else:
            print(f"\nError Response:")
            print(response_payload['body'])
            
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Run test queries"""
    print(f"\n{'#'*80}")
    print(f"# Testing Chat Lambda (Direct Invocation) - STAGING")
    print(f"# Lambda: {LAMBDA_NAME}")
    print(f"{'#'*80}\n")
    
    # Test 1: Basic EUC question
    test_query("What is EUC?")
    
    # Test 2: Service rename question
    test_query("What happened to WorkSpaces?")
    
    print(f"\n{'='*80}")
    print("TESTING COMPLETE!")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    main()
