# ML Blogger Automation System

A production-style Python automation system that publishes technical blog posts to Blogger **every 12 hours automatically** — even when your machine is off — using GitHub Actions as the free scheduler.

Posts are generated from **your own ML/MLOps learning notes**, not generic AI content. The system acts as a writing assistant that expands your raw experience points, mistakes, and lessons into a polished technical article in your voice.

---

## How It Works

```
topics/topics.json  →  topic_loader  →  content_writer  →  html_formatter  →  blogger_client
       (your notes)       (picks next)     (expands notes)   (formats HTML)     (publishes)
```

1. GitHub Actions triggers every 12 hours (06:00 and 18:00 UTC)
2. `topic_loader` reads `topics.json` and picks the next `pending` topic
3. `content_writer` transforms your experience points, mistakes, and lessons into a structured article
4. `html_formatter` converts the article to clean Blogger-compatible HTML
5. `blogger_client` authenticates via OAuth2 and publishes to your Blogger blog
6. The topic is marked as `posted` in `topics.json` and the file is committed back to the repo
7. Logs are saved and uploaded as GitHub Actions artifacts

---

## Project Structure

```
ml-blogger-automation/
├── app/
│   ├── config.py          # All settings via environment variables
│   ├── models.py          # Pydantic data models
│   ├── topic_loader.py    # Load, pick, and update topics
│   ├── content_writer.py  # Notes → article (template or LLM)
│   ├── html_formatter.py  # Article → Blogger HTML
│   ├── blogger_client.py  # Blogger API v3 + OAuth2
│   ├── publisher.py       # Orchestrates the full pipeline
│   └── logger.py          # Logging setup
├── topics/
│   └── topics.json        # Your ML/MLOps experience notes
├── logs/                  # Auto-created at runtime
├── .github/
│   └── workflows/
│       └── blogger-auto-post.yml
├── main.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## Local Setup

### 1. Clone and install

```bash
git clone https://github.com/your-username/ml-blogger-automation.git
cd ml-blogger-automation
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Fill in the credentials (see next section).

### 3. Test locally in dry-run mode

```bash
python main.py --dry-run
```

This runs the full pipeline without making any Blogger API calls. Safe to run anytime.

---

## Setting Up Blogger API Credentials

You need OAuth2 credentials to publish on your behalf.

### Step 1 — Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g., `ml-blogger-automation`)
3. Enable the **Blogger API v3** from APIs & Services → Library

### Step 2 — Create OAuth2 credentials

1. Go to APIs & Services → Credentials
2. Create credentials → **OAuth 2.0 Client ID**
3. Application type: **Desktop app**
4. Download the JSON — you need `client_id` and `client_secret`

### Step 3 — Get your Blogger Blog ID

1. Go to [blogger.com](https://www.blogger.com)
2. Your blog's URL looks like: `https://www.blogger.com/blog/posts/1234567890123456789`
3. The number is your `BLOGGER_BLOG_ID`

### Step 4 — Get a refresh token

Run this one-time script to authorize and get your refresh token:

```python
# get_token.py — run this once locally
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/blogger"]
flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
creds = flow.run_local_server(port=0)
print("Refresh token:", creds.refresh_token)
```

Save the refresh token in your `.env` as `GOOGLE_REFRESH_TOKEN`.

---

## Running Locally

```bash
# Full pipeline (uses .env settings)
python main.py

# Force dry-run from CLI
python main.py --dry-run

# Verify credentials
python main.py --verify

# Show topic queue stats
python main.py --stats
```

---

## Deploying with GitHub Actions (Free, Runs Every 12 Hours)

### Step 1 — Push to GitHub

```bash
git add .
git commit -m "initial setup"
git push origin main
```

### Step 2 — Add GitHub Secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret.

Add these secrets:

| Secret Name           | Value                          |
|-----------------------|--------------------------------|
| `BLOGGER_BLOG_ID`     | Your Blogger blog ID           |
| `GOOGLE_CLIENT_ID`    | OAuth2 client ID               |
| `GOOGLE_CLIENT_SECRET`| OAuth2 client secret           |
| `GOOGLE_REFRESH_TOKEN`| Refresh token from step above  |
| `AUTHOR_NAME`         | Your name (e.g., `Mukesh`)     |

Optional:

| Secret Name      | Value                                       |
|------------------|---------------------------------------------|
| `USE_LLM`        | `true` to enable Groq content enrichment    |
| `GROQ_API_KEY`   | Your Groq API key (free at console.groq.com)|
| `GROQ_MODEL`     | Model name, default: `llama3-8b-8192`       |

### Step 3 — Trigger manually to test

Go to Actions → ML Blogger Auto Post → Run workflow → set `dry_run = true` for the first test.

### Step 4 — Done

The workflow runs at 06:00 and 18:00 UTC every day automatically.
After each successful post, the updated `topics.json` is committed back to the repo.

---

## Adding Your Own Topics

Edit `topics/topics.json`. Each entry follows this schema:

```json
{
  "topic_id": 11,
  "title_seed": "What I learned about X",
  "category": "MLOps",
  "tags": ["tool1", "tool2"],
  "difficulty": "Intermediate",
  "experience_points": [
    "First thing I noticed",
    "Second key learning"
  ],
  "mistakes": [
    "First mistake I made",
    "Second mistake"
  ],
  "lessons": [
    "What I'd do differently"
  ],
  "optional_code_snippet_idea": "brief description of code example",
  "status": "pending",
  "posted_at": null,
  "blogger_post_id": null,
  "blogger_post_url": null
}
```

Set `"status": "pending"` and it will be picked up in the next run.

---

## Content Generation Modes

### Template mode (fallback, no API needed)

The built-in writer uses your notes as-is and expands them into structured prose. Works offline, works in CI, free forever. Activates automatically if Groq is unavailable.

### Groq LLM mode (default, recommended)

Uses **Groq's free API** with `llama3-8b-8192` — ultra-fast inference, no cost for reasonable usage.
Set `USE_LLM=true` and provide `GROQ_API_KEY`. Expands your notes into polished prose while preserving your voice.
Falls back to template mode automatically if the API call fails.

Get your free Groq API key at [console.groq.com](https://console.groq.com).

---

## Logs

- `logs/automation.log` — full execution log with rotation
- `logs/post_history.json` — structured history of every publish attempt

Both are uploaded as GitHub Actions artifacts (retained 14 days).

---

## Phase 2 Improvements

| Feature                  | Description                                                  |
|--------------------------|--------------------------------------------------------------|
| FastAPI admin panel      | REST API to add topics, check status, trigger runs manually  |
| PostgreSQL storage       | Replace JSON file with a proper database for topic tracking  |
| Celery + Redis queue     | Async pipeline with retries and concurrency                  |
| Prometheus metrics       | Track post success/failure rates, API latency                |
| Grafana dashboard        | Visualize post history, topic funnel, error rates            |
| Multi-platform publish   | Dev.to, Hashnode, Medium in addition to Blogger              |
| Analytics integration    | Pull Blogger view counts back and log per-post performance   |
| Thumbnail generation     | Auto-generate post cover images using PIL or DALL-E          |

---

## Built With

- Python 3.11
- Pydantic v2
- python-dotenv
- requests
- GitHub Actions (free CI scheduler)

---

*This project is part of Mukesh's ML Engineer / MLOps portfolio.*
