# Knowledge Base Editor - Design Document

**Feature**: Allow authenticated users to edit Knowledge Base markdown files  
**Purpose**: Enable community contributions to improve chatbot accuracy  
**Access**: Authenticated users only (via profile dropdown)  

---

## 🎯 User Flow

1. User logs in with Cognito
2. Clicks profile dropdown (top right)
3. Sees new option: "Manage Knowledge Base" (between "My Profile" and "Log Out")
4. Clicks "Manage Knowledge Base"
5. Modal opens showing list of KB documents
6. User selects a document to edit
7. Markdown editor opens with current content
8. User makes changes and clicks "Save"
9. System uploads to S3 and triggers ingestion job
10. Success message shown with ingestion status

---

## 🏗️ Architecture

### Frontend Components

**1. Profile Dropdown Menu** (`frontend/profile.js`)
- Add "Manage Knowledge Base" menu item
- Only visible when authenticated
- Opens KB editor modal

**2. KB Editor Modal** (`frontend/kb-editor.js`)
- List view: Shows all KB documents
- Edit view: Markdown editor with preview
- Save functionality with confirmation
- Ingestion status tracking

**3. Markdown Editor** (using library)
- Syntax highlighting
- Live preview
- Validation (max size, format)
- Undo/redo support

### Backend Components

**1. API Lambda Endpoints** (`api_lambda.py`)

**GET /kb-documents**
- Lists all KB documents from S3
- Returns: document names, sizes, last modified
- Auth: Required (JWT validation)

**GET /kb-document/{document_id}**
- Fetches specific document content from S3
- Returns: markdown content, metadata
- Auth: Required (JWT validation)

**PUT /kb-document/{document_id}**
- Updates document in S3
- Triggers Bedrock ingestion job
- Returns: ingestion job ID, status
- Auth: Required (JWT validation)
- Validation: Max size (100KB), markdown format

**GET /kb-ingestion-status/{job_id}**
- Checks ingestion job status
- Returns: status (IN_PROGRESS, COMPLETE, FAILED)
- Auth: Required (JWT validation)

**2. IAM Permissions**
- Lambda needs S3 write permissions
- Lambda needs Bedrock StartIngestionJob permission
- Users tracked via Cognito sub (for audit trail)

### AWS Resources

**1. S3 Bucket** (existing)
- `euc-content-hub-kb-staging` (staging)
- `euc-content-hub-kb-production` (production)
- Versioning enabled (rollback capability)

**2. Bedrock Knowledge Base** (existing)
- ID: MIMYGSK1YU (staging)
- Data Source: S3 bucket
- Ingestion: Triggered via API

**3. DynamoDB Table** (new - optional)
- `kb-edit-history` - Track all edits
- Fields: user_id, document_id, timestamp, change_summary
- Purpose: Audit trail and rollback

---

## 🎨 UI Design

### Profile Dropdown (Updated)
```
┌─────────────────────────┐
│ 👤 John Doe            │
│ 🏆 KB Contributor: #3   │  <- NEW: Leaderboard rank
├─────────────────────────┤
│ My Profile              │
│ Manage Knowledge Base ⭐│  <- NEW
│ KB Contributions 📊     │  <- NEW: View your stats
│ Log Out                 │
└─────────────────────────┘
```

### KB Editor Modal - List View
```
┌────────────────────────────────────────────────────┐
│ 📚 Manage Knowledge Base                      [×]  │
├────────────────────────────────────────────────────┤
│                                                     │
│ Select a document to edit:                         │
│                                                     │
│ ┌────────────────────────────────────────────────┐│
│ │ 📄 Common Questions (Q&A)                      ││
│ │ Last updated: 2 days ago • 12 Q&A pairs       ││
│ │                                    [Edit] ───→ ││
│ └────────────────────────────────────────────────┘│
│                                                     │
│ ┌────────────────────────────────────────────────┐│
│ │ 🔄 Service Renames & History                   ││
│ │ Last updated: 1 week ago • 8 services          ││
│ │                                    [Edit] ───→ ││
│ └────────────────────────────────────────────────┘│
│                                                     │
│ ⚠️  Changes will be reviewed before going live     │
│                                                     │
│                                    [Close]          │
└────────────────────────────────────────────────────┘
```

### KB Editor Modal - Edit View
```
┌────────────────────────────────────────────────────┐
│ ✏️  Edit: Common Questions                    [×]  │
├────────────────────────────────────────────────────┤
│ [Preview] [Edit] [Help]                            │
├────────────────────────────────────────────────────┤
│                                                     │
│ ┌─────────────────────┬─────────────────────────┐ │
│ │ # Common Questions  │ Common Questions        │ │
│ │                     │                         │ │
│ │ ## Q: What is EUC?  │ Q: What is EUC?         │ │
│ │ **A:** EUC stands...│ A: EUC stands for...    │ │
│ │                     │                         │ │
│ │ [Markdown Editor]   │ [Live Preview]          │ │
│ │                     │                         │ │
│ └─────────────────────┴─────────────────────────┘ │
│                                                     │
│ 💡 Tips:                                            │
│ • Use ## for questions                             │
│ • Use **A:** for answers                           │
│ • Keep answers concise (2-3 sentences)             │
│                                                     │
│ Characters: 1,234 / 100,000                        │
│                                                     │
│                        [Cancel]  [Save Changes]    │
└────────────────────────────────────────────────────┘
```

### Save Confirmation Dialog (NEW)
```
┌────────────────────────────────────────────────────┐
│ 💾 Save Changes                               [×]  │
├────────────────────────────────────────────────────┤
│                                                     │
│ Describe your changes: *                           │
│ ┌────────────────────────────────────────────────┐│
│ │ Added Q&A about WorkSpaces Pools and updated  ││
│ │ information about WorkSpaces Personal pricing ││
│ │                                                ││
│ └────────────────────────────────────────────────┘│
│ (Required - min 10 characters)                     │
│                                                     │
│ 📝 Your contribution will be tracked and credited  │
│    to your profile.                                │
│                                                     │
│                        [Cancel]  [Save & Publish]  │
└────────────────────────────────────────────────────┘
```

### Ingestion Status
```
┌────────────────────────────────────────────────────┐
│ ✅ Changes Saved Successfully!                     │
├────────────────────────────────────────────────────┤
│                                                     │
│ Your changes have been saved to the Knowledge Base.│
│                                                     │
│ 🔄 Ingestion Status: IN PROGRESS                   │
│                                                     │
│ ┌────────────────────────────────────────────────┐│
│ │ ████████████░░░░░░░░░░░░░░░░░░░░░░░░ 40%      ││
│ └────────────────────────────────────────────────┘│
│                                                     │
│ The chatbot will use your updated content once     │
│ ingestion is complete (usually 2-3 minutes).       │
│                                                     │
│ 🏆 You've earned +10 contribution points!          │
│                                                     │
│                                    [Close]          │
└────────────────────────────────────────────────────┘
```

### Contributor Dashboard (NEW)
```
┌────────────────────────────────────────────────────┐
│ 🏆 Knowledge Base Contributors                [×]  │
├────────────────────────────────────────────────────┤
│                                                     │
│ Top Contributors This Month:                       │
│                                                     │
│ ┌────────────────────────────────────────────────┐│
│ │ 🥇 1. Sarah Chen                               ││
│ │    23 edits • 156 lines added • 12 documents   ││
│ │    Latest: "Updated AppStream 2.0 pricing"     ││
│ └────────────────────────────────────────────────┘│
│                                                     │
│ ┌────────────────────────────────────────────────┐│
│ │ 🥈 2. Mike Johnson                             ││
│ │    18 edits • 134 lines added • 8 documents    ││
│ │    Latest: "Added WorkSpaces Pools Q&A"        ││
│ └────────────────────────────────────────────────┘│
│                                                     │
│ ┌────────────────────────────────────────────────┐│
│ │ 🥉 3. John Doe (You!)                          ││
│ │    15 edits • 98 lines added • 6 documents     ││
│ │    Latest: "Fixed WorkSpaces rename date"      ││
│ └────────────────────────────────────────────────┘│
│                                                     │
│ [View All Contributors] [View My Contributions]    │
│                                                     │
└────────────────────────────────────────────────────┘
```

### My Contributions View (NEW)
```
┌────────────────────────────────────────────────────┐
│ 📊 My KB Contributions                        [×]  │
├────────────────────────────────────────────────────┤
│                                                     │
│ Your Stats:                                        │
│ • Total Edits: 15                                  │
│ • Lines Added: 98                                  │
│ • Documents Edited: 6                              │
│ • Rank: #3 this month                              │
│ • Member Since: Jan 2026                           │
│                                                     │
│ Recent Contributions:                              │
│                                                     │
│ ┌────────────────────────────────────────────────┐│
│ │ 📄 Common Questions (Q&A)                      ││
│ │ 2 days ago • "Added WorkSpaces Pools Q&A"      ││
│ │ +12 lines, -0 lines                            ││
│ └────────────────────────────────────────────────┘│
│                                                     │
│ ┌────────────────────────────────────────────────┐│
│ │ 🔄 Service Renames & History                   ││
│ │ 1 week ago • "Fixed WorkSpaces rename date"    ││
│ │ +2 lines, -1 line                              ││
│ └────────────────────────────────────────────────┘│
│                                                     │
│                                    [Close]          │
└────────────────────────────────────────────────────┘
```

---

## 🔒 Security & Permissions

### Authentication
- **Required**: Valid Cognito JWT token
- **Validation**: Lambda validates token using Cognito public keys
- **User Tracking**: All edits logged with user_id (Cognito sub)

### Authorization Levels (Future Enhancement)

**Level 1: Viewer** (default for all authenticated users)
- Can view KB documents
- Cannot edit

**Level 2: Editor** (granted by admin)
- Can edit KB documents
- Changes go to staging first
- Requires approval for production

**Level 3: Admin** (site administrators)
- Can edit and approve changes
- Can promote staging to production
- Can rollback changes

**Initial Implementation**: All authenticated users are Editors (staging only)

### Input Validation

**Client-side:**
- Max file size: 100KB
- Valid markdown format
- No script tags or HTML
- Character counter

**Server-side:**
- JWT validation
- File size limit: 100KB
- Content sanitization
- Rate limiting (5 edits per hour per user)

### Audit Trail

**DynamoDB Table: kb-edit-history** (REQUIRED - Not Optional)
```json
{
  "edit_id": "uuid-v4",
  "user_id": "cognito-sub-123",
  "user_email": "user@example.com",
  "user_display_name": "John Doe",
  "document_id": "curated-qa/common-questions.md",
  "document_name": "Common Questions (Q&A)",
  "timestamp": "2026-02-24T17:00:00Z",
  "change_comment": "Added Q&A about WorkSpaces Pools and updated pricing info",
  "content_before_hash": "sha256-hash-of-previous-content",
  "content_after_hash": "sha256-hash-of-new-content",
  "lines_added": 12,
  "lines_removed": 0,
  "lines_modified": 2,
  "s3_version_id": "version-id-from-s3",
  "ingestion_job_id": "job-id-abc123",
  "ingestion_status": "COMPLETE",
  "ingestion_completed_at": "2026-02-24T17:02:30Z"
}
```

**DynamoDB Table: kb-contributor-stats** (NEW)
```json
{
  "user_id": "cognito-sub-123",
  "user_email": "user@example.com",
  "user_display_name": "John Doe",
  "total_edits": 15,
  "total_lines_added": 98,
  "total_lines_removed": 12,
  "total_lines_modified": 23,
  "documents_edited": ["curated-qa/common-questions.md", "service-mappings/service-renames.md"],
  "documents_edited_count": 6,
  "first_contribution": "2026-01-15T10:00:00Z",
  "last_contribution": "2026-02-24T17:00:00Z",
  "monthly_stats": {
    "2026-02": {
      "edits": 8,
      "lines_added": 45,
      "rank": 3
    },
    "2026-01": {
      "edits": 7,
      "lines_added": 53,
      "rank": 5
    }
  },
  "badges": ["first_edit", "10_edits", "top_contributor_feb_2026"]
}
```

**Why Separate Tables?**
- `kb-edit-history`: Immutable audit log (never updated, only appended)
- `kb-contributor-stats`: Aggregated stats (updated on each edit for fast leaderboard queries)
- Separation allows efficient queries for both audit trail and leaderboard
- Stats table can be rebuilt from history if needed

---

## 📝 API Specification

### GET /kb-documents

**Request:**
```http
GET /kb-documents HTTP/1.1
Authorization: Bearer <jwt-token>
```

**Response:**
```json
{
  "documents": [
    {
      "id": "curated-qa/common-questions.md",
      "name": "Common Questions (Q&A)",
      "description": "Frequently asked questions about EUC services",
      "size": 12543,
      "last_modified": "2026-02-24T15:30:00Z",
      "question_count": 12,
      "category": "Q&A"
    },
    {
      "id": "service-mappings/service-renames.md",
      "name": "Service Renames & History",
      "description": "Complete history of EUC service name changes",
      "size": 8234,
      "last_modified": "2026-02-17T10:00:00Z",
      "service_count": 8,
      "category": "Mappings"
    }
  ]
}
```

### GET /kb-document/{document_id}

**Request:**
```http
GET /kb-document/curated-qa%2Fcommon-questions.md HTTP/1.1
Authorization: Bearer <jwt-token>
```

**Response:**
```json
{
  "document_id": "curated-qa/common-questions.md",
  "name": "Common Questions (Q&A)",
  "content": "# Common Questions\n\n## Q: What is EUC?\n**A:** ...",
  "metadata": {
    "size": 12543,
    "last_modified": "2026-02-24T15:30:00Z",
    "version_id": "s3-version-id",
    "question_count": 12
  }
}
```

### PUT /kb-document/{document_id}

**Request:**
```http
PUT /kb-document/curated-qa%2Fcommon-questions.md HTTP/1.1
Authorization: Bearer <jwt-token>
Content-Type: application/json

{
  "content": "# Common Questions\n\n## Q: What is EUC?\n**A:** ...",
  "change_comment": "Added Q&A about WorkSpaces Pools and updated pricing info"
}
```

**Validation:**
- `content`: Required, max 100KB, valid markdown
- `change_comment`: **REQUIRED**, min 10 characters, max 500 characters

**Response:**
```json
{
  "success": true,
  "document_id": "curated-qa/common-questions.md",
  "edit_id": "uuid-v4",
  "s3_version_id": "new-version-id",
  "ingestion_job_id": "abc123xyz",
  "ingestion_status": "IN_PROGRESS",
  "contribution_points": 10,
  "message": "Document updated successfully. Ingestion in progress."
}
```

### GET /kb-contributors

**Request:**
```http
GET /kb-contributors?period=month&limit=10 HTTP/1.1
Authorization: Bearer <jwt-token>
```

**Query Parameters:**
- `period`: "week", "month", "year", "all" (default: "month")
- `limit`: Number of contributors to return (default: 10, max: 100)

**Response:**
```json
{
  "period": "month",
  "period_start": "2026-02-01T00:00:00Z",
  "period_end": "2026-02-29T23:59:59Z",
  "contributors": [
    {
      "rank": 1,
      "user_id": "cognito-sub-456",
      "display_name": "Sarah Chen",
      "email": "sarah@example.com",
      "total_edits": 23,
      "lines_added": 156,
      "documents_edited": 12,
      "latest_contribution": {
        "timestamp": "2026-02-24T15:00:00Z",
        "document": "Common Questions (Q&A)",
        "comment": "Updated AppStream 2.0 pricing"
      }
    },
    {
      "rank": 2,
      "user_id": "cognito-sub-789",
      "display_name": "Mike Johnson",
      "email": "mike@example.com",
      "total_edits": 18,
      "lines_added": 134,
      "documents_edited": 8,
      "latest_contribution": {
        "timestamp": "2026-02-23T10:00:00Z",
        "document": "Service Renames & History",
        "comment": "Added WorkSpaces Pools Q&A"
      }
    }
  ]
}
```

### GET /kb-my-contributions

**Request:**
```http
GET /kb-my-contributions?limit=20 HTTP/1.1
Authorization: Bearer <jwt-token>
```

**Query Parameters:**
- `limit`: Number of recent contributions to return (default: 20, max: 100)

**Response:**
```json
{
  "user_id": "cognito-sub-123",
  "display_name": "John Doe",
  "email": "user@example.com",
  "stats": {
    "total_edits": 15,
    "total_lines_added": 98,
    "total_lines_removed": 12,
    "documents_edited_count": 6,
    "first_contribution": "2026-01-15T10:00:00Z",
    "last_contribution": "2026-02-24T17:00:00Z",
    "current_month_rank": 3,
    "badges": ["first_edit", "10_edits", "top_contributor_feb_2026"]
  },
  "recent_contributions": [
    {
      "edit_id": "uuid-1",
      "document_id": "curated-qa/common-questions.md",
      "document_name": "Common Questions (Q&A)",
      "timestamp": "2026-02-24T17:00:00Z",
      "change_comment": "Added Q&A about WorkSpaces Pools",
      "lines_added": 12,
      "lines_removed": 0,
      "lines_modified": 2
    },
    {
      "edit_id": "uuid-2",
      "document_id": "service-mappings/service-renames.md",
      "document_name": "Service Renames & History",
      "timestamp": "2026-02-17T14:30:00Z",
      "change_comment": "Fixed WorkSpaces rename date",
      "lines_added": 2,
      "lines_removed": 1,
      "lines_modified": 0
    }
  ]
}
```

### GET /kb-ingestion-status/{job_id}

**Request:**
```http
GET /kb-ingestion-status/abc123xyz HTTP/1.1
Authorization: Bearer <jwt-token>
```

**Response:**
```json
{
  "job_id": "abc123xyz",
  "status": "COMPLETE",
  "started_at": "2026-02-24T17:00:00Z",
  "completed_at": "2026-02-24T17:02:30Z",
  "statistics": {
    "documents_scanned": 4,
    "documents_modified": 1,
    "documents_deleted": 0
  }
}
```

---

## 🛠️ Implementation Plan

### Phase 1: Backend API & Database (Priority: High)

**Files to Create:**
- `kb_editor_lambda.py` - New Lambda or extend `api_lambda.py`
- `create_kb_tables.py` - Create DynamoDB tables
- `test_kb_editor_api.py` - API tests

**DynamoDB Tables to Create:**
1. `kb-edit-history` - Immutable audit log
   - Primary Key: `edit_id` (String)
   - GSI: `user_id-timestamp-index` for user history
   - GSI: `document_id-timestamp-index` for document history

2. `kb-contributor-stats` - Aggregated contributor statistics
   - Primary Key: `user_id` (String)
   - GSI: `monthly_rank-index` for leaderboard queries

**API Endpoints to Implement:**
1. GET /kb-documents - List all KB documents
2. GET /kb-document/{id} - Get document content
3. PUT /kb-document/{id} - Update document (requires change_comment)
4. GET /kb-ingestion-status/{id} - Check ingestion status
5. GET /kb-contributors - Get leaderboard
6. GET /kb-my-contributions - Get user's contribution stats

**Tasks:**
1. Create DynamoDB tables with GSIs
2. Implement all 6 API endpoints
3. Add change comment validation (required, 10-500 chars)
4. Calculate line diffs (added/removed/modified)
5. Update contributor stats on each edit
6. Update IAM role with S3 write + Bedrock + DynamoDB permissions
7. Add input validation and sanitization
8. Add rate limiting (5 edits per hour)
9. Test all endpoints

**Estimated Time:** 6-8 hours

### Phase 2: Frontend UI (Priority: High)

**Files to Create:**
- `frontend/kb-editor.js` - KB editor component
- `frontend/kb-editor.css` - Styles
- `frontend/kb-contributors.js` - Contributor dashboard

**Files to Modify:**
- `frontend/profile.js` - Add menu items (Manage KB, View Contributions)
- `frontend/index.html` - Include new scripts

**Tasks:**
1. Add "Manage Knowledge Base" to profile dropdown
2. Add "KB Contributions" to profile dropdown
3. Show contributor rank in profile dropdown
4. Create KB editor modal (list view)
5. Create markdown editor (edit view)
6. Add save confirmation dialog with required change comment field
7. Integrate markdown library (EasyMDE)
8. Add save functionality with API calls
9. Add ingestion status polling
10. Create contributor leaderboard modal
11. Create "My Contributions" modal
12. Add contribution points notification
13. Add error handling and validation
14. Style all components

**Estimated Time:** 8-10 hours

### Phase 3: Contributor Features (Priority: High)

**Tasks:**
1. Implement leaderboard calculation logic
2. Add monthly rank tracking
3. Create badge system (first_edit, 10_edits, top_contributor, etc.)
4. Add contribution points system
5. Create admin view for all contributions (future)
6. Add email notifications for milestones (optional)

**Estimated Time:** 3-4 hours

### Phase 4: Testing & Deployment (Priority: High)

**Tasks:**
1. Test in staging environment
2. Test with multiple users
3. Test change comment validation
4. Test leaderboard calculations
5. Test contribution tracking
6. Test ingestion process
7. Test rollback capability (S3 versioning)
8. Deploy to staging
9. User acceptance testing
10. Deploy to production

**Estimated Time:** 4-5 hours

**Total Estimated Time:** 21-27 hours (increased from 15-20 due to new features)

---

## 📊 Success Metrics

### User Engagement
- Number of KB edits per week
- Number of unique editors
- Average time spent editing

### Quality Metrics
- Chatbot response accuracy improvement
- User satisfaction with chatbot responses
- Number of "Can't find what you're looking for?" clicks

### Technical Metrics
- API response times
- Ingestion job success rate
- S3 storage usage
- Error rates

---

## 🚀 Future Enhancements

### Version Control & Rollback
- View edit history for each document
- Compare versions (diff view)
- Rollback to previous version
- Approve/reject changes workflow

### Collaboration Features
- Multiple users editing simultaneously
- Comments and suggestions
- Change requests (like GitHub PRs)
- Notifications for changes

### Advanced Editor Features
- Markdown templates
- Auto-save drafts
- Spell check
- AI-assisted writing (suggest improvements)

### Analytics Dashboard
- Most edited documents
- Most active contributors
- Impact of edits on chatbot performance
- Popular questions not in KB

### Content Management
- Add new documents (not just edit existing)
- Delete documents
- Organize documents in folders
- Tag documents by topic

---

## 💰 Cost Impact

### Additional Costs

**DynamoDB (Audit Trail + Contributor Stats):**
- On-demand pricing
- Two tables: `kb-edit-history` and `kb-contributor-stats`
- ~$0.25 per million write requests
- ~$0.25 per million read requests
- Estimated: $2-3/month (increased due to leaderboard queries)

**S3 (Versioning):**
- Storage for all versions
- Estimated: $0.50-1/month

**Lambda (Additional API calls):**
- 6 new endpoints (was 4)
- Leaderboard queries add overhead
- Estimated: $0.20/month

**Bedrock (Ingestion Jobs):**
- Charged per ingestion
- ~$0.01 per ingestion
- Estimated: $5-10/month (assuming 500-1000 edits)

**Total Additional Cost:** ~$8-15/month (increased from $7-14 due to contributor features)

---

## 🔐 Security Considerations

### Threats & Mitigations

**1. Malicious Content Injection**
- Threat: User injects harmful content
- Mitigation: Content sanitization, markdown-only, no HTML/scripts

**2. Unauthorized Access**
- Threat: Non-authenticated users access editor
- Mitigation: JWT validation on all endpoints

**3. Rate Limiting Bypass**
- Threat: User floods system with edits
- Mitigation: Rate limiting per user (5 edits/hour)

**4. Data Loss**
- Threat: Accidental deletion or corruption
- Mitigation: S3 versioning, audit trail, rollback capability

**5. Privilege Escalation**
- Threat: User gains admin access
- Mitigation: Role-based access control (future), audit logging

---

## 📚 Dependencies

### Frontend Libraries

**Markdown Editor:**
- **Option 1**: EasyMDE (recommended)
  - Lightweight, simple, good preview
  - MIT license
  - CDN: https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.js

- **Option 2**: SimpleMDE
  - Similar to EasyMDE
  - Slightly older

- **Option 3**: Toast UI Editor
  - More features, heavier
  - WYSIWYG mode

**Recommendation:** EasyMDE for simplicity and performance

### Backend Libraries
- boto3 (already installed) - AWS SDK
- No additional dependencies needed

---

## 🧪 Testing Strategy

### Unit Tests
- API endpoint validation
- Input sanitization
- JWT validation
- S3 upload/download
- Ingestion job triggering

### Integration Tests
- End-to-end edit flow
- Ingestion status polling
- Rollback functionality
- Multi-user scenarios

### User Acceptance Tests
- Edit and save document
- View ingestion status
- Verify chatbot uses updated content
- Test on mobile devices

---

## 📖 Documentation Needed

### User Documentation
- How to edit KB documents
- Markdown formatting guide
- Best practices for Q&A
- Service rename format

### Developer Documentation
- API endpoint documentation
- Deployment guide
- Troubleshooting guide
- Architecture diagrams

---

## ✅ Acceptance Criteria

### Must Have (MVP)
- [ ] Authenticated users can view list of KB documents
- [ ] Users can edit KB documents in markdown
- [ ] Changes are saved to S3
- [ ] Ingestion job is triggered automatically
- [ ] Users see ingestion status
- [ ] Changes appear in chatbot responses after ingestion
- [ ] Input validation prevents malicious content
- [ ] Audit trail logs all edits

### Should Have
- [ ] Live markdown preview
- [ ] Character counter
- [ ] Undo/redo support
- [ ] Mobile responsive design
- [ ] Error handling with user-friendly messages

### Nice to Have
- [ ] Version history view
- [ ] Rollback capability
- [ ] Diff view for changes
- [ ] Auto-save drafts
- [ ] Collaboration features

---

## 🎯 Next Steps

1. **Review & Approve Design** - Get stakeholder approval
2. **Create GitHub Issue** - Track implementation
3. **Start Phase 1** - Implement backend API
4. **Deploy to Staging** - Test with real users
5. **Iterate Based on Feedback** - Improve UX
6. **Deploy to Production** - Roll out to all users

---

## 📞 Questions to Answer

1. **Who can edit?** All authenticated users or specific roles?
   - **Recommendation:** Start with all authenticated users in staging

2. **Approval workflow?** Do edits need approval before going live?
   - **Recommendation:** No approval for staging, consider for production

3. **Notification?** Should admins be notified of edits?
   - **Recommendation:** Email notification for production edits

4. **Limits?** How many edits per user per day?
   - **Recommendation:** 5 edits per hour, 20 per day

5. **Rollback?** Who can rollback changes?
   - **Recommendation:** Admins only (future feature)

---

## 🎉 Conclusion

This feature will enable community-driven improvements to the Knowledge Base, making the chatbot more accurate and helpful over time. The implementation is straightforward with existing AWS services and can be deployed incrementally.

**Estimated Total Time:** 15-20 hours  
**Estimated Cost:** $7-14/month additional  
**User Value:** High - enables self-service KB improvements  
**Technical Risk:** Low - uses existing AWS services  

**Recommendation:** Proceed with implementation, starting with Phase 1 (Backend API).


---

## 🏆 Contributor Tracking & Gamification

### Change Comment Requirement

**Mandatory Field:**
- Every edit MUST include a change comment
- Minimum: 10 characters
- Maximum: 500 characters
- Purpose: Document why changes were made for audit trail

**Validation:**
- Client-side: Show error if comment is too short/long
- Server-side: Reject request if comment is missing or invalid
- User-friendly error messages

**Examples of Good Comments:**
- ✅ "Added Q&A about WorkSpaces Pools pricing and availability"
- ✅ "Fixed incorrect date for WorkSpaces Personal rename (was Nov 15, should be Nov 18)"
- ✅ "Updated AppStream 2.0 section to reflect new name: WorkSpaces Applications"
- ❌ "Updated" (too vague)
- ❌ "Fixed typo" (not descriptive enough)

### Tracking System

**What We Track:**
1. **User Information**
   - User ID (Cognito sub)
   - Email address
   - Display name
   - First contribution date

2. **Edit Details**
   - Document edited
   - Timestamp
   - Change comment (required)
   - Content before/after (hashes for comparison)
   - Lines added/removed/modified
   - S3 version ID
   - Ingestion job ID and status

3. **Aggregated Stats**
   - Total edits per user
   - Total lines added/removed/modified
   - Number of unique documents edited
   - Monthly contribution counts
   - Leaderboard rank

### Leaderboard System

**Ranking Criteria:**
- Primary: Number of edits in period
- Secondary: Lines added (tiebreaker)
- Tertiary: Number of documents edited (tiebreaker)

**Time Periods:**
- This Week (last 7 days)
- This Month (current calendar month)
- This Year (current calendar year)
- All Time (since launch)

**Display:**
- Top 10 contributors shown by default
- User's own rank always visible
- Medal icons for top 3 (🥇🥈🥉)
- Latest contribution shown for each user

### Contribution Points

**Point System:**
- Base edit: 10 points
- First edit ever: +50 bonus points
- Large edit (>50 lines): +20 points
- New document: +30 points
- Consistent contributor (5+ edits/month): +25 monthly bonus

**Purpose:**
- Gamification to encourage contributions
- Recognition for active contributors
- Future: Unlock badges and achievements

### Badge System (Future Enhancement)

**Badges to Implement:**
- 🌟 First Edit - Made your first contribution
- 📝 10 Edits - Completed 10 edits
- 🔥 Streak Master - 7 consecutive days with edits
- 🏆 Top Contributor - #1 contributor for a month
- 📚 Document Master - Edited all documents
- 🎯 Precision Editor - 10 edits with <5 lines each
- 🚀 Power User - 50+ total edits

### Privacy & Data Usage

**What's Public:**
- Display name
- Total contribution counts
- Leaderboard rank
- Recent contribution summaries (document + comment)

**What's Private:**
- Email address (only visible to admins)
- Full edit history (only visible to user and admins)
- Detailed content changes (only visible to admins)

**User Control:**
- Users can view their own full history
- Users can see their rank and stats
- Future: Option to hide from leaderboard

---

## 📊 Database Schema Details

### Table: kb-edit-history

**Purpose:** Immutable audit log of all KB edits

**Primary Key:**
- `edit_id` (String) - UUID v4

**Attributes:**
- `user_id` (String) - Cognito sub
- `user_email` (String)
- `user_display_name` (String)
- `document_id` (String) - S3 key
- `document_name` (String) - Human-readable name
- `timestamp` (String) - ISO 8601 format
- `change_comment` (String) - Required, 10-500 chars
- `content_before_hash` (String) - SHA256 hash
- `content_after_hash` (String) - SHA256 hash
- `lines_added` (Number)
- `lines_removed` (Number)
- `lines_modified` (Number)
- `s3_version_id` (String)
- `ingestion_job_id` (String)
- `ingestion_status` (String) - IN_PROGRESS, COMPLETE, FAILED
- `ingestion_completed_at` (String) - ISO 8601 format

**Global Secondary Indexes:**

1. **user_id-timestamp-index**
   - Partition Key: `user_id`
   - Sort Key: `timestamp`
   - Purpose: Query user's edit history

2. **document_id-timestamp-index**
   - Partition Key: `document_id`
   - Sort Key: `timestamp`
   - Purpose: Query document's edit history

**Access Patterns:**
- Get all edits by user (sorted by time)
- Get all edits for a document (sorted by time)
- Get recent edits across all users (scan with filter)

### Table: kb-contributor-stats

**Purpose:** Aggregated contributor statistics for fast leaderboard queries

**Primary Key:**
- `user_id` (String) - Cognito sub

**Attributes:**
- `user_email` (String)
- `user_display_name` (String)
- `total_edits` (Number)
- `total_lines_added` (Number)
- `total_lines_removed` (Number)
- `total_lines_modified` (Number)
- `documents_edited` (List of Strings) - Document IDs
- `documents_edited_count` (Number)
- `first_contribution` (String) - ISO 8601 format
- `last_contribution` (String) - ISO 8601 format
- `monthly_stats` (Map) - Nested stats by month
  - Key: "YYYY-MM" (e.g., "2026-02")
  - Value: { edits, lines_added, rank }
- `badges` (List of Strings) - Badge IDs earned
- `total_points` (Number) - Gamification points

**Global Secondary Indexes:**

1. **monthly_rank-index**
   - Partition Key: `month` (String, e.g., "2026-02")
   - Sort Key: `monthly_edits` (Number)
   - Purpose: Fast leaderboard queries for current month

**Access Patterns:**
- Get user's stats by user_id
- Get top N contributors for a month (leaderboard)
- Get user's rank for a month

**Update Strategy:**
- Updated atomically on each edit using UpdateExpression
- Increment counters, append to lists
- Recalculate rank periodically (daily cron job)

---

## 🎯 Updated Acceptance Criteria

### Must Have (MVP)
- [ ] Authenticated users can view list of KB documents
- [ ] Users can edit KB documents in markdown
- [ ] **Users MUST enter a change comment (10-500 chars) before saving**
- [ ] Changes are saved to S3 with version tracking
- [ ] Ingestion job is triggered automatically
- [ ] Users see ingestion status
- [ ] Changes appear in chatbot responses after ingestion
- [ ] Input validation prevents malicious content
- [ ] **All edits logged to kb-edit-history table with full details**
- [ ] **Contributor stats updated in kb-contributor-stats table**
- [ ] **Users can view leaderboard (top 10 contributors)**
- [ ] **Users can view their own contribution stats**
- [ ] **User's rank shown in profile dropdown**

### Should Have
- [ ] Live markdown preview
- [ ] Character counter for change comment
- [ ] Undo/redo support in editor
- [ ] Mobile responsive design
- [ ] Error handling with user-friendly messages
- [ ] **Contribution points awarded and displayed**
- [ ] **Medal icons for top 3 contributors**
- [ ] **"My Contributions" view with recent edits**

### Nice to Have
- [ ] Version history view
- [ ] Rollback capability
- [ ] Diff view for changes
- [ ] Auto-save drafts
- [ ] **Badge system with achievements**
- [ ] **Email notifications for milestones**
- [ ] **Weekly/monthly contributor digest**

---

## 🎉 Updated Conclusion

This enhanced feature will enable community-driven improvements to the Knowledge Base with full tracking, accountability, and gamification to encourage quality contributions.

**Key Enhancements:**
- ✅ Mandatory change comments for accountability
- ✅ Comprehensive tracking of who, what, when, why
- ✅ Contributor leaderboard for recognition
- ✅ Personal contribution dashboard
- ✅ Gamification with points and badges
- ✅ Two-table design for efficient queries

**Estimated Total Time:** 21-27 hours (increased from 15-20)  
**Estimated Cost:** $8-15/month additional (increased from $7-14)  
**User Value:** Very High - enables community contributions with recognition  
**Technical Risk:** Low - uses existing AWS services  

**Recommendation:** Proceed with implementation, starting with Phase 1 (Backend API & Database).

**Next Steps:**
1. Review and approve updated design
2. Create GitHub issue for tracking
3. Implement Phase 1 (Backend API & Database)
4. Implement Phase 2 (Frontend UI)
5. Implement Phase 3 (Contributor Features)
6. Deploy to staging and test
7. Deploy to production
