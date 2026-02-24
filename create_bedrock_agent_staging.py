#!/usr/bin/env python3
"""
Create Bedrock Agent - Staging Environment

Phase 2: Create a Bedrock Agent that uses the Knowledge Base
to provide deterministic, structured responses.
"""

import boto3
import json
import time
from datetime import datetime

# Load configuration
with open('kb-config-staging.json') as f:
    config = json.load(f)

REGION = config['region']
ACCOUNT_ID = config['account_id']
KB_ID = config['knowledge_base_id']
ENVIRONMENT = 'staging'

# Agent configuration
AGENT_NAME = f'euc-content-assistant-{ENVIRONMENT}'
AGENT_DESCRIPTION = 'AI assistant for EUC Content Hub - provides deterministic answers using curated knowledge base'

# Initialize AWS clients
iam = boto3.client('iam', region_name=REGION)
bedrock_agent = boto3.client('bedrock-agent', region_name=REGION)

def print_step(step_num, description):
    """Print formatted step header"""
    print(f"\n{'='*80}")
    print(f"STEP {step_num}: {description}")
    print(f"{'='*80}\n")

def create_agent_iam_role():
    """Create IAM role for Bedrock Agent"""
    print_step(1, "Creating IAM Role for Bedrock Agent")
    
    role_name = f'BedrockAgentRole-{ENVIRONMENT}'
    
    # Trust policy for Bedrock Agent
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": ACCOUNT_ID
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:agent/*"
                    }
                }
            }
        ]
    }
    
    # Permissions policy
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel"
                ],
                "Resource": [
                    f"arn:aws:bedrock:{REGION}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:Retrieve"
                ],
                "Resource": [
                    f"arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:knowledge-base/{KB_ID}"
                ]
            }
        ]
    }
    
    try:
        # Check if role exists
        try:
            role = iam.get_role(RoleName=role_name)
            print(f"✓ Role {role_name} already exists")
            role_arn = role['Role']['Arn']
        except iam.exceptions.NoSuchEntityException:
            # Create role
            role = iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f'Role for Bedrock Agent - {ENVIRONMENT}',
                Tags=[
                    {'Key': 'Environment', 'Value': ENVIRONMENT},
                    {'Key': 'Project', 'Value': 'EUC-Content-Hub'}
                ]
            )
            role_arn = role['Role']['Arn']
            print(f"✓ Created role: {role_name}")
        
        # Attach inline policy
        policy_name = f'BedrockAgentPolicy-{ENVIRONMENT}'
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(permissions_policy)
        )
        print(f"✓ Attached policy: {policy_name}")
        
        return role_arn
        
    except Exception as e:
        print(f"✗ Error creating IAM role: {str(e)}")
        raise

def create_agent(role_arn):
    """Create Bedrock Agent"""
    print_step(2, "Creating Bedrock Agent")
    
    # Agent instruction - this is the key to deterministic responses
    agent_instruction = """You are an AI assistant for the EUC Content Hub, helping users discover AWS End User Computing content and answer questions about EUC services.

RESPONSE RULES:
1. ALWAYS prioritize information from the knowledge base (curated Q&A and service mappings)
2. Provide concise, accurate answers (2-3 paragraphs maximum)
3. When mentioning renamed services, ALWAYS include a warning about the old name
4. Cite sources by mentioning if information comes from "curated Q&A" or "service documentation"
5. Use bullet points for lists to improve readability
6. Include a "Learn More" section with relevant topics when appropriate

RESPONSE FORMAT:
[Direct answer to the question - 2-3 paragraphs]

**Key Points:**
- [Important point 1]
- [Important point 2]
- [Important point 3]

**Service Rename Alert:** (if applicable)
[Mention if any services discussed have been renamed, with old and new names]

**Learn More:**
- [Related topic 1]
- [Related topic 2]

IMPORTANT GUIDELINES:
- If the knowledge base doesn't have information, say "I don't have specific information about that in my knowledge base"
- Never make up information - only use what's in the knowledge base
- For questions about blog posts, acknowledge that you can help users find relevant content
- Keep responses professional but friendly
- Use "Amazon" prefix for service names (e.g., "Amazon WorkSpaces Personal" not just "WorkSpaces Personal")

EXAMPLE RESPONSE:
User: "What is EUC?"

EUC stands for End User Computing. It refers to AWS services that enable end users to access applications and desktops, including Amazon WorkSpaces, Amazon AppStream 2.0, Amazon WorkSpaces Web, and Amazon Connect. These services help organizations provide secure, scalable access to applications and desktops for remote workers, contractors, and partners.

The EUC family includes services for virtual desktops (WorkSpaces Personal), application streaming (WorkSpaces Applications), secure web access (WorkSpaces Secure Browser), and contact centers (Amazon Connect).

**Key Points:**
- EUC services enable remote access to applications and desktops
- Includes virtual desktop infrastructure (VDI) and application streaming
- Designed for security, scalability, and ease of management
- Supports various use cases: remote work, BYOD, contractor access, contact centers

**Learn More:**
- Amazon WorkSpaces Personal for persistent virtual desktops
- Amazon WorkSpaces Applications for application streaming
- Amazon Connect for cloud contact centers
"""

    try:
        # Check if agent exists
        try:
            agents = bedrock_agent.list_agents()
            for agent in agents.get('agentSummaries', []):
                if agent['agentName'] == AGENT_NAME:
                    agent_id = agent['agentId']
                    print(f"✓ Agent {AGENT_NAME} already exists")
                    print(f"  Agent ID: {agent_id}")
                    return agent_id
        except:
            pass
        
        # Create agent
        print("Creating agent (this may take a minute)...")
        response = bedrock_agent.create_agent(
            agentName=AGENT_NAME,
            description=AGENT_DESCRIPTION,
            agentResourceRoleArn=role_arn,
            foundationModel='anthropic.claude-3-5-sonnet-20241022-v2:0',
            instruction=agent_instruction,
            idleSessionTTLInSeconds=600,  # 10 minutes
            tags={
                'Environment': ENVIRONMENT,
                'Project': 'EUC-Content-Hub'
            }
        )
        
        agent_id = response['agent']['agentId']
        print(f"✓ Created agent: {AGENT_NAME}")
        print(f"  Agent ID: {agent_id}")
        
        return agent_id
        
    except Exception as e:
        print(f"✗ Error creating agent: {str(e)}")
        raise

def associate_knowledge_base(agent_id):
    """Associate Knowledge Base with Agent"""
    print_step(3, "Associating Knowledge Base with Agent")
    
    try:
        # Check if already associated
        try:
            associations = bedrock_agent.list_agent_knowledge_bases(agentId=agent_id)
            for assoc in associations.get('agentKnowledgeBaseSummaries', []):
                if assoc['knowledgeBaseId'] == KB_ID:
                    print(f"✓ Knowledge Base already associated")
                    return
        except:
            pass
        
        # Associate KB with agent
        response = bedrock_agent.associate_agent_knowledge_base(
            agentId=agent_id,
            agentVersion='DRAFT',
            knowledgeBaseId=KB_ID,
            description='EUC Content Hub knowledge base with curated Q&A and service mappings',
            knowledgeBaseState='ENABLED'
        )
        
        print(f"✓ Associated Knowledge Base with Agent")
        print(f"  KB ID: {KB_ID}")
        
    except Exception as e:
        print(f"✗ Error associating knowledge base: {str(e)}")
        raise

def prepare_agent(agent_id):
    """Prepare agent (required before creating alias)"""
    print_step(4, "Preparing Agent")
    
    try:
        print("Preparing agent (this may take 1-2 minutes)...")
        response = bedrock_agent.prepare_agent(agentId=agent_id)
        
        status = response['agentStatus']
        print(f"  Initial status: {status}")
        
        # Wait for preparation to complete
        max_wait = 180  # 3 minutes
        wait_interval = 10
        elapsed = 0
        
        while elapsed < max_wait:
            time.sleep(wait_interval)
            elapsed += wait_interval
            
            agent_response = bedrock_agent.get_agent(agentId=agent_id)
            status = agent_response['agent']['agentStatus']
            print(f"  Status: {status} ({elapsed}s elapsed)")
            
            if status == 'PREPARED':
                print(f"✓ Agent is prepared!")
                return True
            elif status == 'FAILED':
                raise Exception("Agent preparation failed")
        
        raise Exception("Agent preparation timed out")
        
    except Exception as e:
        print(f"✗ Error preparing agent: {str(e)}")
        raise

def create_agent_alias(agent_id):
    """Create agent alias for stable endpoint"""
    print_step(5, "Creating Agent Alias")
    
    alias_name = f'{ENVIRONMENT}-alias'
    
    try:
        # Check if alias exists
        try:
            aliases = bedrock_agent.list_agent_aliases(agentId=agent_id)
            for alias in aliases.get('agentAliasSummaries', []):
                if alias['agentAliasName'] == alias_name:
                    alias_id = alias['agentAliasId']
                    print(f"✓ Alias {alias_name} already exists")
                    print(f"  Alias ID: {alias_id}")
                    return alias_id
        except:
            pass
        
        # Create alias
        response = bedrock_agent.create_agent_alias(
            agentId=agent_id,
            agentAliasName=alias_name,
            description=f'Stable alias for {ENVIRONMENT} environment'
        )
        
        alias_id = response['agentAlias']['agentAliasId']
        print(f"✓ Created alias: {alias_name}")
        print(f"  Alias ID: {alias_id}")
        
        return alias_id
        
    except Exception as e:
        print(f"✗ Error creating alias: {str(e)}")
        raise

def main():
    """Main setup function"""
    print(f"\n{'#'*80}")
    print(f"# Bedrock Agent Creation - {ENVIRONMENT.upper()}")
    print(f"# Region: {REGION}")
    print(f"# Account: {ACCOUNT_ID}")
    print(f"# Knowledge Base: {KB_ID}")
    print(f"# Timestamp: {datetime.now().isoformat()}")
    print(f"{'#'*80}\n")
    
    try:
        # Step 1: Create IAM role
        role_arn = create_agent_iam_role()
        
        # Wait for IAM role to propagate
        print("\nWaiting 10 seconds for IAM role to propagate...")
        time.sleep(10)
        
        # Step 2: Create agent
        agent_id = create_agent(role_arn)
        
        # Step 3: Associate knowledge base
        associate_knowledge_base(agent_id)
        
        # Step 4: Prepare agent
        prepare_agent(agent_id)
        
        # Step 5: Create alias
        alias_id = create_agent_alias(agent_id)
        
        # Summary
        print(f"\n{'='*80}")
        print("AGENT CREATION COMPLETE!")
        print(f"{'='*80}\n")
        
        print("Resources Created:")
        print(f"  IAM Role: {role_arn}")
        print(f"  Agent ID: {agent_id}")
        print(f"  Agent Alias ID: {alias_id}")
        print(f"  Knowledge Base: {KB_ID}")
        
        print("\nNext Steps:")
        print("  1. Test agent with sample queries")
        print("  2. Refine agent instructions if needed")
        print("  3. Create chat Lambda integration (Phase 3)")
        
        # Update configuration
        config['agent_id'] = agent_id
        config['agent_alias_id'] = alias_id
        config['agent_role_arn'] = role_arn
        config['agent_created_at'] = datetime.now().isoformat()
        
        with open('kb-config-staging.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n✓ Configuration updated: kb-config-staging.json")
        
    except Exception as e:
        print(f"\n{'='*80}")
        print("AGENT CREATION FAILED!")
        print(f"{'='*80}\n")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
