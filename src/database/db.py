import os
import threading
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

_pool: pool.ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()


def _get_pool() -> pool.ThreadedConnectionPool:
    global _pool
    if _pool is not None:
        return _pool
    with _pool_lock:
        if _pool is None:
            _pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "5432")),
                dbname=os.getenv("DB_NAME", "fifa_sentiment"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD"),
            )
    return _pool


@contextmanager
def _db():
    p = _get_pool()
    conn = p.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


def create_table() -> None:
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS match_sentiments (
                    id SERIAL PRIMARY KEY,
                    comment_text TEXT NOT NULL,
                    sentiment VARCHAR(20) NOT NULL,
                    confidence FLOAT NOT NULL,
                    match_title VARCHAR(255),
                    source VARCHAR(50) DEFAULT 'kaggle',
                    source_uri VARCHAR(512),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute(
                "ALTER TABLE match_sentiments ADD COLUMN IF NOT EXISTS source_uri VARCHAR(512)"
            )
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_source_uri
                ON match_sentiments(source_uri)
                WHERE source_uri IS NOT NULL
            """)
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_sentiment ON match_sentiments(sentiment)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_match_title ON match_sentiments(match_title)"
            )
    print("Table ready.")


def insert_batch(rows: list[dict]) -> None:
    if not rows:
        return
    with _db() as conn:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """INSERT INTO match_sentiments
                   (comment_text, sentiment, confidence, match_title, source, source_uri, created_at)
                   VALUES %s
                   ON CONFLICT DO NOTHING""",
                [
                    (
                        r["comment_text"],
                        r["sentiment"],
                        r["confidence"],
                        r.get("match_title"),
                        r.get("source", "kaggle"),
                        r.get("source_uri"),
                        r.get("created_at"),
                    )
                    for r in rows
                ],
                template="(%s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()))",
            )


def get_existing_uris(source: str) -> set[str]:
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT source_uri FROM match_sentiments WHERE source = %s AND source_uri IS NOT NULL",
                (source,),
            )
            return {row[0] for row in cur.fetchall()}


def get_sentiment_counts() -> dict:
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT sentiment, COUNT(*) FROM match_sentiments GROUP BY sentiment")
            return {row[0]: row[1] for row in cur.fetchall()}


def get_recent_tweets(limit: int = 8) -> list[dict]:
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT comment_text, sentiment, confidence, created_at
                FROM match_sentiments
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            return [
                {"comment_text": r[0], "sentiment": r[1], "confidence": r[2], "created_at": r[3]}
                for r in cur.fetchall()
            ]


def get_bluesky_posts(limit: int = 20) -> list[dict]:
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT comment_text, sentiment, confidence, created_at
                FROM match_sentiments
                WHERE source = 'bluesky'
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            return [
                {"comment_text": r[0], "sentiment": r[1], "confidence": r[2], "created_at": r[3]}
                for r in cur.fetchall()
            ]


def get_sentiment_by_match() -> list:
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT match_title, sentiment, COUNT(*) as count
                FROM match_sentiments
                GROUP BY match_title, sentiment
                ORDER BY match_title
            """)
            return cur.fetchall()
