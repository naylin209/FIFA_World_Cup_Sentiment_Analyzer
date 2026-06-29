import os
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

_BASE = "https://api.football-data.org/v4"
_CACHE_TTL = 60  # seconds

_cache: dict[str, tuple[float, object]] = {}


def _headers() -> dict:
    return {"X-Auth-Token": os.getenv("FOOTBALL_API_KEY", "")}


def _get(url: str, params: dict | None = None) -> dict:
    key = url + str(params)
    ts, data = _cache.get(key, (0, None))
    if data is not None and time.time() - ts < _CACHE_TTL:
        return data
    resp = requests.get(url, headers=_headers(), params=params or {}, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    _cache[key] = (time.time(), result)
    return result


def fetch_matches(status: str | None = None) -> list[dict]:
    params = {"status": status} if status else {}
    return _get(f"{_BASE}/competitions/WC/matches", params).get("matches", [])


def fetch_standings() -> list[dict]:
    return _get(f"{_BASE}/competitions/WC/standings").get("standings", [])


def fetch_top_scorers(limit: int = 10) -> list[dict]:
    return _get(f"{_BASE}/competitions/WC/scorers", {"limit": limit}).get("scorers", [])


def parse_kickoff(utc_str: str) -> str:
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        return dt.strftime("%d %b  %H:%M UTC")
    except Exception:
        return utc_str


def match_status_label(match: dict) -> str:
    status = match.get("status", "")
    minute = match.get("minute")
    if status == "IN_PLAY":
        return f"LIVE {minute}'" if minute else "LIVE"
    if status == "PAUSED":
        return "HT"
    if status == "FINISHED":
        return "FT"
    if status in ("SCHEDULED", "TIMED"):
        return parse_kickoff(match.get("utcDate", ""))
    return status.replace("_", " ").title()
