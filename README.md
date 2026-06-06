# 🚀 Autonomous SEO & Content Operations Engine

A sophisticated microservice managing dynamic automated loops and admin configurations for autonomous SEO operations and content generation.

## 📋 Features

- **Autonomous Content Generation**: Automatically discovers SEO opportunities and generates blog posts
- **Intelligent Profiling**: Create and manage dynamic SEO behavior and governance profiles
- **AI-Powered Writing**: Uses Gemini AI to generate SEO-optimized content
- **Human Approval Gates**: Built-in risk assessment and approval workflow
- **Real-time Monitoring**: Monitors content drift and performance metrics
- **Enterprise Auditing**: Complete AI provenance tracking and audit logs
- **Google Ecosystem Integration**: Leverages Google Trends, Google Ads API, and Custom Search

## 🛠️ Prerequisites

- Python 3.11+
- GCP Project with:
  - Firebase/Firestore enabled
  - Google Ads API credentials
  - Google Custom Search API configured
  - Gemini API access
- Docker (optional, for containerized deployment)

## 📦 Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd 1-tech-seo-agent
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

### 5. Set up Google credentials
Place your GCP service account JSON file in the project root or set `GOOGLE_APPLICATION_CREDENTIALS` in .env

## 🚀 Running the Application

### Development
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production (Docker)
```bash
docker build -t seo-agent .
docker run -p 8000:8000 --env-file .env seo-agent
```

### Local Testing
```bash
# Start the server
python -m uvicorn app.main:app --reload

# In another terminal, test the health endpoint
curl http://localhost:8000/
```

## 📚 API Endpoints

### Admin Panel

#### Create Agent Profile
```bash
POST /admin/profiles
Content-Type: application/json

{
  "profile_name": "Enterprise Tech Profile",
  "target_industries": ["Cloud Computing", "AI/ML"],
  "technology_focus": ["Python", "FastAPI"],
  "ranking_goals": ["Increase organic traffic"],
  "preferred_tone": "professional_insightful",
  "max_posts_per_week": 3,
  "approval_threshold_risk": "medium"
}
```

#### List Profiles
```bash
GET /admin/profiles
```

#### Update System Settings
```bash
POST /admin/settings
Content-Type: application/json

{
  "active_profile_id": "profile-doc-id",
  "is_autonomous_mode_enabled": true
}
```

#### Get Pending Approvals
```bash
GET /admin/queue/pending
```

#### Review Blog Post
```bash
POST /admin/queue/review/{blog_id}
Content-Type: application/json

{
  "action": "approve",
  "admin_email": "admin@example.com",
  "rejection_reason": null
}
```

### Agent Operations

#### Trigger Autonomous Loop
```bash
POST /agent/trigger-loop
```

## 🏗️ Architecture

```
app/
├── admin/              # Admin control panel routes
│   ├── routes.py       # Admin API endpoints
│   └── schemas.py      # Pydantic models
├── agent/              # Autonomous agent logic
│   ├── pipeline.py     # Main orchestration loop
│   ├── routes.py       # Webhook endpoints
│   ├── logic/          # Business logic
│   │   ├── drift.py    # Content drift detection
│   │   └── scoring.py  # Opportunity scoring
│   └── services/       # External API integration
│       ├── gemini_ai.py
│       ├── google_ads.py
│       ├── google_trends.py
│       └── search_serp.py
├── core/               # Core utilities
│   └── database.py     # Firestore operations
├── main.py             # FastAPI app initialization
└── __init__.py

config/
├── firebase_config.py  # Firebase initialization
└── settings.py         # Configuration management
```

## 🔑 Environment Variables

```env
# Application
APP_NAME=Autonomous SEO Operations Engine
ENVIRONMENT=development

# GCP
GCP_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# APIs
GOOGLE_ADS_DEVELOPER_TOKEN=token
GOOGLE_ADS_CUSTOMER_ID=customer-id
GOOGLE_CUSTOM_SEARCH_API_KEY=key
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=engine-id
GEMINI_API_KEY=key

# Vertex AI
VERTEX_AI_LOCATION=us-central1
```

## 📊 Firestore Collections

### `agent_profiles`
Stores dynamic SEO behavior profiles with governance rules

### `system_settings`
Global configuration (active profile, autonomous mode state)

### `blogs`
Generated blog posts with approval workflow status

### `ai_provenance_logs`
AI audit trails and model metadata

## 🔐 Security Considerations

- All API credentials are environment-based
- Firebase rules should restrict access to authenticated users only
- Sensitive data is logged to audit collection, not main application logs
- Use Cloud Scheduler with auth headers for autonomous triggers
- Implement rate limiting for production deployment

## 🚦 Deployment to Cloud Run

```bash
# Build and deploy
gcloud run deploy seo-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars GCP_PROJECT_ID=your-project-id \
  --memory 512Mi \
  --timeout 3600
```

## 📝 Logging

Logs are configured at INFO level to console. Adjust in `app/main.py`:
```python
logging.basicConfig(level=logging.DEBUG)  # For verbose logging
```

## 🐛 Troubleshooting

### Firebase Authentication Fails
- Ensure `GOOGLE_APPLICATION_CREDENTIALS` points to valid service account JSON
- Check service account has Firestore permissions

### Gemini API Errors
- Verify `GEMINI_API_KEY` is set in .env
- Ensure Gemini API is enabled in GCP project

### Google Ads API Issues
- Create `google-ads.yaml` configuration file
- Set `GOOGLE_ADS_CUSTOMER_ID` environment variable

## 📄 License

Proprietary - 1TechHub

## 🤝 Support

For issues or questions, contact the development team.
