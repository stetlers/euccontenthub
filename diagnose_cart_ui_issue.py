import requests

print("Diagnosing Cart UI Issue")
print("=" * 60)

# Check if cart-ui.js is accessible
print("\n1. Checking cart-ui.js...")
try:
    response = requests.get('https://staging.awseuccontent.com/cart-ui.js')
    if response.status_code == 200:
        print(f"✅ cart-ui.js is accessible ({len(response.text)} bytes)")
        if 'class CartUI' in response.text:
            print("✅ Contains CartUI class")
        else:
            print("❌ Does NOT contain CartUI class")
    else:
        print(f"❌ cart-ui.js returned status {response.status_code}")
except Exception as e:
    print(f"❌ Error fetching cart-ui.js: {e}")

# Check if cart.css is accessible
print("\n2. Checking cart.css...")
try:
    response = requests.get('https://staging.awseuccontent.com/cart.css')
    if response.status_code == 200:
        print(f"✅ cart.css is accessible ({len(response.text)} bytes)")
        if '.cart-floating-btn' in response.text:
            print("✅ Contains cart button styles")
        else:
            print("❌ Does NOT contain cart button styles")
    else:
        print(f"❌ cart.css returned status {response.status_code}")
except Exception as e:
    print(f"❌ Error fetching cart.css: {e}")

# Check if index-staging.html includes cart files
print("\n3. Checking index-staging.html...")
try:
    response = requests.get('https://staging.awseuccontent.com/index-staging.html')
    if response.status_code == 200:
        html = response.text
        print(f"✅ index-staging.html is accessible ({len(html)} bytes)")
        
        if 'cart.css' in html:
            print("✅ Includes cart.css")
        else:
            print("❌ Does NOT include cart.css")
        
        if 'cart-ui.js' in html:
            print("✅ Includes cart-ui.js")
        else:
            print("❌ Does NOT include cart-ui.js")
        
        if 'cart-manager.js' in html:
            print("✅ Includes cart-manager.js")
        else:
            print("❌ Does NOT include cart-manager.js")
    else:
        print(f"❌ index-staging.html returned status {response.status_code}")
except Exception as e:
    print(f"❌ Error fetching index-staging.html: {e}")

# Check if app-staging.js has CartUI initialization
print("\n4. Checking app-staging.js...")
try:
    response = requests.get('https://staging.awseuccontent.com/app-staging.js')
    if response.status_code == 200:
        js = response.text
        print(f"✅ app-staging.js is accessible ({len(js)} bytes)")
        
        if 'let cartUI' in js:
            print("✅ Has cartUI variable declaration")
        else:
            print("❌ Does NOT have cartUI variable declaration")
        
        if 'new CartUI' in js:
            print("✅ Has CartUI initialization")
        else:
            print("❌ Does NOT have CartUI initialization")
        
        if 'Cart UI initialized' in js:
            print("✅ Has CartUI initialization log")
        else:
            print("❌ Does NOT have CartUI initialization log")
    else:
        print(f"❌ app-staging.js returned status {response.status_code}")
except Exception as e:
    print(f"❌ Error fetching app-staging.js: {e}")

print("\n" + "=" * 60)
print("\nNext Steps:")
print("1. Open https://staging.awseuccontent.com in browser")
print("2. Open browser console (F12)")
print("3. Look for these messages:")
print("   - 'Cart manager initialized'")
print("   - 'Cart UI initialized'")
print("4. Check for any JavaScript errors")
print("5. Look in bottom-right corner for cart button")
