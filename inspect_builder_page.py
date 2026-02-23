"""
Quick script to inspect Builder.AWS page HTML structure
to find the correct author selector
"""
import requests
from bs4 import BeautifulSoup

url = "https://builder.aws.com/content/36EuCtutHruo4fs5aU0hzc5hK7G/building-a-simple-content-summarizer-with-amazon-bedrock"

print(f"Fetching: {url}")
print("=" * 80)

response = requests.get(url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Look for author in meta tags
    print("\n=== META TAGS ===")
    for meta in soup.find_all('meta'):
        name = meta.get('name', '')
        property_val = meta.get('property', '')
        content = meta.get('content', '')
        
        if 'author' in name.lower() or 'author' in property_val.lower():
            print(f"  {name or property_val}: {content}")
    
    # Look for author in common patterns
    print("\n=== POTENTIAL AUTHOR ELEMENTS ===")
    
    # Check for data attributes
    for elem in soup.find_all(attrs={'data-author': True}):
        print(f"  data-author: {elem.get('data-author')}")
    
    # Check for class patterns
    for pattern in ['author', 'byline', 'writer', 'contributor']:
        elements = soup.find_all(class_=lambda x: x and pattern in x.lower())
        for elem in elements[:3]:  # Limit to first 3
            print(f"  class='{elem.get('class')}': {elem.get_text()[:100]}")
    
    # Check for specific text patterns
    print("\n=== SEARCHING FOR 'By' PATTERNS ===")
    for elem in soup.find_all(string=lambda text: text and 'By ' in text):
        parent = elem.parent
        print(f"  {parent.name}.{parent.get('class')}: {elem.strip()[:100]}")
    
    # Look at the page title area
    print("\n=== TITLE AREA ===")
    h1 = soup.find('h1')
    if h1:
        print(f"  H1: {h1.get_text()[:100]}")
        # Check siblings
        for sibling in list(h1.next_siblings)[:5]:
            if hasattr(sibling, 'get_text'):
                text = sibling.get_text().strip()
                if text and len(text) < 200:
                    print(f"  Sibling ({sibling.name}): {text[:100]}")
    
    # Save full HTML for inspection
    with open('builder_page_sample.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    print("\n✓ Full HTML saved to builder_page_sample.html")
    
else:
    print(f"Failed to fetch page: {response.status_code}")
