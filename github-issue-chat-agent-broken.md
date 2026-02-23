# Chat Agent Not Working - Investigation Needed

## Issue Description

The chat assistant widget on the EUC Content Hub website appears to be broken and not responding to user queries.

## Environment

- **Affected Sites**: 
  - Production: https://awseuccontent.com
  - Staging: https://staging.awseuccontent.com (needs verification)
- **Component**: Chat widget (bottom right corner of website)
- **Lambda Function**: `aws-blog-chat-assistant`
- **API Endpoint**: `/chat`

## Observed Behavior

**What's Happening:**
- Chat widget is visible on the site
- User can type messages
- Messages are not being processed/responded to
- No response from AI assistant

**Expected Behavior:**
- User types a question about EUC content
- Chat assistant responds with relevant information
- Assistant can recommend posts from the database
- Streaming responses should appear in real-time

## Potential Causes to Investigate

### 1. Lambda Function Issues
- [ ] Check if Lambda function is deployed correctly
- [ ] Verify Lambda has correct handler configuration
- [ ] Check Lambda timeout settings (should be sufficient for Bedrock calls)
- [ ] Verify Lambda has necessary IAM permissions for Bedrock

### 2. API Gateway Configuration
- [ ] Verify `/chat` endpoint exists in API Gateway
- [ ] Check CORS configuration for chat endpoint
- [ ] Verify API Gateway integration with Lambda
- [ ] Check if endpoint is deployed to both prod and staging stages

### 3. Frontend Issues
- [ ] Check browser console for JavaScript errors
- [ ] Verify chat widget is making API calls
- [ ] Check if API endpoint URL is correct in `chat-widget.js`
- [ ] Verify request/response format matches Lambda expectations

### 4. IAM Permissions
- [ ] Lambda needs `bedrock:InvokeModel` permission for Claude Sonnet
- [ ] Lambda needs DynamoDB read access for post database
- [ ] Check if IAM role has all required permissions

### 5. Bedrock Configuration
- [ ] Verify Bedrock model access (Claude Sonnet)
- [ ] Check if model ID is correct in Lambda code
- [ ] Verify region configuration (us-east-1)
- [ ] Check if Bedrock service is enabled in account

## Diagnostic Steps

### Step 1: Check CloudWatch Logs

```bash
# Check recent chat Lambda logs
aws logs tail /aws/lambda/aws-blog-chat-assistant --since 1h --follow

# Look for errors
aws logs tail /aws/lambda/aws-blog-chat-assistant --since 1h --filter-pattern "ERROR"
```

### Step 2: Test API Endpoint Directly

```bash
# Test production endpoint
curl -X POST https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Amazon WorkSpaces?"}'

# Test staging endpoint
curl -X POST https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Amazon WorkSpaces?"}'
```

### Step 3: Check Lambda Configuration

```bash
# Get Lambda function details
aws lambda get-function --function-name aws-blog-chat-assistant

# Check IAM role permissions
aws lambda get-function-configuration --function-name aws-blog-chat-assistant
```

### Step 4: Check Browser Console

1. Open browser developer tools (F12)
2. Go to Console tab
3. Click chat widget and send a message
4. Look for:
   - JavaScript errors
   - Failed network requests
   - CORS errors
   - API response errors

### Step 5: Check API Gateway

```bash
# List API Gateway resources
aws apigateway get-resources --rest-api-id xox05733ce

# Check if /chat endpoint exists
aws apigateway get-resources --rest-api-id xox05733ce | grep -i chat
```

## Files to Review

- `frontend/chat-widget.js` - Frontend chat widget code
- `chat_lambda.py` - Lambda function for chat assistant
- `lambda_api/lambda_function.py` - API Gateway handler (check /chat route)

## Expected Lambda Response Format

The chat Lambda should return:

```json
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*"
  },
  "body": "{\"response\": \"AI assistant response text here\"}"
}
```

## Common Issues and Solutions

### Issue: "Internal Server Error" (500)
**Possible Causes:**
- Lambda function error
- Bedrock API error
- Missing IAM permissions
- Timeout

**Solution:**
- Check CloudWatch logs for error details
- Verify Bedrock permissions
- Increase Lambda timeout if needed

### Issue: CORS Error
**Possible Causes:**
- Missing CORS headers in Lambda response
- API Gateway CORS not configured

**Solution:**
- Add CORS headers to Lambda response
- Enable CORS in API Gateway for /chat endpoint

### Issue: "Function Not Found"
**Possible Causes:**
- Lambda function not deployed
- Wrong function name in API Gateway integration

**Solution:**
- Verify Lambda function exists
- Check API Gateway integration configuration

### Issue: No Response / Timeout
**Possible Causes:**
- Lambda timeout too short for Bedrock calls
- Bedrock model not responding
- Network issues

**Solution:**
- Increase Lambda timeout to 30-60 seconds
- Check Bedrock service status
- Verify network connectivity

## Testing Checklist

Once fixed, verify:
- [ ] Chat widget opens when clicked
- [ ] User can type messages
- [ ] AI responds to questions
- [ ] Responses are relevant and accurate
- [ ] Streaming works (if implemented)
- [ ] No console errors
- [ ] Works in both production and staging
- [ ] Works on mobile devices
- [ ] CORS headers present
- [ ] Response time is acceptable (< 10 seconds)

## Related Components

- **Lambda**: aws-blog-chat-assistant
- **API Gateway**: xox05733ce (REST API)
- **Bedrock Model**: Claude Sonnet (anthropic.claude-sonnet-3-5-20241022-v2:0 or similar)
- **DynamoDB**: aws-blog-posts (for context retrieval)
- **Frontend**: chat-widget.js, chat-widget.css

## Priority

**Medium-High** - Chat assistant is a key feature for content discovery, but site is functional without it.

## Labels

- `bug`
- `chat-assistant`
- `needs-investigation`
- `lambda`
- `bedrock`

## Acceptance Criteria

- [ ] Chat widget responds to user messages
- [ ] AI provides relevant answers about EUC content
- [ ] No errors in browser console
- [ ] No errors in CloudWatch logs
- [ ] Response time is acceptable (< 10 seconds)
- [ ] Works in both production and staging
- [ ] CORS configured correctly
- [ ] Tested on desktop and mobile

## Additional Notes

- Last known working state: Unknown (needs verification)
- Recent changes: None directly to chat Lambda (verify)
- May be related to IAM policy changes or API Gateway configuration
- Check if issue exists in both staging and production

## Next Steps

1. Run diagnostic steps above
2. Check CloudWatch logs for errors
3. Test API endpoint directly
4. Review Lambda code and configuration
5. Verify IAM permissions
6. Fix identified issues
7. Test thoroughly in staging
8. Deploy fix to production
9. Verify chat works end-to-end

---

**Reported**: February 9, 2026  
**Reporter**: User demonstration  
**Status**: Open - Needs Investigation
