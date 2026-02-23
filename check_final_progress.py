"""
Quick check of remaining posts without summaries
"""
import boto3
import time

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts-staging')

print("\nChecking progress every 30 seconds...")
print("Press Ctrl+C to stop\n")

try:
    while True:
        response = table.scan()
        posts = response['Items']
        
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            posts.extend(response['Items'])
        
        total = len(posts)
        without_summaries = sum(1 for p in posts if not p.get('summary'))
        with_summaries = total - without_summaries
        
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] {with_summaries}/{total} posts have summaries ({with_summaries*100//total}%) - {without_summaries} remaining")
        
        if without_summaries == 0:
            print("\n🎉 100% COMPLETE! All posts have summaries!")
            break
        
        time.sleep(30)
        
except KeyboardInterrupt:
    print("\n\nStopped by user")
