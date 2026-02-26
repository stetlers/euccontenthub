#!/usr/bin/env python3
"""
Test KB Editor API Endpoints in Staging

Tests all 6 KB editor endpoints:
1. GET /kb-documents - List documents
2. GET /kb-document/{id} - Get document content
3. PUT /kb-document/{id} - Update document
4. GET /kb-ingestion-status/{job_id} - Check ingestion status
5. GET /kb-contributors - Get leaderboard
6. GET /kb-my-contributions - Get user contributions
"""

import requests
import json
import time

# Staging API endpoint
API_BASE = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'

# Test JWT token (you'll need to replace this with a valid token)
# Get this from the browser after logging in to staging.awseuccontent.com
JWT_TOKEN = None

def test_list_documents():
    """Test GET /kb-documents"""
    print("\n" + "="*70)
    print("TEST 1: List KB Documents")
    print("="*70)
    
    if not JWT_TOKEN:
        print("❌ JWT_TOKEN not set. Please set JWT_TOKEN variable.")
        return False
    
    headers = {'Authorization': f'Bearer {JWT_TOKEN}'}
    
    try:
        response = requests.get(f'{API_BASE}/kb-documents', headers=headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            documents = data.get('documents', [])
            print(f"✅ Found {len(documents)} documents")
            
            for doc in documents:
                print(f"\n  📄 {doc['name']}")
                print(f"     ID: {doc['id']}")
                print(f"     Category: {doc['category']}")
                print(f"     Size: {doc['size']} bytes")
                
                if 'question_count' in doc:
                    print(f"     Questions: {doc['question_count']}")
                elif 'service_count' in doc:
                    print(f"     Services: {doc['service_count']}")
            
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def test_get_document():
    """Test GET /kb-document/{id}"""
    print("\n" + "="*70)
    print("TEST 2: Get Document Content")
    print("="*70)
    
    if not JWT_TOKEN:
        print("❌ JWT_TOKEN not set. Please set JWT_TOKEN variable.")
        return False
    
    headers = {'Authorization': f'Bearer {JWT_TOKEN}'}
    document_id = 'curated-qa/common-questions.md'
    
    try:
        response = requests.get(f'{API_BASE}/kb-document/{document_id}', headers=headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Retrieved document: {data['name']}")
            print(f"   Content length: {len(data['content'])} characters")
            print(f"   Version ID: {data['metadata'].get('version_id', 'N/A')}")
            
            # Show first 200 chars of content
            content_preview = data['content'][:200]
            print(f"\n   Content preview:")
            print(f"   {content_preview}...")
            
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def test_update_document():
    """Test PUT /kb-document/{id}"""
    print("\n" + "="*70)
    print("TEST 3: Update Document (Test Edit)")
    print("="*70)
    
    if not JWT_TOKEN:
        print("❌ JWT_TOKEN not set. Please set JWT_TOKEN variable.")
        return False
    
    headers = {
        'Authorization': f'Bearer {JWT_TOKEN}',
        'Content-Type': 'application/json'
    }
    document_id = 'curated-qa/common-questions.md'
    
    # First, get current content
    try:
        response = requests.get(f'{API_BASE}/kb-document/{document_id}', headers=headers)
        if response.status_code != 200:
            print(f"❌ Could not fetch current content: {response.text}")
            return False
        
        current_content = response.json()['content']
        
        # Add a test comment at the end
        test_comment = f"\n\n<!-- Test edit at {time.strftime('%Y-%m-%d %H:%M:%S')} -->\n"
        new_content = current_content + test_comment
        
        # Update document
        payload = {
            'content': new_content,
            'change_comment': 'Test edit from KB editor endpoint test script'
        }
        
        response = requests.put(
            f'{API_BASE}/kb-document/{document_id}',
            headers=headers,
            json=payload
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Document updated successfully")
            print(f"   Edit ID: {data['edit_id']}")
            print(f"   S3 Version: {data['s3_version_id']}")
            print(f"   Ingestion Job: {data['ingestion_job_id']}")
            print(f"   Contribution Points: {data['contribution_points']}")
            print(f"   Status: {data['ingestion_status']}")
            
            return data['ingestion_job_id']
        else:
            print(f"❌ Error: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def test_ingestion_status(job_id):
    """Test GET /kb-ingestion-status/{job_id}"""
    print("\n" + "="*70)
    print("TEST 4: Check Ingestion Status")
    print("="*70)
    
    if not JWT_TOKEN:
        print("❌ JWT_TOKEN not set. Please set JWT_TOKEN variable.")
        return False
    
    if not job_id:
        print("⚠️  No job ID provided, skipping test")
        return True
    
    headers = {'Authorization': f'Bearer {JWT_TOKEN}'}
    
    try:
        response = requests.get(f'{API_BASE}/kb-ingestion-status/{job_id}', headers=headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Ingestion job status: {data['status']}")
            print(f"   Job ID: {data['job_id']}")
            print(f"   Started: {data.get('started_at', 'N/A')}")
            print(f"   Completed: {data.get('completed_at', 'N/A')}")
            
            if data.get('statistics'):
                print(f"   Statistics: {json.dumps(data['statistics'], indent=2)}")
            
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def test_contributors():
    """Test GET /kb-contributors"""
    print("\n" + "="*70)
    print("TEST 5: Get Contributor Leaderboard")
    print("="*70)
    
    if not JWT_TOKEN:
        print("❌ JWT_TOKEN not set. Please set JWT_TOKEN variable.")
        return False
    
    headers = {'Authorization': f'Bearer {JWT_TOKEN}'}
    
    try:
        response = requests.get(f'{API_BASE}/kb-contributors?period=month&limit=10', headers=headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            contributors = data.get('contributors', [])
            print(f"✅ Found {len(contributors)} contributors")
            print(f"   Period: {data['period']}")
            
            if contributors:
                print(f"\n   Top Contributors:")
                for contrib in contributors[:5]:
                    print(f"   #{contrib['rank']} {contrib['display_name']}")
                    print(f"       Edits: {contrib['total_edits']}, Lines: {contrib['lines_added']}")
            else:
                print(f"   ℹ️  No contributors yet")
            
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def test_my_contributions():
    """Test GET /kb-my-contributions"""
    print("\n" + "="*70)
    print("TEST 6: Get My Contributions")
    print("="*70)
    
    if not JWT_TOKEN:
        print("❌ JWT_TOKEN not set. Please set JWT_TOKEN variable.")
        return False
    
    headers = {'Authorization': f'Bearer {JWT_TOKEN}'}
    
    try:
        response = requests.get(f'{API_BASE}/kb-my-contributions?limit=10', headers=headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            stats = data.get('stats', {})
            contributions = data.get('recent_contributions', [])
            
            print(f"✅ Retrieved contribution stats")
            print(f"   Display Name: {data['display_name']}")
            print(f"   Total Edits: {stats.get('total_edits', 0)}")
            print(f"   Lines Added: {stats.get('total_lines_added', 0)}")
            print(f"   Documents Edited: {stats.get('documents_edited_count', 0)}")
            
            if contributions:
                print(f"\n   Recent Contributions:")
                for contrib in contributions[:3]:
                    print(f"   • {contrib['document_name']}")
                    print(f"     Comment: {contrib['change_comment']}")
                    print(f"     Lines: +{contrib['lines_added']} -{contrib['lines_removed']}")
            else:
                print(f"   ℹ️  No contributions yet")
            
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("KB EDITOR API ENDPOINT TESTS - STAGING")
    print("="*70)
    
    if not JWT_TOKEN:
        print("\n⚠️  JWT_TOKEN not set!")
        print("\nTo get a JWT token:")
        print("1. Go to https://staging.awseuccontent.com")
        print("2. Sign in with your account")
        print("3. Open browser DevTools (F12)")
        print("4. Go to Application > Local Storage > https://staging.awseuccontent.com")
        print("5. Copy the value of 'id_token'")
        print("6. Set JWT_TOKEN variable in this script")
        print("\nExample:")
        print("JWT_TOKEN = 'eyJraWQiOiJ...'")
        return
    
    results = []
    
    # Test 1: List documents
    results.append(('List Documents', test_list_documents()))
    
    # Test 2: Get document
    results.append(('Get Document', test_get_document()))
    
    # Test 3: Update document (returns job_id)
    job_id = test_update_document()
    results.append(('Update Document', bool(job_id)))
    
    # Test 4: Check ingestion status
    if job_id:
        time.sleep(2)  # Wait a bit for ingestion to start
        results.append(('Ingestion Status', test_ingestion_status(job_id)))
    
    # Test 5: Get contributors
    results.append(('Contributors', test_contributors()))
    
    # Test 6: Get my contributions
    results.append(('My Contributions', test_my_contributions()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

if __name__ == '__main__':
    main()
