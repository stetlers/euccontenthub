# KB Editor Testing Checklist

Use this checklist to verify the KB editor is working correctly.

## Pre-Test Setup

- [ ] Visit https://staging.awseuccontent.com
- [ ] Sign in with your Google account
- [ ] Verify you're signed in (see your name in top right)

## Test 1: Open KB Editor

- [ ] Click your profile dropdown (top right)
- [ ] Click "📚 Edit Knowledge Base"
- [ ] Modal opens successfully
- [ ] See 2 documents listed:
  - [ ] EUC Q&A Pairs
  - [ ] EUC Service Mappings

## Test 2: View Document

- [ ] Click "EUC Q&A Pairs"
- [ ] Document content loads in editor
- [ ] Content is readable and formatted
- [ ] No JavaScript errors in console

## Test 3: Edit Document

- [ ] Make a small edit (add a line, fix typo, etc.)
- [ ] Add a change comment in the text box
- [ ] Comment is at least 10 characters
- [ ] "Save Changes" button is enabled

## Test 4: Save Changes

- [ ] Click "Save Changes"
- [ ] See success message
- [ ] Message shows ingestion job ID
- [ ] Message shows points earned
- [ ] No errors in console

## Test 5: Verify Edit History

- [ ] Click "My Contributions" tab
- [ ] See your recent edit listed
- [ ] Edit shows:
  - [ ] Document name
  - [ ] Timestamp
  - [ ] Change comment
  - [ ] Points earned

## Test 6: Check Leaderboard

- [ ] Click "Leaderboard" tab
- [ ] See contributor list
- [ ] Your name appears in list
- [ ] Points are displayed correctly

## Test 7: Verify Backend (Optional)

If you want to verify the backend is working:

```bash
# Check edit history table
aws dynamodb scan --table-name kb-edit-history-staging --max-items 5

# Check contributor stats table
aws dynamodb scan --table-name kb-contributor-stats-staging

# Check CloudWatch logs
aws logs tail /aws/lambda/aws-blog-api --follow
```

## Expected Results

✅ All steps complete without errors  
✅ Edit is saved to S3  
✅ Edit history recorded in DynamoDB  
✅ Contributor stats updated  
✅ Points awarded correctly  
✅ Bedrock ingestion triggered  

## If Something Fails

1. Check browser console for errors
2. Check CloudWatch logs: `aws logs tail /aws/lambda/aws-blog-api --follow`
3. Run test script: `python test_kb_save_operation.py`
4. Verify permissions: `aws iam list-role-policies --role-name aws-blog-viewer-stack-APILambdaRole-TYW5hnze4yLe`

## Success Criteria

- [ ] Can open KB editor
- [ ] Can view documents
- [ ] Can edit content
- [ ] Can save changes
- [ ] Edit history tracked
- [ ] Points awarded
- [ ] No errors

---

**When all items are checked**: KB editor is fully functional! ✅
