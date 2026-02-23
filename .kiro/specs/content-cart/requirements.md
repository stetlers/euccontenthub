# Requirements Document: Content Cart

## Introduction

The Content Cart feature enables users to collect multiple AWS blog posts and Builder.AWS articles into a temporary collection, then export all selected content to clipboard in various formats (Markdown, Plain Text, HTML) for easy sharing via email, Slack, or other messaging platforms. This feature addresses the common workflow of EUC specialists who need to curate and share multiple pieces of content efficiently.

## Glossary

- **Cart**: A temporary collection of blog posts selected by the user for export
- **Cart_Manager**: The frontend component responsible for managing cart state and operations
- **Cart_Item**: A reference to a blog post stored in the cart (post_id)
- **Export_Format**: The output format for clipboard content (Markdown, Plain Text, or HTML)
- **Cart_Panel**: The slide-out UI component displaying cart contents
- **Cart_Badge**: The visual indicator showing the number of items in the cart
- **Authenticated_User**: A user signed in via Cognito authentication
- **Anonymous_User**: A user browsing without authentication
- **API_Lambda**: The backend Lambda function handling cart API requests
- **User_Profile**: The DynamoDB record storing user data including cart items

## Requirements

### Requirement 1: Add Posts to Cart

**User Story:** As a user, I want to add blog posts to my cart with a single click, so that I can quickly collect content while browsing.

#### Acceptance Criteria

1. WHEN a user clicks the add-to-cart button on a post card, THE Cart_Manager SHALL add the post to the cart
2. WHEN a post is added to the cart, THE Cart_Badge SHALL increment the count by one
3. WHEN a post already in the cart is clicked again, THE System SHALL prevent duplicate additions
4. WHEN a post is successfully added, THE System SHALL provide visual feedback within 100ms
5. THE add-to-cart button SHALL be visible on all post cards in the main feed and search results

### Requirement 2: Cart Persistence for Authenticated Users

**User Story:** As an authenticated user, I want my cart to persist across sessions, so that I can collect content over time without losing my selections.

#### Acceptance Criteria

1. WHEN an authenticated user adds a post to the cart, THE API_Lambda SHALL save the cart to the User_Profile in DynamoDB
2. WHEN an authenticated user loads the application, THE System SHALL retrieve the cart from DynamoDB
3. WHEN cart operations complete, THE System SHALL update DynamoDB within 500ms
4. WHEN a user signs out, THE System SHALL preserve the cart in DynamoDB for future sessions
5. THE cart field in User_Profile SHALL store an array of post_id strings

### Requirement 3: Cart Persistence for Anonymous Users

**User Story:** As an anonymous user, I want to use the cart feature without signing in, so that I can try the feature before creating an account.

#### Acceptance Criteria

1. WHEN an anonymous user adds a post to the cart, THE Cart_Manager SHALL store the cart in localStorage
2. WHEN an anonymous user refreshes the page, THE System SHALL restore the cart from localStorage
3. WHEN the browser storage is cleared, THE System SHALL handle the missing cart gracefully
4. WHEN an anonymous user has items in their cart, THE System SHALL display a banner encouraging sign-in
5. THE banner message SHALL state "Sign in to save your cart permanently"

### Requirement 4: Cart UI Display

**User Story:** As a user, I want to see a floating cart button that shows how many items I've collected, so that I can track my selections without opening the cart.

#### Acceptance Criteria

1. THE System SHALL display a floating cart button in the bottom-right corner of the viewport
2. WHEN the cart contains items, THE Cart_Badge SHALL display the count on the cart button
3. WHEN the cart is empty, THE Cart_Badge SHALL display zero or be hidden
4. THE cart button SHALL remain visible while scrolling
5. WHEN the cart button is clicked, THE System SHALL open the Cart_Panel

### Requirement 5: Cart Panel Interface

**User Story:** As a user, I want to view all items in my cart in a slide-out panel, so that I can review my selections before exporting.

#### Acceptance Criteria

1. WHEN the cart button is clicked, THE System SHALL display the Cart_Panel sliding in from the right
2. THE Cart_Panel SHALL display all cart items with title, author, and date
3. WHEN the Cart_Panel is open, THE System SHALL provide a close button or overlay to dismiss it
4. WHEN the cart is empty, THE Cart_Panel SHALL display a message "Your cart is empty"
5. THE Cart_Panel SHALL include export format options and a copy button

### Requirement 6: Remove Items from Cart

**User Story:** As a user, I want to remove individual items from my cart, so that I can refine my selection before exporting.

#### Acceptance Criteria

1. WHEN a user clicks the remove button on a cart item, THE Cart_Manager SHALL remove that item from the cart
2. WHEN an item is removed, THE Cart_Badge SHALL decrement the count by one
3. WHEN an authenticated user removes an item, THE API_Lambda SHALL update the User_Profile in DynamoDB
4. WHEN an anonymous user removes an item, THE Cart_Manager SHALL update localStorage
5. THE System SHALL provide visual feedback when an item is removed

### Requirement 7: Clear All Cart Items

**User Story:** As a user, I want to clear all items from my cart at once, so that I can start fresh without removing items individually.

#### Acceptance Criteria

1. THE Cart_Panel SHALL display a "Clear All" button
2. WHEN the clear all button is clicked, THE System SHALL prompt for confirmation
3. WHEN the user confirms, THE Cart_Manager SHALL remove all items from the cart
4. WHEN an authenticated user clears the cart, THE API_Lambda SHALL update the User_Profile in DynamoDB
5. WHEN an anonymous user clears the cart, THE Cart_Manager SHALL update localStorage

### Requirement 8: Export Cart to Markdown Format

**User Story:** As a user, I want to copy my cart contents as Markdown, so that I can paste it into Slack or GitHub with proper formatting.

#### Acceptance Criteria

1. WHEN the user selects Markdown format and clicks copy, THE System SHALL generate Markdown text for all cart items
2. THE Markdown format SHALL include post title as a link, authors, date, and summary
3. THE System SHALL copy the Markdown text to the clipboard
4. WHEN the copy succeeds, THE System SHALL display a success notification
5. THE Markdown format SHALL use standard syntax compatible with Slack and GitHub

### Requirement 9: Export Cart to Plain Text Format

**User Story:** As a user, I want to copy my cart contents as plain text, so that I can paste it into email or simple text editors.

#### Acceptance Criteria

1. WHEN the user selects Plain Text format and clicks copy, THE System SHALL generate plain text for all cart items
2. THE Plain Text format SHALL include post title, URL, authors, date, and summary
3. THE System SHALL copy the plain text to the clipboard
4. WHEN the copy succeeds, THE System SHALL display a success notification
5. THE Plain Text format SHALL be readable without any special formatting

### Requirement 10: Export Cart to HTML Format

**User Story:** As a user, I want to copy my cart contents as HTML, so that I can paste it into rich text editors with preserved formatting.

#### Acceptance Criteria

1. WHEN the user selects HTML format and clicks copy, THE System SHALL generate HTML markup for all cart items
2. THE HTML format SHALL include styled post titles, authors, dates, and summaries
3. THE System SHALL copy the HTML to the clipboard
4. WHEN the copy succeeds, THE System SHALL display a success notification
5. THE HTML format SHALL render properly when pasted into rich text editors

### Requirement 11: Cart API Endpoints

**User Story:** As a developer, I want RESTful API endpoints for cart operations, so that the frontend can manage cart state reliably.

#### Acceptance Criteria

1. THE API_Lambda SHALL provide a GET /cart endpoint that returns the authenticated user's cart
2. THE API_Lambda SHALL provide a POST /cart endpoint that adds a post_id to the cart
3. THE API_Lambda SHALL provide a DELETE /cart/{post_id} endpoint that removes a specific item
4. THE API_Lambda SHALL provide a DELETE /cart endpoint that clears all cart items
5. WHEN cart operations fail, THE API_Lambda SHALL return appropriate error codes and messages

### Requirement 12: Cart Performance

**User Story:** As a user, I want cart operations to feel instant, so that the feature doesn't slow down my browsing experience.

#### Acceptance Criteria

1. WHEN a user adds an item to the cart, THE System SHALL update the UI within 100ms
2. WHEN a user removes an item from the cart, THE System SHALL update the UI within 100ms
3. WHEN the Cart_Panel opens, THE System SHALL render within 200ms
4. WHEN copying to clipboard, THE System SHALL complete within 500ms
5. THE cart operations SHALL not block other UI interactions

### Requirement 13: Cart Data Validation

**User Story:** As a developer, I want cart data to be validated, so that the system handles invalid data gracefully.

#### Acceptance Criteria

1. WHEN a post_id is added to the cart, THE System SHALL verify the post exists in the database
2. WHEN loading a cart from storage, THE System SHALL filter out invalid post_ids
3. WHEN the cart contains deleted posts, THE System SHALL remove them automatically
4. WHEN cart data is corrupted, THE System SHALL reset to an empty cart
5. THE System SHALL log validation errors for debugging

### Requirement 14: Clipboard API Integration

**User Story:** As a user, I want the copy-to-clipboard feature to work reliably across different browsers, so that I can use the feature regardless of my browser choice.

#### Acceptance Criteria

1. THE System SHALL use the modern Clipboard API when available
2. WHEN the Clipboard API is unavailable, THE System SHALL fall back to document.execCommand
3. WHEN clipboard access is denied, THE System SHALL display an error message with instructions
4. WHEN the copy succeeds, THE System SHALL display a success notification
5. THE System SHALL handle clipboard errors gracefully without breaking the UI

### Requirement 15: Cart Migration on Sign-In

**User Story:** As an anonymous user who signs in, I want my cart items to be preserved, so that I don't lose my selections when authenticating.

#### Acceptance Criteria

1. WHEN an anonymous user with cart items signs in, THE System SHALL merge localStorage cart with DynamoDB cart
2. WHEN merging carts, THE System SHALL prevent duplicate post_ids
3. WHEN the merge completes, THE System SHALL clear the localStorage cart
4. WHEN the merge fails, THE System SHALL preserve the localStorage cart
5. THE System SHALL display a notification confirming the cart was saved
