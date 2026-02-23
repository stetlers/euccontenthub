# Builder Crawler - Pragmatic Solution

**Date**: 2026-02-12  
**Status**: Recommendation for Path Forward

## The Original Problem

**Issue #26**: AI-generated summaries disappearing from posts after crawler runs, even when content hasn't changed.

**Impact**: 115 posts (24%) lost summaries, affecting user experience.

## What We've Already Fixed

### ✅ Data Preservation Fix (DEPLOYED TO STAGING)

**File**: `enhanced_crawler_lambda.py`  
**Deployed**: 2026-02-12  
**Status**: ✅ Tested and working

**What it does**:
- Uses `if_not_exists()` to preserve existing authors, content, summaries
- Only updates fields that don't already exist
- Never overwrites real data with placeholder data

**Test Results**:
- ✅ 0 summaries lost (was 115 before)
- ✅ 0 authors overwritten
- ✅ 0 content corrupted
- ✅ 100% data preservation

**This fix SOLVES the original issue.**

## What We Tried to Add (But Failed)

### ❌ Selenium Crawler Orchestration (NOT WORKING)

**Goal**: Get real author names for Builder.AWS posts instead of "AWS Builder Community"

**Status**: Blocked by two critical issues:
1. Selenium crawler code never deployed (still old version from Feb 8)
2. Chrome infrastructure completely broken (100% failure rate)

**Impact of not having this**:
- Builder.AWS posts keep placeholder "AWS Builder Community" author
- But summaries are preserved (the original issue is fixed)
- Posts still have content and are searchable

## The Question

Do we need the Selenium crawler to solve Issue #26?

**Answer**: NO

- Issue #26 is about summary loss
- Data preservation fix solves summary loss
- Selenium crawler is about getting real authors (nice-to-have, not critical)

## Recommended Path Forward

### Option A: Deploy Data Preservation Fix Only (RECOMMENDED)

**What to deploy**:
1. Deploy sitemap crawler with data preservation fix to production
2. Skip Selenium crawler orchestration for now
3. Close Issue #26 as resolved

**Pros**:
- ✅ Solves the original problem (summary loss)
- ✅ Already tested and working in staging
- ✅ Low risk (simple fix)
- ✅ Can deploy immediately
- ✅ No Chrome infrastructure issues

**Cons**:
- ⚠️ Builder.AWS posts still have placeholder authors
- ⚠️ Selenium crawler orchestration work is wasted

**Timeline**: Can deploy today

### Option B: Fix Everything Before Deploying (NOT RECOMMENDED)

**What to do**:
1. Debug Chrome crashes (could take days)
2. Build and deploy Selenium crawler Docker image
3. Test complete orchestration
4. Then deploy to production

**Pros**:
- ✅ Gets real authors for Builder.AWS posts
- ✅ Complete solution

**Cons**:
- ❌ Delays fixing the critical issue (summary loss)
- ❌ Chrome issues may be unsolvable in Lambda
- ❌ High complexity and risk
- ❌ May need to move to ECS/Fargate

**Timeline**: 2-3 days minimum, possibly longer

### Option C: Hybrid Approach

**What to do**:
1. Deploy data preservation fix to production NOW (fixes Issue #26)
2. Fix Selenium/Chrome issues separately as a new enhancement
3. Deploy Selenium orchestration later when it's working

**Pros**:
- ✅ Fixes critical issue immediately
- ✅ Allows time to properly fix Selenium
- ✅ Low risk for production
- ✅ Can revisit Selenium as separate project

**Cons**:
- ⚠️ Two deployments instead of one

**Timeline**: Deploy today, Selenium later

## Recommendation: Option C (Hybrid)

### Phase 1: Deploy Data Preservation Fix (TODAY)

**Deploy to production**:
- Sitemap crawler with `if_not_exists()` fix
- Removes Selenium invocation (revert to old behavior)
- Keeps data preservation logic

**Result**:
- ✅ Issue #26 resolved (no more summary loss)
- ✅ Production stable
- ⚠️ Builder.AWS posts keep placeholder authors (acceptable)

### Phase 2: Fix Selenium Infrastructure (LATER)

**Separate project**:
- Debug Chrome crashes
- Consider ECS/Fargate instead of Lambda
- Build and deploy updated Selenium crawler
- Test complete orchestration
- Deploy when ready

**Result**:
- ✅ Real authors for Builder.AWS posts
- ✅ Complete solution
- ✅ No rush, can do it right

## What to Revert

To deploy Option C, we need to revert the Selenium invocation from the sitemap crawler:

**Current code (staging)**:
```python
# Invokes Selenium for changed Builder.AWS posts
if changed_post_ids:
    lambda_client.invoke(
        FunctionName='aws-blog-builder-selenium-crawler',
        Payload=json.dumps({'post_ids': changed_post_ids})
    )
```

**Revert to**:
```python
# Don't invoke Selenium (it's broken anyway)
# Just preserve existing data with if_not_exists()
```

## Why This Makes Sense

1. **Solves the actual problem**: Issue #26 is about summary loss, not author names
2. **Low risk**: Data preservation fix is simple and tested
3. **Unblocks production**: Don't wait for Selenium to be fixed
4. **Pragmatic**: Accept placeholder authors as acceptable trade-off
5. **Allows proper fix later**: Can revisit Selenium when we have time

## What We Learned

1. **Scope creep**: We tried to fix more than the original issue
2. **Infrastructure matters**: Chrome issues blocked the entire solution
3. **Perfect is enemy of good**: Data preservation fix is good enough
4. **Test incrementally**: Should have deployed data fix first, then added Selenium

## Action Items

### Immediate (Today)
1. [ ] Revert Selenium invocation from sitemap crawler
2. [ ] Keep data preservation logic (`if_not_exists()`)
3. [ ] Test in staging
4. [ ] Deploy to production
5. [ ] Close Issue #26

### Future (Separate Project)
1. [ ] Create new issue: "Get real authors for Builder.AWS posts"
2. [ ] Investigate Chrome crashes
3. [ ] Consider ECS/Fargate for Selenium
4. [ ] Build and deploy when ready

## Conclusion

The data preservation fix solves Issue #26 (summary loss). The Selenium orchestration is a nice-to-have enhancement that's blocked by infrastructure issues. Deploy the fix that works, revisit Selenium later.

**Recommendation**: Deploy data preservation fix to production today, fix Selenium later as a separate project.
