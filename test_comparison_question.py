"""
Test comparison question to verify answer-first structure
"""

import json
import urllib.request

STAGING_API = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/chat'

def test_comparison_question(query):
    """Test a comparison question"""
    print(f"\n{'='*80}")
    print(f"Testing: {query}")
    print(f"{'='*80}\n")
    
    try:
        request_body = {'message': query}
        json_data = json.dumps(request_body).encode('utf-8')
        
        req = urllib.request.Request(
            STAGING_API,
            data=json_data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        print(f"✅ Response received\n")
        
        ai_response = data.get('response', 'No response')
        print(f"AI Response:\n{ai_response}\n")
        
        # Check response structure
        response_lower = ai_response.lower()
        
        # Check if it answers the question first
        first_sentence = ai_response.split('.')[0] if '.' in ai_response else ai_response
        
        print(f"Analysis:")
        print(f"First sentence: {first_sentence}")
        
        # For "Is X the same as Y?" questions, check if first sentence contains answer
        if 'is' in query.lower() and 'same' in query.lower():
            if 'no' in first_sentence.lower() or 'different' in first_sentence.lower() or 'not the same' in first_sentence.lower():
                print(f"✅ GOOD: Answers question first (No/Different)")
            elif 'yes' in first_sentence.lower() or 'same' in first_sentence.lower():
                print(f"✅ GOOD: Answers question first (Yes/Same)")
            elif 'renamed' in first_sentence.lower() or 'appstream' in first_sentence.lower():
                print(f"⚠️  BAD: Mentions rename before answering question")
            else:
                print(f"⚠️  UNCLEAR: Doesn't clearly answer yes/no first")
        
        # Check if rename is mentioned
        if 'renamed' in response_lower or 'formerly' in response_lower or 'now called' in response_lower:
            print(f"✅ Mentions service rename")
        else:
            print(f"⚠️  Does not mention service rename")
        
        # Show AWS docs
        aws_docs = data.get('aws_docs', [])
        print(f"\n📚 AWS Documentation References: {len(aws_docs)}")
        
        # Show recommendations
        recommendations = data.get('recommendations', [])
        print(f"📝 Blog Recommendations: {len(recommendations)}")
        
        return data
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    # Test comparison questions
    test_comparison_question("Is WorkSpaces Secure Browser the same thing as AppStream 2.0?")
    test_comparison_question("Is AppStream 2.0 the same as WorkSpaces Applications?")
    test_comparison_question("What is the difference between WorkSpaces and AppStream?")
