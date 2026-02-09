# EUC Content Hub

A serverless AWS blog aggregator and community platform for End User Computing (EUC) content.

**Production Site**: https://awseuccontent.com  
**Staging Site**: https://staging.awseuccontent.com

## Overview

EUC Content Hub aggregates AWS blog posts from multiple sources, generates AI summaries, and provides a community platform for AWS End User Computing professionals to discover, bookmark, vote on, and discuss content.

## Features

### Content Aggregation
- **Multi-source crawling**: AWS Blog and Builder.AWS
- **Automatic content extraction**: Titles, authors, dates, full content
- **EUC filtering**: Only shows WorkSpaces, AppStream, and related content
- **Crawler Triggers**:
  - **Manual**: "Refresh Posts" button on website (authenticated users)
  - **On-Demand**: Direct Lambda invocation via AWS Console or CLI
  - **Note**: No scheduled/automatic crawling - all crawls are manually triggered

### AI-Powered Features
- **AI Summaries**: 2-3 sentence summaries using AWS Bedrock (Claude Haiku)
  - Generated in batches of 10 posts
  - Automatically triggered after crawler completes
  - Can be manually triggered via "Generate Summaries" button (admin)
- **Auto-classification**: Posts categorized by content type
  - Technical How-To
  - Thought Leadership
  - Product Announcement
  - Best Practices
  - Case Study
- **Chat Assistant**: AI-powered content discovery and Q&A using Claude Sonnet
- **Confidence scoring**: Classification confidence levels

### Community Features
- **User Authentication**: Google OAuth via AWS Cognito
- **User Profiles**: Display names, bios, Credly badges, Builder.AWS IDs
- **Bookmarks**: Save posts for later reading
- **Voting System**: Love posts, flag for updates, or suggest removal
- **Comments**: Discuss posts with the community
- **Activity Tracking**: View your bookmarks, votes, and comments

### User Experience
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Dark Mode**: Easy on the eyes
- **Advanced Filtering**: Filter by label, source, bookmarks
- **Search**: Find posts by title or content
- **Analytics Charts**: Top authors, recent posts, most loved content
- **Legal Compliance**: Privacy policy, Terms of Service, data deletion

## Architecture

### Blue-Green Deployment Strategy

The platform uses a blue-green deployment strategy with separate staging and production environments:

**Staging Environment**:
- **Purpose**: Test changes before production deployment
- **Site**: https://staging.awseuccontent.com
- **S3 Bucket**: `aws-blog-viewer-staging-031421429609`
- **CloudFront**: E1IB9VDMV64CQA
- **API**: https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging
- **DynamoDB Tables**: `aws-blog-posts-staging`, `euc-user-profiles-staging`
- **Lambda**: Uses `$LATEST` version (immediate deployment)

**Production Environment**:
- **Purpose**: Live site serving users
- **Site**: https://awseuccontent.com
- **S3 Bucket**: `aws-blog-viewer-031421429609`
- **CloudFront**: E20CC1TSSWTCWN
- **API**: https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod
- **DynamoDB Tables**: `aws-blog-posts`, `euc-user-profiles`
- **Lambda**: Uses versioned aliases (instant rollback capability)

**Deployment Workflow**:
1. Deploy changes to staging
2. Test thoroughly in staging environment
3. If tests pass, deploy to production
4. Monitor production and rollback if needed

See `DEPLOYMENT.md` for detailed deployment procedures.

### AWS Services
- **Lambda**: 6 serverless functions
  - API Gateway handler
  - AWS Blog crawler
  - Builder.AWS Selenium crawler
  - AI summary generator
  - Content classifier
  - Chat assistant
- **DynamoDB**: 2 tables (posts, user profiles)
- **S3**: Static website hosting
- **CloudFront**: Global CDN
- **API Gateway**: REST API
- **Cognito**: User authentication
- **Bedrock**: AI models (Claude Haiku, Claude Sonnet)
- **ECS/Fargate**: Containerized Selenium crawler

### Tech Stack
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Backend**: Python 3.11
- **AI**: AWS Bedrock (Claude models)
- **Web Scraping**: Selenium, BeautifulSoup, requests
- **Authentication**: JWT tokens, Cognito Hosted UI

## Quick Start

### Prerequisites
- AWS Account (account ID: 031421429609)
- AWS CLI configured
- Python 3.11+
- Domain name (optional)

### Deployment

**IMPORTANT**: Always deploy to staging first, test thoroughly, then deploy to production.

1. **Clone the repository**
```bash
git clone https://github.com/stetlers/euccontenthub.git
cd euccontenthub
```

2. **Set up AWS credentials**
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

3. **Deploy infrastructure** (see INFRASTRUCTURE.md for detailed setup)

4. **Deploy frontend to staging**
```bash
python deploy_frontend.py staging
```

5. **Test staging site**
- Visit https://staging.awseuccontent.com
- Test all functionality
- Check browser console for errors

6. **Deploy frontend to production** (if staging tests pass)
```bash
python deploy_frontend.py production
```

7. **Deploy Lambda functions to staging**
```bash
python deploy_lambda.py <function_name> staging
```

8. **Test staging API**
```bash
curl https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/posts
```

9. **Deploy Lambda functions to production** (if staging tests pass)
```bash
python deploy_lambda.py <function_name> production
```

See `DEPLOYMENT.md` for complete deployment runbook with rollback procedures.

## Usage

### For Users
1. Visit https://awseuccontent.com
2. Browse posts or use filters
3. Sign in with Google to bookmark, vote, and comment
4. Use the chat assistant (bottom right) for content discovery

### For Developers
- See `AGENTS.md` for AI agent guidance
- See `INFRASTRUCTURE.md` for AWS setup details
- See `CONTRIBUTING.md` for contribution guidelines

## Project Structure

```
.
├── frontend/              # Frontend SPA
│   ├── index.html        # Main page
│   ├── app.js            # Core application logic
│   ├── auth.js           # Authentication
│   ├── profile.js        # User profiles
│   ├── chat-widget.js    # AI chat assistant
│   └── styles.css        # Styling
├── api_lambda.py         # Main API Lambda
├── enhanced_crawler_lambda.py      # AWS Blog crawler
├── builder_selenium_crawler.py     # Builder.AWS crawler
├── summary_lambda.py     # AI summary generator
├── classifier_lambda.py  # Content classifier
├── chat_lambda.py        # AI chat assistant
├── deploy_*.py           # Deployment scripts
├── test_*.py             # Test scripts
├── check_*.py            # Diagnostic scripts
├── README.md             # This file
├── AGENTS.md             # AI agent guide
├── INFRASTRUCTURE.md     # AWS setup guide
├── CONTRIBUTING.md       # Contribution guidelines
└── LICENSE               # MIT License
```

## Key Features Explained

### Multi-Source Crawling
The platform crawls two sources:
- **AWS Blog**: RSS feed parsing with metadata extraction
- **Builder.AWS**: Selenium-based crawling for dynamic content and real author names

**How Crawlers Are Triggered**:
1. **Website Button**: "Refresh Posts" button (requires authentication)
2. **Manual Invocation**: Direct Lambda/ECS task invocation
3. **No Automatic Scheduling**: Crawlers do NOT run on a schedule

**Crawler Flow**:
1. User clicks "Refresh Posts" or manually invokes crawler
2. Crawler extracts posts and saves to DynamoDB
3. Crawler automatically invokes Summary Generator Lambda
4. Summary Generator processes posts in batches of 10
5. Summary Generator automatically invokes Classifier Lambda
6. Classifier categorizes posts in batches of 50

### AI Summaries
Every post gets a 2-3 sentence AI-generated summary using AWS Bedrock's Claude Haiku model.

**Summary Generation Process**:
- **Batch Size**: 10 posts per invocation
- **Trigger**: Automatically invoked by crawler when new posts are created
- **Manual Trigger**: "Generate Summaries" button (admin) or `generate_all_builder_summaries.py` script
- **Chaining**: Does NOT auto-chain - must be invoked multiple times for large batches
- **Storage**: Cached in DynamoDB `summary` field

### Content Classification
Posts are automatically classified by **content type** (not service):
- **Technical How-To**: Step-by-step guides and tutorials
- **Thought Leadership**: Opinion pieces and industry insights
- **Product Announcement**: New features and service launches
- **Best Practices**: Recommended approaches and patterns
- **Case Study**: Customer success stories and implementations
- **General**: Other EUC-related content

**Classification Process**:
- Uses AWS Bedrock (Claude Haiku)
- Analyzes title and content
- Provides confidence score (0-1)
- Triggered automatically after summary generation

### Chat Assistant
An AI-powered chat widget helps users discover content by:
- Answering questions about EUC topics
- Recommending relevant posts
- Explaining technical concepts
- Providing context from the post database

## API Endpoints

**Production Base URL**: `https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod`  
**Staging Base URL**: `https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging`

- `GET /posts` - List all posts
- `GET /posts/{id}` - Get single post
- `POST /posts/{id}/vote` - Vote on post (requires auth)
- `GET /posts/{id}/comments` - Get comments
- `POST /posts/{id}/comments` - Add comment (requires auth)
- `GET /profile` - Get user profile (requires auth)
- `PUT /profile` - Update profile (requires auth)
- `DELETE /profile` - Delete account (requires auth)
- `GET /bookmarks` - Get user bookmarks (requires auth)
- `POST /posts/{id}/bookmark` - Toggle bookmark (requires auth)
- `POST /chat` - Chat with AI assistant
- `POST /crawl` - Trigger crawler (admin)
- `POST /summaries` - Generate summaries (admin)

## Configuration

### Environment Variables
Lambda functions use these environment variables:
- `DYNAMODB_TABLE_NAME`: aws-blog-posts
- `PROFILES_TABLE_NAME`: euc-user-profiles
- `COGNITO_USER_POOL_ID`: Your Cognito User Pool ID
- `COGNITO_APP_CLIENT_ID`: Your Cognito App Client ID

### Frontend Configuration

**CRITICAL - S3 Bucket Configuration**:
- **Correct Bucket**: `aws-blog-viewer-031421429609`
- **Serves Domain**: `awseuccontent.com` (without www)
- **CloudFront ID**: `E20CC1TSSWTCWN`
- **Wrong Bucket**: `www.awseuccontent.com` (DO NOT USE - exists but not configured)

**Why This Matters**:
- There are TWO S3 buckets with similar names
- Only `aws-blog-viewer-031421429609` is properly configured
- Deploying to wrong bucket breaks the website
- Always use `deploy_frontend_complete.py` which targets correct bucket

**API Endpoint Configuration**:
The deployment script automatically replaces the placeholder in `frontend/app.js`:
```javascript
const API_ENDPOINT = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod';
```

## Monitoring

### CloudWatch Logs
- `/aws/lambda/aws-blog-api` - API requests
- `/aws/lambda/aws-blog-crawler` - Crawler activity
- `/aws/lambda/aws-blog-summary-generator` - Summary generation
- `/aws/lambda/aws-blog-classifier` - Classification
- `/aws/lambda/aws-blog-chat` - Chat interactions

### Diagnostic Scripts
```bash
python check_api_lambda_errors.py      # Check API errors
python check_summary_lambda_logs.py    # Check summary generation
python test_api_posts_endpoint.py      # Test API endpoint
```

## Costs

Estimated monthly costs (low traffic):
- Lambda: $5-10
- DynamoDB: $2-5
- S3: $1-2
- CloudFront: $1-5
- Bedrock: $10-20 (depends on usage)
- **Total**: ~$20-40/month

## Security

- JWT token validation for authenticated endpoints
- CORS enabled for cross-origin requests
- Secrets stored in environment variables (not in code)
- User data deletion capability (GDPR compliant)
- Input validation and sanitization
- Rate limiting on API Gateway

## Contributing

See `CONTRIBUTING.md` for guidelines on:
- Code style
- Pull request process
- Testing requirements
- Documentation standards

## License

MIT License - see `LICENSE` file for details

## Support

- **Issues**: https://github.com/stetlers/euccontenthub/issues
- **Discussions**: https://github.com/stetlers/euccontenthub/discussions

## Acknowledgments

- AWS Blog team for excellent EUC content
- Builder.AWS community for sharing knowledge
- AWS Bedrock team for Claude models
- Open source community for tools and libraries

## Roadmap

- [ ] Email notifications for new posts
- [ ] RSS feed for bookmarked posts
- [ ] Advanced search with filters
- [ ] Post recommendations based on reading history
- [ ] Mobile app (React Native)
- [ ] Integration with AWS re:Post
- [ ] Multi-language support
- [ ] Dark mode improvements

---

Built with ❤️ for the AWS End User Computing community
