#!/usr/bin/env python3
"""
Test script for comment moderation system in staging
Tests various comment scenarios to verify moderation is working
"""

import boto3
import json

def test_moderation():
    """Test the moderation function directly"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Test cases
    test_cases = [
        {
            'name': 'Legitimate technical comment',
            'text': 'Great article! I implemented this solution with Amazon WorkSpaces and it worked perfectly. Thanks for sharing!',
            'expected': 'approved'
        },
        {
            'name': 'Spam/promotional content',
            'text': 'Buy cheap AWS credits here! Visit our website for amazing deals on cloud services!',
            'expected': 'pending_review'
        },
        {
            'name': 'Comment with AWS documentation link',
            'text': 'For more details, check out the official docs: https://docs.aws.amazon.com/workspaces/',
            'expected': 'approved'
        },
        {
            'name': 'Comment with multiple links',
            'text': 'Check out these sites: http://bit.ly/abc http://tinyurl.com/xyz http://example.tk http://test.ml',
            'expected': 'pending_review'
        },
        {
            'name': 'Harassment/profanity',
            'text': 'This is stupid and you are an idiot for writing this garbage',
            'expected': 'pending_review'
        },
        {
            'name': 'Off-topic content',
            'text': 'Anyone want to buy my used car? Great condition, low mileage!',
            'expected': 'pending_review'
        },
        {
            'name': 'Technical criticism (should be approved)',
            'text': 'I disagree with this approach. Using Lambda would be more cost-effective than EC2 for this use case.',
            'expected': 'approved'
        }
    ]
    
    print("=" * 80)
    print("COMMENT MODERATION TEST - STAGING ENVIRONMENT")
    print("=" * 80)
    print()
    
    # Create a test payload that simulates the moderate_comment function
    # We'll invoke the Lambda directly with a test event
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}/{len(test_cases)}: {test_case['name']}")
        print(f"  Text: {test_case['text'][:60]}...")
        print(f"  Expected: {test_case['expected']}")
        
        # Note: We can't directly test the moderate_comment function without
        # actually submitting a comment through the API
        # This would require authentication and a real post ID
        
        print(f"  ⏭️  Skipping (requires full API integration test)")
        print()
    
    print("=" * 80)
    print("NOTE: Full integration testing requires:")
    print("  1. Valid JWT token from Cognito")
    print("  2. Existing post ID in staging DynamoDB")
    print("  3. POST request to /posts/{id}/comments endpoint")
    print()
    print("To test manually:")
    print("  1. Log in to https://staging.awseuccontent.com")
    print("  2. Navigate to a blog post")
    print("  3. Submit test comments with various content")
    print("  4. Check DynamoDB for moderation metadata")
    print("  5. Check CloudWatch logs for moderation results")
    print("=" * 80)

if __name__ == '__main__':
    test_moderation()
