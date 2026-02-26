# KB Editor Fix Plan

## Issues Identified

### Issue 1: Missing Lambda Functions
**Problem**: The KB editor handler functions (`handle_get_kb_documents`, etc.) are missing from the deployed Lambda code.

**Evidence**: CloudWatch logs show `Error: name 'handle_get_kb_documents' is not defined`

**Root Cause**: The functions were documented as added in yesterday's session but were never actually added to the `api_lambda_deploy/lambda_function.py` file.

### Issue 2: JWT Token is Null
**Problem**: Frontend is sending `"Bearer null"` instead of the actual JWT token.

**Evidence**: CloudWatch logs show `"Authorization": ["Bearer null"]`

**Root Cause**: The token retrieval in `kb-editor.js` uses `localStorage.getItem('id_token')` but the token might be stored under a different key or not available when the KB editor loads.

## Solution

### Step 1: Add KB Editor Functions to Lambda

Add these functions to `api_lambda_deploy/lambda_function.py` (after the existing handler functions, around line 600):

```python
# ============================================================================
# KB EDITOR ENDPOINTS
# ============================================================================

# KB Configuration
KB_S3_BUCKET = 'euc-content-hub-kb-staging'
KB_ID = 'MIMYGSK1YU'
KB_DATA_SOURCE_ID = 'XC68GVBFXK'

# KB Documents metadata
KB_DOCUMENTS = [
    {
        'id': 'euc-qa-pairs',
        'name': 'EUC Q&A Pairs',
        'description': 'Common questions and answers about AWS EUC services',
        'category': 'Q&A',
        's3_key': 'euc-qa-pairs.txt',
        'question_count': 50
    },
    {
        'id': 'euc-service-mappings',
        'name': 'EUC Service Mappings',
        'description': 'Mappings between EUC services and AWS services',
        'category': 'Reference',
        's3_key': 'euc-service-mappings.txt',
        'service_count': 25
    }
]

@require_auth
def handle_get_kb_documents(event):
    """GET /kb-documents - List all KB documents"""
    try:
        s3 = boto3.client('s3')
        
        # Enrich documents with S3 metadata
        enriched_docs = []
        for doc in KB_DOCUMENTS:
            try:
                # Get S3 object metadata
                response = s3.head_object(
                    Bucket=KB_S3_BUCKET,
                    Key=doc['s3_key']
                )
                doc_copy = doc.copy()
                doc_copy['size'] = response['ContentLength']
                doc_copy['last_modified'] = response['LastModified'].isoformat()
                enriched_docs.append(doc_copy)
            except Exception as e:
                print(f"Error getting metadata for {doc['id']}: {str(e)}")
                # Include document even if metadata fetch fails
                doc_copy = doc.copy()
                doc_copy['size'] = 0
                doc_copy['last_modified'] = None
                enriched_docs.append(doc_copy)
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'documents': enriched_docs
            })
        }
    
    except Exception as e:
        print(f"Error in handle_get_kb_documents: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to load documents', 'message': str(e)})
        }

@require_auth
def handle_get_kb_document(event, document_id):
    """GET /kb-document/{document_id} - Get KB document content"""
    try:
        # Find document metadata
        doc_meta = next((d for d in KB_DOCUMENTS if d['id'] == document_id), None)
        if not doc_meta:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Document not found'})
            }
        
        # Get document content from S3
        s3 = boto3.client('s3')
        response = s3.get_object(
            Bucket=KB_S3_BUCKET,
            Key=doc_meta['s3_key']
        )
        content = response['Body'].read().decode('utf-8')
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'document': {
                    **doc_meta,
                    'content': content,
                    'size': len(content),
                    'line_count': content.count('\n') + 1
                }
            })
        }
    
    except Exception as e:
        print(f"Error in handle_get_kb_document: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to load document', 'message': str(e)})
        }

@require_auth
def handle_update_kb_document(event, document_id, body):
    """PUT /kb-document/{document_id} - Update KB document"""
    try:
        user = event['user']
        user_id = user['sub']
        
        # Validate request
        new_content = body.get('content')
        change_comment = body.get('change_comment', '').strip()
        
        if not new_content:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Content is required'})
            }
        
        if not change_comment or len(change_comment) < 10:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Change comment must be at least 10 characters'})
            }
        
        if len(change_comment) > 500:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Change comment must be less than 500 characters'})
            }
        
        # Find document metadata
        doc_meta = next((d for d in KB_DOCUMENTS if d['id'] == document_id), None)
        if not doc_meta:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Document not found'})
            }
        
        # Get current content from S3
        s3 = boto3.client('s3')
        try:
            response = s3.get_object(
                Bucket=KB_S3_BUCKET,
                Key=doc_meta['s3_key']
            )
            old_content = response['Body'].read().decode('utf-8')
        except s3.exceptions.NoSuchKey:
            old_content = ''
        
        # Calculate content hashes
        import hashlib
        old_hash = hashlib.sha256(old_content.encode()).hexdigest()
        new_hash = hashlib.sha256(new_content.encode()).hexdigest()
        
        # Check if content actually changed
        if old_hash == new_hash:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'No changes detected'})
            }
        
        # Calculate line changes
        old_lines = old_content.split('\n')
        new_lines = new_content.split('\n')
        lines_added = max(0, len(new_lines) - len(old_lines))
        lines_removed = max(0, len(old_lines) - len(new_lines))
        
        # Upload new content to S3
        s3.put_object(
            Bucket=KB_S3_BUCKET,
            Key=doc_meta['s3_key'],
            Body=new_content.encode('utf-8'),
            ContentType='text/plain'
        )
        
        # Get S3 version ID
        response = s3.head_object(
            Bucket=KB_S3_BUCKET,
            Key=doc_meta['s3_key']
        )
        version_id = response.get('VersionId', 'unknown')
        
        # Record edit in DynamoDB
        edit_history_table = dynamodb.Table('kb-edit-history' + TABLE_SUFFIX)
        edit_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        edit_history_table.put_item(
            Item={
                'edit_id': edit_id,
                'user_id': user_id,
                'document_id': document_id,
                'timestamp': timestamp,
                'change_comment': change_comment,
                'content_hash_before': old_hash,
                'content_hash_after': new_hash,
                'lines_added': lines_added,
                'lines_removed': lines_removed,
                's3_version_id': version_id
            }
        )
        
        # Update contributor stats
        contributor_stats_table = dynamodb.Table('kb-contributor-stats' + TABLE_SUFFIX)
        
        # Calculate points (10 base + bonuses)
        points = 10
        if lines_added > 50:
            points += 5  # Substantial addition
        if len(change_comment) > 100:
            points += 2  # Detailed comment
        
        # Update stats
        contributor_stats_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='''
                SET total_edits = if_not_exists(total_edits, :zero) + :one,
                    total_lines_added = if_not_exists(total_lines_added, :zero) + :lines_added,
                    total_lines_removed = if_not_exists(total_lines_removed, :zero) + :lines_removed,
                    total_points = if_not_exists(total_points, :zero) + :points,
                    last_edit_timestamp = :timestamp,
                    display_name = if_not_exists(display_name, :email)
            ''',
            ExpressionAttributeValues={
                ':zero': 0,
                ':one': 1,
                ':lines_added': lines_added,
                ':lines_removed': lines_removed,
                ':points': points,
                ':timestamp': timestamp,
                ':email': user.get('email', 'Unknown')
            }
        )
        
        # Trigger Bedrock ingestion
        bedrock_agent = boto3.client('bedrock-agent')
        try:
            ingestion_response = bedrock_agent.start_ingestion_job(
                knowledgeBaseId=KB_ID,
                dataSourceId=KB_DATA_SOURCE_ID
            )
            ingestion_job_id = ingestion_response['ingestionJob']['ingestionJobId']
        except Exception as e:
            print(f"Error starting ingestion job: {str(e)}")
            ingestion_job_id = None
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'success': True,
                'edit_id': edit_id,
                'points_earned': points,
                'ingestion_job_id': ingestion_job_id,
                'changes': {
                    'lines_added': lines_added,
                    'lines_removed': lines_removed
                }
            })
        }
    
    except Exception as e:
        print(f"Error in handle_update_kb_document: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to update document', 'message': str(e)})
        }

@require_auth
def handle_get_kb_contributors(event):
    """GET /kb-contributors - Get contributor leaderboard"""
    try:
        query_params = event.get('queryStringParameters') or {}
        period = query_params.get('period', 'all')  # all, month, week
        limit = int(query_params.get('limit', 10))
        
        contributor_stats_table = dynamodb.Table('kb-contributor-stats' + TABLE_SUFFIX)
        
        # Scan all contributors
        response = contributor_stats_table.scan()
        contributors = response.get('Items', [])
        
        # Filter by period if needed
        if period != 'all':
            # For now, return all (period filtering would require monthly_stats field)
            pass
        
        # Sort by total_points
        contributors.sort(key=lambda x: x.get('total_points', 0), reverse=True)
        
        # Limit results
        contributors = contributors[:limit]
        
        # Add rank
        for i, contributor in enumerate(contributors):
            contributor['rank'] = i + 1
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'contributors': contributors,
                'period': period
            }, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error in handle_get_kb_contributors: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to load contributors', 'message': str(e)})
        }

@require_auth
def handle_get_my_contributions(event):
    """GET /kb-my-contributions - Get current user's contributions"""
    try:
        user = event['user']
        user_id = user['sub']
        
        # Get user stats
        contributor_stats_table = dynamodb.Table('kb-contributor-stats' + TABLE_SUFFIX)
        response = contributor_stats_table.get_item(Key={'user_id': user_id})
        stats = response.get('Item', {
            'user_id': user_id,
            'total_edits': 0,
            'total_lines_added': 0,
            'total_lines_removed': 0,
            'total_points': 0
        })
        
        # Get recent edits
        edit_history_table = dynamodb.Table('kb-edit-history' + TABLE_SUFFIX)
        response = edit_history_table.query(
            IndexName='user_id-timestamp-index',
            KeyConditionExpression='user_id = :user_id',
            ExpressionAttributeValues={':user_id': user_id},
            ScanIndexForward=False,  # Newest first
            Limit=10
        )
        recent_edits = response.get('Items', [])
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'stats': stats,
                'recent_edits': recent_edits
            }, cls=DecimalEncoder)
        }
    
    except Exception as e:
        print(f"Error in handle_get_my_contributions: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to load contributions', 'message': str(e)})
        }

@require_auth
def handle_get_ingestion_status(event, job_id):
    """GET /kb-ingestion-status/{job_id} - Check ingestion job status"""
    try:
        bedrock_agent = boto3.client('bedrock-agent')
        
        response = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=KB_ID,
            dataSourceId=KB_DATA_SOURCE_ID,
            ingestionJobId=job_id
        )
        
        job = response['ingestionJob']
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'status': job['status'],
                'started_at': job.get('startedAt', '').isoformat() if job.get('startedAt') else None,
                'completed_at': job.get('updatedAt', '').isoformat() if job.get('updatedAt') else None
            })
        }
    
    except Exception as e:
        print(f"Error in handle_get_ingestion_status: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Failed to check ingestion status', 'message': str(e)})
        }
```

### Step 2: Update Lambda Handler Routing

In the `lambda_handler` function, add these routes (around line 556):

```python
        # KB Editor endpoints
        elif path == '/kb-documents' and http_method == 'GET':
            return handle_get_kb_documents(event)
        elif path.startswith('/kb-document/') and not path.endswith('/kb-document/') and http_method == 'GET':
            document_id = path.split('/')[-1]
            return handle_get_kb_document(event, document_id)
        elif path.startswith('/kb-document/') and not path.endswith('/kb-document/') and http_method == 'PUT':
            document_id = path.split('/')[-1]
            return handle_update_kb_document(event, document_id, body)
        elif path == '/kb-contributors' and http_method == 'GET':
            return handle_get_kb_contributors(event)
        elif path == '/kb-my-contributions' and http_method == 'GET':
            return handle_get_my_contributions(event)
        elif path.startswith('/kb-ingestion-status/') and http_method == 'GET':
            job_id = path.split('/')[-1]
            return handle_get_ingestion_status(event, job_id)
```

### Step 3: Fix JWT Token Retrieval in Frontend

The issue is that `localStorage.getItem('id_token')` returns `null`. We need to check how the token is actually stored. Looking at the auth flow, the token should be available from the auth manager.

Update `frontend/kb-editor.js` line 70:

```javascript
async loadDocuments() {
    const listContainer = document.getElementById('kbDocumentList');
    
    try {
        // Get token from auth manager (not directly from localStorage)
        const token = window.authManager?.getIdToken();
        
        if (!token) {
            throw new Error('Not authenticated');
        }
        
        const response = await fetch(`${API_ENDPOINT}/kb-documents`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        // ... rest of function
    }
}
```

We also need to add a `getIdToken()` method to the auth manager if it doesn't exist. Check `frontend/auth.js` for the AuthManager class and add:

```javascript
getIdToken() {
    return localStorage.getItem('id_token');
}
```

## Deployment Steps

1. **Add KB editor functions to Lambda**:
   - Open `api_lambda_deploy/lambda_function.py`
   - Add the KB editor functions after existing handlers
   - Add the routing in `lambda_handler`

2. **Deploy Lambda to staging**:
   ```bash
   python deploy_lambda.py api_lambda staging
   ```

3. **Fix frontend token retrieval**:
   - Update `frontend/kb-editor.js` to use `window.authManager.getIdToken()`
   - Add `getIdToken()` method to AuthManager if needed

4. **Deploy frontend to staging**:
   ```bash
   python deploy_frontend.py staging
   ```

5. **Test**:
   - Visit https://staging.awseuccontent.com
   - Sign in
   - Click "Edit Knowledge Base"
   - Verify documents load

## Testing Checklist

- [ ] Lambda functions added
- [ ] Lambda deployed to staging
- [ ] Frontend token fix applied
- [ ] Frontend deployed to staging
- [ ] Can open KB editor modal
- [ ] Documents list loads
- [ ] Can view document content
- [ ] Can edit and save document
- [ ] Contribution stats update
- [ ] Leaderboard displays

## Rollback Plan

If issues occur:

1. **Lambda rollback**:
   ```bash
   aws lambda update-alias --function-name aws-blog-api \
     --name staging --function-version <previous-version>
   ```

2. **Frontend rollback**:
   ```bash
   git checkout <previous-commit>
   python deploy_frontend.py staging
   ```
