# SPECTER - GitLab Duo Agent Platform

**SPECTER** (Software Process Engine for Contextual Task Execution and Response) is an AI-powered DevOps agent built on the GitLab Duo Agent Platform for the [GitLab AI Hackathon](https://gitlab.devpost.com/).

## Architecture

SPECTER uses an **Entity-Component-System (ECS)** game-engine architecture to process GitLab events in real-time:

- **Entities**: GitLab events (Issues, MRs, Pipelines)
- **Components**: Structured data (metadata, AI analysis, action plans)
- **Systems**: Processing pipelines (translation, agent reasoning, action execution)

## Features

- Real-time GitLab webhook event processing
- AI-powered issue triage and labeling via Anthropic Claude
- Merge request code review suggestions
- Pipeline failure analysis and remediation
- Interactive dashboard for monitoring agent activity
- Built on GitLab Duo Agent Platform patterns (Tools, Triggers, Context)

## Tech Stack

- **Backend**: Python 3.11, FastAPI, Uvicorn
- **AI**: Anthropic Claude API
- **Infrastructure**: Google Cloud Run, Artifact Registry
- **CI/CD**: Cloud Build
- **Frontend**: Vanilla HTML/CSS/JS dashboard

## Quick Start

```bash
# Clone the repository
git clone https://gitlab.com/gitlab-ai-hackathon/specter-gitlab.git
cd specter-gitlab

# Set up environment
cp src/.env.example src/.env
# Edit src/.env with your API keys

# Run with Docker
docker build -t specter .
docker run -p 8080:8080 specter
```

## Live Demo

- **Cloud Run**: https://specter-agent-1074679862844.us-central1.run.app
- **Health Check**: https://specter-agent-1074679862844.us-central1.run.app/
- **Dashboard**: https://specter-agent-1074679862844.us-central1.run.app/dashboard/

## License

[MIT](LICENSE)
