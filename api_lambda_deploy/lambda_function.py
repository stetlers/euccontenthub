```python
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
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
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


def check_admin_authorization(user_id):
    """
    Check if user has valid Amazon email verification for admin access
    
    Args:
        user_id: The user's Cognito sub ID
    
    Returns:
        dict: {
            'authorized': bool,
            'reason': str (only if not authorized)
        }
    """
    try:
        # Get user profile from DynamoDB
        response = profiles_table.get_item(Key={'user_id': user_id})
        profile = response.get('Item')
        
        if not profile:
            return {
                'authorized': False,
                'reason': 'User profile not found'
            }
        
        # Check if user has Amazon verification
        amazon_verified = profile.get('amazon_verified', False)
        if not amazon_verified:
            return {
                'authorized': False,
                'reason': 'Amazon email verification required for admin access'
            }
        
        # Check if verification has been revoked
        verification_revoked = profile.get('amazon_verification_revoked', False)
        if verification_revoked:
            return {
                'authorized': False,
                'reason': 'Amazon email verification has been revoked'
            }
        
        # Check if verification has expired
        from datetime import datetime
        expires_at_str = profile.get('amazon_verified_expires_at')
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                now = datetime.utcnow()
                if now >= expires_at:
                    return {
                        'authorized': False,
                        'reason': 'Amazon email verification has expired'
                    }
            except Exception as e:
                print(f"Error parsing expiration date: {e}")
                return {
                    'authorized': False,
                    'reason': 'Invalid verification expiration date'
                }
        else:
            return {
                'authorized': False,
                'reason': 'Verification expiration date not set'
            }
        
        # All checks passed
        return {'authorized': True}
    
    except Exception as e:
        print(f"Error checking admin authorization: {str(e)}")
        return {
            'authorized': False,
            'reason': f'Error checking authorization: {str(e)}'
        }


def require_admin(func):
    """
    Decorator to require admin authorization (Amazon email verification)
    Must be used after @require_auth decorator
    """
    @wraps(func)
    def wrapper(event, *args, **kwargs):
        # User info should already be in event from @require_auth
        user_id = event.get('user', {}).get('sub')
        
        if not user_id:
            return {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Unauthorized',
                    'message': 'Authentication required'
                })
            }
        
        # Check admin authorization
        auth_result = check_admin_authorization(user_id)
        
        if not auth_result['authorized']:
            return {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Forbidden',
                    'message': auth_result.get('reason', 'Admin access denied')
                })
            }
        
        # Authorization passed, call the handler
        return func(event, *args, **kwargs)
    
    return wrapper


def lambda_handler(event, context):
    """
    Main Lambda handler
    
    Routes:
    - GET /posts - Get all blog posts
    - GET /posts/{id} - Get a specific post by ID
    - POST /posts/{id}/vote - Vote on a post
    - DELETE /posts/{id}/vote - Remove vote from a post (unvote)
    - POST /posts/{id}/resolve - Mark post as resolved
    - GET /posts/{id}/comments - Get comments for a post
    - POST /posts/{id}/comments - Add a comment to a post
    - DELETE /posts/{id}/comments - Delete a comment (own comments or admin)
    - POST /crawl - Trigger the crawler Lambda
    - POST /summaries - Trigger summary generation
    - GET /profile - Get current user's profile (requires auth)
    - PUT /profile - Update current user's profile (requires auth)
    - DELETE /profile - Delete current user's profile and all data (requires auth)
    - GET /profile/activity - Get current user's activity history (requires auth)
    - GET /profile/{id} - Get public profile of a user
    - POST /verify-email - Request Amazon email verification (requires auth)
    - GET /verify-email - Confirm email verification with token
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