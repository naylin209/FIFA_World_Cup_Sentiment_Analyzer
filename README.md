# FIFA World Cup 2026 Sentiment Tracker

> Real-time fan sentiment analysis on live World Cup social data — deployed on AWS.

**Live demo:** [fifasentiment.me](https://fifasentiment.me)

---

## What It Does

Every 30 seconds, the app pulls live posts from Bluesky searching for World Cup hashtags, classifies each one as positive, negative, or neutral using Cardiff NLP's multilingual XLM-RoBERTa model, stores the results in PostgreSQL, and refreshes the dashboard automatically.

No manual data collection. No manual deploys. Just push to GitHub and everything updates.

---

## Dashboard

| View | Description |
|------|-------------|
| Dashboard | Sentiment pie chart, overall fan mood indicator, and live analytics |
| Matches | Current FIFA World Cup 2026 fixtures with country flags and match status |
| Live Feed | Real-time Bluesky posts with per-post sentiment labels |

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Sentiment model | `cardiffnlp/twitter-xlm-roberta-base-sentiment` (HuggingFace Transformers) |
| Dashboard | Plotly Dash |
| Database | PostgreSQL |
| Data source | Bluesky AT Protocol API |
| Match data | football-data.org API v4 |
| Infrastructure | AWS EC2 + Nginx reverse proxy + systemd |
| CI/CD | GitHub Actions |

---

## Architecture

```
Bluesky API
    |
    v
bluesky_collector.py  -->  analyzer.py (XLM-RoBERTa)
                                |
                                v
                          PostgreSQL DB
                                |
                                v
                          Plotly Dash (app.py)
                                |
                                v
                    Nginx reverse proxy (port 80/443)
                                |
                                v
                          fifasentiment.me
```

**CI/CD flow:**

```
git push main
    |
    v
GitHub Actions
    |
    v
SSH into EC2  -->  git pull origin main  -->  sudo systemctl restart fifa-sentiment
```

---

## Local Setup

### Prerequisites

- Python 3.11+
- PostgreSQL running locally
- A [Bluesky](https://bsky.app) account (for live data collection)
- A [football-data.org](https://www.football-data.org) free API key (for match fixtures)

### Installation

```bash
git clone https://github.com/naylin209/FIFA_World_Cup_Sentiment_Analyzer.git
cd FIFA_World_Cup_Sentiment_Analyzer

python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\activate

pip install -r requirements.txt
```

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fifa_sentiment
DB_USER=postgres
DB_PASSWORD=your_password

BLUESKY_HANDLE=yourhandle.bsky.social
BLUESKY_APP_PASSWORD=your_app_password

FOOTBALL_API_KEY=your_football_data_api_key
```

### Database

```bash
# Create the database
psql -U postgres -c "CREATE DATABASE fifa_sentiment;"

# Tables are created automatically on first run
```

### Run

```bash
python src/dashboard/app.py
```

Open [http://localhost:8050](http://localhost:8050)

The sentiment model (~500MB) downloads automatically on first run and is cached locally after that.

---

## Project Structure

```
.
├── src/
│   ├── collector/
│   │   ├── bluesky_collector.py   # Pulls live posts from Bluesky API
│   │   ├── football_collector.py  # Fetches live match data and fixtures
│   │   └── kaggle_loader.py       # Loads historical FIFA 2022 tweet dataset
│   ├── sentiment/
│   │   └── analyzer.py            # HuggingFace XLM-RoBERTa inference
│   ├── database/
│   │   └── db.py                  # PostgreSQL connection and queries
│   └── dashboard/
│       └── app.py                 # Plotly Dash app with live refresh
├── .github/
│   └── workflows/
│       └── deploy.yml             # GitHub Actions CI/CD to EC2
├── run_pipeline.py                # Manual pipeline runner
├── requirements.txt
└── .env.example
```

---

## CI/CD

On every push to `main`, GitHub Actions:

1. SSHs into the EC2 instance using a stored private key
2. Pulls the latest code
3. Restarts the systemd service

The EC2 instance runs the Dash app as a systemd service behind an Nginx reverse proxy with HTTPS via Let's Encrypt.

---

## Built By

**Nay Lin Aung** — CS grad from RIT, open to roles in data engineering, solutions engineering, and software engineering.

[LinkedIn](https://linkedin.com/in/naylin-aung) | [GitHub](https://github.com/naylin209)
