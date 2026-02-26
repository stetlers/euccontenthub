"""
Quick test of KB editor endpoints
"""
import requests
import json

API_URL = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'

def test_kb_documents():
    """Test the /kb-documents endpoint (no auth required for GET)"""
    print("\n" + "=" * 60)
    print("Testing GET /kb-documents")
    print("=" * 60)
    
    try:
        response = requests.get(f'{API_URL}/kb-documents')
        print(f"\nStatus Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Success! Found {len(data.get('documents', []))} documents")
            for doc in data.get('documents', []):
                print(f"  - {doc.get('name')} ({doc.get('id')})")
        else:
            print(f"\n❌ Error: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")

def test_kb_document_get():
    """Test the /kb-document/{id} endpoint"""
    print("\n" + "=" * 60)
    print("Testing GET /kb-document/euc-qa-pairs")
    print("=" * 60)
    
    try:
        response = requests.get(f'{API_URL}/kb-document/euc-qa-pairs')
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 401:
            print("✅ Endpoint exists and requires authentication (expected)")
        elif response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Document has {len(data.get('content', ''))} characters")
        else:
            print(f"⚠️  Unexpected status: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == '__main__':
    print("\n🧪 TESTING KB EDITOR ENDPOINTS")
    test_kb_documents()
    test_kb_document_get()
    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)
