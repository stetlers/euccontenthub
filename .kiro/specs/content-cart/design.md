# Design Document: Content Cart

## Overview

The Content Cart feature enables users to collect AWS blog posts and Builder.AWS articles into a temporary collection, then export the collection to clipboard in multiple formats (Markdown, Plain Text, HTML). This feature addresses the workflow of EUC specialists who frequently curate and share multiple pieces of content with customers and colleagues.

The design follows the existing EUC Content Hub architecture patterns:
- Frontend: Vanilla JavaScript with modular components
- Backend: AWS Lambda with DynamoDB for persistence
- Authentication: Cognito JWT tokens
- UI: Floating cart button with slide-out panel

## Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Cart Manager │  │  Cart Panel  │  │   Cart UI    │      │
│  │   (State)    │  │  (Display)   │  │  (Buttons)   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   API Gateway   │
                    └────────┬────────┘
                             │
┌────────────────────────────▼─────────────────────────────────┐
│                      Backend (Lambda)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Cart API Endpoints                                   │   │
│  │  - GET /cart                                          │   │
│  │  - POST /cart                                         │   │
│  │  - DELETE /cart/{post_id}                            │   │
│  │  - DELETE /cart                                       │   │
│  └──────────────────────┬───────────────────────────────┘   │
└─────────────────────────┼───────────────────────────────────┘
                          │
                 ┌────────▼────────┐
                 │    DynamoDB     │
                 │  euc-user-      │
                 │   profiles      │
                 └─────────────────┘
```

### Data Flow

**Add to Cart (Authenticated User)**:
1. User clicks "+" button on post card
2. Cart Manager validates post_id
3. Cart Manager updates local state
4. Cart Manager calls POST /cart API
5. API Lambda updates DynamoDB user profile
6. UI updates cart badge count

**Add to Cart (Anonymous User)**:
1. User clicks "+" button on post card
2. Cart Manager validates post_id
3. Cart Manager updates local state
4. Cart Manager saves to localStorage
5. UI updates cart badge count
6. Banner displays "Sign in to save your cart permanently"

**Export Cart**:
1. User opens cart panel
2. User selects format (Markdown/Plain/HTML)
3. User clicks "Copy to Clipboard"
4. Cart Manager generates formatted text
5. Cart Manager copies to clipboard using Clipboard API
6. Success notification displays

## Components and Interfaces

### Frontend Components

#### 1. CartManager Class

**Responsibility**: Manages cart state, persistence, and API communication

**Interface**:
```javascript
class CartManager {
    constructor(apiEndpoint)
    
    // State management
    getCart()                    // Returns array of post_ids
    addToCart(postId)           // Adds post to cart
    removeFromCart(postId)      // Removes post from cart
    clearCart()                 // Removes all items
    isInCart(postId)            // Checks if post is in cart
    getCartCount()              // Returns number of items
    
    // Persistence
    loadCart()                  // Loads cart from storage
    saveCart()                  // Saves cart to storage
    mergeCartsOnSignIn()        // Merges localStorage with DynamoDB
    
    // Export
    exportAsMarkdown()          // Generates Markdown text
    exportAsPlainText()         // Generates plain text
    exportAsHTML()              // Generates HTML markup
    
    // Validation
    validatePostId(postId)      // Checks if post exists
    cleanInvalidPosts()         // Removes deleted posts
}
```


**Implementation Details**:
- Singleton pattern (one instance per page)
- Event-driven updates (emits 'cartChanged' events)
- Automatic persistence on every operation
- Graceful degradation for storage failures

#### 2. CartUI Component

**Responsibility**: Renders cart button, badge, and panel

**Interface**:
```javascript
class CartUI {
    constructor(cartManager)
    
    // Rendering
    renderCartButton()          // Creates floating cart button
    renderCartBadge(count)      // Updates badge with count
    renderCartPanel()           // Creates slide-out panel
    renderCartItems(items)      // Renders list of cart items
    renderEmptyState()          // Shows "cart is empty" message
    renderSignInBanner()        // Shows banner for anonymous users
    
    // Interactions
    openPanel()                 // Opens cart panel
    closePanel()                // Closes cart panel
    togglePanel()               // Toggles panel visibility
    
    // Export UI
    renderExportOptions()       // Shows format selection
    handleCopyToClipboard(format) // Handles copy button click
}
```

**Implementation Details**:
- Fixed positioning for cart button (bottom-right)
- Slide-in animation for panel (CSS transitions)
- Responsive design (mobile-friendly)
- Accessibility: keyboard navigation, ARIA labels

#### 3. ClipboardHelper Utility

**Responsibility**: Handles clipboard operations with fallbacks

**Interface**:
```javascript
class ClipboardHelper {
    static async copyToClipboard(text)  // Copies text to clipboard
    static isClipboardAPIAvailable()    // Checks for modern API
    static fallbackCopy(text)           // Uses execCommand fallback
}
```

**Implementation Details**:
- Prefers modern Clipboard API (navigator.clipboard)
- Falls back to document.execCommand for older browsers
- Handles permission errors gracefully
- Returns success/failure status

### Backend Components

#### 4. Cart API Endpoints (Lambda)

**GET /cart**
- **Authentication**: Required
- **Purpose**: Retrieve user's cart
- **Response**: `{ cart: ['post_id1', 'post_id2'] }`
- **Error Codes**: 401 (unauthorized), 500 (server error)

**POST /cart**
- **Authentication**: Required
- **Purpose**: Add post to cart
- **Request Body**: `{ post_id: 'string' }`
- **Response**: `{ cart: ['post_id1', 'post_id2'], added: true }`
- **Validation**: Checks if post exists, prevents duplicates
- **Error Codes**: 400 (invalid post_id), 401 (unauthorized), 404 (post not found)

**DELETE /cart/{post_id}**
- **Authentication**: Required
- **Purpose**: Remove specific post from cart
- **Response**: `{ cart: ['post_id1'], removed: true }`
- **Error Codes**: 401 (unauthorized), 404 (post not in cart)

**DELETE /cart**
- **Authentication**: Required
- **Purpose**: Clear all cart items
- **Response**: `{ cart: [], cleared: true }`
- **Error Codes**: 401 (unauthorized)

**Implementation Pattern**:
```python
@require_auth
def get_cart(event):
    user_id = event['user']['sub']
    profile = get_user_profile_from_db(user_id)
    cart = profile.get('cart', [])
    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({'cart': cart})
    }

@require_auth
def add_to_cart(event, body):
    user_id = event['user']['sub']
    post_id = body.get('post_id')
    
    # Validate post exists
    if not post_exists(post_id):
        return error_response(404, 'Post not found')
    
    # Get current cart
    profile = get_user_profile_from_db(user_id)
    cart = profile.get('cart', [])
    
    # Add if not duplicate
    if post_id not in cart:
        cart.append(post_id)
        update_user_cart(user_id, cart)
    
    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({'cart': cart, 'added': True})
    }
```

## Data Models

### User Profile Schema (DynamoDB)

**Table**: `euc-user-profiles`

**Updated Schema**:
```python
{
    'user_id': 'string',           # Primary key (Cognito sub)
    'email': 'string',
    'display_name': 'string',
    'bio': 'string',
    'credly_url': 'string',
    'builder_id': 'string',
    'bookmarks': ['post_id'],      # Existing field
    'cart': ['post_id'],           # NEW FIELD - Cart items
    'created_at': 'string',
    'updated_at': 'string'
}
```

**Cart Field Constraints**:
- Type: List of strings
- Default: Empty array `[]`
- Max size: 100 items (reasonable limit)
- Items: Valid post_id strings only
- No duplicates allowed

### LocalStorage Schema (Anonymous Users)

**Key**: `euc_cart`

**Value**:
```javascript
{
    "cart": ["post_id1", "post_id2"],
    "timestamp": "2024-01-15T10:30:00Z"
}
```

**Storage Constraints**:
- Max size: ~5KB (localStorage limit consideration)
- Automatic cleanup of invalid post_ids on load
- Cleared after successful sign-in merge

### Post Data (for Export)

**Required Fields for Export**:
```javascript
{
    post_id: 'string',
    title: 'string',
    url: 'string',
    authors: 'string',
    date_published: 'string',
    summary: 'string',
    label: 'string'  // Optional
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Cart Uniqueness Invariant

*For any* sequence of add operations on the same post_id, the cart should contain that post_id exactly once.

**Validates: Requirements 1.3**

**Rationale**: Prevents duplicate entries in the cart, ensuring clean export output and accurate count display.

### Property 2: Cart Count Consistency

*For any* cart state, the displayed badge count should equal the number of unique post_ids in the cart.

**Validates: Requirements 1.2, 4.2, 6.2**

**Rationale**: Ensures UI accurately reflects cart state at all times.

### Property 3: Authenticated User Persistence

*For any* authenticated user and any cart operation (add, remove, clear), the cart state in DynamoDB should match the local cart state after the operation completes.

**Validates: Requirements 2.1, 6.3, 7.4**

**Rationale**: Ensures cart persists across sessions for authenticated users.

### Property 4: Anonymous User LocalStorage Persistence

*For any* anonymous user and any cart operation (add, remove, clear), the cart state in localStorage should match the local cart state after the operation completes.

**Validates: Requirements 3.1, 6.4, 7.5**

**Rationale**: Ensures cart persists across page refreshes for anonymous users.

### Property 5: Cart Persistence Round Trip (Authenticated)

*For any* authenticated user with a saved cart, signing out and signing back in should restore the exact same cart contents.

**Validates: Requirements 2.2, 2.4**

**Rationale**: Validates that DynamoDB persistence works correctly across sessions.

### Property 6: Cart Persistence Round Trip (Anonymous)

*For any* anonymous user with a cart in localStorage, refreshing the page should restore the exact same cart contents.

**Validates: Requirements 3.2**

**Rationale**: Validates that localStorage persistence works correctly across page loads.

### Property 7: Add-to-Cart Button Visibility

*For any* post rendered in the feed or search results, the add-to-cart button should be present in the DOM.

**Validates: Requirements 1.5**

**Rationale**: Ensures users can always add posts to their cart.

### Property 8: Cart Panel Content Completeness

*For any* non-empty cart, the cart panel should display all cart items with title, author, and date fields present.

**Validates: Requirements 5.2**

**Rationale**: Ensures cart panel shows complete information for all items.

### Property 9: Remove Operation Correctness

*For any* post_id in the cart, removing it should result in the cart no longer containing that post_id.

**Validates: Requirements 6.1**

**Rationale**: Validates that remove operations work correctly.

### Property 10: Clear Operation Completeness

*For any* cart state, clearing the cart should result in an empty cart with zero items.

**Validates: Requirements 7.3**

**Rationale**: Validates that clear operations work correctly.

### Property 11: Markdown Export Completeness

*For any* non-empty cart, the Markdown export should include all cart items with title (as link), authors, date, and summary.

**Validates: Requirements 8.1, 8.2**

**Rationale**: Ensures Markdown export contains all required information.

### Property 12: Markdown Format Validity

*For any* generated Markdown output, the text should contain valid Markdown link syntax `[title](url)` for each post.

**Validates: Requirements 8.5**

**Rationale**: Ensures Markdown is compatible with Slack and GitHub.

### Property 13: Plain Text Export Completeness

*For any* non-empty cart, the plain text export should include all cart items with title, URL, authors, date, and summary.

**Validates: Requirements 9.1, 9.2**

**Rationale**: Ensures plain text export contains all required information.

### Property 14: HTML Export Completeness

*For any* non-empty cart, the HTML export should include all cart items with title, authors, date, and summary wrapped in proper HTML tags.

**Validates: Requirements 10.1, 10.2**

**Rationale**: Ensures HTML export contains all required information with proper structure.

### Property 15: API GET Cart Correctness

*For any* authenticated user, calling GET /cart should return the cart array stored in their DynamoDB profile.

**Validates: Requirements 11.1**

**Rationale**: Validates API correctly retrieves user cart.

### Property 16: API POST Cart Correctness

*For any* valid post_id not already in the cart, calling POST /cart should add it to the user's cart in DynamoDB.

**Validates: Requirements 11.2**

**Rationale**: Validates API correctly adds items to cart.

### Property 17: API DELETE Cart Item Correctness

*For any* post_id in the user's cart, calling DELETE /cart/{post_id} should remove it from the cart in DynamoDB.

**Validates: Requirements 11.3**

**Rationale**: Validates API correctly removes specific items.

### Property 18: API DELETE Cart Correctness

*For any* cart state, calling DELETE /cart should result in an empty cart array in DynamoDB.

**Validates: Requirements 11.4**

**Rationale**: Validates API correctly clears entire cart.

### Property 19: API Error Handling

*For any* invalid post_id (non-existent or malformed), calling POST /cart should return a 400 or 404 error without modifying the cart.

**Validates: Requirements 11.5**

**Rationale**: Ensures API handles invalid inputs gracefully.

### Property 20: Cart Validation Filter

*For any* cart containing a mix of valid and invalid post_ids, loading the cart should filter out all invalid post_ids and keep only valid ones.

**Validates: Requirements 13.1, 13.2, 13.3**

**Rationale**: Ensures cart automatically cleans up deleted or invalid posts.

### Property 21: Clipboard Error Resilience

*For any* clipboard error (permission denied, API unavailable), the cart UI should remain functional and display an appropriate error message.

**Validates: Requirements 14.5**

**Rationale**: Ensures clipboard failures don't break the application.

### Property 22: Cart Merge Uniqueness

*For any* combination of localStorage cart and DynamoDB cart, merging them should produce a cart with no duplicate post_ids.

**Validates: Requirements 15.1, 15.2**

**Rationale**: Ensures sign-in merge doesn't create duplicates.

### Property 23: Cart Merge LocalStorage Cleanup

*For any* successful cart merge operation, the localStorage cart should be cleared after the merge completes.

**Validates: Requirements 15.3**

**Rationale**: Prevents confusion between anonymous and authenticated cart state.

### Property 24: Cart Merge Failure Preservation

*For any* failed cart merge operation, the localStorage cart should remain unchanged.

**Validates: Requirements 15.4**

**Rationale**: Ensures user doesn't lose cart data if merge fails.

## Error Handling

### Frontend Error Scenarios

**1. Post Not Found**
- **Trigger**: Adding a post_id that doesn't exist
- **Handling**: Show error notification, don't add to cart
- **User Message**: "This post is no longer available"

**2. Storage Quota Exceeded**
- **Trigger**: localStorage full (rare, but possible)
- **Handling**: Show error notification, suggest sign-in
- **User Message**: "Cart storage full. Sign in to save unlimited items."

**3. Network Failure**
- **Trigger**: API call fails (timeout, no connection)
- **Handling**: Retry once, then show error
- **User Message**: "Failed to save cart. Please try again."

**4. Clipboard Permission Denied**
- **Trigger**: User denies clipboard access
- **Handling**: Show instructions for manual copy
- **User Message**: "Clipboard access denied. Please enable it in your browser settings."

**5. Corrupted Cart Data**
- **Trigger**: Invalid JSON in localStorage
- **Handling**: Reset to empty cart, log error
- **User Message**: "Cart data was corrupted and has been reset."

### Backend Error Scenarios

**1. Invalid Post ID**
- **HTTP Status**: 400 Bad Request
- **Response**: `{ error: "Invalid post_id format" }`
- **Handling**: Validate post_id format before database lookup

**2. Post Not Found**
- **HTTP Status**: 404 Not Found
- **Response**: `{ error: "Post not found" }`
- **Handling**: Check if post exists in aws-blog-posts table

**3. Unauthorized Access**
- **HTTP Status**: 401 Unauthorized
- **Response**: `{ error: "Authentication required" }`
- **Handling**: Validate JWT token before processing

**4. Cart Size Limit Exceeded**
- **HTTP Status**: 400 Bad Request
- **Response**: `{ error: "Cart limit reached (max 100 items)" }`
- **Handling**: Check cart length before adding

**5. DynamoDB Error**
- **HTTP Status**: 500 Internal Server Error
- **Response**: `{ error: "Failed to update cart" }`
- **Handling**: Log error, return generic message


## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests**: Focus on specific examples, edge cases, and integration points
- Empty cart state rendering
- Single item cart operations
- Sign-in banner display for anonymous users
- Clipboard API fallback behavior
- Error message display
- UI component rendering

**Property-Based Tests**: Verify universal properties across all inputs
- Cart uniqueness invariant (no duplicates)
- Count consistency across operations
- Persistence round-trips (DynamoDB and localStorage)
- Export format completeness
- API endpoint correctness
- Validation and error handling

### Property-Based Testing Configuration

**Library**: Use `fast-check` for JavaScript/TypeScript property-based testing

**Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with feature name and property number
- Tag format: `Feature: content-cart, Property {N}: {property_text}`

**Example Property Test**:
```javascript
// Feature: content-cart, Property 1: Cart Uniqueness Invariant
test('adding same post multiple times results in single entry', () => {
  fc.assert(
    fc.property(
      fc.array(fc.string()),  // Generate array of post_ids
      fc.string(),            // Generate a post_id to add multiple times
      (existingCart, postId) => {
        const cart = new CartManager();
        existingCart.forEach(id => cart.addToCart(id));
        
        // Add same post 5 times
        for (let i = 0; i < 5; i++) {
          cart.addToCart(postId);
        }
        
        // Count occurrences
        const count = cart.getCart().filter(id => id === postId).length;
        expect(count).toBe(1);
      }
    ),
    { numRuns: 100 }
  );
});
```

### Test Coverage Goals

**Frontend**:
- CartManager: 90%+ coverage
- CartUI: 80%+ coverage (UI components harder to test)
- ClipboardHelper: 100% coverage (critical utility)

**Backend**:
- Cart API endpoints: 95%+ coverage
- Validation logic: 100% coverage
- Error handling: 100% coverage

### Integration Testing

**Manual Testing Checklist**:
1. Add posts to cart (authenticated and anonymous)
2. Remove posts from cart
3. Clear entire cart
4. Export in all three formats (Markdown, Plain Text, HTML)
5. Sign in with items in anonymous cart (test merge)
6. Refresh page and verify cart persists
7. Test on mobile devices
8. Test with slow network (throttling)
9. Test clipboard permissions (allow/deny)
10. Test with 100 items in cart (limit)

**Automated Integration Tests**:
- End-to-end flow: Add → View → Export → Copy
- Authentication flow: Anonymous → Sign In → Merge
- Error recovery: Network failure → Retry → Success

## Implementation Notes

### Performance Considerations

**1. Lazy Loading**
- Don't load full post data until cart panel opens
- Store only post_ids in cart state
- Fetch post details on-demand when rendering panel

**2. Debouncing**
- Debounce DynamoDB updates (300ms) to avoid excessive writes
- Batch multiple rapid operations into single API call

**3. Caching**
- Cache post data in memory after first fetch
- Invalidate cache on cart changes

**4. Optimistic UI Updates**
- Update UI immediately, sync with backend asynchronously
- Rollback on failure

### Security Considerations

**1. Input Validation**
- Sanitize post_ids (alphanumeric + hyphens only)
- Limit cart size (max 100 items)
- Validate post existence before adding

**2. Authentication**
- All cart API endpoints require valid JWT
- Verify user owns the cart being modified
- Rate limit API calls (prevent abuse)

**3. XSS Prevention**
- Escape HTML in export formats
- Sanitize user-generated content (post titles, summaries)
- Use textContent instead of innerHTML where possible

### Accessibility

**1. Keyboard Navigation**
- Cart button: Tab-accessible, Enter/Space to open
- Cart panel: Esc to close, Tab through items
- Remove buttons: Tab-accessible, Enter/Space to remove

**2. Screen Reader Support**
- ARIA labels for cart button ("Shopping cart, X items")
- ARIA live region for cart count updates
- ARIA labels for remove buttons ("Remove [post title]")

**3. Visual Indicators**
- High contrast for cart badge
- Focus indicators for all interactive elements
- Loading states with aria-busy attribute

### Browser Compatibility

**Minimum Supported Browsers**:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Polyfills Required**:
- None (all features supported in minimum browsers)

**Fallbacks**:
- Clipboard API → document.execCommand (for older browsers)
- CSS Grid → Flexbox (for cart panel layout)

### Migration Strategy

**Phase 1: Backend Setup**
- Add `cart` field to user profile schema
- Deploy cart API endpoints
- Test with staging environment

**Phase 2: Frontend Core**
- Implement CartManager class
- Add cart button to post cards
- Implement localStorage persistence

**Phase 3: Cart Panel**
- Build cart panel UI
- Implement remove/clear operations
- Add export format selection

**Phase 4: Export Functionality**
- Implement Markdown generator
- Implement Plain Text generator
- Implement HTML generator
- Add clipboard integration

**Phase 5: Polish**
- Add animations and transitions
- Implement sign-in merge
- Add error handling and notifications
- Accessibility improvements

**Phase 6: Testing & Launch**
- Property-based tests
- Integration tests
- User acceptance testing
- Production deployment

### Monitoring and Analytics

**Metrics to Track**:
- Cart usage rate (% of users who add items)
- Average cart size
- Export format preferences (Markdown vs Plain vs HTML)
- Cart abandonment rate (items added but not exported)
- Sign-in conversion from cart banner
- Error rates (API failures, clipboard errors)

**Logging**:
- Cart operations (add, remove, clear)
- Export operations (format, item count)
- API errors (with sanitized details)
- Validation failures (invalid post_ids)

### Future Enhancements

**Potential Features** (not in current scope):
- Cart sharing (generate shareable link)
- Cart templates (save common collections)
- Drag-and-drop reordering in cart panel
- Bulk add (select multiple posts at once)
- Cart history (view past exports)
- Email export (send cart via email)
- Custom export templates
- Cart analytics dashboard
