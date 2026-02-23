"""
Test script for cart API endpoints
Tests all four cart endpoints in staging environment
"""

import boto3
import json
import requests
from datetime import datetime

# Configuration
API_ENDPOINT = "https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging"
REGION = "us-east-1"

# You'll need to provide a valid JWT token for testing
# Get this by signing in to staging.awseuccontent.com and copying from localStorage
JWT_TOKEN = input("Enter your JWT token from staging.awseuccontent.com: ").strip()

def test_get_cart():
    """Test GET /cart endpoint"""
    print("\n=== Testing GET /cart ===")
    
    headers = {
        'Authorization': f'Bearer {JWT_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(f"{API_ENDPOINT}/cart", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.json()

def test_add_to_cart(post_id):
    """Test POST /cart endpoint"""
    print(f"\n=== Testing POST /cart (add {post_id}) ===")
    
    headers = {
        'Authorization': f'Bearer {JWT_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    body = {'post_id': post_id}
    
    response = requests.post(f"{API_ENDPOINT}/cart", headers=headers, json=body)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.json()

def test_remove_from_cart(post_id):
    """Test DELETE /cart/{post_id} endpoint"""
    print(f"\n=== Testing DELETE /cart/{post_id} ===")
    
    headers = {
        'Authorization': f'Bearer {JWT_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    response = requests.delete(f"{API_ENDPOINT}/cart/{post_id}", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.json()

def test_clear_cart():
    """Test DELETE /cart endpoint"""
    print("\n=== Testing DELETE /cart (clear all) ===")
    
    headers = {
        'Authorization': f'Bearer {JWT_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    response = requests.delete(f"{API_ENDPOINT}/cart", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.json()

def get_sample_post_ids():
    """Get some sample post IDs from staging"""
    print("\n=== Getting sample post IDs ===")
    
    response = requests.get(f"{API_ENDPOINT}/posts")
    if response.status_code == 200:
        posts = response.json().get('posts', [])
        if posts:
            post_ids = [post['post_id'] for post in posts[:3]]
            print(f"Sample post IDs: {post_ids}")
            return post_ids
    
    return []

def main():
    """Run all cart endpoint tests"""
    print("=" * 60)
    print("Cart API Endpoint Tests - Staging Environment")
    print("=" * 60)
    
    try:
        # Get sample post IDs
        post_ids = get_sample_post_ids()
        if not post_ids:
            print("ERROR: Could not get sample post IDs")
            return
        
        # Test 1: Get initial cart (should be empty or have existing items)
        cart_data = test_get_cart()
        initial_cart = cart_data.get('cart', [])
        print(f"\nInitial cart has {len(initial_cart)} items")
        
        # Test 2: Add first post to cart
        result = test_add_to_cart(post_ids[0])
        assert result.get('added') == True, "Post should be added"
        assert post_ids[0] in result.get('cart', []), "Post should be in cart"
        
        # Test 3: Try adding same post again (should not duplicate)
        result = test_add_to_cart(post_ids[0])
        assert result.get('added') == False, "Post should not be added again"
        cart_count = result.get('cart', []).count(post_ids[0])
        assert cart_count == 1, f"Post should appear only once, found {cart_count}"
        
        # Test 4: Add second post to cart
        result = test_add_to_cart(post_ids[1])
        assert result.get('added') == True, "Second post should be added"
        assert len(result.get('cart', [])) >= 2, "Cart should have at least 2 items"
        
        # Test 5: Get cart (should have both posts)
        cart_data = test_get_cart()
        cart = cart_data.get('cart', [])
        assert post_ids[0] in cart, "First post should be in cart"
        assert post_ids[1] in cart, "Second post should be in cart"
        
        # Test 6: Remove first post from cart
        result = test_remove_from_cart(post_ids[0])
        assert result.get('removed') == True, "Post should be removed"
        assert post_ids[0] not in result.get('cart', []), "Post should not be in cart"
        assert post_ids[1] in result.get('cart', []), "Second post should still be in cart"
        
        # Test 7: Try removing post that's not in cart
        result = test_remove_from_cart(post_ids[0])
        assert result.get('removed') == False, "Post should not be removed (not in cart)"
        
        # Test 8: Clear entire cart
        result = test_clear_cart()
        assert result.get('cleared') == True, "Cart should be cleared"
        assert len(result.get('cart', [])) == 0, "Cart should be empty"
        
        # Test 9: Verify cart is empty
        cart_data = test_get_cart()
        assert len(cart_data.get('cart', [])) == 0, "Cart should be empty"
        
        # Test 10: Test invalid post_id
        print("\n=== Testing POST /cart with invalid post_id ===")
        headers = {
            'Authorization': f'Bearer {JWT_TOKEN}',
            'Content-Type': 'application/json'
        }
        response = requests.post(f"{API_ENDPOINT}/cart", headers=headers, json={'post_id': 'invalid-post-id-12345'})
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        assert response.status_code == 404, "Should return 404 for invalid post"
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    main()
