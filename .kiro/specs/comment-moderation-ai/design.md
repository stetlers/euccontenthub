# Design Document: Automated Comment Moderation System

## Overview

The automated comment moderation system integrates AWS Bedrock (Claude Haiku) into the existing comment submission flow to analyze content in real-time. The system operates synchronously during comment submission with a 2-second timeout, defaulting to approval on timeout or error to maintain user experience. Comments are stored with moderation metadata in DynamoDB, and the frontend implements differential display logic to show pending comments only to their authors.

The design prioritizes:
- **Low latency**: 2-second timeout ensures fast comment submission
- **High availability**: Graceful degradation on errors (default to approved)
- **User transparency**: Authors see their pending comments with clear status
- **Security**: Protects users from spam, dangerous links, and harassment
- **Minimal false positives**: Prefers letting borderline content through

## Architecture

### System Components

```
┌─────────────┐
│   Frontend  │
│  (app.js)   │
└──────┬──────┘
       │ POST /posts/{id}/comments
       │ {text, voter_id}
       ▼
┌─────────────────────────────────────────┐
│         API Lambda                      │
│  (lambda_function.py)                   │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  add_comment()                   │  │
│  │  1. Validate auth & input        │  │
│  │  2. Call moderate_comment()      │  │
│  │  3. Store with moderation data   │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  moderate_comment()              │  │
│  │  1. Call Bedrock API             │  │
│  │  2. Parse moderation result      │  │
│  │  3. Return status + reason       │  │
│  │  4. Timeout after 2 seconds      │  │
│  └──────────────────────────────────┘  │
└─────────────┬───────────────────────────┘
              │
              ▼
       ┌─────────────┐
       │   Bedrock   │
       │   Claude    │
       │   Haiku     │
       └─────────────┘
              │
              ▼
       ┌─────────────┐
       │  DynamoDB   │
       │ aws-blog-   │
       │   posts     │
       └─────────────┘
              │
              ▼
       ┌─────────────┐
       │   Frontend  │
       │  Display    │
       │   Logic     │
       └─────────────┘
```

### Data Flow

1. **Comment Submission**: User submits comment via frontend
2. **Authentication**: API Lambda validates JWT token
3. **Moderation Analysis**: Lambda calls `moderate_comment()` which invokes Bedrock
4. **Timeout Handling**: If Bedrock takes >2s, default to 'approved'
5. **Storage**: Comment stored in DynamoDB with moderation metadata
6. **Response**: API returns comment with moderation status
7. **Display**: Frontend filters comments based on moderation status and viewer identity

## Components and Interfaces

### 1. Moderation Function (Python)

**Location**: `lambda_api/lambda_function.py`

**Function Signature**:
```python
def moderate_comment(text: str, post_context: dict) -> dict:
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
    
    Raises:
        TimeoutError: If analysis exceeds 2 seconds
        Exception: On Bedrock API errors
    """
```

**Implementation Details**:
- Uses `boto3` Bedrock Runtime client
- Model: `anthropic.claude-3-haiku-20240307-v1:0`
- Timeout: 2 seconds using `signal.alarm()` or threading
- Prompt engineering: Structured prompt with clear classification criteria
- Error handling: Returns `{'status': 'approved'}` on any error

### 2. Enhanced Comment Storage

**DynamoDB Schema Extension**:
```python
comment = {
    'comment_id': str,           # UUID (existing)
    'voter_id': str,             # User ID (existing)
    'display_name': str,         # Display name (existing)
    'text': str,                 # Comment text (existing)
    'timestamp': str,            # ISO 8601 (existing)
    
    # NEW FIELDS
    'moderation_status': str,    # 'approved' | 'pending_review' | 'rejected'
    'moderation_reason': str,    # Why flagged (optional)
    'moderation_confidence': float,  # 0.0 to 1.0
    'moderation_timestamp': str, # When analyzed
    'admin_reviewed_by': str,    # Admin user ID (future)
    'admin_review_timestamp': str  # When reviewed (future)
}
```

### 3. Modified add_comment() Function

**Changes to Existing Function**:
```python
@require_auth
def add_comment(event, body):
    """
    Add a comment to a post with automated moderation.
    """
    # ... existing validation code ...
    
    # NEW: Get post context for moderation
    post_response = table.get_item(Key={'post_id': post_id})
    post = post_response.get('Item', {})
    post_context = {
        'post_id': post_id,
        'title': post.get('title', ''),
        'tags': post.get('tags', '')
    }
    
    # NEW: Moderate comment
    try:
        moderation_result = moderate_comment(text, post_context)
    except Exception as e:
        print(f"Moderation error: {e}")
        # Default to approved on error
        moderation_result = {
            'status': 'approved',
            'reason': None,
            'confidence': 0.0,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    # Create comment with moderation data
    comment = {
        'comment_id': str(uuid.uuid4()),
        'voter_id': voter_id,
        'display_name': display_name,
        'text': text,
        'timestamp': datetime.utcnow().isoformat(),
        'moderation_status': moderation_result['status'],
        'moderation_confidence': moderation_result['confidence'],
        'moderation_timestamp': moderation_result['timestamp']
    }
    
    # Add reason if flagged
    if moderation_result['status'] == 'pending_review':
        comment['moderation_reason'] = moderation_result['reason']
    
    # ... existing storage code ...
```

### 4. Modified get_comments() Function

**Changes to Existing Function**:
```python
def get_comments(post_id):
    """
    Get comments for a post, filtered by moderation status.
    """
    # ... existing code to fetch post ...
    
    comments = item.get('comments', [])
    
    # NEW: Filter comments based on viewer
    # Check if request is authenticated
    auth_header = event.get('headers', {}).get('Authorization')
    current_user_id = None
    
    if auth_header:
        try:
            decoded = validate_jwt_token(auth_header)
            current_user_id = decoded.get('sub')
        except:
            pass
    
    # Filter comments
    filtered_comments = []
    for comment in comments:
        status = comment.get('moderation_status', 'approved')
        
        # Show approved comments to everyone
        if status == 'approved':
            filtered_comments.append(comment)
        # Show pending comments only to author
        elif status == 'pending_review' and comment.get('voter_id') == current_user_id:
            filtered_comments.append(comment)
        # Hide rejected comments from everyone
        # (future: may show to admins)
    
    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({
            'comments': filtered_comments,
            'count': len(filtered_comments)
        }, cls=DecimalEncoder)
    }
```

### 5. Frontend Display Logic

**Location**: `frontend/app.js`

**Comment Rendering**:
```javascript
function renderComment(comment, isAuthor) {
    const status = comment.moderation_status || 'approved';
    const isPending = status === 'pending_review';
    
    // Only show pending comments to author
    if (isPending && !isAuthor) {
        return null;
    }
    
    const commentDiv = document.createElement('div');
    commentDiv.className = 'comment';
    
    // Add pending styling for author
    if (isPending && isAuthor) {
        commentDiv.classList.add('comment-pending');
    }
    
    commentDiv.innerHTML = `
        <div class="comment-header">
            <span class="comment-author">${escapeHtml(comment.display_name)}</span>
            <span class="comment-timestamp">${formatTimestamp(comment.timestamp)}</span>
            ${isPending && isAuthor ? '<span class="comment-status">⚠️ Pending Administrative Review</span>' : ''}
        </div>
        <div class="comment-text ${isPending && isAuthor ? 'pending-text' : ''}">
            ${escapeHtml(comment.text)}
        </div>
    `;
    
    return commentDiv;
}
```

**CSS Styling**:
```css
.comment-pending {
    background-color: #fff9e6;
    border-left: 3px solid #ff9800;
}

.comment-pending .pending-text {
    color: #e65100;
}

.comment-status {
    background-color: #ff9800;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.85em;
    font-weight: 600;
}
```

## Data Models

### Comment Object (Extended)

```python
{
    # Existing fields
    'comment_id': 'uuid-string',
    'voter_id': 'cognito-user-id',
    'display_name': 'User Display Name',
    'text': 'Comment text content',
    'timestamp': '2024-01-15T10:30:00.000Z',
    
    # New moderation fields
    'moderation_status': 'approved',  # or 'pending_review' or 'rejected'
    'moderation_reason': 'Contains promotional content',  # Optional
    'moderation_confidence': 0.85,  # 0.0 to 1.0
    'moderation_timestamp': '2024-01-15T10:30:00.500Z',
    
    # Future admin review fields
    'admin_reviewed_by': None,  # Will be admin user ID
    'admin_review_timestamp': None  # Will be ISO 8601 timestamp
}
```

### Moderation Prompt Structure

```python
MODERATION_PROMPT = """You are a content moderator for an AWS End User Computing (EUC) technical community platform. Analyze the following comment and determine if it should be approved or flagged for review.

CONTEXT:
- Post Title: {post_title}
- Post Tags: {post_tags}

COMMENT TO ANALYZE:
{comment_text}

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
{
  "status": "approved" or "pending_review",
  "reason": "Brief explanation if pending_review, null if approved",
  "confidence": 0.0 to 1.0
}
"""
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Before defining the correctness properties, I'll analyze each acceptance criterion for testability:


### Property 1: Moderation Status Validity

*For any* comment stored in DynamoDB, the moderation_status field SHALL be either 'approved', 'pending_review', or 'rejected', or absent (for backward compatibility).

**Validates: Requirements 1.3, 2.1**

### Property 2: Moderation Precedes Storage

*For any* comment with a moderation_timestamp, the moderation_timestamp SHALL be less than or equal to the comment timestamp, ensuring moderation occurs before or during storage.

**Validates: Requirements 1.1, 2.3**

### Property 3: Flagged Comments Include Reason

*For any* comment with moderation_status 'pending_review', the comment SHALL include a non-empty moderation_reason field explaining why it was flagged.

**Validates: Requirements 2.2**

### Property 4: Comment Filtering by Viewer Identity

*For any* set of comments on a post, when retrieved by a user, the returned comments SHALL include all 'approved' comments plus any 'pending_review' comments where the viewer is the comment author, and SHALL exclude all other 'pending_review' comments.

**Validates: Requirements 3.1, 3.2**

### Property 5: Pending Comment Visual Distinction

*For any* comment with moderation_status 'pending_review' rendered for its author, the HTML output SHALL contain CSS classes for distinct styling and SHALL include the text "Pending Administrative Review".

**Validates: Requirements 3.3, 3.4**

### Property 6: Public Comment Count Accuracy

*For any* post, the public comment count SHALL equal the number of comments with moderation_status 'approved' or absent (legacy comments), excluding all 'pending_review' and 'rejected' comments.

**Validates: Requirements 3.5**

### Property 7: Link Count Threshold

*For any* comment containing 4 or more URLs, the Moderation_System SHALL assign moderation_status 'pending_review' regardless of the URL domains.

**Validates: Requirements 4.3, 5.3**

### Property 8: Suspicious URL Pattern Detection

*For any* comment containing URLs with IP addresses, URL shorteners (bit.ly, tinyurl, etc.), or uncommon TLDs (.tk, .ml, .ga, etc.), the Moderation_System SHALL assign moderation_status 'pending_review'.

**Validates: Requirements 5.1**

### Property 9: Legacy Comment Compatibility

*For any* comment without a moderation_status field, the System SHALL treat it as having moderation_status 'approved' when filtering and displaying comments.

**Validates: Requirements 2.4, 2.5**

### Property 10: Moderation Performance

*For any* comment submitted under normal conditions, the moderation analysis SHALL complete within 2 seconds, measured from the start of moderate_comment() to its return.

**Validates: Requirements 8.1**

## Error Handling

### Timeout Handling

**Scenario**: Bedrock API takes longer than 2 seconds to respond

**Behavior**:
1. Python timeout mechanism (using `signal.alarm()` or `threading.Timer`) triggers after 2 seconds
2. Function catches `TimeoutError` exception
3. Returns `{'status': 'approved', 'confidence': 0.0, 'reason': None}`
4. Logs warning: `"Moderation timeout for comment {comment_id}, defaulting to approved"`
5. Comment is stored with 'approved' status

**Rationale**: Prioritizes user experience over perfect moderation. Better to let a potentially problematic comment through than to block legitimate users.

### Bedrock API Errors

**Scenario**: Bedrock API returns error (throttling, service unavailable, invalid request)

**Behavior**:
1. Function catches exception from `boto3` Bedrock client
2. Returns `{'status': 'approved', 'confidence': 0.0, 'reason': None}`
3. Logs error: `"Moderation error for comment {comment_id}: {error_message}, defaulting to approved"`
4. Comment is stored with 'approved' status

**Error Types**:
- `ThrottlingException`: Too many requests to Bedrock
- `ServiceUnavailableException`: Bedrock temporarily unavailable
- `ValidationException`: Invalid request format
- `AccessDeniedException`: IAM permissions issue

### JSON Parsing Errors

**Scenario**: Bedrock returns malformed JSON response

**Behavior**:
1. Function catches `json.JSONDecodeError`
2. Returns `{'status': 'approved', 'confidence': 0.0, 'reason': None}`
3. Logs error: `"Failed to parse moderation response for comment {comment_id}, defaulting to approved"`
4. Comment is stored with 'approved' status

### Missing Required Fields

**Scenario**: Bedrock JSON response missing 'status' or 'confidence' fields

**Behavior**:
1. Function validates response structure
2. If missing required fields, returns `{'status': 'approved', 'confidence': 0.0, 'reason': None}`
3. Logs warning: `"Incomplete moderation response for comment {comment_id}, defaulting to approved"`
4. Comment is stored with 'approved' status

### DynamoDB Storage Errors

**Scenario**: DynamoDB update fails after successful moderation

**Behavior**:
1. API Lambda catches DynamoDB exception
2. Returns 500 error to client with message: "Failed to store comment"
3. Logs error with full exception details
4. Client can retry submission

**Note**: Moderation result is not cached, so retry will re-moderate the comment.

## Testing Strategy

### Dual Testing Approach

The testing strategy combines unit tests for specific scenarios and property-based tests for comprehensive coverage:

**Unit Tests** (specific examples and edge cases):
- Spam detection with promotional language
- Harassment detection with profanity and threats
- Off-topic content detection
- Legitimate technical discussions (should be approved)
- Timeout handling with mocked slow responses
- Error handling with mocked Bedrock failures
- Legacy comment handling (comments without moderation fields)
- Backward compatibility scenarios

**Property-Based Tests** (universal properties across all inputs):
- Moderation status validity (Property 1)
- Moderation timing (Property 2)
- Flagged comment metadata (Property 3)
- Comment filtering logic (Property 4)
- Visual distinction rendering (Property 5)
- Comment count accuracy (Property 6)
- Link count threshold (Property 7)
- Suspicious URL detection (Property 8)
- Legacy compatibility (Property 9)
- Performance timing (Property 10)

### Property-Based Testing Configuration

**Library**: Use `hypothesis` for Python (Lambda functions) and `fast-check` for JavaScript (frontend)

**Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with: `Feature: comment-moderation-ai, Property {number}: {property_text}`
- Tests run in CI/CD pipeline before deployment

**Example Property Test Structure** (Python):
```python
from hypothesis import given, strategies as st
import pytest

@given(
    comment_text=st.text(min_size=1, max_size=1000),
    post_context=st.fixed_dictionaries({
        'post_id': st.uuids(),
        'title': st.text(),
        'tags': st.text()
    })
)
def test_property_1_moderation_status_validity(comment_text, post_context):
    """
    Feature: comment-moderation-ai, Property 1: Moderation Status Validity
    
    For any comment stored in DynamoDB, the moderation_status field SHALL be
    either 'approved', 'pending_review', or 'rejected', or absent.
    """
    result = moderate_comment(comment_text, post_context)
    
    assert result['status'] in ['approved', 'pending_review', 'rejected']
```

### Integration Testing

**Test Environment**: Staging environment with separate DynamoDB tables

**Test Scenarios**:
1. End-to-end comment submission with moderation
2. Comment retrieval with filtering by viewer identity
3. Frontend display of pending comments to author
4. Frontend hiding of pending comments from other users
5. Performance testing with concurrent comment submissions
6. Bedrock API integration (real API calls in staging)

### Manual Testing Checklist

Before production deployment:
- [ ] Submit legitimate technical comment → Verify approved
- [ ] Submit spam comment → Verify flagged
- [ ] Submit comment with 4+ links → Verify flagged
- [ ] Submit comment with suspicious URL → Verify flagged
- [ ] Submit comment with profanity → Verify flagged
- [ ] View comments as author → Verify pending comments visible
- [ ] View comments as different user → Verify pending comments hidden
- [ ] Check comment count on post card → Verify excludes pending
- [ ] Test timeout scenario (mock slow Bedrock) → Verify defaults to approved
- [ ] Test error scenario (mock Bedrock error) → Verify defaults to approved

## Implementation Notes

### Bedrock Model Selection

**Model**: `anthropic.claude-3-haiku-20240307-v1:0`

**Rationale**:
- **Speed**: Haiku is optimized for low-latency responses (<1 second typical)
- **Cost**: Most cost-effective Claude model (~$0.25 per million input tokens)
- **Capability**: Sufficient for content moderation tasks
- **Availability**: Available in us-east-1 region

**Alternative**: If Haiku is unavailable, fall back to Claude 3 Sonnet, but expect higher latency and cost.

### Timeout Implementation

**Approach**: Use Python `signal` module for timeout

```python
import signal

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Moderation timeout")

def moderate_comment(text, post_context):
    # Set 2-second timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(2)
    
    try:
        # Call Bedrock API
        response = bedrock_client.invoke_model(...)
        signal.alarm(0)  # Cancel alarm
        return parse_response(response)
    except TimeoutError:
        signal.alarm(0)  # Cancel alarm
        return {'status': 'approved', 'confidence': 0.0, 'reason': None}
```

**Note**: `signal.alarm()` only works on Unix-like systems. For Windows or Lambda, use `threading.Timer` as alternative.

### Prompt Engineering Best Practices

**Clarity**: Use explicit criteria with examples
**Structure**: JSON output format for easy parsing
**Context**: Include post title and tags for relevance evaluation
**Bias**: Explicitly state preference for false negatives over false positives
**Examples**: Provide clear examples of what to flag and what to approve

### Performance Optimization

**Caching**: Do not cache moderation results (each comment is unique)
**Batching**: Do not batch comments (each needs individual analysis)
**Async Processing**: Initial implementation is synchronous; async can be added later if needed
**Connection Pooling**: Reuse Bedrock client across Lambda invocations

### Security Considerations

**Input Validation**: Comment text is already validated in `add_comment()` (max length, required field)
**Injection Prevention**: Bedrock API handles prompt injection; no additional escaping needed
**PII Protection**: Do not log comment text in CloudWatch (only comment_id and moderation result)
**Rate Limiting**: Rely on API Gateway rate limiting (existing configuration)

### Monitoring and Observability

**CloudWatch Metrics**:
- `ModerationLatency`: Time taken for moderation analysis
- `ModerationTimeouts`: Count of timeout occurrences
- `ModerationErrors`: Count of Bedrock API errors
- `FlaggedComments`: Count of comments flagged as pending_review
- `ApprovedComments`: Count of comments approved

**CloudWatch Logs**:
- Log moderation result for each comment (status, confidence, reason)
- Log timeouts and errors with comment_id
- Do not log comment text (privacy concern)

**Alarms**:
- Alert if moderation timeout rate exceeds 5%
- Alert if moderation error rate exceeds 10%
- Alert if average latency exceeds 1.5 seconds

### Deployment Strategy

**Phase 1**: Deploy to staging environment
- Test with sample comments
- Verify Bedrock integration
- Validate filtering logic
- Check frontend display

**Phase 2**: Deploy to production with monitoring
- Deploy Lambda changes
- Deploy frontend changes
- Monitor CloudWatch metrics
- Watch for errors or timeouts

**Phase 3**: Iterate based on feedback
- Adjust moderation prompt if too many false positives
- Tune confidence thresholds
- Add admin review interface (future work)

**Rollback Plan**: If issues occur, revert Lambda to previous version (instant rollback via alias)
