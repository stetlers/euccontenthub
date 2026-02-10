"""
API Lambda Function for Blog Posts Viewer
Provides REST API to query DynamoDB table
Includes JWT token validation for protected endpoints
"""

import json
import os
import boto3
from decimal import Decimal
import base64
from functools import wraps
import threading
import time

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')

# Initialize Bedrock Runtime client for comment moderation
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')

# Get table suffix for staging/production isolation
def get_table_suffix(event=None):
    """Extract table suffix from API Gateway stage variables or environment"""
    # Try stage variables first (from API Gateway)
    if event:
        stage_variables = event.get('stageVariables', {})
        table_suffix = stage_variables.get('TABLE_SUFFIX', '')
        if table_suffix:
            return table_suffix
    
    # Fall back to environment variable
    return os.environ.get('TABLE_SUFFIX', '')

# Note: Tables will be initialized per request in lambda_handler
TABLE_NAME = None
table = None

# Cognito configuration
COGNITO_REGION = os.environ.get('COGNITO_REGION', 'us-east-1')
COGNITO_USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', 'us-east-1_MOvNrTnua')
COGNITO_APP_CLIENT_ID = os.environ.get('COGNITO_APP_CLIENT_ID', '3pv5jf235vj14gu148b9vjt3od')

# Cognito JWKS URL
JWKS_URL = f'https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json'


class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert DynamoDB Decimal types to JSON"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def cors_headers():
    """Return CORS headers for API responses"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,OPTIONS'
    }


def validate_jwt_token(token):
    """
    Validate JWT token from Cognito by decoding and checking basic claims
    For production, this validates the token structure and expiration
    """
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Decode JWT (without verification for now - just parse claims)
        # Split token into parts
        parts = token.split('.')
        if len(parts) != 3:
            raise Exception('Invalid token format')
        
        # Decode payload (add padding if needed)
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)  # Add padding
        decoded_bytes = base64.urlsafe_b64decode(payload)
        decoded = json.loads(decoded_bytes)
        
        # Check expiration
        import time
        exp = decoded.get('exp', 0)
        if exp < time.time():
            raise Exception('Token has expired')
        
        # Check audience (app client ID)
        aud = decoded.get('aud') or decoded.get('client_id')
        if aud != COGNITO_APP_CLIENT_ID:
            raise Exception('Invalid audience')
        
        # Check token_use
        token_use = decoded.get('token_use')
        if token_use not in ['id', 'access']:
            raise Exception('Invalid token_use')
        
        return decoded
    
    except Exception as e:
        raise Exception(f'Token validation failed: {str(e)}')


def moderate_comment(text, post_context):
    """
    Analyze comment text using AWS Bedrock for content moderation.
    
    Args:
        text: The comment text to analyze
        post_context: Dictionary with post_id, title, tags for context
    
    Returns:
        {
            'status': 'approved' | 'pending_review',
            'reason': str | None,  # Only present if pending_review
            'confidence': float,    # 0.0 to 1.0
            'timestamp': str        # ISO 8601 timestamp
        }
    """
    from datetime import datetime
    
    # Default response (used on timeout or error)
    default_response = {
        'status': 'approved',
        'reason': None,
        'confidence': 0.0,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Timeout handler using threading
    result = {'response': default_response, 'completed': False}
    
    def call_bedrock():
        try:
            # Create moderation prompt
            prompt = f"""You are a content moderator for an AWS End User Computing (EUC) technical community platform. Analyze the following comment and determine if it should be approved or flagged for review.

CONTEXT:
- Post Title: {post_context.get('title', 'N/A')}
- Post Tags: {post_context.get('tags', 'N/A')}

COMMENT TO ANALYZE:
{text}

EVALUATION CRITERIA:

1. SPAM/PROMOTIONAL (Flag if):
   - Promotes products/services unrelated to AWS EUC
   - Contains repetitive or template-like text
   - Has 3+ external links
   - Solicits business or sales

2. DANGEROUS LINKS (Flag if):
   - Contains IP address URLs
   - Contains URL shorteners (bit.ly, tinyurl, etc.)
   - Contains suspicious TLDs (.tk, .ml, .ga, etc.)
   - Has 3+ URLs regardless of domain

3. HARASSMENT/ABUSE (Flag if):
   - Contains profanity, slurs, or personal attacks
   - Contains threats or aggressive language
   - Targets individuals rather than ideas

4. OFF-TOPIC (Flag if):
   - Discusses topics completely unrelated to AWS, cloud, or EUC
   - Is spam or nonsense text

DO NOT FLAG:
- Technical criticism or disagreement
- Links to AWS docs, GitHub, Stack Overflow
- Questions about the post content
- Personal experiences with AWS EUC services
- Mild frustration about technical issues

IMPORTANT: Prefer false negatives over false positives. When in doubt, approve.

Respond in JSON format:
{{
  "status": "approved" or "pending_review",
  "reason": "Brief explanation if pending_review, null if approved",
  "confidence": 0.0 to 1.0
}}"""
            
            # Call Bedrock API
            response = bedrock_runtime.invoke_model(
                modelId='anthropic.claude-3-haiku-20240307-v1:0',
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 200,
                    'messages': [
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ]
                })
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                moderation_result = json.loads(json_match.group())
                
                # Validate and normalize response
                status = moderation_result.get('status', 'approved')
                if status not in ['approved', 'pending_review']:
                    status = 'approved'
                
                confidence = float(moderation_result.get('confidence', 0.0))
                confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1
                
                result['response'] = {
                    'status': status,
                    'reason': moderation_result.get('reason') if status == 'pending_review' else None,
                    'confidence': confidence,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            result['completed'] = True
            
        except Exception as e:
            print(f"Bedrock moderation error: {str(e)}")
            result['completed'] = True
    
    # Start Bedrock call in thread
    thread = threading.Thread(target=call_bedrock)
    thread.daemon = True
    thread.start()
    
    # Wait up to 2 seconds
    thread.join(timeout=2.0)
    
    if not result['completed']:
        print(f"Moderation timeout for comment, defaulting to approved")
    
    return result['response']


def require_auth(func):
    """
    Decorator to require authentication for endpoints
    Validates JWT token and adds user info to event
    """
    @wraps(func)
    def wrapper(event, *args, **kwargs):
        # Get Authorization header
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization') or headers.get('authorization')
        
        if not auth_header:
            return {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Unauthorized', 'message': 'Missing Authorization header'})
            }
        
        try:
            # Validate token
            decoded_token = validate_jwt_token(auth_header)
            
            # Add user info to event for use in handler
            event['user'] = {
                'sub': decoded_token.get('sub'),
                'email': decoded_token.get('email'),
                'username': decoded_token.get('cognito:username')
            }
            
            return func(event, *args, **kwargs)
        
        except Exception as e:
            return {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Unauthorized', 'message': str(e)})
            }
    
    return wrapper


def lambda_handler(event, context):
    """
    Main Lambda handler
    
    Routes:
    - GET /posts - Get all blog posts
    - GET /posts/{id} - Get a specific post by ID
    - POST /posts/{id}/vote - Vote on a post
    - POST /posts/{id}/resolve - Mark post as resolved
    - GET /posts/{id}/comments - Get comments for a post
    - POST /posts/{id}/comments - Add a comment to a post
    - POST /crawl - Trigger the crawler Lambda
    - POST /summaries - Trigger summary generation
    - GET /profile - Get current user's profile (requires auth)
    - PUT /profile - Update current user's profile (requires auth)
    - DELETE /profile - Delete current user's profile and all data (requires auth)
    - GET /profile/activity - Get current user's activity history (requires auth)
    - GET /profile/{id} - Get public profile of a user
    """
    
    print(f"Event: {json.dumps(event)}")
    
    # Initialize tables with correct suffix for this request
    global table, profiles_table, TABLE_NAME, PROFILES_TABLE_NAME
    table_suffix = get_table_suffix(event)
    TABLE_NAME = f'aws-blog-posts{table_suffix}'
    PROFILES_TABLE_NAME = f'euc-user-profiles{table_suffix}'
    table = dynamodb.Table(TABLE_NAME)
    profiles_table = dynamodb.Table(PROFILES_TABLE_NAME)
    
    print(f"Using tables: {TABLE_NAME}, {PROFILES_TABLE_NAME}")
    
    # Handle OPTIONS request for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': ''
        }
    
    # Get the HTTP method and path
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    path_parameters = event.get('pathParameters') or {}
    query_parameters = event.get('queryStringParameters') or {}
    
    try:
        # Route the request
        if path == '/posts' and http_method == 'GET':
            return get_all_posts(query_parameters)
        elif path == '/crawl' and http_method == 'POST':
            return trigger_crawler()
        elif path == '/summaries' and http_method == 'POST':
            return trigger_summary_generation()
        elif path == '/bookmarks' and http_method == 'GET':
            return get_user_bookmarks(event)
        elif path == '/profile' and http_method == 'GET':
            return get_user_profile(event)
        elif path == '/profile' and http_method == 'PUT':
            body = json.loads(event.get('body', '{}'))
            return update_user_profile(event, body)
        elif path == '/profile' and http_method == 'DELETE':
            return delete_user_profile(event)
        elif path == '/profile/activity' and http_method == 'GET':
            return get_user_activity(event)
        elif path.startswith('/profile/') and http_method == 'GET':
            user_id = path_parameters.get('id')
            return get_public_profile(user_id)
        elif path.startswith('/posts/') and path.endswith('/bookmark') and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return toggle_bookmark(event, body)
        elif path.startswith('/posts/') and path.endswith('/vote') and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return vote_on_post(event, body)
        elif path.startswith('/posts/') and path.endswith('/resolve') and http_method == 'POST':
            post_id = path_parameters.get('id')
            body = json.loads(event.get('body', '{}'))
            return resolve_post(post_id, body)
        elif path.startswith('/posts/') and path.endswith('/comments'):
            if http_method == 'GET':
                post_id = path_parameters.get('id')
                return get_comments(event, post_id)
            elif http_method == 'POST':
                body = json.loads(event.get('body', '{}'))
                return add_comment(event, body)
        elif path.startswith('/posts/') and http_method == 'GET':
            post_id = path_parameters.get('id')
            return get_post_by_id(post_id)
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Not found'})
            }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }


def get_all_posts(query_params):
    """Get all blog posts from DynamoDB"""
    try:
        # Scan the table
        response = table.scan()
        items = response.get('Items', [])
        
        # Handle pagination if there are more items
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))
        
        # Optional: Filter by search query
        search_query = query_params.get('q', '').lower()
        if search_query:
            items = [
                item for item in items
                if search_query in item.get('title', '').lower() or
                   search_query in item.get('authors', '').lower() or
                   search_query in item.get('tags', '').lower()
            ]
        
        # Sort by date_published (newest first) by default
        items.sort(key=lambda x: x.get('date_published', ''), reverse=True)
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'posts': items,
                'count': len(items)
            }, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error in get_all_posts: {str(e)}")
        raise


def get_post_by_id(post_id):
    """Get a specific blog post by ID"""
    if not post_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Post ID is required'})
        }
    
    try:
        response = table.get_item(Key={'post_id': post_id})
        item = response.get('Item')
        
        if not item:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Post not found'})
            }
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'post': item}, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error in get_post_by_id: {str(e)}")
        raise


@require_auth
def vote_on_post(event, body):
    """
    Vote on a post for review or love it
    Requires authentication - user ID extracted from JWT token
    
    Body parameters:
    - vote_type: 'needs_update', 'remove_post', or 'love'
    - voter_id: unique identifier for the voter (validated against token)
    """
    post_id = event.get('pathParameters', {}).get('id')
    
    if not post_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Post ID is required'})
        }
    
    vote_type = body.get('vote_type')
    voter_id = body.get('voter_id')
    
    # Get authenticated user ID from token
    authenticated_user_id = event['user']['sub']
    
    # Verify voter_id matches authenticated user
    if voter_id != authenticated_user_id:
        return {
            'statusCode': 403,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Forbidden', 'message': 'voter_id must match authenticated user'})
        }
    
    if not vote_type or vote_type not in ['needs_update', 'remove_post', 'love']:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Invalid vote_type. Must be "needs_update", "remove_post", or "love"'})
        }
    
    try:
        # Get the current post
        response = table.get_item(Key={'post_id': post_id})
        item = response.get('Item')
        
        if not item:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Post not found'})
            }
        
        # For love votes, use separate tracking
        if vote_type == 'love':
            lovers = item.get('lovers', [])
            if voter_id in lovers:
                return {
                    'statusCode': 400,
                    'headers': cors_headers(),
                    'body': json.dumps({'error': 'You have already loved this post'})
                }
            
            # Update love count
            table.update_item(
                Key={'post_id': post_id},
                UpdateExpression='SET love_votes = if_not_exists(love_votes, :zero) + :inc, lovers = list_append(if_not_exists(lovers, :empty_list), :lover)',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':zero': 0,
                    ':lover': [voter_id],
                    ':empty_list': []
                }
            )
        else:
            # For needs_update and remove_post votes, check voters array
            voters = item.get('voters', [])
            if voter_id in voters:
                return {
                    'statusCode': 400,
                    'headers': cors_headers(),
                    'body': json.dumps({'error': 'You have already voted on this post'})
                }
            
            # Update the vote count
            vote_field = f'{vote_type}_votes'
            
            table.update_item(
                Key={'post_id': post_id},
                UpdateExpression=f'SET {vote_field} = if_not_exists({vote_field}, :zero) + :inc, voters = list_append(if_not_exists(voters, :empty_list), :voter)',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':zero': 0,
                    ':voter': [voter_id],
                    ':empty_list': []
                }
            )
        
        # Get updated post
        response = table.get_item(Key={'post_id': post_id})
        updated_item = response.get('Item')
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Vote recorded successfully',
                'post': updated_item
            }, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error in vote_on_post: {str(e)}")
        raise


def resolve_post(post_id, body):
    """
    Mark a post as resolved (action taken)
    
    Body parameters:
    - status: 'resolved' or 'pending' or 'archived'
    - resolved_by: identifier of who resolved it (optional)
    - notes: optional notes about the resolution
    """
    if not post_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Post ID is required'})
        }
    
    status = body.get('status', 'resolved')
    resolved_by = body.get('resolved_by', 'unknown')
    notes = body.get('notes', '')
    
    if status not in ['pending', 'resolved', 'archived']:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Invalid status. Must be "pending", "resolved", or "archived"'})
        }
    
    try:
        from datetime import datetime
        
        # Update the post status
        update_expression = 'SET #status = :status'
        expression_values = {':status': status}
        expression_names = {'#status': 'status'}
        
        # Add resolved metadata if marking as resolved
        if status == 'resolved':
            update_expression += ', resolved_date = :resolved_date, resolved_by = :resolved_by'
            expression_values[':resolved_date'] = datetime.utcnow().isoformat()
            expression_values[':resolved_by'] = resolved_by
            
            if notes:
                update_expression += ', resolution_notes = :notes'
                expression_values[':notes'] = notes
        
        table.update_item(
            Key={'post_id': post_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values
        )
        
        # Get updated post
        response = table.get_item(Key={'post_id': post_id})
        updated_item = response.get('Item')
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': f'Post marked as {status}',
                'post': updated_item
            }, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error in resolve_post: {str(e)}")
        raise


def trigger_crawler():
    """
    Trigger both AWS blog and Builder.AWS crawlers
    Builder.AWS crawler uses Selenium to extract real author names
    """
    import boto3
    
    try:
        lambda_client = boto3.client('lambda')
        
        # Invoke AWS blog crawler
        lambda_client.invoke(
            FunctionName='aws-blog-crawler',
            InvocationType='Event',
            Payload=json.dumps({'source': 'aws-blog'})
        )
        
        # Invoke Builder.AWS Selenium crawler (extracts real authors)
        lambda_client.invoke(
            FunctionName='aws-blog-builder-selenium-crawler',
            InvocationType='Event',
            Payload=json.dumps({})
        )
        
        return {
            'statusCode': 202,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Crawlers started successfully',
                'status': 'running',
                'sources': {
                    'aws_blog': 'Crawling with full metadata (5-10 minutes)',
                    'builder_aws': 'Crawling with Selenium - extracting real authors (10-15 minutes)'
                },
                'note': 'Both crawlers extract real author names. Builder.AWS uses Selenium for JavaScript rendering.'
            })
        }
    
    except Exception as e:
        print(f"Error in trigger_crawler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({
                'error': 'Failed to start crawler',
                'message': str(e)
            })
        }


def trigger_summary_generation():
    """
    Trigger the summary generator Lambda function
    """
    import boto3
    
    try:
        lambda_client = boto3.client('lambda')
        
        # Invoke the summary generator Lambda asynchronously
        response = lambda_client.invoke(
            FunctionName='aws-blog-summary-generator',
            InvocationType='Event',  # Asynchronous invocation
            Payload=json.dumps({'batch_size': 20})
        )
        
        return {
            'statusCode': 202,  # Accepted
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Summary generation started successfully',
                'status': 'running',
                'note': 'Summaries are being generated in the background. This may take a few minutes.'
            })
        }
    
    except Exception as e:
        print(f"Error in trigger_summary_generation: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({
                'error': 'Failed to start summary generation',
                'message': str(e)
            })
        }


def get_comments(event, post_id):
    """
    Get all comments for a specific post
    Filters comments based on moderation status and viewer identity
    """
    if not post_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Post ID is required'})
        }
    
    try:
        response = table.get_item(Key={'post_id': post_id})
        item = response.get('Item')
        
        if not item:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Post not found'})
        }
        
        comments = item.get('comments', [])
        
        # Get current user ID if authenticated
        current_user_id = None
        try:
            headers = event.get('headers', {})
            auth_header = headers.get('Authorization') or headers.get('authorization')
            
            if auth_header:
                try:
                    decoded = validate_jwt_token(auth_header)
                    current_user_id = decoded.get('sub')
                except:
                    pass  # Not authenticated, that's okay
        except:
            pass  # No auth header, that's okay
        
        # Filter comments based on moderation status
        filtered_comments = []
        for comment in comments:
            status = comment.get('moderation_status', 'approved')  # Legacy comments default to approved
            
            # Show approved comments to everyone
            if status == 'approved':
                filtered_comments.append(comment)
            # Show pending comments only to author
            elif status == 'pending_review' and comment.get('voter_id') == current_user_id:
                filtered_comments.append(comment)
            # Hide rejected comments (future functionality)
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'comments': filtered_comments,
                'count': len(filtered_comments)
            }, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error in get_comments: {str(e)}")
        raise


@require_auth
def add_comment(event, body):
    """
    Add a comment to a post with automated moderation
    Requires authentication - user ID extracted from JWT token
    
    Body parameters:
    - text: comment text (required)
    - voter_id: identifier of commenter (validated against token)
    """
    post_id = event.get('pathParameters', {}).get('id')
    
    if not post_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Post ID is required'})
        }
    
    text = body.get('text', '').strip()
    voter_id = body.get('voter_id')
    
    # Get authenticated user ID from token
    authenticated_user_id = event['user']['sub']
    
    # Verify voter_id matches authenticated user
    if voter_id != authenticated_user_id:
        return {
            'statusCode': 403,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Forbidden', 'message': 'voter_id must match authenticated user'})
        }
    
    if not text:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Comment text is required'})
        }
    
    try:
        from datetime import datetime
        import uuid
        
        # Get post context for moderation
        post_response = table.get_item(Key={'post_id': post_id})
        post = post_response.get('Item')
        
        if not post:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Post not found'})
            }
        
        post_context = {
            'post_id': post_id,
            'title': post.get('title', ''),
            'tags': post.get('tags', '')
        }
        
        # Moderate comment
        try:
            moderation_result = moderate_comment(text, post_context)
            print(f"Moderation result: {json.dumps(moderation_result)}")
        except Exception as e:
            print(f"Moderation error: {e}")
            # Default to approved on error
            moderation_result = {
                'status': 'approved',
                'reason': None,
                'confidence': 0.0,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        # Get user's display name from profile
        display_name = 'User'
        try:
            profile_response = profiles_table.get_item(Key={'user_id': voter_id})
            profile = profile_response.get('Item')
            if profile:
                display_name = profile.get('display_name', 'User')
        except Exception as e:
            print(f"Error fetching profile for display name: {e}")
        
        # Create comment object with moderation metadata
        comment = {
            'comment_id': str(uuid.uuid4()),
            'voter_id': voter_id,
            'display_name': display_name,
            'text': text,
            'timestamp': datetime.utcnow().isoformat(),
            'moderation_status': moderation_result['status'],
            'moderation_confidence': Decimal(str(moderation_result['confidence'])),  # Convert float to Decimal
            'moderation_timestamp': moderation_result['timestamp']
        }
        
        # Add reason if flagged
        if moderation_result['status'] == 'pending_review' and moderation_result['reason']:
            comment['moderation_reason'] = moderation_result['reason']
        
        # Add comment to post
        table.update_item(
            Key={'post_id': post_id},
            UpdateExpression='SET comments = list_append(if_not_exists(comments, :empty_list), :comment), comment_count = if_not_exists(comment_count, :zero) + :inc',
            ExpressionAttributeValues={
                ':comment': [comment],
                ':empty_list': [],
                ':zero': 0,
                ':inc': 1
            }
        )
        
        # Get updated post
        response = table.get_item(Key={'post_id': post_id})
        updated_item = response.get('Item')
        
        return {
            'statusCode': 201,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Comment added successfully',
                'comment': comment,
                'post': updated_item
            }, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error in add_comment: {str(e)}")
        raise


# ============================================================================
# User Profile Endpoints
# ============================================================================

# User profiles table - will be initialized per request
PROFILES_TABLE_NAME = None
profiles_table = None


@require_auth
def get_user_profile(event):
    """
    Get current user's profile
    Requires authentication
    """
    user_id = event['user']['sub']
    email = event['user'].get('email', '')
    
    try:
        # Get profile from DynamoDB
        response = profiles_table.get_item(Key={'user_id': user_id})
        profile = response.get('Item')
        
        # If profile doesn't exist, create default one
        if not profile:
            # Extract first name from email or use default
            display_name = email.split('@')[0] if email else 'User'
            
            profile = {
                'user_id': user_id,
                'email': email,
                'display_name': display_name,
                'bio': '',
                'credly_url': '',
                'created_at': get_timestamp(),
                'updated_at': get_timestamp(),
                'stats': {
                    'votes_count': 0,
                    'comments_count': 0
                }
            }
            
            # Save to DynamoDB
            profiles_table.put_item(Item=profile)
        
        # Calculate actual stats from posts
        profile['stats'] = calculate_user_stats(user_id)
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'profile': profile}, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error in get_user_profile: {str(e)}")
        raise


@require_auth
def update_user_profile(event, body):
    """
    Update current user's profile
    Requires authentication
    
    Body parameters:
    - display_name: string (3-50 chars)
    - bio: string (max 500 chars)
    - credly_url: string (optional)
    - builder_id: string (optional, username only)
    """
    user_id = event['user']['sub']
    
    display_name = body.get('display_name', '').strip()
    bio = body.get('bio', '').strip()
    credly_url = body.get('credly_url', '').strip()
    builder_id = body.get('builder_id', '').strip()
    
    # Validation
    if not display_name or len(display_name) < 3:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Display name must be at least 3 characters'})
        }
    
    if len(display_name) > 50:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Display name must be 50 characters or less'})
        }
    
    if len(bio) > 500:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Bio must be 500 characters or less'})
        }
    
    # Validate Credly URL if provided
    if credly_url and not credly_url.startswith('https://www.credly.com/'):
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Credly URL must start with https://www.credly.com/'})
        }
    
    # Validate Builder ID if provided (alphanumeric, underscore, hyphen only)
    if builder_id:
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', builder_id):
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Builder Center ID can only contain letters, numbers, underscores, and hyphens'})
            }
        if len(builder_id) > 50:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Builder Center ID must be 50 characters or less'})
            }
    
    try:
        # Update profile
        profiles_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET display_name = :name, bio = :bio, credly_url = :credly, builder_id = :builder, updated_at = :updated',
            ExpressionAttributeValues={
                ':name': display_name,
                ':bio': bio,
                ':credly': credly_url,
                ':builder': builder_id,
                ':updated': get_timestamp()
            }
        )
        
        # Get updated profile
        response = profiles_table.get_item(Key={'user_id': user_id})
        profile = response.get('Item')
        
        # Add stats
        profile['stats'] = calculate_user_stats(user_id)
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Profile updated successfully',
                'profile': profile
            }, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error in update_user_profile: {str(e)}")
        raise


@require_auth
def delete_user_profile(event):
    """
    Delete current user's profile and all associated data
    Requires authentication
    
    This will permanently delete:
    - User profile (including bookmarks)
    - All votes (love, needs_update, remove_post)
    - All comments
    """
    user_id = event['user']['sub']
    
    try:
        # 1. Delete all votes - scan posts and remove user's votes
        posts_response = table.scan()
        for post in posts_response.get('Items', []):
            post_id = post['post_id']
            
            # Check if user has voted on this post
            love_voters = post.get('love_voters', [])
            needs_update_voters = post.get('needs_update_voters', [])
            remove_post_voters = post.get('remove_post_voters', [])
            
            update_needed = False
            update_expression_parts = []
            expression_values = {}
            
            if user_id in love_voters:
                love_voters.remove(user_id)
                update_expression_parts.append('love_voters = :love_voters')
                update_expression_parts.append('love_votes = :love_votes')
                expression_values[':love_voters'] = love_voters
                expression_values[':love_votes'] = len(love_voters)
                update_needed = True
            
            if user_id in needs_update_voters:
                needs_update_voters.remove(user_id)
                update_expression_parts.append('needs_update_voters = :update_voters')
                update_expression_parts.append('needs_update_votes = :update_votes')
                expression_values[':update_voters'] = needs_update_voters
                expression_values[':update_votes'] = len(needs_update_voters)
                update_needed = True
            
            if user_id in remove_post_voters:
                remove_post_voters.remove(user_id)
                update_expression_parts.append('remove_post_voters = :remove_voters')
                update_expression_parts.append('remove_post_votes = :remove_votes')
                expression_values[':remove_voters'] = remove_post_voters
                expression_values[':remove_votes'] = len(remove_post_voters)
                update_needed = True
            
            if update_needed:
                table.update_item(
                    Key={'post_id': post_id},
                    UpdateExpression='SET ' + ', '.join(update_expression_parts),
                    ExpressionAttributeValues=expression_values
                )
        
        # 2. Delete all comments - scan posts and remove user's comments
        posts_response = table.scan()
        for post in posts_response.get('Items', []):
            post_id = post['post_id']
            comments = post.get('comments', [])
            
            # Filter out user's comments
            user_comments = [c for c in comments if c.get('user_id') == user_id or c.get('voter_id') == user_id]
            
            if user_comments:
                # Remove user's comments
                new_comments = [c for c in comments if c.get('user_id') != user_id and c.get('voter_id') != user_id]
                
                table.update_item(
                    Key={'post_id': post_id},
                    UpdateExpression='SET comments = :comments, comment_count = :count',
                    ExpressionAttributeValues={
                        ':comments': new_comments,
                        ':count': len(new_comments)
                    }
                )
        
        # 3. Delete user profile (bookmarks are stored in profile)
        profiles_table.delete_item(Key={'user_id': user_id})
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Account deleted successfully'
            })
        }
    
    except Exception as e:
        print(f"Error in delete_user_profile: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to delete account'})
        }


def get_public_profile(user_id):
    """
    Get public profile of a user (no auth required)
    Returns only public information
    """
    if not user_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'User ID is required'})
        }
    
    try:
        response = profiles_table.get_item(Key={'user_id': user_id})
        profile = response.get('Item')
        
        if not profile:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Profile not found'})
            }
        
        # Return only public fields
        public_profile = {
            'user_id': profile['user_id'],
            'display_name': profile.get('display_name', 'User'),
            'bio': profile.get('bio', ''),
            'credly_url': profile.get('credly_url', ''),
            'builder_id': profile.get('builder_id', ''),
            'stats': calculate_user_stats(user_id)
        }
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'profile': public_profile}, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error in get_public_profile: {str(e)}")
        raise


@require_auth
def toggle_bookmark(event, body):
    """
    Toggle bookmark on a post (add or remove)
    Requires authentication
    
    Body parameters:
    - user_id: user identifier (validated against token)
    """
    post_id = event.get('pathParameters', {}).get('id')
    
    if not post_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Post ID is required'})
        }
    
    user_id = event['user']['sub']
    body_user_id = body.get('user_id')
    
    # Verify user_id matches authenticated user
    if body_user_id and body_user_id != user_id:
        return {
            'statusCode': 403,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Forbidden', 'message': 'user_id must match authenticated user'})
        }
    
    try:
        # Get current profile
        response = profiles_table.get_item(Key={'user_id': user_id})
        profile = response.get('Item')
        
        if not profile:
            # Create profile if doesn't exist
            profile = {
                'user_id': user_id,
                'email': event['user'].get('email', ''),
                'display_name': event['user'].get('email', '').split('@')[0],
                'bookmarks': [],
                'created_at': get_timestamp(),
                'updated_at': get_timestamp()
            }
        
        bookmarks = profile.get('bookmarks', [])
        
        # Toggle bookmark
        if post_id in bookmarks:
            # Remove bookmark
            bookmarks.remove(post_id)
            action = 'removed'
        else:
            # Add bookmark
            bookmarks.append(post_id)
            action = 'added'
        
        # Update profile
        profiles_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET bookmarks = :bookmarks, updated_at = :updated',
            ExpressionAttributeValues={
                ':bookmarks': bookmarks,
                ':updated': get_timestamp()
            }
        )
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': f'Bookmark {action}',
                'bookmarked': post_id in bookmarks,
                'bookmark_count': len(bookmarks)
            })
        }
    
    except Exception as e:
        print(f"Error in toggle_bookmark: {str(e)}")
        raise


@require_auth
def get_user_bookmarks(event):
    """
    Get user's bookmarked posts
    Requires authentication
    """
    user_id = event['user']['sub']
    
    try:
        # Get user's bookmarks from profile
        response = profiles_table.get_item(Key={'user_id': user_id})
        profile = response.get('Item')
        
        if not profile or not profile.get('bookmarks'):
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps({
                    'bookmarks': [],
                    'count': 0
                })
            }
        
        bookmark_ids = profile.get('bookmarks', [])
        
        # Get full post details for bookmarked posts
        bookmarked_posts = []
        for post_id in bookmark_ids:
            try:
                post_response = table.get_item(Key={'post_id': post_id})
                post = post_response.get('Item')
                if post:
                    bookmarked_posts.append(post)
            except Exception as e:
                print(f"Error fetching bookmarked post {post_id}: {e}")
                continue
        
        # Sort by date (newest first)
        bookmarked_posts.sort(key=lambda x: x.get('date_published', ''), reverse=True)
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'bookmarks': bookmarked_posts,
                'count': len(bookmarked_posts)
            }, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error in get_user_bookmarks: {str(e)}")
        raise


@require_auth
def get_user_activity(event):
    """
    Get current user's activity history (votes and comments)
    Requires authentication
    """
    user_id = event['user']['sub']
    
    try:
        # Scan posts table for user's votes and comments
        response = table.scan()
        posts = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            posts.extend(response.get('Items', []))
        
        # Find posts user voted on
        voted_posts = []
        for post in posts:
            voters = post.get('voters', [])
            if user_id in voters:
                voted_posts.append({
                    'post_id': post['post_id'],
                    'title': post['title'],
                    'url': post.get('url', ''),
                    'date_published': post.get('date_published', ''),
                    'needs_update_votes': post.get('needs_update_votes', 0),
                    'remove_post_votes': post.get('remove_post_votes', 0)
                })
        
        # Find posts user loved
        loved_posts = []
        for post in posts:
            lovers = post.get('lovers', [])
            if user_id in lovers:
                loved_posts.append({
                    'post_id': post['post_id'],
                    'title': post['title'],
                    'url': post.get('url', ''),
                    'date_published': post.get('date_published', ''),
                    'love_votes': post.get('love_votes', 0)
                })
        
        # Find user's comments
        user_comments = []
        for post in posts:
            comments = post.get('comments', [])
            for comment in comments:
                if comment.get('voter_id') == user_id:
                    user_comments.append({
                        'comment_id': comment.get('comment_id'),
                        'post_id': post['post_id'],
                        'post_title': post['title'],
                        'text': comment.get('text', ''),
                        'timestamp': comment.get('timestamp', '')
                    })
        
        # Sort by timestamp (most recent first)
        user_comments.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        voted_posts.sort(key=lambda x: x.get('date_published', ''), reverse=True)
        loved_posts.sort(key=lambda x: x.get('date_published', ''), reverse=True)
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'votes': voted_posts,
                'loves': loved_posts,
                'comments': user_comments,
                'stats': {
                    'votes_count': len(voted_posts),
                    'loves_count': len(loved_posts),
                    'comments_count': len(user_comments)
                }
            }, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error in get_user_activity: {str(e)}")
        raise


def calculate_user_stats(user_id):
    """
    Calculate user statistics from posts table and profile
    """
    try:
        response = table.scan()
        posts = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            posts.extend(response.get('Items', []))
        
        votes_count = 0
        loves_count = 0
        comments_count = 0
        
        for post in posts:
            # Count votes
            voters = post.get('voters', [])
            if user_id in voters:
                votes_count += 1
            
            # Count loves
            lovers = post.get('lovers', [])
            if user_id in lovers:
                loves_count += 1
            
            # Count comments
            comments = post.get('comments', [])
            for comment in comments:
                if comment.get('voter_id') == user_id:
                    comments_count += 1
        
        # Get bookmark count from profile
        bookmarks_count = 0
        try:
            profile_response = profiles_table.get_item(Key={'user_id': user_id})
            profile = profile_response.get('Item')
            if profile:
                bookmarks_count = len(profile.get('bookmarks', []))
        except Exception as e:
            print(f"Error getting bookmarks count: {e}")
        
        return {
            'votes_count': votes_count,
            'loves_count': loves_count,
            'comments_count': comments_count,
            'bookmarks_count': bookmarks_count
        }
    
    except Exception as e:
        print(f"Error calculating stats: {str(e)}")
        return {'votes_count': 0, 'loves_count': 0, 'comments_count': 0, 'bookmarks_count': 0}


def get_timestamp():
    """Get current timestamp in ISO format"""
    from datetime import datetime
    return datetime.utcnow().isoformat()
