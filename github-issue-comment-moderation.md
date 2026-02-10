# AI-Powered Comment Moderation System

## Priority: High

## Overview

Implement an automated comment moderation system using AWS Bedrock (Claude Haiku) to analyze comments in real-time and flag inappropriate content for administrative review. This ensures a safe, on-topic community environment while maintaining transparency with comment authors.

## Problem Statement

Currently, the EUC Content Hub has no automated moderation for user comments. This creates risk of:
- Spam and promotional content cluttering discussions
- Dangerous links exposing users to malicious websites
- Harassment or abusive content harming community members
- Off-topic content diluting the focus on AWS EUC services

Manual moderation is not scalable and creates delays in content visibility.

## Proposed Solution

Integrate AWS Bedrock (Claude Haiku) into the comment submission flow to automatically analyze content and assign moderation status:

- **Approved**: Comment is immediately visible to all users
- **Pending Review**: Comment is visible only to its author with "Pending Administrative Review" message
- **Rejected**: (Future) Comment is hidden from all users after admin review

### Key Features

1. **Real-time Analysis**: Comments analyzed during submission (2-second timeout)
2. **Graceful Degradation**: Defaults to "approved" on timeout/error to maintain UX
3. **Differential Display**: Authors see their pending comments, others don't
4. **Content Detection**:
   - Spam and promotional content unrelated to AWS EUC
   - Dangerous links (IP addresses, URL shorteners, suspicious TLDs)
   - Harassment and abusive language
   - Off-topic content unrelated to AWS/cloud/EUC

5. **Transparency**: Clear messaging to authors when comments are pending review
6. **Low False Positives**: System prefers letting borderline content through rather than incorrectly flagging legitimate comments

### Technical Approach

- **Model**: Claude Haiku (fast, cost-effective)
- **Timeout**: 2 seconds (maintains fast comment submission)
- **Error Handling**: Default to "approved" on any error
- **Storage**: Add moderation metadata to DynamoDB comment objects
- **Display**: Frontend filters comments based on viewer identity

## Implementation Plan

Complete specification available in `.kiro/specs/comment-moderation-ai/`:
- **requirements.md**: 10 requirements with 50 acceptance criteria
- **design.md**: Architecture, data models, error handling, testing strategy
- **tasks.md**: 12 main tasks with 15 sub-tasks

### Task Breakdown

1. ✅ Set up Bedrock client and moderation infrastructure
2. ✅ Implement moderation prompt and response parsing
3. ✅ Integrate moderation into comment submission flow
4. ⏸️ Checkpoint - Test moderation integration in staging
5. ✅ Implement comment filtering logic
6. ✅ Implement frontend comment display logic
7. ✅ Add CSS styling for pending comments
8. ⏸️ Checkpoint - Test end-to-end flow in staging
9. ✅ Add CloudWatch monitoring and logging
10. ✅ Update IAM permissions for Bedrock access
11. ✅ Integration testing and documentation
12. ⏸️ Final checkpoint - Production deployment preparation

### Testing Strategy

- **Property-based tests**: 10 universal correctness properties (100+ iterations each)
- **Unit tests**: Specific scenarios for spam, links, harassment, off-topic detection
- **Integration tests**: End-to-end flow in staging environment
- **Manual testing**: Comprehensive checklist before production deployment

## Success Criteria

- [ ] Comments are automatically analyzed within 2 seconds
- [ ] Spam, dangerous links, harassment, and off-topic content are flagged
- [ ] Legitimate technical discussions are approved
- [ ] Authors can see their pending comments with clear status message
- [ ] Other users cannot see pending comments
- [ ] Comment counts exclude pending comments
- [ ] System gracefully handles timeouts and errors (defaults to approved)
- [ ] All property tests pass (100+ iterations each)
- [ ] All unit tests pass
- [ ] Staging environment testing complete
- [ ] CloudWatch monitoring in place
- [ ] Documentation updated

## Deployment Strategy

1. **Phase 1**: Deploy to staging environment
   - Test with sample comments
   - Verify Bedrock integration
   - Validate filtering logic
   - Check frontend display

2. **Phase 2**: Deploy to production with monitoring
   - Deploy Lambda changes
   - Deploy frontend changes
   - Monitor CloudWatch metrics
   - Watch for errors or timeouts

3. **Phase 3**: Iterate based on feedback
   - Adjust moderation prompt if needed
   - Tune confidence thresholds
   - Add admin review interface (future work)

## Rollback Plan

- **Lambda**: Instant rollback via alias update to previous version
- **Frontend**: 2-3 minute rollback via git revert and redeploy

## Dependencies

- AWS Bedrock access (Claude Haiku model)
- IAM permissions for `bedrock:InvokeModel`
- Existing comment submission flow in API Lambda
- Existing frontend comment display logic

## Future Enhancements

- Admin interface for reviewing flagged comments
- Ability to approve/reject pending comments
- User reputation system to reduce false positives for trusted users
- Batch moderation for existing comments
- Moderation analytics dashboard

## Related Documentation

- Spec: `.kiro/specs/comment-moderation-ai/`
- API Lambda: `lambda_api/lambda_function.py`
- Frontend: `frontend/app.js`
- Deployment Guide: `DEPLOYMENT.md`

## Estimated Effort

- **Backend Implementation**: 4-6 hours
- **Frontend Implementation**: 2-3 hours
- **Testing**: 3-4 hours
- **Staging Deployment & Validation**: 2-3 hours
- **Production Deployment**: 1-2 hours
- **Total**: 12-18 hours

## Notes

- This feature aligns with platform goal of maintaining high-quality technical discussions
- Graceful degradation ensures user experience is not impacted by moderation system issues
- Property-based testing provides high confidence in correctness across all scenarios
- Blue-green deployment strategy allows safe rollout with instant rollback capability
