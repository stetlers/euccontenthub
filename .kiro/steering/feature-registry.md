---
inclusion: auto
---

# Feature Registry & Regression Prevention

This file documents every active feature in the EUC Content Hub, which files it touches, and what to verify after changes. Use this as a checklist when building new features to avoid regressions.

## CRITICAL RULES

1. **Always read the current version of a file before modifying it.** Never assume you know what's in a file from a previous conversation.
2. **Both app.js and app-staging.js must stay in sync.** Every feature class and function must exist identically in both files.
3. **Both auth.js and auth-staging.js must stay in sync.** Every dropdown item, profile fetch logic, and trigger must match.
4. **Never overwrite a file wholesale.** Use targeted edits (strReplace, editCode) to modify specific sections. Wholesale writes cause regressions.
5. **After modifying app.js, always apply the same change to app-staging.js** (and vice versa for auth files).
6. **Deploy to staging first, test, then production.** No exceptions.

## File Pairs (must stay in sync)

| Production | Staging |
|---|---|
| `frontend/app.js` | `frontend/app-staging.js` |
| `frontend/auth.js` | `frontend/auth-staging.js` |
| `frontend/index.html` | `frontend/index-staging.html` |

## Active Features

### 1. Post Loading, Search, Filtering, Sorting
- **Files**: `app.js` (functions: `loadPosts`, `handleSearch`, `handleFilter`, `handleSort`, `renderPosts`, `createPostCard`)
- **Verify**: Posts load, search works, all 6 stat card filters work, label category filters work, sort dropdown works
- **Dependencies**: API GET /posts endpoint

### 2. Flip Card Post Design
- **Files**: `app.js` (`createPostCard`), `styles-refined.css` (`.post-card`, `.post-flip-*`)
- **Verify**: Cards render with front (title, author, label, action buttons) and back (summary, date, tags). Click to flip works. Zoom mode works.
- **Dependencies**: `zoom-mode.js`, `zoom-mode.css`

### 3. Voting (Love, Needs Update, Remove Post)
- **Files**: `app.js` (`handleVote`, `createPostCard`), `lambda_api/lambda_function.py` (vote endpoint)
- **Verify**: Love/vote/remove buttons work, counts update, buttons disable after voting, badge responses processed
- **Dependencies**: Authentication required

### 4. Comments
- **Files**: `app.js` (`openCommentsModal`, `loadComments`, `handleSubmitComment`, `createCommentHTML`), `lambda_api/lambda_function.py`
- **Verify**: Comment modal opens, comments load, new comments submit, character counter works
- **Dependencies**: Authentication required, Bedrock moderation

### 5. Bookmarks
- **Files**: `app.js` (`handleBookmark`, `loadUserBookmarks`), `lambda_api/lambda_function.py`
- **Verify**: Bookmark toggle works, "My Bookmarks" filter shows bookmarked posts
- **Dependencies**: Authentication required

### 6. Content Cart
- **Files**: `cart-manager.js`, `cart-ui.js`, `cart.css`, `app.js` (`initializeCart`, `handleCart`, `updateCartButtons`)
- **Verify**: Add/remove from cart, cart UI opens, checkout with AI summaries works, cart merge on sign-in
- **Dependencies**: Authentication optional (localStorage for anonymous, DynamoDB for authenticated)

### 7. Article Proposals
- **Files**: `app.js` (`ArticleProposal` class, `setupProposalsDropdown`), `lambda_api/lambda_function.py` (POST /proposals)
- **Verify**: Proposals dropdown shows 3 options (Article, Feature, Review), article proposal modal opens, Bedrock AI enhancement works, submission works
- **Dependencies**: Authentication required, Bedrock

### 8. Feature Proposals
- **Files**: `app.js` (`FeatureProposal` class), `lambda_api/lambda_function.py` (POST /propose-feature)
- **Verify**: Feature proposal modal opens with service selector, priority dropdown, AI enhancement works, submission works
- **Dependencies**: Authentication required, Bedrock

### 9. Proposals Review
- **Files**: `app.js` (`ProposalsReview` class), `lambda_api/lambda_function.py` (GET /proposals)
- **Verify**: Review modal opens from dropdown, type filter tabs work (All/Articles/Features), voting and commenting on proposals works, delete own proposals works
- **Dependencies**: Authentication required

### 10. User Profiles
- **Files**: `profile.js`, `lambda_api/lambda_function.py` (GET/PUT/DELETE /profile)
- **Verify**: Profile modal opens, display name/bio/credly/builder ID editable, visit streak displays, achievements display, activity stats display, public profile popup works
- **Dependencies**: Authentication required

### 11. Achievements
- **Files**: `lambda_api/lambda_function.py` (`BADGE_REGISTRY`, `evaluate_badges`, `evaluate_and_award_badges`), `app.js` (`showBadgeToast`, `processBadgeResponse`), `profile.js`
- **Verify**: Badge toasts appear on earning, profile shows achievements with flip cards, 27 badges across 7 categories
- **Dependencies**: Triggered by votes, comments, bookmarks, heartbeat, proposals

### 12. Visit Streak Tracking
- **Files**: `lambda_api/lambda_function.py` (heartbeat endpoint), `profile.js`
- **Verify**: Heartbeat fires on page load, streak increments daily, longest streak tracked, profile displays streak
- **Dependencies**: Authentication required

### 13. AI Chat Assistant
- **Files**: `chat-widget-kb.js`, `chat-widget-kb-styles.css`, `chat_lambda_kb_staging.py`
- **Verify**: Chat widget opens, messages send, KB citations work, conversation history persists, new conversation button works
- **Dependencies**: Bedrock, chat-conversations DynamoDB table

### 14. Knowledge Base Editor
- **Files**: `kb-editor.js`, `kb-editor-styles.css`
- **Verify**: KB editor opens from profile dropdown, can add/edit/delete entries
- **Dependencies**: Authentication required

### 15. News Ticker (What's New Chyron)
- **Files**: `app.js` (`loadWhatsNewChiron`), `lambda_api/lambda_function.py` (GET /whats-new)
- **Verify**: Ticker scrolls at top of page, shows latest announcements, speed adjustable

### 16. Activity Dashboard Charts
- **Files**: `app.js` (`renderCharts`, `renderLeaderboardChart`, `renderRecentBlogsChart`, `renderTopLovedChart`, `renderTopVotesChart`, `renderTopCommentsChart`, `loadReleasesPerMonthChart`, `loadKBLeaderboard`)
- **Verify**: All 7 dashboard charts render (Leaderboard, Posts Added, Most Loved, Top Votes, Comments, EUC Releases, KB Leaders)
- **Dependencies**: Chart.js library

### 17. Crawler & Pipeline
- **Files**: `app.js` (`handleCrawl`, `startCrawlerPolling`, `fetchPipelineStatus`), `enhanced_crawler_lambda.py`, `builder_selenium_crawler.py`, `pipeline_processor_lambda.py`, `pipeline_utils.py`, `daily_backfill_lambda.py`
- **Verify**: Crawler button visible for authenticated users, pipeline status indicator shows queue depth, SQS processing works
- **Dependencies**: Authentication required, SQS queues, ECS/Fargate

### 18. Interactive Tour
- **Files**: `app.js` (`InteractiveTour` class), `auth.js` (tour triggers in `fetchDisplayName`, `_showTourPrompt`, tourBtn), `lambda_api/lambda_function.py` (`tour_completed` field)
- **Verify**: Tour auto-launches for new users, "What's New" prompt for 30+ day absence, dropdown "Take the Tour" works, pause/resume/prev/next work, hotspot clicks jump to step, tour_completed persists after completion
- **Dependencies**: Authentication required

### 19. Service Name Detector
- **Files**: `service-name-detector.js`, `euc-service-name-mapping.json`
- **Verify**: Renamed service badges appear on relevant post cards

### 20. Zoom Mode
- **Files**: `zoom-mode.js`, `zoom-mode.css`
- **Verify**: Zoom button appears on cards, enlarges card for presentations

### 22. Innovation Hub
- **Files**: `app.js` (`InnovationHub` class), `lambda_api/lambda_function.py` (7 endpoints: GET/POST /innovations, POST /innovations/{id}/vote, GET/POST /innovations/{id}/comments, POST /innovations/{id}/bookmark, DELETE /innovations/{id}, PUT /innovations/{id}), `styles-refined.css`, `index.html` (Prism.js CDN)
- **Verify**: Innovation Hub button visible, browse view with cards/filters/sort/search, detail view with Mermaid diagrams and Prism.js syntax highlighting, submission form with validation, voting/comments/bookmarks work, featured innovation section, Regenerate Diagram button for broken Mermaid (owner-only), delete own innovations
- **Dependencies**: Authentication required for submit/vote/comment/bookmark/delete, Bedrock for Mermaid diagram generation and content moderation, DynamoDB `innovations` table

### 23. Innovation-to-Proposal Promotion
- **Files**: `app.js` (`InnovationHub` class: `openPromotionPathSelector`, `refineForPromotion`, `openPromotionReviewForm`, `submitPromotion`), `lambda_api/lambda_function.py` (`promote_innovation`, `refine_innovation_to_article`, `refine_innovation_to_feature`, `convert_mermaid_to_png`; route: POST /innovations/{id}/promote), `setup_innovation_promote_api.py`
- **Verify**: "Promote to Proposal" button visible on own published innovations (not already promoted), path selection modal (Article vs Feature), AI refinement returns pre-filled form, review/edit form submits correctly, proposal created with `source_innovation_id` and `architecture_diagram_url`, innovation marked with `promoted_to_proposal_id`, "📤 Promoted" badge on innovation cards, "View Proposal" link on promoted innovations, diagram PNG renders in proposal detail with download button, code snippets carry forward, "Promoted from Innovation Hub" badge on proposals
- **Dependencies**: Authentication required, Bedrock for AI content refinement, S3 for diagram PNG storage (diagrams/ prefix), mermaid.ink API for Mermaid-to-PNG conversion, DynamoDB `innovations` and `proposed-articles` tables, IAM DiagramUploadPolicy on Lambda role

### 21. Legal Modals (Privacy, Terms, Data Deletion)
- **Files**: `app.js` (`setupPrivacyModal`, `setupTermsModal`, `setupDataDeletionModal`), `index.html`
- **Verify**: Footer links open modals with legal text

## Auth Dropdown Menu (order matters)
The profile dropdown in `auth.js` / `auth-staging.js` has these items in order:
1. 👤 My Profile
2. 📚 Edit Knowledge Base
3. 🗺️ Take the Tour
4. 🚪 Sign Out

When adding new menu items, maintain this order and add between KB Editor and Tour unless there's a specific reason not to.

## Post-Deployment Smoke Test Checklist
After any deployment, verify these core flows:
- [ ] Page loads, posts render
- [ ] Search returns results
- [ ] Sign in works
- [ ] Profile opens
- [ ] Vote on a post
- [ ] Open comments modal
- [ ] Proposals dropdown shows 3 options
- [ ] Chat widget opens and responds
- [ ] News ticker scrolls
- [ ] Dashboard charts render
- [ ] Innovation Hub opens, cards render, detail view works
- [ ] Promote button visible on own innovations, promotion flow creates proposal with diagram
