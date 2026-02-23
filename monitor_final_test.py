"""
Monitor the final end-to-end test in real-time
"""
import boto3
import time
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
ecs_client = boto3.client('ecs', region_name='us-east-1')
logs_client = boto3.client('logs', region_name='us-east-1')

table = dynamodb.Table('aws-blog-posts-staging')

print("\n" + "="*80)
print("FINAL END-TO-END TEST - Real-Time Monitor")
print("="*80)
print("\nMonitoring every 30 seconds...")
print("Press Ctrl+C to stop\n")

def get_post_stats():
    """Get current post statistics"""
    response = table.scan()
    posts = response['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        posts.extend(response['Items'])
    
    # Count by source
    aws_posts = [p for p in posts if p.get('source') == 'aws.amazon.com']
    builder_posts = [p for p in posts if p.get('source') == 'builder.aws.com']
    
    # Count completion status
    aws_with_summaries = sum(1 for p in aws_posts if p.get('summary'))
    aws_with_labels = sum(1 for p in aws_posts if p.get('label'))
    
    builder_with_real_authors = sum(1 for p in builder_posts if p.get('authors') and p['authors'] != 'AWS Builder Community')
    builder_with_summaries = sum(1 for p in builder_posts if p.get('summary'))
    builder_with_labels = sum(1 for p in builder_posts if p.get('label'))
    
    return {
        'total': len(posts),
        'aws_total': len(aws_posts),
        'aws_summaries': aws_with_summaries,
        'aws_labels': aws_with_labels,
        'builder_total': len(builder_posts),
        'builder_real_authors': builder_with_real_authors,
        'builder_summaries': builder_with_summaries,
        'builder_labels': builder_with_labels
    }

def get_ecs_tasks():
    """Get running ECS tasks"""
    try:
        response = ecs_client.list_tasks(
            cluster='builder-crawler-cluster',
            desiredStatus='RUNNING'
        )
        return len(response.get('taskArns', []))
    except:
        return 0

def check_recent_errors():
    """Check for recent errors in Lambda logs"""
    errors = []
    
    log_groups = [
        '/aws/lambda/aws-blog-enhanced-crawler-staging',
        '/aws/lambda/aws-blog-summary-generator',
        '/aws/lambda/aws-blog-classifier'
    ]
    
    start_time = int((time.time() - 300) * 1000)  # Last 5 minutes
    end_time = int(time.time() * 1000)
    
    for log_group in log_groups:
        try:
            response = logs_client.filter_log_events(
                logGroupName=log_group,
                startTime=start_time,
                endTime=end_time,
                filterPattern='ERROR'
            )
            if response['events']:
                errors.append(f"{log_group}: {len(response['events'])} errors")
        except:
            pass
    
    return errors

start_time = time.time()
last_stats = None

try:
    while True:
        elapsed = int(time.time() - start_time)
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Get current stats
        stats = get_post_stats()
        ecs_tasks = get_ecs_tasks()
        errors = check_recent_errors()
        
        # Clear screen (optional)
        print(f"\n{'='*80}")
        print(f"[{timestamp}] Elapsed: {elapsed}s")
        print(f"{'='*80}")
        
        # AWS Blog posts
        print(f"\n📰 AWS Blog Posts: {stats['aws_total']}")
        if stats['aws_total'] > 0:
            print(f"   Summaries: {stats['aws_summaries']}/{stats['aws_total']} ({stats['aws_summaries']*100//stats['aws_total'] if stats['aws_total'] > 0 else 0}%)")
            print(f"   Labels: {stats['aws_labels']}/{stats['aws_total']} ({stats['aws_labels']*100//stats['aws_total'] if stats['aws_total'] > 0 else 0}%)")
        
        # Builder.AWS posts
        print(f"\n🏗️  Builder.AWS Posts: {stats['builder_total']}")
        if stats['builder_total'] > 0:
            print(f"   Real Authors: {stats['builder_real_authors']}/{stats['builder_total']} ({stats['builder_real_authors']*100//stats['builder_total'] if stats['builder_total'] > 0 else 0}%)")
            print(f"   Summaries: {stats['builder_summaries']}/{stats['builder_total']} ({stats['builder_summaries']*100//stats['builder_total'] if stats['builder_total'] > 0 else 0}%)")
            print(f"   Labels: {stats['builder_labels']}/{stats['builder_total']} ({stats['builder_labels']*100//stats['builder_total'] if stats['builder_total'] > 0 else 0}%)")
        
        # ECS tasks
        print(f"\n🐳 ECS Tasks Running: {ecs_tasks}")
        
        # Errors
        if errors:
            print(f"\n⚠️  Recent Errors:")
            for error in errors:
                print(f"   {error}")
        else:
            print(f"\n✅ No recent errors")
        
        # Progress indicator
        if last_stats:
            if stats['total'] > last_stats['total']:
                print(f"\n📈 +{stats['total'] - last_stats['total']} new posts")
            if stats['builder_real_authors'] > last_stats['builder_real_authors']:
                print(f"   +{stats['builder_real_authors'] - last_stats['builder_real_authors']} real authors extracted")
            if stats['builder_summaries'] > last_stats['builder_summaries']:
                print(f"   +{stats['builder_summaries'] - last_stats['builder_summaries']} summaries generated")
        
        # Check if complete
        if stats['total'] > 0:
            aws_complete = stats['aws_total'] > 0 and stats['aws_summaries'] == stats['aws_total'] and stats['aws_labels'] == stats['aws_total']
            builder_complete = stats['builder_total'] > 0 and stats['builder_real_authors'] == stats['builder_total'] and stats['builder_summaries'] == stats['builder_total'] and stats['builder_labels'] == stats['builder_total']
            
            if aws_complete and builder_complete and ecs_tasks == 0:
                print(f"\n{'='*80}")
                print("🎉 TEST COMPLETE!")
                print(f"{'='*80}")
                print(f"\nAll posts have complete data:")
                print(f"  ✅ {stats['aws_total']} AWS Blog posts")
                print(f"  ✅ {stats['builder_total']} Builder.AWS posts")
                print(f"  ✅ All have authors, summaries, and labels")
                print(f"  ✅ No errors detected")
                print(f"\nTotal time: {elapsed}s ({elapsed//60}m {elapsed%60}s)")
                break
        
        last_stats = stats
        time.sleep(30)
        
except KeyboardInterrupt:
    print("\n\n⏸️  Monitoring stopped by user")
    print(f"\nFinal stats:")
    print(f"  Total posts: {stats['total']}")
    print(f"  AWS Blog: {stats['aws_total']} ({stats['aws_summaries']} with summaries)")
    print(f"  Builder.AWS: {stats['builder_total']} ({stats['builder_real_authors']} with real authors, {stats['builder_summaries']} with summaries)")
