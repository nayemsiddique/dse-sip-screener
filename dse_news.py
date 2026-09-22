"""Cash-flow figures from DSE's news archive.

displayCompany.php carries no cash-flow line, but the quarterly disclosures
DSE publishes under old_news.php quote NOCFPS (and the EPS for the same
period) in prose:

    EPS was Tk. 11.45 for January-June 2026 as against Tk. 10.02 ...;
    NOCFPS was Tk. 22.27 for January-June 2026 as against Tk. 19.80 ...

This module pulls the latest such disclosure for one trading code and reads
both figures out of it, so cash conversion compares like with like instead of
mixing a quarterly NOCFPS with the annual EPS from the company page.
"""

import re
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

import dse

NEWS_URL = (
    "https://www.dsebd.org/old_news.php"
    "?startDate={start}&endDate={end}&criteria=4&archive=news&inst={symbol}"
)

# "Tk. (0.18)" is how the disclosures write a negative figure.
_MONEY = r"\(?-?[\d,]+(?:\.\d+)?\)?"
NOCFPS_RE = re.compile(
    rf"NOCFPS\s+was\s+Tk\.?\s*({_MONEY})\s+for\s+(.+?)\s+as\s+against", re.I
)
EPS_RE = re.compile(
    rf"EPS\s+was\s+Tk\.?\s*({_MONEY})\s+for\s+(.+?)\s+as\s+against", re.I
)


def _money(text):
    """'(0.18)' -> -0.18, '22.27' -> 22.27."""
    cleaned = text.strip().replace(",", "")
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -value if negative else value


def _parse_items(html):
    """The archive is one long table of repeating label/value rows."""
    soup = BeautifulSoup(html, "html.parser")
    # Pick by content, not size: the page also carries the all-market ticker,
    # which has far more rows than a single company's news list.
    table = next(
        (
            t
            for t in soup.find_all("table")
            if "Trading Code:" in t.get_text() and "Post Date:" in t.get_text()
        ),
        None,
    )
    if table is None:
        return []

    items, current = [], None
    for row in table.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        key, value = cells[0].rstrip(":").strip().lower(), cells[1]
        if key == "trading code":
            if current:
                items.append(current)
            current = {"code": value, "news": "", "title": "", "post_date": ""}
        elif current is None:
            continue
        elif key == "news title":
            current["title"] = value
        elif key == "news":
            current["news"] = value
        elif key == "post date":
            current["post_date"] = value
    if current:
        items.append(current)
    return items


def fetch_cashflow(symbol, days=400):
    """Latest disclosed NOCFPS for `symbol`, with the EPS of the same period.

    Returns (payload, None) or (None, reason). A company that simply has not
    disclosed one in the window is a reason, not an error.
    """
    symbol = symbol.strip().upper()
    end = date.today()
    start = end - timedelta(days=days)
    url = NEWS_URL.format(start=start.isoformat(), end=end.isoformat(), symbol=symbol)

    try:
        response = dse.session().get(url, timeout=dse.NEWS_TIMEOUT)
        response.raise_for_status()
    except Exception as e:
        return None, f"Could not reach the DSE news archive: {e}"

    candidates = []
    for item in _parse_items(response.text):
        if item["code"].strip().upper() != symbol:
            continue
        match = NOCFPS_RE.search(item["news"])
        if not match:
            continue
        nocfps = _money(match.group(1))
        if nocfps is None:
            continue
        period = match.group(2).strip()

        # Take the EPS quoted for the same period in the same disclosure; these
        # items also quote a quarter-only EPS, which must not be paired with a
        # cumulative NOCFPS.
        eps = None
        for eps_match in EPS_RE.finditer(item["news"]):
            if eps_match.group(2).strip().lower() == period.lower():
                eps = _money(eps_match.group(1))
                break

        candidates.append(
            {
                "nocfps": nocfps,
                "eps": eps,
                "period": period,
                "post_date": item["post_date"],
                "title": item["title"],
                "source_url": url,
            }
        )

    if not candidates:
        return None, f"No NOCFPS disclosure for {symbol} in the last {days} days."

    candidates.sort(key=lambda c: c["post_date"], reverse=True)
    return candidates[0], None
