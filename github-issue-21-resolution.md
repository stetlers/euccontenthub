# Issue #21 Resolution: Chat Assistant Fixed

## Summary

The chat assistant is now fully functional on both production and staging environments. The issue was **not** related to Bedrock permissions, but rather a missing API Gateway endpoint configuration in the frontend code.

## Root Cause

The `chat-widget.js` file had a placeholder value for the API endpoint that was never replaced during deployment:

```javascript
const CHAT_API_ENDPOINT = 'API_GATEWAY_URL_HERE';  // ❌ Placeholder
```

This caused all chat requests to fail immediately (before reaching the Lambda), resulting in the instant "Sorry, I encountered an error" message.

## Investigation Steps Taken

1. **Verified Bedrock IAM Permissions** ✅
   - Checked chat Lambda IAM role: `aws-blog-chat-lambda-ChatLambdaExecutionRole-hOjBmpObj2Rv`
   - Confirmed BedrockAccess policy includes Claude Sonnet models:
     - `anthropic.claude-3-haiku-20240307-v1:0`
     - `anthropic.claude-3-sonnet-20240229-v1:0`
     - `anthropic.claude-sonnet-3-5-20241022-v2:0`
     - `anthropic.claude-3-5-sonnet-20240620-v1:0`
   - Permissions were already correct

2. **Verified API Gateway Configuration** ✅
   - Confirmed `/chat` endpoint exists (resource ID: wyie3h)
   - Verified Lambda integration is correct
   - API Gateway was properly configured

3. **Checked CloudWatch Logs** ✅
   - No recent logs found
   - Indicated Lambda was never being invoked
   - Confirmed issue was on frontend side

4. **Identified Frontend Issue** ❌
   - Downloaded production `chat-widget.js` from S3
   - Found placeholder `'API_GATEWAY_URL_HERE'` instead of actual endpoint
   - This caused immediate fetch failures

## Fix Applied

### Production Environment

**File**: `frontend/chat-widget.js`

**Change**:
```javascript
// Before
const CHAT_API_ENDPOINT = 'API_GATEWAY_URL_HERE';

// After
const CHAT_API_ENDPOINT = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod';
```

**Deployment**:
```bash
aws s3 cp frontend/chat-widget.js s3://aws-blog-viewer-031421429609/chat-widget.js \
  --content-type "application/javascript"

aws cloudfront create-invalidation --distribution-id E20CC1TSSWTCWN \
  --paths "/chat-widget.js"
```

### Staging Environment

**File**: `frontend/chat-widget-staging.js`

**Change**:
```javascript
const CHAT_API_ENDPOINT = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging';
```

**Additional Issue Found**: UTF-8 Encoding Corruption
- Initial deployment using PowerShell string manipulation corrupted emoji characters
- Chat button emoji displayed as `ðŸ'¬` instead of `💬`
- Fixed by creating file with proper UTF-8 encoding using fsWrite/fsAppend

**Deployment**:
```bash
aws s3 cp frontend/chat-widget-staging.js s3://aws-blog-viewer-staging-031421429609/chat-widget.js \
  --content-type "application/javascript" --metadata-directive REPLACE

aws cloudfront create-invalidation --distribution-id E1IB9VDMV64CQA \
  --paths "/chat-widget.js"
```

## Verification

### Production (https://awseuccontent.com)
- ✅ Chat button displays correct emoji (💬)
- ✅ Chat widget opens when clicked
- ✅ User can send messages
- ✅ AI responds with relevant content recommendations
- ✅ No console errors
- ✅ API calls reach Lambda successfully

### Staging (https://staging.awseuccontent.com)
- ✅ Chat button displays correct emoji (💬)
- ✅ Chat widget opens when clicked
- ✅ User can send messages
- ✅ AI responds with relevant content recommendations
- ✅ No console errors
- ✅ API calls reach staging Lambda successfully
- ✅ UTF-8 encoding preserved

## Files Modified

1. `frontend/chat-widget.js` - Production version with `/prod` endpoint
2. `frontend/chat-widget-staging.js` - Staging version with `/staging` endpoint (new file)

## Lessons Learned

1. **Deployment Scripts Need Validation**: The deployment process should validate that placeholder values are replaced
2. **Test Both Environments**: Always verify fixes work in both staging and production
3. **UTF-8 Encoding Matters**: PowerShell string manipulation can corrupt UTF-8 characters; use proper file operations
4. **Check Frontend First**: Instant errors often indicate frontend issues, not backend
5. **CloudWatch Logs Are Diagnostic**: No logs = Lambda not invoked = frontend issue

## Recommendations

1. **Update Deployment Scripts**: Add validation to ensure API endpoints are not placeholders
2. **Add Pre-Deployment Checks**: Script should verify critical configuration values before upload
3. **Document Encoding Requirements**: Note that emoji/UTF-8 files need special handling in PowerShell
4. **Create Separate Files**: Maintain separate production and staging versions to avoid encoding issues

## Related Components

- **Lambda**: aws-blog-chat-assistant (no changes needed)
- **API Gateway**: xox05733ce (no changes needed)
- **Bedrock**: IAM permissions were already correct
- **Frontend**: chat-widget.js (fixed in both environments)
- **S3 Buckets**: 
  - Production: `aws-blog-viewer-031421429609`
  - Staging: `aws-blog-viewer-staging-031421429609`
- **CloudFront Distributions**:
  - Production: E20CC1TSSWTCWN
  - Staging: E1IB9VDMV64CQA

## Status

✅ **RESOLVED** - Chat assistant is fully functional in both production and staging environments.

---

**Resolved**: February 9, 2026  
**Resolution Time**: ~30 minutes  
**Environments Fixed**: Production + Staging
