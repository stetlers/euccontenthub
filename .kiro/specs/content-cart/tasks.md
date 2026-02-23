# Implementation Plan: Content Cart

## Overview

This implementation plan breaks down the Content Cart feature into discrete, incremental tasks. Each task builds on previous work and includes testing to validate functionality early. The implementation follows a phased approach: backend setup, frontend core, cart UI, export functionality, and polish.

## Tasks

- [ ] 1. Backend: Add cart field to user profile schema
  - Update DynamoDB user profile schema to include `cart` field (array of strings)
  - Add migration logic to initialize empty cart for existing users
  - Update profile creation to include empty cart by default
  - _Requirements: 2.5_

- [ ]* 1.1 Write property test for cart field schema
  - **Property 5: Authenticated User Persistence**
  - **Validates: Requirements 2.1, 6.3, 7.4**

- [ ] 2. Backend: Implement GET /cart endpoint
  - [ ] 2.1 Add GET /cart route to lambda_handler
    - Extract user_id from JWT token
    - Retrieve user profile from DynamoDB
    - Return cart array from profile
    - Handle missing profile gracefully
    - _Requirements: 11.1_
  
  - [ ]* 2.2 Write property test for GET /cart
    - **Property 15: API GET Cart Correctness**
    - **Validates: Requirements 11.1**
  
  - [ ]* 2.3 Write unit tests for GET /cart edge cases
    - Test with empty cart
    - Test with non-existent user
    - Test with missing cart field (legacy profiles)
    - _Requirements: 11.1_

- [ ] 3. Backend: Implement POST /cart endpoint
  - [ ] 3.1 Add POST /cart route to lambda_handler
    - Extract user_id from JWT token
    - Validate post_id format
    - Check if post exists in aws-blog-posts table
    - Get current cart from user profile
    - Add post_id if not already in cart (prevent duplicates)
    - Update user profile in DynamoDB
    - Return updated cart array
    - _Requirements: 11.2, 13.1_
  
  - [ ]* 3.2 Write property test for POST /cart
    - **Property 16: API POST Cart Correctness**
    - **Validates: Requirements 11.2**
  
  - [ ]* 3.3 Write property test for duplicate prevention
    - **Property 1: Cart Uniqueness Invariant**
    - **Validates: Requirements 1.3**
  
  - [ ]* 3.4 Write unit tests for POST /cart error cases
    - Test with invalid post_id format
    - Test with non-existent post_id
    - Test with cart at max size (100 items)
    - _Requirements: 11.5, 13.1_

- [ ] 4. Backend: Implement DELETE /cart/{post_id} endpoint
  - [ ] 4.1 Add DELETE /cart/{post_id} route to lambda_handler
    - Extract user_id from JWT token
    - Extract post_id from path parameters
    - Get current cart from user profile
    - Remove post_id from cart if present
    - Update user profile in DynamoDB
    - Return updated cart array
    - _Requirements: 11.3_
  
  - [ ]* 4.2 Write property test for DELETE /cart/{post_id}
    - **Property 17: API DELETE Cart Item Correctness**
    - **Validates: Requirements 11.3**
  
  - [ ]* 4.3 Write property test for remove operation
    - **Property 9: Remove Operation Correctness**
    - **Validates: Requirements 6.1**

- [ ] 5. Backend: Implement DELETE /cart endpoint
  - [ ] 5.1 Add DELETE /cart route to lambda_handler
    - Extract user_id from JWT token
    - Set cart to empty array in user profile
    - Update user profile in DynamoDB
    - Return empty cart array
    - _Requirements: 11.4_
  
  - [ ]* 5.2 Write property test for DELETE /cart
    - **Property 18: API DELETE Cart Correctness**
    - **Validates: Requirements 11.4**
  
  - [ ]* 5.3 Write property test for clear operation
    - **Property 10: Clear Operation Completeness**
    - **Validates: Requirements 7.3**

- [ ] 6. Checkpoint - Backend API complete
  - Deploy backend changes to staging
  - Test all cart endpoints with Postman or curl
  - Verify DynamoDB updates correctly
  - Check CloudWatch logs for errors
  - Ensure all tests pass

- [ ] 7. Frontend: Create CartManager class
  - [ ] 7.1 Create frontend/cart-manager.js file
    - Implement CartManager class with constructor
    - Add cart state management (array of post_ids)
    - Implement getCart(), getCartCount(), isInCart() methods
    - Add event emitter for 'cartChanged' events
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [ ] 7.2 Implement addToCart() method
    - Validate post_id is not empty
    - Check for duplicates before adding
    - Update local state
    - Emit 'cartChanged' event
    - Call persistence method
    - _Requirements: 1.1, 1.3_
  
  - [ ] 7.3 Implement removeFromCart() method
    - Remove post_id from cart array
    - Update local state
    - Emit 'cartChanged' event
    - Call persistence method
    - _Requirements: 6.1_
  
  - [ ] 7.4 Implement clearCart() method
    - Set cart to empty array
    - Update local state
    - Emit 'cartChanged' event
    - Call persistence method
    - _Requirements: 7.3_
  
  - [ ]* 7.5 Write property tests for CartManager
    - **Property 1: Cart Uniqueness Invariant**
    - **Property 2: Cart Count Consistency**
    - **Validates: Requirements 1.2, 1.3, 4.2, 6.2**

- [ ] 8. Frontend: Implement cart persistence
  - [ ] 8.1 Add localStorage persistence for anonymous users
    - Implement saveToLocalStorage() method
    - Implement loadFromLocalStorage() method
    - Handle JSON parse errors gracefully
    - Store cart with timestamp
    - _Requirements: 3.1, 3.2_
  
  - [ ] 8.2 Add DynamoDB persistence for authenticated users
    - Implement saveToAPI() method using POST /cart
    - Implement loadFromAPI() method using GET /cart
    - Handle network errors gracefully
    - Add retry logic for failed requests
    - _Requirements: 2.1, 2.2_
  
  - [ ] 8.3 Implement automatic persistence detection
    - Check if user is authenticated (window.authManager)
    - Route to localStorage or API based on auth state
    - Implement saveCart() method that delegates correctly
    - Implement loadCart() method that delegates correctly
    - _Requirements: 2.1, 3.1_
  
  - [ ]* 8.4 Write property tests for persistence
    - **Property 4: Anonymous User LocalStorage Persistence**
    - **Property 5: Cart Persistence Round Trip (Authenticated)**
    - **Property 6: Cart Persistence Round Trip (Anonymous)**
    - **Validates: Requirements 2.1, 2.2, 2.4, 3.1, 3.2, 6.3, 6.4, 7.4, 7.5**

- [ ] 9. Frontend: Add cart buttons to post cards
  - [ ] 9.1 Update createPostCard() in app.js
    - Add "+" button to post card header
    - Style button to match existing UI
    - Add data-post-id attribute
    - Add click event listener
    - _Requirements: 1.1, 1.5_
  
  - [ ] 9.2 Implement handleAddToCart() function
    - Get post_id from button data attribute
    - Call cartManager.addToCart(post_id)
    - Show success notification
    - Update button state (disable if already in cart)
    - Handle errors gracefully
    - _Requirements: 1.1, 1.4_
  
  - [ ] 9.3 Update post card rendering to show cart state
    - Check if post is in cart on render
    - Disable "+" button if already in cart
    - Add visual indicator (checkmark icon)
    - _Requirements: 1.3_
  
  - [ ]* 9.4 Write property test for button visibility
    - **Property 7: Add-to-Cart Button Visibility**
    - **Validates: Requirements 1.5**

- [ ] 10. Frontend: Create floating cart button
  - [ ] 10.1 Create frontend/cart-ui.js file
    - Implement CartUI class with constructor
    - Create floating cart button HTML
    - Position button in bottom-right corner (fixed)
    - Add cart icon (🛒 or shopping cart SVG)
    - _Requirements: 4.1_
  
  - [ ] 10.2 Implement cart badge
    - Add badge element to cart button
    - Update badge count on 'cartChanged' events
    - Hide badge when count is zero
    - Style badge with notification styling
    - _Requirements: 4.2, 4.3_
  
  - [ ] 10.3 Add cart button click handler
    - Listen for click events on cart button
    - Call openPanel() method
    - Add keyboard support (Enter/Space)
    - _Requirements: 4.5_
  
  - [ ]* 10.4 Write property test for badge count
    - **Property 2: Cart Count Consistency**
    - **Validates: Requirements 1.2, 4.2, 6.2**

- [ ] 11. Frontend: Create cart panel UI
  - [ ] 11.1 Implement renderCartPanel() method
    - Create slide-out panel HTML structure
    - Add panel header with title and close button
    - Add panel body for cart items
    - Add panel footer for export options
    - Position panel off-screen initially (right: -400px)
    - _Requirements: 5.1, 5.2_
  
  - [ ] 11.2 Implement openPanel() and closePanel() methods
    - Animate panel sliding in from right (CSS transition)
    - Add overlay backdrop
    - Handle Esc key to close
    - Handle click outside to close
    - Prevent body scroll when open
    - _Requirements: 5.1, 5.3_
  
  - [ ] 11.3 Implement renderCartItems() method
    - Fetch post data for all cart post_ids
    - Render each item with title, author, date
    - Add remove button for each item
    - Show empty state if cart is empty
    - Handle loading state while fetching
    - _Requirements: 5.2, 5.4_
  
  - [ ]* 11.4 Write property test for panel content
    - **Property 8: Cart Panel Content Completeness**
    - **Validates: Requirements 5.2**

- [ ] 12. Frontend: Implement cart item removal
  - [ ] 12.1 Add remove button to each cart item
    - Add "×" button next to each item
    - Style button consistently
    - Add data-post-id attribute
    - Add click event listener
    - _Requirements: 6.1_
  
  - [ ] 12.2 Implement handleRemoveFromCart() function
    - Get post_id from button data attribute
    - Call cartManager.removeFromCart(post_id)
    - Re-render cart items
    - Show notification
    - Handle errors gracefully
    - _Requirements: 6.1, 6.5_
  
  - [ ] 12.3 Add "Clear All" button
    - Add button to panel footer
    - Implement confirmation dialog
    - Call cartManager.clearCart() on confirm
    - Re-render cart items
    - _Requirements: 7.1, 7.2_

- [ ] 13. Checkpoint - Cart UI complete
  - Test adding posts to cart
  - Test removing posts from cart
  - Test clearing cart
  - Test cart persistence (refresh page)
  - Test on mobile devices
  - Ensure all tests pass

- [ ] 14. Frontend: Implement export format generators
  - [ ] 14.1 Create frontend/cart-export.js file
    - Create CartExport utility class
    - Add method to fetch full post data for cart items
    - Implement error handling for missing posts
    - _Requirements: 8.1, 9.1, 10.1_
  
  - [ ] 14.2 Implement exportAsMarkdown() method
    - Generate Markdown text for all cart items
    - Format: `[Title](URL)` for each post
    - Include authors, date, summary
    - Add separator between posts
    - Return formatted string
    - _Requirements: 8.1, 8.2, 8.5_
  
  - [ ] 14.3 Implement exportAsPlainText() method
    - Generate plain text for all cart items
    - Format: Title, URL, Authors, Date, Summary
    - Use clear separators and line breaks
    - Return formatted string
    - _Requirements: 9.1, 9.2_
  
  - [ ] 14.4 Implement exportAsHTML() method
    - Generate HTML markup for all cart items
    - Use semantic HTML tags (h3, p, a)
    - Include inline styles for formatting
    - Return formatted HTML string
    - _Requirements: 10.1, 10.2_
  
  - [ ]* 14.5 Write property tests for export formats
    - **Property 11: Markdown Export Completeness**
    - **Property 12: Markdown Format Validity**
    - **Property 13: Plain Text Export Completeness**
    - **Property 14: HTML Export Completeness**
    - **Validates: Requirements 8.1, 8.2, 8.5, 9.1, 9.2, 10.1, 10.2**

- [ ] 15. Frontend: Implement clipboard integration
  - [ ] 15.1 Create frontend/clipboard-helper.js file
    - Create ClipboardHelper utility class
    - Implement isClipboardAPIAvailable() method
    - Check for navigator.clipboard support
    - _Requirements: 14.1_
  
  - [ ] 15.2 Implement copyToClipboard() method
    - Try modern Clipboard API first (navigator.clipboard.writeText)
    - Fall back to document.execCommand('copy') if unavailable
    - Handle permission errors
    - Return success/failure status
    - _Requirements: 14.1, 14.2, 14.3_
  
  - [ ] 15.3 Implement fallbackCopy() method
    - Create temporary textarea element
    - Set value to text to copy
    - Select text and execute copy command
    - Remove temporary element
    - _Requirements: 14.2_
  
  - [ ]* 15.4 Write property test for clipboard error handling
    - **Property 21: Clipboard Error Resilience**
    - **Validates: Requirements 14.5**

- [ ] 16. Frontend: Add export UI to cart panel
  - [ ] 16.1 Add export format selection to panel
    - Add radio buttons for Markdown, Plain Text, HTML
    - Style format options
    - Set Markdown as default
    - _Requirements: 5.5_
  
  - [ ] 16.2 Add "Copy to Clipboard" button
    - Add button to panel footer
    - Style button prominently
    - Disable when cart is empty
    - _Requirements: 5.5_
  
  - [ ] 16.3 Implement handleCopyToClipboard() function
    - Get selected format from radio buttons
    - Generate export text using CartExport
    - Call ClipboardHelper.copyToClipboard()
    - Show success notification
    - Handle errors and show error message
    - _Requirements: 8.3, 8.4, 9.3, 9.4, 10.3, 10.4, 14.3_

- [ ] 17. Frontend: Implement sign-in banner for anonymous users
  - [ ] 17.1 Add renderSignInBanner() method to CartUI
    - Check if user is anonymous (not authenticated)
    - Check if cart has items
    - Render banner above cart items
    - Include message: "Sign in to save your cart permanently"
    - Add "Sign In" button
    - _Requirements: 3.4, 3.5_
  
  - [ ] 17.2 Implement sign-in button click handler
    - Call window.authManager.signIn()
    - Close cart panel
    - _Requirements: 3.4_

- [ ] 18. Frontend: Implement cart merge on sign-in
  - [ ] 18.1 Add mergeCartsOnSignIn() method to CartManager
    - Get cart from localStorage
    - Get cart from DynamoDB (via API)
    - Merge both arrays, removing duplicates
    - Save merged cart to DynamoDB
    - Clear localStorage cart
    - Show success notification
    - _Requirements: 15.1, 15.2, 15.3_
  
  - [ ] 18.2 Hook merge into auth flow
    - Listen for auth state changes
    - Call mergeCartsOnSignIn() after successful sign-in
    - Handle merge errors gracefully
    - Preserve localStorage cart on failure
    - _Requirements: 15.1, 15.4_
  
  - [ ]* 18.3 Write property tests for cart merge
    - **Property 22: Cart Merge Uniqueness**
    - **Property 23: Cart Merge LocalStorage Cleanup**
    - **Property 24: Cart Merge Failure Preservation**
    - **Validates: Requirements 15.1, 15.2, 15.3, 15.4**

- [ ] 19. Frontend: Implement cart validation
  - [ ] 19.1 Add validatePostId() method to CartManager
    - Check if post_id exists in allPosts array
    - Return true/false
    - _Requirements: 13.1_
  
  - [ ] 19.2 Add cleanInvalidPosts() method
    - Filter cart to remove invalid post_ids
    - Call on cart load
    - Log removed post_ids for debugging
    - Update cart state and persistence
    - _Requirements: 13.2, 13.3_
  
  - [ ] 19.3 Handle corrupted cart data
    - Wrap JSON.parse in try-catch
    - Reset to empty cart on parse error
    - Log error for debugging
    - Show notification to user
    - _Requirements: 13.4_
  
  - [ ]* 19.4 Write property test for cart validation
    - **Property 20: Cart Validation Filter**
    - **Validates: Requirements 13.1, 13.2, 13.3**

- [ ] 20. Frontend: Add CSS styling
  - [ ] 20.1 Create frontend/cart.css file
    - Style floating cart button
    - Style cart badge
    - Style cart panel (slide-out)
    - Style cart items list
    - Style export options
    - Style sign-in banner
    - Add responsive styles for mobile
    - _Requirements: 4.1, 4.2, 5.1_
  
  - [ ] 20.2 Add animations and transitions
    - Panel slide-in animation
    - Button hover effects
    - Badge pulse animation on add
    - Loading spinners
    - _Requirements: 5.1_
  
  - [ ] 20.3 Add accessibility styles
    - Focus indicators for all interactive elements
    - High contrast for cart badge
    - Visible loading states
    - _Requirements: 4.1_

- [ ] 21. Frontend: Initialize cart on page load
  - [ ] 21.1 Update app.js DOMContentLoaded handler
    - Initialize CartManager
    - Initialize CartUI
    - Load cart from storage
    - Render cart button
    - Set up event listeners
    - _Requirements: 2.2, 3.2_
  
  - [ ] 21.2 Add cart script includes to index.html
    - Add script tags for cart-manager.js
    - Add script tags for cart-ui.js
    - Add script tags for cart-export.js
    - Add script tags for clipboard-helper.js
    - Add link tag for cart.css
    - Ensure correct load order
    - _Requirements: All_

- [ ] 22. Checkpoint - Feature complete
  - Test complete end-to-end flow
  - Test all export formats
  - Test sign-in merge
  - Test error scenarios
  - Test on multiple browsers
  - Test on mobile devices
  - Ensure all tests pass

- [ ] 23. Deploy to staging
  - Deploy backend changes to staging Lambda
  - Deploy frontend changes to staging S3 bucket
  - Invalidate CloudFront cache
  - Test on staging environment
  - Verify DynamoDB updates in staging tables
  - Check CloudWatch logs for errors

- [ ] 24. Production deployment
  - Deploy backend changes to production Lambda
  - Deploy frontend changes to production S3 bucket
  - Invalidate CloudFront cache
  - Monitor CloudWatch logs
  - Test on production environment
  - Announce feature to users

## Notes

- Tasks marked with `*` are optional property-based tests and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Follow existing code patterns in the EUC Content Hub codebase
- Use vanilla JavaScript (no frameworks)
- Follow existing styling conventions
- Test thoroughly in staging before production deployment
