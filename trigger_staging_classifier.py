#!/usr/bin/env python3
"""
Trigger classifier Lambda for staging posts that have summaries but no labels.
"""
import boto3
import json

def trigger_classifier_lambda():
    """Trigger the classifier Lambda for staging environment."""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Invoke classifier Lambda with staging table
    # It will scan for posts without labels and classify them
    response = lambda_client.invoke(
        FunctionName='aws-blog-classifier',
        InvocationType='Event',  # Async
        Payload=json.dumps({
            'table_name': 'aws-blog-posts-staging',
            'environment': 'staging',
            'batch_size': 50  # Process up to 50 posts
        })
    )
    
    print(f"Classifier Lambda invoked for staging")
    print(f"Status Code: {response['StatusCode']}")
    print(f"Request ID: {response['ResponseMetadata']['RequestId']}")
    
    if response['StatusCode'] == 202:
        print("\n✅ Classification triggered successfully!")
        print("The Lambda will process posts without labels.")
        print("Check CloudWatch logs: /aws/lambda/aws-blog-classifier")
    else:
        print(f"\n❌ Failed to trigger classification")

if __name__ == '__main__':
    trigger_classifier_lambda()
