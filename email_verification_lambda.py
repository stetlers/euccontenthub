import boto3
import json
import uuid
import time
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

# Table names - will be set via environment variables
PROFILES_TABLE = 'euc-user-profiles-staging'
TOKENS_TABLE = 'email-verification-tokens-staging'

profiles_table = dynamodb.Table(PROFILES_TABLE)
tokens_table = dynamodb.Table(TOKENS_TABLE)

def cors_headers():
    """Return CORS headers for API responses"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }

def lambda_handler(event, context):
    """Main Lambda handler"""
    print(f"Event: {json.dumps(event)}")
    
    path = event.get('path', '')
    method = event.get('httpMethod', '')
    
    # Handle OPTIONS for CORS
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': ''
        }
    
    if path == '/verify-email/request' and method == 'POST':
        return request_verification(event)
    elif path == '/verify-email/confirm' and method == 'GET':
        return confirm_verification(event)
    
    return {
        'statusCode': 404,
        'headers': cors_headers(),
        'body': json.dumps({'error': 'Not found'})
    }

def request_verification(event):
    """Send verification email"""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        amazon_email = body.get('amazon_email', '').strip().lower()
        
        # Get user from JWT (simplified - in production, validate JWT properly)
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header:
            return {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Unauthorized'})
            }
        
        # For now, extract user_id from event (API Gateway should set this)
        user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
        if not user_id:
            # Fallback for testing
            user_id = 'test_user_123'
        
        # Validate email format
        if not amazon_email.endswith('@amazon.com'):
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Must be @amazon.com email'})
            }
        
        # Generate verification token
        token = str(uuid.uuid4())
        created_at = int(time.time())
        expires_at = created_at + 3600  # 1 hour
        
        # Store token in DynamoDB
        tokens_table.put_item(
            Item={
                'token': token,
                'user_id': user_id,
                'email': amazon_email,
                'created_at': created_at,
                'expires_at': expires_at,
                'used': False
            }
        )
        
        # Send verification email
        verification_link = f"https://staging.awseuccontent.com/verify?token={token}"
        
        # Get user's display name
        try:
            profile_response = profiles_table.get_item(Key={'user_id': user_id})
            display_name = profile_response.get('Item', {}).get('display_name', 'User')
        except:
            display_name = 'User'
        
        ses.send_email(
            Source='stetlers@amazon.com',  # Verified email
            Destination={'ToAddresses': [amazon_email]},
            Message={
                'Subject': {'Data': 'Verify your Amazon email for EUC Content Hub'},
                'Body': {
                    'Html': {
                        'Data': f"""
                        <html>
                        <body>
                            <h2>Verify Your Amazon Email</h2>
                            <p>Hi {display_name},</p>
                            <p>Click the link below to verify your Amazon email address and gain admin access to EUC Content Hub:</p>
                            <p><a href="{verification_link}" style="background-color: #FF9900; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Verify Email</a></p>
                            <p>Or copy and paste this link: {verification_link}</p>
                            <p><strong>This link expires in 1 hour.</strong></p>
                            <p>If you didn't request this, you can safely ignore this email.</p>
                            <p>Thanks,<br>EUC Content Hub Team</p>
                        </body>
                        </html>
                        """
                    }
                }
            }
        )
        
        print(f"Verification email sent to {amazon_email} for user {user_id}")
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'message': 'Verification email sent'})
        }
        
    except Exception as e:
        print(f"Error in request_verification: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error'})
        }

def confirm_verification(event):
    """Confirm email verification from link"""
    try:
        # Extract token from query string
        token = event.get('queryStringParameters', {}).get('token', '')
        
        if not token:
            return redirect_to_profile(False, 'No token provided')
        
        # Look up token in DynamoDB
        try:
            response = tokens_table.get_item(Key={'token': token})
            token_item = response.get('Item')
        except Exception as e:
            print(f"Error fetching token: {str(e)}")
            return redirect_to_profile(False, 'Invalid token')
        
        if not token_item:
            return redirect_to_profile(False, 'Token not found')
        
        # Check if token is expired
        now = int(time.time())
        if now > token_item['expires_at']:
            return redirect_to_profile(False, 'Token expired')
        
        # Check if token is already used
        if token_item.get('used', False):
            return redirect_to_profile(False, 'Token already used')
        
        # Mark token as used
        tokens_table.update_item(
            Key={'token': token},
            UpdateExpression='SET used = :true',
            ExpressionAttributeValues={':true': True}
        )
        
        # Update user profile with verification
        user_id = token_item['user_id']
        amazon_email = token_item['email']
        verified_at = datetime.utcnow().isoformat() + 'Z'
        expires_at = (datetime.utcnow() + timedelta(days=90)).isoformat() + 'Z'
        
        profiles_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET amazon_email = :email, amazon_verified = :verified, amazon_verified_at = :verified_at, amazon_verified_expires_at = :expires_at, verification_reminder_sent = :false',
            ExpressionAttributeValues={
                ':email': amazon_email,
                ':verified': True,
                ':verified_at': verified_at,
                ':expires_at': expires_at,
                ':false': False
            }
        )
        
        print(f"Verified {amazon_email} for user {user_id}")
        
        return redirect_to_profile(True, 'Email verified successfully')
        
    except Exception as e:
        print(f"Error in confirm_verification: {str(e)}")
        return redirect_to_profile(False, f'Error: {str(e)}')

def redirect_to_profile(success, message):
    """Return JSON response with verification status"""
    return {
        'statusCode': 200 if success else 400,
        'headers': cors_headers(),
        'body': json.dumps({
            'success': success,
            'message': message
        })
    }
