"""
Monitor Production Deployment Progress

Tracks:
- Total posts created
- Summaries generated
- Labels assigned
- Builder.AWS author status
"""
import boto3
import time
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts')

def get_status():
    """Get current production status"""
    response = table.scan()
    posts = response['Items']
    
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        posts.extend(response['Items'])
    
    total = len(posts)
    
    # Count by source
    aws_blog = len([p for p in posts if p.get('source') == 'aws.amazon.com'])
    builder = len([p for p in posts if p.get('source') == 'builder.aws.com'])
    
    # Count summaries
    with_summary = len([p for p in posts if p.get('summary') and p['summary'].strip()])
    without_summary = total - with_summary
    error_summary = len([p for p in posts if p.get('summary', '').startswith('Error generating')])
    
    # Count labels
    with_label = len([p for p in posts if p.get('label') and p['label'].strip()])
    
    # Builder.AWS authors
    builder_posts = [p for p in posts if p.get('source') == 'builder.aws.com']
    builder_community = len([p for p in builder_posts if p.get('authors') == 'AWS Builder Community'])
    builder_real = len([p for p in builder_posts if p.get('authors') and p['authors'] != 'AWS Builder Community'])
    
    return {
        'total': total,
        'aws_blog': aws_blog,
        'builder': builder,
        'with_summary': with_summary,
        'without_summary': without_summary,
        'error_summary': error_summary,
        'with_label': with_label,
        'builder_community': builder_community,
        'builder_real': builder_real
    }

print("=" * 80)
print("PRODUCTION DEPLOYMENT MONITOR")
print("=" * 80)
print("\nMonitoring production table: aws-blog-posts")
print("Press Ctrl+C to stop\n")

start_time = datetime.now()
iteration = 0

try:
    while True:
        iteration += 1
        elapsed = (datetime.now() - start_time).total_seconds() / 60
        
        status = get_status()
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Iteration {iteration} (Elapsed: {elapsed:.1f} min)")
        print(f"  Posts: {status['total']} (AWS: {status['aws_blog']}, Builder: {status['builder']})")
        print(f"  Summaries: {status['with_summary']}/{status['total']} ({status['with_summary']/max(status['total'],1)*100:.1f}%)")
        
        if status['error_summary'] > 0:
            print(f"  ⚠️  Error summaries: {status['error_summary']}")
        
        print(f"  Labels: {status['with_label']}/{status['total']} ({status['with_label']/max(status['total'],1)*100:.1f}%)")
        
        if status['builder'] > 0:
            print(f"  Builder Authors: Real={status['builder_real']}, Placeholder={status['builder_community']}")
        
        # Check if complete
        if status['total'] > 400:  # Expected ~479 posts
            completion = status['with_summary'] / status['total'] * 100
            if completion >= 95:
                print(f"\n🎉 DEPLOYMENT COMPLETE! {completion:.1f}% success rate")
                break
        
        time.sleep(30)  # Check every 30 seconds
        
except KeyboardInterrupt:
    print("\n\n⏸️  Monitoring stopped by user")
    print(f"Final status: {status['with_summary']}/{status['total']} posts with summaries")

print("\n" + "=" * 80)
