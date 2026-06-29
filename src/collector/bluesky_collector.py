import os
from datetime import datetime
import requests
from dotenv import load_dotenv

try:
    from langdetect import detect, LangDetectException
    from langdetect import DetectorFactory
    DetectorFactory.seed = 0  # deterministic results across runs

    def _is_english(text: str) -> bool:
        if len(text.strip()) < 15:
            return False
        try:
            return detect(text) == "en"
        except LangDetectException:
            return False
except ImportError:
    print("[bluesky] langdetect not installed — language filter disabled")
    def _is_english(text: str) -> bool:
        return True

load_dotenv()

AUTH_URL   = "https://bsky.social/xrpc/com.atproto.server.createSession"
SEARCH_URL = "https://bsky.social/xrpc/app.bsky.feed.searchPosts"
SEARCH_TERMS = ["#WorldCup2026", "FIFA World Cup", "#FIFAWorldCup"]

_cached_token: str | None = None


def _get_token(force_refresh: bool = False) -> str | None:
    """Return a cached Bearer token, re-authenticating if force_refresh or no token exists."""
    global _cached_token
    if _cached_token and not force_refresh:
        return _cached_token

    handle   = os.getenv("BLUESKY_HANDLE")
    password = os.getenv("BLUESKY_APP_PASSWORD")
    if not handle or not password:
        print("[bluesky] BLUESKY_HANDLE / BLUESKY_APP_PASSWORD not set in .env")
        return None

    try:
        resp = requests.post(AUTH_URL, json={"identifier": handle, "password": password}, timeout=10)
        resp.raise_for_status()
        _cached_token = resp.json()["accessJwt"]
        action = "refreshed" if force_refresh else "authenticated"
        print(f"[bluesky] {action} as {handle}")
        return _cached_token
    except requests.RequestException as exc:
        print(f"[bluesky] auth error: {exc}")
        return None


def _authenticated_get(params: dict) -> requests.Response | None:
    """GET with Bearer auth, retrying once on 401 (expired token)."""
    global _cached_token
    for attempt in range(2):
        token = _get_token(force_refresh=(attempt > 0))
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            resp = requests.get(SEARCH_URL, params=params, headers=headers, timeout=10)
            if resp.status_code == 401 and attempt == 0:
                _cached_token = None  # clear so next attempt forces re-auth
                continue
            return resp
        except requests.RequestException as exc:
            print(f"[bluesky] request error: {exc}")
            return None
    return None


def _parse_dt(iso: str) -> datetime | None:
    """Parse a Bluesky ISO-8601 timestamp into a naive UTC datetime."""
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)  # strip tz — DB column is TIMESTAMP (no tz)
    except ValueError:
        return None


def fetch_posts(limit: int = 25) -> list[dict]:
    """Fetch World Cup posts from Bluesky. Requires BLUESKY_HANDLE + BLUESKY_APP_PASSWORD in .env.

    Returns dicts: uri, comment_text, match_title, source, created_at (original post time).
    uri lets callers deduplicate across polling cycles.
    """
    seen: set[str] = set()
    posts: list[dict] = []

    for term in SEARCH_TERMS:
        resp = _authenticated_get({"q": term, "limit": limit})
        if resp is None:
            continue
        try:
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[bluesky] fetch error for '{term}': {exc}")
            continue

        for item in resp.json().get("posts", []):
            uri    = item.get("uri", "")
            record = item.get("record", {})
            text   = record.get("text", "").strip()
            if not text or uri in seen:
                continue
            if not _is_english(text):
                continue
            seen.add(uri)
            posts.append({
                "uri":          uri,
                "comment_text": text,
                "match_title":  "World Cup 2026",
                "source":       "bluesky",
                "created_at":   _parse_dt(record.get("createdAt", "")),
            })

    return posts
