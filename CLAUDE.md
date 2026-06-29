# FIFA World Cup 2026 Sentiment Tracker — Project Context

Built by Nay Lin Aung. Portfolio project targeting Solutions Engineer / Forward Deployed Engineer roles.
The World Cup is happening right now (June/July 2026), making this timely and demo-able.

---

## What This Project Does

Pulls fan comments/tweets about FIFA World Cup matches, runs them through a Hugging Face NLP model
to classify sentiment (positive / negative / neutral), stores results in PostgreSQL, and displays
everything on a live Plotly Dash dashboard. Eventually deployed on AWS EC2 with GitHub Actions CI/CD.

---

## Tech Stack

| Layer | Tool | Notes |
|-------|------|-------|
| Data (current) | Kaggle FIFA 2022 tweet dataset | 22,524 tweets, stored in data/kaggle_fifa_2022/ |
| Data (future) | Reddit PRAW API | r/soccer post-match threads, blocked pending account age |
| Sentiment model | cardiffnlp/twitter-roberta-base-sentiment-latest | Hugging Face, cached at C:\Users\nayli\.cache\huggingface |
| Dashboard | Plotly Dash | Pure Python, no JavaScript needed |
| Database | PostgreSQL 18 | Port 5432, db name: fifa_sentiment |
| Backend (planned) | FastAPI | Optional API layer |
| Deployment (planned) | AWS EC2 t2.micro | Free tier |
| CI/CD (planned) | GitHub Actions | Auto-deploy on push to main |

---

## Project Structure

```
fifa-sentiment-tracker/
├── CLAUDE.md                          <- you are here
├── run_pipeline.py                    <- entry point: runs full data -> score -> save pipeline
├── requirements.txt                   <- pinned dependencies
├── .env                               <- secrets (never commit), copied from .env.example
├── .env.example                       <- template for .env
├── .gitignore
├── src/
│   ├── collector/
│   │   ├── kaggle_loader.py           <- loads kaggle_fifa_2022.csv into a DataFrame
│   │   └── reddit_collector.py        <- (not built yet) PRAW scraper for r/soccer
│   ├── sentiment/
│   │   └── analyzer.py               <- Hugging Face sentiment pipeline
│   ├── database/
│   │   └── db.py                     <- PostgreSQL connection and query functions
│   ├── dashboard/
│   │   └── app.py                    <- (not built yet) Plotly Dash dashboard
│   └── api/
│       └── main.py                   <- (not built yet) FastAPI backend
├── tests/
│   └── test_sentiment.py             <- (not built yet)
└── data/
    └── kaggle_fifa_2022/
        └── kaggle_fifa_2022.csv      <- Kaggle dataset, gitignored
```

---

## What Has Been Built (Days 1-3 Complete)

### Day 1 — Environment + Data Loading
- Created full project folder structure
- Python venv at `venv/`, all packages installed
- `src/collector/kaggle_loader.py` loads the CSV into pandas
- Dataset: 22,524 tweets, text column is called `Tweet` (capital T)
- The dataset has a `Sentiment` column (pre-labeled) but we generate our own with the NLP model

### Day 2 — Hugging Face Sentiment Model
- `src/sentiment/analyzer.py` uses `cardiffnlp/twitter-roberta-base-sentiment-latest`
- Model auto-downloaded (~500MB) on first run, now cached locally — no account needed
- `analyze_sentiment(text)` returns `{"sentiment": "positive/negative/neutral", "confidence": 0.95}`
- `analyze_dataframe(df, text_column)` adds `predicted_sentiment` and `confidence` columns
- The "LOAD REPORT / UNEXPECTED keys" warning on startup is harmless — ignore it

### Day 3 — PostgreSQL Database
- PostgreSQL 18 at `C:\Program Files\PostgreSQL\18\`, port 5432, service name `postgresql-18`
- Database: `fifa_sentiment`, table: `match_sentiments`
- Table columns: id, comment_text, sentiment, confidence, match_title, source, created_at
- `src/database/db.py`: get_connection(), create_table(), insert_batch(), get_sentiment_counts(), get_sentiment_by_match()
- `run_pipeline.py` ties it all together: load 500 rows -> score -> save to DB
- 500 rows already in the database from the first run

---

## What Is Next

### Day 4 — Plotly Dash Dashboard
- Build `src/dashboard/app.py`
- Charts: sentiment pie, sentiment bar, per-match breakdown
- Auto-refreshes every 30 seconds from the live database
- Run with: `python src/dashboard/app.py` -> http://localhost:8050

### Day 5 — AWS EC2 Deployment
### Day 6 — GitHub Actions CI/CD
### Bonus — Reddit live data, Docker

---

## Environment Variables (.env)

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fifa_sentiment
DB_USER=postgres
DB_PASSWORD=<postgres password>
REDDIT_CLIENT_ID=<placeholder>
REDDIT_CLIENT_SECRET=<placeholder>
REDDIT_USER_AGENT=fifa_sentiment/1.0
```

---

## Key Commands

```powershell
# Activate venv
.\venv\Scripts\activate

# Run the full pipeline (load -> score -> save)
python run_pipeline.py

# Run the dashboard (Day 4+)
python src/dashboard/app.py

# Connect to database
psql -U postgres -d fifa_sentiment
# Inside psql: run \encoding UTF8 first, then query normally

# If PostgreSQL service stops (admin PowerShell required)
Start-Service postgresql-18
```

---

## Known Gotchas

- PostgreSQL port is 5432 (was misconfigured as 5433 on install, fixed in postgresql.conf)
- Run `\encoding UTF8` inside psql before querying comment_text — tweets contain emojis
- If psycopg2 throws "Connection refused", run `Start-Service postgresql-18` in admin PowerShell
- Reddit API blocked for new accounts — Kaggle dataset is the fallback (fine for portfolio)
