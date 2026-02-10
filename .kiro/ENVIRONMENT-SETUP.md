# Kiro Environment Setup Guide

## ⚠️ CRITICAL: READ THIS FIRST BEFORE ANY COMMAND ⚠️

**EVERY TIME you run a command (AWS CLI, Git, GitHub CLI, Python/boto3), you MUST verify the environment is set up in that terminal session.**

**Environment variables do NOT persist across terminal sessions or command invocations.**

### Quick Check Before Running Commands
```powershell
# Run this to verify environment is ready:
if ($Env:AWS_ACCESS_KEY_ID) { "✅ AWS credentials set" } else { "❌ AWS credentials NOT set - run setup!" }
if (Get-Command git -ErrorAction SilentlyContinue) { "✅ Git available" } else { "❌ Git NOT in PATH - run setup!" }
if (Get-Command aws -ErrorAction SilentlyContinue) { "✅ AWS CLI available" } else { "❌ AWS CLI NOT in PATH - run setup!" }
if (Get-Command gh -ErrorAction SilentlyContinue) { "✅ GitHub CLI available" } else { "❌ GitHub CLI NOT in PATH - run setup!" }
```

**If ANY show ❌, run the Complete Setup Script below BEFORE proceeding.**

---

## Critical: Run This First in Every New Terminal Session

This file contains the environment setup commands that must be executed before running any AWS, Git, or GitHub CLI commands.

---

## 🤖 FOR KIRO (AI AGENT): MANDATORY CHECKLIST

**Before running ANY command (aws, git, gh, python), you MUST:**

1. ✅ Check if this is a new terminal session
2. ✅ If new session, run the Complete Setup Script above
3. ✅ Verify environment with the Quick Check commands
4. ✅ If verification fails, STOP and tell user environment needs setup
5. ✅ Do NOT proceed with commands if environment is not ready

**Signs you're in a new terminal session:**
- Previous command failed with "not recognized" error
- Previous command failed with "Unable to locate credentials" error
- You just started working after a context transfer
- User opened a new terminal window

**What to do:**
1. Tell user: "I need to set up the environment first"
2. Ask user: "Do you have the AWS credentials ready?"
3. Run the Complete Setup Script with user's credentials
4. Verify with Quick Check commands
5. Only then proceed with the actual task

**DO NOT:**
- ❌ Run commands without verifying environment first
- ❌ Assume environment is set up from previous commands
- ❌ Skip the setup because you "think" it's already done
- ❌ Run multiple commands hoping one will work

---

## Step 0: Check Credential Status

**BEFORE doing anything else, ask the user:**

> "Is this the first time we're working today, or are we continuing from an earlier session?"

### If First Time Today:
- AWS credentials have expired (8-hour limit)
- Ask user: "I need fresh AWS credentials to proceed. Please provide the AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_SESSION_TOKEN."
- Wait for user to provide credentials
- Proceed with full setup

### If Continuing Same Day:
- Credentials from earlier session should still be valid
- Check context transfer summary for credentials
- Look for credentials in format:
  ```
  $Env:AWS_ACCESS_KEY_ID="ASIA..."
  $Env:AWS_SECRET_ACCESS_KEY="..."
  $Env:AWS_SESSION_TOKEN="IQoJb3JpZ2luX2VjE..."
  ```
- If found in context, use those credentials
- If not found or unclear, ask user for credentials

### Credential Lifespan
- **Valid for**: 8 hours from issuance
- **Typical work session**: 2-4 hours
- **Rule of thumb**: If more than 8 hours since last session, credentials are expired

---

## PowerShell Environment Setup Command

Copy and run this single command at the start of each session:

```powershell
# Add all required paths
$Env:Path += ";$env:LOCALAPPDATA\Programs\Git\bin";
$Env:Path += ";C:\Program Files\Amazon\AWSCLIV2";
$Env:Path += ";C:\Program Files\GitHub CLI";
Write-Output "✅ Paths configured: Git, AWS CLI, GitHub CLI"
```

---

## AWS Credentials Setup

**IMPORTANT**: AWS credentials are temporary session tokens that expire after 8 hours.

### When to Set Credentials
- At the start of each work session
- When you see `AccessDenied` or credential errors
- When running Python scripts with boto3
- After 8 hours of work

### How to Set Credentials

User will provide credentials in this format:
```powershell
$Env:AWS_ACCESS_KEY_ID="ASIA..."
$Env:AWS_SECRET_ACCESS_KEY="..."
$Env:AWS_SESSION_TOKEN="IQoJb3JpZ2luX2VjE..."
$Env:AWS_DEFAULT_REGION="us-east-1"
```

**CRITICAL for Python/Boto3**: These environment variables must be set in the SAME terminal session where you run Python scripts. Each new terminal requires credentials to be set again.

### Verify Credentials

**For AWS CLI:**
```powershell
aws sts get-caller-identity
```

**For Python/Boto3:**
```powershell
python -c "import boto3; print(boto3.client('sts').get_caller_identity())"
```

Expected output:
```json
{
    "UserId": "AROAXXXXXXXXXX:username",
    "Account": "031421429609",
    "Arn": "arn:aws:sts::031421429609:assumed-role/Admin/username"
}
```

---

## Complete Setup Script

**⚠️ RUN THIS EVERY TIME before executing commands in a new terminal session:**

```powershell
# 1. Add paths
$Env:Path += ";$env:LOCALAPPDATA\Programs\Git\bin"
$Env:Path += ";C:\Program Files\Amazon\AWSCLIV2"
$Env:Path += ";C:\Program Files\GitHub CLI"

# 2. Set AWS credentials (user will provide these)
$Env:AWS_ACCESS_KEY_ID="ASIA..."
$Env:AWS_SECRET_ACCESS_KEY="..."
$Env:AWS_SESSION_TOKEN="IQoJb3JpZ2luX2VjE..."
$Env:AWS_DEFAULT_REGION="us-east-1"

# 3. Verify setup (optional but recommended)
if ($Env:AWS_ACCESS_KEY_ID) { "✅ AWS credentials set" } else { "❌ AWS credentials NOT set" }
if (Get-Command git -ErrorAction SilentlyContinue) { "✅ Git available" } else { "❌ Git NOT available" }
if (Get-Command aws -ErrorAction SilentlyContinue) { "✅ AWS CLI available" } else { "❌ AWS CLI NOT available" }
if (Get-Command gh -ErrorAction SilentlyContinue) { "✅ GitHub CLI available" } else { "❌ GitHub CLI NOT available" }
```

**IMPORTANT**: Replace the credential values with actual credentials from the user.

---

## Tool Locations

### Git
- **Path**: `$env:LOCALAPPDATA\Programs\Git\bin`
- **Full Path**: `D:\Users\stetlers\AppData\Local\Programs\Git\bin`
- **Executable**: `git.exe`
- **Status**: ✅ Installed

### AWS CLI
- **Path**: `C:\Program Files\Amazon\AWSCLIV2`
- **Executable**: `aws.exe`
- **Status**: ✅ Installed

### GitHub CLI
- **Path**: `C:\Program Files\GitHub CLI`
- **Executable**: `gh.exe`
- **Status**: ✅ Installed

---

## Common Issues and Solutions

### Issue: "git is not recognized"
**Solution**: Run path setup command above

### Issue: "aws is not recognized"
**Solution**: Run path setup command above

### Issue: "gh is not recognized"
**Solution**: Run path setup command above to add `C:\Program Files\GitHub CLI` to PATH

### Issue: "AccessDeniedException" from AWS
**Solution**: 
1. Credentials expired (8-hour limit)
2. Ask user for fresh credentials
3. Re-run credential setup

### Issue: "The security token included in the request is invalid"
**Solution**: Session token expired - ask user for new credentials

---

## AWS Account Information

- **Account ID**: 031421429609
- **Region**: us-east-1
- **IAM Role**: Admin/stetlers-Isengard
- **Credential Type**: Temporary session tokens (8-hour expiry)

---

## Project-Specific Paths

### S3 Buckets
- **Production**: `aws-blog-viewer-031421429609`
- **Staging**: `aws-blog-viewer-staging-031421429609`

### CloudFront Distributions
- **Production**: E20CC1TSSWTCWN
- **Staging**: E1IB9VDMV64CQA

### API Gateway
- **API ID**: xox05733ce
- **Production Stage**: prod
- **Staging Stage**: staging

### DynamoDB Tables
- **Production Posts**: aws-blog-posts
- **Production Profiles**: euc-user-profiles
- **Staging Posts**: aws-blog-posts-staging
- **Staging Profiles**: euc-user-profiles-staging

### Lambda Functions
- aws-blog-api
- aws-blog-crawler
- aws-blog-builder-selenium-crawler
- aws-blog-summary-generator
- aws-blog-classifier
- aws-blog-chat-assistant

---

## Best Practices

### 1. Always Verify Environment First
Before running any commands, verify tools are available:
```powershell
Get-Command git, aws, gh -ErrorAction SilentlyContinue
```

### 2. Test AWS Credentials Early
Don't wait for a command to fail - test credentials immediately:
```powershell
aws sts get-caller-identity
```

### 3. Ask User for Credentials
If credentials are missing or expired, **STOP** and ask user:
> "I need fresh AWS credentials to proceed. Please provide the AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_SESSION_TOKEN."

### 4. Don't Retry Failed Commands Repeatedly
If a command fails due to missing tools or credentials:
1. Identify the issue
2. Tell user what's needed
3. Wait for user to provide solution
4. Don't retry more than once without fixing the root cause

### 5. Session Persistence
Remember that environment variables set in one terminal session do NOT persist to new sessions. Each new terminal requires full setup.

### 6. Git Security - CRITICAL
**Before any git commit or push:**
- Review files with `git status`
- Check for AWS account numbers (031421429609)
- Check for ARNs (arn:aws:...)
- Check for sensitive configuration data
- Verify `.gitignore` is protecting sensitive files
- If Code Defender blocks a push, remove the file and update `.gitignore`

**Never commit:**
- Files with ARNs
- Files with AWS account numbers
- Certificate files
- Cognito/domain configuration files
- CloudFront configuration files
- Deployment artifacts (*.zip)

---

## Quick Reference Commands

### Git/GitHub Security Rules

**CRITICAL: Never commit files with AWS account information**

Files that should NEVER be committed (already in .gitignore):
- Any file containing ARNs (Amazon Resource Names)
- Any file containing AWS account number (031421429609)
- Certificate files (*.pem, certificate_arn.txt)
- Configuration files with sensitive data (cognito_config.json, domain_config.json)
- CloudFront configuration files (staging-cloudfront-config.json, production-cf-config.json)
- Deployment artifacts (*.zip)

**Before any `git add` or `git commit`:**
1. Check `.gitignore` is up to date
2. Review files being added with `git status`
3. Look for AWS account numbers, ARNs, or sensitive data
4. If Code Defender blocks a push, remove the sensitive file and update `.gitignore`

**If you accidentally stage a sensitive file:**
```powershell
# Remove from staging
git reset HEAD <filename>

# Add to .gitignore
Add-Content .gitignore "`n<filename>"
```

### Verify Environment
```powershell
# Check if tools are available
Get-Command git, aws, gh -ErrorAction SilentlyContinue | Format-Table Name, Source

# Check AWS credentials
aws sts get-caller-identity

# Check current AWS region
echo $Env:AWS_DEFAULT_REGION
```

### Reset Environment (if needed)
```powershell
# Clear and re-add paths
$Env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
$Env:Path += ";$env:LOCALAPPDATA\Programs\Git\bin"
$Env:Path += ";C:\Program Files\Amazon\AWSCLIV2"
$Env:Path += ";C:\Program Files\GitHub CLI"
```

---

## Context Transfer Note

When a conversation is summarized and a new session starts:

### Credentials in Context Transfer
1. **Check if credentials are in the summary** - Look for the AWS credential block in the context transfer
2. **Credentials format to look for**:
   ```
   $Env:AWS_ACCESS_KEY_ID="ASIA..."
   $Env:AWS_SECRET_ACCESS_KEY="..."
   $Env:AWS_SESSION_TOKEN="IQoJb3JpZ2luX2VjE..."
   ```
3. **If found**: Use those credentials (they're likely still valid if same day)
4. **If not found**: Ask user if this is first session of the day

### What's NOT Transferred
- **Path variables are NOT transferred** (each terminal is fresh)
- **Always run path setup first** before any commands

### Decision Tree for New Sessions
```
New Session Started
    ↓
Ask: "First time working today?"
    ↓
    ├─ YES → Ask for fresh credentials
    │         ↓
    │         Set up paths + new credentials
    │         ↓
    │         Verify with aws sts get-caller-identity
    │
    └─ NO → Check context transfer for credentials
              ↓
              ├─ Found → Use those credentials
              │          ↓
              │          Set up paths + use context credentials
              │          ↓
              │          Verify with aws sts get-caller-identity
              │
              └─ Not Found → Ask user for credentials
                             ↓
                             Set up paths + provided credentials
                             ↓
                             Verify with aws sts get-caller-identity
```

---

## Checklist for New Sessions

- [ ] **ASK USER**: "Is this the first time we're working today?"
- [ ] **IF YES**: Request fresh credentials from user
- [ ] **IF NO**: Check context transfer summary for credentials
- [ ] Add Git to PATH (`$env:LOCALAPPDATA\Programs\Git\bin`)
- [ ] Add AWS CLI to PATH (`C:\Program Files\Amazon\AWSCLIV2`)
- [ ] Add GitHub CLI to PATH (`C:\Program Files\GitHub CLI`)
- [ ] Set AWS credentials (from user or context)
- [ ] Set AWS_DEFAULT_REGION=us-east-1
- [ ] Verify with `aws sts get-caller-identity`
- [ ] **If running Python/boto3 scripts**: Verify boto3 can access credentials
- [ ] Verify with `git --version`
- [ ] Verify with `gh --version`

---

## Python/Boto3 Specific Notes

### Environment Variables for Boto3
Boto3 (AWS SDK for Python) reads credentials from environment variables:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN`
- `AWS_DEFAULT_REGION`

These MUST be set in the same PowerShell session where Python scripts run.

### Common Python Scripts in This Project
- `deploy_frontend.py` - Deploy frontend to S3/CloudFront
- `deploy_lambda.py` - Deploy Lambda functions
- `copy_data_to_staging.py` - Copy DynamoDB data
- `configure_lambda_staging.py` - Configure Lambda environments

### Before Running Python Scripts
```powershell
# Verify credentials are set
python -c "import boto3; boto3.client('sts').get_caller_identity()"
```

If you get `Unable to locate credentials`, the environment variables aren't set in that terminal session.

---

---

## Frontend File Requirements - CRITICAL

**⚠️ ALWAYS verify these requirements before deploying frontend changes to prevent regressions**

### Required Files for Each Environment

#### Production Files (frontend/)
- ✅ `index.html` - Main HTML with production config
- ✅ `auth.js` - Auth with redirectUri: `https://awseuccontent.com/callback`
- ✅ `app.js` - Main application logic
- ✅ `profile.js` - User profile management
- ✅ `chat-widget.js` - AI chat assistant
- ✅ `chat-widget.css` - Chat widget styles
- ✅ `styles.css` - Main styles
- ✅ `zoom-mode.js` - Zoom/presentation mode (Issue #12)
- ✅ `zoom-mode.css` - Zoom mode styles

#### Staging-Specific Files (frontend/)
- ✅ `index-staging.html` - **MUST be complete copy of index.html with title changed to "Staging"**
- ✅ `auth-staging.js` - Auth with redirectUri: `https://staging.awseuccontent.com/callback`

### Critical File Checks

#### 1. index-staging.html
**Problem**: This file has been deployed incomplete (only 446 bytes) causing staging to break
**Solution**: Always verify it's a complete copy of index.html

```powershell
# Check file size (should be ~15KB, not 446 bytes)
(Get-Item "frontend/index-staging.html").Length

# If too small, recreate from index.html
Copy-Item "frontend/index.html" "frontend/index-staging.html" -Force
```

**Required changes in index-staging.html**:
- Title: `<title>EUC Content Hub - Staging</title>`
- All other content identical to index.html

#### 2. index.html Required Links
**CSS Links** (in `<head>`):
```html
<link rel="stylesheet" href="styles.css">
<link rel="stylesheet" href="chat-widget.css">
<link rel="stylesheet" href="zoom-mode.css">
```

**Script Links** (before `</body>`):
```html
<script src="auth.js"></script>
<script src="app.js"></script>
<script src="profile.js"></script>
<script src="chat-widget.js"></script>
<script src="zoom-mode.js"></script>
```

#### 3. auth.js vs auth-staging.js
**Production (auth.js)**:
```javascript
redirectUri: 'https://awseuccontent.com/callback'
```

**Staging (auth-staging.js)**:
```javascript
redirectUri: 'https://staging.awseuccontent.com/callback'
```

**Critical**: Staging MUST use auth-staging.js or users will be redirected to production after login!

#### 4. app.js Required Features
Verify these features are present:
- ✅ Comment moderation UI (lines ~1200-1320)
  - `moderation_status` handling
  - `pending_review` status with yellow background
  - Warning notifications for flagged comments
- ✅ Zoom mode integration (if applicable)
  - `window.refreshZoomButtons()` calls after post rendering

#### 5. styles.css Required Styles
Verify these style blocks exist:
- ✅ `.comment-pending` - Yellow background for pending comments
- ✅ `.comment-pending-badge` - Orange "⏳ Pending Review" badge
- ✅ `.notification.warning` - Orange warning notifications

### Deployment Script Requirements

**deploy_frontend.py** must handle environment-specific files:

```python
# For staging deployment
if environment == 'staging':
    # Use index-staging.html as index.html
    if filename == 'index.html':
        source_filename = 'index-staging.html'
    # Use auth-staging.js as auth.js
    elif filename == 'auth.js':
        source_filename = 'auth-staging.js'
```

### Pre-Deployment Checklist

**Before deploying to staging:**
- [ ] Verify index-staging.html is complete (not 446 bytes)
- [ ] Verify auth-staging.js has correct staging redirect URI
- [ ] Verify all CSS/JS files are linked in index-staging.html
- [ ] Verify deploy_frontend.py uses staging-specific files

**Before deploying to production:**
- [ ] Test in staging first
- [ ] Verify auth.js has production redirect URI
- [ ] Verify all features work in staging
- [ ] Verify zoom mode buttons appear on post cards
- [ ] Verify comment moderation UI shows pending comments correctly

### Common Regression Issues

#### Issue: Staging redirects to production after login
**Cause**: auth.js deployed instead of auth-staging.js
**Fix**: Deploy with `python deploy_frontend.py staging` (uses auth-staging.js)

#### Issue: Staging shows blank page
**Cause**: index-staging.html is incomplete
**Fix**: 
```powershell
Copy-Item "frontend/index.html" "frontend/index-staging.html" -Force
# Update title to "Staging"
# Redeploy
```

#### Issue: Zoom mode missing
**Cause**: zoom-mode.js or zoom-mode.css not linked in HTML
**Fix**: Add links to both index.html and index-staging.html

#### Issue: Comment moderation UI missing
**Cause**: Old version of app.js deployed
**Fix**: Verify app.js has moderation_status handling (lines ~1200-1320)

### File Verification Commands

```powershell
# Check all required files exist
$requiredFiles = @(
    "frontend/index.html",
    "frontend/index-staging.html",
    "frontend/auth.js",
    "frontend/auth-staging.js",
    "frontend/app.js",
    "frontend/profile.js",
    "frontend/chat-widget.js",
    "frontend/chat-widget.css",
    "frontend/styles.css",
    "frontend/zoom-mode.js",
    "frontend/zoom-mode.css"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        $size = (Get-Item $file).Length
        Write-Output "✅ $file ($size bytes)"
    } else {
        Write-Output "❌ $file MISSING"
    }
}

# Check index-staging.html size
$stagingSize = (Get-Item "frontend/index-staging.html").Length
if ($stagingSize -lt 10000) {
    Write-Output "⚠️ WARNING: index-staging.html is only $stagingSize bytes (should be ~15KB)"
    Write-Output "   Run: Copy-Item 'frontend/index.html' 'frontend/index-staging.html' -Force"
}
```

---

**Last Updated**: 2026-02-10
**Project**: EUC Content Hub (awseuccontent.com)
**Repository**: https://github.com/stetlers/euccontenthub
