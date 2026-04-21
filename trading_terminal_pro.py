#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║       TRADING TERMINAL PRO  ·  v5.0  ·  HFT ENGINE & DELTA ONE MODULE         ║
║       Architecture : Salle des Marchés  ·  Bloomberg Terminal Style            ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║  ⚠️  AVERTISSEMENT LÉGAL OBLIGATOIRE :                                         ║
║  Cet outil est EXCLUSIVEMENT éducatif et pédagogique. Toutes les données       ║
║  financières sont fournies à titre informatif via yfinance (données publiques). ║
║  Aucun ordre réel n'est jamais exécuté. Le module "Shadow Ledger" reproduit    ║
║  la mécanique de la fraude Kerviel (SocGen, 2008, ~4.9 Md€) à des fins       ║
║  d'enseignement du contrôle interne et de la gestion des risques financiers.   ║
║  Son utilisation à des fins réelles est illégale. Ce simulateur ne constitue  ║
║  en aucun cas un conseil financier ou d'investissement.                        ║
╚══════════════════════════════════════════════════════════════════════════════════╝

Usage:
    pip install streamlit yfinance pandas numpy plotly
    streamlit run trading_terminal_pro.py
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import io
import random
import math

# ══════════════════════════════════════════════════════════════════════════════
# § 1 · PAGE CONFIGURATION (must be first Streamlit call)
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="⚡ TRADING TERMINAL PRO",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
# § 2 · CONSTANTS & BUSINESS CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════
INITIAL_CAPITAL  = 10_000_000.0    # $10M starting capital (typical prop desk)
COMMISSION_RATE  = 0.001           # 10 bps — standard institutional commission
MAX_SLIPPAGE_BPS = 3               # 3 bps max market impact
VAR_LIMIT_PCT    = 0.02            # 2% VaR limit as % of AUM (regulatory)
VAR_CONFIDENCE   = 0.99            # 99% — Basel III standard
VAR_HORIZON_DAYS = 1               # 1-day VaR
HURDLE_RATE      = 0.05            # 5% return on capital before bonus kicks in
BASE_SALARY      = 250_000         # $250k base (VP-level, bulge bracket)
BONUS_SHARE_PCT  = 0.40            # 40% of excess P&L → bonus pool
DEFERRED_PCT     = 0.60            # 60% of bonus deferred (3-year, clawback)
CLAWBACK_YEARS   = 3               # Deferred vesting period

WATCHLIST_TICKERS = [
    "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "GS", "JPM", "AMZN",
    "BTC-USD", "ETH-USD", "GC=F", "ES=F", "NQ=F", "^VIX",
]

DELTA_ONE_PAIRS = {
    "SPY ↔ Top-5 Holdings (S&P 500 Arb)": {
        "index":      "SPY",
        "components": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"],
        "weights":    [0.0700, 0.0650, 0.0600, 0.0550, 0.0500],
        "description": "Arbitrage ETF vs composantes pondérées — typique Delta One desk",
    },
    "QQQ ↔ Tech Mega-Cap (Nasdaq Arb)": {
        "index":      "QQQ",
        "components": ["AAPL", "MSFT", "NVDA", "META", "AMZN"],
        "weights":    [0.0900, 0.0800, 0.0700, 0.0600, 0.0500],
        "description": "Stratégie Kerviel-style : futures Nasdaq vs basket actions",
    },
}

# Simulated news feed (in production: plug Bloomberg API / Reuters Eikon)
NEWS_FEED = [
    ("🔴", "BREAKING", "Fed signals surprise 50bps hike — Russell 2000 -3.2%", "14:32:01"),
    ("🟡", "ALERT",    "Goldman upgrades NVDA → Strong Buy, PT $1,050", "14:28:45"),
    ("🔴", "FLASH",    "Eurozone CPI 4.2% YoY — EUR/USD +80 pips, Bund -45bps", "14:15:22"),
    ("🟢", "UPDATE",   "SPY gamma squeeze: $2.3B 0DTE call flow — market makers delta-hedging", "14:10:05"),
    ("🔴", "BREAKING", "China crackdown 2.0 — Hang Seng -4.7%, Alibaba halted", "13:55:33"),
    ("🟡", "ALERT",    "US10Y breaches 4.5% resistance — risk-off rotation underway", "13:42:17"),
    ("🟢", "UPDATE",   "AAPL $90B buyback approved — share count -5% annualized", "13:30:00"),
    ("🔴", "FLASH",    "OPEC+ surprise output cut — Brent +3.8%, airline stocks -4%", "13:15:44"),
    ("🟡", "ALERT",    "VIX spikes 25.3 — hedging demand surge, put/call ratio 1.4", "12:58:02"),
    ("🟢", "UPDATE",   "MSFT beats EPS +$0.18 vs consensus, Azure +28% YoY", "12:45:30"),
    ("🔴", "FLASH",    "SocGen rogue trader detected: $6.9B exposure on Eurostoxx futures", "12:30:11"),
    ("🟡", "ALERT",    "JPMorgan CIO whale position unwinding — IG CDX spreads +40bps", "12:15:07"),
]


# ══════════════════════════════════════════════════════════════════════════════
# § 3 · CSS INJECTION — BLOOMBERG / HFT TERMINAL THEME
# ══════════════════════════════════════════════════════════════════════════════
def inject_css() -> None:
    """Inject full custom CSS for Bloomberg-terminal aesthetic."""
    st.markdown(r"""
<style>
/* ── Font Import ───────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Barlow+Condensed:wght@300;400;600;700&display=swap');

/* ── CSS Variables ─────────────────────────────────────────────────────── */
:root {
  --bg:        #060a0f;
  --bg2:       #0a0e14;
  --bg3:       #0d1520;
  --border:    #1a2535;
  --border2:   #243040;
  --green:     #00ff88;
  --green-dim: #00cc6a;
  --red:       #ff3355;
  --red-dim:   #cc2244;
  --blue:      #00d4ff;
  --gold:      #ffd700;
  --purple:    #aa55cc;
  --text-1:    #dde3ec;
  --text-2:    #8899aa;
  --text-3:    #3a5f7a;
  --mono:      'JetBrains Mono', 'Consolas', monospace;
  --sans:      'Barlow Condensed', sans-serif;
}

/* ── Global Reset ──────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }
.stApp, .main { background: var(--bg) !important; color: var(--text-1) !important; }
body { font-family: var(--mono) !important; }
#MainMenu, footer, header { visibility: hidden !important; }
.block-container { padding: 0.2rem 0.6rem 2rem !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { background: var(--bg) !important; border-right: 1px solid var(--border) !important; }
section[data-testid="stSidebar"] * { color: var(--text-2) !important; font-family: var(--mono) !important; font-size: 0.75rem !important; }

/* ── Terminal Top Bar ──────────────────────────────────────────────────── */
.t-bar {
    display: flex; justify-content: space-between; align-items: center;
    background: linear-gradient(90deg, #08142a 0%, #0d1f3c 40%, #0a1a32 70%, #08142a 100%);
    border-bottom: 1px solid #00ff8833;
    border-top: 2px solid #00ff8866;
    padding: 5px 14px;
    margin-bottom: 5px;
    border-radius: 0 0 4px 4px;
}
.t-title {
    color: var(--green);
    font-size: 0.88rem;
    font-weight: 700;
    letter-spacing: 4px;
    text-shadow: 0 0 15px #00ff8877, 0 0 30px #00ff8833;
    font-family: var(--sans);
}
.t-subtitle { color: var(--text-3); font-size: 0.58rem; letter-spacing: 2px; margin-top: 1px; }
.t-clock { color: var(--blue); font-size: 1.05rem; font-weight: 700; letter-spacing: 3px; text-align: right; }
.t-date { color: var(--text-3); font-size: 0.58rem; letter-spacing: 1px; text-align: right; }
.t-acct { color: var(--text-3); font-size: 0.62rem; letter-spacing: 1px; text-align: center; }

/* ── Panel System ──────────────────────────────────────────────────────── */
.panel {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 3px;
    padding: 6px 7px;
    margin-bottom: 5px;
    position: relative;
}
.ph {
    font-size: 0.56rem; font-weight: 700; color: var(--text-3); letter-spacing: 2.5px;
    text-transform: uppercase; border-bottom: 1px solid var(--border);
    padding-bottom: 3px; margin-bottom: 5px; font-family: var(--sans);
}
.ph::before { content: ''; display: inline-block; width: 4px; height: 4px;
    background: var(--green); border-radius: 50%; margin-right: 5px; margin-bottom: 1px; }

/* ── Watchlist ─────────────────────────────────────────────────────────── */
.wl-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 3px 5px; border-radius: 2px; border-left: 2px solid transparent;
    margin: 1px 0; cursor: default; transition: all 0.12s;
}
.wl-row:hover { background: var(--bg3); border-left-color: #00ff8866; }
.wl-sym { color: var(--text-1); font-size: 0.7rem; font-weight: 600; letter-spacing: 0.5px; }
.wl-px  { font-size: 0.76rem; font-weight: 700; font-family: var(--mono); }
.wl-up  { color: var(--green); font-size: 0.62rem; }
.wl-dn  { color: var(--red);   font-size: 0.62rem; }
.wl-cat { color: var(--text-3); font-size: 0.55rem; letter-spacing: 2px;
    margin: 6px 0 2px 5px; font-family: var(--sans); }

/* ── News Feed ─────────────────────────────────────────────────────────── */
.ni { padding: 3px 4px; border-left: 2px solid var(--border); margin: 2px 0; border-radius: 0 2px 2px 0; }
.ni:hover { border-left-color: var(--blue); background: #090d18; }
.nb-r { color: var(--red);   font-weight: 700; font-size: 0.58rem; }
.nb-y { color: var(--gold);  font-weight: 700; font-size: 0.58rem; }
.nb-g { color: var(--green); font-weight: 700; font-size: 0.58rem; }
.nt   { color: var(--text-3); font-size: 0.56rem; margin-left: 3px; }
.nx   { color: #aab4be; font-size: 0.62rem; line-height: 1.35; }

/* ── Order Book ────────────────────────────────────────────────────────── */
.ob-hdr {
    display: flex; justify-content: space-between; padding: 2px 4px;
    color: var(--text-3); font-size: 0.55rem; letter-spacing: 1px; border-bottom: 1px solid var(--border);
}
.ob-row { display: flex; justify-content: space-between; align-items: center; padding: 2px 4px; font-size: 0.68rem; }
.ob-a   { background: #150910; }
.ob-b   { background: #091510; }
.ob-a:hover { background: #1f0d18; }
.ob-b:hover { background: #0d1f10; }
.pr-a   { color: var(--red);   font-weight: 600; font-family: var(--mono); }
.pr-b   { color: var(--green); font-weight: 600; font-family: var(--mono); }
.pr-sz  { color: var(--text-3); font-size: 0.64rem; }
.ob-mid {
    text-align: center; padding: 3px 0; font-size: 0.82rem; font-weight: 700;
    color: var(--text-1); border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
    background: var(--bg3); letter-spacing: 1px; font-family: var(--mono);
}
.ob-bar-a { height: 3px; background: #ff335533; border-radius: 1px; margin: 0 3px; }
.ob-bar-b { height: 3px; background: #00ff8833; border-radius: 1px; margin: 0 3px; }

/* ── Metrics Override ──────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--bg2) !important; border: 1px solid var(--border) !important;
    border-radius: 3px !important; padding: 5px 9px !important;
}
[data-testid="stMetricLabel"] p {
    font-size: 0.55rem !important; color: var(--text-3) !important;
    letter-spacing: 1.5px !important; text-transform: uppercase !important;
    font-family: var(--sans) !important; font-weight: 600 !important;
}
[data-testid="stMetricValue"] {
    font-size: 0.95rem !important; font-family: var(--mono) !important; font-weight: 700 !important;
}
[data-testid="stMetricDelta"] { font-size: 0.68rem !important; font-family: var(--mono) !important; }

/* ── Buttons ───────────────────────────────────────────────────────────── */
.stButton > button {
    background: var(--bg3) !important; border: 1px solid var(--border) !important;
    color: var(--text-2) !important; font-family: var(--mono) !important;
    font-size: 0.7rem !important; border-radius: 2px !important;
    letter-spacing: 0.5px !important; padding: 4px 10px !important; transition: all 0.12s;
}
.stButton > button:hover {
    border-color: #00ff8877 !important; color: var(--green) !important;
    background: #051008 !important; box-shadow: 0 0 8px #00ff8822 !important;
}

/* ── Inputs ────────────────────────────────────────────────────────────── */
.stSelectbox > div > div, .stNumberInput > div > div > input {
    background: var(--bg3) !important; border: 1px solid var(--border) !important;
    color: var(--text-1) !important; font-family: var(--mono) !important;
    font-size: 0.73rem !important; border-radius: 2px !important;
}
.stSelectbox > div > div:hover { border-color: var(--border2) !important; }
label { color: var(--text-3) !important; font-size: 0.58rem !important;
    letter-spacing: 1.5px !important; text-transform: uppercase !important; font-family: var(--sans) !important; }

/* ── Tabs ──────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--bg) !important; border-bottom: 1px solid var(--border) !important; gap: 2px !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important; color: var(--text-3) !important;
    font-family: var(--sans) !important; font-size: 0.65rem !important;
    letter-spacing: 1.5px !important; padding: 5px 14px !important; font-weight: 600 !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: var(--green) !important; border-bottom: 2px solid var(--green) !important;
    background: transparent !important;
}

/* ── DataFrames ────────────────────────────────────────────────────────── */
.stDataFrame { font-family: var(--mono) !important; }
[data-testid="stDataFrameResizable"] { border: 1px solid var(--border) !important; border-radius: 3px !important; }

/* ── Positions Table ───────────────────────────────────────────────────── */
.pos-table { width: 100%; border-collapse: collapse; font-size: 0.7rem; font-family: var(--mono); }
.pos-table th {
    color: var(--text-3); text-align: right; padding: 3px 6px;
    border-bottom: 1px solid var(--border); font-size: 0.58rem;
    letter-spacing: 1.5px; font-family: var(--sans); font-weight: 600;
}
.pos-table th:first-child { text-align: left; }
.pos-table td {
    padding: 3px 6px; border-bottom: 1px solid #0c1118;
    text-align: right; color: var(--text-2);
}
.pos-table td:first-child { text-align: left; color: var(--text-1); font-weight: 600; }
.pos-table tr:hover td { background: var(--bg3); }

/* ── Trade Log ─────────────────────────────────────────────────────────── */
.tl-entry {
    font-size: 0.63rem; padding: 2px 0; border-bottom: 1px solid #0c1118;
    color: var(--text-3); font-family: var(--mono); line-height: 1.6;
}
.tl-buy  { color: var(--green); font-weight: 700; }
.tl-sell { color: var(--red);   font-weight: 700; }
.tl-shadow { color: var(--purple); }

/* ── Shadow Ledger Panel ───────────────────────────────────────────────── */
.sl-outer {
    background: #060408; border: 1px solid #3a1555;
    border-radius: 3px; padding: 8px 9px;
    box-shadow: inset 0 0 20px #33006622;
}
.sl-title { color: var(--purple); font-size: 0.56rem; font-weight: 700; letter-spacing: 2.5px; font-family: var(--sans); }
.sl-warn  { color: #cc4488; font-size: 0.62rem; line-height: 1.5; margin: 4px 0; }
.sl-active-badge {
    display: inline-block; background: #3a1555; color: var(--purple);
    padding: 1px 6px; border-radius: 2px; font-size: 0.58rem; font-weight: 700; margin-left: 6px;
}

/* ── Compliance / VaR ──────────────────────────────────────────────────── */
.var-ok     { color: var(--green); font-size: 1.05rem; font-weight: 700; }
.var-breach { color: var(--red); font-size: 1.05rem; font-weight: 700; animation: blink 1.2s infinite; }
.var-lbl    { color: var(--text-3); font-size: 0.56rem; letter-spacing: 1px; font-family: var(--sans); }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.35} }

/* ── Compensation ──────────────────────────────────────────────────────── */
.comp-box {
    border-left: 3px solid var(--border2); padding: 4px 10px;
    margin: 2px 0; background: #090d0d; border-radius: 0 2px 2px 0;
}
.comp-lbl  { color: var(--text-3); font-size: 0.58rem; letter-spacing: 1px; font-family: var(--sans); }
.comp-val  { color: var(--gold); font-size: 0.88rem; font-weight: 700; }
.comp-note { color: #3a5a4a; font-size: 0.56rem; }
.tier-badge {
    display: inline-block; padding: 3px 10px; border-radius: 2px;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 1px;
    font-family: var(--sans); margin: 6px 0;
}

/* ── Status Indicator ──────────────────────────────────────────────────── */
.live-dot {
    display: inline-block; width: 6px; height: 6px; border-radius: 50%;
    background: var(--green); box-shadow: 0 0 5px var(--green);
    animation: pulse-dot 2s ease-in-out infinite; margin-right: 4px;
    vertical-align: middle;
}
@keyframes pulse-dot { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(0.85)} }

/* ── Scrollbars ────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

/* ── Misc ──────────────────────────────────────────────────────────────── */
hr { border-color: var(--border) !important; margin: 5px 0 !important; }
.stAlert { border-radius: 2px !important; font-family: var(--mono) !important; font-size: 0.72rem !important; }
.st-emotion-cache-1v0mbdj img { border-radius: 2px; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# § 4 · SESSION STATE INITIALIZATION
# ══════════════════════════════════════════════════════════════════════════════
def init_session() -> None:
    """Initialize all session state variables with safe defaults."""
    defaults = {
        "cash":            INITIAL_CAPITAL,
        "positions":       {},   # {ticker: {"qty": int, "avg_cost": float}}
        "trades":          [],   # list[dict] — real order log
        "shadow_trades":   [],   # list[dict] — hidden mirror trades (Kerviel)
        "realized_pnl":    0.0,
        "selected_ticker": "SPY",
        "chart_period":    "3mo",
        "delta_pair":      list(DELTA_ONE_PAIRS.keys())[0],
        "total_commission":0.0,
        "total_slippage":  0.0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


# ══════════════════════════════════════════════════════════════════════════════
# § 5 · DATA ENGINE (cached yfinance layer)
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=15, show_spinner=False)
def fetch_quote(ticker: str) -> dict:
    """Fetch current price, change, pct change. Cached 15s for near-realtime."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d", interval="1d")
        if hist.empty:
            return {}
        hist = hist.dropna(subset=["Close"])
        price = float(hist["Close"].iloc[-1])
        prev  = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
        chg   = price - prev
        chg_p = chg / prev * 100 if prev != 0 else 0.0
        vol   = float(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0
        high  = float(hist["High"].iloc[-1])   if "High" in hist.columns else price
        low   = float(hist["Low"].iloc[-1])    if "Low" in hist.columns else price
        return {
            "ticker": ticker, "price": price, "prev": prev,
            "chg": chg, "chg_pct": chg_p, "volume": vol,
            "high": high, "low": low,
        }
    except Exception:
        return {}


@st.cache_data(ttl=60, show_spinner=False)
def fetch_ohlcv(ticker: str, period: str = "3mo") -> pd.DataFrame:
    """Fetch OHLCV candles for chart. Cached 60s."""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval="1d")
        if df.empty:
            return pd.DataFrame()
        df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_var_returns(tickers: tuple, period: str = "6mo") -> pd.DataFrame:
    """Fetch log-returns for VaR calculation. Cached 5 min."""
    try:
        if len(tickers) == 0:
            return pd.DataFrame()
        tickers_list = list(tickers)
        if len(tickers_list) == 1:
            data = yf.download(tickers_list[0], period=period, progress=False, auto_adjust=True)["Close"]
            data = data.to_frame(name=tickers_list[0])
        else:
            raw = yf.download(tickers_list, period=period, progress=False, auto_adjust=True)["Close"]
            data = raw if isinstance(raw, pd.DataFrame) else raw.to_frame()
        returns = np.log(data / data.shift(1)).dropna()
        return returns
    except Exception:
        return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
# § 6 · ORDER EXECUTION ENGINE
# ══════════════════════════════════════════════════════════════════════════════
def compute_slippage(price: float, qty: int) -> float:
    """
    Square-root market impact model:
    slippage = σ * sqrt(qty / ADV) * price
    Simplified here as random with size factor.
    """
    base_bps = random.uniform(0.3, MAX_SLIPPAGE_BPS)
    size_factor = min(math.sqrt(abs(qty) / 200.0), 3.0)
    slip_usd = price * (base_bps / 10_000) * size_factor
    return slip_usd


def execute_order(
    ticker: str,
    qty: int,
    side: str,
    order_type: str = "MARKET",
    limit_price: float | None = None,
    shadow: bool = False,
) -> dict | None:
    """
    Execute a simulated order.

    Args:
        ticker:      Instrument symbol
        qty:         Number of shares / contracts
        side:        "BUY" or "SELL"
        order_type:  "MARKET" or "LIMIT"
        limit_price: Price for limit orders
        shadow:      If True → hidden mirror trade (Shadow Ledger)

    Returns:
        Trade confirmation dict, or None if rejected.
    """
    quote = fetch_quote(ticker)
    if not quote:
        return None

    mid = quote["price"]

    # ── Limit order fill logic ──
    if order_type == "LIMIT" and limit_price is not None:
        if side == "BUY"  and mid > limit_price: return None  # Not filled yet
        if side == "SELL" and mid < limit_price: return None
        exec_price = limit_price
        slip_usd = 0.0
        slip_bps = 0.0
    else:
        slip_usd = compute_slippage(mid, qty)
        slip_usd = slip_usd if side == "BUY" else -slip_usd
        exec_price = mid + slip_usd
        slip_bps = abs(slip_usd / mid * 10_000)

    notional   = exec_price * abs(qty)
    commission = notional * COMMISSION_RATE
    net_debit  = notional + commission if side == "BUY" else -(notional - commission)

    trade = {
        "ts":         datetime.now().strftime("%H:%M:%S.%f")[:-3],
        "date":       datetime.now().strftime("%Y-%m-%d"),
        "ticker":     ticker,
        "side":       side,
        "qty":        qty,
        "exec_px":    round(exec_price, 4),
        "mid_px":     round(mid, 4),
        "slip_bps":   round(slip_bps, 2),
        "slip_usd":   round(abs(slip_usd) * qty, 2),
        "notional":   round(notional, 2),
        "commission": round(commission, 2),
        "net_debit":  round(net_debit, 2),
        "order_type": order_type,
        "shadow":     shadow,
    }

    # ── Shadow Ledger (Kerviel Engine) ─────────────────────────────────────
    if shadow:
        st.session_state.shadow_trades.append(trade)
        return trade

    # ── Real Execution ─────────────────────────────────────────────────────
    if side == "BUY":
        if st.session_state.cash < net_debit:
            return None  # Insufficient funds

        st.session_state.cash -= net_debit
        pos = st.session_state.positions.get(ticker, {"qty": 0, "avg_cost": 0.0})
        new_qty = pos["qty"] + qty
        new_cost = (
            (pos["qty"] * pos["avg_cost"] + qty * exec_price) / new_qty
            if new_qty != 0 else 0.0
        )
        st.session_state.positions[ticker] = {"qty": new_qty, "avg_cost": round(new_cost, 4)}

    elif side == "SELL":
        pos = st.session_state.positions.get(ticker, {"qty": 0, "avg_cost": 0.0})
        if pos["qty"] < qty:
            return None  # Insufficient position

        realized_gross = (exec_price - pos["avg_cost"]) * qty
        realized_net   = realized_gross - commission
        st.session_state.realized_pnl += realized_net
        st.session_state.cash += abs(net_debit)

        new_qty = pos["qty"] - qty
        if new_qty == 0:
            del st.session_state.positions[ticker]
        else:
            st.session_state.positions[ticker]["qty"] = new_qty

    # Accumulate costs
    st.session_state.total_commission += commission
    st.session_state.total_slippage   += abs(slip_usd) * qty

    st.session_state.trades.append(trade)
    return trade


# ══════════════════════════════════════════════════════════════════════════════
# § 7 · PORTFOLIO MANAGER
# ══════════════════════════════════════════════════════════════════════════════
def compute_portfolio_metrics() -> dict:
    """Compute real-time P&L, exposure, NAV."""
    positions = st.session_state.positions
    rows = []
    total_mv = 0.0
    total_cost = 0.0
    gross_long = 0.0
    gross_short = 0.0

    for ticker, pos in positions.items():
        q = fetch_quote(ticker)
        price = q.get("price", pos["avg_cost"]) if q else pos["avg_cost"]
        qty   = pos["qty"]
        cost  = pos["avg_cost"] * qty
        mv    = price * qty
        upnl  = mv - cost
        upnl_pct = upnl / cost * 100 if cost != 0 else 0.0
        rows.append({
            "Ticker": ticker, "Qty": qty,
            "AvgCost": pos["avg_cost"], "Price": price,
            "MktVal": mv, "UPNL": upnl, "UPNL%": upnl_pct,
        })
        total_mv   += mv
        total_cost += cost
        if qty > 0: gross_long  += mv
        else:       gross_short += abs(mv)

    unrealized = total_mv - total_cost
    total_pnl  = unrealized + st.session_state.realized_pnl
    nav        = st.session_state.cash + total_mv
    return {
        "rows":           rows,
        "market_value":   total_mv,
        "cost_basis":     total_cost,
        "unrealized_pnl": unrealized,
        "realized_pnl":   st.session_state.realized_pnl,
        "total_pnl":      total_pnl,
        "gross_exposure": gross_long + gross_short,
        "net_exposure":   gross_long - gross_short,
        "gross_long":     gross_long,
        "gross_short":    gross_short,
        "nav":            nav,
    }


# ══════════════════════════════════════════════════════════════════════════════
# § 8 · VAR ENGINE (Historical Simulation, Basel III)
# ══════════════════════════════════════════════════════════════════════════════
def compute_var(positions: dict, shadow_trades: list, apply_shadow: bool = False) -> dict:
    """
    99% 1-day Historical Simulation VaR.

    apply_shadow=True simulates the Kerviel mechanism: fictitious hedges
    are added to the return series, reducing displayed VaR without touching
    the real portfolio. Risk team sees reduced VaR; real exposure unchanged.
    """
    limit_usd = INITIAL_CAPITAL * VAR_LIMIT_PCT

    if not positions:
        return {"var_pct": 0.0, "var_usd": 0.0, "limit_usd": limit_usd, "breach": False, "buffer_usd": limit_usd}

    tickers = tuple(positions.keys())
    returns_df = fetch_var_returns(tickers)

    # Fallback: use parametric VaR if no returns
    if returns_df.empty:
        var_pct = 0.012  # 1.2% assumed 1-day vol
        total_mv = sum(abs(fetch_quote(t).get("price", 0) * positions[t]["qty"]) for t in tickers)
        var_usd = var_pct * total_mv
        return {"var_pct": var_pct, "var_usd": var_usd, "limit_usd": limit_usd,
                "breach": var_usd > limit_usd, "buffer_usd": limit_usd - var_usd}

    # Build portfolio weights
    mvs = {}
    for t in tickers:
        q = fetch_quote(t)
        px = q.get("price", 0) if q else 0
        mvs[t] = px * positions[t]["qty"]

    total_mv = sum(abs(v) for v in mvs.values())
    if total_mv == 0:
        return {"var_pct": 0.0, "var_usd": 0.0, "limit_usd": limit_usd, "breach": False, "buffer_usd": limit_usd}

    # Weighted portfolio return series
    port_ret = pd.Series(0.0, index=returns_df.index, dtype=float)
    for t in tickers:
        if t in returns_df.columns:
            w = mvs[t] / total_mv
            port_ret = port_ret.add(returns_df[t] * w, fill_value=0)

    # ── Shadow Ledger VaR Reduction (Kerviel mechanism) ──
    shadow_reduction = 0.0
    if apply_shadow and shadow_trades:
        shadow_notional = sum(tr["notional"] for tr in shadow_trades)
        # Each $1M shadow hedge reduces displayed VaR by ~0.3 bps
        shadow_reduction = (shadow_notional / 1_000_000) * 0.00003

    var_1d  = abs(float(np.percentile(port_ret, (1 - VAR_CONFIDENCE) * 100)))
    var_pct = max(var_1d - shadow_reduction, 0.0001)
    var_usd = var_pct * total_mv

    return {
        "var_pct":    var_pct,
        "var_usd":    var_usd,
        "limit_usd":  limit_usd,
        "breach":     var_usd > limit_usd,
        "buffer_usd": limit_usd - var_usd,
        "shadow_red": shadow_reduction,
    }


# ══════════════════════════════════════════════════════════════════════════════
# § 9 · DELTA ONE ENGINE (Kerviel-style Index vs. Basket Arbitrage)
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=90, show_spinner=False)
def compute_d1_spread(pair_name: str) -> dict:
    """
    Compute index price vs. weighted synthetic basket.
    Spread in bps signals potential arbitrage opportunity.
    """
    cfg = DELTA_ONE_PAIRS[pair_name]
    idx_q = fetch_quote(cfg["index"])
    if not idx_q:
        return {}

    idx_price  = idx_q["price"]
    synthetic  = 0.0
    components = []

    for tk, wt in zip(cfg["components"], cfg["weights"]):
        q = fetch_quote(tk)
        if q:
            px      = q["price"]
            contrib = px * wt
            synthetic += contrib
            components.append({
                "Ticker":  tk,
                "Price":   f"${px:,.2f}",
                "Weight":  f"{wt*100:.1f}%",
                "Contrib": f"{contrib:.4f}",
                "Δ Day":   f"{q.get('chg_pct', 0):+.2f}%",
                "Vol":     f"{q.get('volume', 0)/1e6:.1f}M",
            })

    # Normalise synthetic to index price scale
    scale_factor  = idx_price / synthetic if synthetic > 0 else 1.0
    synthetic_norm = synthetic * scale_factor
    spread_bps    = (synthetic_norm - idx_price) / idx_price * 10_000

    return {
        "index":          cfg["index"],
        "index_price":    idx_price,
        "synthetic":      synthetic_norm,
        "spread_bps":     spread_bps,
        "arb_opportunity": abs(spread_bps) > 5.0,
        "components":     components,
        "description":    cfg["description"],
        "idx_chg":        idx_q.get("chg_pct", 0),
    }


# ══════════════════════════════════════════════════════════════════════════════
# § 10 · TRADER COMPENSATION MODEL (Real Bank Structure)
# ══════════════════════════════════════════════════════════════════════════════
def compute_compensation(total_pnl: float) -> dict:
    """
    Bulge bracket trader compensation model:

    Structure (based on industry norms, post-Dodd-Frank):
    1. Fixed base:    $250k (VP/Trader level)
    2. Bonus pool:    40% of P&L exceeding 5% hurdle on capital
    3. Cash portion:  40% of bonus — paid T+1 year-end
    4. Deferred:      60% of bonus — 3-year vesting, clawback provisions
    5. Tier scaling:  Diminishing returns above $5M bonus (regulatory cap)
    6. Malus trigger: Negative P&L → full deferral clawback possible
    """
    hurdle = INITIAL_CAPITAL * HURDLE_RATE  # $500k
    excess = max(0.0, total_pnl - hurdle)
    bonus  = excess * BONUS_SHARE_PCT

    # Regulatory tiered cap (CRD IV / Dodd-Frank variable comp rules)
    if bonus > 5_000_000:
        bonus = 5_000_000 + (bonus - 5_000_000) * 0.5  # 50% rate above $5M
    if bonus > 15_000_000:
        bonus = min(bonus, 20_000_000)  # Hard cap

    cash_bonus     = bonus * (1 - DEFERRED_PCT)
    deferred_bonus = bonus * DEFERRED_PCT
    annual_vest    = deferred_bonus / CLAWBACK_YEARS if bonus > 0 else 0
    total_comp     = BASE_SALARY + bonus
    roc            = total_pnl / INITIAL_CAPITAL * 100

    # Tier determination
    if total_pnl < 0:
        tier, tier_color = "UNDER REVIEW — CLAWBACK RISK", "#ff3355"
    elif total_pnl < 200_000:
        tier, tier_color = "ANALYST / JUNIOR TRADER",       "#8899aa"
    elif total_pnl < 1_000_000:
        tier, tier_color = "ASSOCIATE — PERFORMING",        "#00d4ff"
    elif total_pnl < 3_000_000:
        tier, tier_color = "VP / SENIOR TRADER",            "#ffd700"
    elif total_pnl < 10_000_000:
        tier, tier_color = "DIRECTOR / DESK HEAD",          "#ff8800"
    else:
        tier, tier_color = "★ MD — STAR TRADER",            "#ff3355"

    return {
        "base":          BASE_SALARY,
        "bonus":         bonus,
        "cash_bonus":    cash_bonus,
        "deferred":      deferred_bonus,
        "annual_vest":   annual_vest,
        "total":         total_comp,
        "hurdle":        hurdle,
        "excess":        excess,
        "roc":           roc,
        "tier":          tier,
        "tier_color":    tier_color,
        "malus_risk":    total_pnl < 0,
    }


# ══════════════════════════════════════════════════════════════════════════════
# § 11 · CHART ENGINE
# ══════════════════════════════════════════════════════════════════════════════
def build_chart(ticker: str, period: str) -> go.Figure:
    """Build full Bloomberg-style candlestick chart with overlays."""
    df = fetch_ohlcv(ticker, period)

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="NO DATA AVAILABLE", showarrow=False,
                           font=dict(color="#ff3355", size=14, family="JetBrains Mono"))
        fig.update_layout(paper_bgcolor="#0a0e14", plot_bgcolor="#0a0e14", height=400)
        return fig

    close = df["Close"].dropna()

    # ── Technical Indicators ──
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    std20 = close.rolling(20).std()
    bb_up = sma20 + 2.0 * std20
    bb_dn = sma20 - 2.0 * std20

    # VWAP (simplified daily cumulative)
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    vwap = (typical * df["Volume"]).cumsum() / df["Volume"].cumsum()

    # RSI (14)
    delta_ = close.diff()
    gain   = delta_.clip(lower=0).rolling(14).mean()
    loss   = (-delta_.clip(upper=0)).rolling(14).mean()
    rs     = gain / loss.replace(0, 1e-9)
    rsi    = 100 - 100 / (1 + rs)

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.66, 0.18, 0.16],
        subplot_titles=["", "", ""],
    )

    # ── Candlesticks ──
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name=ticker,
        increasing=dict(line=dict(color="#00ff88", width=1), fillcolor="#004422"),
        decreasing=dict(line=dict(color="#ff3355", width=1), fillcolor="#440011"),
    ), row=1, col=1)

    # Bollinger Bands
    fig.add_trace(go.Scatter(x=df.index, y=bb_up, line=dict(color="rgba(0,212,255,0.12)", width=1),
                             showlegend=False, hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=bb_dn, line=dict(color="rgba(0,212,255,0.12)", width=1),
                             fill="tonexty", fillcolor="rgba(0,212,255,0.04)", showlegend=False, hoverinfo="skip"), row=1, col=1)

    # SMA lines
    fig.add_trace(go.Scatter(x=df.index, y=sma20, line=dict(color="#ffd700", width=1, dash="dot"),
                             name="SMA20", showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=sma50, line=dict(color="#ff8800", width=1, dash="dash"),
                             name="SMA50", showlegend=False), row=1, col=1)

    # VWAP
    fig.add_trace(go.Scatter(x=df.index, y=vwap, line=dict(color="#aa55cc", width=1),
                             name="VWAP", showlegend=False), row=1, col=1)

    # ── Volume ──
    bar_colors = ["#004422" if c >= o else "#440011"
                  for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], marker_color=bar_colors,
                         showlegend=False, opacity=0.65), row=2, col=1)

    # ── RSI ──
    fig.add_trace(go.Scatter(x=df.index, y=rsi, line=dict(color="#00d4ff", width=1.5),
                             showlegend=False, fill="tozeroy", fillcolor="rgba(0,212,255,0.04)"), row=3, col=1)
    fig.add_hline(y=70, line=dict(color="#ff3355", width=0.8, dash="dot"), row=3, col=1)
    fig.add_hline(y=30, line=dict(color="#00ff88", width=0.8, dash="dot"), row=3, col=1)
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(255,51,85,0.03)",   line_width=0, row=3, col=1)
    fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(0,255,136,0.03)",   line_width=0, row=3, col=1)

    # ── Layout ──
    BG  = "#0a0e14"
    GRD = "#0d1520"
    TXT = dict(family="JetBrains Mono", size=9, color="#3a5f7a")

    fig.update_layout(
        paper_bgcolor=BG, plot_bgcolor=BG,
        margin=dict(l=0, r=4, t=6, b=0),
        height=440,
        xaxis_rangeslider_visible=False,
        font=TXT,
        legend=dict(bgcolor=BG, bordercolor="#1a2535", font=dict(size=8)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#0d1520", font=dict(family="JetBrains Mono", size=10)),
    )

    for axis in ["xaxis", "xaxis2", "xaxis3"]:
        fig.update_layout(**{axis: dict(gridcolor=GRD, tickfont=dict(size=8, color="#3a5f7a"),
                                        showgrid=True, zeroline=False)})
    for axis in ["yaxis", "yaxis2", "yaxis3"]:
        fig.update_layout(**{axis: dict(gridcolor=GRD, tickfont=dict(size=8, color="#3a5f7a"),
                                        side="right", showgrid=True, zeroline=False)})

    return fig


# ══════════════════════════════════════════════════════════════════════════════
# § 12 · SYNTHETIC ORDER BOOK GENERATOR
# ══════════════════════════════════════════════════════════════════════════════
def generate_order_book(mid: float, spread_bps: float = 1.5, levels: int = 8):
    """Generate realistic simulated order book depth."""
    half_spread = mid * spread_bps / 20_000
    asks, bids = [], []
    for i in range(levels):
        tick = mid * 0.00008 * (i + 1)
        ask_px = round(mid + half_spread + tick, 4)
        bid_px = round(mid - half_spread - tick, 4)
        # Depth: exponential-ish distribution (market order resting)
        base  = random.randint(80, 600)
        decay = random.uniform(0.7, 1.8)
        ask_sz = int(base * (1 + i * decay * 0.5) * random.uniform(0.8, 1.2))
        bid_sz = int(base * (1 + i * decay * 0.5) * random.uniform(0.8, 1.2))
        asks.append((ask_px, ask_sz))
        bids.append((bid_px, bid_sz))
    return list(reversed(asks)), bids  # asks: high→low, bids: high→low


# ══════════════════════════════════════════════════════════════════════════════
# § 13 · UTILITY FORMATTERS
# ══════════════════════════════════════════════════════════════════════════════
def f_usd(v: float, d: int = 0) -> str:
    s = "+" if v >= 0 else ""
    return f"{s}${v:,.{d}f}"

def f_pct(v: float) -> str:
    return f"{v:+.2f}%"

def pnl_color(v: float) -> str:
    return "#00ff88" if v >= 0 else "#ff3355"


# ══════════════════════════════════════════════════════════════════════════════
# § 14 · UI RENDER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def render_topbar() -> None:
    date     = datetime.now().strftime("%A %d %B %Y").upper()
    last_upd = datetime.now().strftime("%H:%M:%S")
    metrics  = compute_portfolio_metrics()
    nav_delta = metrics["nav"] - INITIAL_CAPITAL
    nav_col   = pnl_color(nav_delta)
    st.markdown(f"""
<div class="t-bar">
  <div>
    <div class="t-title">⚡ TRADING TERMINAL PRO</div>
    <div class="t-subtitle">HFT ENGINE · DELTA ONE · MODULE KERVIEL™ · SALLE DES MARCHÉS</div>
  </div>
  <div style="text-align:center">
    <div class="t-acct"><span class="live-dot"></span>ACCT: TRADER-001 · DESK: EQUITY DERIVATIVES · SESSION ACTIVE</div>
    <div style="margin-top:2px">
      <span style="color:#3a5f7a;font-size:0.58rem">NAV</span>
      <span style="color:{nav_col};font-size:0.82rem;font-weight:700;margin:0 8px">${metrics['nav']:,.0f}</span>
      <span style="color:{nav_col};font-size:0.68rem">{f_usd(nav_delta)} ({nav_delta/INITIAL_CAPITAL*100:+.2f}%)</span>
    </div>
    <div style="color:#3a5f7a;font-size:0.55rem;margin-top:1px">
      QUOTES: 15s REFRESH · LAST PULL: {last_upd}
    </div>
  </div>
  <div>
    <div class="t-clock" id="live-clock">--:--:--</div>
    <div class="t-date">{date}</div>
  </div>
</div>
<script>
(function(){{
  function pad(n){{return n<10?'0'+n:''+(n);}}
  function tick(){{
    var d=new Date();
    var t=pad(d.getHours())+':'+pad(d.getMinutes())+':'+pad(d.getSeconds());
    var el=document.getElementById('live-clock');
    if(el){{el.textContent=t;}}
  }}
  tick(); setInterval(tick,1000);
}})();
</script>
""", unsafe_allow_html=True)


def render_watchlist() -> None:
    st.markdown('<div class="ph">WATCHLIST — LIVE QUOTES</div>', unsafe_allow_html=True)

    categories = {
        "US EQUITIES / ETF": ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "GS", "JPM", "AMZN"],
        "ALTERNATIVES":      ["BTC-USD", "ETH-USD", "GC=F"],
        "FUTURES / VOL":     ["ES=F", "NQ=F", "^VIX"],
    }

    for cat, tickers in categories.items():
        st.markdown(f'<div class="wl-cat">{cat}</div>', unsafe_allow_html=True)
        for tk in tickers:
            q = fetch_quote(tk)
            if not q:
                continue
            px  = q["price"]
            chp = q["chg_pct"]
            sym = "▲" if chp >= 0 else "▼"
            col_px  = "#00ff88" if chp >= 0 else "#ff3355"
            col_cls = "wl-up" if chp >= 0 else "wl-dn"
            # Format price
            fmt_px = f"${px:,.4f}" if px < 100 else f"${px:,.2f}"
            st.markdown(f"""
<div class="wl-row">
  <span class="wl-sym">{tk}</span>
  <div style="text-align:right">
    <div class="wl-px" style="color:{col_px}">{fmt_px}</div>
    <div class="{col_cls}">{sym}{abs(chp):.2f}%</div>
  </div>
</div>""", unsafe_allow_html=True)

    # Ticker selector
    st.markdown("<div style='margin-top:6px'>", unsafe_allow_html=True)
    sel = st.selectbox(
        "ACTIVE TICKER",
        WATCHLIST_TICKERS,
        index=WATCHLIST_TICKERS.index(st.session_state.selected_ticker),
        key="wl_sel",
    )
    if sel != st.session_state.selected_ticker:
        st.session_state.selected_ticker = sel
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_news() -> None:
    st.markdown('<div class="ph" style="margin-top:6px">NEWS WIRE — MARKET INTELLIGENCE</div>', unsafe_allow_html=True)
    badge_class = {"🔴": "nb-r", "🟡": "nb-y", "🟢": "nb-g"}
    for icon, badge, text, ts in NEWS_FEED:
        cls = badge_class.get(icon, "nb-y")
        st.markdown(f"""
<div class="ni">
  <span class="{cls}">{icon} {badge}</span><span class="nt">{ts}</span><br>
  <span class="nx">{text}</span>
</div>""", unsafe_allow_html=True)


def render_chart() -> None:
    ticker = st.session_state.selected_ticker
    q = fetch_quote(ticker)
    px  = q.get("price", 0)    if q else 0
    chg = q.get("chg", 0)      if q else 0
    chp = q.get("chg_pct", 0)  if q else 0
    hi  = q.get("high", px)    if q else 0
    lo  = q.get("low", px)     if q else 0
    vol = q.get("volume", 0)   if q else 0
    chc = pnl_color(chg)

    # Header row
    h1, h2, h3, h4, h5 = st.columns([2, 2, 1.5, 1.5, 3])
    with h1:
        st.markdown(f"""
<div style="line-height:1.2">
  <span style="color:#e0e8f0;font-size:1.1rem;font-weight:700;letter-spacing:2px">{ticker}</span>
  <span style="color:#3a5f7a;font-size:0.6rem;margin-left:6px">EQUITY</span>
</div>""", unsafe_allow_html=True)
    with h2:
        st.markdown(f'<div style="color:{chc};font-size:1.05rem;font-weight:700">${px:,.4f}<br>'
                    f'<span style="font-size:0.68rem">{f_usd(chg, 2)} {f_pct(chp)}</span></div>',
                    unsafe_allow_html=True)
    with h3:
        st.markdown(f'<div style="color:#3a5f7a;font-size:0.56rem">HIGH<br>'
                    f'<span style="color:#e0e8f0;font-size:0.78rem">${hi:,.2f}</span></div>',
                    unsafe_allow_html=True)
    with h4:
        st.markdown(f'<div style="color:#3a5f7a;font-size:0.56rem">LOW<br>'
                    f'<span style="color:#e0e8f0;font-size:0.78rem">${lo:,.2f}</span></div>',
                    unsafe_allow_html=True)
    with h5:
        period = st.radio(
            "PERIOD", ["1mo", "3mo", "6mo", "1y", "2y"], horizontal=True,
            index=["1mo", "3mo", "6mo", "1y", "2y"].index(st.session_state.chart_period),
            key="period_radio",
        )
        if period != st.session_state.chart_period:
            st.session_state.chart_period = period

    fig = build_chart(ticker, st.session_state.chart_period)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_order_book() -> None:
    st.markdown('<div class="ph">ORDER BOOK — L2 DEPTH</div>', unsafe_allow_html=True)
    ticker = st.session_state.selected_ticker
    q = fetch_quote(ticker)
    if not q:
        st.markdown('<div style="color:#ff3355;font-size:0.7rem;padding:4px">⚠ FEED INTERRUPTED</div>',
                    unsafe_allow_html=True)
        return

    mid = q["price"]
    asks, bids = generate_order_book(mid)
    max_sz = max([s for _, s in asks] + [s for _, s in bids], default=1)

    st.markdown('<div class="ob-hdr"><span>SIZE</span><span>ASK PRICE</span></div>', unsafe_allow_html=True)
    for px, sz in asks:
        bar_w = int(sz / max_sz * 55)
        st.markdown(f"""
<div class="ob-row ob-a">
  <span class="pr-sz">{sz:,}</span>
  <div style="display:flex;align-items:center;gap:3px">
    <div class="ob-bar-a" style="width:{bar_w}px"></div>
    <span class="pr-a">{px:.4f}</span>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown(f'<div class="ob-mid"><span class="live-dot"></span>{mid:,.4f}</div>', unsafe_allow_html=True)

    st.markdown('<div class="ob-hdr"><span>BID PRICE</span><span>SIZE</span></div>', unsafe_allow_html=True)
    for px, sz in bids:
        bar_w = int(sz / max_sz * 55)
        st.markdown(f"""
<div class="ob-row ob-b">
  <div style="display:flex;align-items:center;gap:3px">
    <span class="pr-b">{px:.4f}</span>
    <div class="ob-bar-b" style="width:{bar_w}px"></div>
  </div>
  <span class="pr-sz">{sz:,}</span>
</div>""", unsafe_allow_html=True)

    # Spread display
    if asks and bids:
        spread_bps = (asks[-1][0] - bids[0][0]) / mid * 10_000
        st.markdown(f'<div style="text-align:center;color:#3a5f7a;font-size:0.58rem;margin-top:3px">'
                    f'SPREAD: {spread_bps:.1f} bps</div>', unsafe_allow_html=True)


def render_trade_terminal() -> None:
    st.markdown('<div class="ph" style="margin-top:4px">EXECUTION TERMINAL</div>', unsafe_allow_html=True)
    ticker = st.session_state.selected_ticker
    q = fetch_quote(ticker)
    mid = q.get("price", 0) if q else 0

    c1, c2 = st.columns(2)
    with c1:
        qty = st.number_input("QTY (shares)", min_value=1, max_value=500_000,
                              value=100, step=50, key="exec_qty")
    with c2:
        otype = st.selectbox("ORDER TYPE", ["MARKET", "LIMIT"], key="exec_otype")

    limit_px = None
    if otype == "LIMIT":
        limit_px = st.number_input("LIMIT PRICE", value=round(mid * 0.995, 2),
                                   step=0.01, format="%.4f", key="exec_limitpx")

    # Pre-trade analytics
    notional  = mid * qty
    comm      = notional * COMMISSION_RATE
    slip_est  = notional * MAX_SLIPPAGE_BPS / 10_000
    st.markdown(f"""
<div style="background:#090d14;border:1px solid #1a2535;border-radius:2px;padding:4px 6px;margin:4px 0">
  <span style="color:#3a5f7a;font-size:0.58rem">NOTIONAL</span>
  <span style="color:#e0e8f0;font-size:0.72rem;margin:0 8px">${notional:,.0f}</span>
  <span style="color:#3a5f7a;font-size:0.58rem">COMM ~</span>
  <span style="color:#ffd700;font-size:0.72rem;margin:0 8px">${comm:,.0f}</span>
  <span style="color:#3a5f7a;font-size:0.58rem">SLIP EST ~</span>
  <span style="color:#ff8800;font-size:0.72rem">${slip_est:,.0f}</span>
</div>""", unsafe_allow_html=True)

    cb, cs = st.columns(2)
    with cb:
        if st.button(f"▲ BUY  {ticker}", use_container_width=True, key="btn_buy"):
            t = execute_order(ticker, qty, "BUY", otype, limit_px)
            if t:
                st.success(f"✓ FILLED: BUY {qty:,} {ticker} @ {t['exec_px']:.4f} | slip {t['slip_bps']:.1f}bps")
            else:
                st.error("✗ REJECTED — Insufficient funds or limit not reached")
    with cs:
        if st.button(f"▼ SELL {ticker}", use_container_width=True, key="btn_sell"):
            t = execute_order(ticker, qty, "SELL", otype, limit_px)
            if t:
                st.success(f"✓ FILLED: SELL {qty:,} {ticker} @ {t['exec_px']:.4f}")
            else:
                st.error("✗ REJECTED — No position or limit not reached")

    # Execution stats
    st.markdown(f"""
<div style="color:#3a5f7a;font-size:0.58rem;margin-top:4px;text-align:center">
  TOTAL COMM PAID: ${st.session_state.total_commission:,.0f} &nbsp;|&nbsp;
  TOTAL SLIPPAGE: ${st.session_state.total_slippage:,.0f}
</div>""", unsafe_allow_html=True)


def render_pnl_strip(metrics: dict) -> None:
    """Top-level P&L metrics strip."""
    st.markdown('<div class="ph">P&L DASHBOARD — REAL-TIME</div>', unsafe_allow_html=True)
    nav_d  = metrics["nav"] - INITIAL_CAPITAL
    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)

    with c1: st.metric("NAV",           f"${metrics['nav']:,.0f}",           delta=f_usd(nav_d))
    with c2: st.metric("UNREALIZED P&L", f_usd(metrics["unrealized_pnl"]))
    with c3: st.metric("REALIZED P&L",   f_usd(metrics["realized_pnl"]))
    with c4: st.metric("TOTAL P&L",      f_usd(metrics["total_pnl"]))
    with c5: st.metric("CASH",           f"${st.session_state.cash:,.0f}")
    with c6: st.metric("GROSS EXP.",     f"${metrics['gross_exposure']:,.0f}")
    with c7: st.metric("NET EXP.",       f"${metrics['net_exposure']:,.0f}")
    with c8: st.metric("POSITIONS",      str(len(st.session_state.positions)))


def render_positions(metrics: dict) -> None:
    if not metrics["rows"]:
        st.markdown('<div style="color:#3a5f7a;font-size:0.72rem;padding:10px;text-align:center">'
                    '— NO OPEN POSITIONS —</div>', unsafe_allow_html=True)
        return

    rows_html = ""
    for r in metrics["rows"]:
        c  = pnl_color(r["UPNL"])
        rows_html += f"""
<tr>
  <td>{r['Ticker']}</td>
  <td style="text-align:right">{r['Qty']:,}</td>
  <td style="text-align:right">{r['AvgCost']:.4f}</td>
  <td style="text-align:right">{r['Price']:.4f}</td>
  <td style="text-align:right">${r['MktVal']:,.0f}</td>
  <td style="text-align:right;color:{c}">{f_usd(r['UPNL'])}</td>
  <td style="text-align:right;color:{c}">{r['UPNL%']:+.2f}%</td>
</tr>"""

    st.markdown(f"""
<table class="pos-table">
<thead><tr>
  <th>TICKER</th><th>QTY</th><th>AVG COST</th><th>LAST</th><th>MKT VALUE</th><th>UNREALIZED P&L</th><th>UPNL%</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>""", unsafe_allow_html=True)


def render_trade_history() -> None:
    trades = st.session_state.trades
    if not trades:
        st.markdown('<div style="color:#3a5f7a;font-size:0.72rem;padding:10px;text-align:center">'
                    '— NO TRADES EXECUTED —</div>', unsafe_allow_html=True)
        return

    for t in reversed(trades[-30:]):
        side_cls = "tl-buy" if t["side"] == "BUY" else "tl-sell"
        arrow    = "▲" if t["side"] == "BUY" else "▼"
        st.markdown(f"""
<div class="tl-entry">
  <span style="color:#3a5f7a">{t['ts']}</span> &nbsp;
  <span class="{side_cls}">{arrow} {t['side']}</span> &nbsp;
  <span style="color:#dde3ec">{t['ticker']}</span> &nbsp;
  {t['qty']:,}× @ <strong>{t['exec_px']:.4f}</strong> &nbsp;|&nbsp;
  Slip: {t['slip_bps']:.1f}bps &nbsp;|&nbsp; Com: ${t['commission']:,.0f} &nbsp;|&nbsp; {t['order_type']}
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:8px'>", unsafe_allow_html=True)
    df_exp = pd.DataFrame(trades)
    csv = df_exp.to_csv(index=False)
    st.download_button(
        label="⬇  EXPORT TRADE LOG (CSV)",
        data=csv.encode("utf-8"),
        file_name=f"trade_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True,
        key="dl_trades",
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_delta_one() -> None:
    """Delta One Arbitrage Engine — Kerviel-style index vs. basket."""
    st.markdown('<div class="ph">DELTA ONE ENGINE — INDEX vs. BASKET ARBITRAGE</div>', unsafe_allow_html=True)

    pair_name = st.selectbox("ARBITRAGE STRATEGY", list(DELTA_ONE_PAIRS.keys()), key="d1_sel")
    data = compute_d1_spread(pair_name)

    if not data:
        st.error("⚠ Market data unavailable for this strategy")
        return

    spread    = data["spread_bps"]
    arb       = data["arb_opportunity"]
    spread_col = "#00ff88" if arb else "#3a5f7a"
    arb_label  = "▶ TRADEABLE SPREAD DETECTED — EXECUTE ARBITRAGE" if arb else "— SPREAD BELOW THRESHOLD (< 5 bps)"

    st.markdown(f'<div style="color:#3a5f7a;font-size:0.62rem;margin-bottom:4px">{data["description"]}</div>',
                unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric(f"{data['index']} (INDEX)",   f"${data['index_price']:,.2f}",
                        delta=f"{data['idx_chg']:+.2f}%")
    with c2: st.metric("SYNTHETIC BASKET",           f"${data['synthetic']:,.2f}")
    with c3: st.metric("SPREAD",                     f"{spread:+.2f} bps")
    with c4: st.metric("ARB THRESHOLD",              "5.0 bps", delta="OPPORTUNITY" if arb else "TIGHT",
                        delta_color="normal" if arb else "off")

    st.markdown(f'<div style="color:{spread_col};font-size:0.72rem;font-weight:700;margin:4px 0">'
                f'{arb_label}</div>', unsafe_allow_html=True)

    # Component table
    if data.get("components"):
        df_c = pd.DataFrame(data["components"])
        st.dataframe(df_c, use_container_width=True, hide_index=True, height=180)

    # Trade buttons
    if arb:
        st.markdown("**ARBITRAGE EXECUTION**")
        qty_d1 = st.number_input("INDEX UNITS", value=1000, step=100, min_value=1, key="d1_qty")
        notional_est = data["index_price"] * qty_d1
        st.markdown(f'<div style="color:#3a5f7a;font-size:0.6rem">ESTIMATED NOTIONAL: ${notional_est:,.0f} | '
                    f'COMM: ${notional_est * COMMISSION_RATE:,.0f}</div>', unsafe_allow_html=True)

        ca, cb = st.columns(2)
        with ca:
            if st.button(f"▲ LONG {data['index']} / SHORT BASKET", use_container_width=True, key="d1_buy"):
                t = execute_order(data["index"], qty_d1, "BUY")
                if t:
                    st.success(f"✓ Delta One LONG: {data['index']} {qty_d1:,}× @ {t['exec_px']:.2f}")
                else:
                    st.error("✗ Insufficient capital")
        with cb:
            if st.button(f"▼ SHORT {data['index']} / LONG BASKET", use_container_width=True, key="d1_sell"):
                t = execute_order(data["index"], qty_d1, "SELL")
                if t:
                    st.success(f"✓ Delta One SHORT: {data['index']} {qty_d1:,}× @ {t['exec_px']:.2f}")
                else:
                    st.error("✗ No existing position to sell")


def render_compliance(metrics: dict) -> None:
    """Compliance Dashboard — VaR Monitor with Shadow Ledger manipulation."""
    st.markdown('<div class="ph">COMPLIANCE & RISK — VaR MONITOR (99%, 1-DAY, HISTORICAL SIM)</div>',
                unsafe_allow_html=True)

    positions = st.session_state.positions
    shadows   = st.session_state.shadow_trades

    var_true    = compute_var(positions, [], apply_shadow=False)
    var_display = compute_var(positions, shadows, apply_shadow=True)
    limit       = var_true["limit_usd"]

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        cls = "var-breach" if var_true["breach"] else "var-ok"
        st.markdown(f"""
<div><div class="var-lbl">TRUE VAR (INTERNAL)</div>
<div class="{cls}">${var_true["var_usd"]:,.0f}</div>
<div class="var-lbl">{var_true["var_pct"]*100:.3f}% of AUM</div></div>
""", unsafe_allow_html=True)

    with c2:
        cls2 = "var-breach" if var_display["breach"] else "var-ok"
        shd_label = " (+SHADOW HEDGE)" if shadows else ""
        st.markdown(f"""
<div><div class="var-lbl">REPORTED VAR{shd_label}</div>
<div class="{cls2}">${var_display["var_usd"]:,.0f}</div>
<div class="var-lbl">{var_display["var_pct"]*100:.3f}% — Compliance view</div></div>
""", unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
<div><div class="var-lbl">VAR LIMIT (2% AUM)</div>
<div style="color:#ffd700;font-size:1.05rem;font-weight:700">${limit:,.0f}</div>
<div class="var-lbl">Buffer: ${var_true["buffer_usd"]:,.0f}</div></div>
""", unsafe_allow_html=True)

    with c4:
        breach_status = "⛔ LIMIT BREACH" if var_true["breach"] else "✓ WITHIN LIMITS"
        breach_col    = "#ff3355" if var_true["breach"] else "#00ff88"
        st.markdown(f"""
<div><div class="var-lbl">STATUS</div>
<div style="color:{breach_col};font-size:0.92rem;font-weight:700">{breach_status}</div>
<div class="var-lbl">VaR/Limit: {var_true["var_usd"]/limit*100:.1f}%</div></div>
""", unsafe_allow_html=True)

    with c5:
        if shadows:
            shd_notional = sum(t["notional"] for t in shadows)
            var_red = var_true["var_usd"] - var_display["var_usd"]
            st.markdown(f"""
<div class="sl-outer" style="padding:5px 7px">
<div class="sl-title">⬡ SHADOW ACTIVE</div>
<div class="sl-warn" style="font-size:0.6rem">
{len(shadows)} hidden op(s)<br>
Notional: ${shd_notional:,.0f}<br>
VaR concealed: <span style="color:#ff3355">${var_red:,.0f}</span>
</div></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
<div><div class="var-lbl">SHADOW LEDGER</div>
<div style="color:#3a5f7a;font-size:0.8rem;font-weight:700">INACTIVE</div>
<div class="var-lbl">No hidden ops</div></div>""", unsafe_allow_html=True)


def render_shadow_ledger() -> None:
    """
    MODULE KERVIEL™ — Hidden Mirror Trades (Shadow Ledger).

    Educational reconstruction of the SocGen 2008 fraud mechanism:
    - Jérôme Kerviel accumulated ~€50B in hidden futures positions
    - He offset them with fictitious hedges on SocGen's books
    - Risk systems showed neutral/hedged exposure → VaR within limits
    - Real P&L was unhedged; actual loss reached €4.9 billion
    - Discovered Jan 2008; SocGen unwound positions over 3 days
    """
    shd_count = len(st.session_state.shadow_trades)
    badge = f'<span class="sl-active-badge">⬡ {shd_count} OPS ACTIVE</span>' if shd_count else ""

    st.markdown(f"""
<div class="sl-outer">
<div class="sl-title">☠ SHADOW LEDGER — MODULE KERVIEL™{badge}</div>
<div class="sl-warn">
⚠ USAGE PÉDAGOGIQUE EXCLUSIVEMENT<br>
Reproduit la fraude SocGen/Kerviel (Jan 2008, ~4.9 Md€). Ces opérations fictives
réduisent la VaR <i>affichée</i> en compliance <strong>sans modifier le P&L réel</strong>.
Le desk Risk voit une exposition neutre — le P&L réel reste exposé.
</div>
</div>""", unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    with c1:
        sl_ticker = st.selectbox("FICTITIOUS HEDGE TICKER", WATCHLIST_TICKERS, key="sl_tk")
        sl_notl   = st.number_input("FICTITIOUS NOTIONAL ($)", value=2_000_000,
                                    step=500_000, min_value=100_000, key="sl_notl")
    with c2:
        sl_side_label = st.selectbox("DIRECTION", ["BUY (Fictitious Long)", "SELL (Fictitious Short)"], key="sl_side")
        sl_side = "BUY" if sl_side_label.startswith("BUY") else "SELL"

    c3, c4, c5 = st.columns(3)
    with c3:
        if st.button("🔒 REGISTER HIDDEN MIRROR TRADE", use_container_width=True, key="sl_exec"):
            q = fetch_quote(sl_ticker)
            if q and q.get("price", 0) > 0:
                qty_shadow = max(1, int(sl_notl / q["price"]))
                t = execute_order(sl_ticker, qty_shadow, sl_side, shadow=True)
                if t:
                    st.success(f"⬡ Shadow: {sl_side} {sl_ticker} ×{t['qty']:,} @ {t['exec_px']:.2f} | "
                               f"${t['notional']:,.0f} | HIDDEN FROM RISK DESK")
            else:
                st.error("⚠ Could not fetch price for shadow trade")

    with c4:
        if st.button("🗑 CLEAR SHADOW LEDGER", use_container_width=True, key="sl_clr"):
            st.session_state.shadow_trades = []
            st.info("Shadow ledger cleared — VaR reverts to true exposure")

    with c5:
        if st.session_state.shadow_trades:
            df_shd = pd.DataFrame(st.session_state.shadow_trades)
            csv_shd = df_shd.to_csv(index=False)
            st.download_button("⬇ EXPORT SHADOW LOG", csv_shd.encode(),
                               f"shadow_log_{datetime.now().strftime('%Y%m%d')}.csv",
                               mime="text/csv", use_container_width=True, key="dl_shadow")

    # Display recent shadow trades
    if st.session_state.shadow_trades:
        st.markdown('<div style="margin-top:5px">', unsafe_allow_html=True)
        for t in reversed(st.session_state.shadow_trades[-6:]):
            side_cls = "tl-buy" if t["side"] == "BUY" else "tl-sell"
            st.markdown(f"""
<div class="tl-entry tl-shadow">
  <span style="color:#3a5f7a">{t['ts']}</span> &nbsp;
  ⬡ <span class="{side_cls}">{t['side']}</span> &nbsp;
  {t['ticker']} {t['qty']:,}× @ {t['exec_px']:.4f} &nbsp;|&nbsp;
  ${t['notional']:,.0f} &nbsp;|&nbsp;
  <span style="color:#ff3355;font-size:0.58rem">SHADOW / NOT REPORTED</span>
</div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def render_compensation(metrics: dict) -> None:
    comp = compute_compensation(metrics["total_pnl"])

    st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
  <div>
    <div class="var-lbl">TRADER TIER</div>
    <span class="tier-badge" style="background:#0d1010;color:{comp['tier_color']};
          border:1px solid {comp['tier_color']}44">{comp['tier']}</span>
  </div>
  <div style="text-align:right">
    <div class="var-lbl">RETURN ON CAPITAL</div>
    <div style="color:{'#00ff88' if comp['roc']>=0 else '#ff3355'};font-size:1.1rem;font-weight:700">{comp['roc']:+.2f}%</div>
    <div class="var-lbl">HURDLE: {HURDLE_RATE*100:.0f}% (${comp['hurdle']:,.0f})</div>
  </div>
</div>""", unsafe_allow_html=True)

    if comp["malus_risk"]:
        st.markdown('<div style="color:#ff3355;font-size:0.68rem;border:1px solid #ff335533;'
                    'border-radius:2px;padding:4px 7px;margin-bottom:5px">'
                    '⚠ MALUS TRIGGER — Negative P&L activates deferred compensation clawback provisions. '
                    'All vested deferred comp may be recovered.</div>', unsafe_allow_html=True)

    items = [
        ("BASE SALARY (FIXED)",        f"${comp['base']:,.0f}",        "VP/Trader level — paid regardless of performance"),
        ("GROSS BONUS (VARIABLE)",     f"${comp['bonus']:,.0f}",        f"40% of P&L > hurdle · Excess P&L: ${comp['excess']:,.0f}"),
        ("   ↳ CASH BONUS (40%)",      f"${comp['cash_bonus']:,.0f}",   "Paid T+1 year-end · Immediately vested"),
        ("   ↳ DEFERRED (60%)",        f"${comp['deferred']:,.0f}",     f"3-yr vesting · ${comp['annual_vest']:,.0f}/yr · Subject to clawback"),
        ("TOTAL COMPENSATION",         f"${comp['total']:,.0f}",        "Pre-tax · Excludes benefits & carried interest"),
    ]

    for lbl, val, note in items:
        is_total  = "TOTAL" in lbl
        bdr_color = comp["tier_color"] if is_total else "#2a3535"
        val_color = comp["tier_color"] if is_total else "#ffd700"
        if val == "$0" and "BONUS" in lbl:
            val_color = "#3a5f7a"
        st.markdown(f"""
<div class="comp-box" style="border-left-color:{bdr_color}">
  <div class="comp-lbl">{lbl}</div>
  <div class="comp-val" style="color:{val_color}">{val}</div>
  <div class="comp-note">{note}</div>
</div>""", unsafe_allow_html=True)

    # Note on co-investment / carried interest
    if comp["total"] > 1_000_000:
        st.markdown("""
<div style="color:#3a5a4a;font-size:0.58rem;margin-top:5px;border-top:1px solid #1a2535;padding-top:4px">
★ At this P&L level, typical bulge bracket structures also include: co-investment rights in PE/HF vehicles,
carried interest on managed accounts, long-term incentive plans (LTIP), and restricted stock units (RSU).
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# § 15 · MAIN APPLICATION LAYOUT
# ══════════════════════════════════════════════════════════════════════════════
def main() -> None:
    # ── Auto-refresh via JS (no external package) ────────────────────────────
    # A hidden JS snippet reloads the page at the configured interval.
    # st.session_state["refresh_count"] is incremented manually each run.
    _interval_ms = st.session_state.get("refresh_interval_ms", 15_000)
    if "refresh_count" not in st.session_state:
        st.session_state["refresh_count"] = 0
    st.session_state["refresh_count"] += 1
    refresh_count = st.session_state["refresh_count"]
    # Inject JS reload timer — replaces itself each Streamlit run
    st.markdown(
        f'''<script>
(function(){{
  if(window._refreshTimer){{clearTimeout(window._refreshTimer);}}
  window._refreshTimer = setTimeout(function(){{
    window.location.reload();
  }}, {_interval_ms});
}})();
</script>''',
        unsafe_allow_html=True,
    )

    inject_css()
    render_topbar()

    # Compute portfolio once per render cycle
    metrics = compute_portfolio_metrics()

    # ─── THREE-COLUMN TRADING LAYOUT ─────────────────────────────────────────
    col_l, col_c, col_r = st.columns([1.35, 4.1, 1.55])

    # LEFT — Watchlist + News Wire
    with col_l:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        render_watchlist()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        render_news()
        st.markdown('</div>', unsafe_allow_html=True)

    # CENTER — Chart + P&L strip + Tabbed content
    with col_c:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        render_chart()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        render_pnl_strip(metrics)
        st.markdown('</div>', unsafe_allow_html=True)

        tab_pos, tab_hist, tab_d1, tab_comp, tab_risk = st.tabs([
            "📊  POSITIONS",
            "📋  TRADE HISTORY",
            "⚡  DELTA ONE ENGINE",
            "💰  COMPENSATION",
            "🛡  RISK ANALYTICS",
        ])
        with tab_pos:
            render_positions(metrics)
        with tab_hist:
            render_trade_history()
        with tab_d1:
            render_delta_one()
        with tab_comp:
            render_compensation(metrics)
        with tab_risk:
            # Mini risk breakdown
            st.markdown('<div class="ph">RISK BREAKDOWN</div>', unsafe_allow_html=True)
            if metrics["rows"]:
                risk_rows = []
                for r in metrics["rows"]:
                    q = fetch_quote(r["Ticker"])
                    chp = q.get("chg_pct", 0) if q else 0
                    dv01_est = r["MktVal"] * 0.0001
                    risk_rows.append({
                        "Ticker":        r["Ticker"],
                        "Mkt Val ($)":   f"${r['MktVal']:,.0f}",
                        "Weight %":      f"{r['MktVal']/metrics['gross_exposure']*100:.1f}%" if metrics["gross_exposure"] else "0%",
                        "Day Δ":         f"{chp:+.2f}%",
                        "1D P&L Est":    f"${r['MktVal']*chp/100:,.0f}",
                        "DV01 Est":      f"${dv01_est:,.0f}",
                    })
                st.dataframe(pd.DataFrame(risk_rows), use_container_width=True, hide_index=True)

                # Concentration
                st.markdown('<div class="ph" style="margin-top:6px">CONCENTRATION RISK</div>', unsafe_allow_html=True)
                if metrics["gross_exposure"] > 0:
                    for r in sorted(metrics["rows"], key=lambda x: abs(x["MktVal"]), reverse=True)[:5]:
                        pct = abs(r["MktVal"]) / metrics["gross_exposure"] * 100
                        bar = int(pct * 2.5)
                        col = "#ff3355" if pct > 30 else "#ffd700" if pct > 20 else "#00ff88"
                        st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;margin:2px 0;font-size:0.68rem">
  <span style="color:#e0e8f0;width:50px">{r['Ticker']}</span>
  <div style="flex:1;background:#0d1520;border-radius:2px;height:8px;overflow:hidden">
    <div style="width:{min(bar,250)}px;height:100%;background:{col};border-radius:2px"></div>
  </div>
  <span style="color:{col};width:45px;text-align:right">{pct:.1f}%</span>
</div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:#3a5f7a;font-size:0.72rem;padding:10px;text-align:center">'
                            '— NO POSITIONS TO ANALYZE —</div>', unsafe_allow_html=True)

    # RIGHT — Order Book + Execution Terminal
    with col_r:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        render_order_book()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        render_trade_terminal()
        st.markdown('</div>', unsafe_allow_html=True)

    # ─── FULL-WIDTH BOTTOM ROW ────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    col_compliance, col_shadow = st.columns([3, 2])

    with col_compliance:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        render_compliance(metrics)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_shadow:
        render_shadow_ledger()

    # ─── SIDEBAR ─────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙ SETTINGS")
        st.markdown("---")

        auto = st.checkbox("Auto-refresh (60s)", value=False, key="auto_refresh")
        if auto:
            import time as _time
            _time.sleep(60)
            st.rerun()

        st.markdown("---")
        st.markdown("**LIVE REFRESH**")
        refresh_opt = st.selectbox(
            "Refresh interval",
            ["5s", "10s", "15s", "30s", "60s"],
            index=2, key="refresh_sel"
        )
        interval_map = {"5s": 5_000, "10s": 10_000, "15s": 15_000, "30s": 30_000, "60s": 60_000}
        st.session_state["refresh_interval_ms"] = interval_map[refresh_opt]

        # Show refresh counter as heartbeat
        st.markdown(
            f'<div style="color:#3a5f7a;font-size:0.6rem;margin-top:4px">'
            f'<span class="live-dot"></span>CYCLE #{refresh_count} · {refresh_opt} interval</div>',
            unsafe_allow_html=True
        )

        st.markdown("---")
        st.markdown("**ACCOUNT CONTROLS**")
        if st.button("🔄 Reset Terminal", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

        if st.button("💾 Snapshot P&L", use_container_width=True):
            snap = {
                "timestamp": datetime.now().isoformat(),
                "nav": metrics["nav"],
                "total_pnl": metrics["total_pnl"],
                "positions": len(st.session_state.positions),
                "trades": len(st.session_state.trades),
            }
            st.success(f"P&L snapshot: {snap}")

        st.markdown("---")
        st.markdown("**SYSTEM INFO**")
        st.markdown(f"""
<div style="font-size:0.62rem;color:#3a5f7a;line-height:1.8">
  DATA: yfinance (60s cache)<br>
  COMMISSION: {COMMISSION_RATE*100:.1f}%<br>
  SLIPPAGE: 0–{MAX_SLIPPAGE_BPS}bps sqr-root model<br>
  VAR CONF: {VAR_CONFIDENCE*100:.0f}% · {VAR_HORIZON_DAYS}D horizon<br>
  VAR LIMIT: {VAR_LIMIT_PCT*100:.0f}% AUM<br>
  INITIAL CAPITAL: ${INITIAL_CAPITAL:,.0f}<br>
</div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("""
<div style="font-size:0.58rem;color:#3a5f7a;line-height:1.6;border:1px solid #1a2535;border-radius:2px;padding:6px">
⚠ <strong style="color:#ff355555">AVERTISSEMENT LÉGAL</strong><br>
Outil 100% éducatif et pédagogique. Aucune transaction réelle n'est effectuée. Le module Shadow Ledger
reproduit la fraude Kerviel/SocGen (2008) à des fins d'enseignement uniquement.
Ne constitue pas un conseil en investissement.
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# § 16 · ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()
