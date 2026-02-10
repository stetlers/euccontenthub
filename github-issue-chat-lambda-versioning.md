# GitHub Issue: Implement Blue-Green Deployment for Chat Lambda

## Issue Title
Chat Lambda needs versioned aliases for proper staging/production separation

## Labels
- `infrastructure`
- `deployment`
- `chat`
- `technical-debt`

## Priority
Medium (not blocking, but important for deployment safety)

## Problem Description

The chat Lambda (`aws-blog-chat-assistant`) currently lacks proper blue-green deployment separation between staging and production environments.

**Current State**:
- Both staging AND production call `$LATEST` directly
- Changes deployed to staging immediately affect production
- No rollback capability for production
- Same issue exists with API Lambda (see related issues)

**Discovered During**: Chat search relevance improvement deployment (2026-02-10)
- Deployed improved search to staging
- Changes immediately appeared in production
- No way to test in staging without affecting production users

## Expected Behavior

**Staging**:
- API Gateway `/staging` stage → Chat Lambda `$LATEST`
- Always uses latest code
- Safe testing environment

**Production**:
- API Gateway `/prod` stage → Chat Lambda `production` alias → Specific version (e.g., v5)
- Uses stable, tested version
- Instant rollback by updating alias

## Current Architecture

```
API Gateway /staging  ──→ aws-blog-chat-assistant ($LATEST)
                                    ↑
API Gateway /prod     ──────────────┘
                    (both call $LATEST!)
```

## Desired Architecture

```
API Gateway /staging  ──→ aws-blog-chat-assistant ($LATEST)

API Gateway /prod     ──→ aws-blog-chat-assistant (production alias) ──→ Version 5
```

## Implementation Steps

### 1. Create Production Alias
```bash
# Publish current $LATEST as version
aws lambda publish-version --function-name aws-blog-chat-assistant \
  --description "Improved search relevance - 2026-02-10"

# Create production alias pointing to new version
aws lambda create-alias --function-name aws-blog-chat-assistant \
  --name production --function-version 5 \
  --description "Production stable version"
```

### 2. Update API Gateway Integration
```bash
# Update /prod stage to use production alias
# In API Gateway console or via CLI:
# Integration endpoint: arn:aws:lambda:us-east-1:031421429609:function:aws-blog-chat-assistant:production
```

### 3. Update Deployment Script
Update `deploy_lambda.py` to handle chat Lambda versioning:
```python
# After deploying to staging, prompt for production
if environment == 'production':
    # Publish new version
    # Update production alias
    # Verify deployment
```

### 4. Test Rollback
```bash
# Rollback to previous version (instant)
aws lambda update-alias --function-name aws-blog-chat-assistant \
  --name production --function-version 4
```

## Benefits

1. **Safe Testing**: Test chat changes in staging without affecting production
2. **Instant Rollback**: Revert production to previous version in seconds
3. **Version History**: Track which version is in production
4. **Consistency**: Same deployment pattern as other Lambdas (API, crawler, etc.)
5. **Confidence**: Deploy changes knowing production is protected

## Related Issues

- API Lambda has same issue (both environments call $LATEST)
- Should fix both at the same time for consistency
- Part of broader blue-green deployment strategy (Issue #1)

## Testing Plan

1. Create production alias pointing to current version
2. Update API Gateway /prod to use alias
3. Verify production still works
4. Deploy test change to staging
5. Verify production is NOT affected
6. Promote staging to production by updating alias
7. Test rollback by reverting alias

## Rollback Plan

If alias setup breaks production:
1. Revert API Gateway integration to call `$LATEST` directly
2. Delete alias
3. Production returns to current behavior

## Notes

- **Current Version**: $LATEST (improved search deployed 2026-02-10)
- **Function Name**: `aws-blog-chat-assistant`
- **API Gateway**: xox05733ce
- **Stages**: `/prod` and `/staging`

## When to Implement

- Next time we make changes to chat Lambda
- Or as part of broader Lambda versioning fix
- Not urgent since current code is stable and working

## Success Criteria

- [ ] Production alias created and pointing to stable version
- [ ] API Gateway /prod uses production alias
- [ ] API Gateway /staging uses $LATEST
- [ ] Deploy to staging doesn't affect production
- [ ] Rollback tested and works
- [ ] Documentation updated

## Additional Context

This is part of the blue-green deployment strategy implemented in Issue #1. The chat Lambda was missed during initial implementation because it was added later.

**Same fix needed for**:
- aws-blog-chat-assistant (this issue)
- aws-blog-api (separate issue needed)
