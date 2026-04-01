# Requirements Document

## Introduction

The "Promote Innovation to Proposal" feature enables Innovation Hub authors to graduate mature innovation ideas into formal proposals within the existing Proposals section. Authors choose between two promotion paths — a Builder.AWS Article Proposal or a Service Feature Proposal. The system uses AI (Bedrock Claude Haiku) to transform innovation content (title, problem statement, architecture description, diagram, code snippets, community feedback) into the appropriate proposal format. After promotion, the innovation remains in the Hub as a historical record with a bidirectional link to the resulting proposal.

## Glossary

- **Innovation**: A community-submitted idea stored in the `innovations` DynamoDB table, containing a title, problem statement, architecture description, architecture diagram, code snippets, AWS services, complexity level, votes, and comments.
- **Proposal**: A formal article or feature request stored in the `proposed-articles` DynamoDB table, created via `POST /propose-article` or `POST /propose-feature`.
- **Promotion_Service**: The backend logic (Lambda API endpoint and AI refinement) responsible for converting an Innovation into a Proposal.
- **Promotion_UI**: The frontend components (button, path selector modal, review form) that guide the author through the promotion workflow.
- **Article_Proposal**: A Proposal with `proposal_type: "article"` targeting a Builder.AWS community article.
- **Feature_Proposal**: A Proposal with `proposal_type: "feature"` targeting a service feature request for an EUC service.
- **Promotion_Path**: The author's choice of target format — either Article_Proposal or Feature_Proposal.
- **Bidirectional_Link**: A pair of references: the Innovation stores the resulting `proposal_id`, and the Proposal stores the originating `innovation_id`.
- **Content_Refiner**: The Bedrock Claude Haiku AI call that transforms Innovation fields into the structured format required by the chosen Promotion_Path.

## Requirements

### Requirement 1: Promotion Eligibility

**User Story:** As an innovation author, I want the "Promote to Proposal" option to appear only when my innovation qualifies, so that premature ideas are not promoted.

#### Acceptance Criteria

1. WHEN an authenticated user views their own Innovation detail modal, THE Promotion_UI SHALL display a "Promote to Proposal" button only if the Innovation has a status of "published" and has not already been promoted.
2. WHILE an Innovation has a `promoted_to_proposal_id` field set, THE Promotion_UI SHALL hide the "Promote to Proposal" button and display a "View Proposal" link pointing to the linked Proposal instead.
3. WHEN an unauthenticated user or a user who is not the Innovation author views the Innovation detail modal, THE Promotion_UI SHALL not display the "Promote to Proposal" button.

### Requirement 2: Promotion Path Selection

**User Story:** As an innovation author, I want to choose whether my innovation becomes a Builder.AWS article proposal or a service feature proposal, so that the content is formatted for the right audience.

#### Acceptance Criteria

1. WHEN the author clicks "Promote to Proposal", THE Promotion_UI SHALL display a modal with two selectable options: "Builder.AWS Article Proposal" and "Service Feature Proposal".
2. THE Promotion_UI SHALL display a brief description for each Promotion_Path explaining the target format and audience.
3. WHEN the author selects a Promotion_Path and confirms, THE Promotion_UI SHALL proceed to the AI content refinement step for the selected path.

### Requirement 3: AI Content Refinement for Article Proposals

**User Story:** As an innovation author choosing the article path, I want AI to transform my innovation content into a structured article proposal, so that I have a strong starting draft.

#### Acceptance Criteria

1. WHEN the author selects the Article_Proposal path, THE Content_Refiner SHALL receive the Innovation title, problem statement, architecture description, code snippets, and community feedback summary as input.
2. THE Content_Refiner SHALL return a JSON object containing: a refined title, a category (from the six existing article categories), a summary, an outline (list of sections), key topics, target audience, and estimated length.
3. IF the Bedrock API call fails, THEN THE Promotion_Service SHALL return a fallback response using the original Innovation title as the proposal title, "Technical How-To" as the default category, and the problem statement as the summary.

### Requirement 4: AI Content Refinement for Feature Proposals

**User Story:** As an innovation author choosing the feature path, I want AI to transform my innovation content into a structured feature proposal, so that the request is clear and actionable for the service team.

#### Acceptance Criteria

1. WHEN the author selects the Feature_Proposal path, THE Content_Refiner SHALL receive the Innovation title, problem statement, architecture description, AWS services list, and complexity level as input.
2. THE Content_Refiner SHALL return a JSON object containing: a refined description, related existing features or workarounds, and a request category (New Capability, Enhancement, Integration, Performance, or Usability).
3. IF the Bedrock API call fails, THEN THE Promotion_Service SHALL return a fallback response with empty refined_description, related_features, and request_category fields.

### Requirement 5: Proposal Review and Editing

**User Story:** As an innovation author, I want to review and edit the AI-generated proposal content before submitting, so that I can correct or improve the draft.

#### Acceptance Criteria

1. WHEN the Content_Refiner returns the refined content, THE Promotion_UI SHALL display a pre-filled proposal form matching the chosen Promotion_Path format.
2. THE Promotion_UI SHALL allow the author to edit all pre-filled fields before submission.
3. WHEN the author submits the reviewed form, THE Promotion_Service SHALL validate the edited fields using the same validation rules as the existing `POST /propose-article` or `POST /propose-feature` endpoints.

### Requirement 6: Proposal Creation with Innovation Link

**User Story:** As an innovation author, I want the submitted proposal to be linked back to my original innovation, so that reviewers can see the idea's history and community feedback.

#### Acceptance Criteria

1. WHEN the author submits the promotion form, THE Promotion_Service SHALL create a new Proposal in the `proposed-articles` table with a `source_innovation_id` field set to the originating Innovation's `innovation_id`.
2. WHEN the Proposal is created successfully, THE Promotion_Service SHALL update the originating Innovation record by setting `promoted_to_proposal_id` to the new Proposal's `proposal_id` and setting `promoted_at` to the current UTC timestamp.
3. WHEN the Promotion_Path is Article_Proposal, THE Promotion_Service SHALL convert the Innovation's `architecture_diagram` Mermaid.js code string into a PNG image, store it in S3, and set the Proposal record's `architecture_diagram_url` field to the S3 URL. THE Promotion_UI SHALL display this diagram image within the Proposal detail view, and provide a "Download Diagram (PNG)" button so the author can save it for upload to Builder.aws.
4. THE `architecture_diagram_url` field SHALL only be populated through the promotion workflow. THE existing proposal submission forms (`POST /propose-article`, `POST /propose-feature`) SHALL NOT add an image upload prompt or expose this field to regular proposal authors.
5. WHEN the Promotion_Path is Feature_Proposal, THE Promotion_Service SHALL carry forward the Innovation's `architecture_diagram` field as a Mermaid.js code string into the Proposal record (no image conversion needed for feature requests).
6. THE Promotion_Service SHALL carry forward the Innovation's `code_snippets` array into the Proposal record.

### Requirement 7: Promotion API Endpoint

**User Story:** As a frontend developer, I want a single API endpoint to handle the promotion workflow, so that the frontend can orchestrate the process with minimal API calls.

#### Acceptance Criteria

1. THE Promotion_Service SHALL expose a `POST /innovations/{innovation_id}/promote` endpoint that accepts a JSON body with a `promotion_path` field ("article" or "feature") and optional edited content fields.
2. WHEN the endpoint receives a valid request, THE Promotion_Service SHALL authenticate the caller, verify the caller is the Innovation author, verify the Innovation has not already been promoted, invoke the Content_Refiner, create the Proposal, update the Innovation, and return the created Proposal in the response.
3. IF the `innovation_id` does not exist, THEN THE Promotion_Service SHALL return HTTP 404 with an error message.
4. IF the caller is not the Innovation author, THEN THE Promotion_Service SHALL return HTTP 403 with an error message.
5. IF the Innovation has already been promoted, THEN THE Promotion_Service SHALL return HTTP 409 with an error message indicating the Innovation is already linked to a Proposal.

### Requirement 8: Innovation Historical Record

**User Story:** As a community member, I want promoted innovations to remain visible in the Innovation Hub, so that the community can still view and reference the original idea.

#### Acceptance Criteria

1. WHEN an Innovation is promoted, THE Promotion_Service SHALL retain the Innovation in the `innovations` table with its original status of "published".
2. WHEN a promoted Innovation is displayed in the Innovation Hub list, THE Promotion_UI SHALL show a visual badge or indicator that the Innovation has been promoted to a Proposal.
3. WHEN a user views a promoted Innovation's detail modal, THE Promotion_UI SHALL display a link to the resulting Proposal.

### Requirement 9: Bidirectional Navigation

**User Story:** As a community member, I want to navigate between a promoted innovation and its resulting proposal, so that I can see the full journey of an idea.

#### Acceptance Criteria

1. WHEN a user views a Proposal that has a `source_innovation_id` field, THE Promotion_UI SHALL display a "View Original Innovation" link that opens the linked Innovation detail modal.
2. WHEN a user views a promoted Innovation that has a `promoted_to_proposal_id` field, THE Promotion_UI SHALL display a "View Proposal" link that navigates to the linked Proposal.

### Requirement 10: Frontend Parity Between Production and Staging

**User Story:** As a developer, I want all promotion UI changes to be applied to both `app.js` and `app-staging.js`, so that the blue-green deployment model is maintained.

#### Acceptance Criteria

1. THE Promotion_UI SHALL implement all frontend changes in both `frontend/app.js` and `frontend/app-staging.js` with identical logic.
2. WHEN a promotion-related change is made to one frontend file, THE same change SHALL be applied to the other frontend file before deployment.
