"""
Test KB document save operation with proper authentication
"""
import requests
import json

# Staging API endpoint
API_BASE = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'

# You'll need to get this from browser localStorage after signing in
# localStorage.getItem('id_token')
TOKEN = input("Enter your JWT token from browser (localStorage.getItem('id_token')): ").strip()

if not TOKEN:
    print("❌ Token is required. Sign in to staging site and get token from browser console.")
    exit(1)

headers = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json'
}

# Test 1: Get document
print("\n📖 Test 1: Getting document...")
print("=" * 70)
response = requests.get(
    f'{API_BASE}/kb-document/euc-qa-pairs',
    headers=headers
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    doc = response.json()
    print(f"✅ Document loaded: {doc.get('name')}")
    print(f"Content length: {len(doc.get('content', ''))}")
    original_content = doc.get('content', '')
else:
    print(f"❌ Error: {response.text}")
    exit(1)

# Test 2: Save document with minor change
print("\n💾 Test 2: Saving document with test edit...")
print("=" * 70)

# Add a test comment at the end
test_content = original_content + "\n\n<!-- Test edit from API -->"

save_data = {
    'content': test_content,
    'change_comment': 'Test edit to verify save functionality works correctly'
}

response = requests.put(
    f'{API_BASE}/kb-document/euc-qa-pairs',
    headers=headers,
    json=save_data
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"✅ Document saved successfully!")
    print(f"Ingestion Job ID: {result.get('ingestion_job_id')}")
    print(f"Points earned: {result.get('points_earned')}")
else:
    print(f"❌ Error: {response.text}")
    try:
        error_data = response.json()
        print(f"Error details: {json.dumps(error_data, indent=2)}")
    except:
        pass

# Test 3: Check ingestion status (if we got a job ID)
if response.status_code == 200:
    result = response.json()
    job_id = result.get('ingestion_job_id')
    if job_id:
        print(f"\n🔍 Test 3: Checking ingestion status...")
        print("=" * 70)
        response = requests.get(
            f'{API_BASE}/kb-ingestion-status/{job_id}',
            headers=headers
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Ingestion status: {status.get('status')}")
        else:
            print(f"❌ Error: {response.text}")

print("\n" + "=" * 70)
print("✅ Test complete!")
print("=" * 70)
