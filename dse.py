"""Scraping and scoring for dsebd.org company pages.

Kept free of Streamlit so it can be exercised headless; app.py wraps the two
entry points (`fetch_symbols`, `fetch_company`) in Streamlit's cache.
"""

import json
import os
import re
import tempfile

import certifi
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://www.dsebd.org"
COMPANY_URL = BASE + "/displayCompany.php?name={symbol}"
LISTING_URL = BASE + "/company_listing.php"
# Plain-text feed of every instrument's last trade price: ~6 KB and ~0.04s,
# against ~330 KB for a company page. This is what intraday polling hits.
# quotes_script.php only 302-redirects here, so asking for the file directly
# halves the round trips — the polling fragment runs every 5 seconds.
QUOTES_URL = BASE + "/datafile/quotes.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

HERE = os.path.dirname(os.path.abspath(__file__))

# dsebd.org serves an incomplete TLS chain: it sends the leaf certificate and
# the Sectigo root R46, but omits the "Sectigo Public Server Authentication
# CA DV R36" intermediate. certifi trusts the root, so verification still fails
# with CERTIFICATE_VERIFY_FAILED. We build a CA bundle of certifi + that
# intermediate rather than disabling verification.
INTERMEDIATE_PEM = os.path.join(HERE, "certs_dsebd_intermediate.pem")

# DSE publishes no company names in any listing page, so names are learned one
# at a time as companies are visited and remembered here for the sidebar.
NAME_CACHE = os.path.join(HERE, "symbol_names.json")

DEFAULT_CODE = "SQURPHARMA"


class Unreachable(RuntimeError):
    """dsebd.org did not answer after the session's retries.

    Raised rather than returned so `st.cache_data` never stores it: Streamlit
    caches return values, not exceptions. A returned error would be frozen in
    for the whole TTL — half an hour for a company page, twelve hours for the
    code list — which turned one blip into a symbol that looked permanently
    broken while every other symbol worked.
    """

_ca_bundle_path = None


def ca_bundle():
    """Path to certifi's bundle plus the intermediate DSE fails to send."""
    global _ca_bundle_path
    if _ca_bundle_path:
        return _ca_bundle_path
    if not os.path.exists(INTERMEDIATE_PEM):
        _ca_bundle_path = certifi.where()
        return _ca_bundle_path

    bundle = tempfile.NamedTemporaryFile(
        mode="wb", suffix=".pem", delete=False, prefix="dse_ca_"
    )
    with open(certifi.where(), "rb") as f:
        bundle.write(f.read())
    bundle.write(b"\n")
    with open(INTERMEDIATE_PEM, "rb") as f:
        bundle.write(f.read())
    bundle.close()
    _ca_bundle_path = bundle.name
    return _ca_bundle_path


# -----------------------------------------------------------------------------
# HTTP SESSION
# -----------------------------------------------------------------------------
# dsebd.org drops connections often enough that a single attempt is not a fair
# test of whether it is up: a blip surfaced as a full-page "Scraping Error" with
# ConnectTimeoutError. Retries with backoff absorb that, and the pooled session
# also saves a TCP and TLS handshake per call.
_session = None

# Timeouts are (connect, read). Connect is kept short because a dead handshake
# is the failure being retried; three attempts at 8s beat one at 20s.
COMPANY_TIMEOUT = (8, 25)
LISTING_TIMEOUT = (8, 25)
QUOTES_TIMEOUT = (5, 10)
NEWS_TIMEOUT = (8, 45)


def session():
    """Shared session: retries, connection pooling, and the DSE CA bundle."""
    global _session
    if _session is not None:
        return _session
    retry = Retry(
        total=3,
        connect=3,
        read=2,
        backoff_factor=0.6,          # sleeps 0s, 1.2s, 2.4s between attempts
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=8)
    _session = requests.Session()
    _session.mount("https://", adapter)
    _session.mount("http://", adapter)
    _session.headers.update(HEADERS)
    # certifi plus the intermediate DSE omits; a superset of certifi, so it is
    # equally valid for the non-DSE hosts that share this session.
    _session.verify = ca_bundle()
    return _session


# -----------------------------------------------------------------------------
# HTML HELPERS
# -----------------------------------------------------------------------------
def _to_float(text):
    """Parses a DSE table cell into a float, or None for '-' / blank / junk."""
    if text is None:
        return None
    cleaned = text.replace(",", "").replace("%", "").strip()
    return float(cleaned) if re.match(r"^-?\d+(\.\d+)?$", cleaned) else None


def _cell_after(scope, label):
    """Text of the cell following the one whose text equals `label`."""
    for row in scope.find_all("tr"):
        cells = row.find_all(["td", "th"])
        for i, cell in enumerate(cells[:-1]):
            if cell.get_text(" ", strip=True).lower() == label.lower():
                return cells[i + 1].get_text(" ", strip=True)
    return None


def _row_starting_with(scope, prefix):
    """Cell texts of the first row whose first cell starts with `prefix`."""
    for row in scope.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
        if cells and cells[0].lower().startswith(prefix.lower()):
            return cells
    return None


def _last_numeric(cells):
    """Right-most parseable number in a row of cells."""
    for text in reversed(cells[1:]):
        value = _to_float(text)
        if value is not None:
            return value
    return None


def _latest_year_row(scope):
    """Final data row of the 'Year / EPS / NAV Per Share' history table."""
    for table in scope.find_all("table"):
        header = table.find("tr")
        if not header or "NAV Per Share" not in header.get_text(" ", strip=True):
            continue
        year_rows = [
            [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
            for row in table.find_all("tr")
        ]
        year_rows = [r for r in year_rows if r and re.match(r"^(19|20)\d{2}$", r[0])]
        if year_rows:
            return year_rows[-1]
    return None


# -----------------------------------------------------------------------------
# NAME CACHE
# -----------------------------------------------------------------------------
def load_names():
    try:
        with open(NAME_CACHE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


# Treasury bonds have no company name on DSE; their code encodes the tenor and
# maturity, e.g. TB20Y0934 is a 20-year BGTB maturing 09/2034.
BOND_CODE = re.compile(r"^TB(\d+)Y(\d{2})(\d{2})$")


def display_name(symbol, names=None):
    """Label for a trading code: the cached company name, or a derived one."""
    names = load_names() if names is None else names
    if symbol in names:
        return names[symbol]
    bond = BOND_CODE.match(symbol or "")
    if bond:
        years, month, year = bond.groups()
        return f"{years}-year BGTB, matures {month}/20{year}"
    return None


def save_names(names):
    """Writes the whole cache at once; used by build_names.py."""
    try:
        with open(NAME_CACHE, "w", encoding="utf-8") as f:
            json.dump(names, f, indent=1, sort_keys=True, ensure_ascii=False)
        return True
    except OSError:
        return False


def remember_name(symbol, name):
    if not symbol or not name or name == symbol:
        return
    names = load_names()
    if names.get(symbol) == name:
        return
    names[symbol] = name
    try:
        with open(NAME_CACHE, "w", encoding="utf-8") as f:
            json.dump(names, f, indent=1, sort_keys=True)
    except OSError:
        pass  # a read-only deploy still works, it just never learns names


# -----------------------------------------------------------------------------
# SCRAPERS
# -----------------------------------------------------------------------------
def fetch_symbols():
    """Every trading code listed on dsebd.org, sorted.

    company_listing.php links each instrument as displayCompany.php?name=CODE.
    The page also embeds the scrolling all-market ticker, whose links carry a
    price and a percentage in their text, so those are filtered out.
    """
    try:
        response = session().get(LISTING_URL, timeout=LISTING_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        scope = soup.find(id="section-to-print") or soup

        symbols = set()
        for link in scope.find_all("a"):
            href = link.get("href") or ""
            if "displayCompany.php?name=" not in href:
                continue
            if "%" in link.get_text():  # ticker entry, not a listing row
                continue
            code = href.split("name=")[1].split("&")[0].strip().upper()
            if code:
                symbols.add(code)

        if symbols:
            return sorted(symbols), None
        return [], "DSE returned no trading codes."
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        raise Unreachable("dsebd.org did not answer with the trading-code list.")
    except Exception as e:
        return [], f"Could not load the trading-code list: {e}"


QUOTE_LINE = re.compile(r"^\s*([A-Z0-9()\-.]+)\s+([\d,]+\.?\d*)\s*$")
QUOTE_STAMP = re.compile(r"Date:\s*([\d-]+)\s+Time:\s*([\d:]+)")


def fetch_quotes():
    """Last trade price for every instrument, from DSE's text quote feed.

    Returns (prices, stamp, error). `stamp` is DSE's own "date time" header.
    Instruments that have not traded come through as 0.0 and are dropped.
    """
    try:
        response = session().get(QUOTES_URL, timeout=QUOTES_TIMEOUT)
        response.raise_for_status()
    except Exception as e:
        return {}, None, f"Quote feed unavailable: {e}"

    text = response.text
    prices = {}
    for line in text.splitlines():
        match = QUOTE_LINE.match(line.strip())
        if not match:
            continue
        price = float(match.group(2).replace(",", ""))
        if price > 0:
            prices[match.group(1)] = price

    stamp = QUOTE_STAMP.search(text)
    stamp_text = " ".join(stamp.groups()) if stamp else None
    if not prices:
        return {}, stamp_text, "Quote feed returned no prices."
    return prices, stamp_text, None


def fetch_company(symbol):
    """Scrapes one company page into a flat dict of figures."""
    symbol = symbol.strip().upper()

    try:
        response = session().get(
            COMPANY_URL.format(symbol=symbol), timeout=COMPANY_TIMEOUT
        )
        if response.status_code != 200:
            return None, f"Failed to connect to DSE (Status Code: {response.status_code})"

        soup = BeautifulSoup(response.content, "html.parser")

        # Everything about the company lives inside the printable section; the
        # rest of the page is the scrolling all-market ticker, which would
        # otherwise poison every label lookup.
        scope = soup.find(id="section-to-print") or soup

        heading = scope.find("h2", class_="BodyHead")
        heading_text = heading.get_text(" ", strip=True) if heading else ""
        if "company name" not in heading_text.lower():
            return None, f"Trading Code '{symbol}' not found on DSE."

        d = {"symbol": symbol}
        d["name"] = re.sub(r"^\s*Company Name\s*:\s*", "", heading_text).strip() or symbol

        # --- Market snapshot -------------------------------------------------
        d["ltp"] = _to_float(_cell_after(scope, "Last Trading Price"))
        d["closing_price"] = _to_float(_cell_after(scope, "Closing Price"))
        d["yesterday_close"] = _to_float(_cell_after(scope, "Yesterday's Closing Price"))
        d["opening_price"] = _to_float(_cell_after(scope, "Opening Price"))
        d["day_range"] = _cell_after(scope, "Day's Range")
        d["week52_range"] = _cell_after(scope, "52 Weeks' Moving Range")
        d["volume"] = _cell_after(scope, "Day's Volume (Nos.)")
        d["trades"] = _cell_after(scope, "Day's Trade (Nos.)")
        d["turnover_mn"] = _to_float(_cell_after(scope, "Day's Value (mn)"))
        d["market_cap_mn"] = _to_float(_cell_after(scope, "Market Capitalization (mn)"))
        d["free_float_cap_mn"] = _to_float(_cell_after(scope, "Free Float Market Cap. (mn)"))
        d["last_update"] = _cell_after(scope, "Last Update")

        # "Change*" reads like "-0.5 -0.21%" — absolute move then percentage.
        change = _cell_after(scope, "Change*") or ""
        change_match = re.match(r"\s*(-?[\d.]+)\s+(-?[\d.]+)\s*%", change)
        d["change_abs"] = float(change_match.group(1)) if change_match else None
        d["change_pct"] = float(change_match.group(2)) if change_match else None

        # --- Company profile --------------------------------------------------
        d["sector"] = _cell_after(scope, "Sector")
        d["category"] = (_cell_after(scope, "Market Category") or "").strip().upper() or None
        d["listing_year"] = _cell_after(scope, "Listing Year")
        d["year_end"] = _cell_after(scope, "Year End")
        d["face_value"] = _to_float(_cell_after(scope, "Face/par Value")) or 10.0
        d["authorized_cap_mn"] = _to_float(_cell_after(scope, "Authorized Capital (mn)"))
        d["paid_up_cap_mn"] = _to_float(_cell_after(scope, "Paid-up Capital (mn)"))
        d["total_shares"] = _to_float(
            _cell_after(scope, "Total No. of Outstanding Securities")
        )
        d["reserve_mn"] = _to_float(
            _cell_after(scope, "Reserve & Surplus without OCI (mn)")
        )

        # --- Debt (from the loan-status block) ---------------------------------
        d["short_term_loan_mn"] = _to_float(_cell_after(scope, "Short-term loan (mn)"))
        d["long_term_loan_mn"] = _to_float(_cell_after(scope, "Long-term loan (mn)"))

        # --- P/E: right-most (most recent) column of the daily P/E table --------
        pe_row = _row_starting_with(scope, "Current P/E Ratio using Basic EPS")
        d["pe_ratio"] = _last_numeric(pe_row) if pe_row else None
        if d["pe_ratio"] is None:
            trailing = _row_starting_with(scope, "Trailing P/E Ratio")
            d["pe_ratio"] = _last_numeric(trailing) if trailing else None

        # --- EPS / NAV: last row of the annual history table --------------------
        # Layout after the Year cell is 12 columns:
        #   0-2  EPS (Basic Original, Basic Restated, Diluted)
        #   3-5  EPS continuing ops (Basic Original, Basic Restated, Diluted)
        #   6-8  NAV Per Share (Original, Restated, Diluted)
        #   9-11 PCO, Profit for the year, TCI
        year_row = _latest_year_row(scope)
        d["financial_year"] = year_row[0] if year_row else None
        if year_row and len(year_row) >= 10:
            values = year_row[1:]
            d["eps"] = next((v for v in (_to_float(x) for x in values[0:6]) if v is not None), None)
            d["nav"] = next((v for v in (_to_float(x) for x in values[6:9]) if v is not None), None)
            d["profit_mn"] = next(
                (v for v in (_to_float(x) for x in values[9:12]) if v is not None), None
            )
        else:
            d["eps"] = d["nav"] = d["profit_mn"] = None

        # --- Dividend: "215% 2025, 330% 2024, ..." -> most recent percentage -----
        cash_div = _cell_after(scope, "Cash Dividend")
        div_match = re.search(r"([\d.]+)\s*%", cash_div) if cash_div else None
        d["cash_dividend_pct"] = float(div_match.group(1)) if div_match else None

        # Dividend is declared on face value (Tk 10 par); convert to yield on price.
        if d["cash_dividend_pct"] is not None and d["ltp"]:
            d["dividend_yield"] = (
                d["cash_dividend_pct"] / 100.0 * d["face_value"] / d["ltp"] * 100.0
            )
        else:
            d["dividend_yield"] = None

        # NOCFPS is NOT published on displayCompany.php for any symbol. It is
        # quoted in the quarterly disclosures DSE posts to its news archive;
        # dse_news.fetch_cashflow fills these in, and they stay None when the
        # company has not disclosed one.
        d["nocfps"] = None
        d["nocfps_eps"] = None
        d["nocfps_period"] = None
        d["nocfps_as_of"] = None

        remember_name(symbol, d["name"])
        return d, None

    except requests.exceptions.SSLError as e:
        return None, (
            "TLS verification failed for dsebd.org. The site serves an incomplete "
            "certificate chain; make sure certs_dsebd_intermediate.pem sits next "
            f"to dse.py. Details: {e}"
        )
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # Already retried three times by the session, so say so plainly rather
        # than surfacing a urllib3 traceback the reader cannot act on.
        raise Unreachable(
            f"dsebd.org did not answer for {symbol} after 3 attempts. The site "
            "drops connections regularly; this usually clears on its own."
        )
    except Exception as e:
        return None, f"Scraping Error: {e}"


# -----------------------------------------------------------------------------
# FRAMEWORK EVALUATION
# -----------------------------------------------------------------------------
PASS, FAIL, NODATA = "Pass", "Fail", "No data"


def evaluate(d):
    """Scores the long-term framework against one scraped company.

    A criterion whose inputs are missing is reported as "No data" and dropped
    from the denominator instead of counting as a failure.
    """
    eps, nav, ltp = d.get("eps"), d.get("nav"), d.get("ltp")
    nocfps, pe = d.get("nocfps"), d.get("pe_ratio")
    shares, face = d.get("total_shares"), d.get("face_value") or 10.0

    roe = (eps / nav) * 100 if (eps is not None and nav) else None

    equity_mn = (nav * shares / 1e6) if (nav and shares) else None
    short_loan, long_loan = d.get("short_term_loan_mn"), d.get("long_term_loan_mn")
    debt_mn = None
    if short_loan is not None or long_loan is not None:
        debt_mn = (short_loan or 0.0) + (long_loan or 0.0)
    debt_equity = (debt_mn / equity_mn) if (debt_mn is not None and equity_mn) else None

    div_pct = d.get("cash_dividend_pct")
    payout = (div_pct / 100.0 * face / eps * 100.0) if (div_pct is not None and eps and eps > 0) else None

    # Pair NOCFPS with the EPS disclosed for the same period where we have it;
    # falling back to the annual EPS would compare a quarter against a year.
    cf_eps = d.get("nocfps_eps") or eps
    cash_conversion = (nocfps / cf_eps) if (cf_eps and cf_eps > 0 and nocfps is not None) else None
    div_yield = d.get("dividend_yield")
    category = d.get("category")

    period = d.get("nocfps_period")
    as_of = d.get("nocfps_as_of")
    cf_note = (
        f"Disclosed {period} ÷ same-period EPS"
        if period
        else "Not disclosed to DSE in the last 400 days"
    )
    ocf_note = (
        f"Disclosed {period}, announced {as_of}"
        if period
        else "Not disclosed to DSE in the last 400 days"
    )

    def status(ok):
        return NODATA if ok is None else (PASS if ok else FAIL)

    rows = [
        {
            "name": "DSE category compliance",
            "note": "Public-market board the scrip trades on",
            "value": f"Category {category}" if category else "—",
            "threshold": "A or B",
            "status": status((category in ("A", "B")) if category else None),
        },
        {
            "name": "Return on equity",
            "note": "Basic EPS ÷ NAV per share",
            "value": f"{roe:.2f}%" if roe is not None else "—",
            "threshold": "≥ 15%",
            "status": status((roe >= 15.0) if roe is not None else None),
        },
        {
            "name": "Debt-to-equity",
            "note": "Short- + long-term loans ÷ (NAV × shares)",
            "value": f"{debt_equity:.2f}" if debt_equity is not None else "—",
            "threshold": "≤ 0.50",
            "status": status((debt_equity <= 0.50) if debt_equity is not None else None),
        },
        {
            "name": "Dividend payout ratio",
            "note": "Cash dividend on face value ÷ EPS",
            "value": f"{payout:.1f}%" if payout is not None else "—",
            "threshold": "30–70%",
            "status": status((30.0 <= payout <= 70.0) if payout is not None else None),
        },
        {
            "name": "Dividend yield",
            "note": "Cash dividend ÷ last trading price",
            "value": f"{div_yield:.2f}%" if div_yield is not None else "—",
            "threshold": "≥ 3%",
            "status": status((div_yield >= 3.0) if div_yield is not None else None),
        },
        {
            "name": "Price-to-earnings",
            "note": "DSE's current P/E on basic EPS",
            "value": f"{pe:.2f}" if pe is not None else "—",
            "threshold": "≤ 25",
            "status": status((0 < pe <= 25.0) if pe is not None else None),
        },
        {
            "name": "Cash conversion (NOCFPS ÷ EPS)",
            "note": cf_note,
            "value": f"{cash_conversion:.2f}x" if cash_conversion is not None else "—",
            "threshold": "≥ 0.85",
            "status": status((cash_conversion >= 0.85) if cash_conversion is not None else None),
        },
        {
            "name": "Positive operating cash flow",
            "note": ocf_note,
            "value": f"Tk {nocfps}" if nocfps is not None else "—",
            "threshold": "> 0",
            "status": status((nocfps > 0) if nocfps is not None else None),
        },
    ]

    passed = sum(1 for r in rows if r["status"] == PASS)
    failed = sum(1 for r in rows if r["status"] == FAIL)
    unscored = sum(1 for r in rows if r["status"] == NODATA)
    scored = passed + failed

    return {
        "rows": rows,
        "roe": roe,
        "debt_equity": debt_equity,
        "payout": payout,
        "cash_conversion": cash_conversion,
        "cashflow_eps": cf_eps,
        "cashflow_period": period,
        "equity_mn": equity_mn,
        "debt_mn": debt_mn,
        "passed": passed,
        "failed": failed,
        "unscored": unscored,
        "scored": scored,
        "qualified": scored > 0 and passed / scored >= 0.8,
    }
