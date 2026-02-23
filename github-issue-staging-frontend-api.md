# Staging Frontend Uses Production API Endpoint

## Problem Statement

The staging frontend (https://staging.awseuccontent.com) is hardcoded to use the **production API endpoint**, which defeats the purpose of having a staging environment. This means:

1. **Staging site triggers production Lambda functions** - Not staging versions
2. **Staging site reads/writes production data** - No data isolation
3. **Cannot test backend changes in staging** - Frontend always hits production
4. **Staging environment is incomplete** - Only frontend files are isolated, not the full stack

## Current Behavior

### Staging Frontend Configuration
**File**: `frontend/app.js` (line 2)
```javascript
const API_ENDPOINT = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod';
```

**Result**:
- Staging site → `/prod` API → Production Lambda → Production DynamoDB
- User clicks "Crawl for New Posts" on staging → Triggers production crawler
- All API calls from staging hit production backend

### Expected Behavior

**Staging should use staging API:**
```javascript
const API_ENDPOINT = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging';
```

**Result**:
- Staging site → `/staging` API → Staging Lambda → Staging DynamoDB
- Complete isolation from production
- Safe testing of full stack changes

## Impact

### Current Issues
1. **No true staging environment** - Backend is still production
2. **Cannot test Lambda changes** - Staging frontend triggers production Lambdas
3. **Data isolation broken** - Staging reads/writes production data
4. **Risk of production impact** - Staging actions affect production users
5. **Misleading testing** - Think you're testing staging, but hitting production

### Example Scenario (What Just Happened)
1. User visits https://staging.awseuccontent.com
2. User clicks "Crawl for New Posts" button
3. Frontend calls `${API_ENDPOINT}/crawl` = `/prod/crawl`
4. **Production crawler runs** (not staging crawler)
5. Production data potentially affected
6. Staging crawler never tested

## Root Cause

### Hardcoded API Endpoint
The `API_ENDPOINT` constant is hardcoded in `frontend/app.js` and not environment-aware.

**Files Affected:**
- `frontend/app.js` - Main API endpoint
- `frontend/auth.js` - Fallback to prod endpoint
- `frontend/chat-widget.js` - Chat API endpoint
- `frontend/profile.js` - Uses API_ENDPOINT from app.js

### Deployment Script Issue
The `deploy_frontend.py` script deploys files as-is without modifying the API endpoint based on environment.

## Proposed Solution

### Option 1: Environment-Specific Deployment (Recommended)

**Approach**: Modify `deploy_frontend.py` to replace API endpoint during deployment

**Implementation**:
```python
def deploy_frontend(environment='production'):
    # Determine API endpoint based on environment
    if environment == 'production':
        api_endpoint = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod'
        bucket = 'aws-blog-viewer-031421429609'
        distribution_id = 'E20CC1TSSWTCWN'
    elif environment == 'staging':
        api_endpoint = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'
        bucket = 'aws-blog-viewer-staging-031421429609'
        distribution_id = 'E1IB9VDMV64CQA'
    
    # Read app.js and replace API endpoint
    with open('frontend/app.js', 'r') as f:
        content = f.read()
    
    # Replace API endpoint
    content = re.sub(
        r"const API_ENDPOINT = '[^']+';",
        f"const API_ENDPOINT = '{api_endpoint}';",
        content
    )
    
    # Upload modified content
    s3.put_object(
        Bucket=bucket,
        Key='app.js',
        Body=content,
        ContentType='application/javascript'
    )
```

**Pros**:
- ✅ Clean separation of environments
- ✅ No runtime detection needed
- ✅ Works with existing code structure
- ✅ Easy to implement and maintain

**Cons**:
- ❌ Requires deployment script modification
- ❌ Source file remains with prod endpoint (could be confusing)

---

### Option 2: Runtime Environment Detection

**Approach**: Detect environment at runtime based on hostname

**Implementation**:
```javascript
// Detect environment from hostname
const isStaging = window.location.hostname === 'staging.awseuccontent.com';
const API_ENDPOINT = isStaging 
    ? 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'
    : 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod';

console.log(`Environment: ${isStaging ? 'STAGING' : 'PRODUCTION'}`);
console.log(`API Endpoint: ${API_ENDPOINT}`);
```

**Pros**:
- ✅ No deployment script changes needed
- ✅ Self-documenting (clear in source code)
- ✅ Works automatically based on domain
- ✅ Easy to understand and maintain

**Cons**:
- ❌ Requires frontend code change
- ❌ Relies on hostname detection

---

### Option 3: Configuration File

**Approach**: Use separate config files for staging/production

**Implementation**:
```javascript
// config.js (deployed differently per environment)
const CONFIG = {
    apiEndpoint: 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging',
    environment: 'staging'
};
```

**Pros**:
- ✅ Clean separation
- ✅ Easy to modify per environment
- ✅ Can include other environment-specific settings

**Cons**:
- ❌ Additional file to manage
- ❌ Deployment script must handle config file

---

## Recommendation

**Option 2 (Runtime Environment Detection)** because:

1. **Simple** - One code change, no deployment script changes
2. **Automatic** - Works based on domain name
3. **Clear** - Easy to see what's happening in browser console
4. **Maintainable** - No special deployment logic needed
5. **Future-proof** - Works for any new environments (dev, qa, etc.)

## Implementation Plan

### Step 1: Update Frontend Code

**File**: `frontend/app.js`

**Change**:
```javascript
// OLD (line 2):
const API_ENDPOINT = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod';

// NEW:
// Detect environment from hostname
const isStaging = window.location.hostname === 'staging.awseuccontent.com';
const API_ENDPOINT = isStaging 
    ? 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'
    : 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod';

console.log(`🌍 Environment: ${isStaging ? 'STAGING' : 'PRODUCTION'}`);
console.log(`🔗 API Endpoint: ${API_ENDPOINT}`);
```

### Step 2: Update Chat Widget (if needed)

**File**: `frontend/chat-widget.js`

Check if chat widget needs similar update for chat API endpoint.

### Step 3: Deploy to Staging

```bash
python deploy_frontend.py staging
```

### Step 4: Verify

1. Visit https://staging.awseuccontent.com
2. Open browser console
3. Look for: "🌍 Environment: STAGING"
4. Look for: "🔗 API Endpoint: .../staging"
5. Test API calls (load posts, trigger crawler)

### Step 5: Deploy to Production

```bash
python deploy_frontend.py production
```

### Step 6: Verify Production

1. Visit https://awseuccontent.com
2. Open browser console
3. Look for: "🌍 Environment: PRODUCTION"
4. Look for: "🔗 API Endpoint: .../prod"

---

## Testing Checklist

### Staging Environment
- [ ] Staging frontend detects staging hostname
- [ ] API_ENDPOINT points to `/staging`
- [ ] Posts load from staging API (50 posts)
- [ ] Crawler button triggers staging crawler
- [ ] All API calls go to staging backend
- [ ] Browser console shows "Environment: STAGING"

### Production Environment
- [ ] Production frontend detects production hostname
- [ ] API_ENDPOINT points to `/prod`
- [ ] Posts load from production API (479 posts)
- [ ] Crawler button triggers production crawler
- [ ] All API calls go to production backend
- [ ] Browser console shows "Environment: PRODUCTION"

---

## Success Criteria

- [ ] Staging frontend uses staging API endpoint
- [ ] Production frontend uses production API endpoint
- [ ] Environment detection works automatically
- [ ] No manual configuration needed
- [ ] Browser console shows correct environment
- [ ] Complete data isolation achieved

---

## Related Issues

- **Blocks**: #20 (Builder Crawler Fix) - Cannot test in staging without proper API routing
- **Related to**: #1 (Blue-Green Deployment) - Completes the staging environment
- **Related to**: #19 (Crawler Staging Support) - Enables testing of crawler changes

---

## Priority

**CRITICAL** - Without this fix:
- Staging environment is incomplete
- Cannot safely test backend changes
- Risk of production impact from staging actions
- Blue-green deployment strategy is ineffective

---

## Labels

- bug
- critical
- staging
- frontend
- deployment

---

**Status**: Ready for implementation  
**Recommended Solution**: Option 2 (Runtime Environment Detection)  
**Estimated Time**: 30 minutes (change + deploy + test)  
**Risk**: Low (simple change, easy to verify)
