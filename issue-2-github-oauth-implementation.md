# Issue #2: Amazon Email Verification for Admin Access

## Overview

Allow Amazon employees to verify their @amazon.com email address to gain admin access privileges. This uses a simple email verification flow with time-expiring confirmation links, leveraging Amazon's existing email security infrastructure.

## Solution: Email Verification Flow

**Key Concept**: Users prove they're Amazonians by verifying they have access to an @amazon.com email account.

**Benefits**:
- ✅ No OAuth complexity or third-party integrations
- ✅ Leverages Amazon's existing email security (MFA, VPN, etc.)
- ✅ Simple user experience
- ✅ Time-limited verification links prevent abuse
- ✅ Automatically revoked when employee leaves (email access removed)
- ✅ Works with any authentication provider (Google, GitHub, etc.)

## Prerequisites

- AWS SES (Simple Email Service) for sending verification emails
- DynamoDB table: `euc-user-profiles` (already exists)
- Lambda function for email verification logic
- Frontend profile page (already exists)

## User Flow

### For Regular Users (Non-Amazon)
1. Sign in with Google (existing flow)
2. Use all community features (comment, vote, bookmark)
3. No admin access

### For Amazon Employees
1. Sign in with Google (existing flow)
2. Go to Profile page
3. See "Verify Amazon Email" section
4. Enter @amazon.com email address
5. Click "Send Verification Email"
6. Check Amazon email inbox
7. Click verification link (expires in 1 hour)
8. Redirected back to site with verified status
9. Profile now shows "Amazon Verified ✓" badge
10. Gain access to admin features (Issue #7)

---

## Implementation Steps

### Step 1: Update DynamoDB Schema

**Add fields to `euc-user-profiles` table:**
```python
{
    'user_id': 'string',           # Existing
    'email': 'string',             # Existing (from Google OAuth)
    'display_name': 'string',      # Existing
    'bio': 'string',               # Existing
    'credly_url': 'string',        # Existing
    'builder_id': 'string',        # Existing
    'bookmarks': ['post_id'],      # Existing
    'created_at': 'string',        # Existing
    'updated_at': 'string',        # Existing
    
    # NEW FIELDS - Amazon Verification
    'amazon_email': 'string',              # @amazon.com email to verify
    'amazon_verified': 'boolean',          # True if verified
    'amazon_verified_at': 'string',        # Timestamp of verification
    'amazon_verified_expires_at': 'string', # Expiration (90 days from verification)
    'verification_reminder_sent': 'boolean', # True if 7-day reminder sent
    'is_admin': 'boolean'                  # Admin privileges (set by super admin)
}
```

**No migration needed** - fields added on-demand with UpdateExpression

---

### Step 2: Verification Expiration Strategy

**Hybrid Approach**: Automatic expiration + manual revocation

**Why This Matters:**
- Users authenticate with Google (not Amazon email)
- Former employees could retain verified status indefinitely
- Need automatic cleanup for security

**Solution:**
1. **90-Day Expiration**: Verification expires automatically after 90 days
2. **7-Day Reminder**: Email reminder sent 7 days before expiration
3. **Easy Re-verification**: One-click link in reminder email
4. **Manual Revocation**: Super admins can revoke anytime (Issue #7)
5. **Automatic Enforcement**: Admin actions check verification status

**Benefits:**
- Former employees lose access within 90 days (can't access @amazon.com email)
- Active employees get proactive reminders
- Super admins can take immediate action if needed
- Balances security with user convenience

---

### Step 3: Create Verification Token Table

**New DynamoDB table: `email-verification-tokens`**
```python
{
    'token': 'string',             # Primary key (UUID)
    'user_id': 'string',           # User requesting verification
    'email': 'string',             # Email to verify
    'created_at': 'number',        # Unix timestamp
    'expires_at': 'number',        # Unix timestamp (created_at + 1 hour)
    'used': 'boolean'              # True if already used
}
```

**TTL enabled** on `expires_at` field (auto-delete expired tokens)

---

### Step 4: Set Up AWS SES

**Configure SES for sending emails:**

1. **Verify Domain** (awseuccontent.com):
   ```bash
   aws ses verify-domain-identity --domain awseuccontent.com
   ```
   - Add DNS records for verification
   - Add DKIM records for email authentication

2. **Request Production Access**:
   - By default, SES is in sandbox mode (can only send to verified emails)
   - Request production access to send to any @amazon.com address
   - Justification: "Email verification for Amazon employee admin access"

3. **Create Email Template**:
   ```html
   Subject: Verify your Amazon email for EUC Content Hub
   
   Body:
   Hi {{display_name}},
   
   Click the link below to verify your Amazon email address and gain admin access to EUC Content Hub:
   
   {{verification_link}}
   
   This link expires in 1 hour.
   
   If you didn't request this, you can safely ignore this email.
   
   Thanks,
   EUC Content Hub Team
   ```

---

### Step 5: Create Email Verification Lambda

**New Lambda: `aws-blog-email-verification`**

**Handler: `lambda_function.lambda_handler`**

**Endpoints:**
- `POST /verify-email/request` - Request verification email
- `GET /verify-email/confirm` - Confirm verification (from email link)

**Code structure:**
```python
import boto3
import json
import uuid
import time
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')
profiles_table = dynamodb.Table('euc-user-profiles')
tokens_table = dynamodb.Table('email-verification-tokens')

def lambda_handler(event, context):
    path = event.get('path', '')
    method = event.get('httpMethod', '')
    
    if path == '/verify-email/request' and method == 'POST':
        return request_verification(event)
    elif path == '/verify-email/confirm' and method == 'GET':
        return confirm_verification(event)
    
    return {'statusCode': 404, 'body': 'Not found'}

def request_verification(event):
    """Send verification email"""
    # 1. Validate user is authenticated
    # 2. Parse amazon_email from request body
    # 3. Validate email ends with @amazon.com
    # 4. Generate UUID token
    # 5. Store token in DynamoDB with 1-hour expiry
    # 6. Send email via SES with verification link
    # 7. Return success response

def confirm_verification(event):
    """Confirm email verification from link"""
    # 1. Extract token from query string
    # 2. Look up token in DynamoDB
    # 3. Validate token exists, not expired, not used
    # 4. Mark token as used
    # 5. Update user profile with:
    #    - amazon_verified=True
    #    - amazon_verified_at=now
    #    - amazon_verified_expires_at=now+90days
    #    - verification_reminder_sent=False
    # 6. Redirect to profile page with success message
```

---

### Step 6: Create Verification Expiration Lambda

**New Lambda: `aws-blog-verification-checker`**

**Purpose**: Daily scheduled job to check for expiring verifications

**Trigger**: CloudWatch Events (runs daily at 9 AM UTC)

**Code structure:**
```python
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')
profiles_table = dynamodb.Table('euc-user-profiles')

def lambda_handler(event, context):
    """Check for expiring verifications and send reminders"""
    
    # 1. Scan for verified users
    response = profiles_table.scan(
        FilterExpression='amazon_verified = :true',
        ExpressionAttributeValues={':true': True}
    )
    
    now = datetime.utcnow()
    reminder_threshold = now + timedelta(days=7)  # 7 days from now
    expiration_threshold = now  # Already expired
    
    reminders_sent = 0
    verifications_revoked = 0
    
    for user in response['Items']:
        expires_at = datetime.fromisoformat(user.get('amazon_verified_expires_at', ''))
        reminder_sent = user.get('verification_reminder_sent', False)
        
        # Check if expired
        if expires_at < expiration_threshold:
            revoke_verification(user['user_id'])
            verifications_revoked += 1
            print(f"Revoked expired verification for user {user['user_id']}")
        
        # Check if reminder needed (expires in 7 days and reminder not sent)
        elif expires_at < reminder_threshold and not reminder_sent:
            send_reminder_email(user)
            mark_reminder_sent(user['user_id'])
            reminders_sent += 1
            print(f"Sent reminder to user {user['user_id']}")
    
    return {
        'statusCode': 200,
        'body': {
            'reminders_sent': reminders_sent,
            'verifications_revoked': verifications_revoked
        }
    }

def revoke_verification(user_id):
    """Revoke verification and admin access"""
    profiles_table.update_item(
        Key={'user_id': user_id},
        UpdateExpression='SET amazon_verified = :false, is_admin = :false',
        ExpressionAttributeValues={
            ':false': False
        }
    )

def send_reminder_email(user):
    """Send 7-day expiration reminder"""
    ses.send_email(
        Source='noreply@awseuccontent.com',
        Destination={'ToAddresses': [user['amazon_email']]},
        Message={
            'Subject': {'Data': 'Your Amazon verification expires in 7 days'},
            'Body': {
                'Html': {
                    'Data': f"""
                    <p>Hi {user['display_name']},</p>
                    <p>Your Amazon email verification for EUC Content Hub expires in 7 days.</p>
                    <p>To maintain your admin access, please re-verify your email:</p>
                    <p><a href="https://awseuccontent.com/profile?reverify=true">Re-verify Now</a></p>
                    <p>This takes just a few seconds - we'll send a new verification link to {user['amazon_email']}.</p>
                    <p>Thanks,<br>EUC Content Hub Team</p>
                    """
                }
            }
        }
    )

def mark_reminder_sent(user_id):
    """Mark that reminder has been sent"""
    profiles_table.update_item(
        Key={'user_id': user_id},
        UpdateExpression='SET verification_reminder_sent = :true',
        ExpressionAttributeValues={':true': True}
    )
```

**CloudWatch Events Rule:**
```bash
aws events put-rule \
    --name daily-verification-check \
    --schedule-expression "cron(0 9 * * ? *)" \
    --description "Check for expiring Amazon email verifications"

aws events put-targets \
    --rule daily-verification-check \
    --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:031421429609:function:aws-blog-verification-checker"
```

---

### Step 7: Update API Lambda

**Add endpoint to `api_lambda.py`:**

```python
# In lambda_handler(), add route:
elif path == '/profile/amazon-email' and method == 'POST':
    return update_amazon_email(event, body)

@require_auth
def update_amazon_email(event, body):
    """Update user's Amazon email (doesn't verify yet)"""
    user_id = event['user']['sub']
    amazon_email = body.get('amazon_email', '').strip().lower()
    
    # Validate email format
    if not amazon_email.endswith('@amazon.com'):
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Must be @amazon.com email'})
        }
    
    # Update profile (reset verification if email changed)
    profiles_table.update_item(
        Key={'user_id': user_id},
        UpdateExpression='SET amazon_email = :email, amazon_verified = :verified, verification_reminder_sent = :false',
        ExpressionAttributeValues={
            ':email': amazon_email,
            ':verified': False,  # Reset verification status
            ':false': False
        }
    )
    
    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({'message': 'Amazon email updated'})
    }
```

---

**Add verification check decorator:**
```python
def require_current_verification(func):
    """Decorator to check if Amazon verification is current"""
    def wrapper(event, body):
        user_id = event['user']['sub']
        
        # Get user profile
        response = profiles_table.get_item(Key={'user_id': user_id})
        user = response.get('Item', {})
        
        # Check if verified
        if not user.get('amazon_verified', False):
            return {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Amazon verification required'})
            }
        
        # Check if expired
        expires_at = datetime.fromisoformat(user.get('amazon_verified_expires_at', ''))
        if datetime.utcnow() > expires_at:
            # Revoke verification
            profiles_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='SET amazon_verified = :false, is_admin = :false',
                ExpressionAttributeValues={':false': False}
            )
            return {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Amazon verification expired. Please re-verify.'})
            }
        
        # Verification is current - proceed
        return func(event, body)
    
    return wrapper

# Use on admin endpoints (Issue #7)
@require_auth
@require_current_verification
def admin_delete_post(event, body):
    """Admin-only endpoint to delete posts"""
    # Admin logic here
    pass
```

---

### Step 8: Update Frontend Profile Page

**Add to `frontend/profile.js`:**

```javascript
// Add Amazon email verification section
function renderAmazonVerification(profile) {
    const isVerified = profile.amazon_verified || false;
    const amazonEmail = profile.amazon_email || '';
    const expiresAt = profile.amazon_verified_expires_at;
    
    // Calculate days until expiration
    let daysUntilExpiration = null;
    let expirationWarning = false;
    if (isVerified && expiresAt) {
        const expireDate = new Date(expiresAt);
        const now = new Date();
        daysUntilExpiration = Math.ceil((expireDate - now) / (1000 * 60 * 60 * 24));
        expirationWarning = daysUntilExpiration <= 14; // Show warning if < 14 days
    }
    
    return `
        <div class="amazon-verification-section">
            <h3>Amazon Employee Verification</h3>
            ${isVerified ? `
                <div class="verified-badge ${expirationWarning ? 'expiring-soon' : ''}">
                    <span class="badge-icon">✓</span>
                    <span>Amazon Verified</span>
                    <p class="verified-email">${amazonEmail}</p>
                    ${expirationWarning ? `
                        <p class="expiration-warning">
                            ⚠️ Expires in ${daysUntilExpiration} days
                            <button onclick="requestAmazonVerification()" class="reverify-btn">
                                Re-verify Now
                            </button>
                        </p>
                    ` : `
                        <p class="expiration-info">
                            Expires in ${daysUntilExpiration} days
                        </p>
                    `}
                </div>
            ` : `
                <p>Verify your @amazon.com email to gain admin access</p>
                <input type="email" 
                       id="amazon-email-input" 
                       placeholder="username@amazon.com"
                       value="${amazonEmail}">
                <button onclick="requestAmazonVerification()">
                    Send Verification Email
                </button>
            `}
        </div>
    `;
}

async function requestAmazonVerification() {
    const email = document.getElementById('amazon-email-input').value.trim();
    
    if (!email.endsWith('@amazon.com')) {
        showNotification('Must be an @amazon.com email address', 'error');
        return;
    }
    
    try {
        // First, update the email in profile
        const updateResponse = await fetch(`${API_BASE_URL}/profile/amazon-email`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ amazon_email: email })
        });
        
        if (!updateResponse.ok) throw new Error('Failed to update email');
        
        // Then, request verification email
        const verifyResponse = await fetch(`${API_BASE_URL}/verify-email/request`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ amazon_email: email })
        });
        
        if (!verifyResponse.ok) throw new Error('Failed to send verification');
        
        showNotification('Verification email sent! Check your inbox.', 'success');
    } catch (error) {
        console.error('Verification error:', error);
        showNotification('Failed to send verification email', 'error');
    }
}

// Handle verification callback (when user clicks email link)
function handleVerificationCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const verified = urlParams.get('verified');
    const reverify = urlParams.get('reverify');
    
    if (verified === 'true') {
        showNotification('Amazon email verified successfully! Valid for 90 days.', 'success');
        loadProfile(); // Reload profile to show verified badge
    } else if (verified === 'false') {
        showNotification('Verification failed or expired', 'error');
    }
    
    // Handle re-verification request from reminder email
    if (reverify === 'true') {
        showNotification('Please re-verify your Amazon email to maintain admin access', 'info');
        // Auto-focus the email input or show verification section
    }
}

// Call on page load
document.addEventListener('DOMContentLoaded', handleVerificationCallback);
```

**Add to `frontend/styles.css`:**
```css
.amazon-verification-section {
    margin-top: 2rem;
    padding: 1.5rem;
    background: #f8f9fa;
    border-radius: 8px;
}

.verified-badge {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 1rem;
    background: #d4edda;
    border: 1px solid #c3e6cb;
    border-radius: 4px;
    color: #155724;
}

.verified-badge.expiring-soon {
    background: #fff3cd;
    border-color: #ffc107;
    color: #856404;
}

.badge-icon {
    font-size: 1.5rem;
    color: #28a745;
}

.verified-email {
    margin-top: 0.5rem;
    font-size: 0.9rem;
    color: #666;
}

#amazon-email-input {
    width: 100%;
    padding: 0.75rem;
    margin: 1rem 0;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
}

.expiration-warning {
    margin-top: 0.5rem;
    padding: 0.5rem;
    background: #fff3cd;
    border-radius: 4px;
    font-weight: bold;
}

.expiration-info {
    margin-top: 0.5rem;
    font-size: 0.85rem;
    color: #666;
}

.reverify-btn {
    margin-left: 0.5rem;
    padding: 0.25rem 0.75rem;
    background: #ffc107;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
}

.reverify-btn:hover {
    background: #e0a800;
}
```

---

### Step 9: Create Verification Token Table

**AWS CLI command:**
```bash
aws dynamodb create-table \
    --table-name email-verification-tokens \
    --attribute-definitions \
        AttributeName=token,AttributeType=S \
    --key-schema \
        AttributeName=token,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --time-to-live-specification \
        Enabled=true,AttributeName=expires_at
```

---

### Step 10: Deploy and Test

**Deployment order:**
1. Create DynamoDB table for tokens
2. Set up SES domain verification
3. Deploy email verification Lambda
4. Deploy verification checker Lambda
5. Set up CloudWatch Events rule for daily checks
6. Update API Lambda with new endpoints and decorator
7. Deploy frontend changes to staging
8. Test full flow in staging (including expiration)
9. Deploy to production

**Testing checklist:**
- [ ] User can enter @amazon.com email
- [ ] Verification email is sent
- [ ] Email contains working link
- [ ] Link expires after 1 hour
- [ ] Clicking link verifies email
- [ ] Profile shows verified badge with expiration date
- [ ] Non-@amazon.com emails are rejected
- [ ] Used tokens can't be reused
- [ ] Verification expires after 90 days
- [ ] Reminder email sent 7 days before expiration
- [ ] Expired verifications are automatically revoked
- [ ] Re-verification works correctly
- [ ] Admin actions check verification status
- [ ] Expiration warning shows when < 14 days remaining

---

## Security Considerations

### Email Validation
- **Server-side validation**: Must end with `@amazon.com`
- **Case-insensitive**: Convert to lowercase before storing
- **No wildcards**: Exact domain match only

### Token Security
- **UUID v4**: Cryptographically random, unguessable
- **One-time use**: Mark as used after verification
- **Time-limited**: 1-hour expiration
- **Auto-cleanup**: DynamoDB TTL removes expired tokens

### Verification Link
```
https://awseuccontent.com/verify?token=550e8400-e29b-41d4-a716-446655440000
```
- Token in query string (not in URL path for better logging)
- HTTPS only
- No sensitive data in URL

### Rate Limiting
- **Per user**: Max 3 verification requests per hour
- **Per email**: Max 5 verification requests per day
- Prevents abuse and spam

### Email Spoofing Protection
- **SPF record**: Authorize SES to send from awseuccontent.com
- **DKIM**: Sign emails cryptographically
- **DMARC**: Policy for handling failures

---

## Data Model Changes

### User Profile (euc-user-profiles)
```python
# Before
{
    'user_id': 'google_123456',
    'email': 'user@gmail.com',
    'display_name': 'John Doe'
}

# After verification
{
    'user_id': 'google_123456',
    'email': 'user@gmail.com',                      # Google email (for login)
    'display_name': 'John Doe',
    'amazon_email': 'jdoe@amazon.com',              # Verified Amazon email
    'amazon_verified': True,
    'amazon_verified_at': '2026-02-11T10:30:00Z',
    'amazon_verified_expires_at': '2026-05-11T10:30:00Z',  # 90 days later
    'verification_reminder_sent': False,
    'is_admin': False                                # Set by super admin later
}
```

### Verification Token (email-verification-tokens)
```python
{
    'token': '550e8400-e29b-41d4-a716-446655440000',
    'user_id': 'google_123456',
    'email': 'jdoe@amazon.com',
    'created_at': 1707649800,            # Unix timestamp
    'expires_at': 1707653400,            # created_at + 3600 seconds
    'used': False
}
```

---

## Testing Scenarios

### Test Case 1: Happy Path
1. User signs in with Google
2. Goes to profile page
3. Enters jdoe@amazon.com
4. Clicks "Send Verification Email"
5. Receives email at jdoe@amazon.com
6. Clicks verification link
7. Redirected to profile with success message
8. Profile shows "Amazon Verified ✓" badge

**Expected Result**: ✅ User is verified

### Test Case 2: Invalid Email Domain
1. User enters jdoe@gmail.com
2. Clicks "Send Verification Email"

**Expected Result**: ❌ Error: "Must be @amazon.com email"

### Test Case 3: Expired Token
1. User requests verification
2. Waits 2 hours
3. Clicks verification link

**Expected Result**: ❌ Error: "Verification link expired"

### Test Case 4: Reused Token
1. User verifies email successfully
2. Clicks same verification link again

**Expected Result**: ❌ Error: "Verification link already used"

### Test Case 5: Verification Expiration
1. User verifies jdoe@amazon.com
2. Manually set expiration to 6 days from now (for testing)
3. Wait for daily checker to run
4. User receives reminder email
5. User clicks re-verify link
6. User completes re-verification
7. Expiration extended by 90 days

**Expected Result**: ✅ Reminder sent, re-verification works, expiration extended

### Test Case 6: Expired Verification
1. User verifies jdoe@amazon.com
2. Manually set expiration to yesterday (for testing)
3. Wait for daily checker to run
4. User's verification is revoked
5. User tries to access admin feature
6. Access denied

**Expected Result**: ✅ Verification revoked, admin access removed

### Test Case 7: Email Change
1. User verifies jdoe@amazon.com
2. Later changes to jdoe2@amazon.com
3. Verification status resets to False
4. Must verify new email

**Expected Result**: ✅ Verification status correctly reset

---

## Rollback Procedure

If issues occur:

1. **Disable verification feature**:
   - Remove frontend UI (deploy previous version)
   - Keep backend endpoints (no harm if not called)

2. **No data loss**:
   - Existing verified users keep their status
   - New verifications just won't work

3. **Quick fix**:
   - Frontend change only (2-3 min rollback)
   - No Lambda or database changes needed

---

## Cost Estimate

### AWS SES
- **Free tier**: 62,000 emails/month (first 12 months)
- **After free tier**: $0.10 per 1,000 emails
- **Expected usage**: ~100 verifications/month = $0.01/month

### DynamoDB
- **Tokens table**: Pay-per-request pricing
- **Expected usage**: ~100 writes/month, ~100 reads/month
- **Cost**: < $0.01/month

### Lambda
- **Verification Lambda**: Minimal invocations
- **Cost**: Free tier covers it

**Total additional cost**: < $0.02/month

---

## Verification Expiration Details

### Timeline
- **Day 0**: User verifies Amazon email
- **Day 83**: Reminder email sent (7 days before expiration)
- **Day 90**: Verification expires if not renewed
- **Day 90+**: Admin access automatically revoked

### Reminder Email Content
```
Subject: Your Amazon verification expires in 7 days

Hi [Name],

Your Amazon email verification for EUC Content Hub expires in 7 days.

To maintain your admin access, please re-verify your email:
[Re-verify Now Button]

This takes just a few seconds - we'll send a new verification link to your Amazon email.

Thanks,
EUC Content Hub Team
```

### Re-verification Process
1. User clicks "Re-verify Now" in reminder email
2. Redirected to profile page with `?reverify=true`
3. User clicks "Send Verification Email" button
4. New verification email sent to Amazon address
5. User clicks link in email
6. Verification renewed for another 90 days
7. Reminder flag reset

### Manual Revocation (Issue #7)
Super admins can manually revoke verification:
- Immediate effect (no waiting for expiration)
- Used for security incidents, layoffs, etc.
- Revokes both `amazon_verified` and `is_admin` flags

---

## Success Criteria

- [ ] DynamoDB schema updated with expiration fields
- [ ] Verification tokens table created with TTL
- [ ] SES domain verified and production access granted
- [ ] Email verification Lambda created and deployed
- [ ] Verification checker Lambda created and deployed
- [ ] CloudWatch Events rule configured for daily checks
- [ ] API Lambda updated with verification decorator
- [ ] Frontend profile page shows verification UI with expiration
- [ ] Verification email sends successfully
- [ ] Verification link works and sets 90-day expiration
- [ ] Verified badge shows expiration date
- [ ] Token expiration works (1 hour)
- [ ] Used tokens can't be reused
- [ ] Non-@amazon.com emails rejected
- [ ] Reminder emails sent 7 days before expiration
- [ ] Expired verifications automatically revoked
- [ ] Re-verification extends expiration by 90 days
- [ ] Admin actions check current verification status
- [ ] Staging tested end-to-end
- [ ] Production deployed and verified

---

## Next Steps (Issue #7)

After email verification is working:
1. Add admin dashboard UI
2. Add admin-only features (delete posts, ban users, etc.)
3. Add super admin role for granting admin access
4. Build admin approval workflow (optional)

---

**Issue**: #2  
**Priority**: High  
**Status**: Ready for implementation  
**Estimated Time**: 2-3 hours  
**Dependencies**: AWS SES setup  
**Blocks**: Issue #7 (Admin Portal)
