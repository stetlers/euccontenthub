# KB Editor Troubleshooting Guide

## Issue: "Edit Knowledge Base" option not showing in profile dropdown

### Possible Causes & Solutions

#### 1. Browser Cache (Most Common)
**Symptoms**: Old version of the site is loading

**Solutions**:
- **Hard Refresh**: 
  - Windows/Linux: `Ctrl + F5` or `Ctrl + Shift + R`
  - Mac: `Cmd + Shift + R`
  
- **Clear Browser Cache**:
  - Chrome: Settings > Privacy > Clear browsing data > Cached images and files
  - Firefox: Settings > Privacy > Clear Data > Cached Web Content
  - Safari: Develop > Empty Caches (or Cmd + Option + E)

- **Incognito/Private Mode**:
  - Open staging site in incognito/private window
  - This bypasses cache completely

#### 2. CloudFront Cache Not Invalidated Yet
**Symptoms**: Changes deployed but not visible

**Solutions**:
- Wait 2-3 minutes for CloudFront invalidation to complete
- Check invalidation status:
  ```bash
  aws cloudfront get-invalidation \
    --distribution-id E1IB9VDMV64CQA \
    --id IIE3NVLT231RMAKTIR7XDMEKT
  ```

#### 3. JavaScript Not Loading
**Symptoms**: Console errors, menu doesn't work

**Solutions**:
- Open browser DevTools (F12)
- Check Console tab for errors
- Check Network tab to see if files loaded:
  - `auth.js?v=20260225-kb` should load
  - `kb-editor.js?v=20260225-kb` should load
  - `kb-editor-styles.css?v=20260225-kb` should load

#### 4. Not Signed In
**Symptoms**: Profile dropdown doesn't appear

**Solutions**:
- Make sure you're signed in to staging
- Click "Sign In" button in top right
- Authenticate with Google

#### 5. Wrong Environment
**Symptoms**: Looking at production instead of staging

**Solutions**:
- Verify URL is: `https://staging.awseuccontent.com`
- NOT: `https://awseuccontent.com` (production)

## Verification Steps

### 1. Check if files are deployed
```bash
# Check S3 bucket
aws s3 ls s3://aws-blog-viewer-staging-031421429609/ | grep -E "auth.js|kb-editor"

# Should show:
# 2026-02-25 XX:XX:XX  13036 auth.js
# 2026-02-25 XX:XX:XX  10453 kb-editor-styles.css
# 2026-02-25 XX:XX:XX  25480 kb-editor.js
```

### 2. Check if auth.js has the menu option
```bash
# Download and check auth.js
aws s3 cp s3://aws-blog-viewer-staging-031421429609/auth.js - | grep "Edit Knowledge Base"

# Should show:
# <span>📚</span> Edit Knowledge Base
```

### 3. Check browser console
1. Open staging site: https://staging.awseuccontent.com
2. Press F12 to open DevTools
3. Go to Console tab
4. Look for errors related to:
   - `kb-editor.js`
   - `kbEditor`
   - `window.kbEditor`

### 4. Check if kbEditor is loaded
1. Open browser console (F12)
2. Type: `window.kbEditor`
3. Should show: `KBEditor {currentDocument: null, ...}`
4. If undefined, kb-editor.js didn't load

### 5. Manually test the function
1. Open browser console (F12)
2. Type: `window.kbEditor.showEditor()`
3. Should open the KB editor modal
4. If error, check what the error says

## Manual Deployment (If Automated Fails)

### Upload files manually
```bash
# Upload auth.js
aws s3 cp frontend/auth.js s3://aws-blog-viewer-staging-031421429609/auth.js \
  --content-type "application/javascript"

# Upload kb-editor.js
aws s3 cp frontend/kb-editor.js s3://aws-blog-viewer-staging-031421429609/kb-editor.js \
  --content-type "application/javascript"

# Upload kb-editor-styles.css
aws s3 cp frontend/kb-editor-styles.css s3://aws-blog-viewer-staging-031421429609/kb-editor-styles.css \
  --content-type "text/css"

# Upload index.html
aws s3 cp frontend/index.html s3://aws-blog-viewer-staging-031421429609/index.html \
  --content-type "text/html"
```

### Invalidate CloudFront cache
```bash
aws cloudfront create-invalidation \
  --distribution-id E1IB9VDMV64CQA \
  --paths "/index.html" "/auth.js" "/kb-editor.js" "/kb-editor-styles.css"
```

## Quick Test Script

Save this as `test_kb_editor_ui.html` and open in browser:

```html
<!DOCTYPE html>
<html>
<head>
    <title>KB Editor Test</title>
</head>
<body>
    <h1>KB Editor UI Test</h1>
    <button onclick="testKBEditor()">Test KB Editor</button>
    <div id="result"></div>
    
    <script>
        function testKBEditor() {
            const result = document.getElementById('result');
            
            // Test 1: Check if kbEditor exists
            if (typeof window.kbEditor === 'undefined') {
                result.innerHTML = '❌ window.kbEditor is undefined<br>kb-editor.js did not load';
                return;
            }
            
            result.innerHTML = '✅ window.kbEditor exists<br>';
            
            // Test 2: Check if showEditor method exists
            if (typeof window.kbEditor.showEditor !== 'function') {
                result.innerHTML += '❌ showEditor method not found';
                return;
            }
            
            result.innerHTML += '✅ showEditor method exists<br>';
            
            // Test 3: Try to call showEditor
            try {
                window.kbEditor.showEditor();
                result.innerHTML += '✅ showEditor() called successfully';
            } catch (error) {
                result.innerHTML += '❌ Error calling showEditor: ' + error.message;
            }
        }
    </script>
</body>
</html>
```

## Common Error Messages

### "kbEditor is not defined"
**Cause**: kb-editor.js didn't load  
**Fix**: Check Network tab, clear cache, hard refresh

### "Cannot read property 'showEditor' of undefined"
**Cause**: kbEditor object not initialized  
**Fix**: Check console for initialization errors

### "No authentication token available"
**Cause**: Not signed in  
**Fix**: Sign in with Google

### "Failed to load documents"
**Cause**: API endpoint not responding  
**Fix**: Check Lambda deployment, check API Gateway

## Contact Support

If none of these solutions work:

1. Take screenshots of:
   - Browser console (F12 > Console tab)
   - Network tab showing loaded files
   - The profile dropdown menu

2. Note:
   - Browser and version
   - Operating system
   - Exact URL you're visiting
   - Steps you took

3. Share with development team

## Expected Behavior

When working correctly:

1. Visit https://staging.awseuccontent.com
2. Sign in with Google
3. Click profile dropdown (top right, shows your name)
4. See menu with:
   - 👤 My Profile
   - 📚 Edit Knowledge Base ← This should be visible
   - 🚪 Sign Out
5. Click "📚 Edit Knowledge Base"
6. Modal opens showing document list
7. Click a document to edit
8. Editor interface loads with markdown content

## Version Information

**Current Deployment**:
- Date: February 25, 2026
- Version: 20260225-kb
- CloudFront Invalidation: IIE3NVLT231RMAKTIR7XDMEKT
- Files:
  - auth.js?v=20260225-kb
  - kb-editor.js?v=20260225-kb
  - kb-editor-styles.css?v=20260225-kb
