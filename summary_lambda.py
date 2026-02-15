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


def generate_summary(title, content, max_retries=5):
    """
    Generate a 2-3 sentence summary using AWS Bedrock with exponential backoff
    
    Args:
        title: Blog post title
        content: Blog post content
        max_retries: Maximum number of retry attempts (default: 5)
    
    Returns:
        Summary string or None if all retries fail
    """
    import time
    
    if not content or len(content.strip()) < 50:
        return "Summary not available - insufficient content."
    
    # Prepare the prompt
    prompt = f"""You are a technical writer creating concise summaries of AWS blog posts.

Blog Title: {title}

Blog Content:
{content[:2000]}

Task: Write a 2-3 sentence summary that captures the main topic and key takeaways of this blog post. Focus on what the post teaches or demonstrates. Be concise and technical.

Summary:"""

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
    
    # Exponential backoff retry logic
    for attempt in range(max_retries):
        try:
            response = bedrock.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            summary = response_body['content'][0]['text'].strip()
            
            return summary
            
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a throttling error
            if 'ThrottlingException' in error_str or 'Too many requests' in error_str:
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s, 8s, 16s
                    wait_time = 2 ** attempt
                    print(f"  Throttled, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  Max retries reached after throttling")
                    return None  # Return None instead of error message
            else:
                # Non-throttling error, don't retry
                print(f"  Non-throttling error: {e}")
                return None
    
    # All retries exhausted
    print(f"  Failed to generate summary after {max_retries} attempts")
    return None


def lambda_handler(event, context):
    """
    Lambda handler - generates summaries for posts without them
    
    Event parameters:
    - post_id (optional): Generate summary for specific post
    - batch_size (optional): Number of posts to process (default: 10)
    - force (optional): Regenerate summaries even if they exist
    """
    
    try:
        print(f"DEBUG: Raw event: {json.dumps(event) if event else 'None'}")
        post_id = event.get('post_id') if event else None
        batch_size = event.get('batch_size', 10) if event else 10
        force = event.get('force', False) if event else False
        
        print(f"Starting summary generation")
        print(f"DEBUG: Extracted post_id={post_id}, batch_size={batch_size}, force={force}")
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
        
        # Track post IDs that get summaries for classifier
        summarized_post_ids = []
        
        # Process each post
        for post in posts_to_process:
            current_post_id = post['post_id']
            title = post.get('title', 'Untitled')
            content = post.get('content', '')
            
            print(f"Processing: {title[:50]}...")
            posts_processed += 1
            
            try:
                # Generate summary with exponential backoff
                summary = generate_summary(title, content)
                
                # If summary generation failed (returned None), skip this post
                if summary is None:
                    print(f"  ⚠️  Skipped - failed to generate summary after retries")
                    errors += 1
                    continue
                
                # Save to DynamoDB
                table.update_item(
                    Key={'post_id': current_post_id},
                    UpdateExpression='SET summary = :summary, summary_generated = :timestamp',
                    ExpressionAttributeValues={
                        ':summary': summary,
                        ':timestamp': getattr(context, 'aws_request_id', 'local-test') if context else 'local-test'
                    }
                )
                
                summaries_generated += 1
                summarized_post_ids.append(current_post_id)
                print(f"  ✓ Summary generated: {summary[:80]}...")
                
            except Exception as e:
                print(f"  ✗ Error processing {current_post_id}: {e}")
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
        print(f"  [AUTOCHAIN-V2-DEPLOYED]")  # Marker to verify deployment
        
        # Automatically invoke classifier Lambda for posts that got summaries
        if summaries_generated > 0 and summarized_post_ids:
            print(f"\n{summaries_generated} posts got new summaries")
            print("Invoking classifier Lambda for specific posts...")
            
            try:
                lambda_client = boto3.client('lambda')
                
                # Determine which alias to use based on environment
                environment = os.environ.get('ENVIRONMENT', 'production')
                function_name = f"aws-blog-classifier:{environment}"
                
                # Invoke classifier once for each post that got a summary
                # This ensures the classifier processes these specific posts
                for summarized_post_id in summarized_post_ids:
                    lambda_client.invoke(
                        FunctionName=function_name,
                        InvocationType='Event',  # Async invocation
                        Payload=json.dumps({
                            'post_id': summarized_post_id
                        })
                    )
                
                print(f"  Invoked classifier for {len(summarized_post_ids)} posts ({function_name})")
                result['classifier_invocations'] = len(summarized_post_ids)
            except Exception as e:
                print(f"  Warning: Could not invoke classifier Lambda: {e}")
                result['classifier_error'] = str(e)
        
        # AUTO-CHAINING: Check if there are more posts to process
        # Only auto-chain if we processed a full batch (indicates more work to do)
        print(f"\nAuto-chain check: post_id={post_id}, posts_processed={posts_processed}, batch_size={batch_size}, force={force}")
        if not post_id and posts_processed >= batch_size and not force:
            print("\nChecking for more posts to process...")
            
            try:
                # Quick count of remaining posts without summaries
                response = table.scan(
                    FilterExpression='attribute_not_exists(summary) OR summary = :empty',
                    ExpressionAttributeValues={':empty': ''},
                    Select='COUNT'
                )
                
                remaining_count = response['Count']
                
                # Handle pagination for count
                while 'LastEvaluatedKey' in response:
                    response = table.scan(
                        FilterExpression='attribute_not_exists(summary) OR summary = :empty',
                        ExpressionAttributeValues={':empty': ''},
                        Select='COUNT',
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
                    remaining_count += response['Count']
                
                if remaining_count > 0:
                    print(f"  Found {remaining_count} more posts without summaries")
                    print("  Auto-chaining: Invoking summary generator again...")
                    
                    lambda_client = boto3.client('lambda')
                    environment = os.environ.get('ENVIRONMENT', 'production')
                    summary_function = f"aws-blog-summary-generator:{environment}"
                    
                    # Invoke self with same parameters
                    lambda_client.invoke(
                        FunctionName=summary_function,
                        InvocationType='Event',  # Async
                        Payload=json.dumps({
                            'batch_size': batch_size,
                            'force': False,
                            'table_name': TABLE_NAME
                        })
                    )
                    
                    print(f"  ✓ Auto-chained to process next batch")
                    result['auto_chained'] = True
                    result['remaining_posts'] = remaining_count
                else:
                    print("  ✓ No more posts to process")
                    result['auto_chained'] = False
                    
            except Exception as e:
                print(f"  Warning: Could not check for remaining posts: {e}")
                result['auto_chain_error'] = str(e)
        
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
