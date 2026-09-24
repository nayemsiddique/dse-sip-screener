"""Backup source: the redesigned www.dsebd.org.

dse.py scrapes old.dsebd.org, which still serves the site this app was built
against. This module reads the same figures from the new Next.js site and is
only called when the old site is unreachable, so it returns exactly the shapes
the old-site functions do and the rest of the app cannot tell them apart.

The new site's robots.txt disallows all automated access, so it is kept as a
fallback rather than the primary source, and the live price feed is held for
FEED_TTL seconds however often the price tile polls.

Two kinds of source:

* ``/api/live/*`` — JSON endpoints the site's own pages fetch (prices,
  instrument list, day-end archive, news).
* ``/company/{CODE}`` — has no endpoint. The page is rendered on the server and
  embeds a ``"company":{...}`` object in its React Server Components payload,
  which is decoded here.

These are undocumented internals and may change without notice; every failure
surfaces as dse.Unreachable so nothing broken is ever cached.
"""

import calendar
import json
import re
import time
from datetime import date, timedelta

import requests

import dse

BASE = "https://www.dsebd.org"
API = BASE + "/api/live"
COMPANY_URL = BASE + "/company/{symbol}"

# The site refreshes its live data about every 15 seconds; polling faster only
# re-downloads the same 38 KB.
FEED_TTL = 15


def _get(url, timeout, what):
    """GET through the shared session, translating failures to Unreachable."""
    try:
        response = dse.session().get(url, timeout=timeout)
        response.raise_for_status()
        return response
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        raise dse.Unreachable(f"www.dsebd.org did not answer with {what}.")
    except requests.exceptions.HTTPError as e:
        raise dse.Unreachable(
            f"www.dsebd.org returned HTTP {e.response.status_code} for {what}."
        )


def _json(url, timeout, what):
    try:
        return _get(url, timeout, what).json()
    except ValueError:
        raise dse.Unreachable(f"www.dsebd.org sent unreadable data for {what}.")


# -----------------------------------------------------------------------------
# INSTRUMENTS AND LIVE PRICES
# -----------------------------------------------------------------------------
def fetch_symbols():
    """Every trading code in the day-end archive's instrument list, sorted."""
    data = _json(API + "/data-archive/instruments", dse.LISTING_TIMEOUT, "the trading-code list")
    symbols = sorted({str(c).strip().upper() for c in data.get("instruments") or [] if c})
    if not symbols:
        return [], "DSE returned no trading codes."
    return symbols, None


_feed = {"at": 0.0, "value": None}


def fetch_quotes():
    """Last trade price per instrument, as dse.fetch_quotes returns it.

    /prices is columnar: a `cols` header plus rows of bare values.
    """
    if _feed["value"] is not None and time.monotonic() - _feed["at"] < FEED_TTL:
        return _feed["value"]
    try:
        data = _json(API + "/prices", dse.QUOTES_TIMEOUT, "the price feed")
    except dse.Unreachable as e:
        return {}, None, f"Quote feed unavailable: {e}"

    cols = data.get("cols") or []
    if "code" not in cols or "ltp" not in cols:
        return {}, None, "Quote feed changed shape on www.dsebd.org."
    code_at, ltp_at = cols.index("code"), cols.index("ltp")

    prices = {}
    for row in data.get("rows") or []:
        try:
            price = float(row[ltp_at])
        except (IndexError, TypeError, ValueError):
            continue
        if price > 0:
            prices[str(row[code_at])] = price

    session = data.get("session") or {}
    stamp = session.get("date")
    if not prices:
        return {}, stamp, "Quote feed returned no prices."
    _feed.update(at=time.monotonic(), value=(prices, stamp, None))
    return prices, stamp, None


# -----------------------------------------------------------------------------
# COMPANY PAGE
# -----------------------------------------------------------------------------
# Each flight chunk is pushed as self.__next_f.push([1,"<json string>"]).
FLIGHT_CHUNK = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)')


def _flight(html):
    """The page's concatenated React Server Components payload."""
    return "".join(json.loads('"' + chunk + '"') for chunk in FLIGHT_CHUNK.findall(html))


def _clean(value):
    """Swaps the payload's "$undefined" placeholder for None, recursively."""
    if value == "$undefined":
        return None
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


def _company_object(html):
    """The embedded company record, or None when the code is unknown."""
    flight = _flight(html)
    marker = flight.find('"company":{"code":')
    if marker < 0:
        return None  # an unknown code renders "company":"$undefined"
    start = marker + len('"company":')
    record, _ = json.JSONDecoder().raw_decode(flight[start:])
    return _clean(record)


def _first(*values):
    return next((v for v in values if isinstance(v, (int, float))), None)


def _mn(value):
    return value / 1e6 if isinstance(value, (int, float)) else None


def _count(value):
    """Formats a count the way the old page printed it, e.g. '170,012'."""
    return f"{value:,.0f}" if isinstance(value, (int, float)) else None


def _range(low, high):
    """'217.10 - 218.00', as the old page printed its ranges."""
    if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
        return None
    return f"{low:.2f} - {high:.2f}"


# The new site abbreviates sector names; these are the old site's spellings,
# matched by looking the same companies up on both.
SECTORS = {
    "Ceramic": "Ceramics Sector",
    "CorpBond": "Corporate Bond",
    "Financial In": "Financial Institutions",
    "FoodAllied": "Food & Allied",
    "FuelPower": "Fuel & Power",
    "IT": "IT Sector",
    "Misc": "Miscellaneous",
    "MutFund": "Mutual Funds",
    "PaperPrint": "Paper & Printing",
    "PharmaChem": "Pharmaceuticals & Chemicals",
    "ServRealEst": "Services & Real Estate",
    "Tannery": "Tannery Industries",
    "Telecom": "Telecommunication",
    "TravelLeisur": "Travel & Leisure",
}

MONTHS = {name.lower(): number for number, name in enumerate(calendar.month_name) if name}


def _year_end(month):
    """'June' -> '30-Jun', the old page's day-month form."""
    number = MONTHS.get((month or "").strip().lower())
    if not number:
        return month
    last_day = calendar.monthrange(2001, number)[1]  # a non-leap year, as DSE uses
    return f"{last_day}-{calendar.month_abbr[number]}"


def fetch_company(symbol):
    """One company as the dict dse.fetch_company builds from the old page."""
    symbol = symbol.strip().upper()
    response = _get(
        COMPANY_URL.format(symbol=symbol), dse.COMPANY_TIMEOUT, f"{symbol}'s company page"
    )
    try:
        c = _company_object(response.text)
    except ValueError:
        raise dse.Unreachable(f"www.dsebd.org sent an unreadable page for {symbol}.")
    if c is None:
        return None, f"Trading Code '{symbol}' not found on DSE."

    d = {"symbol": symbol, "name": c.get("name") or symbol}

    # --- Market snapshot -----------------------------------------------------
    d["ltp"] = c.get("price")
    d["closing_price"] = None  # the new page carries no separate close
    d["yesterday_close"] = c.get("prevClose")
    d["opening_price"] = c.get("open")
    d["day_range"] = _range(c.get("low"), c.get("high"))
    d["week52_range"] = _range(c.get("weekLow52"), c.get("weekHigh52"))
    d["volume"] = _count(c.get("volume"))
    d["trades"] = _count(c.get("trades"))
    d["turnover_mn"] = None  # only in the live feed, not the company record
    d["market_cap_mn"] = _mn(c.get("marketCap"))
    d["free_float_cap_mn"] = _mn(c.get("freeFloatMarketCap"))
    d["last_update"] = c.get("lastPriceUpdate")
    d["change_abs"] = c.get("change")
    d["change_pct"] = c.get("changePct")

    # --- Company profile ------------------------------------------------------
    d["sector"] = SECTORS.get(c.get("sector"), c.get("sector"))
    d["category"] = (c.get("category") or "").strip().upper() or None
    d["listing_year"] = str(c["listingYear"]) if c.get("listingYear") else None
    d["year_end"] = _year_end(c.get("yearEnd"))
    d["face_value"] = c.get("faceValue") or 10.0
    d["authorized_cap_mn"] = c.get("authorizedCapital")  # already in mn
    d["paid_up_cap_mn"] = _mn(c.get("paidUpCapital"))
    # No share count in the record; paid-up capital is shares x face value.
    paid_up = c.get("paidUpCapital")
    d["total_shares"] = paid_up / d["face_value"] if isinstance(paid_up, (int, float)) else None
    d["reserve_mn"] = c.get("reserveWithoutOci")

    # --- Debt -------------------------------------------------------------------
    # The new site drops a zero loan, and the whole block when both are zero,
    # where the old page printed 0.
    loans = c.get("loanStatus") or {}
    d["short_term_loan_mn"] = loans.get("shortTerm") or 0.0
    d["long_term_loan_mn"] = loans.get("longTerm") or 0.0

    # --- P/E: latest column of the unaudited basic-EPS table, as on the old page
    pe_table = c.get("peUnauditedTable") or {}
    basic = [v for v in pe_table.get("basic") or [] if isinstance(v, (int, float))]
    trailing = [v for v in pe_table.get("trailing") or [] if isinstance(v, (int, float))]
    d["pe_ratio"] = basic[-1] if basic else (trailing[-1] if trailing else None)

    # --- EPS / NAV: latest year, same column preference as the old table ---------
    years = [y for y in c.get("multiYearFinancials") or [] if y.get("year")]
    latest = max(years, key=lambda y: y["year"]) if years else None
    d["financial_year"] = str(latest["year"]) if latest else None
    if latest:
        d["eps"] = _first(
            latest.get("epsBasicOriginal"), latest.get("epsBasicRestated"),
            latest.get("epsDiluted"), latest.get("epsContBasicOriginal"),
            latest.get("epsContBasicRestated"), latest.get("epsContDiluted"),
        )
        d["nav"] = _first(
            latest.get("navOriginal"), latest.get("navRestated"), latest.get("navDiluted")
        )
        d["profit_mn"] = _first(
            latest.get("pco"), latest.get("profitForYear"), latest.get("comprehensive")
        )
    else:
        d["eps"] = d["nav"] = d["profit_mn"] = None

    # --- Dividend: the most recent cash dividend declared ----------------------
    # Years that paid no cash are skipped, as the old page's "Cash Dividend"
    # line only lists paying years; this keeps both sources scoring alike.
    dividends = [x for x in c.get("dividendHistory") or [] if x.get("year") and x.get("cash")]
    recent = max(dividends, key=lambda x: x["year"]) if dividends else None
    d["cash_dividend_pct"] = recent.get("cash") if recent else None
    if d["cash_dividend_pct"] is not None and d["ltp"]:
        d["dividend_yield"] = (
            d["cash_dividend_pct"] / 100.0 * d["face_value"] / d["ltp"] * 100.0
        )
    else:
        d["dividend_yield"] = None

    d["nocfps"] = None
    d["nocfps_eps"] = None
    d["nocfps_period"] = None
    d["nocfps_as_of"] = None

    dse.remember_name(symbol, d["name"])
    return d, None


# -----------------------------------------------------------------------------
# DAY-END HISTORY AND NEWS
# -----------------------------------------------------------------------------
def fetch_history(symbol, days=730):
    """Daily bars, oldest first, as dse_history's sources return them."""
    end = date.today()
    start = end - timedelta(days=days)
    data = _json(
        f"{API}/data-archive/day-end?from={start.isoformat()}&to={end.isoformat()}&inst={symbol}",
        (8, 30),
        f"{symbol}'s day-end archive",
    )
    bars = []
    for row in data.get("rows") or []:
        close, high, low = row.get("closep"), row.get("high"), row.get("low")
        if not close or not high or not low:
            continue
        bars.append({
            "date": row.get("date"),
            "open": row.get("openp") or close,
            "high": high,
            "low": low,
            "close": close,
            "volume": row.get("volume") or 0.0,
        })
    if not bars:
        raise ValueError(f"DSE has no day-end history for {symbol}")
    bars.sort(key=lambda b: b["date"])
    return bars


def fetch_news(symbol, start, end):
    """News items shaped like dse_news._parse_items output, plus the URL."""
    url = f"{API}/news?from={start.isoformat()}&to={end.isoformat()}&code={symbol}"
    data = _json(url, dse.NEWS_TIMEOUT, "the news archive")
    items = [
        {
            "code": row.get("code") or "",
            "news": row.get("body") or "",
            "title": row.get("summary") or "",
            "post_date": row.get("filedAt") or "",
        }
        for row in data.get("rows") or []
    ]
    return items, url
