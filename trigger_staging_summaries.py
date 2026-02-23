#!/usr/bin/env python3
"""
Trigger summary generation for staging posts without summaries.
"""
import boto3
import json

def trigger_summary_lambda():
    """Trigger the summary Lambda for staging environment."""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Invoke summary Lambda with staging table
    response = lambda_client.invoke(
        FunctionName='aws-blog-summary-generator',
        InvocationType='Event',  # Async
        Payload=json.dumps({
            'table_name': 'aws-blog-posts-staging',
            'environment': 'staging'
        })
    )
    
    print(f"Summary Lambda invoked for staging")
    print(f"Status Code: {response['StatusCode']}")
    print(f"Request ID: {response['ResponseMetadata']['RequestId']}")
    
    if response['StatusCode'] == 202:
        print("\n✅ Summary generation triggered successfully!")
        print("The Lambda will process 5 posts per batch.")
        print("Check CloudWatch logs: /aws/lambda/aws-blog-summary-generator")
    else:
        print(f"\n❌ Failed to trigger summary generation")

if __name__ == '__main__':
    trigger_summary_lambda()
