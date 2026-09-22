# DSE Stock Analyzer & SIP Screener

Screens Dhaka Stock Exchange listings against a long-term framework — category,
capital efficiency, debt safety, dividend balance, valuation and cash
conversion — using data scraped live from [dsebd.org](https://www.dsebd.org/).

Not investment advice.

## Running it

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Layout

| file | role |
|---|---|
| `app.py` | Streamlit UI |
| `dse.py` | company-page scraper and framework scoring |
| `dse_history.py` | daily OHLCV history: amarstock, falling back to DSE |
| `pricechart.py` | the chart: canvas renderer, indicators, drawings, replay |
| `tvchart.py` | optional: use a licensed TradingView library if one is present |
| `static/charting_library/` | empty unless you supply that library |
| `dse_news.py` | NOCFPS from DSE's news archive |
| `theme.py` | design tokens and CSS |
| `build_names.py` | one-off builder for the trading-code → company-name cache |
| `symbol_names.json` | that cache, committed so a fresh deploy has names immediately |
| `certs_dsebd_intermediate.pem` | TLS intermediate dsebd.org fails to send |

## Live prices

The price tile refreshes itself every 5 seconds via `st.fragment(run_every=5)`.
It reads `datafile/quotes.txt` — a ~6 KB plain-text feed of every instrument's
last trade price, served in about 0.04s — rather than re-fetching the ~330 KB
company page. Note the URL: `datafile/quotes_script.php` only 302-redirects to
that file, so asking for it by name halves the round trips, which matters at one
poll per 5 seconds. The 5-second `st.cache_data` on that fetch is shared across
viewers, so the app makes one small request per 5s regardless of how many people
have it open.

Everything else on the page is quarterly or annual data and stays on the
30-minute company-page cache. Treasury bonds and untraded scrips are absent
from the quote feed; those fall back to the company-page price and are labelled
"page value".

## The price chart

Hand-built, in `pricechart.py`. It renders on a canvas inside a
`components.html` iframe, because Streamlit has no candlestick primitive and
strips `<script>` from `st.markdown`. The whole daily series is inlined once and
everything else — rollups, indicators, drawings, replay, the viewport — runs in
the browser, so no control costs a rerun or a second scrape.

Its chrome is `DSE Stock Analyzer.dc.html`'s Price chart panel: the toolbar, the
42px tool rail, the overlaid OHLC header and legend, the bottom bar. So is its
geometry — `PAD_R 64`, `AXIS_H 22`, `GAP 8`, and a price pane that absorbs
whatever the sub-panes give back so the panel stays a constant 470px. The design
draws SVG over 260 synthetic bars; canvas is used instead because the real
series runs to ~4,000 daily bars and `1D` over `5y` would otherwise put ~2,500
candles into the DOM. `theme.CHART` carries the design's palette as sRGB, since
a canvas cannot read CSS variables and `oklch()` in `fillStyle` is not safe
across browsers.

The feature set is modelled on TradingView, written from scratch.

| | |
|---|---|
| Chart types | Candles, hollow candles, bars, line, step line, area, baseline, high-low, columns, Heikin-Ashi |
| Overlays | Bollinger Bands, SMA, EMA, rolling VWAP, Keltner, Donchian, Supertrend, Parabolic SAR, Ichimoku cloud |
| Panes | Volume, RSI, MACD, Stochastic, ATR, OBV, ADX/DMI, CCI, Williams %R, MFI, ROC, Std Dev |
| Drawings | Trend line, ray, extended line, horizontal line, vertical line, parallel channel, rectangle, ellipse, arrow, Fib retracement, Fib extension, brush, text, measure |
| Drawing edit | Select, move, drag individual handles, per-drawing colour / width / dash, hide, delete, undo/redo, object list |
| Replay | Step back and forward, play/pause, 1×/2×/4× |
| Navigation | Drag to pan, wheel to zoom, drag the price scale, double-click to auto-fit, `1D/1W/1M/3M`, `1y/2y/3y/5y`, go to date |
| Scales | Auto, log, percent, invert |
| Panels | Data window, object tree, indicator settings, chart settings |
| Output | PNG export with caption |

Every indicator is implemented in `pricechart.py` — Wilder smoothing for RSI,
ADX and ATR, a proper Supertrend flip, Ichimoku spans projected forward by the
base period, and so on. Drawings are stored as `{t, p}` anchors — a timestamp
and a price — so they stay pinned to the same bar and level through zoom, pan
and interval changes. Drawings and toolbar settings persist in `localStorage`,
per symbol for drawings and globally for preferences; every read and write is
wrapped, so a private window or blocked storage just falls back to defaults.

Renko, Kagi, Point & Figure, Line Break and Range are not offered: they
re-bucket the series by price rather than by time, so they cannot share an
x-axis with the panes below them.

### The optional TradingView path

`tvchart.py` and `static/charting_library/` are dead weight unless someone drops
a licensed TradingView Charting Library into that folder, in which case the tab
uses it instead. Nothing in the app depends on it and the folder is empty in
this repo. For the record of why the free TradingView *widget* cannot be used
here: TradingView does carry DSE as the `DSEBD` exchange, but the widget answers
"This symbol is only available on TradingView" for those symbols, while
rendering `NASDAQ:AAPL` fine — the data is not licensed for embedding.

## Where the history comes from

`dse_history.py` tries two sources in order, and the one in use is named in
small type at the right of the legend:

1. **amarstock.com** — the JSON feed behind its own price chart, reaching back
   to 2010 with split-adjusted closes. This is what makes the 5Y/10Y/MAX views
   possible. Its data routes sit behind hashed path segments kept in the site's
   `common` script bundle; the known one is tried first and re-read out of that
   bundle if it has been rotated.
2. **dsebd.org's day-end archive** — the fallback. DSE publishes no long
   history anywhere: `day_end_archive.php` returns nothing before today minus
   ~730 days whatever start date you ask for, and its own chart tool
   (`php_graph/monthly_graph.php`) offers at most 24 months. Its prices are also
   unadjusted for splits.

Which range buttons appear depends on what the source actually returned — every
preset the data covers, plus the first one that overruns it, so there is always
a button that shows the whole series. On the DSE fallback that means the buttons
stop at 2Y.

## When dsebd.org does not answer

It often does not. A single connect timeout used to surface as a full-page
`Scraping Error: HTTPSConnectionPool(...) ConnectTimeoutError` and `st.stop()`,
which blanked a page whose chart would have rendered fine.

`dse.session()` is now the one HTTP session every scraper shares: `urllib3`
`Retry(total=3, connect=3, backoff_factor=0.6)`, connection pooling so a repeat
call costs no fresh TCP and TLS handshake, and the DSE CA bundle. Timeouts are
`(connect, read)` tuples with a short connect, because a dead handshake is
exactly what is being retried — three attempts at 8s beat one at 20s.

If all three attempts fail, the scrapers **raise** `dse.Unreachable` rather than
returning an error string. That matters because of caching: `st.cache_data`
stores return values but not exceptions, so a returned error would be served
from cache for the whole TTL — half an hour for a company page, six hours for
history, twelve for the code list. One blip left a single symbol looking
permanently broken while every other symbol worked, because only that symbol's
cache entry held the failure. Raising means the next run retries.

Each loader in `app.py` is therefore a thin wrapper over a cached fetch: the
cached function is free to raise, and the wrapper turns `Unreachable` back into
a message for the UI.

When it does fail, `app.py` degrades rather than stopping. The failure appears
as a notice with a **Try again** button, and the price chart is still drawn,
since it comes from a different source entirely.

## Two things worth knowing

**The TLS certificate.** dsebd.org serves an incomplete chain: the leaf and the
Sectigo root R46, but not the `Sectigo Public Server Authentication CA DV R36`
intermediate in between. certifi trusts the root but cannot bridge the gap, so
verification fails with `CERTIFICATE_VERIFY_FAILED`. `dse.ca_bundle()` builds
certifi + that intermediate and verifies against it. Certificate verification
stays on; nothing uses `verify=False`.

**NOCFPS is not on the company page.** `displayCompany.php` publishes no
cash-flow line for any symbol. The quarterly disclosures in DSE's news archive
quote it in prose, so `dse_news.py` reads the figure and the EPS for the *same*
period out of the latest one. Companies that have not disclosed in the window
show those two criteria as "No data" and drop out of the score's denominator
rather than counting as failures.

## Refreshing the name cache

`symbol_names.json` covers every listed company. After a new listing:

```bash
python3 build_names.py            # fetch only what is missing
python3 build_names.py --refresh  # rebuild from scratch
```

Treasury bonds have no company name anywhere on DSE; their label is derived
from the code, which encodes tenor and maturity (`TB20Y0934` → 20-year BGTB
maturing 09/2034).
