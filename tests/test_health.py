"""Tests for the /health endpoint (feed-freshness guardrail).

DB access and the collector-thread check are monkeypatched so these run
without Postgres — same constraint as CI's import smoke test.
"""

import threading

import pytest

import src.dashboard.app as dash_app


class _FakeThread:
    name = "bluesky-poller"

    @staticmethod
    def is_alive() -> bool:
        return True


@pytest.fixture
def client():
    return dash_app.app.server.test_client()


@pytest.fixture
def collector_alive(monkeypatch):
    monkeypatch.setattr(threading, "enumerate", lambda: [_FakeThread])


def test_healthy_when_feed_fresh_and_collector_alive(client, monkeypatch, collector_alive):
    monkeypatch.setattr(dash_app, "get_feed_lag_seconds", lambda source: 42.0)

    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["checks"]["db"] == "ok"
    assert body["checks"]["feed"] == {"status": "fresh", "lag_seconds": 42}
    assert body["checks"]["collector_thread"] == "alive"


def test_degraded_when_feed_stale(client, monkeypatch, collector_alive):
    stale_lag = dash_app.FEED_STALE_SECONDS + 1
    monkeypatch.setattr(dash_app, "get_feed_lag_seconds", lambda source: float(stale_lag))

    resp = client.get("/health")

    assert resp.status_code == 503
    body = resp.get_json()
    assert body["status"] == "degraded"
    assert body["checks"]["feed"]["status"] == "stale"
    assert body["checks"]["feed"]["lag_seconds"] == stale_lag


def test_degraded_when_no_rows_yet(client, monkeypatch, collector_alive):
    monkeypatch.setattr(dash_app, "get_feed_lag_seconds", lambda source: None)

    resp = client.get("/health")

    assert resp.status_code == 503
    assert resp.get_json()["checks"]["feed"]["status"] == "empty"


def test_degraded_when_db_unreachable(client, monkeypatch, collector_alive):
    def _boom(source):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(dash_app, "get_feed_lag_seconds", _boom)

    resp = client.get("/health")

    assert resp.status_code == 503
    body = resp.get_json()
    assert body["checks"]["db"] == "error"
    assert body["checks"]["feed"]["status"] == "unknown"
    # No internal error detail should leak to the response
    assert "connection refused" not in resp.get_data(as_text=True)


def test_degraded_when_collector_thread_dead(client, monkeypatch):
    monkeypatch.setattr(dash_app, "get_feed_lag_seconds", lambda source: 10.0)
    monkeypatch.setattr(threading, "enumerate", lambda: [])

    resp = client.get("/health")

    assert resp.status_code == 503
    assert resp.get_json()["checks"]["collector_thread"] == "dead"
