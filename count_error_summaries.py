"""
Count posts with error summaries (read-only check)
"""
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("\n" + "="*80)
print("Checking for Error Summaries")
print("="*80)

# Scan for posts
response = table.scan()
posts = response['Items']

while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    posts.extend(response['Items'])

# Count different types
total = len(posts)
with_summaries = sum(1 for p in posts if p.get('summary'))
error_summaries = sum(1 for p in posts if p.get('summary') and ('Error generating summary' in p['summary'] or 'ThrottlingException' in p['summary']))
good_summaries = with_summaries - error_summaries
without_summaries = total - with_summaries

print(f"\nTotal posts: {total}")
print(f"Posts with good summaries: {good_summaries} ({good_summaries*100//total if total > 0 else 0}%)")
print(f"Posts with error summaries: {error_summaries} ({error_summaries*100//total if total > 0 else 0}%)")
print(f"Posts without summaries: {without_summaries} ({without_summaries*100//total if total > 0 else 0}%)")

if error_summaries > 0:
    print(f"\n⚠️  {error_summaries} posts have error messages as summaries")
    print("   These need to be cleared so auto-chain can regenerate them")
    print("\n   Run: python fix_throttled_summaries.py")
else:
    print("\n✅ No error summaries found!")

print("\n" + "="*80)
