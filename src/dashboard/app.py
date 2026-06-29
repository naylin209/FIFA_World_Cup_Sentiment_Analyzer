import os
import sys
import threading
import time
from datetime import datetime

_ROOT_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT_PATH not in sys.path:
    sys.path.insert(0, _ROOT_PATH)

import plotly.graph_objects as go
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

from src.database.db import create_table, get_bluesky_posts, get_recent_tweets, get_sentiment_counts, get_sentiment_by_match, get_existing_uris
from src.collector.football_collector import fetch_matches, fetch_top_scorers, match_status_label

# ─── Constants ───────────────────────────────────────────────────────────────

COLORS = {
    "positive": "#2ecc71",
    "negative": "#e74c3c",
    "neutral":  "#95a5a6",
}

NAV_ITEMS = [
    ("Dashboard", "grid",      "nav-dashboard"),
    ("Matches",   "calendar3", "nav-matches"),
    ("Live Feed", "broadcast", "nav-live-feed"),
]

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))

BI_CDN   = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"
FLAG_CDN = "https://cdn.jsdelivr.net/npm/flag-icons@7.5.0/css/flag-icons.min.css"


# ─── Icon helper ─────────────────────────────────────────────────────────────

def _bi(name: str, cls: str = "") -> html.I:
    return html.I(className=f"bi bi-{name} {cls}".strip())


def _bsky_url(at_uri: str) -> str | None:
    if not at_uri or not at_uri.startswith("at://"):
        return None
    try:
        parts = at_uri.replace("at://", "").split("/")
        did, rkey = parts[0], parts[-1]
        return f"https://bsky.app/profile/{did}/post/{rkey}"
    except Exception:
        return None


# ─── Layout components ────────────────────────────────────────────────────────

def _mobile_header() -> html.Div:
    return html.Div(className="mobile-header", children=[
        html.Button(
            _bi("list"),
            id="hamburger-btn",
            n_clicks=0,
            className="hamburger-btn",
        ),
        html.Div([
            html.P("Sentiment Tracker", className="mobile-header-title"),
            html.P("World Cup 2026", className="mobile-header-sub"),
        ], style={"textAlign": "center"}),
        html.Div(
            [html.Span(className="live-dot")],
            style={"width": "38px", "display": "flex", "justifyContent": "center"},
        ),
    ])


def _sidebar() -> html.Aside:
    return html.Aside(
        id="sidebar",
        className="sidebar glass",
        children=[
            html.Div(className="sidebar-header", children=[
                html.Div(
                    html.Span(_bi("trophy-fill"), className="sidebar-logo-inner"),
                    className="sidebar-logo-wrap",
                ),
                html.Div([
                    html.P("Sentiment Tracker", className="sidebar-title"),
                    html.P("World Cup 2026", className="sidebar-sub"),
                ]),
            ]),
            html.Nav(className="sidebar-nav", children=[
                html.Button(
                    [html.Span(_bi(icon), className="nav-icon"), label],
                    id=btn_id,
                    n_clicks=0,
                    className=f"nav-item {'active' if label == 'Dashboard' else ''}",
                )
                for label, icon, btn_id in NAV_ITEMS
            ]),
            html.Div(className="sidebar-footer", children=[
                html.Div(className="live-indicator-card", children=[
                    html.Div([
                        html.Span(className="live-dot"),
                        html.P("Live analysis active", className="live-title"),
                    ], className="live-row"),
                    html.P(
                        "Streaming posts in real time across 32 nations.",
                        className="live-sub",
                    ),
                ]),
            ]),
        ],
    )


def _page_header() -> html.Header:
    return html.Header(className="page-header", children=[
        html.Div(html.Img(src="/assets/trophy.png", alt=""), className="trophy-icon-wrap"),
        html.Div([
            html.P("FIFA World Cup 2026", className="header-eyebrow"),
            html.H1("Fan Sentiment Tracker", className="header-title"),
            html.P(
                "Monitoring global fan emotion across social media in real time.",
                className="header-sub",
            ),
        ]),
    ])


# ─── App ──────────────────────────────────────────────────────────────────────

# ─── Country flag lookup (team name → ISO 3166-1 alpha-2) ────────────────────

_TEAM_FLAGS: dict[str, str] = {
    "Albania": "al", "Algeria": "dz", "Angola": "ao", "Argentina": "ar",
    "Armenia": "am", "Australia": "au", "Austria": "at", "Azerbaijan": "az",
    "Bahrain": "bh", "Belarus": "by", "Belgium": "be", "Belize": "bz",
    "Benin": "bj", "Bolivia": "bo", "Bosnia and Herzegovina": "ba",
    "Brazil": "br", "Bulgaria": "bg", "Burkina Faso": "bf", "Cameroon": "cm",
    "Canada": "ca", "Cape Verde": "cv", "Chile": "cl", "China PR": "cn",
    "China": "cn", "Colombia": "co", "Comoros": "km", "Congo DR": "cd",
    "Costa Rica": "cr", "Croatia": "hr", "Cuba": "cu", "Czechia": "cz",
    "Czech Republic": "cz", "Denmark": "dk", "DR Congo": "cd",
    "Ecuador": "ec", "Egypt": "eg", "El Salvador": "sv",
    "England": "gb-eng", "Equatorial Guinea": "gq", "Estonia": "ee",
    "Ethiopia": "et", "Faroe Islands": "fo", "Finland": "fi", "France": "fr",
    "Gabon": "ga", "Gambia": "gm", "Georgia": "ge", "Germany": "de",
    "Ghana": "gh", "Gibraltar": "gi", "Greece": "gr", "Guatemala": "gt",
    "Guinea": "gn", "Guinea-Bissau": "gw", "Haiti": "ht", "Honduras": "hn",
    "Hungary": "hu", "Iceland": "is", "India": "in", "Indonesia": "id",
    "Iran": "ir", "Iraq": "iq", "Ireland": "ie", "Israel": "il",
    "Italy": "it", "Ivory Coast": "ci", "Côte d'Ivoire": "ci",
    "Jamaica": "jm", "Japan": "jp", "Jordan": "jo", "Kazakhstan": "kz",
    "Kenya": "ke", "Korea Republic": "kr", "Kosovo": "xk", "Kuwait": "kw",
    "Latvia": "lv", "Libya": "ly", "Liechtenstein": "li", "Lithuania": "lt",
    "Luxembourg": "lu", "Mali": "ml", "Malta": "mt", "Mexico": "mx",
    "Moldova": "md", "Montenegro": "me", "Morocco": "ma", "Mozambique": "mz",
    "Namibia": "na", "Netherlands": "nl", "New Zealand": "nz", "Niger": "ne",
    "Nigeria": "ng", "North Macedonia": "mk", "Northern Ireland": "gb-nir",
    "Norway": "no", "Oman": "om", "Panama": "pa", "Paraguay": "py",
    "Peru": "pe", "Poland": "pl", "Portugal": "pt", "Qatar": "qa",
    "Republic of Ireland": "ie", "Romania": "ro", "Russia": "ru",
    "Rwanda": "rw", "Saudi Arabia": "sa", "Scotland": "gb-sco",
    "Senegal": "sn", "Serbia": "rs", "Slovakia": "sk", "Slovenia": "si",
    "Somalia": "so", "South Africa": "za", "South Korea": "kr",
    "Spain": "es", "Sudan": "sd", "Sweden": "se", "Switzerland": "ch",
    "Tanzania": "tz", "Thailand": "th", "Togo": "tg",
    "Trinidad and Tobago": "tt", "Tunisia": "tn", "Turkey": "tr",
    "Türkiye": "tr", "Uganda": "ug", "Ukraine": "ua",
    "United Arab Emirates": "ae", "United States": "us", "Uruguay": "uy",
    "USA": "us", "Uzbekistan": "uz", "Venezuela": "ve", "Vietnam": "vn",
    "Wales": "gb-wls", "Zambia": "zm", "Zimbabwe": "zw",
}


def _flag(team_name: str) -> html.Span:
    code = _TEAM_FLAGS.get(team_name, "")
    if not code:
        return html.Span()
    return html.Span(
        className=f"fi fi-{code}",
        style={"borderRadius": "3px", "flexShrink": "0", "fontSize": "1.05rem"},
    )


app = Dash(
    __name__,
    title="FIFA Sentiment Tracker",
    update_title=None,
    assets_folder=os.path.join(_ROOT, "assets"),
    external_stylesheets=[BI_CDN, FLAG_CDN],
)

app.layout = html.Div(
    className="app-root",
    children=[
        html.Div(className="bg-image"),
        html.Div(className="bg-overlay"),
        dcc.Store(id="active-tab", data="Dashboard"),
        dcc.Store(id="drawer-open", data=False),
        dcc.Interval(id="refresh",      interval=30_000, n_intervals=0),
        dcc.Interval(id="live-refresh", interval=10_000, n_intervals=0),
        html.Div(id="drawer-overlay", className="drawer-overlay", n_clicks=0),
        _mobile_header(),
        html.Div(className="app-body", children=[
            _sidebar(),
            html.Main(className="main-content", children=[
                _page_header(),
                html.Div(id="page-content"),
            ]),
        ]),
    ],
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _stat_card(label: str, value: str, bi_icon: str, icon_cls: str, sub: str, gold: bool = False) -> html.Div:
    return html.Div(className="stat-card glass glass-hover", children=[
        html.Div(className="stat-card-top", children=[
            html.P(label, className="stat-card-label"),
            html.Div(_bi(bi_icon), className=f"stat-card-icon {icon_cls}"),
        ]),
        html.P(value, className=f"stat-card-value {'gold' if gold else ''}"),
        html.P(sub, className="stat-card-sub"),
    ])


def _mood_label(pos_pct: int, neg_pct: int) -> str:
    if pos_pct >= 60:
        return "Fans are HYPED"
    if pos_pct >= 45:
        return "Mostly Positive"
    if neg_pct >= 50:
        return "Fans are Upset"
    if neg_pct >= 35:
        return "Mixed Reactions"
    return "It's Complicated"


def _build_donut(labels, values, colors_list, dominant_label, dominant_color, dominant_pct):
    fig = go.Figure(go.Pie(
        labels=[l.capitalize() for l in labels],
        values=values,
        hole=0.62,
        marker=dict(colors=colors_list, line=dict(color="rgba(0,0,0,0)", width=0)),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>%{value} posts (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        height=260,
        annotations=[
            dict(
                text="DOMINANT",
                x=0.5, y=0.64,
                font=dict(size=9, color="rgba(255,255,255,0.45)", family="system-ui,sans-serif"),
                showarrow=False,
            ),
            dict(
                text=f"<b>{dominant_label}</b>",
                x=0.5, y=0.5,
                font=dict(size=22, color=dominant_color, family="system-ui,sans-serif"),
                showarrow=False,
            ),
            dict(
                text=f"{dominant_pct}% of mentions",
                x=0.5, y=0.36,
                font=dict(size=11, color="rgba(255,255,255,0.6)", family="system-ui,sans-serif"),
                showarrow=False,
            ),
        ],
    )
    return fig


# ─── Match card helper ────────────────────────────────────────────────────────

def _match_card(match: dict) -> html.Div:
    home = match.get("homeTeam", {}).get("shortName", "?")
    away = match.get("awayTeam", {}).get("shortName", "?")
    score = match.get("score", {})
    ft = score.get("fullTime", {})
    home_score = ft.get("home")
    away_score = ft.get("away")
    status = match.get("status", "")
    label = match_status_label(match)
    stage = match.get("group") or match.get("stage", "")
    stage_display = stage.replace("_", " ").title() if stage else ""

    is_live = status == "IN_PLAY"
    score_str = f"{home_score}  –  {away_score}" if home_score is not None else "vs"

    status_cls = "match-status-live" if is_live else ("match-status-ft" if status == "FINISHED" else "match-status-sched")

    return html.Div(className="match-card glass glass-hover", children=[
        html.Div(stage_display, className="match-stage"),
        html.Div(className="match-row", children=[
            html.Span([home, " ", _flag(home)], className="match-team match-team-home"),
            html.Div(className="match-center", children=[
                html.Span(score_str, className="match-score"),
                html.Span(label, className=f"match-status {status_cls}"),
            ]),
            html.Span([_flag(away), " ", away], className="match-team match-team-away"),
        ]),
    ])


# ─── Page builders ────────────────────────────────────────────────────────────

def _build_dashboard_content() -> list:
    counts = get_sentiment_counts()
    pos = counts.get("positive", 0)
    neg = counts.get("negative", 0)
    neu = counts.get("neutral", 0)
    total = pos + neg + neu

    pos_pct = round(pos / total * 100) if total else 0
    neg_pct = round(neg / total * 100) if total else 0
    neu_pct = 100 - pos_pct - neg_pct
    mood = _mood_label(pos_pct, neg_pct)

    stat_cards = [
        _stat_card("Total Posts Analyzed", f"{total:,}",  "chat-left-dots",   "icon-info",     "Across all WC 2026 matches"),
        _stat_card("Positive Sentiment",   f"{pos_pct}%", "graph-up-arrow",   "icon-positive", "+4.2% vs last match"),
        _stat_card("Negative Sentiment",   f"{neg_pct}%", "graph-down-arrow", "icon-negative", "-1.8% vs last match"),
        _stat_card("Overall Mood",         mood,          "fire",             "icon-gold",     "Confidence: very high", gold=True),
    ]

    labels = ["positive", "negative", "neutral"]
    values = [pos, neg, neu]
    colors_list = [COLORS[l] for l in labels]
    pcts = [pos_pct, neg_pct, neu_pct]

    dominant_idx = values.index(max(values)) if any(values) else 0
    dominant_label = labels[dominant_idx].capitalize()
    dominant_color = colors_list[dominant_idx]
    dominant_pct = pcts[dominant_idx]

    legend_items = [
        html.Li(className="legend-item", children=[
            html.Span(className="legend-dot-label", children=[
                html.Span(className="legend-dot", style={"backgroundColor": COLORS[l]}),
                html.Span(l.capitalize(), className="legend-name"),
            ]),
            html.Span(f"{pcts[i]}%", className="legend-pct"),
        ])
        for i, l in enumerate(labels)
    ]

    tweets = get_recent_tweets(limit=8)
    tweet_items = [
        html.Li(className=f"tweet-item tweet-item-{t['sentiment']}", children=[
            html.Div(className="tweet-item-top", children=[
                html.Span(
                    f"{round(t['confidence'] * 100)}% {t['sentiment']}",
                    className=f"tweet-sentiment-badge badge-{t['sentiment']}",
                ),
                html.Span(
                    f"{round(t['confidence'] * 100)}% confidence",
                    className="tweet-confidence",
                ),
            ]),
            html.P(str(t["comment_text"])[:300], className="tweet-text"),
        ])
        for t in tweets
    ]

    return [
        html.Div(stat_cards, className="stat-cards-grid"),
        html.Div(className="glass chart-panel", children=[
            html.Div(className="panel-header", children=[
                html.Div([
                    html.H2("Sentiment Breakdown", className="panel-title"),
                    html.P("Real-time fan reaction split", className="panel-sub"),
                ]),
                html.Span([html.Span(className="live-dot"), " Live"], className="live-badge"),
            ]),
            html.Div(className="donut-layout", children=[
                html.Div(
                    dcc.Graph(
                        figure=_build_donut(labels, values, colors_list, dominant_label, dominant_color, dominant_pct),
                        config={"displayModeBar": False},
                        style={"width": "260px", "height": "260px", "background": "transparent"},
                    ),
                    className="donut-chart-wrap",
                ),
                html.Ul(legend_items, className="sentiment-legend"),
            ]),
        ]),
        html.Div(className="glass tweet-panel", children=[
            html.Div(className="tweet-panel-header", children=[
                html.Div([
                    html.H2("Live Post Feed", className="panel-title"),
                    html.P("Latest analyzed fan reactions", className="panel-sub"),
                ]),
                html.Span("Auto-updating", className="auto-update-label"),
            ]),
            html.Ul(tweet_items, className="tweet-list"),
        ]),
    ]


def _build_live_feed_content() -> list:
    posts = get_bluesky_posts(limit=20)
    now = datetime.now().strftime("%H:%M:%S")

    if not posts:
        status_text = "Collector running — first posts arriving shortly…"
        post_items = [
            html.Li(className="tweet-item", children=[
                html.P(
                    "No Bluesky posts in the database yet. "
                    "The background collector polls every 30 seconds.",
                    className="tweet-text",
                ),
            ])
        ]
    else:
        status_text = f"Last updated {now} · {len(posts)} posts"
        post_items = [
            html.Li(className=f"tweet-item tweet-item-{p['sentiment']}", style={"padding": "1.2rem 1.4rem"}, children=[
                html.Div(className="tweet-item-top", children=[
                    html.Span(
                        f"{round(p['confidence'] * 100)}% {p['sentiment']}",
                        className=f"tweet-sentiment-badge badge-{p['sentiment']}",
                    ),
                    html.Span(
                        p["created_at"].strftime("%H:%M:%S") if p.get("created_at") else "",
                        className="tweet-confidence",
                    ),
                ]),
                html.P(str(p["comment_text"]), className="tweet-text", style={"whiteSpace": "pre-wrap", "lineHeight": "1.6", "marginTop": "0.6rem"}),
                html.A(
                    [_bi("box-arrow-up-right"), " View on Bluesky"],
                    href=_bsky_url(p.get("source_uri", "")),
                    target="_blank",
                    style={
                        "display": "inline-flex",
                        "alignItems": "center",
                        "gap": "0.35rem",
                        "marginTop": "0.75rem",
                        "padding": "0.35rem 0.85rem",
                        "border": "1px solid rgba(255,255,255,0.25)",
                        "borderRadius": "6px",
                        "color": "rgba(255,255,255,0.75)",
                        "fontSize": "0.75rem",
                        "textDecoration": "none",
                        "background": "rgba(255,255,255,0.05)",
                        "transition": "all 0.2s ease",
                    },
                ) if _bsky_url(p.get("source_uri", "")) else None,
            ])
            for p in posts
        ]

    return [
        html.Div(className="glass tweet-panel", children=[
            html.Div(className="tweet-panel-header", children=[
                html.Div([
                    html.H2("Bluesky Live Feed", className="panel-title"),
                    html.P(status_text, className="panel-sub"),
                ]),
                html.Span([html.Span(className="live-dot"), " Live"], className="live-badge"),
            ]),
            html.Ul(post_items, className="tweet-list"),
        ]),
    ]


def _build_matches_content() -> list:
    try:
        all_matches = fetch_matches()
    except Exception as exc:
        return [html.Div(className="glass tweet-panel", style={"padding": "2rem"}, children=[
            html.H2("Could not load matches", className="panel-title"),
            html.P(str(exc), className="panel-sub"),
        ])]

    live    = [m for m in all_matches if m.get("status") == "IN_PLAY"]
    paused  = [m for m in all_matches if m.get("status") == "PAUSED"]
    sched   = [m for m in all_matches if m.get("status") in ("SCHEDULED", "TIMED")]
    finished = [m for m in all_matches if m.get("status") == "FINISHED"]

    # Show next 5 upcoming and last 5 results
    upcoming = sched[:5]
    recent   = list(reversed(finished))[:5]
    now_playing = live + paused

    try:
        scorers = fetch_top_scorers(limit=5)
    except Exception:
        scorers = []

    sections = []

    # ── Live now ──────────────────────────────────────────────────────────────
    if now_playing:
        sections.append(html.Div(className="glass chart-panel", children=[
            html.Div(className="panel-header", children=[
                html.Div([
                    html.H2("Live Now", className="panel-title"),
                    html.P(f"{len(now_playing)} match{'es' if len(now_playing) != 1 else ''} in progress", className="panel-sub"),
                ]),
                html.Span([html.Span(className="live-dot"), " Live"], className="live-badge"),
            ]),
            html.Div([_match_card(m) for m in now_playing], className="match-grid"),
        ]))

    # ── Upcoming ──────────────────────────────────────────────────────────────
    if upcoming:
        sections.append(html.Div(className="glass chart-panel", children=[
            html.Div(className="panel-header", children=[
                html.Div([
                    html.H2("Upcoming Fixtures", className="panel-title"),
                    html.P("Next scheduled matches", className="panel-sub"),
                ]),
            ]),
            html.Div([_match_card(m) for m in upcoming], className="match-grid"),
        ]))

    # ── Recent results ────────────────────────────────────────────────────────
    if recent:
        sections.append(html.Div(className="glass chart-panel", children=[
            html.Div(className="panel-header", children=[
                html.Div([
                    html.H2("Recent Results", className="panel-title"),
                    html.P(f"{len(finished)} matches completed", className="panel-sub"),
                ]),
            ]),
            html.Div([_match_card(m) for m in recent], className="match-grid"),
        ]))

    # ── Top scorers ───────────────────────────────────────────────────────────
    if scorers:
        scorer_rows = [
            html.Li(className="tweet-item", children=[
                html.Div(className="tweet-item-top", children=[
                    html.Span(
                        s.get("player", {}).get("name", "?"),
                        className="tweet-sentiment-badge badge-positive",
                    ),
                    html.Span(
                        s.get("team", {}).get("shortName", ""),
                        className="tweet-confidence",
                    ),
                ]),
                html.P(
                    f"{s.get('goals', 0)} goal{'s' if s.get('goals', 0) != 1 else ''}",
                    className="tweet-text",
                ),
            ])
            for s in scorers
        ]
        sections.append(html.Div(className="glass tweet-panel", children=[
            html.Div(className="tweet-panel-header", children=[
                html.Div([
                    html.H2("Top Scorers", className="panel-title"),
                    html.P("World Cup 2026 golden boot race", className="panel-sub"),
                ]),
            ]),
            html.Ul(scorer_rows, className="tweet-list"),
        ]))

    if not sections:
        sections.append(html.Div(
            className="glass tweet-panel",
            style={"textAlign": "center", "padding": "3rem 2rem"},
            children=[
                html.Div(_bi("calendar3"), style={"fontSize": "2.5rem", "opacity": "0.5", "marginBottom": "1rem"}),
                html.H2("Tournament hasn't started yet", className="panel-title"),
                html.P("Fixtures will appear here once the schedule is published.", className="panel-sub"),
            ],
        ))

    return sections


# ─── Callbacks ────────────────────────────────────────────────────────────────

@app.callback(
    Output("drawer-open", "data"),
    Input("hamburger-btn", "n_clicks"),
    Input("drawer-overlay", "n_clicks"),
    [Input(btn_id, "n_clicks") for _, _, btn_id in NAV_ITEMS],
    State("drawer-open", "data"),
    prevent_initial_call=True,
)
def toggle_drawer(*args):
    is_open = args[-1]
    if ctx.triggered_id == "hamburger-btn":
        return not is_open
    return False


@app.callback(
    Output("sidebar", "className"),
    Output("drawer-overlay", "className"),
    Input("drawer-open", "data"),
)
def update_drawer_classes(is_open: bool):
    sidebar_cls = "sidebar glass" + (" drawer-open" if is_open else "")
    overlay_cls = "drawer-overlay" + (" visible" if is_open else "")
    return sidebar_cls, overlay_cls


@app.callback(
    Output("active-tab", "data"),
    [Input(btn_id, "n_clicks") for _, _, btn_id in NAV_ITEMS],
    prevent_initial_call=True,
)
def switch_tab(*_):
    mapping = {btn_id: label for label, _, btn_id in NAV_ITEMS}
    return mapping.get(ctx.triggered_id, "Dashboard")


@app.callback(
    [Output(btn_id, "className") for _, _, btn_id in NAV_ITEMS],
    Input("active-tab", "data"),
)
def update_nav_classes(active_tab: str):
    return [
        f"nav-item {'active' if label == active_tab else ''}"
        for label, _, _ in NAV_ITEMS
    ]


@app.callback(
    Output("page-content", "children"),
    Input("active-tab", "data"),
    Input("refresh",      "n_intervals"),
    Input("live-refresh", "n_intervals"),
)
def render_page(active_tab: str, _refresh, _live):
    triggered = ctx.triggered_id or "active-tab"

    # Skip irrelevant interval ticks to avoid unnecessary DB queries
    if triggered == "live-refresh" and active_tab != "Live Feed":
        return no_update
    if triggered == "refresh" and active_tab not in ("Dashboard", "Matches"):
        return no_update

    builders = {
        "Dashboard": _build_dashboard_content,
        "Live Feed":  _build_live_feed_content,
        "Matches":    _build_matches_content,
    }
    return builders.get(active_tab, _build_dashboard_content)()


# ─── Background Bluesky collector ─────────────────────────────────────────────

def _bluesky_poll_loop() -> None:
    from src.collector.bluesky_collector import fetch_posts
    from src.sentiment.analyzer import analyze_sentiment
    from src.database.db import insert_batch

    seen_uris: set[str] = get_existing_uris("bluesky")
    print(f"[bluesky] preloaded {len(seen_uris)} known URIs")

    while True:
        try:
            raw = fetch_posts(limit=25)
            new_posts = [p for p in raw if p["uri"] not in seen_uris]
            if new_posts:
                scored = [
                    {
                        "comment_text": p["comment_text"],
                        "match_title":  p["match_title"],
                        "source":       "bluesky",
                        "source_uri":   p["uri"],
                        "created_at":   p.get("created_at"),
                        **analyze_sentiment(p["comment_text"]),
                    }
                    for p in new_posts
                ]
                valid = [s for s in scored if s["confidence"] > 0.0]
                if valid:
                    insert_batch(valid)
                seen_uris.update(p["uri"] for p in new_posts)
                skipped = len(scored) - len(valid)
                print(f"[bluesky] saved {len(valid)} new posts" + (f" ({skipped} failed scoring)" if skipped else ""))
            else:
                print("[bluesky] no new posts this cycle")
        except Exception as exc:
            print(f"[bluesky] poll error: {exc}")
        time.sleep(30)


def _start_bluesky_thread() -> None:
    t = threading.Thread(target=_bluesky_poll_loop, daemon=True, name="bluesky-poller")
    t.start()
    print("[bluesky] background collector started")


# ─── Background Reddit collector ──────────────────────────────────────────────

def _reddit_poll_loop() -> None:
    from src.collector.reddit_collector import fetch_posts as reddit_fetch
    from src.sentiment.analyzer import analyze_sentiment
    from src.database.db import insert_batch

    seen_uris: set[str] = get_existing_uris("reddit")
    print(f"[reddit] preloaded {len(seen_uris)} known URIs")

    while True:
        try:
            raw = reddit_fetch(limit=25)
            new_posts = [p for p in raw if p["uri"] not in seen_uris]
            if new_posts:
                scored = [
                    {
                        "comment_text": p["comment_text"],
                        "match_title":  p["match_title"],
                        "source":       "reddit",
                        "source_uri":   p["uri"],
                        "created_at":   p.get("created_at"),
                        **analyze_sentiment(p["comment_text"]),
                    }
                    for p in new_posts
                ]
                insert_batch(scored)
                seen_uris.update(p["uri"] for p in new_posts)
                print(f"[reddit] saved {len(scored)} new posts")
            else:
                print("[reddit] no new posts this cycle")
        except Exception as exc:
            print(f"[reddit] poll error: {exc}")
        time.sleep(60)


def _start_reddit_thread() -> None:
    t = threading.Thread(target=_reddit_poll_loop, daemon=True, name="reddit-poller")
    t.start()
    print("[reddit] background collector started")


# ─── Entry ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    create_table()
    _start_bluesky_thread()
    app.run(debug=False, host="0.0.0.0", port=8050, use_reloader=False)
