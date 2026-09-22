"""DSE Stock Analyzer & SIP Screener.

UI implements the `DSE Stock Analyzer.dc.html` design: sidebar code search,
sticky breadcrumb bar, verdict donut, metric strip, and three tabs
(checklist / ratio benchmarks / scraped payload).
"""

import html
from datetime import datetime, timedelta, timezone

import streamlit as st
import streamlit.components.v1 as components

import dse
import dse_history
import dse_news
import pricechart
import theme
import tvchart

st.set_page_config(
    page_title="DSE Screener",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(theme.CSS, unsafe_allow_html=True)

BST = timezone(timedelta(hours=6))
PILL_COLORS = {
    dse.PASS: theme.ACCENT,
    dse.FAIL: theme.FAIL,
    dse.NODATA: theme.WARN,
}


# -----------------------------------------------------------------------------
# CACHED DATA
# -----------------------------------------------------------------------------
@st.cache_data(ttl=43200)  # The listed-instrument set changes rarely; cache 12h
def load_symbols():
    symbols, err = dse.fetch_symbols()
    return symbols, err, datetime.now(BST).strftime("%H:%M")


@st.cache_data(ttl=1800)  # Prices move intraday; cache 30 min
def load_company(symbol):
    return dse.fetch_company(symbol)


@st.cache_data(ttl=21600)  # Quarterly disclosures change a few times a year
def load_cashflow(symbol):
    return dse_news.fetch_cashflow(symbol)


@st.cache_data(ttl=21600)  # Day-end bars are published once, after the close
def load_history(symbol):
    return dse_history.fetch_history(symbol)


@st.cache_data(ttl=5, show_spinner=False)  # Polled live; see the fragment below
def load_quotes():
    return dse.fetch_quotes()


# -----------------------------------------------------------------------------
# SMALL RENDER HELPERS
# -----------------------------------------------------------------------------
def esc(value, dash="—"):
    return html.escape(str(value)) if value not in (None, "", "-") else dash


def num(value, spec="{:,.2f}", dash="—"):
    return spec.format(value) if value is not None else dash


def pill(status):
    fg = PILL_COLORS.get(status, theme.WARN)
    bg = theme.tint(fg, 13)
    border = theme.tint(fg, 32)
    return (
        f'<span class="pill" style="color:{fg};background:{bg};'
        f'border:1px solid {border}">{html.escape(status)}</span>'
    )


def metric(label, value, sub, accent=False, sub_color=None):
    color = f"color:{theme.ACCENT_TEXT}" if accent else ""
    sub_style = f"color:{sub_color}" if sub_color else ""
    return (
        f'<div class="metric"><div class="metric-k">{html.escape(label)}</div>'
        f'<div class="metric-v" style="{color}">{value}</div>'
        f'<div class="metric-s" style="{sub_style}">{html.escape(sub)}</div></div>'
    )


def bar_row(label, value, display, maximum, threshold):
    """One benchmark bar: fill = this company, tick = framework threshold."""
    if value is None or maximum <= 0:
        fill = '<div class="bar-fill" style="width:0"></div>'
    else:
        pct = max(0.0, min(100.0, value / maximum * 100.0))
        gradient = f"linear-gradient(90deg, {theme.tint(theme.ACCENT, 45)}, {theme.ACCENT})"
        fill = f'<div class="bar-fill" style="width:{pct:.1f}%;background:{gradient}"></div>'
    tick = ""
    if threshold is not None and maximum > 0:
        left = max(0.0, min(99.0, threshold / maximum * 100.0))
        tick = f'<div class="bar-mark" style="left:{left:.1f}%"></div>'
    return (
        f'<div class="bar-row"><div class="bar-label">{html.escape(label)}</div>'
        f'<div class="bar-track">{fill}{tick}</div>'
        f'<div class="bar-val">{display}</div></div>'
    )


# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------
symbols, symbols_err, synced_at = load_symbols()
names = dse.load_names()

# The selection lives in the URL rather than on disk: a server-side file would
# be shared by every visitor once this is deployed, and it makes links to a
# particular stock shareable and reload-safe.
if "code" not in st.session_state:
    from_url = (st.query_params.get("code") or "").strip().upper()
    for candidate in (from_url, dse.DEFAULT_CODE):
        if candidate and candidate in symbols:
            st.session_state.code = candidate
            break
    else:
        st.session_state.code = symbols[0] if symbols else dse.DEFAULT_CODE

with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brand-mark">DS</div>'
        '<div class="brand-name">DSE Screener</div>'
        '<div class="brand-ver">v9</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sec-label">Trading code</div>', unsafe_allow_html=True)

    if symbols:
        # st.text_input only reruns on Enter or blur, so a hand-rolled result
        # list never filters while typing. The selectbox is a combobox: its
        # popover filters on every keystroke, and it matches the company name
        # as well as the code because both are in the label.
        def option_label(symbol):
            listing_name = dse.display_name(symbol, names)
            return f"{symbol} — {listing_name}" if listing_name else symbol

        picked = st.selectbox(
            "Trading code",
            options=symbols,
            index=symbols.index(st.session_state.code)
            if st.session_state.code in symbols
            else 0,
            format_func=option_label,
            label_visibility="collapsed",
            placeholder=f"Search {len(symbols)} codes…",
        )
        if picked and picked != st.session_state.code:
            st.session_state.code = picked

        st.markdown(
            f'<div class="side-note">{len(symbols)} codes · synced {synced_at} BST</div>',
            unsafe_allow_html=True,
        )
    else:
        st.warning(symbols_err or "Trading-code list unavailable.")
        st.session_state.code = st.text_input("Trading code", value=st.session_state.code).upper()

    st.markdown('<div class="side-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-label">Framework</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="side-body">Long-term test across category, capital efficiency, '
        'debt safety, dividend balance and valuation.</p>',
        unsafe_allow_html=True,
    )
    tally_slot = st.empty()

    st.markdown(
        '<div class="side-foot">Source: <a href="https://dsebd.org" target="_blank">'
        "dsebd.org</a><br />Not investment advice.</div>",
        unsafe_allow_html=True,
    )

code = st.session_state.code
if st.query_params.get("code") != code:
    st.query_params["code"] = code

# -----------------------------------------------------------------------------
# DATA
# -----------------------------------------------------------------------------
with st.spinner(f"Scraping dsebd.org for {code}…"):
    data, err = load_company(code)
    if not err:
        # NOCFPS is not on the company page; it comes from the news archive.
        cashflow, cashflow_err = load_cashflow(code)
        if cashflow:
            data = dict(data)
            data["nocfps"] = cashflow["nocfps"]
            data["nocfps_eps"] = cashflow["eps"]
            data["nocfps_period"] = cashflow["period"]
            data["nocfps_as_of"] = cashflow["post_date"]
    else:
        cashflow, cashflow_err = None, None

# --- sticky breadcrumb bar ----------------------------------------------------
st.markdown(
    f'<div class="topbar"><div class="crumb">DSE / EQUITY / <b>{esc(code)}</b></div></div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="topbar-rule"></div>', unsafe_allow_html=True)

if err:
    # The company page is only one of this app's sources. Losing it should not
    # blank the page: the price chart is drawn from a separate feed and stays
    # useful, so show the failure as a notice and still render the chart.
    tally_slot.markdown("", unsafe_allow_html=True)
    st.markdown(
        f'<h1 class="co-name">{esc(code)}</h1>'
        f'<div class="notice" style="margin-top:14px"><span>&#9651;</span>'
        f"<p>{esc(err)}</p></div>",
        unsafe_allow_html=True,
    )
    bars, history_source, history_err = load_history(code)
    if history_err:
        st.markdown(
            f'<div class="notice"><span>&#9651;</span><p>{esc(history_err)}</p></div>',
            unsafe_allow_html=True,
        )
    else:
        components.html(
            pricechart.render(code, bars, history_source), height=pricechart.HEIGHT
        )
    st.stop()

verdict = dse.evaluate(data)

# --- sidebar tally, now that the verdict exists --------------------------------
tally_slot.markdown(
    f'<div class="tally"><span>Passed</span><b style="color:{theme.ACCENT}">{verdict["passed"]}</b></div>'
    f'<div class="tally"><span>Failed</span><b style="color:{theme.TEXT}">{verdict["failed"]}</b></div>'
    f'<div class="tally"><span>Unscored</span><b style="color:{theme.WARN}">{verdict["unscored"]}</b></div>',
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# HEADER: NAME, CHIPS, VERDICT DONUT
# -----------------------------------------------------------------------------
chips = [f'<span class="chip code">{esc(code)}</span>']
for label in (
    data.get("sector"),
    f"Category {data['category']}" if data.get("category") else None,
    f"FY{data['financial_year']} financials" if data.get("financial_year") else None,
):
    if label:
        chips.append(f'<span class="chip">{esc(label)}</span>')

frac = verdict["passed"] / verdict["scored"] if verdict["scored"] else 0.0
ring = theme.ACCENT if verdict["qualified"] else theme.WARN
verdict_title = "Qualified for SIP" if verdict["qualified"] else "Not qualified for SIP"
verdict_sub = (
    "Capital return · debt safety · valuation"
    if verdict["qualified"]
    else "Fails one or more long-term thresholds"
)

head_left, head_right = st.columns([3, 2], vertical_alignment="center")
with head_left:
    st.markdown(
        f'<h1 class="co-name">{esc(data["name"])}</h1>'
        f'<div class="chips">{"".join(chips)}</div>',
        unsafe_allow_html=True,
    )
with head_right:
    st.markdown(
        f'<div class="verdict" style="border:1px solid {theme.tint(ring, 35)}">'
        f'<div class="donut" style="background:conic-gradient({ring} 0turn {frac:.4f}turn,'
        f' #23262c {frac:.4f}turn 1turn)">'
        f'<div class="donut-in" style="color:{ring}">{verdict["passed"]}/{verdict["scored"]}</div></div>'
        f'<div><div class="verdict-title" style="color:{ring}">{verdict_title}</div>'
        f'<div class="verdict-sub">{verdict_sub}</div></div></div>',
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# METRIC STRIP
# -----------------------------------------------------------------------------
# The price tile refreshes on its own every 5s. It reads DSE's ~6 KB text quote
# feed rather than the ~330 KB company page, and the cache is shared across
# viewers, so the whole app costs one small request per 5s no matter how many
# people have it open. Everything else on the page is quarterly or annual data
# and stays on the 30-minute company-page cache.
@st.fragment(run_every=5)
def metric_strip(d):
    quotes, stamp, quote_err = load_quotes()

    live_price = quotes.get(d["symbol"])
    price = live_price if live_price is not None else d.get("ltp")

    previous = d.get("yesterday_close")
    if price is not None and previous:
        change_pct = (price - previous) / previous * 100.0
    else:
        change_pct = d.get("change_pct")

    if change_pct is None:
        change_sub, change_color = "no change data", None
    else:
        change_sub = f"{change_pct:+.2f}% today"
        change_color = (
            theme.ACCENT if change_pct > 0 else (theme.FAIL if change_pct < 0 else None)
        )

    if live_price is not None:
        # DSE's own feed stamp is a 12-hour clock served inconsistently across
        # its cache nodes, so show when we polled instead.
        change_sub += f" · {datetime.now(BST).strftime('%H:%M:%S')}"
    if quote_err or live_price is None:
        # Bonds and untraded scrips are absent from the feed; say so rather than
        # showing a stale price as though it were live.
        change_sub += " · page value"

    financial_year = d.get("financial_year") or "—"
    st.markdown(
        '<div class="metrics">'
        + metric("LTP (Tk)", num(price, "{:,.1f}"), change_sub, sub_color=change_color)
        + metric("EPS (Tk)", num(d.get("eps")), f"FY{financial_year} basic")
        + metric("NAV (Tk)", num(d.get("nav")), "per share")
        + metric("P/E Ratio", num(d.get("pe_ratio")), "current, basic EPS")
        + metric(
            "Div. Yield",
            num(d.get("dividend_yield"), "{:,.2f}%"),
            f"cash, FY{financial_year}",
            accent=d.get("dividend_yield") is not None,
        )
        + "</div>",
        unsafe_allow_html=True,
    )


metric_strip(data)

# -----------------------------------------------------------------------------
# TABS
# -----------------------------------------------------------------------------
tab_check, tab_chart, tab_ratios, tab_raw = st.tabs(
    ["Checklist & calculation", "Price chart", "Ratio benchmarks", "Scraped DSE data"]
)

with tab_check:
    if verdict["unscored"]:
        reason = html.escape(cashflow_err) if cashflow_err else (
            "some figures are missing from the DSE company page"
        )
        st.markdown(
            f'<div class="notice"><span>△</span><p>{verdict["unscored"]} criteria could not be '
            f"scored — {reason}</p></div>",
            unsafe_allow_html=True,
        )
    elif verdict["cashflow_period"]:
        st.markdown(
            '<div class="notice" style="background:color-mix(in oklch, var(--accent) 6%, transparent);'
            'border-color:color-mix(in oklch, var(--accent) 26%, transparent)">'
            f'<span style="color:{theme.ACCENT}">◆</span><p>Cash-flow criteria use the NOCFPS DSE '
            f'disclosed for {html.escape(verdict["cashflow_period"])}, announced '
            f'{esc(data.get("nocfps_as_of"))}, against the EPS quoted for the same period.</p></div>',
            unsafe_allow_html=True,
        )

    rows = "".join(
        '<div class="grid-row">'
        f'<div><div class="crit-name">{esc(r["name"])}</div>'
        f'<div class="crit-note">{esc(r["note"])}</div></div>'
        f'<div class="crit-val">{esc(r["value"])}</div>'
        f'<div class="crit-thr">{esc(r["threshold"])}</div>'
        f'<div style="text-align:right">{pill(r["status"])}</div>'
        "</div>"
        for r in verdict["rows"]
    )
    st.markdown(
        '<div class="grid-table"><div class="grid-head"><div>Criterion</div><div>Value</div>'
        '<div>Threshold</div><div style="text-align:right">Status</div></div>'
        f"{rows}</div>",
        unsafe_allow_html=True,
    )

with tab_chart:
    bars, history_source, history_err = load_history(code)
    if history_err:
        st.markdown(
            f'<div class="notice"><span>&#9651;</span><p>{esc(history_err)}</p></div>',
            unsafe_allow_html=True,
        )
    elif tvchart.available():
        # Optional: if someone has dropped a licensed TradingView Charting
        # Library into static/, use it. Nothing here depends on that.
        components.html(
            tvchart.render(code, bars, data.get("name")), height=tvchart.HEIGHT
        )
    else:
        # The component is an iframe with its own document, so it draws the
        # panel chrome itself rather than inheriting the page's CSS.
        components.html(
            pricechart.render(code, bars, history_source), height=pricechart.HEIGHT
        )

with tab_ratios:
    roe, de, payout = verdict["roe"], verdict["debt_equity"], verdict["payout"]
    yield_pct, pe = data.get("dividend_yield"), data.get("pe_ratio")

    specs = [
        ("ROE (%)", roe, num(roe, "{:,.1f}"), max(50.0, (roe or 0) * 1.2), 15.0),
        ("Debt-to-equity", de, num(de, "{:,.2f}"), max(1.0, (de or 0) * 1.2), 0.50),
        ("Payout ratio (%)", payout, num(payout, "{:,.1f}"), max(120.0, (payout or 0) * 1.2), 70.0),
        ("Dividend yield (%)", yield_pct, num(yield_pct, "{:,.2f}"), max(12.0, (yield_pct or 0) * 1.2), 3.0),
        ("P/E ratio", pe, num(pe, "{:,.2f}"), max(30.0, (pe or 0) * 1.2), 25.0),
    ]
    bars = "".join(bar_row(*spec) for spec in specs)
    st.markdown(
        '<div class="panel"><div class="panel-head"><h2>Key ratio benchmarks</h2>'
        f"<span>bar = {esc(code)} · tick = framework threshold</span></div>"
        f'<div class="bars">{bars}</div></div>',
        unsafe_allow_html=True,
    )

with tab_raw:
    cells = "".join(
        f'<div class="raw-cell"><div class="raw-k">{esc(key)}</div>'
        f'<div class="raw-v">{esc(value)}</div></div>'
        for key, value in data.items()
    )
    st.markdown(
        '<div class="raw"><div class="raw-head">'
        '<span class="sec-label">Scraped payload</span>'
        f'<span class="req">GET /displayCompany.php?name={esc(code)}</span>'
        f'<span class="req" style="margin-left:auto">last update {esc(data.get("last_update"))}</span>'
        f'</div><div class="raw-grid">{cells}</div></div>',
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# SEARCH-BOX BEHAVIOUR
# -----------------------------------------------------------------------------
# Streamlit's selectbox keeps the chosen label in the input itself, so searching
# again means deleting it first. Clear it on focus instead. Streamlit strips
# <script> from st.markdown, so this rides in a zero-height component iframe and
# reaches the app through window.parent (same origin).
with st.container(key="focus-script"):
    components.html(
        """
<script>
(function () {
  const doc = window.parent.document;
  const win = window.parent;

  function clearOnFocus(input) {
    if (input.dataset.dseClearOnFocus) return;
    input.dataset.dseClearOnFocus = "1";
    input.addEventListener("focus", function () {
      if (!input.value) return;
      // The input is React-controlled, so assigning .value is ignored unless we
      // go through the native setter and fire the event React listens for.
      const setter = Object.getOwnPropertyDescriptor(
        win.HTMLInputElement.prototype, "value"
      ).set;
      setter.call(input, "");
      input.dispatchEvent(new win.Event("input", { bubbles: true }));
    });
  }

  function hook() {
    doc.querySelectorAll(
      '[data-testid="stSidebar"] [data-testid="stSelectbox"] input'
    ).forEach(clearOnFocus);
  }

  hook();
  // Streamlit replaces the widget on every rerun, so re-attach when it does.
  new win.MutationObserver(hook).observe(doc.body, { childList: true, subtree: true });
})();
</script>
""",
        height=0,
    )
