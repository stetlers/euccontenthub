# Implementation Plan: Innovation Promotion

## Overview

Implement the "Promote to Proposal" workflow that lets Innovation Hub authors convert published innovations into formal proposals (Article or Feature). The backend adds a two-step promote endpoint (refine mode + submit mode) to `lambda_api/lambda_function.py`, two new Content Refiner functions, and a Mermaid-to-PNG converter. The frontend extends InnovationHub and ArticleProposal classes in both `app.js` and `app-staging.js` with promotion UI, bidirectional links, and diagram display. All changes use Python (backend) and vanilla JavaScript (frontend).

## Tasks

- [x] 1. Implement Content Refiner functions
  - [x] 1.1 Add `refine_innovation_to_article(innovation)` function in `lambda_api/lambda_function.py`
    - Build Bedrock prompt from innovation title, problem_statement, architecture_description, code_snippets, upvotes, and comment_count
    - Return JSON: {title, category, summary, outline, key_topics, target_audience, estimated_length}
    - Include fallback on Bedrock failure: original title, "Technical How-To" category, problem_statement as summary, generic outline
    - Follow existing `refine_article_proposal` pattern for Bedrock invocation and JSON extraction
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 1.2 Add `refine_innovation_to_feature(innovation)` function in `lambda_api/lambda_function.py`
    - Build Bedrock prompt from innovation title, problem_statement, architecture_description, aws_services, complexity_level
    - Return JSON: {refined_description, related_features, request_category}
    - Include fallback on Bedrock failure: empty strings for all fields
    - Follow existing `refine_feature_proposal` pattern
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ]* 1.3 Write property test for refiner input completeness
    - **Property 2: Refiner input completeness**
    - Generate random innovation objects, call each refiner, assert prompt contains all required fields
    - **Validates: Requirements 3.1, 4.1**

  - [ ]* 1.4 Write property test for refiner output completeness
    - **Property 3: Refiner output completeness**
    - Generate random innovations, mock Bedrock success and failure, assert output always contains all required keys with correct fallback values
    - **Validates: Requirements 3.2, 3.3, 4.2, 4.3**

- [x] 2. Implement Mermaid-to-PNG converter
  - [x] 2.1 Add `convert_mermaid_to_png(mermaid_code, innovation_id)` function in `lambda_api/lambda_function.py`
    - Convert Mermaid.js code string to PNG image
    - Upload PNG to S3 at `diagrams/{innovation_id}.png`
    - Return the S3 URL on success, empty string on failure (non-blocking)
    - _Requirements: 6.3_

- [x] 3. Implement promote endpoint
  - [x] 3.1 Add `promote_innovation(event, body)` handler function in `lambda_api/lambda_function.py`
    - Decorate with `@require_auth`
    - Extract `innovation_id` from path, parse `promotion_path`, `refine_only`, and edited content fields from body
    - Fetch innovation from DynamoDB, verify caller is author (`user_id` match), verify status is "published", verify not already promoted (`promoted_to_proposal_id` absent)
    - Return 404 if innovation not found, 403 if not author, 409 if already promoted, 400 if not published or invalid promotion_path
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 3.2 Implement refine mode in `promote_innovation`
    - When `refine_only` is true: call `refine_innovation_to_article` or `refine_innovation_to_feature` based on `promotion_path`
    - Return `{refined_content, innovation}` without creating any records
    - _Requirements: 3.1, 3.2, 4.1, 4.2, 5.1_

  - [x] 3.3 Implement submit mode in `promote_innovation`
    - Validate edited fields using same rules as existing `submit_proposal` / `submit_feature_proposal`
    - For article path: call `convert_mermaid_to_png` if architecture_diagram is non-empty, create proposal with `source_innovation_id`, `architecture_diagram_url`, and `code_snippets`
    - For feature path: create proposal with `source_innovation_id`, `architecture_diagram` (Mermaid string), and `code_snippets`
    - Update innovation record: set `promoted_to_proposal_id` and `promoted_at`
    - Return `{message, proposal, innovation}`
    - _Requirements: 5.3, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 8.1_

  - [x] 3.4 Add route for `POST /innovations/{innovation_id}/promote` in `lambda_handler`
    - Add routing logic in the Innovation Hub endpoints section of `lambda_handler`
    - Extract `innovation_id` from path, parse body, call `promote_innovation`
    - _Requirements: 7.1_

  - [ ]* 3.5 Write property test for promotion validation consistency
    - **Property 4: Promotion validation consistency**
    - Generate random edited content fields, run through both promotion validation and existing endpoint validation, assert identical accept/reject decisions
    - **Validates: Requirements 5.3**

  - [ ]* 3.6 Write property test for bidirectional link creation
    - **Property 5: Bidirectional link creation**
    - Generate random valid innovations and promotion requests, after promotion assert proposal has `source_innovation_id` and innovation has `promoted_to_proposal_id` and `promoted_at`
    - **Validates: Requirements 6.1, 6.2**

  - [ ]* 3.7 Write property test for article promotion diagram conversion
    - **Property 6: Article promotion diagram conversion**
    - Generate random innovations with non-empty Mermaid diagrams, after article promotion assert `architecture_diagram_url` is a valid S3 URL
    - **Validates: Requirements 6.3**

  - [ ]* 3.8 Write property test for regular proposals excluding diagram URL
    - **Property 7: Regular proposals exclude diagram URL**
    - Generate random proposal submissions through standard endpoints, assert `architecture_diagram_url` is absent or empty
    - **Validates: Requirements 6.4**

  - [ ]* 3.9 Write property test for content carry-forward
    - **Property 8: Content carry-forward**
    - Generate random innovations with code_snippets and architecture_diagram, after promotion assert proposal contains same code_snippets; for feature path assert same architecture_diagram string
    - **Validates: Requirements 6.5, 6.6**

  - [ ]* 3.10 Write property test for innovation status preservation
    - **Property 9: Innovation status preservation**
    - Generate random valid innovations with status "published", after promotion assert status remains "published"
    - **Validates: Requirements 8.1**

- [x] 4. Checkpoint - Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement promotion UI in frontend (app-staging.js)
  - [x] 5.1 Add "Promote to Proposal" button to innovation detail modal in `frontend/app-staging.js`
    - Show button only when user is authenticated, is the innovation author, innovation status is "published", and `promoted_to_proposal_id` is not set
    - When `promoted_to_proposal_id` is set, show "View Proposal" link instead
    - Hide button entirely for non-authors and unauthenticated users
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 5.2 Add path selection modal in `frontend/app-staging.js`
    - Display two selectable cards: "Builder.AWS Article Proposal" and "Service Feature Proposal"
    - Include brief description for each path explaining target format and audience
    - On confirm, call `POST /innovations/{id}/promote` with `refine_only: true` and selected `promotion_path`
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 5.3 Add review/edit form in `frontend/app-staging.js`
    - Display pre-filled form matching chosen path format with AI-refined content
    - For articles: title, category dropdown, summary, outline (editable list), key topics, target audience, estimated length
    - For features: service dropdown, title, description, priority, use case
    - Allow editing all fields before submission
    - On submit, call `POST /innovations/{id}/promote` with `refine_only: false` and edited fields
    - _Requirements: 5.1, 5.2_

  - [x] 5.4 Add promoted badge and bidirectional links in `frontend/app-staging.js`
    - Show "📤 Promoted" badge on innovation cards when `promoted_to_proposal_id` is set
    - In innovation detail modal: show "View Proposal" link for promoted innovations
    - In proposal detail view: show "View Original Innovation" link when `source_innovation_id` is set
    - _Requirements: 8.2, 8.3, 9.1, 9.2_

  - [x] 5.5 Add diagram display for article proposals in `frontend/app-staging.js`
    - For proposals with `architecture_diagram_url`, render the PNG image in proposal detail view
    - Provide a "Download Diagram (PNG)" button
    - Fallback: if URL is empty, render Mermaid code client-side
    - _Requirements: 6.3_

  - [ ]* 5.6 Write property test for promote button visibility
    - **Property 1: Promote button visibility**
    - Generate random innovation objects with varying auth/ownership/status/promotion states, assert button visibility matches conjunction of all conditions
    - **Validates: Requirements 1.1, 1.2, 1.3, 8.3, 9.2**

  - [ ]* 5.7 Write property test for bidirectional navigation rendering
    - **Property 10: Bidirectional navigation rendering**
    - Generate random innovation objects with/without promoted_to_proposal_id and random proposals with/without source_innovation_id, assert correct badges and links
    - **Validates: Requirements 8.2, 9.1**

- [x] 6. Checkpoint - Ensure staging frontend works end-to-end
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Mirror frontend changes to production app.js
  - [x] 7.1 Copy all promotion UI changes from `frontend/app-staging.js` to `frontend/app.js`
    - Replicate promote button, path selection modal, review form, promoted badge, bidirectional links, and diagram display with identical logic
    - _Requirements: 10.1, 10.2_

- [x] 8. Add API Gateway route for promote endpoint
  - [x] 8.1 Update API Gateway setup script to add `POST /innovations/{innovation_id}/promote` route
    - Follow existing pattern in `setup_innovation_api_gateway.py`
    - Add route for both staging and production stages
    - _Requirements: 7.1_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using Hypothesis (Python backend)
- The promote endpoint uses a two-step flow: refine mode (AI draft) then submit mode (create proposal)
- All frontend changes must be applied to both `app.js` and `app-staging.js` per Requirement 10
