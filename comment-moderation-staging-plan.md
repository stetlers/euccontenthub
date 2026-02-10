# Comment Moderation AI - Staging Rollout Plan

## Issue: #22 - AI-Powered Comment Moderation System

## Overview

This document outlines the step-by-step plan for implementing and testing the comment moderation system in the staging environment before production deployment.

---

## Phase 1: Backend Implementation (Lambda)

### Task 1.1: Set up Bedrock Client Infrastructure
**File**: `lambda_api/lambda_function.py`

**Changes**:
- Import boto3 Bedrock Runtime client
- Add timeout mechanism (using threading.Timer for Lambda compatibility)
- Create `moderate_comment()` function skeleton
- Add error handling that defaults to 'approved'

**Testing**:
- Unit test: Verify function returns proper structure
- Unit test: Verify timeout mechanism works
- Unit test: Verify error handling defaults to approved

**Estimated Time**: 1 hour

---

### Task 1.2: Implement Moderation Prompt
**File**: `lambda_api/lambda_function.py`

**Changes**:
- Create structured prompt template with evaluation criteria
- Include post context (title, tags) in prompt
- Implement JSON response parsing
- Handle malformed JSON gracefully
- Validate confidence scores (0.0 to 1.0)

**Testing**:
- Unit test: Spam detection (promotional content, multiple links)
- Unit test: Dangerous link detection (IP addresses, URL shorteners, suspicious TLDs)
- Unit test: Harassment detection (profanity, threats, personal attacks)
- Unit test: Off-topic detection (unrelated content)
- Unit test: Legitimate content approval (technical discussions, AWS links)

**Estimated Time**: 2 hours

---

### Task 1.3: Integrate Moderation into Comment Submission
**File**: `lambda_api/lambda_function.py`

**Changes**:
- Modify `add_comment()` function to call `moderate_comment()`
- Fetch post context before moderation
- Add moderation metadata to comment object:
  - `moderation_status`: 'approved' | 'pending_review'
  - `moderation_reason`: string (if flagged)
  - `moderation_confidence`: float (0.0 to 1.0)
  - `moderation_timestamp`: ISO 8601 timestamp
- Handle moderation errors gracefully

**Testing**:
- Unit test: Verify moderation is called before storage
- Unit test: Verify metadata is added to comment
- Unit test: Verify error handling works
- Property test: Moderation precedes storage (Property 2)
- Property test: Flagged comments include reason (Property 3)

**Estimated Time**: 1.5 hours

---

### Task 1.4: Update IAM Permissions
**Action**: Add Bedrock permissions to API Lambda role

**Required Permission**:
```json
{
  "Effect": "Allow",
  "Action": "bedrock:InvokeModel",
  "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
}
```

**Testing**:
- Verify Lambda can invoke Bedrock in staging
- Check CloudWatch logs for permission errors

**Estimated Time**: 30 minutes

---

### Task 1.5: Deploy Lambda to Staging
**Script**: `python deploy_lambda.py api_lambda staging`

**Verification**:
- Check Lambda version updated
- Verify staging alias points to $LATEST
- Test API endpoint: `https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/posts`

**Estimated Time**: 15 minutes

---

### Checkpoint 1: Test Backend in Staging

**Test Cases**:
1. Submit legitimate technical comment → Verify approved
2. Submit spam comment → Verify flagged
3. Submit comment with 4+ links → Verify flagged
4. Submit comment with suspicious URL → Verify flagged
5. Submit comment with profanity → Verify flagged
6. Check DynamoDB for moderation metadata
7. Check CloudWatch logs for errors
8. Verify timeout handling (mock slow response)

**Success Criteria**:
- All test cases pass
- No errors in CloudWatch logs
- Moderation completes within 2 seconds
- Metadata stored correctly in DynamoDB

**Estimated Time**: 1 hour

---

## Phase 2: Backend Comment Filtering

### Task 2.1: Implement Comment Filtering Logic
**File**: `lambda_api/lambda_function.py`

**Changes**:
- Modify `get_comments()` or equivalent endpoint
- Extract current user ID from JWT token (if authenticated)
- Filter comments:
  - Show all 'approved' comments to everyone
  - Show 'pending_review' comments only to author
  - Hide 'rejected' comments (future)
- Handle legacy comments without moderation_status (treat as approved)
- Update comment count to exclude pending comments

**Testing**:
- Unit test: Verify filtering logic for authenticated user
- Unit test: Verify filtering logic for unauthenticated user
- Unit test: Verify legacy comment handling
- Property test: Comment filtering by viewer identity (Property 4)
- Property test: Public comment count accuracy (Property 6)
- Property test: Legacy comment compatibility (Property 9)

**Estimated Time**: 1.5 hours

---

### Task 2.2: Deploy Lambda to Staging
**Script**: `python deploy_lambda.py api_lambda staging`

**Verification**:
- Test GET /posts endpoint
- Verify comments are filtered correctly
- Check as different users (author vs. other users)

**Estimated Time**: 15 minutes

---

### Checkpoint 2: Test Comment Filtering in Staging

**Test Cases**:
1. Create pending comment as User A
2. View comments as User A → Verify pending comment visible
3. View comments as User B → Verify pending comment hidden
4. View comments as unauthenticated → Verify pending comment hidden
5. Check comment count excludes pending comments
6. Test with legacy comments (no moderation_status)

**Success Criteria**:
- Filtering works correctly for all user types
- Comment counts are accurate
- Legacy comments display correctly
- No errors in CloudWatch logs

**Estimated Time**: 45 minutes

---

## Phase 3: Frontend Implementation

### Task 3.1: Implement Frontend Display Logic
**File**: `frontend/app.js`

**Changes**:
- Modify `renderComment()` function (or equivalent)
- Detect pending comments for current user
- Add CSS classes for pending comment styling
- Add "Pending Administrative Review" message
- Update comment count display to use filtered count from API

**Testing**:
- Manual test: View as comment author
- Manual test: View as different user
- Manual test: Check visual styling
- Property test: Pending comment visual distinction (Property 5)

**Estimated Time**: 1.5 hours

---

### Task 3.2: Add CSS Styling
**File**: `frontend/styles.css`

**Changes**:
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

**Testing**:
- Visual inspection in staging
- Test on desktop and mobile
- Verify colors are accessible

**Estimated Time**: 30 minutes

---

### Task 3.3: Deploy Frontend to Staging
**Script**: `python deploy_frontend.py staging`

**Verification**:
- Visit https://staging.awseuccontent.com
- Check browser console for errors
- Verify CloudFront cache invalidated

**Estimated Time**: 15 minutes

---

### Checkpoint 3: End-to-End Testing in Staging

**Test Scenarios**:

1. **Legitimate Comment Flow**:
   - Submit technical comment about AWS EUC
   - Verify approved immediately
   - Verify visible to all users
   - Verify included in comment count

2. **Spam Comment Flow**:
   - Submit promotional comment
   - Verify flagged as pending
   - Verify visible only to author with orange styling
   - Verify "Pending Administrative Review" message
   - Verify not included in public comment count
   - Log in as different user → Verify comment hidden

3. **Dangerous Link Flow**:
   - Submit comment with suspicious URL
   - Verify flagged as pending
   - Verify differential display works

4. **Harassment Flow**:
   - Submit comment with profanity
   - Verify flagged as pending
   - Verify differential display works

5. **Off-Topic Flow**:
   - Submit completely unrelated comment
   - Verify flagged as pending
   - Verify differential display works

6. **Edge Cases**:
   - Submit comment with AWS documentation link → Verify approved
   - Submit comment with 3 links → Verify approved
   - Submit comment with 4 links → Verify flagged
   - Submit technical criticism → Verify approved
   - Test timeout scenario (if possible)
   - Test error scenario (if possible)

7. **Legacy Comments**:
   - View posts with existing comments (no moderation fields)
   - Verify they display normally
   - Verify no errors

**Success Criteria**:
- All test scenarios pass
- Visual styling looks good
- No JavaScript errors in console
- No errors in CloudWatch logs
- Performance is acceptable (<2 seconds for comment submission)

**Estimated Time**: 2 hours

---

## Phase 4: Monitoring and Documentation

### Task 4.1: Add CloudWatch Monitoring
**File**: `lambda_api/lambda_function.py`

**Changes**:
- Add custom CloudWatch metrics:
  - `ModerationLatency`: Time taken for analysis
  - `ModerationTimeouts`: Count of timeouts
  - `ModerationErrors`: Count of errors
  - `FlaggedComments`: Count of flagged comments
  - `ApprovedComments`: Count of approved comments
- Log moderation results (without comment text)
- Log timeouts and errors with comment_id

**Testing**:
- Verify metrics appear in CloudWatch
- Verify logs are structured correctly
- Verify no PII in logs

**Estimated Time**: 1 hour

---

### Task 4.2: Update Documentation
**Files**: `README.md`, `AGENTS.md`

**Changes**:
- Document moderation system behavior
- Update API documentation with new comment fields
- Add troubleshooting section
- Document monitoring and metrics

**Estimated Time**: 30 minutes

---

### Checkpoint 4: Final Staging Validation

**Validation Checklist**:
- [ ] All unit tests pass
- [ ] All property tests pass (100+ iterations each)
- [ ] All integration tests pass
- [ ] All manual test scenarios pass
- [ ] CloudWatch metrics working
- [ ] CloudWatch logs structured correctly
- [ ] No errors in staging environment
- [ ] Performance acceptable (<2 seconds)
- [ ] Visual styling looks good
- [ ] Documentation updated
- [ ] Rollback plan tested

**Estimated Time**: 1 hour

---

## Phase 5: Production Deployment (After Staging Success)

### Task 5.1: Deploy Lambda to Production
**Script**: `python deploy_lambda.py api_lambda production`

**Steps**:
1. Create new Lambda version
2. Update production alias to new version
3. Verify production endpoint works
4. Monitor CloudWatch logs for 15 minutes

**Rollback**: Update alias to previous version if issues occur

**Estimated Time**: 30 minutes

---

### Task 5.2: Deploy Frontend to Production
**Script**: `python deploy_frontend.py production`

**Steps**:
1. Deploy to S3 bucket: `aws-blog-viewer-031421429609`
2. Invalidate CloudFront cache: `E20CC1TSSWTCWN`
3. Verify https://awseuccontent.com loads correctly
4. Test comment submission and display

**Rollback**: Git revert and redeploy if issues occur (2-3 minutes)

**Estimated Time**: 30 minutes

---

### Task 5.3: Monitor Production
**Duration**: 24 hours

**Monitoring**:
- Watch CloudWatch metrics for anomalies
- Check error rates
- Monitor timeout rates
- Watch for user reports
- Check comment submission rates

**Success Criteria**:
- Error rate < 1%
- Timeout rate < 5%
- No user complaints
- Comment submission working smoothly

**Estimated Time**: Ongoing monitoring

---

## Total Estimated Time

- **Phase 1 (Backend)**: 5 hours
- **Phase 2 (Filtering)**: 2.5 hours
- **Phase 3 (Frontend)**: 4 hours
- **Phase 4 (Monitoring)**: 1.5 hours
- **Phase 5 (Production)**: 1 hour
- **Total**: 14 hours

---

## Risk Mitigation

### Risk 1: Bedrock API Latency
**Mitigation**: 2-second timeout with default to approved

### Risk 2: Too Many False Positives
**Mitigation**: 
- Tune prompt in staging
- Prefer false negatives over false positives
- Can adjust prompt in production if needed

### Risk 3: Bedrock API Errors
**Mitigation**: Default to approved, log errors, monitor CloudWatch

### Risk 4: User Confusion
**Mitigation**: Clear "Pending Administrative Review" message with distinct styling

### Risk 5: Performance Impact
**Mitigation**: 
- Use fast Claude Haiku model
- 2-second timeout
- Async processing if needed (future)

---

## Rollback Procedures

### Lambda Rollback (Instant)
```bash
aws lambda update-alias \
  --function-name aws-blog-api \
  --name staging \
  --function-version <previous-version>
```

### Frontend Rollback (2-3 minutes)
```bash
git revert <commit-hash>
python deploy_frontend.py staging
```

---

## Success Metrics

After 1 week in production:
- [ ] Comment submission rate unchanged or increased
- [ ] Spam comments reduced by >80%
- [ ] Dangerous links blocked
- [ ] Harassment incidents reduced
- [ ] User satisfaction maintained or improved
- [ ] Error rate < 1%
- [ ] Timeout rate < 5%
- [ ] Average moderation latency < 1 second

---

## Next Steps After Production

1. Monitor metrics for 1 week
2. Gather user feedback
3. Tune moderation prompt if needed
4. Plan admin review interface (future enhancement)
5. Consider batch moderation for existing comments

---

**Created**: 2026-02-10
**Issue**: #22
**Status**: Ready for implementation
