#!/usr/bin/env python3
"""
Create DynamoDB Tables for KB Editor - Staging

This script creates two DynamoDB tables:
1. kb-edit-history-staging - Immutable audit log
2. kb-contributor-stats-staging - Aggregated contributor statistics
"""

import boto3
import json
from datetime import datetime

# Configuration
REGION = 'us-east-1'
ENVIRONMENT = 'staging'

# Table names
EDIT_HISTORY_TABLE = f'kb-edit-history-{ENVIRONMENT}'
CONTRIBUTOR_STATS_TABLE = f'kb-contributor-stats-{ENVIRONMENT}'

# Initialize AWS client
dynamodb = boto3.client('dynamodb', region_name=REGION)

def print_step(step_num, description):
    """Print formatted step header"""
    print(f"\n{'='*80}")
    print(f"STEP {step_num}: {description}")
    print(f"{'='*80}\n")

def create_edit_history_table():
    """Create kb-edit-history table"""
    print_step(1, "Creating kb-edit-history Table")
    
    try:
        response = dynamodb.create_table(
            TableName=EDIT_HISTORY_TABLE,
            KeySchema=[
                {
                    'AttributeName': 'edit_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'edit_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'document_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'timestamp',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user_id-timestamp-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'user_id',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'timestamp',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                },
                {
                    'IndexName': 'document_id-timestamp-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'document_id',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'timestamp',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                }
            ],
            BillingMode='PAY_PER_REQUEST',  # On-demand pricing
            Tags=[
                {
                    'Key': 'Environment',
                    'Value': ENVIRONMENT
                },
                {
                    'Key': 'Project',
                    'Value': 'EUC-Content-Hub'
                },
                {
                    'Key': 'Purpose',
                    'Value': 'KB-Edit-Audit-Log'
                }
            ]
        )
        
        print(f"✓ Created table: {EDIT_HISTORY_TABLE}")
        print(f"  Status: {response['TableDescription']['TableStatus']}")
        print(f"  ARN: {response['TableDescription']['TableArn']}")
        
        return response['TableDescription']['TableArn']
        
    except dynamodb.exceptions.ResourceInUseException:
        print(f"✓ Table {EDIT_HISTORY_TABLE} already exists")
        response = dynamodb.describe_table(TableName=EDIT_HISTORY_TABLE)
        return response['Table']['TableArn']
    except Exception as e:
        print(f"✗ Error creating table: {str(e)}")
        raise

def create_contributor_stats_table():
    """Create kb-contributor-stats table"""
    print_step(2, "Creating kb-contributor-stats Table")
    
    try:
        response = dynamodb.create_table(
            TableName=CONTRIBUTOR_STATS_TABLE,
            KeySchema=[
                {
                    'AttributeName': 'user_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST',  # On-demand pricing
            Tags=[
                {
                    'Key': 'Environment',
                    'Value': ENVIRONMENT
                },
                {
                    'Key': 'Project',
                    'Value': 'EUC-Content-Hub'
                },
                {
                    'Key': 'Purpose',
                    'Value': 'KB-Contributor-Stats'
                }
            ]
        )
        
        print(f"✓ Created table: {CONTRIBUTOR_STATS_TABLE}")
        print(f"  Status: {response['TableDescription']['TableStatus']}")
        print(f"  ARN: {response['TableDescription']['TableArn']}")
        
        return response['TableDescription']['TableArn']
        
    except dynamodb.exceptions.ResourceInUseException:
        print(f"✓ Table {CONTRIBUTOR_STATS_TABLE} already exists")
        response = dynamodb.describe_table(TableName=CONTRIBUTOR_STATS_TABLE)
        return response['Table']['TableArn']
    except Exception as e:
        print(f"✗ Error creating table: {str(e)}")
        raise

def wait_for_tables():
    """Wait for tables to become active"""
    print_step(3, "Waiting for Tables to Become Active")
    
    waiter = dynamodb.get_waiter('table_exists')
    
    print(f"Waiting for {EDIT_HISTORY_TABLE}...")
    waiter.wait(
        TableName=EDIT_HISTORY_TABLE,
        WaiterConfig={
            'Delay': 5,
            'MaxAttempts': 25
        }
    )
    print(f"✓ {EDIT_HISTORY_TABLE} is active")
    
    print(f"Waiting for {CONTRIBUTOR_STATS_TABLE}...")
    waiter.wait(
        TableName=CONTRIBUTOR_STATS_TABLE,
        WaiterConfig={
            'Delay': 5,
            'MaxAttempts': 25
        }
    )
    print(f"✓ {CONTRIBUTOR_STATS_TABLE} is active")

def verify_tables():
    """Verify tables are created correctly"""
    print_step(4, "Verifying Tables")
    
    # Verify edit history table
    response = dynamodb.describe_table(TableName=EDIT_HISTORY_TABLE)
    table = response['Table']
    
    print(f"\n{EDIT_HISTORY_TABLE}:")
    print(f"  Status: {table['TableStatus']}")
    print(f"  Item Count: {table['ItemCount']}")
    print(f"  Size: {table['TableSizeBytes']} bytes")
    print(f"  GSIs: {len(table.get('GlobalSecondaryIndexes', []))}")
    
    for gsi in table.get('GlobalSecondaryIndexes', []):
        print(f"    - {gsi['IndexName']}: {gsi['IndexStatus']}")
    
    # Verify contributor stats table
    response = dynamodb.describe_table(TableName=CONTRIBUTOR_STATS_TABLE)
    table = response['Table']
    
    print(f"\n{CONTRIBUTOR_STATS_TABLE}:")
    print(f"  Status: {table['TableStatus']}")
    print(f"  Item Count: {table['ItemCount']}")
    print(f"  Size: {table['TableSizeBytes']} bytes")

def save_config():
    """Save table configuration"""
    print_step(5, "Saving Configuration")
    
    config = {
        'environment': ENVIRONMENT,
        'region': REGION,
        'tables': {
            'edit_history': EDIT_HISTORY_TABLE,
            'contributor_stats': CONTRIBUTOR_STATS_TABLE
        },
        'created_at': datetime.now().isoformat()
    }
    
    # Load existing config if it exists
    try:
        with open('kb-config-staging.json', 'r') as f:
            existing_config = json.load(f)
            existing_config.update(config)
            config = existing_config
    except FileNotFoundError:
        pass
    
    with open('kb-config-staging.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✓ Configuration saved to kb-config-staging.json")

def main():
    """Main function"""
    print(f"\n{'#'*80}")
    print(f"# Create DynamoDB Tables for KB Editor - {ENVIRONMENT.upper()}")
    print(f"# Region: {REGION}")
    print(f"# Timestamp: {datetime.now().isoformat()}")
    print(f"{'#'*80}\n")
    
    try:
        # Step 1: Create edit history table
        edit_history_arn = create_edit_history_table()
        
        # Step 2: Create contributor stats table
        contributor_stats_arn = create_contributor_stats_table()
        
        # Step 3: Wait for tables to become active
        wait_for_tables()
        
        # Step 4: Verify tables
        verify_tables()
        
        # Step 5: Save configuration
        save_config()
        
        # Summary
        print(f"\n{'='*80}")
        print("TABLE CREATION COMPLETE!")
        print(f"{'='*80}\n")
        
        print("Tables Created:")
        print(f"  1. {EDIT_HISTORY_TABLE}")
        print(f"     ARN: {edit_history_arn}")
        print(f"     Purpose: Immutable audit log of all KB edits")
        print(f"     GSIs: user_id-timestamp-index, document_id-timestamp-index")
        
        print(f"\n  2. {CONTRIBUTOR_STATS_TABLE}")
        print(f"     ARN: {contributor_stats_arn}")
        print(f"     Purpose: Aggregated contributor statistics")
        print(f"     GSIs: None (simple key-value lookup)")
        
        print("\nBilling Mode: PAY_PER_REQUEST (On-Demand)")
        print("Estimated Cost: $2-3/month")
        
        print("\nNext Steps:")
        print("  1. Implement Lambda endpoints for KB editor")
        print("  2. Test edit tracking and contributor stats")
        print("  3. Deploy frontend UI")
        
    except Exception as e:
        print(f"\n{'='*80}")
        print("TABLE CREATION FAILED!")
        print(f"{'='*80}\n")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
