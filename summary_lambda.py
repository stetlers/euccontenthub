"""
AWS Blog Summary Generator Lambda Function
Uses AWS Bedrock to generate AI summaries for blog posts
"""

import json
import os
import boto3
from decimal import Decimal

# Initialize clients
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

# Environment detection for staging support
def get_table_suffix():
    """
    Determine table suffix based on environment.
    Returns '-staging' for staging environment, empty string for production.
    """
    environment = os.environ.get('ENVIRONMENT', 'production')
    return '-staging' if environment == 'staging' else ''

# Get table name with environment suffix
TABLE_SUFFIX = get_table_suffix()
TABLE_NAME = f"aws-blog-posts{TABLE_SUFFIX}"
table = dynamodb.Table(TABLE_NAME)

print(f"Environment: {os.environ.get('ENVIRONMENT', 'production')}")
print(f"Using table: {TABLE_NAME}")

# Bedrock model to use
MODEL_ID = 'anthropic.claude-3-haiku-20240307-v1:0'  # Fast and cheap


class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert DynamoDB Decimal types to JSON"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def generate_summary(title, content):
    """
    Generate a 2-3 sentence summary using AWS Bedrock
    """
    if not content or len(content.strip()) < 50:
        return "Summary not available - insufficient content."
    
    # Prepare the prompt
    prompt = f"""You are a technical writer creating concise summaries of AWS blog posts.

Blog Title: {title}

Blog Content:
{content[:2000]}

Task: Write a 2-3 sentence summary that captures the main topic and key takeaways of this blog post. Focus on what the post teaches or demonstrates. Be concise and technical.

Summary:"""

    try:
        # Call Bedrock API
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,
            "temperature": 0.3,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        summary = response_body['content'][0]['text'].strip()
        
        return summary
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        return f"Error generating summary: {str(e)}"


def lambda_handler(event, context):
    """
    Lambda handler - generates summaries for posts without them
    
    Event parameters:
    - post_id (optional): Generate summary for specific post
    - batch_size (optional): Number of posts to process (default: 10)
    - force (optional): Regenerate summaries even if they exist
    """
    
    try:
        post_id = event.get('post_id') if event else None
        batch_size = event.get('batch_size', 5) if event else 5
        force = event.get('force', False) if event else False
        
        print(f"Starting summary generation")
        print(f"Batch size: {batch_size}")
        print(f"Force regenerate: {force}")
        
        posts_processed = 0
        summaries_generated = 0
        errors = 0
        
        if post_id:
            # Process single post - fetch full post data from DynamoDB
            print(f"Processing single post: {post_id}")
            try:
                response = table.get_item(Key={'post_id': post_id})
                if 'Item' in response:
                    posts_to_process = [response['Item']]
                else:
                    print(f"Post {post_id} not found in database")
                    posts_to_process = []
            except Exception as e:
                print(f"Error fetching post {post_id}: {e}")
                posts_to_process = []
        else:
            # Scan for posts without summaries
            print("Scanning for posts without summaries...")
            
            if force:
                # Get all posts
                response = table.scan()
            else:
                # Get posts without summary field or with empty summary
                response = table.scan(
                    FilterExpression='attribute_not_exists(summary) OR summary = :empty',
                    ExpressionAttributeValues={':empty': ''}
                )
            
            posts_to_process = response.get('Items', [])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response and len(posts_to_process) < batch_size:
                if force:
                    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                else:
                    response = table.scan(
                        ExclusiveStartKey=response['LastEvaluatedKey'],
                        FilterExpression='attribute_not_exists(summary) OR summary = :empty',
                        ExpressionAttributeValues={':empty': ''}
                    )
                posts_to_process.extend(response.get('Items', []))
            
            # Limit to batch size
            posts_to_process = posts_to_process[:batch_size]
        
        print(f"Found {len(posts_to_process)} posts to process")
        
        # Process each post
        for post in posts_to_process:
            post_id = post['post_id']
            title = post.get('title', 'Untitled')
            content = post.get('content', '')
            
            print(f"Processing: {title[:50]}...")
            posts_processed += 1
            
            try:
                # Generate summary
                summary = generate_summary(title, content)
                
                # Save to DynamoDB
                table.update_item(
                    Key={'post_id': post_id},
                    UpdateExpression='SET summary = :summary, summary_generated = :timestamp',
                    ExpressionAttributeValues={
                        ':summary': summary,
                        ':timestamp': getattr(context, 'aws_request_id', 'local-test') if context else 'local-test'
                    }
                )
                
                summaries_generated += 1
                print(f"  ✓ Summary generated: {summary[:80]}...")
                
            except Exception as e:
                print(f"  ✗ Error processing {post_id}: {e}")
                errors += 1
        
        # Prepare response
        result = {
            'posts_processed': posts_processed,
            'summaries_generated': summaries_generated,
            'errors': errors,
            'batch_size': batch_size
        }
        
        print(f"\nSummary Generation Complete:")
        print(f"  Posts processed: {posts_processed}")
        print(f"  Summaries generated: {summaries_generated}")
        print(f"  Errors: {errors}")
        
        # Automatically invoke classifier Lambda for posts that got summaries
        if summaries_generated > 0:
            print(f"\n{summaries_generated} posts got new summaries")
            print("Invoking classifier Lambda...")
            
            try:
                lambda_client = boto3.client('lambda')
                
                # Determine which alias to use based on environment
                environment = os.environ.get('ENVIRONMENT', 'production')
                function_name = f"aws-blog-classifier:{environment}"
                
                # Calculate number of batches needed (50 posts per batch)
                classifier_batch_size = 50
                num_batches = (summaries_generated + classifier_batch_size - 1) // classifier_batch_size
                
                for i in range(num_batches):
                    lambda_client.invoke(
                        FunctionName=function_name,
                        InvocationType='Event',  # Async invocation
                        Payload=json.dumps({
                            'batch_size': classifier_batch_size
                        })
                    )
                    print(f"  Invoked classifier batch {i+1}/{num_batches} ({function_name})")
                
                result['classifier_batches_invoked'] = num_batches
            except Exception as e:
                print(f"  Warning: Could not invoke classifier Lambda: {e}")
                result['classifier_error'] = str(e)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Summary generation completed',
                'results': result
            }, cls=DecimalEncoder)
        }
        
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Summary generation failed',
                'error': str(e)
            })
        }


# For local testing
if __name__ == '__main__':
    # Test with a small batch
    test_event = {
        'batch_size': 5,
        'force': False
    }
    
    class MockContext:
        request_id = 'test-request-123'
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
