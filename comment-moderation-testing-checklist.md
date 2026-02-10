# Comment Moderation Testing Checklist - Staging

## Phase 1: Backend Testing (Lambda) ✅ DEPLOYED

### Deployment Status
- [x] Bedrock IAM permissions added to Lambda role
- [x] Lambda code updated with moderation function
- [x] Lambda deployed to staging ($LATEST)
- [x] Deployment successful

### Manual Testing Required

#### Test 1: Legitimate Technical Comment
**Action**: Submit a normal technical comment about AWS EUC
```
"Great article! I implemented this solution with Amazon WorkSpaces and it worked perfectly. Thanks for sharing!"
```
**Expected Result**:
- ✅ Comment approved immediately
- ✅ `moderation_status`: "approved"
- ✅ Comment visible to all users
- ✅ Included in comment count

**How to Test**:
1. Log in to https://staging.awseuccontent.com
2. Navigate to any blog post
3. Submit the comment above
4. Verify it appears immediately
5. Check DynamoDB for moderation metadata

---

#### Test 2: Spam/Promotional Content
**Action**: Submit promotional spam
```
"Buy cheap AWS credits here! Visit our website for amazing deals on cloud services! http://example.com"
```
**Expected Result**:
- ✅ Comment flagged as `pending_review`
- ✅ `moderation_reason` populated
- ✅ Comment visible only to author (orange styling)
- ✅ "Pending Administrative Review" message shown
- ✅ NOT included in public comment count

**How to Test**:
1. Log in to staging
2. Submit the spam comment
3. Verify you see it with orange styling and warning message
4. Log out or use different browser
5. Verify comment is NOT visible to other users

---

#### Test 3: AWS Documentation Link (Should Approve)
**Action**: Submit comment with AWS docs link
```
"For more details, check out the official docs: https://docs.aws.amazon.com/workspaces/"
```
**Expected Result**:
- ✅ Comment approved (AWS links are allowed)
- ✅ Visible to all users

---

#### Test 4: Multiple Links (Should Flag)
**Action**: Submit comment with 4+ links
```
"Check these out: http://bit.ly/abc http://tinyurl.com/xyz http://example.tk http://test.ml"
```
**Expected Result**:
- ✅ Comment flagged as `pending_review`
- ✅ Reason mentions multiple links or suspicious URLs

---

#### Test 5: Harassment/Profanity
**Action**: Submit abusive comment
```
"This is stupid and you are an idiot for writing this garbage"
```
**Expected Result**:
- ✅ Comment flagged as `pending_review`
- ✅ Reason mentions harassment or inappropriate language

---

#### Test 6: Off-Topic Content
**Action**: Submit completely unrelated comment
```
"Anyone want to buy my used car? Great condition, low mileage!"
```
**Expected Result**:
- ✅ Comment flagged as `pending_review`
- ✅ Reason mentions off-topic content

---

#### Test 7: Technical Criticism (Should Approve)
**Action**: Submit respectful disagreement
```
"I disagree with this approach. Using Lambda would be more cost-effective than EC2 for this use case."
```
**Expected Result**:
- ✅ Comment approved (technical debate is allowed)
- ✅ Visible to all users

---

#### Test 8: Timeout Handling
**Action**: Monitor CloudWatch logs during comment submission
**Expected Result**:
- ✅ If Bedrock takes >2 seconds, comment defaults to "approved"
- ✅ Timeout logged in CloudWatch
- ✅ User experience not impacted

---

#### Test 9: Error Handling
**Action**: Check CloudWatch logs for any Bedrock errors
**Expected Result**:
- ✅ Errors logged with details
- ✅ Comments default to "approved" on error
- ✅ No user-facing errors

---

#### Test 10: Legacy Comments
**Action**: View posts with existing comments (no moderation fields)
**Expected Result**:
- ✅ Old comments display normally
- ✅ No errors in console
- ✅ Treated as "approved"

---

## Phase 2: Frontend Testing (Not Yet Implemented)

### Tasks Remaining:
- [ ] Update `frontend/app.js` to handle moderation status
- [ ] Add CSS styling for pending comments
- [ ] Implement differential display logic
- [ ] Deploy frontend to staging
- [ ] Test end-to-end flow

---

## CloudWatch Monitoring

### Logs to Check:
1. **Lambda Logs** (`/aws/lambda/aws-blog-api`)
   - Look for "Moderation result:" entries
   - Check for timeout warnings
   - Check for Bedrock errors

2. **Metrics to Monitor**:
   - Lambda duration (should be <3 seconds)
   - Error count (should be 0)
   - Invocation count

### How to Check Logs:
```bash
# Get recent logs
aws logs tail /aws/lambda/aws-blog-api --follow --since 5m

# Search for moderation results
aws logs filter-log-events \
  --log-group-name /aws/lambda/aws-blog-api \
  --filter-pattern "Moderation result" \
  --start-time $(date -u -d '5 minutes ago' +%s)000
```

---

## DynamoDB Verification

### Check Comment Structure:
```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('aws-blog-posts-staging')

# Get a post with comments
response = table.get_item(Key={'post_id': '<post-id>'})
comments = response['Item'].get('comments', [])

# Verify moderation fields exist
for comment in comments:
    print(f"Comment ID: {comment['comment_id']}")
    print(f"  Status: {comment.get('moderation_status', 'MISSING')}")
    print(f"  Confidence: {comment.get('moderation_confidence', 'MISSING')}")
    print(f"  Timestamp: {comment.get('moderation_timestamp', 'MISSING')}")
    if comment.get('moderation_reason'):
        print(f"  Reason: {comment['moderation_reason']}")
    print()
```

---

## Success Criteria

### Backend (Current Phase):
- [x] Lambda deployed successfully
- [ ] All 10 test cases pass
- [ ] No errors in CloudWatch logs
- [ ] Moderation completes within 2 seconds
- [ ] Metadata stored correctly in DynamoDB
- [ ] Timeout handling works
- [ ] Error handling works
- [ ] Legacy comments work

### Frontend (Next Phase):
- [ ] Pending comments visible to author only
- [ ] Orange styling applied correctly
- [ ] "Pending Administrative Review" message shown
- [ ] Comment count excludes pending comments
- [ ] No JavaScript errors in console

---

## Issues Found

### Issue Log:
| # | Issue | Severity | Status | Resolution |
|---|-------|----------|--------|------------|
| - | None yet | - | - | - |

---

## Next Steps

1. **Complete Backend Testing** (Current)
   - [ ] Test all 10 scenarios manually in staging
   - [ ] Verify CloudWatch logs
   - [ ] Verify DynamoDB structure
   - [ ] Document any issues

2. **Implement Frontend** (Next)
   - [ ] Update app.js with display logic
   - [ ] Add CSS styling
   - [ ] Deploy to staging
   - [ ] Test end-to-end

3. **Production Deployment** (Final)
   - [ ] Review all test results
   - [ ] Deploy Lambda to production
   - [ ] Deploy frontend to production
   - [ ] Monitor for 24 hours

---

**Created**: 2026-02-10
**Issue**: #22
**Environment**: Staging
**Status**: Backend deployed, awaiting manual testing
