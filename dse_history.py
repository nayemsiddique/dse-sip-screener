"""Daily OHLCV history for one trading code.

Two sources, in order:

* **amarstock.com** — the JSON feed behind its own price chart. It reaches back
  to 2010 and the closes are split-adjusted, which is what makes a ten-year view
  possible at all.
* **dsebd.org's day-end archive** — used only when amarstock cannot be reached.
  DSE caps that archive at two years (asking for 2021 still returns nothing
  before today minus ~730 days) and its prices are unadjusted, so the chart
  quietly shortens to whatever the fallback can cover.

Kept free of Streamlit so it can be exercised headless; app.py wraps
`fetch_history` in Streamlit's cache.
"""

import json
import re
from datetime import date, datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

from dse import HEADERS, ca_bundle

# ---------------------------------------------------------------------------
# amarstock
# ---------------------------------------------------------------------------
AMAR_BASE = "https://www.amarstock.com"
AMAR_PAGE = AMAR_BASE + "/stock/{symbol}"
# amarstock hides its data routes behind hashed path segments that it keeps in
# its `common` script bundle. This is the one the price chart uses ("qbf"); if
# it is ever rotated, `_amar_data_path` reads the current one back out of the
# bundle rather than giving up.
AMAR_DATA_PATH = "data/5ee4d332a90e"
AMAR_FROM = "2010-01-01"

_amar_path_cache = AMAR_DATA_PATH


def _amar_session_headers(symbol):
    return {**HEADERS, "Referer": AMAR_PAGE.format(symbol=symbol),
            "Accept": "application/json, text/plain, */*"}


def _amar_data_path(symbol):
    """Re-reads the hashed data route out of amarstock's own script bundle."""
    page = requests.get(
        AMAR_PAGE.format(symbol=symbol), headers=HEADERS, timeout=20
    ).text
    bundle = re.search(r'src="([^"]*bundles/js/common\?v=[^"]+)"', page)
    if not bundle:
        raise ValueError("amarstock page carries no common bundle")
    script = requests.get(bundle.group(1), headers=HEADERS, timeout=20).text
    route = re.search(r'qbf:"([^"]+)"', script)
    if not route:
        raise ValueError("amarstock bundle carries no chart data route")
    return route.group(1).strip("/")


def _amar_fetch(symbol, path):
    url = f"{AMAR_BASE}/{path}/?scrip={symbol}&cycle=Day1&dtFrom={AMAR_FROM}"
    response = requests.get(url, headers=_amar_session_headers(symbol), timeout=30)
    response.raise_for_status()
    return response.json()


def _from_amarstock(symbol):
    """Split-adjusted daily bars from 2010 on, oldest first."""
    global _amar_path_cache
    try:
        rows = _amar_fetch(symbol, _amar_path_cache)
    except Exception:
        # A rotated route, not an outage: find the current one and try once more.
        _amar_path_cache = _amar_data_path(symbol)
        rows = _amar_fetch(symbol, _amar_path_cache)

    if not isinstance(rows, list):
        raise ValueError("amarstock returned no series")

    bars = []
    for row in rows:
        close = row.get("Close")
        high, low = row.get("High"), row.get("Low")
        if not close or not high or not low:
            continue  # a day the scrip did not trade
        stamp = row.get("DateEpoch")
        if not stamp:
            continue
        bars.append({
            "date": datetime.fromtimestamp(stamp / 1000, timezone.utc)
                            .strftime("%Y-%m-%d"),
            "open": row.get("Open") or close,
            "high": high,
            "low": low,
            "close": close,
            "volume": row.get("Volume") or 0.0,
        })
    if not bars:
        raise ValueError("amarstock returned an empty series")
    bars.sort(key=lambda b: b["date"])
    return bars


# ---------------------------------------------------------------------------
# dsebd.org day-end archive (fallback)
# ---------------------------------------------------------------------------
ARCHIVE_URL = (
    "https://www.dsebd.org/day_end_archive.php"
    "?startDate={start}&endDate={end}&inst={symbol}&archive=data"
)

# DSE's own date pickers on that page are clamped to two years back, and the
# backend honours the same limit, so there is no point asking for more.
MAX_DAYS = 730

# Column order of the result table, after the leading row-number cell:
#   DATE, TRADING CODE, LTP*, HIGH, LOW, OPENP*, CLOSEP*, YCP, TRADE,
#   VALUE (mn), VOLUME
COL = {"date": 1, "high": 4, "low": 5, "open": 6, "close": 7, "volume": 11}


def _num(text):
    try:
        return float(text.replace(",", "").strip())
    except (AttributeError, ValueError):
        return None


def _archive_table(soup):
    """The day-end table, picked out of the page's ~390 ticker tables."""
    for table in soup.find_all("table"):
        header = table.find("tr")
        if header and "TRADING CODE" in header.get_text(" ", strip=True).upper():
            return table
    return None


def _from_dse(symbol, today=None):
    end = today or date.today()
    start = end - timedelta(days=MAX_DAYS)
    response = requests.get(
        ARCHIVE_URL.format(start=start.isoformat(), end=end.isoformat(), symbol=symbol),
        headers=HEADERS,
        timeout=30,
        verify=ca_bundle(),
    )
    response.raise_for_status()

    table = _archive_table(BeautifulSoup(response.content, "html.parser"))
    if table is None:
        raise ValueError("DSE returned no day-end archive table")

    bars = []
    for row in table.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
        if len(cells) <= COL["volume"] or not cells[COL["date"]][:4].isdigit():
            continue  # header, footnote, or a short malformed row

        bar = {"date": cells[COL["date"]]}
        for key in ("open", "high", "low", "close", "volume"):
            bar[key] = _num(cells[COL[key]])
        if not bar["close"] or not bar["high"] or not bar["low"]:
            continue
        if not bar["open"]:
            bar["open"] = bar["close"]
        bar["volume"] = bar["volume"] or 0.0
        bars.append(bar)

    if not bars:
        raise ValueError(f"DSE has no day-end history for {symbol}")
    bars.reverse()  # the archive is newest first; charts want oldest first
    return bars


# ---------------------------------------------------------------------------
SOURCES = [
    ("amarstock · split-adjusted", _from_amarstock),
    ("dsebd.org day-end · last 2 years", _from_dse),
]


def fetch_history(symbol):
    """Daily bars for `symbol`, oldest first.

    Returns (bars, source_label, error). Each bar is a dict of
    date/open/high/low/close/volume.
    """
    symbol = (symbol or "").strip().upper()
    problems = []
    for label, source in SOURCES:
        try:
            return source(symbol), label, None
        except Exception as e:
            problems.append(f"{label.split(' ·')[0]}: {e}")
    return [], None, "Price history unavailable — " + "; ".join(problems)
