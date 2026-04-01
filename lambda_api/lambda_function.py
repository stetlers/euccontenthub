"""
API Lambda Function for Blog Posts Viewer
Provides REST API to query DynamoDB table
Includes JWT token validation for protected endpoints
Includes KB Editor endpoints for community contributions
"""

import json
import os
import boto3
from decimal import Decimal
import base64
from functools import wraps
import threading
import time
import uuid
import hashlib
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key, Attr

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')

# Initialize Bedrock Runtime client for comment moderation
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')

# Initialize S3 and Bedrock Agent clients for KB editor
s3 = boto3.client('s3')
bedrock_agent = boto3.client('bedrock-agent', region_name='us-east-1')

# Get table suffix for staging/production isolation
def get_table_suffix(event=None):
    """Extract table suffix from API Gateway stage variables or environment"""
    # Try stage variables first (from API Gateway)
    if event:
        stage_variables = event.get('stageVariables') or {}
        table_suffix = stage_variables.get('TABLE_SUFFIX', '')
        if table_suffix:
            return table_suffix
    
    # Fall back to environment variable
    return os.environ.get('TABLE_SUFFIX', '')

# Note: Tables will be initialized per request in lambda_handler
TABLE_NAME = None
table = None
WHATS_NEW_TABLE_NAME = None
whats_new_table = None
PROPOSALS_TABLE_NAME = None
proposals_table = None
CHAT_CONVERSATIONS_TABLE_NAME = None
chat_conversations_table = None
INNOVATIONS_TABLE_NAME = None
innovations_table = None

# Cognito configuration
COGNITO_REGION = os.environ.get('COGNITO_REGION', 'us-east-1')
COGNITO_USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', 'us-east-1_MOvNrTnua')
COGNITO_APP_CLIENT_ID = os.environ.get('COGNITO_APP_CLIENT_ID', '3pv5jf235vj14gu148b9vjt3od')

# Cognito JWKS URL
JWKS_URL = f'https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json'

# KB Editor configuration
KB_S3_BUCKET = os.environ.get('KB_S3_BUCKET', 'euc-content-hub-kb-staging')
KB_ID = os.environ.get('KB_ID', 'MIMYGSK1YU')
KB_DATA_SOURCE_ID = os.environ.get('KB_DATA_SOURCE_ID', 'XC68GVBFXK')
RATE_LIMIT_EDITS_PER_HOUR = 5

# KB Document metadata
KB_DOCUMENTS = {
    'curated-qa/common-questions.md': {
        'name': 'Common Questions (Q&A)',
        'description': 'Frequently asked questions about EUC services',
        'category': 'Q&A'
    },
    'service-mappings/service-renames.md': {
        'name': 'Service Renames & History',
        'description': 'Complete history of EUC service name changes',
        'category': 'Mappings'
    }
}

# Badge system constants
SITE_LAUNCH_DATE = '2026-01-15'

BADGE_CATEGORIES = [
    'Getting Started',
    'Voting Milestones',
    'Commenting Milestones',
    'Bookmarking',
    'Proposals',
    'Streaks and Consistency',
    'Special',
]

BADGE_REGISTRY = {
    # --- Getting Started ---
    'first_steps': {
        'name': 'First Steps',
        'icon': '👣',
        'category': 'Getting Started',
        'condition': {'type': 'auto_award'},
    },
    'lurker_no_more': {
        'name': 'Lurker No More',
        'icon': '🗳️',
        'category': 'Getting Started',
        'condition': {'type': 'threshold', 'counter': 'love_votes_given', 'value': 1},
    },
    'hot_take': {
        'name': 'Hot Take',
        'icon': '🔥',
        'category': 'Getting Started',
        'condition': {'type': 'threshold', 'counter': 'comments_made', 'value': 1},
    },
    'bookworm': {
        'name': 'Bookworm',
        'icon': '📖',
        'category': 'Getting Started',
        'condition': {'type': 'threshold', 'counter': 'bookmarks_held', 'value': 1},
    },
    # --- Voting Milestones ---
    'love_machine': {
        'name': 'Love Machine',
        'icon': '❤️',
        'category': 'Voting Milestones',
        'condition': {'type': 'threshold', 'counter': 'love_votes_given', 'value': 10},
    },
    'spread_the_love': {
        'name': 'Spread the Love',
        'icon': '💕',
        'category': 'Voting Milestones',
        'condition': {'type': 'threshold', 'counter': 'love_votes_given', 'value': 50},
    },
    'cupid_of_content': {
        'name': 'Cupid of Content',
        'icon': '💘',
        'category': 'Voting Milestones',
        'condition': {'type': 'threshold', 'counter': 'love_votes_given', 'value': 100},
    },
    'quality_inspector': {
        'name': 'Quality Inspector',
        'icon': '🔍',
        'category': 'Voting Milestones',
        'condition': {'type': 'threshold', 'counter': 'needs_update_votes_given', 'value': 5},
    },
    'the_auditor': {
        'name': 'The Auditor',
        'icon': '📋',
        'category': 'Voting Milestones',
        'condition': {'type': 'threshold', 'counter': 'needs_update_votes_given', 'value': 25},
    },
    # --- Commenting Milestones ---
    'chatterbox': {
        'name': 'Chatterbox',
        'icon': '💬',
        'category': 'Commenting Milestones',
        'condition': {'type': 'threshold', 'counter': 'comments_made', 'value': 10},
    },
    'town_crier': {
        'name': 'Town Crier',
        'icon': '📢',
        'category': 'Commenting Milestones',
        'condition': {'type': 'threshold', 'counter': 'comments_made', 'value': 25},
    },
    'the_commentator': {
        'name': 'The Commentator',
        'icon': '🎙️',
        'category': 'Commenting Milestones',
        'condition': {'type': 'threshold', 'counter': 'comments_made', 'value': 50},
    },
    'novelist': {
        'name': 'Novelist',
        'icon': '📝',
        'category': 'Commenting Milestones',
        'condition': {'type': 'text_length', 'counter': 'comment_length', 'value': 500},
    },
    # --- Bookmarking ---
    'collector': {
        'name': 'Collector',
        'icon': '📚',
        'category': 'Bookmarking',
        'condition': {'type': 'threshold', 'counter': 'bookmarks_held', 'value': 10},
    },
    'hoarder': {
        'name': 'Hoarder',
        'icon': '🗄️',
        'category': 'Bookmarking',
        'condition': {'type': 'threshold', 'counter': 'bookmarks_held', 'value': 50},
    },
    'the_librarian': {
        'name': 'The Librarian',
        'icon': '🏛️',
        'category': 'Bookmarking',
        'condition': {'type': 'threshold', 'counter': 'bookmarks_held', 'value': 100},
    },
    # --- Proposals ---
    'idea_person': {
        'name': 'Idea Person',
        'icon': '💡',
        'category': 'Proposals',
        'condition': {'type': 'threshold', 'counter': 'proposals_submitted', 'value': 1},
    },
    'pitch_perfect': {
        'name': 'Pitch Perfect',
        'icon': '🎯',
        'category': 'Proposals',
        'condition': {'type': 'threshold', 'counter': 'proposals_approved', 'value': 1},
    },
    # --- Streaks and Consistency ---
    'regular': {
        'name': 'Regular',
        'icon': '📅',
        'category': 'Streaks and Consistency',
        'condition': {'type': 'streak', 'counter': 'visit_streak', 'value': 5},
    },
    'dedicated': {
        'name': 'Dedicated',
        'icon': '🔥',
        'category': 'Streaks and Consistency',
        'condition': {'type': 'streak', 'counter': 'visit_streak', 'value': 15},
    },
    'no_life': {
        'name': 'No Life (Compliment)',
        'icon': '🏆',
        'category': 'Streaks and Consistency',
        'condition': {'type': 'streak', 'counter': 'visit_streak', 'value': 30},
    },
    # --- Special ---
    'night_owl': {
        'name': 'Night Owl',
        'icon': '🦉',
        'category': 'Special',
        'condition': {'type': 'time_of_day', 'min_hour': 0, 'max_hour': 4},
    },
    'early_bird': {
        'name': 'Early Bird',
        'icon': '🐦',
        'category': 'Special',
        'condition': {'type': 'time_of_day', 'min_hour': 5, 'max_hour': 6},
    },
    'explorer': {
        'name': 'Explorer',
        'icon': '🧭',
        'category': 'Special',
        'condition': {'type': 'set_size', 'counter': 'distinct_labels_read', 'value': 5},
    },
    'og': {
        'name': 'OG',
        'icon': '👑',
        'category': 'Special',
        'condition': {'type': 'auto_award'},
    },
    'chatty_with_the_bot': {
        'name': 'Chatty with the Bot',
        'icon': '🤖',
        'category': 'Special',
        'condition': {'type': 'threshold', 'counter': 'chatbot_questions', 'value': 20},
    },
}


def evaluate_badges(badge_progress, existing_badge_ids, visit_streak=0, utc_hour=None, comment_length=0, created_at=None):
    """
    Compare progress against all badge thresholds.
    Pure function — no DB calls, no side effects.
    Returns list of newly earned badge dicts: [{"badge_id": ..., "name": ..., "icon": ...}]
    """
    new_badges = []

    for badge_id, badge in BADGE_REGISTRY.items():
        # Skip badges the user already has
        if badge_id in existing_badge_ids:
            continue

        condition = badge.get('condition', {})
        ctype = condition.get('type')

        earned = False

        if ctype == 'auto_award':
            # Auto-award badges (First Steps, OG) are handled elsewhere
            continue

        elif ctype == 'threshold':
            counter_val = badge_progress.get(condition.get('counter', ''), 0)
            earned = counter_val >= condition.get('value', 0)

        elif ctype == 'streak':
            earned = visit_streak >= condition.get('value', 0)

        elif ctype == 'time_of_day':
            if utc_hour is not None:
                earned = condition.get('min_hour', 0) <= utc_hour <= condition.get('max_hour', 23)

        elif ctype == 'set_size':
            counter_val = badge_progress.get(condition.get('counter', ''), [])
            earned = len(counter_val) >= condition.get('value', 0)

        elif ctype == 'text_length':
            earned = comment_length > condition.get('value', 0)

        if earned:
            new_badges.append({
                'badge_id': badge_id,
                'name': badge['name'],
                'icon': badge['icon'],
            })

    return new_badges

def build_badge_progress_update(action_type, **kwargs):
    """
    Build DynamoDB UpdateExpression fragments for badge progress updates.

    Args:
        action_type: one of 'love_vote', 'needs_update_vote', 'comment', 'bookmark',
                     'proposal_submitted', 'proposal_approved', 'chatbot_question', 'label_read'
        **kwargs: additional context (e.g., bookmarks_count=N for bookmark, label='Technical How-To' for label_read)

    Returns:
        dict with keys:
        - 'update_parts': list of SET/ADD expression fragments
        - 'expr_values': dict of ExpressionAttributeValues
        - 'expr_names': dict of ExpressionAttributeNames
    """
    update_parts = []
    expr_values = {}
    expr_names = {'#bp': 'badge_progress'}

    counter_map = {
        'love_vote': 'love_votes_given',
        'needs_update_vote': 'needs_update_votes_given',
        'comment': 'comments_made',
        'proposal_submitted': 'proposals_submitted',
        'proposal_approved': 'proposals_approved',
        'chatbot_question': 'chatbot_questions',
    }

    if action_type in counter_map:
        counter_name = counter_map[action_type]
        expr_names['#counter'] = counter_name
        expr_values[':zero'] = 0
        expr_values[':one'] = 1
        update_parts.append('SET #bp.#counter = if_not_exists(#bp.#counter, :zero) + :one')

    elif action_type == 'bookmark':
        bookmarks_count = kwargs.get('bookmarks_count', 0)
        expr_names['#bh'] = 'bookmarks_held'
        expr_values[':bookmarks_count'] = bookmarks_count
        update_parts.append('SET #bp.#bh = :bookmarks_count')

    elif action_type == 'label_read':
        label = kwargs.get('label', '')
        if label:
            expr_names['#dlr'] = 'distinct_labels_read'
            expr_values[':label_set'] = {label}
            update_parts.append('ADD #bp.#dlr :label_set')

    return {
        'update_parts': update_parts,
        'expr_values': expr_values,
        'expr_names': expr_names,
    }

def evaluate_and_award_badges(user_id, action_type, visit_streak=0, utc_hour=None, comment_length=0, created_at=None, **kwargs):
    """
    Load user's badge state, update progress, evaluate badges, persist new awards.
    Returns list of newly earned badge dicts, or empty list on failure.
    """
    try:
        # 1. Get current user profile
        response = profiles_table.get_item(Key={'user_id': user_id})
        profile = response.get('Item')
        if not profile:
            print(f"Badge evaluation: no profile found for user {user_id}")
            return []

        badge_progress = profile.get('badge_progress', {})
        existing_badges = profile.get('badges', [])
        existing_badge_ids = {b['badge_id'] for b in existing_badges if isinstance(b, dict) and 'badge_id' in b}

        # 2. Build and apply badge progress update
        progress_update = build_badge_progress_update(action_type, **kwargs)
        if progress_update['update_parts']:
            set_clauses = [p[4:] for p in progress_update['update_parts'] if p.startswith('SET ')]
            add_clauses = [p[4:] for p in progress_update['update_parts'] if p.startswith('ADD ')]

            full_expr = ''
            if set_clauses:
                full_expr = 'SET ' + ', '.join(set_clauses)
            if add_clauses:
                full_expr += (' ' if full_expr else '') + 'ADD ' + ', '.join(add_clauses)

            profiles_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression=full_expr,
                ExpressionAttributeValues=progress_update['expr_values'],
                ExpressionAttributeNames=progress_update['expr_names'],
            )

            # Re-read the updated badge_progress
            response = profiles_table.get_item(Key={'user_id': user_id})
            profile = response.get('Item', {})
            badge_progress = profile.get('badge_progress', {})

        # 3. Evaluate badges
        if not created_at:
            created_at = profile.get('created_at')

        new_badges = evaluate_badges(
            badge_progress, existing_badge_ids,
            visit_streak=visit_streak,
            utc_hour=utc_hour,
            comment_length=comment_length,
            created_at=created_at,
        )

        # 4. Persist newly earned badges
        if new_badges:
            now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            badge_records = [
                {'badge_id': b['badge_id'], 'earned_at': now}
                for b in new_badges
            ]
            profiles_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='SET badges = list_append(if_not_exists(badges, :empty_list), :new_badges)',
                ExpressionAttributeValues={
                    ':new_badges': badge_records,
                    ':empty_list': [],
                },
            )

        return new_badges

    except Exception as e:
        print(f"Badge evaluation error for user {user_id}, action {action_type}: {str(e)}")
        return []


def backfill_badge_progress(user_id, profile):
    """
    One-time computation of badge_progress from existing data.
    Sets badges_backfilled = True when complete.
    Returns (badge_progress, new_badges).

    Pragmatic approach: backfill what we can cheaply from profile data
    (bookmarks, visit_streak, created_at). Vote/comment/proposal counts
    would require expensive full-table scans, so we set those to 0 and
    let future actions increment them naturally.
    """
    try:
        badge_progress = profile.get('badge_progress', {})
        existing_badges = profile.get('badges', [])
        existing_badge_ids = {b['badge_id'] for b in existing_badges if isinstance(b, dict) and 'badge_id' in b}

        # Backfill what we can from profile data
        bookmarks = profile.get('bookmarks', [])
        badge_progress['bookmarks_held'] = len(bookmarks)

        visit_streak = int(profile.get('visit_streak', 0))
        created_at = profile.get('created_at', '')

        # Evaluate badges with current progress
        new_badges = evaluate_badges(
            badge_progress, existing_badge_ids,
            visit_streak=visit_streak,
            created_at=created_at,
        )

        # Auto-award First Steps
        if 'first_steps' not in existing_badge_ids:
            first_steps_already_new = any(b['badge_id'] == 'first_steps' for b in new_badges)
            if not first_steps_already_new:
                new_badges.append({'badge_id': 'first_steps', 'name': 'First Steps', 'icon': '👣'})

        # Check OG badge
        if 'og' not in existing_badge_ids:
            og_already_new = any(b['badge_id'] == 'og' for b in new_badges)
            if not og_already_new and created_at:
                try:
                    launch = datetime.strptime(SITE_LAUNCH_DATE, '%Y-%m-%d')
                    user_created = datetime.fromisoformat(created_at.replace('Z', '+00:00')).replace(tzinfo=None)
                    if user_created <= launch + timedelta(days=30):
                        new_badges.append({'badge_id': 'og', 'name': 'OG', 'icon': '👑'})
                except Exception:
                    pass

        # Persist badge_progress, badges, and badges_backfilled flag
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        badge_records = [
            {'badge_id': b['badge_id'], 'earned_at': now}
            for b in new_badges
        ]
        all_badges = existing_badges + badge_records

        profiles_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET badge_progress = :bp, badges = :badges, badges_backfilled = :bf',
            ExpressionAttributeValues={
                ':bp': badge_progress,
                ':badges': all_badges,
                ':bf': True,
            },
        )

        return badge_progress, new_badges

    except Exception as e:
        print(f"Backfill error for user {user_id}: {str(e)}")
        return {}, []


class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert DynamoDB Decimal types and sets to JSON"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, set):
            return list(obj)
        return super(DecimalEncoder, self).default(obj)


def cors_headers():
    """Return CORS headers for API responses"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

def compute_streak_update(last_visit_date, visit_streak, longest_streak, total_visits, today):
    """Pure function to compute updated streak fields.

    Args:
        last_visit_date: string (YYYY-MM-DD) or empty string/None for first visit
        visit_streak: int, current streak count
        longest_streak: int, all-time high
        total_visits: int, lifetime count
        today: string (YYYY-MM-DD), current UTC date

    Returns:
        dict with: last_visit_date, visit_streak, longest_streak, total_visits
    """
    new_total = total_visits + 1

    if not last_visit_date:
        # First visit
        new_streak = 1
    else:
        today_date = datetime.strptime(today, '%Y-%m-%d').date()
        last_date = datetime.strptime(last_visit_date, '%Y-%m-%d').date()
        diff = (today_date - last_date).days

        if diff == 0:
            # Same day — streak unchanged
            new_streak = visit_streak
        elif diff == 1:
            # Yesterday — continue streak
            new_streak = visit_streak + 1
        else:
            # Gap — reset
            new_streak = 1

    new_longest = max(longest_streak, new_streak)

    return {
        'last_visit_date': today,
        'visit_streak': new_streak,
        'longest_streak': new_longest,
        'total_visits': new_total,
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


# ============================================================================
# INNOVATION HUB ENDPOINTS
# ============================================================================

def sanitize_mermaid(code):
    """Clean up AI-generated Mermaid code to fix common syntax issues."""
    if not code:
        return code
    lines = code.strip().split('\n')
    cleaned = []
    for line in lines:
        # Remove any HTML entities
        line = line.replace('&amp;', 'and').replace('&lt;', '').replace('&gt;', '').replace('&quot;', '')
        # Replace problematic characters in labels
        line = line.replace('#', '').replace('&', 'and')
        cleaned.append(line)
    result = '\n'.join(cleaned)
    # Ensure it starts with a valid graph declaration
    first_line = result.strip().split('\n')[0].strip().lower()
    if not first_line.startswith(('graph ', 'flowchart ', 'sequencediagram', 'classDiagram'.lower(), 'statediagram')):
        result = 'graph TD\n' + result
    return result


@require_auth
def create_innovation(event, body):
    """Create a new innovation submission with moderation."""
    user_id = event['user']['sub']

    # Validate required fields
    title = body.get('title', '')
    problem_statement = body.get('problem_statement', '')
    architecture_description = body.get('architecture_description', '')
    aws_services = body.get('aws_services', [])
    complexity_level = body.get('complexity_level', '')
    code_snippets = body.get('code_snippets', [])

    if not title or len(title) < 10 or len(title) > 200:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Title must be between 10 and 200 characters'})
        }

    if not problem_statement or len(problem_statement) < 20 or len(problem_statement) > 2000:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Problem statement must be between 20 and 2000 characters'})
        }

    if not architecture_description or len(architecture_description) < 50 or len(architecture_description) > 5000:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Architecture description must be between 50 and 5000 characters'})
        }

    if not aws_services or not isinstance(aws_services, list) or len(aws_services) == 0:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'At least one AWS service is required'})
        }

    if complexity_level not in ('Beginner', 'Intermediate', 'Advanced'):
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Invalid complexity_level. Must be Beginner, Intermediate, or Advanced'})
        }

    try:
        # Get user display name
        display_name = 'User'
        try:
            profile_response = profiles_table.get_item(Key={'user_id': user_id})
            profile = profile_response.get('Item')
            if profile:
                display_name = profile.get('display_name', 'User')
        except Exception as e:
            print(f"Error fetching profile for display name: {e}")

        # Moderate content
        moderation_text = f"{title} {problem_statement} {architecture_description}"
        try:
            moderation_result = moderate_comment(moderation_text, 'Innovation submission')
            print(f"Innovation moderation result: {json.dumps(moderation_result)}")
        except Exception as e:
            print(f"Moderation error: {e}")
            moderation_result = {
                'status': 'approved',
                'reason': None,
                'confidence': 0.0,
                'timestamp': datetime.utcnow().isoformat()
            }

        status = 'published' if moderation_result['status'] == 'approved' else 'pending_review'
        now = get_timestamp()

        # Generate Mermaid architecture diagram using Bedrock
        architecture_diagram = ''
        try:
            diagram_prompt = f"""Based on this architecture description, generate a Mermaid.js flowchart diagram.
Return ONLY valid Mermaid code. No explanation, no markdown fences, no comments.

STRICT RULES for valid Mermaid syntax:
1. Start with exactly: graph TD
2. Node IDs must be simple alphanumeric (e.g., A, B, userReq, lambdaFn) — NO spaces, NO special characters in IDs
3. Node labels MUST be in square brackets: A[My Label] — NEVER use parentheses () or curly braces {{}} for labels
4. Arrow syntax: A --> B or A -->|label| B
5. Subgraph titles must be plain text: subgraph Title
6. NEVER use quotes around labels — use square brackets only
7. NEVER use special characters like &, <, >, or # inside labels
8. Keep labels short (under 30 chars)
9. End subgraphs with: end

Example of VALID syntax:
graph TD
    A[User Request] --> B[API Gateway]
    B --> C[Lambda Function]
    subgraph Storage
        D[DynamoDB]
        E[S3 Bucket]
    end
    C --> D
    C --> E

Architecture description:
{architecture_description}

AWS Services involved: {', '.join(aws_services)}"""

            diagram_response = bedrock_runtime.invoke_model(
                modelId='anthropic.claude-3-haiku-20240307-v1:0',
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 1000,
                    'messages': [{'role': 'user', 'content': diagram_prompt}]
                }),
                contentType='application/json'
            )
            diagram_body = json.loads(diagram_response['body'].read())
            architecture_diagram = diagram_body['content'][0]['text'].strip()
            # Clean up any markdown fences if present
            if architecture_diagram.startswith('```'):
                lines = architecture_diagram.split('\n')
                architecture_diagram = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
            architecture_diagram = sanitize_mermaid(architecture_diagram)
            print(f"Generated Mermaid diagram ({len(architecture_diagram)} chars)")
        except Exception as e:
            print(f"Diagram generation failed (non-blocking): {e}")
            architecture_diagram = ''

        innovation = {
            'innovation_id': str(uuid.uuid4()),
            'user_id': user_id,
            'display_name': display_name,
            'title': title,
            'problem_statement': problem_statement,
            'architecture_description': architecture_description,
            'architecture_diagram': architecture_diagram,
            'code_snippets': code_snippets,
            'aws_services': aws_services,
            'complexity_level': complexity_level,
            'status': status,
            'upvotes': 0,
            'downvotes': 0,
            'upvoters': [],
            'downvoters': [],
            'comments': [],
            'comment_count': 0,
            'created_at': now,
            'updated_at': now
        }

        innovations_table.put_item(Item=innovation)

        return {
            'statusCode': 201,
            'headers': cors_headers(),
            'body': json.dumps(innovation, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error in create_innovation: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }


def get_innovations(query_params):
    """Get all published innovations with optional filtering and sorting."""
    try:
        response = innovations_table.scan(
            FilterExpression=Attr('status').eq('published')
        )
        innovations = response.get('Items', [])

        # Handle pagination for large datasets
        while 'LastEvaluatedKey' in response:
            response = innovations_table.scan(
                FilterExpression=Attr('status').eq('published'),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            innovations.extend(response.get('Items', []))

        # Filter by AWS service
        service_filter = query_params.get('service', '')
        if service_filter:
            innovations = [i for i in innovations if service_filter in i.get('aws_services', [])]

        # Filter by complexity
        complexity_filter = query_params.get('complexity', '')
        if complexity_filter:
            innovations = [i for i in innovations if i.get('complexity_level') == complexity_filter]

        # Text search (case-insensitive on title, problem_statement, aws_services)
        search_query = query_params.get('search', '')
        if search_query:
            search_lower = search_query.lower()
            filtered = []
            for i in innovations:
                title = i.get('title', '').lower()
                problem = i.get('problem_statement', '').lower()
                services = ' '.join(i.get('aws_services', [])).lower()
                if search_lower in title or search_lower in problem or search_lower in services:
                    filtered.append(i)
            innovations = filtered

        # Sort
        sort_by = query_params.get('sort_by', 'newest')
        if sort_by == 'votes':
            innovations.sort(key=lambda x: float(x.get('upvotes', 0)) - float(x.get('downvotes', 0)), reverse=True)
        elif sort_by == 'oldest':
            innovations.sort(key=lambda x: x.get('created_at', ''))
        else:  # newest (default)
            innovations.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'innovations': innovations}, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error in get_innovations: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }


@require_auth
def vote_on_innovation(event, body):
    """Vote on an innovation (upvote or downvote)."""
    innovation_id = body.get('innovation_id')
    if not innovation_id:
        # Try extracting from path
        path = event.get('path', '')
        parts = path.split('/')
        if len(parts) >= 3:
            innovation_id = parts[2]

    if not innovation_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'innovation_id is required'})
        }

    vote_type = body.get('vote_type')
    if vote_type not in ('upvote', 'downvote'):
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Invalid vote_type. Must be upvote or downvote'})
        }

    user_id = event['user']['sub']

    try:
        response = innovations_table.get_item(Key={'innovation_id': innovation_id})
        item = response.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Innovation not found'})
            }

        upvoters = item.get('upvoters', [])
        downvoters = item.get('downvoters', [])

        if user_id in upvoters or user_id in downvoters:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'You have already voted on this innovation'})
            }

        if vote_type == 'upvote':
            innovations_table.update_item(
                Key={'innovation_id': innovation_id},
                UpdateExpression='SET upvotes = if_not_exists(upvotes, :zero) + :inc, upvoters = list_append(if_not_exists(upvoters, :empty_list), :voter)',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':zero': 0,
                    ':voter': [user_id],
                    ':empty_list': []
                }
            )
        else:
            innovations_table.update_item(
                Key={'innovation_id': innovation_id},
                UpdateExpression='SET downvotes = if_not_exists(downvotes, :zero) + :inc, downvoters = list_append(if_not_exists(downvoters, :empty_list), :voter)',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':zero': 0,
                    ':voter': [user_id],
                    ':empty_list': []
                }
            )

        # Return updated innovation
        response = innovations_table.get_item(Key={'innovation_id': innovation_id})
        updated_item = response.get('Item')

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Vote recorded successfully',
                'innovation': updated_item
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error in vote_on_innovation: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }


@require_auth
def add_innovation_comment(event, body):
    """Add a comment to an innovation with moderation."""
    innovation_id = body.get('innovation_id')
    if not innovation_id:
        path = event.get('path', '')
        parts = path.split('/')
        if len(parts) >= 3:
            innovation_id = parts[2]

    if not innovation_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'innovation_id is required'})
        }

    text = body.get('text', '').strip()
    if not text:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Comment text is required'})
        }

    user_id = event['user']['sub']

    try:
        # Get innovation for moderation context
        inn_response = innovations_table.get_item(Key={'innovation_id': innovation_id})
        innovation = inn_response.get('Item')

        if not innovation:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Innovation not found'})
            }

        post_context = {
            'post_id': innovation_id,
            'title': innovation.get('title', ''),
            'tags': ', '.join(innovation.get('aws_services', []))
        }

        # Moderate comment
        try:
            moderation_result = moderate_comment(text, post_context)
            print(f"Innovation comment moderation result: {json.dumps(moderation_result)}")
        except Exception as e:
            print(f"Moderation error: {e}")
            moderation_result = {
                'status': 'approved',
                'reason': None,
                'confidence': 0.0,
                'timestamp': datetime.utcnow().isoformat()
            }

        # Get user display name
        display_name = 'User'
        try:
            profile_response = profiles_table.get_item(Key={'user_id': user_id})
            profile = profile_response.get('Item')
            if profile:
                display_name = profile.get('display_name', 'User')
        except Exception as e:
            print(f"Error fetching profile for display name: {e}")

        comment = {
            'comment_id': str(uuid.uuid4()),
            'user_id': user_id,
            'display_name': display_name,
            'text': text,
            'timestamp': datetime.utcnow().isoformat(),
            'moderation_status': moderation_result['status'],
            'moderation_confidence': Decimal(str(moderation_result['confidence']))
        }

        if moderation_result['status'] == 'pending_review' and moderation_result.get('reason'):
            comment['moderation_reason'] = moderation_result['reason']

        innovations_table.update_item(
            Key={'innovation_id': innovation_id},
            UpdateExpression='SET comments = list_append(if_not_exists(comments, :empty_list), :comment), comment_count = if_not_exists(comment_count, :zero) + :inc, updated_at = :now',
            ExpressionAttributeValues={
                ':comment': [comment],
                ':empty_list': [],
                ':zero': 0,
                ':inc': 1,
                ':now': get_timestamp()
            }
        )

        response = innovations_table.get_item(Key={'innovation_id': innovation_id})
        updated_item = response.get('Item')

        return {
            'statusCode': 201,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Comment added successfully',
                'comment': comment,
                'innovation': updated_item
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error in add_innovation_comment: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }


def get_innovation_comments(event, innovation_id):
    """Get all comments for an innovation, sorted by timestamp ascending."""
    if not innovation_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Innovation ID is required'})
        }

    try:
        response = innovations_table.get_item(Key={'innovation_id': innovation_id})
        item = response.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Innovation not found'})
            }

        comments = item.get('comments', [])

        # Sort by timestamp ascending (oldest first)
        comments.sort(key=lambda c: c.get('timestamp', ''))

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'comments': comments,
                'count': len(comments)
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error in get_innovation_comments: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }


@require_auth
def delete_innovation_comment(event, body):
    """Delete a comment from an innovation. Only the comment owner can delete."""
    innovation_id = body.get('innovation_id')
    comment_id = body.get('comment_id')
    if not innovation_id or not comment_id:
        return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': 'innovation_id and comment_id are required'})}

    user_id = event['user']['sub']

    try:
        response = innovations_table.get_item(Key={'innovation_id': innovation_id})
        item = response.get('Item')
        if not item:
            return {'statusCode': 404, 'headers': cors_headers(), 'body': json.dumps({'error': 'Innovation not found'})}

        comments = item.get('comments', [])
        new_comments = []
        found = False
        for c in comments:
            if c.get('comment_id') == comment_id:
                if c.get('user_id') != user_id:
                    return {'statusCode': 403, 'headers': cors_headers(), 'body': json.dumps({'error': 'You can only delete your own comments'})}
                found = True
            else:
                new_comments.append(c)

        if not found:
            return {'statusCode': 404, 'headers': cors_headers(), 'body': json.dumps({'error': 'Comment not found'})}

        innovations_table.update_item(
            Key={'innovation_id': innovation_id},
            UpdateExpression='SET comments = :comments, comment_count = :count, updated_at = :now',
            ExpressionAttributeValues={':comments': new_comments, ':count': len(new_comments), ':now': get_timestamp()}
        )

        return {'statusCode': 200, 'headers': cors_headers(), 'body': json.dumps({'message': 'Comment deleted'})}

    except Exception as e:
        print(f"Error in delete_innovation_comment: {str(e)}")
        return {'statusCode': 500, 'headers': cors_headers(), 'body': json.dumps({'error': 'Internal server error'})}


@require_auth
def toggle_innovation_bookmark(event, body):
    """Toggle bookmark on an innovation (add or remove)."""
    innovation_id = body.get('innovation_id')
    if not innovation_id:
        path = event.get('path', '')
        parts = path.split('/')
        if len(parts) >= 3:
            innovation_id = parts[2]

    if not innovation_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Innovation ID is required'})
        }

    user_id = event['user']['sub']

    try:
        response = profiles_table.get_item(Key={'user_id': user_id})
        profile = response.get('Item')

        if not profile:
            profile = {
                'user_id': user_id,
                'email': event['user'].get('email', ''),
                'display_name': event['user'].get('email', '').split('@')[0],
                'bookmarks': [],
                'created_at': get_timestamp(),
                'updated_at': get_timestamp()
            }

        bookmarks = profile.get('bookmarks', [])

        if innovation_id in bookmarks:
            bookmarks.remove(innovation_id)
            action = 'removed'
        else:
            bookmarks.append(innovation_id)
            action = 'added'

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
                'bookmarked': innovation_id in bookmarks,
                'bookmark_count': len(bookmarks)
            })
        }

    except Exception as e:
        print(f"Error in toggle_innovation_bookmark: {str(e)}")
        raise


@require_auth
def update_innovation(event, body):
    """Update an innovation. Only the owner can edit. Regenerates diagram if architecture changes."""
    innovation_id = body.get('innovation_id')
    if not innovation_id:
        path = event.get('path', '')
        parts = path.split('/')
        if len(parts) >= 3:
            innovation_id = parts[2]

    if not innovation_id:
        return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': 'Innovation ID is required'})}

    user_id = event['user']['sub']

    try:
        response = innovations_table.get_item(Key={'innovation_id': innovation_id})
        item = response.get('Item')
        if not item:
            return {'statusCode': 404, 'headers': cors_headers(), 'body': json.dumps({'error': 'Innovation not found'})}
        if item.get('user_id') != user_id:
            return {'statusCode': 403, 'headers': cors_headers(), 'body': json.dumps({'error': 'You can only edit your own innovations'})}

        # Build update expression from provided fields
        update_parts = ['updated_at = :now']
        expr_values = {':now': get_timestamp()}
        arch_changed = False

        for field, key, min_len, max_len in [
            ('title', ':title', 10, 200),
            ('problem_statement', ':ps', 20, 2000),
            ('architecture_description', ':ad', 50, 5000)
        ]:
            val = body.get(field)
            if val is not None:
                val = val.strip()
                if len(val) < min_len or len(val) > max_len:
                    return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': f'{field} must be {min_len}-{max_len} characters'})}
                update_parts.append(f'{field} = {key}')
                expr_values[key] = val
                if field == 'architecture_description':
                    arch_changed = True

        if 'aws_services' in body:
            services = body['aws_services']
            if not services or not isinstance(services, list):
                return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': 'At least one AWS service is required'})}
            update_parts.append('aws_services = :svc')
            expr_values[':svc'] = services

        if 'complexity_level' in body:
            cl = body['complexity_level']
            if cl not in ('Beginner', 'Intermediate', 'Advanced'):
                return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': 'Invalid complexity_level'})}
            update_parts.append('complexity_level = :cl')
            expr_values[':cl'] = cl

        if 'code_snippets' in body:
            update_parts.append('code_snippets = :cs')
            expr_values[':cs'] = body['code_snippets']

        # Regenerate diagram if architecture description changed OR explicitly requested
        regenerate_diagram = body.get('regenerate_diagram', False)
        if arch_changed or regenerate_diagram:
            arch_desc = body.get('architecture_description', item.get('architecture_description', ''))
            services = body.get('aws_services', item.get('aws_services', []))
            try:
                diagram_prompt = f"""Based on this architecture description, generate a Mermaid.js flowchart diagram.
Return ONLY valid Mermaid code. No explanation, no markdown fences, no comments.

STRICT RULES for valid Mermaid syntax:
1. Start with exactly: graph TD
2. Node IDs must be simple alphanumeric (e.g., A, B, userReq, lambdaFn) — NO spaces, NO special characters in IDs
3. Node labels MUST be in square brackets: A[My Label] — NEVER use parentheses () or curly braces {{}} for labels
4. Arrow syntax: A --> B or A -->|label| B
5. Subgraph titles must be plain text: subgraph Title
6. NEVER use quotes around labels — use square brackets only
7. NEVER use special characters like &, <, >, or # inside labels
8. Keep labels short (under 30 chars)
9. End subgraphs with: end

Example of VALID syntax:
graph TD
    A[User Request] --> B[API Gateway]
    B --> C[Lambda Function]
    subgraph Storage
        D[DynamoDB]
        E[S3 Bucket]
    end
    C --> D
    C --> E

Architecture description:
{arch_desc}

AWS Services involved: {', '.join(services)}"""
                diagram_response = bedrock_runtime.invoke_model(
                    modelId='anthropic.claude-3-haiku-20240307-v1:0',
                    body=json.dumps({
                        'anthropic_version': 'bedrock-2023-05-31',
                        'max_tokens': 1000,
                        'messages': [{'role': 'user', 'content': diagram_prompt}]
                    }),
                    contentType='application/json'
                )
                diagram_body = json.loads(diagram_response['body'].read())
                diagram = diagram_body['content'][0]['text'].strip()
                if diagram.startswith('```'):
                    lines = diagram.split('\n')
                    diagram = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
                diagram = sanitize_mermaid(diagram)
                update_parts.append('architecture_diagram = :diag')
                expr_values[':diag'] = diagram
            except Exception as e:
                print(f"Diagram regeneration failed: {e}")

        innovations_table.update_item(
            Key={'innovation_id': innovation_id},
            UpdateExpression='SET ' + ', '.join(update_parts),
            ExpressionAttributeValues=expr_values
        )

        response = innovations_table.get_item(Key={'innovation_id': innovation_id})
        updated = response.get('Item')

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'message': 'Innovation updated', 'innovation': updated}, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error in update_innovation: {str(e)}")
        return {'statusCode': 500, 'headers': cors_headers(), 'body': json.dumps({'error': 'Internal server error', 'message': str(e)})}


@require_auth
def delete_innovation(event, body):
    """Delete an innovation. Only the owner can delete their own innovation."""
    innovation_id = body.get('innovation_id')
    if not innovation_id:
        path = event.get('path', '')
        parts = path.split('/')
        if len(parts) >= 3:
            innovation_id = parts[2]

    if not innovation_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Innovation ID is required'})
        }

    user_id = event['user']['sub']

    try:
        response = innovations_table.get_item(Key={'innovation_id': innovation_id})
        item = response.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Innovation not found'})
            }

        if item.get('user_id') != user_id:
            return {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Forbidden', 'message': 'You can only delete your own innovations'})
            }

        innovations_table.delete_item(Key={'innovation_id': innovation_id})

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'message': 'Innovation deleted'})
        }

    except Exception as e:
        print(f"Error in delete_innovation: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }


@require_auth
def promote_innovation(event, body):
    """Promote an innovation to a proposal (article or feature).
    
    Two modes:
    - refine_only=true: Returns AI-refined content for review, no records created
    - refine_only=false (default): Validates, creates proposal, updates innovation
    """
    user_id = event['user']['sub']

    # Extract innovation_id from path
    path = event.get('path', '')
    parts = path.split('/')
    innovation_id = parts[2] if len(parts) >= 4 else body.get('innovation_id')

    if not innovation_id:
        return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': 'innovation_id is required'})}

    promotion_path = body.get('promotion_path', '')
    if promotion_path not in ('article', 'feature'):
        return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': "promotion_path must be 'article' or 'feature'"})}

    refine_only = body.get('refine_only', False)

    try:
        # Fetch innovation
        response = innovations_table.get_item(Key={'innovation_id': innovation_id})
        innovation = response.get('Item')

        if not innovation:
            return {'statusCode': 404, 'headers': cors_headers(), 'body': json.dumps({'error': 'Innovation not found'})}

        if innovation.get('user_id') != user_id:
            return {'statusCode': 403, 'headers': cors_headers(), 'body': json.dumps({'error': 'Only the innovation author can promote'})}

        if innovation.get('status') != 'published':
            return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': 'Only published innovations can be promoted'})}

        if innovation.get('promoted_to_proposal_id'):
            return {'statusCode': 409, 'headers': cors_headers(), 'body': json.dumps({'error': 'Innovation has already been promoted to a proposal'})}

        # Refine mode — return AI content for review
        if refine_only:
            if promotion_path == 'article':
                refined = refine_innovation_to_article(innovation)
            else:
                refined = refine_innovation_to_feature(innovation)

            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps({'refined_content': refined, 'innovation': innovation}, cls=DecimalEncoder)
            }

        # Submit mode — create proposal
        # Get display name
        display_name = 'User'
        try:
            profile_resp = profiles_table.get_item(Key={'user_id': user_id})
            profile = profile_resp.get('Item')
            if profile:
                display_name = profile.get('display_name', 'User')
        except Exception as e:
            print(f"Error fetching profile for promotion: {e}")

        now = get_timestamp()
        proposal_id = str(uuid.uuid4())

        if promotion_path == 'article':
            # Validate article fields
            title = body.get('title', '').strip()
            description = body.get('description', '').strip() or innovation.get('problem_statement', '')
            category = body.get('category', 'Technical How-To')

            if not title or len(title) < 10:
                return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': 'Title must be at least 10 characters'})}
            if not description or len(description) < 20:
                return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': 'Description must be at least 20 characters'})}

            # Convert Mermaid diagram to PNG for article proposals
            diagram_url = ''
            mermaid_code = innovation.get('architecture_diagram', '')
            if mermaid_code:
                diagram_url = convert_mermaid_to_png(mermaid_code, innovation_id)

            ai_content = body.get('ai_generated_content', {})

            proposal = {
                'proposal_id': proposal_id,
                'proposal_type': 'article',
                'user_id': user_id,
                'display_name': display_name,
                'title': title,
                'description': description,
                'category': category,
                'ai_generated_content': {
                    'outline': ai_content.get('outline', []),
                    'summary': ai_content.get('summary', ''),
                    'key_topics': ai_content.get('key_topics', []),
                    'target_audience': ai_content.get('target_audience', ''),
                    'estimated_length': ai_content.get('estimated_length', ''),
                    'writing_tips': ai_content.get('writing_tips', '')
                },
                'source_innovation_id': innovation_id,
                'architecture_diagram_url': diagram_url,
                'code_snippets': innovation.get('code_snippets', []),
                'status': 'pending',
                'votes': 0,
                'voters': [],
                'created_at': now,
                'updated_at': now
            }

        else:
            # Feature proposal
            service = body.get('service', '').strip()
            title = body.get('title', '').strip()
            description = body.get('description', '').strip()
            priority = body.get('priority', 'Nice to Have')
            use_case = body.get('use_case', '').strip()

            if not service:
                return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': 'Service is required'})}
            if not title or len(title) < 10:
                return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': 'Title must be at least 10 characters'})}
            if not description or len(description) < 30:
                return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': 'Description must be at least 30 characters'})}

            ai_content = body.get('ai_generated_content', {})

            # Convert Mermaid diagram to PNG for feature proposals too
            diagram_url = ''
            mermaid_code = innovation.get('architecture_diagram', '')
            if mermaid_code:
                diagram_url = convert_mermaid_to_png(mermaid_code, innovation_id)

            proposal = {
                'proposal_id': proposal_id,
                'proposal_type': 'feature',
                'user_id': user_id,
                'display_name': display_name,
                'service': service,
                'title': title,
                'description': description,
                'priority': priority,
                'use_case': use_case,
                'ai_generated_content': ai_content,
                'source_innovation_id': innovation_id,
                'architecture_diagram_url': diagram_url,
                'architecture_diagram': innovation.get('architecture_diagram', ''),
                'code_snippets': innovation.get('code_snippets', []),
                'status': 'pending',
                'votes': 0,
                'upvotes': 0,
                'downvotes': 0,
                'voters': [],
                'comments': [],
                'created_at': now,
                'updated_at': now
            }

        # Save proposal
        proposals_table.put_item(Item=proposal)

        # Update innovation with promotion link
        innovations_table.update_item(
            Key={'innovation_id': innovation_id},
            UpdateExpression='SET promoted_to_proposal_id = :pid, promoted_at = :pat',
            ExpressionAttributeValues={':pid': proposal_id, ':pat': now}
        )

        # Badge evaluation
        new_badges = []
        try:
            new_badges = evaluate_and_award_badges(user_id, 'proposal_submitted')
        except Exception as e:
            print(f"Badge evaluation error in promote_innovation: {e}")

        return {
            'statusCode': 201,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Innovation promoted successfully',
                'proposal': proposal,
                'innovation_id': innovation_id,
                'new_badges': new_badges
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error in promote_innovation: {str(e)}")
        return {'statusCode': 500, 'headers': cors_headers(), 'body': json.dumps({'error': 'Internal server error', 'message': str(e)})}


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
    - POST /heartbeat - Record user visit for streak tracking (requires auth)
    - GET /profile - Get current user's profile (requires auth)
    - PUT /profile - Update current user's profile (requires auth)
    - DELETE /profile - Delete current user's profile and all data (requires auth)
    - GET /profile/activity - Get current user's activity history (requires auth)
    - GET /profile/{id} - Get public profile of a user
    - POST /verify-email - Request Amazon email verification (requires auth)
    - GET /verify-email - Confirm email verification with token
    - GET /cart - Get current user's cart (requires auth)
    - POST /cart - Add post to cart (requires auth)
    - DELETE /cart/{post_id} - Remove post from cart (requires auth)
    - DELETE /cart - Clear all cart items (requires auth)
    - GET /kb-documents - List KB documents (requires auth)
    - GET /kb-document/{document_id} - Get KB document content (requires auth)
    - PUT /kb-document/{document_id} - Update KB document (requires auth)
    - GET /kb-ingestion-status/{job_id} - Get ingestion status (requires auth)
    - GET /kb-contributors - Get contributor leaderboard (requires auth)
    - GET /kb-my-contributions - Get user's contributions (requires auth)
    - POST /propose-article - Submit a new article proposal (requires auth)
    - GET /proposals - List proposals with optional status/user_id filters
    - POST /proposals/{proposal_id}/vote - Vote on a proposal (requires auth)
    """
    
    print(f"Event: {json.dumps(event)}")
    
    # Initialize tables with correct suffix for this request
    global table, profiles_table, TABLE_NAME, PROFILES_TABLE_NAME
    global kb_edit_history_table, kb_contributor_stats_table
    global whats_new_table, WHATS_NEW_TABLE_NAME
    global proposals_table, PROPOSALS_TABLE_NAME
    global chat_conversations_table, CHAT_CONVERSATIONS_TABLE_NAME
    global innovations_table, INNOVATIONS_TABLE_NAME
    table_suffix = get_table_suffix(event)
    TABLE_NAME = f'aws-blog-posts{table_suffix}'
    PROFILES_TABLE_NAME = f'euc-user-profiles{table_suffix}'
    WHATS_NEW_TABLE_NAME = f'aws-whats-new{table_suffix}'
    PROPOSALS_TABLE_NAME = f'proposed-articles{table_suffix}'
    table = dynamodb.Table(TABLE_NAME)
    profiles_table = dynamodb.Table(PROFILES_TABLE_NAME)
    whats_new_table = dynamodb.Table(WHATS_NEW_TABLE_NAME)
    proposals_table = dynamodb.Table(PROPOSALS_TABLE_NAME)
    
    # Initialize innovations table
    INNOVATIONS_TABLE_NAME = f'innovations{table_suffix}'
    innovations_table = dynamodb.Table(INNOVATIONS_TABLE_NAME)
    
    # Initialize chat conversations table
    CHAT_CONVERSATIONS_TABLE_NAME = f'chat-conversations{table_suffix}'
    chat_conversations_table = dynamodb.Table(CHAT_CONVERSATIONS_TABLE_NAME)
    
    # Initialize KB editor tables
    kb_edit_history_table = dynamodb.Table(f'kb-edit-history{table_suffix}')
    kb_contributor_stats_table = dynamodb.Table(f'kb-contributor-stats{table_suffix}')
    
    print(f"Using tables: {TABLE_NAME}, {PROFILES_TABLE_NAME}, {WHATS_NEW_TABLE_NAME}, {PROPOSALS_TABLE_NAME}, {INNOVATIONS_TABLE_NAME}")
    
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
            return trigger_crawler(event)  # Pass event for environment detection
        elif path == '/summaries' and http_method == 'POST':
            return trigger_summary_generation()
        elif path == '/heartbeat' and http_method == 'POST':
            return handle_heartbeat(event)
        elif path == '/verify-email' and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return request_email_verification(event, body)
        elif path == '/verify-email' and http_method == 'GET':
            return confirm_email_verification(event, query_parameters)
        elif path == '/bookmarks' and http_method == 'GET':
            return get_user_bookmarks(event)
        elif path == '/cart' and http_method == 'GET':
            return get_cart(event)
        elif path == '/cart' and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return add_to_cart(event, body)
        elif path == '/cart' and http_method == 'DELETE':
            return clear_cart(event)
        elif path.startswith('/cart/') and http_method == 'DELETE':
            post_id = path_parameters.get('post_id')
            return remove_from_cart(event, post_id)
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
            elif http_method == 'DELETE':
                body = json.loads(event.get('body', '{}'))
                return delete_comment(event, body)
        elif path.startswith('/posts/') and http_method == 'GET':
            post_id = path_parameters.get('id')
            return get_post_by_id(post_id)
        # What's New endpoints
        elif path == '/whats-new' and http_method == 'GET':
            return get_all_announcements(query_parameters)
        elif path == '/whats-new/stats' and http_method == 'GET':
            return get_announcement_stats()
        elif path.startswith('/whats-new/') and path.endswith('/vote') and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return vote_on_announcement(event, body)
        elif path.startswith('/whats-new/') and path.endswith('/bookmark') and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return toggle_announcement_bookmark(event, body)
        elif path.startswith('/whats-new/') and path.endswith('/comments'):
            announcement_id = path.split('/')[2]
            if http_method == 'GET':
                return get_announcement_comments(event, announcement_id)
            elif http_method == 'POST':
                body = json.loads(event.get('body', '{}'))
                return add_announcement_comment(event, body)
        elif path.startswith('/whats-new/') and http_method == 'GET':
            announcement_id = path_parameters.get('id') or path.split('/')[-1]
            return get_announcement_by_id(announcement_id)
        # KB Editor endpoints
        elif path == '/kb-documents' and http_method == 'GET':
            return handle_get_kb_documents(event)
        elif path.startswith('/kb-document/') and not path.endswith('/kb-document/') and http_method == 'GET':
            document_id = path.split('/')[-1]
            return handle_get_kb_document(event, document_id)
        elif path.startswith('/kb-document/') and not path.endswith('/kb-document/') and http_method == 'PUT':
            document_id = path.split('/')[-1]
            body = json.loads(event.get('body', '{}'))
            return handle_update_kb_document(event, document_id, body)
        elif path == '/kb-contributors' and http_method == 'GET':
            return handle_get_kb_contributors(event)
        elif path == '/kb-my-contributions' and http_method == 'GET':
            return handle_get_my_contributions(event)
        elif path.startswith('/kb-ingestion-status/') and http_method == 'GET':
            job_id = path.split('/')[-1]
            return handle_get_ingestion_status(event, job_id)
        # Proposal endpoints
        elif path == '/propose-article' and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return submit_proposal(event, body)
        elif path == '/propose-feature' and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return submit_feature_proposal(event, body)
        elif path == '/proposals' and http_method == 'GET':
            return list_proposals(query_parameters)
        elif path.startswith('/proposals/') and path.endswith('/vote') and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return vote_on_proposal(event, body)
        elif path.startswith('/proposals/') and path.endswith('/comments') and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return comment_on_proposal(event, body)
        elif path.startswith('/proposals/') and path.endswith('/comments') and http_method == 'GET':
            proposal_id = path.split('/')[2]
            response = proposals_table.get_item(Key={'proposal_id': proposal_id})
            item = response.get('Item')
            if not item:
                return {'statusCode': 404, 'headers': cors_headers(), 'body': json.dumps({'error': 'Proposal not found'})}
            return {'statusCode': 200, 'headers': cors_headers(), 'body': json.dumps({'comments': item.get('comments', [])}, cls=DecimalEncoder)}
        elif path.startswith('/proposals/') and not path.endswith('/vote') and not path.endswith('/comments') and http_method == 'DELETE':
            return delete_proposal(event, {})
        # Chat history endpoints
        elif path == '/chat/history' and http_method == 'GET':
            return get_chat_history(event)
        elif path.startswith('/chat/history/') and http_method == 'GET':
            conversation_id = path.split('/')[-1]
            return get_chat_conversation(event, conversation_id)
        elif path.startswith('/chat/history/') and http_method == 'DELETE':
            conversation_id = path.split('/')[-1]
            return delete_chat_conversation(event, conversation_id)
        # Pipeline status endpoint
        elif path == '/pipeline-status' and http_method == 'GET':
            return get_pipeline_status(event)
        # Innovation Hub endpoints
        elif path == '/innovations' and http_method == 'GET':
            return get_innovations(query_parameters)
        elif path == '/innovations' and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return create_innovation(event, body)
        elif path.startswith('/innovations/') and path.endswith('/vote') and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            innovation_id = path.split('/')[2]
            body['innovation_id'] = innovation_id
            return vote_on_innovation(event, body)
        elif path.startswith('/innovations/') and path.endswith('/comments') and http_method == 'GET':
            innovation_id = path.split('/')[2]
            return get_innovation_comments(event, innovation_id)
        elif path.startswith('/innovations/') and path.endswith('/comments') and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            innovation_id = path.split('/')[2]
            body['innovation_id'] = innovation_id
            return add_innovation_comment(event, body)
        elif path.startswith('/innovations/') and path.endswith('/comments') and http_method == 'DELETE':
            body = json.loads(event.get('body', '{}') or '{}')
            innovation_id = path.split('/')[2]
            body['innovation_id'] = innovation_id
            return delete_innovation_comment(event, body)
        elif path.startswith('/innovations/') and path.endswith('/bookmark') and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            innovation_id = path.split('/')[2]
            body['innovation_id'] = innovation_id
            return toggle_innovation_bookmark(event, body)
        elif path.startswith('/innovations/') and path.endswith('/promote') and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return promote_innovation(event, body)
        elif path.startswith('/innovations/') and http_method == 'PUT':
            body = json.loads(event.get('body', '{}') or '{}')
            innovation_id = path.split('/')[2]
            body['innovation_id'] = innovation_id
            return update_innovation(event, body)
        elif path.startswith('/innovations/') and http_method == 'DELETE':
            body = json.loads(event.get('body', '{}') or '{}')
            innovation_id = path.split('/')[2]
            body['innovation_id'] = innovation_id
            return delete_innovation(event, body)
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
        
        # Badge evaluation
        new_badges = []
        try:
            badge_action = 'love_vote' if vote_type == 'love' else 'needs_update_vote'
            new_badges = evaluate_and_award_badges(authenticated_user_id, badge_action)
            # Also track the post's label for Explorer badge
            post_label = updated_item.get('label', '') if updated_item else ''
            if post_label:
                evaluate_and_award_badges(authenticated_user_id, 'label_read', label=post_label)
        except Exception as e:
            print(f"Badge evaluation error in vote_on_post: {str(e)}")
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Vote recorded successfully',
                'post': updated_item,
                'new_badges': new_badges
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


@require_auth
def trigger_crawler(event):
    """
    Trigger both AWS blog and Builder.AWS crawlers
    Builder.AWS crawler uses Selenium to extract real author names
    
    Requires authentication - only authenticated users can trigger crawlers
    
    Args:
        event: API Gateway event (to extract stage variables for environment)
    """
    import boto3
    
    try:
        lambda_client = boto3.client('lambda')
        
        # Determine environment from stage variables
        # API Gateway staging stage has TABLE_SUFFIX=-staging
        environment = 'production'  # Default
        if event:
            stage_variables = event.get('stageVariables', {})
            table_suffix = stage_variables.get('TABLE_SUFFIX', '')
            if table_suffix == '-staging':
                environment = 'staging'
        
        print(f"Triggering crawler for environment: {environment}")
        
        # Invoke crawler for all sources (AWS Blog + Builder.AWS)
        # Pass environment so crawler knows which table to use
        # The crawler will automatically invoke ECS for Builder.AWS posts
        lambda_client.invoke(
            FunctionName='aws-blog-crawler',
            InvocationType='Event',
            Payload=json.dumps({
                'source': 'all',
                'environment': environment  # Pass environment to crawler
            })
        )
        
        return {
            'statusCode': 202,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Crawlers started successfully',
                'status': 'running',
                'environment': environment,
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
        
        # Badge evaluation
        new_badges = []
        try:
            new_badges = evaluate_and_award_badges(authenticated_user_id, 'comment', comment_length=len(text))
            # Also track the post's label for Explorer badge
            post_label = updated_item.get('label', '') if updated_item else ''
            if post_label:
                evaluate_and_award_badges(authenticated_user_id, 'label_read', label=post_label)
        except Exception as e:
            print(f"Badge evaluation error in add_comment: {str(e)}")
        
        return {
            'statusCode': 201,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Comment added successfully',
                'comment': comment,
                'post': updated_item,
                'new_badges': new_badges
            }, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error in add_comment: {str(e)}")
        raise


@require_auth
@require_admin
def delete_comment(event, body):
    """
    Delete a comment from a post
    Requires authentication and admin authorization (Amazon email verification)
    
    Body parameters:
    - post_id: ID of the post containing the comment
    - comment_id: ID of the comment to delete
    """
    post_id = body.get('post_id')
    comment_id = body.get('comment_id')
    
    if not post_id or not comment_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'post_id and comment_id are required'})
        }
    
    try:
        # Get the post
        response = table.get_item(Key={'post_id': post_id})
        post = response.get('Item')
        
        if not post:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Post not found'})
            }
        
        # Find and remove the comment
        comments = post.get('comments', [])
        original_count = len(comments)
        
        # Filter out the comment to delete
        updated_comments = [c for c in comments if c.get('comment_id') != comment_id]
        
        if len(updated_comments) == original_count:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Comment not found'})
            }
        
        # Update the post with filtered comments
        table.update_item(
            Key={'post_id': post_id},
            UpdateExpression='SET comments = :comments, comment_count = :count',
            ExpressionAttributeValues={
                ':comments': updated_comments,
                ':count': len(updated_comments)
            }
        )
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Comment deleted successfully',
                'deleted_comment_id': comment_id
            })
        }
    
    except Exception as e:
        print(f"Error in delete_comment: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to delete comment', 'message': str(e)})
        }


# ============================================================================
# User Profile Endpoints
# ============================================================================

# User profiles table - will be initialized per request
PROFILES_TABLE_NAME = None
profiles_table = None


@require_auth
def handle_heartbeat(event):
    """
    Record a user visit and update streak data.
    Requires authentication.

    Returns updated visit_streak, longest_streak, and total_visits.
    """
    user_id = event['user']['sub']
    today = datetime.utcnow().strftime('%Y-%m-%d')

    try:
        # Read current profile
        response = profiles_table.get_item(Key={'user_id': user_id})
        profile = response.get('Item', {})

        # Get current streak values, defaulting to 0/empty for missing fields
        last_visit_date = profile.get('last_visit_date', '') or ''
        visit_streak = int(profile.get('visit_streak', 0))
        longest_streak = int(profile.get('longest_streak', 0))
        total_visits = int(profile.get('total_visits', 0))

        # Compute updated streak values
        updated = compute_streak_update(
            last_visit_date, visit_streak, longest_streak, total_visits, today
        )

        # Write computed values back with a single UpdateItem
        profiles_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET last_visit_date = :lvd, visit_streak = :vs, longest_streak = :ls, total_visits = :tv',
            ExpressionAttributeValues={
                ':lvd': updated['last_visit_date'],
                ':vs': updated['visit_streak'],
                ':ls': updated['longest_streak'],
                ':tv': updated['total_visits'],
            }
        )

        # Badge evaluation (streak and time-of-day badges)
        new_badges = []
        try:
            utc_hour = datetime.utcnow().hour
            new_badges = evaluate_and_award_badges(
                user_id, 'heartbeat',
                visit_streak=updated['visit_streak'],
                utc_hour=utc_hour
            )
        except Exception as e:
            print(f"Badge evaluation error in handle_heartbeat: {str(e)}")

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'visit_streak': updated['visit_streak'],
                'longest_streak': updated['longest_streak'],
                'total_visits': updated['total_visits'],
                'new_badges': new_badges,
            })
        }

    except Exception as e:
        print(f"Error in handle_heartbeat: {str(e)}")
        raise


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
                'bookmarks': [],
                'cart': [],
                'created_at': get_timestamp(),
                'updated_at': get_timestamp(),
                'last_visit_date': '',
                'visit_streak': 0,
                'longest_streak': 0,
                'total_visits': 0,
                'stats': {
                    'votes_count': 0,
                    'comments_count': 0
                },
                'badges': [],
                'badge_progress': {},
                'badges_backfilled': True,
                'tour_completed': False,
            }
            
            # Save to DynamoDB
            profiles_table.put_item(Item=profile)

        # Initialize badges and badge_progress if they don't exist
        if 'badges' not in profile:
            profile['badges'] = []
        if 'badge_progress' not in profile:
            profile['badge_progress'] = {}
        if 'tour_completed' not in profile:
            profile['tour_completed'] = False

        # One-time backfill for existing users
        if not profile.get('badges_backfilled'):
            try:
                badge_progress, new_badges = backfill_badge_progress(user_id, profile)
                if badge_progress:
                    profile['badge_progress'] = badge_progress
                if new_badges:
                    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
                    badge_records = [{'badge_id': b['badge_id'], 'earned_at': now} for b in new_badges]
                    profile['badges'] = profile.get('badges', []) + badge_records
                profile['badges_backfilled'] = True
            except Exception as e:
                print(f"Backfill failed for user {user_id}: {str(e)}")
        
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
    
    # Handle tour_completed-only update (no profile fields required)
    tour_completed = body.get('tour_completed')
    if tour_completed is not None and len(body) == 1:
        if not isinstance(tour_completed, bool):
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'tour_completed must be a boolean'})
            }
        try:
            profiles_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='SET tour_completed = :tc, updated_at = :updated',
                ExpressionAttributeValues={
                    ':tc': tour_completed,
                    ':updated': get_timestamp()
                }
            )
            response = profiles_table.get_item(Key={'user_id': user_id})
            profile = response.get('Item')
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
            print(f"Error updating tour_completed: {str(e)}")
            raise
    
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
    
    # Handle optional tour_completed field
    tour_completed = body.get('tour_completed')
    if tour_completed is not None:
        if not isinstance(tour_completed, bool):
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'tour_completed must be a boolean'})
            }
    
    try:
        # Build update expression dynamically
        update_expr = 'SET display_name = :name, bio = :bio, credly_url = :credly, builder_id = :builder, updated_at = :updated'
        expr_values = {
            ':name': display_name,
            ':bio': bio,
            ':credly': credly_url,
            ':builder': builder_id,
            ':updated': get_timestamp()
        }
        
        if tour_completed is not None:
            update_expr += ', tour_completed = :tc'
            expr_values[':tc'] = tour_completed
        
        # Update profile
        profiles_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values
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
            'stats': calculate_user_stats(user_id),
            'visit_streak': int(profile.get('visit_streak', 0)),
            'longest_streak': int(profile.get('longest_streak', 0)),
            'badges': profile.get('badges', [])
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
                'cart': [],
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
        
        # Badge evaluation
        new_badges = []
        try:
            new_badges = evaluate_and_award_badges(user_id, 'bookmark', bookmarks_count=len(bookmarks))
        except Exception as e:
            print(f"Badge evaluation error in toggle_bookmark: {str(e)}")
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': f'Bookmark {action}',
                'bookmarked': post_id in bookmarks,
                'bookmark_count': len(bookmarks),
                'new_badges': new_badges
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


@require_auth
def get_cart(event):
    """
    Get current user's cart
    Requires authentication
    
    Returns:
    - cart: array of post_ids
    """
    user_id = event['user']['sub']
    
    try:
        # Get profile from DynamoDB
        response = profiles_table.get_item(Key={'user_id': user_id})
        profile = response.get('Item')
        
        # Return empty cart if profile doesn't exist or cart field missing
        cart = profile.get('cart', []) if profile else []
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'cart': cart})
        }
    
    except Exception as e:
        print(f"Error in get_cart: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to retrieve cart'})
        }


@require_auth
def add_to_cart(event, body):
    """
    Add a post to the user's cart
    Requires authentication
    
    Body parameters:
    - post_id: string (required)
    
    Returns:
    - cart: updated array of post_ids
    - added: boolean indicating if post was added
    """
    user_id = event['user']['sub']
    post_id = body.get('post_id', '').strip()
    
    # Validate post_id
    if not post_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'post_id is required'})
        }
    
    # Validate post_id format (alphanumeric, hyphens, underscores)
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', post_id):
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Invalid post_id format'})
        }
    
    try:
        # Check if post exists
        post_response = table.get_item(Key={'post_id': post_id})
        if 'Item' not in post_response:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Post not found'})
            }
        
        # Get current profile
        response = profiles_table.get_item(Key={'user_id': user_id})
        profile = response.get('Item')
        
        # Initialize cart if profile doesn't exist or cart field missing
        if not profile:
            profile = {
                'user_id': user_id,
                'email': event['user'].get('email', ''),
                'display_name': event['user'].get('email', '').split('@')[0],
                'bookmarks': [],
                'cart': [],
                'created_at': get_timestamp(),
                'updated_at': get_timestamp()
            }
        
        cart = profile.get('cart', [])
        
        # Check cart size limit (max 100 items)
        if len(cart) >= 100 and post_id not in cart:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Cart limit reached (max 100 items)'})
            }
        
        # Add post_id if not already in cart (prevent duplicates)
        added = False
        if post_id not in cart:
            cart.append(post_id)
            added = True
        
        # Update profile
        profiles_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET cart = :cart, updated_at = :updated',
            ExpressionAttributeValues={
                ':cart': cart,
                ':updated': get_timestamp()
            }
        )
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'cart': cart,
                'added': added,
                'message': 'Post added to cart' if added else 'Post already in cart'
            })
        }
    
    except Exception as e:
        print(f"Error in add_to_cart: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to add to cart'})
        }


@require_auth
def remove_from_cart(event, post_id):
    """
    Remove a specific post from the user's cart
    Requires authentication
    
    Path parameters:
    - post_id: string (required)
    
    Returns:
    - cart: updated array of post_ids
    - removed: boolean indicating if post was removed
    """
    user_id = event['user']['sub']
    
    if not post_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'post_id is required'})
        }
    
    try:
        # Get current profile
        response = profiles_table.get_item(Key={'user_id': user_id})
        profile = response.get('Item')
        
        if not profile:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Profile not found'})
            }
        
        cart = profile.get('cart', [])
        
        # Remove post_id if present
        removed = False
        if post_id in cart:
            cart.remove(post_id)
            removed = True
        
        # Update profile
        profiles_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET cart = :cart, updated_at = :updated',
            ExpressionAttributeValues={
                ':cart': cart,
                ':updated': get_timestamp()
            }
        )
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'cart': cart,
                'removed': removed,
                'message': 'Post removed from cart' if removed else 'Post not in cart'
            })
        }
    
    except Exception as e:
        print(f"Error in remove_from_cart: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to remove from cart'})
        }


@require_auth
def clear_cart(event):
    """
    Clear all items from the user's cart
    Requires authentication
    
    Returns:
    - cart: empty array
    - cleared: boolean (always true)
    """
    user_id = event['user']['sub']
    
    try:
        # Update profile with empty cart
        profiles_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET cart = :cart, updated_at = :updated',
            ExpressionAttributeValues={
                ':cart': [],
                ':updated': get_timestamp()
            }
        )
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'cart': [],
                'cleared': True,
                'message': 'Cart cleared successfully'
            })
        }
    
    except Exception as e:
        print(f"Error in clear_cart: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to clear cart'})
        }

@require_auth
def get_chat_history(event):
    """Get list of user's conversations sorted by updated_at descending"""
    user_id = event['user']['sub']

    try:
        response = chat_conversations_table.query(
            IndexName='user_id-updated_at-index',
            KeyConditionExpression=Key('user_id').eq(user_id),
            ScanIndexForward=False  # Descending order
        )

        conversations = []
        for item in response.get('Items', []):
            conversations.append({
                'conversation_id': item['conversation_id'],
                'title': item.get('title', ''),
                'updated_at': item.get('updated_at', ''),
                'message_count': len(item.get('messages', []))
            })

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'conversations': conversations}, cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"Error getting chat history: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }


@require_auth
def get_chat_conversation(event, conversation_id):
    """Get full conversation by ID with ownership verification"""
    user_id = event['user']['sub']

    try:
        response = chat_conversations_table.get_item(Key={'conversation_id': conversation_id})
        item = response.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Conversation not found'})
            }

        if item.get('user_id') != user_id:
            return {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Forbidden'})
            }

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'conversation_id': item['conversation_id'],
                'title': item.get('title', ''),
                'created_at': item.get('created_at', ''),
                'updated_at': item.get('updated_at', ''),
                'messages': item.get('messages', [])
            }, cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"Error getting conversation: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }


@require_auth
def delete_chat_conversation(event, conversation_id):
    """Delete a conversation with ownership verification"""
    user_id = event['user']['sub']

    try:
        response = chat_conversations_table.get_item(Key={'conversation_id': conversation_id})
        item = response.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Conversation not found'})
            }

        if item.get('user_id') != user_id:
            return {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Forbidden'})
            }

        chat_conversations_table.delete_item(Key={'conversation_id': conversation_id})

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'message': 'Conversation deleted successfully'})
        }
    except Exception as e:
        print(f"Error deleting conversation: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }


@require_auth
def get_pipeline_status(event):
    """Return queue depths for the processing pipeline."""
    try:
        table_suffix = get_table_suffix(event)
        is_staging = bool(table_suffix)
        
        queue_name = 'euc-processing-queue-staging' if is_staging else 'euc-processing-queue'
        dlq_name = 'euc-processing-dlq-staging' if is_staging else 'euc-processing-dlq'
        account_id = '031421429609'
        region = 'us-east-1'
        
        sqs_client = boto3.client('sqs', region_name=region)
        
        queue_url = f'https://sqs.{region}.amazonaws.com/{account_id}/{queue_name}'
        dlq_url = f'https://sqs.{region}.amazonaws.com/{account_id}/{dlq_name}'
        
        queue_attrs = sqs_client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
        )
        dlq_attrs = sqs_client.get_queue_attributes(
            QueueUrl=dlq_url,
            AttributeNames=['ApproximateNumberOfMessages']
        )
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'queue_depth': int(queue_attrs['Attributes'].get('ApproximateNumberOfMessages', 0)),
                'in_flight': int(queue_attrs['Attributes'].get('ApproximateNumberOfMessagesNotVisible', 0)),
                'dlq_depth': int(dlq_attrs['Attributes'].get('ApproximateNumberOfMessages', 0))
            })
        }
    except Exception as e:
        print(f"Error getting pipeline status: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to get pipeline status'})
        }


def get_timestamp():
    """Get current timestamp in ISO format"""
    from datetime import datetime
    return datetime.utcnow().isoformat()


# ============================================================================
# Amazon Email Verification Endpoints
# ============================================================================

@require_auth
def request_email_verification(event, body):
    """
    Request Amazon email verification
    Invokes the email verification Lambda to send verification email
    Requires authentication
    """
    user_id = event['user']['sub']
    amazon_email = body.get('amazon_email', '').strip().lower()
    
    try:
        # Validate email format
        if not amazon_email.endswith('@amazon.com'):
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Must be @amazon.com email'})
            }
        
        # Invoke email verification Lambda
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        # Prepare payload for verification Lambda
        verification_payload = {
            'path': '/verify-email/request',
            'httpMethod': 'POST',
            'headers': {
                'Authorization': event.get('headers', {}).get('Authorization', '')
            },
            'body': json.dumps({'amazon_email': amazon_email}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id
                    }
                }
            }
        }
        
        # Invoke verification Lambda asynchronously
        response = lambda_client.invoke(
            FunctionName='amazon-email-verification',
            InvocationType='RequestResponse',
            Payload=json.dumps(verification_payload)
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        # Return the response from verification Lambda
        return {
            'statusCode': response_payload.get('statusCode', 200),
            'headers': cors_headers(),
            'body': response_payload.get('body', '{}')
        }
    
    except Exception as e:
        print(f"Error in request_email_verification: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to send verification email', 'message': str(e)})
        }


def confirm_email_verification(event, query_params):
    """
    Confirm email verification with token
    Invokes the email verification Lambda to validate token and update profile
    Does not require authentication (token is the auth)
    """
    token = query_params.get('token', '')
    
    try:
        if not token:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Token is required'})
            }
        
        # Invoke email verification Lambda
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        # Prepare payload for verification Lambda
        verification_payload = {
            'path': '/verify-email/confirm',
            'httpMethod': 'GET',
            'queryStringParameters': {
                'token': token
            }
        }
        
        # Invoke verification Lambda synchronously
        response = lambda_client.invoke(
            FunctionName='amazon-email-verification',
            InvocationType='RequestResponse',
            Payload=json.dumps(verification_payload)
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        # Return the response from verification Lambda (includes redirect)
        return {
            'statusCode': response_payload.get('statusCode', 200),
            'headers': {
                **cors_headers(),
                **response_payload.get('headers', {})
            },
            'body': response_payload.get('body', '')
        }
    
    except Exception as e:
        print(f"Error in confirm_email_verification: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to confirm verification', 'message': str(e)})
        }


# ============================================================================
# WHAT'S NEW ENDPOINTS
# ============================================================================


def get_all_announcements(query_params):
    """Get all What's New announcements from DynamoDB"""
    try:
        response = whats_new_table.scan()
        items = response.get('Items', [])

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = whats_new_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))

        # Optional: Filter by search query
        search_query = query_params.get('q', '').lower()
        if search_query:
            items = [
                item for item in items
                if search_query in item.get('title', '').lower() or
                   search_query in item.get('description', '').lower() or
                   search_query in item.get('service_tag', '').lower()
            ]

        # Sort by date_published descending
        items.sort(key=lambda x: x.get('date_published', ''), reverse=True)

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'announcements': items,
                'count': len(items)
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error in get_all_announcements: {str(e)}")
        raise


def get_announcement_by_id(announcement_id):
    """Get a specific What's New announcement by ID"""
    if not announcement_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Announcement ID is required'})
        }

    try:
        response = whats_new_table.get_item(Key={'announcement_id': announcement_id})
        item = response.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Announcement not found'})
            }

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'announcement': item}, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error in get_announcement_by_id: {str(e)}")
        raise


def get_announcement_stats():
    """Get aggregate stats for What's New announcements"""
    try:
        response = whats_new_table.scan()
        items = response.get('Items', [])

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = whats_new_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))

        total = len(items)

        # Count per service_tag
        service_counts = {}
        for item in items:
            tag = item.get('service_tag', 'Unknown')
            service_counts[tag] = service_counts.get(tag, 0) + 1

        # Count per label
        label_counts = {}
        for item in items:
            label = item.get('label', '')
            if label:
                label_counts[label] = label_counts.get(label, 0) + 1

        # Count last 30 days
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        last_30_days = sum(
            1 for item in items
            if item.get('date_published', '') >= thirty_days_ago
        )

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'total': total,
                'service_counts': service_counts,
                'label_counts': label_counts,
                'last_30_days': last_30_days
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error in get_announcement_stats: {str(e)}")
        raise


@require_auth
def vote_on_announcement(event, body):
    """Vote on a What's New announcement"""
    announcement_id = event.get('pathParameters', {}).get('id')
    if not announcement_id:
        # Extract from path
        path = event.get('path', '')
        parts = path.split('/')
        if len(parts) >= 3:
            announcement_id = parts[2]

    if not announcement_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Announcement ID is required'})
        }

    vote_type = body.get('vote_type')
    voter_id = body.get('voter_id')
    authenticated_user_id = event['user']['sub']

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
        response = whats_new_table.get_item(Key={'announcement_id': announcement_id})
        item = response.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Announcement not found'})
            }

        if vote_type == 'love':
            lovers = item.get('love_voters', [])
            if voter_id in lovers:
                return {
                    'statusCode': 400,
                    'headers': cors_headers(),
                    'body': json.dumps({'error': 'You have already loved this announcement'})
                }

            whats_new_table.update_item(
                Key={'announcement_id': announcement_id},
                UpdateExpression='SET love_votes = if_not_exists(love_votes, :zero) + :inc, love_voters = list_append(if_not_exists(love_voters, :empty_list), :voter)',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':zero': 0,
                    ':voter': [voter_id],
                    ':empty_list': []
                }
            )
        else:
            vote_field = f'{vote_type}_votes'
            voters_field = f'{vote_type}_voters'
            voters = item.get(voters_field, [])
            if voter_id in voters:
                return {
                    'statusCode': 400,
                    'headers': cors_headers(),
                    'body': json.dumps({'error': 'You have already voted on this announcement'})
                }

            whats_new_table.update_item(
                Key={'announcement_id': announcement_id},
                UpdateExpression=f'SET {vote_field} = if_not_exists({vote_field}, :zero) + :inc, {voters_field} = list_append(if_not_exists({voters_field}, :empty_list), :voter)',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':zero': 0,
                    ':voter': [voter_id],
                    ':empty_list': []
                }
            )

        response = whats_new_table.get_item(Key={'announcement_id': announcement_id})
        updated_item = response.get('Item')

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Vote recorded successfully',
                'announcement': updated_item
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error in vote_on_announcement: {str(e)}")
        raise


@require_auth
def toggle_announcement_bookmark(event, body):
    """Toggle bookmark on a What's New announcement"""
    announcement_id = event.get('pathParameters', {}).get('id')
    if not announcement_id:
        path = event.get('path', '')
        parts = path.split('/')
        if len(parts) >= 3:
            announcement_id = parts[2]

    if not announcement_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Announcement ID is required'})
        }

    user_id = event['user']['sub']
    body_user_id = body.get('user_id')

    if body_user_id and body_user_id != user_id:
        return {
            'statusCode': 403,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Forbidden', 'message': 'user_id must match authenticated user'})
        }

    try:
        response = profiles_table.get_item(Key={'user_id': user_id})
        profile = response.get('Item')

        if not profile:
            profile = {
                'user_id': user_id,
                'email': event['user'].get('email', ''),
                'display_name': event['user'].get('email', '').split('@')[0],
                'bookmarks': [],
                'created_at': get_timestamp(),
                'updated_at': get_timestamp()
            }

        bookmarks = profile.get('bookmarks', [])

        if announcement_id in bookmarks:
            bookmarks.remove(announcement_id)
            action = 'removed'
        else:
            bookmarks.append(announcement_id)
            action = 'added'

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
                'bookmarked': announcement_id in bookmarks,
                'bookmark_count': len(bookmarks)
            })
        }

    except Exception as e:
        print(f"Error in toggle_announcement_bookmark: {str(e)}")
        raise


def get_announcement_comments(event, announcement_id):
    """Get all comments for a What's New announcement"""
    if not announcement_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Announcement ID is required'})
        }

    try:
        response = whats_new_table.get_item(Key={'announcement_id': announcement_id})
        item = response.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Announcement not found'})
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
                    pass
        except:
            pass

        # Filter comments based on moderation status
        filtered_comments = []
        for comment in comments:
            status = comment.get('moderation_status', 'approved')
            if status == 'approved':
                filtered_comments.append(comment)
            elif status == 'pending_review' and comment.get('voter_id') == current_user_id:
                filtered_comments.append(comment)

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'comments': filtered_comments,
                'count': len(filtered_comments)
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error in get_announcement_comments: {str(e)}")
        raise


@require_auth
def add_announcement_comment(event, body):
    """Add a comment to a What's New announcement"""
    announcement_id = event.get('pathParameters', {}).get('id')
    if not announcement_id:
        path = event.get('path', '')
        parts = path.split('/')
        if len(parts) >= 3:
            announcement_id = parts[2]

    if not announcement_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Announcement ID is required'})
        }

    text = body.get('text', '').strip()
    voter_id = body.get('voter_id')
    authenticated_user_id = event['user']['sub']

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
        # Get announcement for moderation context
        ann_response = whats_new_table.get_item(Key={'announcement_id': announcement_id})
        announcement = ann_response.get('Item')

        if not announcement:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Announcement not found'})
            }

        post_context = {
            'post_id': announcement_id,
            'title': announcement.get('title', ''),
            'tags': announcement.get('service_tag', '')
        }

        # Moderate comment
        try:
            moderation_result = moderate_comment(text, post_context)
            print(f"Moderation result: {json.dumps(moderation_result)}")
        except Exception as e:
            print(f"Moderation error: {e}")
            moderation_result = {
                'status': 'approved',
                'reason': None,
                'confidence': 0.0,
                'timestamp': datetime.utcnow().isoformat()
            }

        # Get user's display name
        display_name = 'User'
        try:
            profile_response = profiles_table.get_item(Key={'user_id': voter_id})
            profile = profile_response.get('Item')
            if profile:
                display_name = profile.get('display_name', 'User')
        except Exception as e:
            print(f"Error fetching profile for display name: {e}")

        comment = {
            'comment_id': str(uuid.uuid4()),
            'voter_id': voter_id,
            'display_name': display_name,
            'text': text,
            'timestamp': datetime.utcnow().isoformat(),
            'moderation_status': moderation_result['status'],
            'moderation_confidence': Decimal(str(moderation_result['confidence'])),
            'moderation_timestamp': moderation_result['timestamp']
        }

        if moderation_result['status'] == 'pending_review' and moderation_result['reason']:
            comment['moderation_reason'] = moderation_result['reason']

        whats_new_table.update_item(
            Key={'announcement_id': announcement_id},
            UpdateExpression='SET comments = list_append(if_not_exists(comments, :empty_list), :comment), comment_count = if_not_exists(comment_count, :zero) + :inc',
            ExpressionAttributeValues={
                ':comment': [comment],
                ':empty_list': [],
                ':zero': 0,
                ':inc': 1
            }
        )

        response = whats_new_table.get_item(Key={'announcement_id': announcement_id})
        updated_item = response.get('Item')

        return {
            'statusCode': 201,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Comment added successfully',
                'comment': comment,
                'announcement': updated_item
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error in add_announcement_comment: {str(e)}")
        raise


# ============================================================================
# KB EDITOR ENDPOINTS
# ============================================================================

# KB Configuration
KB_S3_BUCKET = 'euc-content-hub-kb-staging'
KB_ID = 'MIMYGSK1YU'
KB_DATA_SOURCE_ID = 'XC68GVBFXK'

# KB Documents metadata
KB_DOCUMENTS = [
    {
        'id': 'euc-qa-pairs',
        'name': 'EUC Q&A Pairs',
        'description': 'Common questions and answers about AWS EUC services',
        'category': 'Q&A',
        's3_key': 'curated-qa/common-questions.md',
        'question_count': 50
    },
    {
        'id': 'euc-service-mappings',
        'name': 'EUC Service Mappings',
        'description': 'Mappings between EUC services and AWS services',
        'category': 'Reference',
        's3_key': 'service-mappings/service-renames.md',
        'service_count': 25
    }
]

@require_auth
def handle_get_kb_documents(event):
    """GET /kb-documents - List all KB documents"""
    try:
        s3 = boto3.client('s3')
        
        # Enrich documents with S3 metadata
        enriched_docs = []
        for doc in KB_DOCUMENTS:
            try:
                # Get S3 object metadata
                response = s3.head_object(
                    Bucket=KB_S3_BUCKET,
                    Key=doc['s3_key']
                )
                doc_copy = doc.copy()
                doc_copy['size'] = response['ContentLength']
                doc_copy['last_modified'] = response['LastModified'].isoformat()
                enriched_docs.append(doc_copy)
            except Exception as e:
                print(f"Error getting metadata for {doc['id']}: {str(e)}")
                # Include document even if metadata fetch fails
                doc_copy = doc.copy()
                doc_copy['size'] = 0
                doc_copy['last_modified'] = None
                enriched_docs.append(doc_copy)
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'documents': enriched_docs
            })
        }
    
    except Exception as e:
        print(f"Error in handle_get_kb_documents: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to load documents', 'message': str(e)})
        }

@require_auth
def handle_get_kb_document(event, document_id):
    """GET /kb-document/{document_id} - Get KB document content"""
    try:
        # Find document metadata
        doc_meta = next((d for d in KB_DOCUMENTS if d['id'] == document_id), None)
        if not doc_meta:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Document not found'})
            }
        
        # Get document content from S3
        s3 = boto3.client('s3')
        response = s3.get_object(
            Bucket=KB_S3_BUCKET,
            Key=doc_meta['s3_key']
        )
        content = response['Body'].read().decode('utf-8')
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                **doc_meta,
                'content': content,
                'size': len(content),
                'line_count': content.count('\n') + 1
            })
        }
    
    except Exception as e:
        print(f"Error in handle_get_kb_document: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to load document', 'message': str(e)})
        }

@require_auth
def handle_update_kb_document(event, document_id, body):
    """PUT /kb-document/{document_id} - Update KB document"""
    try:
        import uuid
        import hashlib
        from datetime import datetime
        
        user = event['user']
        user_id = user['sub']
        table_suffix = get_table_suffix(event)
        
        # Validate request
        new_content = body.get('content')
        change_comment = body.get('change_comment', '').strip()
        
        if not new_content:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Content is required'})
            }
        
        if not change_comment or len(change_comment) < 10:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Change comment must be at least 10 characters'})
            }
        
        if len(change_comment) > 500:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Change comment must be less than 500 characters'})
            }
        
        # Find document metadata
        doc_meta = next((d for d in KB_DOCUMENTS if d['id'] == document_id), None)
        if not doc_meta:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Document not found'})
            }
        
        # Get current content from S3
        s3 = boto3.client('s3')
        try:
            response = s3.get_object(
                Bucket=KB_S3_BUCKET,
                Key=doc_meta['s3_key']
            )
            old_content = response['Body'].read().decode('utf-8')
        except s3.exceptions.NoSuchKey:
            old_content = ''
        
        # Calculate content hashes
        old_hash = hashlib.sha256(old_content.encode()).hexdigest()
        new_hash = hashlib.sha256(new_content.encode()).hexdigest()
        
        # Check if content actually changed
        if old_hash == new_hash:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'No changes detected'})
            }
        
        # Calculate line changes
        old_lines = old_content.split('\n')
        new_lines = new_content.split('\n')
        lines_added = max(0, len(new_lines) - len(old_lines))
        lines_removed = max(0, len(old_lines) - len(new_lines))
        
        # Upload new content to S3
        s3.put_object(
            Bucket=KB_S3_BUCKET,
            Key=doc_meta['s3_key'],
            Body=new_content.encode('utf-8'),
            ContentType='text/plain'
        )
        
        # Get S3 version ID
        response = s3.head_object(
            Bucket=KB_S3_BUCKET,
            Key=doc_meta['s3_key']
        )
        version_id = response.get('VersionId', 'unknown')
        
        # Record edit in DynamoDB
        edit_history_table = dynamodb.Table(f'kb-edit-history{table_suffix}')
        edit_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        edit_history_table.put_item(
            Item={
                'edit_id': edit_id,
                'user_id': user_id,
                'document_id': document_id,
                'timestamp': timestamp,
                'change_comment': change_comment,
                'content_hash_before': old_hash,
                'content_hash_after': new_hash,
                'lines_added': lines_added,
                'lines_removed': lines_removed,
                's3_version_id': version_id
            }
        )
        
        # Update contributor stats
        contributor_stats_table = dynamodb.Table(f'kb-contributor-stats{table_suffix}')
        
        # Calculate points (10 base + bonuses)
        points = 10
        if lines_added > 50:
            points += 5  # Substantial addition
        if len(change_comment) > 100:
            points += 2  # Detailed comment
        
        # Get user's display name from profile
        try:
            profile_response = profiles_table.get_item(Key={'user_id': user_id})
            profile = profile_response.get('Item', {})
            contributor_display_name = profile.get('display_name', user.get('email', 'Unknown'))
        except Exception:
            contributor_display_name = user.get('email', 'Unknown')
        
        # Update stats
        contributor_stats_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='''
                SET total_edits = if_not_exists(total_edits, :zero) + :one,
                    total_lines_added = if_not_exists(total_lines_added, :zero) + :lines_added,
                    total_lines_removed = if_not_exists(total_lines_removed, :zero) + :lines_removed,
                    total_points = if_not_exists(total_points, :zero) + :points,
                    last_edit_timestamp = :timestamp,
                    display_name = :display_name
            ''',
            ExpressionAttributeValues={
                ':zero': 0,
                ':one': 1,
                ':lines_added': lines_added,
                ':lines_removed': lines_removed,
                ':points': points,
                ':timestamp': timestamp,
                ':display_name': contributor_display_name
            }
        )
        
        # Trigger Bedrock ingestion
        bedrock_agent = boto3.client('bedrock-agent')
        try:
            ingestion_response = bedrock_agent.start_ingestion_job(
                knowledgeBaseId=KB_ID,
                dataSourceId=KB_DATA_SOURCE_ID
            )
            ingestion_job_id = ingestion_response['ingestionJob']['ingestionJobId']
        except Exception as e:
            print(f"Error starting ingestion job: {str(e)}")
            ingestion_job_id = None
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'success': True,
                'edit_id': edit_id,
                'points_earned': points,
                'ingestion_job_id': ingestion_job_id,
                'changes': {
                    'lines_added': lines_added,
                    'lines_removed': lines_removed
                }
            })
        }
    
    except Exception as e:
        print(f"Error in handle_update_kb_document: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to update document', 'message': str(e)})
        }

def handle_get_kb_contributors(event):
    """GET /kb-contributors - Get contributor leaderboard"""
    try:
        query_params = event.get('queryStringParameters') or {}
        period = query_params.get('period', 'all')  # all, month, week
        limit = int(query_params.get('limit', 10))
        table_suffix = get_table_suffix(event)
        
        contributor_stats_table = dynamodb.Table(f'kb-contributor-stats{table_suffix}')
        
        # Scan all contributors
        response = contributor_stats_table.scan()
        contributors = response.get('Items', [])
        
        # Filter by period if needed
        if period != 'all':
            # For now, return all (period filtering would require monthly_stats field)
            pass
        
        # Sort by total_points
        contributors.sort(key=lambda x: x.get('total_points', 0), reverse=True)
        
        # Limit results
        contributors = contributors[:limit]
        
        # Add rank
        for i, contributor in enumerate(contributors):
            contributor['rank'] = i + 1
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'contributors': contributors,
                'period': period
            }, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error in handle_get_kb_contributors: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to load contributors', 'message': str(e)})
        }

@require_auth
def handle_get_my_contributions(event):
    """GET /kb-my-contributions - Get current user's contributions"""
    try:
        user = event['user']
        user_id = user['sub']
        display_name = user.get('name', user.get('email', 'Anonymous'))
        table_suffix = get_table_suffix(event)
        
        # Get user stats
        contributor_stats_table = dynamodb.Table(f'kb-contributor-stats{table_suffix}')
        response = contributor_stats_table.get_item(Key={'user_id': user_id})
        stats = response.get('Item', {
            'user_id': user_id,
            'total_edits': 0,
            'total_lines_added': 0,
            'total_lines_removed': 0,
            'total_points': 0,
            'documents_edited_count': 0
        })
        
        # Ensure documents_edited_count exists
        if 'documents_edited_count' not in stats:
            stats['documents_edited_count'] = 0
        
        # Get recent edits
        edit_history_table = dynamodb.Table(f'kb-edit-history{table_suffix}')
        response = edit_history_table.query(
            IndexName='user_id-timestamp-index',
            KeyConditionExpression='user_id = :user_id',
            ExpressionAttributeValues={':user_id': user_id},
            ScanIndexForward=False,  # Newest first
            Limit=10
        )
        recent_edits = response.get('Items', [])
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'display_name': display_name,
                'stats': stats,
                'recent_contributions': recent_edits
            }, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error in handle_get_my_contributions: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to load contributions', 'message': str(e)})
        }

@require_auth
def handle_get_ingestion_status(event, job_id):
    """GET /kb-ingestion-status/{job_id} - Check ingestion job status"""
    try:
        bedrock_agent = boto3.client('bedrock-agent')
        
        response = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=KB_ID,
            dataSourceId=KB_DATA_SOURCE_ID,
            ingestionJobId=job_id
        )
        
        job = response['ingestionJob']
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'status': job['status'],
                'started_at': job.get('startedAt', '').isoformat() if job.get('startedAt') else None,
                'completed_at': job.get('updatedAt', '').isoformat() if job.get('updatedAt') else None
            })
        }
    
    except Exception as e:
        print(f"Error in handle_get_ingestion_status: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to check ingestion status', 'message': str(e)})
        }

def refine_article_proposal(user_input, selected_category=None):
    """Use Bedrock to refine a user's article idea into a structured proposal."""
    category_guidance = ""
    if selected_category:
        category_guidance = f"\nThe user prefers the '{selected_category}' category. Tailor the proposal to fit this category's style."

    prompt = f"""You are an expert AWS technical writer helping someone create a community article proposal for the EUC (End User Computing) Content Hub.

The user wants to write about:
{user_input}
{category_guidance}

Available article categories:
1. Announcement - Promotes releases, events, open-source code, or new tools.
2. Best Practices - Shows patterns, anti-patterns, how to build better applications.
3. Curation - Helps discover other content and events.
4. Customer Story - Highlights how a customer solved a technical challenge.
5. Technical How-To - Provides how-to content with code examples.
6. Thought Leadership - Sets context on broader technical challenges.

Create a refined article proposal. Respond in JSON format:
{{
    "title": "Compelling article title",
    "category": "One of the 6 categories",
    "summary": "2-3 sentence summary",
    "outline": ["Section 1", "Section 2", "Section 3", "Section 4"],
    "key_topics": ["topic1", "topic2", "topic3"],
    "target_audience": "Who should read this",
    "estimated_length": "Short (600 words) / Medium (1200 words) / Long (2400 words)",
    "writing_tips": "2-3 specific tips for writing this article"
}}"""

    try:
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 1500,
                'temperature': 0.7,
                'messages': [{'role': 'user', 'content': prompt}]
            })
        )
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text'].strip()

        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        return json.loads(content)
    except Exception as e:
        print(f"Error refining proposal with Bedrock: {e}")
        return {
            'title': 'Article Proposal',
            'category': selected_category or 'Technical How-To',
            'summary': user_input[:200],
            'outline': ['Introduction', 'Main Content', 'Conclusion'],
            'key_topics': ['EUC', 'AWS'],
            'target_audience': 'IT professionals',
            'estimated_length': 'Medium (1200 words)',
            'writing_tips': 'Focus on practical examples and clear explanations.'
        }

EUC_SERVICES = [
    "Amazon WorkSpaces Personal", "Amazon WorkSpaces Pools", "Amazon WorkSpaces Core",
    "Amazon WorkSpaces Applications (formerly AppStream 2.0)", "Amazon WorkSpaces Secure Browser",
    "Amazon WorkSpaces Thin Client", "Amazon DCV", "Other/General EUC"
]

PRIORITY_LEVELS = ["Nice to Have", "Important", "Critical"]

def refine_feature_proposal(service, title, description, priority, use_case=None):
    """Use Bedrock to refine a feature proposal."""
    try:
        prompt = f"""You are an AWS End User Computing product manager. A community member has submitted a feature request. Analyze and enhance it.

Service: {service}
Feature Title: {title}
Description: {description}
Priority: {priority}
{f'Use Case: {use_case}' if use_case else ''}

Respond in JSON format:
{{
    "refined_description": "A clearer, more structured version of the feature description",
    "related_features": "Known existing features or workarounds that partially address this need",
    "request_category": "One of: New Capability, Enhancement, Integration, Performance, Usability"
}}"""

        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 500,
                'messages': [{'role': 'user', 'content': prompt}]
            })
        )

        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']

        # Extract JSON, handling ```json wrappers
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        import re
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

        return {'refined_description': '', 'related_features': '', 'request_category': ''}
    except Exception as e:
        print(f"Error refining feature proposal with Bedrock: {e}")
        return {'refined_description': '', 'related_features': '', 'request_category': ''}


def convert_mermaid_to_png(mermaid_code, innovation_id):
    """Convert Mermaid.js code to PNG image and upload to S3.
    
    Uses the mermaid.ink public API to render the diagram as PNG,
    then uploads to S3. Returns the S3 URL on success, empty string on failure.
    Non-blocking — promotion succeeds even if conversion fails.
    """
    try:
        import urllib.request
        import urllib.error

        # Base64-encode the Mermaid code for the mermaid.ink API
        encoded = base64.urlsafe_b64encode(mermaid_code.encode('utf-8')).decode('utf-8')
        render_url = f'https://mermaid.ink/img/{encoded}?type=png'

        # Fetch the rendered PNG
        req = urllib.request.Request(render_url, headers={'User-Agent': 'EUCContentHub/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            png_data = resp.read()

        if not png_data or len(png_data) < 100:
            print(f"Mermaid render returned empty/tiny response for {innovation_id}")
            return ''

        # Determine S3 bucket based on environment
        table_suffix = os.environ.get('TABLE_SUFFIX', '')
        if table_suffix == '-staging':
            bucket = 'aws-blog-viewer-staging-031421429609'
        else:
            bucket = 'aws-blog-viewer-031421429609'

        s3_key = f'diagrams/{innovation_id}.png'

        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=png_data,
            ContentType='image/png',
            CacheControl='max-age=86400'
        )

        # Return CloudFront-friendly URL
        if table_suffix == '-staging':
            return f'https://staging.awseuccontent.com/{s3_key}'
        else:
            return f'https://awseuccontent.com/{s3_key}'

    except Exception as e:
        print(f"Mermaid-to-PNG conversion failed for {innovation_id}: {e}")
        return ''


def refine_innovation_to_article(innovation):
    """Use Bedrock to transform an innovation into a structured article proposal."""
    title = innovation.get('title', '')
    problem = innovation.get('problem_statement', '')
    arch = innovation.get('architecture_description', '')
    snippets = innovation.get('code_snippets', [])
    upvotes = innovation.get('upvotes', 0)
    comment_count = innovation.get('comment_count', 0)

    snippets_text = ''
    for s in snippets[:3]:
        snippets_text += f"\n[{s.get('language', 'code')}]: {s.get('code', '')[:300]}"

    prompt = f"""You are an expert AWS technical writer helping transform a community innovation into a Builder.AWS article proposal.

Innovation Title: {title}
Problem Statement: {problem}
Architecture Description: {arch}
Code Snippets (preview): {snippets_text}
Community Engagement: {upvotes} upvotes, {comment_count} comments

Available article categories:
1. Announcement - Promotes releases, events, open-source code, or new tools.
2. Best Practices - Shows patterns, anti-patterns, how to build better applications.
3. Curation - Helps discover other content and events.
4. Customer Story - Highlights how a customer solved a technical challenge.
5. Technical How-To - Provides how-to content with code examples.
6. Thought Leadership - Sets context on broader technical challenges.

Transform this innovation into a compelling article proposal. The article should tell the story of the problem, the architectural approach, and the solution. Respond in JSON format:
{{
    "title": "Compelling article title",
    "category": "One of the 6 categories",
    "summary": "2-3 sentence summary of the article",
    "outline": ["Section 1", "Section 2", "Section 3", "Section 4"],
    "key_topics": ["topic1", "topic2", "topic3"],
    "target_audience": "Who should read this",
    "estimated_length": "Short (600 words) / Medium (1200 words) / Long (2400 words)",
    "writing_tips": "2-3 specific tips for writing this article"
}}"""

    try:
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 1500,
                'temperature': 0.7,
                'messages': [{'role': 'user', 'content': prompt}]
            })
        )
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text'].strip()

        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        return json.loads(content)
    except Exception as e:
        print(f"Error refining innovation to article with Bedrock: {e}")
        return {
            'title': title or 'Article Proposal',
            'category': 'Technical How-To',
            'summary': problem[:200] if problem else '',
            'outline': ['Introduction', 'Problem Statement', 'Architecture', 'Implementation', 'Conclusion'],
            'key_topics': ['EUC', 'AWS'],
            'target_audience': 'IT professionals and cloud architects',
            'estimated_length': 'Long (2400 words)',
            'writing_tips': 'Focus on the problem-solution narrative and include architecture diagrams.'
        }


def refine_innovation_to_feature(innovation):
    """Use Bedrock to transform an innovation into a structured feature proposal."""
    title = innovation.get('title', '')
    problem = innovation.get('problem_statement', '')
    arch = innovation.get('architecture_description', '')
    services = innovation.get('aws_services', [])
    complexity = innovation.get('complexity_level', '')

    try:
        prompt = f"""You are an AWS End User Computing product manager. A community member has developed an innovation that reveals a potential service feature opportunity. Analyze and transform it into a feature request.

Innovation Title: {title}
Problem Statement: {problem}
Architecture Description: {arch}
AWS Services Used: {', '.join(services) if services else 'N/A'}
Complexity Level: {complexity}

Respond in JSON format:
{{
    "refined_description": "A clear, structured feature description distilled from the innovation",
    "related_features": "Known existing features or workarounds that partially address this need",
    "request_category": "One of: New Capability, Enhancement, Integration, Performance, Usability"
}}"""

        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 500,
                'messages': [{'role': 'user', 'content': prompt}]
            })
        )

        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']

        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        import re
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

        return {'refined_description': '', 'related_features': '', 'request_category': ''}
    except Exception as e:
        print(f"Error refining innovation to feature with Bedrock: {e}")
        return {'refined_description': '', 'related_features': '', 'request_category': ''}


@require_auth
def submit_feature_proposal(event, body):
    """Submit a new service feature proposal."""
    user_id = event['user']['sub']
    
    # Validate required fields
    service = body.get('service', '').strip()
    title = body.get('title', '').strip()
    description = body.get('description', '').strip()
    priority = body.get('priority', '').strip()
    use_case = body.get('use_case', '').strip()
    
    if not service:
        return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': 'Service is required'})}
    if not title or len(title) < 10:
        return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': 'Title must be at least 10 characters'})}
    if not description or len(description) < 30:
        return {'statusCode': 400, 'headers': cors_headers(), 'body': json.dumps({'error': 'Description must be at least 30 characters'})}
    
    if priority not in PRIORITY_LEVELS:
        priority = 'Nice to Have'
    
    # Get display name
    try:
        profile_resp = profiles_table.get_item(Key={'user_id': user_id})
        display_name = profile_resp.get('Item', {}).get('display_name', event['user'].get('email', '').split('@')[0])
    except:
        display_name = event['user'].get('email', '').split('@')[0]
    
    # AI enhancement
    ai_content = refine_feature_proposal(service, title, description, priority, use_case)
    
    # Create proposal
    proposal_id = str(uuid.uuid4())
    now = get_timestamp()
    
    proposal = {
        'proposal_id': proposal_id,
        'proposal_type': 'feature',
        'user_id': user_id,
        'display_name': display_name,
        'service': service,
        'title': title,
        'description': description,
        'priority': priority,
        'use_case': use_case,
        'ai_generated_content': ai_content,
        'status': 'pending',
        'votes': 0,
        'upvotes': 0,
        'downvotes': 0,
        'voters': [],
        'comments': [],
        'created_at': now,
        'updated_at': now
    }
    
    proposals_table.put_item(Item=proposal)
    
    # Badge evaluation
    new_badges = []
    try:
        new_badges = evaluate_and_award_badges(user_id, 'proposal_submitted')
    except Exception as e:
        print(f"Badge evaluation error: {e}")
    
    return {
        'statusCode': 201,
        'headers': cors_headers(),
        'body': json.dumps({'message': 'Feature proposal created successfully', 'proposal': proposal, 'new_badges': new_badges}, cls=DecimalEncoder)
    }


@require_auth
def submit_proposal(event, body):
    """
    Submit a new article proposal.
    Requires authentication - user ID extracted from JWT token.

    Supports two modes:
    1. AI generation mode: body contains 'user_input' (and optional 'category').
       Calls Bedrock to generate title, outline, summary, etc., then persists.
    2. Direct mode: body contains 'title' and 'description' (and optional 'ai_generated_content').
       Persists directly without AI generation.
    """
    user_input = body.get('user_input', '').strip() if body.get('user_input') else ''

    if user_input:
        # --- AI generation mode ---
        if len(user_input) < 20:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Please provide more details (at least 20 characters)'})
            }

        try:
            user_id = event['user']['sub']
            display_name = 'User'
            try:
                profile_response = profiles_table.get_item(Key={'user_id': user_id})
                profile = profile_response.get('Item')
                if profile:
                    display_name = profile.get('display_name', 'User')
            except Exception as e:
                print(f"Error fetching profile for display name: {e}")

            selected_category = body.get('category', '')
            ai_proposal = refine_article_proposal(user_input, selected_category)

            now = datetime.utcnow().isoformat() + 'Z'
            proposal = {
                'proposal_id': str(uuid.uuid4()),
                'proposal_type': 'article',
                'user_id': user_id,
                'display_name': display_name,
                'title': ai_proposal.get('title', 'Article Proposal'),
                'description': user_input,
                'category': ai_proposal.get('category', selected_category or ''),
                'ai_generated_content': {
                    'outline': ai_proposal.get('outline', []),
                    'summary': ai_proposal.get('summary', ''),
                    'key_topics': ai_proposal.get('key_topics', []),
                    'target_audience': ai_proposal.get('target_audience', ''),
                    'estimated_length': ai_proposal.get('estimated_length', ''),
                    'writing_tips': ai_proposal.get('writing_tips', '')
                },
                'status': 'pending',
                'votes': 0,
                'voters': [],
                'created_at': now,
                'updated_at': now
            }

            proposals_table.put_item(Item=proposal)

            # Badge evaluation
            new_badges = []
            try:
                new_badges = evaluate_and_award_badges(user_id, 'proposal_submitted')
            except Exception as e:
                print(f"Badge evaluation error in submit_proposal: {str(e)}")

            # Return flat fields for backward compatibility with frontend displayProposal
            flat_response = {
                **proposal,
                'title': proposal['title'],
                'summary': proposal['ai_generated_content']['summary'],
                'outline': proposal['ai_generated_content']['outline'],
                'key_topics': proposal['ai_generated_content']['key_topics'],
                'target_audience': proposal['ai_generated_content']['target_audience'],
                'estimated_length': proposal['ai_generated_content']['estimated_length'],
                'writing_tips': proposal['ai_generated_content']['writing_tips'],
                'original_input': user_input
            }

            return {
                'statusCode': 201,
                'headers': cors_headers(),
                'body': json.dumps({
                    'message': 'Proposal created successfully',
                    'proposal': flat_response,
                    'new_badges': new_badges
                }, cls=DecimalEncoder)
            }

        except Exception as e:
            print(f"Error in submit_proposal (AI mode): {str(e)}")
            return {
                'statusCode': 500,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
            }

    # --- Direct mode (title + description provided) ---
    title = body.get('title', '').strip() if body.get('title') else ''
    description = body.get('description', '').strip() if body.get('description') else ''

    if not title or not description:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Missing required fields', 'message': 'title and description are required'})
        }

    try:
        user_id = event['user']['sub']
        display_name = 'User'
        try:
            profile_response = profiles_table.get_item(Key={'user_id': user_id})
            profile = profile_response.get('Item')
            if profile:
                display_name = profile.get('display_name', 'User')
        except Exception as e:
            print(f"Error fetching profile for display name: {e}")

        ai_input = body.get('ai_generated_content', {}) or {}
        ai_generated_content = {
            'outline': ai_input.get('outline', []),
            'summary': ai_input.get('summary', ''),
            'key_topics': ai_input.get('key_topics', []),
            'target_audience': ai_input.get('target_audience', ''),
            'estimated_length': ai_input.get('estimated_length', ''),
            'writing_tips': ai_input.get('writing_tips', '')
        }

        now = datetime.utcnow().isoformat() + 'Z'
        proposal = {
            'proposal_id': str(uuid.uuid4()),
            'proposal_type': 'article',
            'user_id': user_id,
            'display_name': display_name,
            'title': title,
            'description': description,
            'category': body.get('category', ''),
            'ai_generated_content': ai_generated_content,
            'status': 'pending',
            'votes': 0,
            'voters': [],
            'created_at': now,
            'updated_at': now
        }

        proposals_table.put_item(Item=proposal)

        # Badge evaluation
        new_badges = []
        try:
            new_badges = evaluate_and_award_badges(user_id, 'proposal_submitted')
        except Exception as e:
            print(f"Badge evaluation error in submit_proposal: {str(e)}")

        return {
            'statusCode': 201,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Proposal created successfully',
                'proposal': proposal,
                'new_badges': new_badges
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error in submit_proposal: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }


def list_proposals(query_params):
    """
    List proposals with optional filtering by status, user_id, or proposal_type.
    No authentication required (public read endpoint).

    Query parameters:
    - status: filter by proposal status (queries GSI for efficient lookup)
    - user_id: filter by submitter user_id (scan with filter)
    - proposal_type: filter by proposal type ('article' or 'feature')
    - (none): return all proposals
    All results sorted by created_at descending (newest first).
    """
    try:
        status = query_params.get('status', '').strip() if query_params.get('status') else ''
        user_id = query_params.get('user_id', '').strip() if query_params.get('user_id') else ''
        proposal_type_filter = query_params.get('proposal_type', '').strip() if query_params.get('proposal_type') else ''

        if status:
            # Query GSI for efficient status-based lookup, sorted by created_at descending
            response = proposals_table.query(
                IndexName='status-created_at-index',
                KeyConditionExpression=Key('status').eq(status),
                ScanIndexForward=False
            )
            proposals = response['Items']
        elif user_id:
            # Scan with filter on user_id, sort client-side
            response = proposals_table.scan(
                FilterExpression=Attr('user_id').eq(user_id)
            )
            proposals = sorted(response['Items'], key=lambda x: x.get('created_at', ''), reverse=True)
        else:
            # Full table scan, sort client-side
            response = proposals_table.scan()
            proposals = sorted(response['Items'], key=lambda x: x.get('created_at', ''), reverse=True)

        # Apply proposal_type filter in Python after fetching
        if proposal_type_filter:
            if proposal_type_filter == 'article':
                # Treat records without proposal_type as 'article' for backward compatibility
                proposals = [p for p in proposals if p.get('proposal_type', 'article') == 'article']
            else:
                proposals = [p for p in proposals if p.get('proposal_type') == proposal_type_filter]

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'proposals': proposals}, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error in list_proposals: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }



@require_auth
def vote_on_proposal(event, body):
    """
    Vote on a proposal (upvote or downvote).
    Requires authentication. Each user gets one vote per proposal.

    Body: { "vote_type": "up" | "down" }
    Thresholds: 5 upvotes -> approved, 3 downvotes -> rejected
    """
    APPROVE_THRESHOLD = 5
    REJECT_THRESHOLD = 3

    try:
        path = event.get('path', '')
        parts = path.strip('/').split('/')
        proposal_id = parts[1] if len(parts) >= 3 else None

        if not proposal_id:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Proposal ID is required'})
            }

        vote_type = body.get('vote_type', 'up')
        if vote_type not in ('up', 'down'):
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'vote_type must be "up" or "down"'})
            }

        response = proposals_table.get_item(Key={'proposal_id': proposal_id})
        item = response.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Proposal not found'})
            }

        user_id = event['user']['sub']
        voters = item.get('voters', [])

        if user_id in voters:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Already voted', 'message': 'You have already voted on this proposal'})
            }

        now = datetime.utcnow().isoformat() + 'Z'

        if vote_type == 'up':
            update_expr = 'SET votes = if_not_exists(votes, :zero) + :inc, upvotes = if_not_exists(upvotes, :zero) + :inc, voters = list_append(if_not_exists(voters, :empty), :voter), updated_at = :ts'
        else:
            update_expr = 'SET downvotes = if_not_exists(downvotes, :zero) + :inc, voters = list_append(if_not_exists(voters, :empty), :voter), updated_at = :ts'

        response = proposals_table.update_item(
            Key={'proposal_id': proposal_id},
            UpdateExpression=update_expr,
            ExpressionAttributeValues={
                ':inc': 1,
                ':zero': 0,
                ':voter': [user_id],
                ':empty': [],
                ':ts': now
            },
            ReturnValues='ALL_NEW'
        )
        updated = response['Attributes']

        # Check thresholds for auto status change
        upvotes = int(updated.get('upvotes', 0))
        downvotes = int(updated.get('downvotes', 0))
        current_status = updated.get('status', 'pending')

        new_status = current_status
        if current_status == 'pending':
            if upvotes >= APPROVE_THRESHOLD:
                new_status = 'approved'
            elif downvotes >= REJECT_THRESHOLD:
                new_status = 'rejected'

        if new_status != current_status:
            proposals_table.update_item(
                Key={'proposal_id': proposal_id},
                UpdateExpression='SET #s = :status, updated_at = :ts',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':status': new_status, ':ts': now}
            )
            updated['status'] = new_status

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Vote recorded successfully',
                'proposal': updated
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error in vote_on_proposal: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }


@require_auth
def comment_on_proposal(event, body):
    """Add a comment/feedback to a proposal. Requires authentication."""
    try:
        path = event.get('path', '')
        parts = path.strip('/').split('/')
        proposal_id = parts[1] if len(parts) >= 3 else None

        if not proposal_id:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Proposal ID is required'})
            }

        text = body.get('text', '').strip()
        if not text:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Comment text is required'})
            }

        # Verify proposal exists
        response = proposals_table.get_item(Key={'proposal_id': proposal_id})
        if not response.get('Item'):
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Proposal not found'})
            }

        user_id = event['user']['sub']
        display_name = 'User'
        try:
            profile_response = profiles_table.get_item(Key={'user_id': user_id})
            profile = profile_response.get('Item')
            if profile:
                display_name = profile.get('display_name', 'User')
        except Exception as e:
            print(f"Error fetching profile: {e}")

        now = datetime.utcnow().isoformat() + 'Z'
        comment = {
            'comment_id': str(uuid.uuid4()),
            'user_id': user_id,
            'display_name': display_name,
            'text': text,
            'created_at': now
        }

        proposals_table.update_item(
            Key={'proposal_id': proposal_id},
            UpdateExpression='SET comments = list_append(if_not_exists(comments, :empty), :comment), updated_at = :ts',
            ExpressionAttributeValues={
                ':comment': [comment],
                ':empty': [],
                ':ts': now
            }
        )

        return {
            'statusCode': 201,
            'headers': cors_headers(),
            'body': json.dumps({'message': 'Comment added', 'comment': comment}, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error in comment_on_proposal: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }


@require_auth
def delete_proposal(event, body):
    """Delete a proposal. Only the author can delete their own proposal."""
    try:
        path = event.get('path', '')
        parts = path.strip('/').split('/')
        proposal_id = parts[1] if len(parts) >= 2 else None

        if not proposal_id:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Proposal ID is required'})
            }

        response = proposals_table.get_item(Key={'proposal_id': proposal_id})
        item = response.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Proposal not found'})
            }

        user_id = event['user']['sub']
        if item.get('user_id') != user_id:
            return {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Forbidden', 'message': 'You can only delete your own proposals'})
            }

        proposals_table.delete_item(Key={'proposal_id': proposal_id})

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'message': 'Proposal deleted'})
        }

    except Exception as e:
        print(f"Error in delete_proposal: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }

