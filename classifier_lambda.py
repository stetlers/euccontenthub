"""
AWS Blog Classifier Lambda Function
Uses AWS Bedrock to classify blog posts into 6 categories
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
MODEL_ID = 'anthropic.claude-3-haiku-20240307-v1:0'

# Classification categories
LABELS = [
    'Announcement',
    'Best Practices',
    'Curation',
    'Customer Story',
    'Technical How-To',
    'Thought Leadership'
]


class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert DynamoDB Decimal types to JSON"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def classify_post(title, summary, content):
    """
    Classify a blog post using AWS Bedrock
    
    Args:
        title: Post title
        summary: AI-generated summary
        content: First 2000 chars of content
    
    Returns:
        {
            'label': str,
            'confidence': float
        }
    """
    
    # Prepare classification prompt
    prompt = f"""You are an expert at classifying AWS blog posts into categories.

Analyze the following blog post and classify it into ONE of these 6 categories:

1. Announcement - Promotes releases, events, open-source code, or new tools. Usually short (≤600 words), foundational level. Keywords: "announcing", "available now", "released", "new feature", "launch"

2. Best Practices - Shows patterns, anti-patterns, how to build better applications. Medium-long (≤2400 words), intermediate to expert level. Keywords: "best practices", "patterns", "recommendations", "should", "avoid"

3. Curation - Helps discover other content and events. Medium length (≤1200 words), foundational level. Keywords: "guide to", "collection", "roundup", "at re:Invent", event names, multiple links

4. Customer Story - Highlights how a customer solved a technical challenge. Medium-long (≤2400 words), intermediate to expert level. Keywords: customer names, "customer", "case study", specific company names

5. Technical How-To - Provides how-to content with code examples. Medium-long (≤2400 words), intermediate to expert level. Keywords: "how to", "step-by-step", "tutorial", "walkthrough", code examples

6. Thought Leadership - Sets context on broader technical challenges. Medium length (≤1200 words), foundational level. Keywords: "future of", "trends", "evolution", "landscape", opinion

Blog Post:
Title: {title}
Summary: {summary}
Content Preview: {content[:2000]}

Respond in JSON format:
{{
    "label": "one of the 6 categories exactly as written above",
    "confidence": 0.0 to 1.0,
    "reasoning": "brief explanation of why this category fits"
}}"""

    try:
        # Call Bedrock API
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
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
        response_text = response_body['content'][0]['text'].strip()
        
        # Extract JSON from response (handle markdown code blocks)
        if '```json' in response_text:
            json_start = response_text.find('```json') + 7
            json_end = response_text.find('```', json_start)
            response_text = response_text[json_start:json_end].strip()
        elif '```' in response_text:
            json_start = response_text.find('```') + 3
            json_end = response_text.find('```', json_start)
            response_text = response_text[json_start:json_end].strip()
        
        # Parse JSON
        classification = json.loads(response_text)
        
        # Validate label
        label = classification.get('label', '')
        if label not in LABELS:
            # Try to find closest match
            label_lower = label.lower()
            for valid_label in LABELS:
                if valid_label.lower() in label_lower or label_lower in valid_label.lower():
                    label = valid_label
                    break
            else:
                # Default to Technical How-To if no match
                label = 'Technical How-To'
                print(f"Warning: Invalid label '{classification.get('label')}', defaulting to '{label}'")
        
        # Validate confidence
        confidence = float(classification.get('confidence', 0.5))
        confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
        
        reasoning = classification.get('reasoning', '')
        
        print(f"  Classification: {label} (confidence: {confidence:.2f})")
        print(f"  Reasoning: {reasoning}")
        
        return {
            'label': label,
            'confidence': confidence
        }
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Response text: {response_text}")
        return {
            'label': 'Technical How-To',
            'confidence': 0.5
        }
    except Exception as e:
        print(f"Error classifying post: {e}")
        return {
            'label': 'Technical How-To',
            'confidence': 0.5
        }


def lambda_handler(event, context):
    """
    Lambda handler - classifies posts without labels
    
    Event parameters:
    - post_id (optional): Classify specific post
    - batch_size (optional): Number of posts to process (default: 50)
    - force (optional): Reclassify all posts (default: False)
    """
    
    try:
        post_id = event.get('post_id') if event else None
        batch_size = event.get('batch_size', 50) if event else 50
        force = event.get('force', False) if event else False
        
        print(f"Starting classification")
        print(f"Batch size: {batch_size}")
        print(f"Force reclassify: {force}")
        
        posts_processed = 0
        posts_classified = 0
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
            # Scan for posts without labels
            print("Scanning for posts without labels...")
            
            if force:
                # Get all posts
                response = table.scan()
            else:
                # Get posts without label field or with empty label
                response = table.scan(
                    FilterExpression='attribute_not_exists(label) OR label = :empty',
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
                        FilterExpression='attribute_not_exists(label) OR label = :empty',
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
            summary = post.get('summary', '')
            content = post.get('content', '')
            
            print(f"Processing: {title[:50]}...")
            posts_processed += 1
            
            try:
                # Classify post
                classification = classify_post(title, summary, content)
                
                # Save to DynamoDB
                from datetime import datetime
                table.update_item(
                    Key={'post_id': post_id},
                    UpdateExpression='SET label = :label, label_confidence = :confidence, label_generated = :timestamp',
                    ExpressionAttributeValues={
                        ':label': classification['label'],
                        ':confidence': Decimal(str(classification['confidence'])),
                        ':timestamp': datetime.utcnow().isoformat()
                    }
                )
                
                posts_classified += 1
                print(f"  ✓ Classified as: {classification['label']}")
                
            except Exception as e:
                print(f"  ✗ Error processing {post_id}: {e}")
                errors += 1
        
        # Prepare response
        result = {
            'posts_processed': posts_processed,
            'posts_classified': posts_classified,
            'errors': errors,
            'batch_size': batch_size
        }
        
        print(f"\nClassification Complete:")
        print(f"  Posts processed: {posts_processed}")
        print(f"  Posts classified: {posts_classified}")
        print(f"  Errors: {errors}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Classification completed',
                'results': result
            }, cls=DecimalEncoder)
        }
        
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Classification failed',
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
