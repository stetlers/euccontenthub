# Fix Cognito Authentication for Staging Environment

## Priority: High

## Problem Statement

When users attempt to authenticate on the staging environment (https://staging.awseuccontent.com), they are redirected back to the production site (https://awseuccontent.com) after successful login. This prevents testing of authenticated features in staging, including:

- Comment submission (requires authentication)
- Profile management
- Bookmarking posts
- Voting on posts
- Any other authenticated endpoints

## Root Cause

The Cognito User Pool is only configured with production callback URLs. When a user logs in via staging, Cognito doesn't recognize `https://staging.awseuccontent.com` as a valid callback URL and defaults to the production URL.

**Current Cognito Configuration**:
- User Pool ID: `us-east-1_MOvNrTnua`
- App Client ID: `3pv5jf235vj14gu148b9vjt3od`
- Callback URLs: Only production (`https://awseuccontent.com`)
- Sign-out URLs: Only production

## Impact

**Severity**: High - Blocks all staging testing of authenticated features

**Affected Features**:
- ❌ Cannot test comment moderation system (Issue #22)
- ❌ Cannot test profile updates
- ❌ Cannot test bookmarks
- ❌ Cannot test voting
- ❌ Cannot verify authenticated API endpoints

**Workaround**: None - authentication is required for these features

## Proposed Solution

Update Cognito User Pool App Client to include staging callback URLs:

### 1. Add Staging Callback URLs

**Current**:
```
https://awseuccontent.com
```

**Updated**:
```
https://awseuccontent.com
https://staging.awseuccontent.com
```

### 2. Add Staging Sign-out URLs

**Current**:
```
https://awseuccontent.com
```

**Updated**:
```
https://awseuccontent.com
https://staging.awseuccontent.com
```

### 3. Update Frontend Auth Configuration (if needed)

Check if `frontend/auth.js` needs environment-aware redirect URLs.

## Implementation Steps

### Step 1: Update Cognito App Client Settings

```bash
# Get current app client configuration
aws cognito-idp describe-user-pool-client \
  --user-pool-id us-east-1_MOvNrTnua \
  --client-id 3pv5jf235vj14gu148b9vjt3od

# Update callback URLs
aws cognito-idp update-user-pool-client \
  --user-pool-id us-east-1_MOvNrTnua \
  --client-id 3pv5jf235vj14gu148b9vjt3od \
  --callback-urls "https://awseuccontent.com" "https://staging.awseuccontent.com" \
  --logout-urls "https://awseuccontent.com" "https://staging.awseuccontent.com"
```

### Step 2: Verify Configuration

1. Check Cognito console to confirm URLs are updated
2. Test login flow on staging
3. Verify redirect to staging after authentication
4. Test logout flow

### Step 3: Test Authenticated Features

Once authentication works:
- [ ] Test comment submission
- [ ] Test profile updates
- [ ] Test bookmarks
- [ ] Test voting
- [ ] Verify JWT tokens work with staging API

## Testing Checklist

- [ ] Login on staging redirects back to staging (not production)
- [ ] Logout on staging works correctly
- [ ] JWT token is valid for staging API endpoints
- [ ] Can submit comments on staging
- [ ] Can update profile on staging
- [ ] Can bookmark posts on staging
- [ ] Can vote on posts on staging
- [ ] Production authentication still works (no regression)

## Success Criteria

- [ ] Users can authenticate on staging environment
- [ ] After login, users remain on staging (not redirected to production)
- [ ] All authenticated features work on staging
- [ ] Production authentication unaffected
- [ ] Comment moderation testing can proceed (Issue #22)

## Dependencies

**Blocks**:
- Issue #22 - AI-Powered Comment Moderation System (cannot test without auth)

**Related**:
- Issue #1 - Blue-Green Deployment (staging environment setup)

## Estimated Effort

- **Configuration Update**: 15 minutes
- **Testing**: 30 minutes
- **Total**: 45 minutes

## Notes

- This is a configuration-only change (no code changes required)
- Should have been part of initial staging environment setup (Issue #1)
- Quick fix that unblocks critical testing
- No risk to production (only adding staging URLs)

## Rollback Plan

If issues occur, remove staging URLs from Cognito:

```bash
aws cognito-idp update-user-pool-client \
  --user-pool-id us-east-1_MOvNrTnua \
  --client-id 3pv5jf235vj14gu148b9vjt3od \
  --callback-urls "https://awseuccontent.com" \
  --logout-urls "https://awseuccontent.com"
```

## Additional Considerations

### Option 1: Shared Cognito (Recommended)
- Use same User Pool for both environments
- Add staging URLs to callback/logout lists
- **Pros**: Simple, users can test with real accounts
- **Cons**: Staging and production share user data

### Option 2: Separate Cognito User Pool
- Create dedicated User Pool for staging
- Update staging frontend to use staging User Pool
- **Pros**: Complete isolation
- **Cons**: More complex, requires code changes, separate user accounts

**Recommendation**: Use Option 1 (shared Cognito) for simplicity and faster testing.
