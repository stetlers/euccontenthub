"""
Test if we can scrape Builder.AWS without Selenium
"""
import requests
from bs4 import BeautifulSoup

# Test URL from staging
test_url = "https://builder.aws.com/content/2y6XQVt601LaNN4i8CvDi4WTbhN/building-a-simple-content-summarizer-with-amazon-bedrock"

print(f"Testing simple HTTP scraping for: {test_url}\n")

try:
    # Make HTTP request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(test_url, headers=headers, timeout=10)
    response.raise_for_status()
    
    print(f"✓ HTTP request successful (status: {response.status_code})")
    print(f"✓ Content length: {len(response.text)} chars\n")
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Try to extract author
    print("Attempting to extract author...")
    author = None
    
    # Try meta tag
    meta_author = soup.find('meta', {'name': 'author'})
    if meta_author:
        author = meta_author.get('content')
        print(f"  ✓ Found in meta tag: {author}")
    
    # Try common author selectors
    if not author:
        for selector in ['.author', '[class*="author"]', '[data-author]']:
            elem = soup.select_one(selector)
            if elem:
                author = elem.get_text().strip()
                print(f"  ✓ Found with selector '{selector}': {author}")
                break
    
    if not author:
        print("  ⚠ No author found - will use 'AWS Builder Community'")
        author = "AWS Builder Community"
    
    # Try to extract content
    print("\nAttempting to extract content...")
    content = None
    
    # Try article tag
    article = soup.find('article')
    if article:
        content = article.get_text().strip()
        print(f"  ✓ Found in <article> tag: {len(content)} chars")
    
    # Try main tag
    if not content or len(content) < 100:
        main = soup.find('main')
        if main:
            content = main.get_text().strip()
            print(f"  ✓ Found in <main> tag: {len(content)} chars")
    
    # Fallback to body
    if not content or len(content) < 100:
        body = soup.find('body')
        if body:
            content = body.get_text().strip()
            print(f"  ⚠ Using <body> tag: {len(content)} chars")
    
    if content:
        # Limit to 3000 chars
        if len(content) > 3000:
            content = content[:3000]
        
        print(f"\n✓ Successfully extracted content ({len(content)} chars)")
        print(f"\nFirst 200 chars of content:")
        print(f"  {content[:200]}...")
    else:
        print("  ✗ No content found")
    
    print("\n" + "=" * 60)
    print("CONCLUSION:")
    if author and content and len(content) > 100:
        print("✓ Simple HTTP scraping WORKS - no Selenium needed!")
        print("  This is much faster, cheaper, and more reliable than Selenium")
    else:
        print("✗ Simple HTTP scraping insufficient - Selenium may be needed")
    print("=" * 60)
    
except Exception as e:
    print(f"✗ Error: {e}")
    print("\nThis suggests the page requires JavaScript rendering (Selenium needed)")
