# Issue #2: GitHub OAuth Implementation Guide

## Overview

Add GitHub as an identity provider in AWS Cognito to allow users to authenticate with their GitHub accounts alongside existing Google authentication.

## Prerequisites

- AWS Cognito User Pool ID: `us-east-1_MOvNrTnua`
- Cognito App Client ID: `3pv5jf235vj14gu148b9vjt3od`
- Production URL: `https://awseuccontent.com`
- Staging URL: `https://staging.awseuccontent.com`

## Implementation Steps

### Step 1: Create GitHub OAuth App

**Navigate to GitHub:**
1. Go to https://github.com/settings/developers
2. Click "OAuth Apps" → "New OAuth App"

**OAuth App Configuration:**
```
Application name: EUC Content Hub
Homepage URL: https://awseuccontent.com
Application description: AWS End User Computing Content Hub - Community platform for AWS EUC blog posts
Authorization callback URL: https://awseuccontent.auth.us-east-1.amazoncognito.com/oauth2/idpresponse
```

**After Creation:**
- Note the **Client ID**
- Generate and note the **Client Secret**
- Keep these secure - you'll need them for Cognito configuration

**For Staging (Optional but Recommended):**
Create a second OAuth app for staging:
```
Application name: EUC Content Hub (Staging)
Homepage URL: https://staging.awseuccontent.com
Authorization callback URL: https://staging.awseuccontent.auth.us-east-1.amazoncognito.com/oauth2/idpresponse
```

---

### Step 2: Configure GitHub Identity Provider in Cognito

**AWS Console Steps:**

1. **Navigate to Cognito:**
   - Go to AWS Console → Cognito
   - Select User Pool: `us-east-1_MOvNrTnua`

2. **Add Identity Provider:**
   - Go to "Sign-in experience" tab
   - Click "Add identity provider"
   - Select "GitHub"

3. **Configure GitHub Provider:**
   ```
   Provider name: GitHub
   Client ID: [Your GitHub OAuth App Client ID]
   Client secret: [Your GitHub OAuth App Client Secret]
   Authorize scopes: user:email
   ```

4. **Attribute Mapping:**
   Map GitHub attributes to Cognito user pool attributes:
   ```
   GitHub Attribute → Cognito Attribute
   email            → email
   name             → name
   login            → preferred_username
   ```

5. **Save Configuration**

---

### Step 3: Update Cognito App Client

**Update App Client Settings:**

1. **Navigate to App Client:**
   - Go to "App integration" tab
   - Select app client: `3pv5jf235vj14gu148b9vjt3od`

2. **Update Identity Providers:**
   - Ensure both providers are enabled:
     - ✅ Google
     - ✅ GitHub

3. **Verify OAuth Settings:**
   ```
   Allowed callback URLs:
   - https://awseuccontent.com
   - https://staging.awseuccontent.com
   
   Allowed sign-out URLs:
   - https://awseuccontent.com
   - https://staging.awseuccontent.com
   
   OAuth 2.0 Grant Types:
   - ✅ Authorization code grant
   
   OAuth Scopes:
   - ✅ email
   - ✅ openid
   - ✅ profile
   ```

4. **Save Changes**

---

### Step 4: Update Cognito Hosted UI

**Hosted UI Configuration:**

1. **Navigate to Hosted UI:**
   - Go to "App integration" tab
   - Click "View Hosted UI"

2. **Verify Appearance:**
   - Should now show both "Sign in with Google" and "Sign in with GitHub" buttons
   - Test the UI appearance

3. **Customize (Optional):**
   - Go to "Branding" tab
   - Customize logo, colors if desired

---

### Step 5: Test Authentication Flow

**Testing Checklist:**

#### Production Testing
1. **Navigate to**: https://awseuccontent.com
2. **Click "Sign In"**
3. **Verify**: Both Google and GitHub buttons appear
4. **Test GitHub Login:**
   - Click "Sign in with GitHub"
   - Authorize the app
   - Verify redirect back to site
   - Check user profile is created
   - Verify email is captured

#### Staging Testing
1. **Navigate to**: https://staging.awseuccontent.com
2. **Repeat same tests**
3. **Verify**: Separate OAuth app works correctly

#### Profile Verification
1. **After GitHub login**, check user profile:
   - Email should be populated
   - Display name should default to GitHub username
   - User ID (sub) should be unique

2. **Check DynamoDB:**
   ```bash
   aws dynamodb scan --table-name euc-user-profiles \
     --filter-expression "contains(email, :github)" \
     --expression-attribute-values '{":github":{"S":"@users.noreply.github.com"}}' \
     --limit 5
   ```

---

### Step 6: Frontend Verification (No Changes Needed)

**Current Implementation:**
- Frontend uses Cognito Hosted UI
- No code changes required
- GitHub button automatically appears

**Verify in Browser:**
```javascript
// After GitHub login, check JWT token
const user = window.authManager.getUser();
console.log('User:', user);
console.log('Email:', user.email);
console.log('Identity Provider:', user['cognito:username']); // Should show 'GitHub_...'
```

---

### Step 7: Documentation Updates

**Update README.md:**
```markdown
## Authentication

Users can sign in using:
- **Google Account**: OAuth 2.0 via Google
- **GitHub Account**: OAuth 2.0 via GitHub

Both providers require email verification and provide secure authentication.
```

**Update AGENTS.md:**
```markdown
### Authentication Flow
1. User clicks "Sign In" → Redirects to Cognito Hosted UI
2. User selects provider (Google or GitHub)
3. Cognito redirects to provider for authentication
4. Provider redirects back with authorization code
5. Frontend exchanges code for JWT tokens
6. Tokens stored in localStorage
7. API requests include JWT in Authorization header
8. Lambda validates JWT using Cognito public keys
```

---

## Configuration Reference

### GitHub OAuth App Settings

**Production:**
```
Client ID: [From GitHub OAuth App]
Client Secret: [From GitHub OAuth App]
Callback URL: https://awseuccontent.auth.us-east-1.amazoncognito.com/oauth2/idpresponse
```

**Staging:**
```
Client ID: [From GitHub OAuth App - Staging]
Client Secret: [From GitHub OAuth App - Staging]
Callback URL: https://staging.awseuccontent.auth.us-east-1.amazoncognito.com/oauth2/idpresponse
```

### Cognito Configuration

**User Pool:**
- ID: `us-east-1_MOvNrTnua`
- Region: `us-east-1`
- Domain: `awseuccontent.auth.us-east-1.amazoncognito.com`

**App Client:**
- ID: `3pv5jf235vj14gu148b9vjt3od`
- Type: Public client
- Auth flows: Authorization code grant

**Identity Providers:**
- Google (existing)
- GitHub (new)

---

## Testing Scenarios

### Test Case 1: New User with GitHub
1. User has never signed in before
2. Clicks "Sign in with GitHub"
3. Authorizes app on GitHub
4. Redirected back to site
5. Profile created with GitHub email
6. Can comment, vote, bookmark

**Expected Result:**
- ✅ User profile created in DynamoDB
- ✅ Email from GitHub stored
- ✅ Display name defaults to GitHub username
- ✅ All features work

### Test Case 2: Existing Google User Tries GitHub
1. User previously signed in with Google
2. Tries to sign in with GitHub using same email
3. Cognito links accounts (if email matches)

**Expected Result:**
- ✅ Same user profile used
- ✅ Can sign in with either provider
- ✅ Data preserved

### Test Case 3: GitHub User with Private Email
1. User has email privacy enabled on GitHub
2. GitHub provides `@users.noreply.github.com` email
3. User signs in

**Expected Result:**
- ✅ Profile created with GitHub proxy email
- ✅ Can still use all features
- ⚠️ Cannot request admin access (not @amazon.com)

### Test Case 4: Amazon Employee with GitHub
1. Amazon employee signs in with GitHub
2. GitHub email is `username@amazon.com`
3. User can request admin access

**Expected Result:**
- ✅ Profile created with @amazon.com email
- ✅ "Request Admin Access" button visible in profile
- ✅ Can submit admin request (Issue #7)

---

## Rollback Procedure

If issues occur:

1. **Disable GitHub Provider in Cognito:**
   - Go to User Pool → Sign-in experience
   - Disable GitHub identity provider
   - Users can still sign in with Google

2. **No Code Changes Needed:**
   - Frontend automatically adapts
   - Only Google button will show

3. **No Data Loss:**
   - Existing users unaffected
   - GitHub users can't sign in until re-enabled

---

## Security Considerations

### Email Verification
- GitHub emails are pre-verified by GitHub
- Cognito trusts GitHub's verification
- No additional email verification needed

### Scopes
- **Minimum**: `user:email` (read email address)
- **Optional**: `read:user` (read profile info)
- **Not Needed**: `repo`, `write:*` (no repository access)

### Token Security
- JWT tokens stored in localStorage
- Tokens expire after 1 hour
- Refresh tokens valid for 30 days
- All API calls require valid token

### Account Linking
- Cognito can link accounts with same email
- User can sign in with either provider
- Single profile in DynamoDB

---

## Monitoring

### CloudWatch Logs
Monitor for authentication errors:
```bash
aws logs tail /aws/lambda/aws-blog-api --follow --filter-pattern "GitHub"
```

### Cognito Metrics
- Sign-in attempts
- Failed authentications
- Provider usage (Google vs GitHub)

### User Feedback
- Monitor for authentication issues
- Check for email capture problems
- Verify profile creation

---

## Success Criteria

- [x] GitHub OAuth app created
- [ ] Cognito configured with GitHub provider
- [ ] Both Google and GitHub buttons visible in Hosted UI
- [ ] Users can sign in with GitHub
- [ ] Email captured from GitHub
- [ ] User profile created correctly
- [ ] All features work (comment, vote, bookmark)
- [ ] Staging environment tested
- [ ] Production environment tested
- [ ] Documentation updated

---

## Next Steps (Issue #7)

After GitHub OAuth is working:
1. Add `role` field to user profiles
2. Add "Request Admin Access" button for @amazon.com users
3. Build admin dashboard
4. Implement admin approval workflow

---

**Issue**: #2  
**Priority**: High  
**Status**: Ready for implementation  
**Estimated Time**: 30-45 minutes  
**Dependencies**: None  
**Blocks**: Issue #7 (Admin Portal)
