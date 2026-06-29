from datetime import datetime, timezone

import requests

_HEADERS = {"User-Agent": "FIFA_Sentiment_Analyzer/1.0 (portfolio project; non-commercial)"}

_SUBREDDITS = ["worldcup", "soccer"]

_WC_KEYWORDS = {"world cup", "worldcup", "wc2026", "wc 2026", "match thread", "fifa", "2026"}


def _is_wc_related(title: str) -> bool:
    low = title.lower()
    return any(kw in low for kw in _WC_KEYWORDS)


def fetch_posts(limit: int = 25) -> list[dict]:
    results = []
    for sub in _SUBREDDITS:
        try:
            resp = requests.get(
                f"https://www.reddit.com/r/{sub}/new.json",
                headers=_HEADERS,
                params={"limit": limit},
                timeout=10,
            )
            resp.raise_for_status()
            children = resp.json().get("data", {}).get("children", [])
            for child in children:
                data = child.get("data", {})
                title = data.get("title", "")
                if sub == "soccer" and not _is_wc_related(title):
                    continue
                selftext = data.get("selftext") or ""
                if selftext in ("[deleted]", "[removed]"):
                    selftext = ""
                text = f"{title} {selftext}".strip()[:1000]
                if not text:
                    continue
                utc = data.get("created_utc")
                created_at = datetime.fromtimestamp(utc, tz=timezone.utc) if utc else None
                results.append({
                    "uri":          f"reddit_{data.get('id', '')}",
                    "comment_text": text,
                    "match_title":  "World Cup 2026",
                    "source":       "reddit",
                    "created_at":   created_at,
                })
        except Exception as exc:
            print(f"[reddit] r/{sub} error: {exc}")
    return results
