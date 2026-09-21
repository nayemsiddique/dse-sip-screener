"""TradingView Advanced Charts, fed with our own DSE bars.

TradingView lists DSE as the `DSEBD` exchange, but its free embeddable widget
refuses those symbols ("This symbol is only available on TradingView") — the
data is not licensed for embedding. The Charting Library is the way round that:
it ships no data at all, so we hand it the series `dse_history` already scrapes
and the licensing question never arises.

The library is not redistributable, so it is not in this repo. `available()`
reports whether it has been dropped into `static/charting_library/`; until then
app.py falls back to the built-in canvas chart in `pricechart.py`.

The datafeed is implemented in the iframe over bars inlined at render time
rather than as a UDF HTTP service. That keeps the whole thing on Streamlit's
one port, which a hosted deploy will not give us a second of. The cost is that
the library's symbol search and compare see only the symbol on screen; the
sidebar is what changes symbols in this app.
"""

import json
import os

import theme

HERE = os.path.dirname(os.path.abspath(__file__))
LIBRARY_DIR = os.path.join(HERE, "static", "charting_library")
# The one file the standalone build needs; everything else it pulls in itself.
LIBRARY_ENTRY = "charting_library.standalone.js"
# Streamlit serves ./static/ here when server.enableStaticServing is on.
LIBRARY_URL = "/app/static/charting_library/"

HEIGHT = 720

# Bangladesh has no DST, so a fixed offset is honest and avoids depending on
# the library's timezone list carrying Asia/Dhaka.
TIMEZONE = "Asia/Dhaka"
SESSION = "1000-1430"  # DSE continuous trading, BST


def available():
    """True once the licensed library has been unpacked into static/."""
    return os.path.exists(os.path.join(LIBRARY_DIR, LIBRARY_ENTRY))


def install_hint():
    return (
        "TradingView's Charting Library is not in this checkout. Request access "
        "at tradingview.com/advanced-charts, then copy the repo's "
        "`charting_library/` folder to `static/charting_library/` — the chart "
        "switches over on the next rerun."
    )


_TEMPLATE = """
<!doctype html>
<meta charset="utf-8">
<style>
  html, body { margin: 0; padding: 0; height: 100%; background: __BG__; }
  #chart { height: 100vh; }
  #fail {
    display: none; padding: 28px; color: __MUTED__; background: __CARD__;
    border: 1px solid __BORDER__; border-radius: 14px; margin: 10px;
    font: 13px/1.6 __SANS__;
  }
  #fail b { color: __TEXT__; font-weight: 600; }
</style>

<div id="chart"></div>
<div id="fail"></div>

<script src="__LIB_URL____LIB_ENTRY__"></script>
<script>
const BARS = __BARS__;        // [[date, open, high, low, close, volume], ...] oldest first
const CFG = __CONFIG__;

function fail(message) {
  document.getElementById("chart").style.display = "none";
  const box = document.getElementById("fail");
  box.style.display = "block";
  box.innerHTML = "<b>Chart could not start.</b><br>" + message;
}

// --------------------------------------------------------------- series ----
// One daily series arrives; the library asks for weeks and months separately,
// so they are rolled up on demand and kept.
const daily = BARS.map((b) => ({
  time: Date.parse(b[0] + "T00:00:00Z"),
  open: b[1], high: b[2], low: b[3], close: b[4], volume: b[5],
}));

function rollup(bars, keyOf) {
  const out = [];
  let key = null;
  for (const b of bars) {
    const k = keyOf(b.time);
    if (k !== key) {
      key = k;
      out.push({ ...b });
    } else {
      const c = out[out.length - 1];
      c.high = Math.max(c.high, b.high);
      c.low = Math.min(c.low, b.low);
      c.close = b.close;
      c.volume += b.volume;
    }
  }
  return out;
}

const weekKey = (t) => {
  const d = new Date(t);
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));   // back to Monday
  return d.toISOString().slice(0, 10);
};
const monthKey = (t) => new Date(t).toISOString().slice(0, 7);

const SERIES = {
  "1D": daily,
  "1W": rollup(daily, weekKey),
  "1M": rollup(daily, monthKey),
};

function seriesFor(resolution) {
  if (resolution === "1W" || resolution === "W") return SERIES["1W"];
  if (resolution === "1M" || resolution === "M") return SERIES["1M"];
  return SERIES["1D"];
}

// -------------------------------------------------------------- datafeed ----
// Only what the library actually calls: this app has no intraday data and no
// realtime stream, so subscribeBars is a no-op rather than a fake ticker.
const datafeed = {
  onReady(callback) {
    setTimeout(() => callback({
      supports_search: false,
      supports_group_request: false,
      supports_marks: false,
      supports_timescale_marks: false,
      supports_time: true,
      supported_resolutions: ["1D", "1W", "1M"],
      exchanges: [{ value: "DSE", name: "DSE", desc: "Dhaka Stock Exchange" }],
      symbols_types: [{ name: "stock", value: "stock" }],
    }), 0);
  },

  searchSymbols(userInput, exchange, symbolType, onResult) {
    onResult([]);   // the sidebar picks the symbol; see the module docstring
  },

  resolveSymbol(symbolName, onResolve, onError) {
    setTimeout(() => onResolve({
      ticker: CFG.symbol,
      name: CFG.symbol,
      description: CFG.description,
      type: "stock",
      session: CFG.session,
      timezone: CFG.timezone,
      exchange: "DSE",
      listed_exchange: "DSE",
      format: "price",
      minmov: 1,
      pricescale: 10,           // DSE quotes to one decimal
      has_intraday: false,
      has_daily: true,
      has_weekly_and_monthly: true,   // rolled up here, not by the library
      supported_resolutions: ["1D", "1W", "1M"],
      volume_precision: 0,
      data_status: "endofday",
      currency_code: "BDT",
    }), 0);
  },

  getBars(symbolInfo, resolution, periodParams, onHistory, onError) {
    try {
      const { from, to, firstDataRequest, countBack } = periodParams;
      const bars = seriesFor(resolution);
      // periodParams is in seconds and `to` is exclusive; bar times are ms.
      let slice = bars.filter((b) => b.time >= from * 1000 && b.time < to * 1000);
      // countBack is the number of bars the library really wants; honouring it
      // keeps the first screen full even when the window starts mid-gap.
      if (countBack && slice.length < countBack) {
        const end = bars.findIndex((b) => b.time >= to * 1000);
        const stop = end === -1 ? bars.length : end;
        slice = bars.slice(Math.max(0, stop - countBack), stop);
      }
      onHistory(slice, { noData: slice.length === 0 });
    } catch (e) {
      onError(String(e));
    }
  },

  // Day-end data: nothing streams, so there is nothing to subscribe to. The
  // live price lives in the metric strip above the chart instead.
  subscribeBars() {},
  unsubscribeBars() {},
};

// ---------------------------------------------------------------- widget ----
if (!window.TradingView || !window.TradingView.widget) {
  fail("The Charting Library did not load from <code>" + CFG.libraryPath +
       "</code>. Check that the folder was copied into <code>static/</code>.");
} else {
  const widget = new window.TradingView.widget({
    container: "chart",
    library_path: CFG.libraryPath,
    datafeed,
    symbol: CFG.symbol,
    interval: "1D",
    locale: "en",
    theme: "dark",
    autosize: true,
    timezone: CFG.timezone,
    overrides: CFG.overrides,
    studies_overrides: CFG.studiesOverrides,
    // Intraday resolutions and realtime UI would promise data we do not have.
    disabled_features: [
      "header_symbol_search",
      "symbol_search_hot_key",
      "compare_symbol",
      "header_compare",
      "go_to_date",
      "timeframes_toolbar",
    ],
    enabled_features: ["hide_left_toolbar_by_default"],
    custom_css_url: CFG.customCss || undefined,
  });

  widget.onChartReady(() => {
    const chart = widget.activeChart();
    // The same two studies the built-in chart draws, so switching between them
    // does not change what is on screen.
    chart.createStudy("Bollinger Bands", false, false, { in_0: 20, in_1: 2 });
    chart.createStudy("Relative Strength Index", false, false, { in_0: 14 });
  });
}
</script>
"""


def render(symbol, bars, description=None):
    """HTML for the Charting Library component, bars inlined."""
    payload = [
        [b["date"], b["open"], b["high"], b["low"], b["close"], b["volume"]]
        for b in bars
    ]
    config = {
        "symbol": symbol,
        "description": description or symbol,
        "session": SESSION,
        "timezone": TIMEZONE,
        "libraryPath": LIBRARY_URL,
        "customCss": "",
        # The library's own dark theme, nudged onto this app's palette.
        "overrides": {
            "paneProperties.background": theme.CARD,
            "paneProperties.backgroundType": "solid",
            "paneProperties.vertGridProperties.color": theme.LINE,
            "paneProperties.horzGridProperties.color": theme.LINE,
            "scalesProperties.textColor": theme.MUTED,
            "scalesProperties.lineColor": theme.BORDER,
            "mainSeriesProperties.candleStyle.upColor": theme.CHART["up"],
            "mainSeriesProperties.candleStyle.downColor": theme.CHART["down"],
            "mainSeriesProperties.candleStyle.borderUpColor": theme.CHART["up"],
            "mainSeriesProperties.candleStyle.borderDownColor": theme.CHART["down"],
            "mainSeriesProperties.candleStyle.wickUpColor": theme.CHART["up"],
            "mainSeriesProperties.candleStyle.wickDownColor": theme.CHART["down"],
        },
        "studiesOverrides": {
            "volume.volume.color.0": theme.CHART["down"],
            "volume.volume.color.1": theme.CHART["up"],
            "bollinger bands.median.color": theme.CHART["band"],
            "bollinger bands.upper.color": theme.CHART["band"],
            "bollinger bands.lower.color": theme.CHART["band"],
            "relative strength index.plot.color": theme.CHART["rsi"],
        },
    }
    substitutions = {
        "__BARS__": json.dumps(payload, separators=(",", ":")),
        "__CONFIG__": json.dumps(config),
        "__LIB_URL__": LIBRARY_URL,
        "__LIB_ENTRY__": LIBRARY_ENTRY,
        "__BG__": theme.BG,
        "__CARD__": theme.CARD,
        "__BORDER__": theme.BORDER,
        "__TEXT__": theme.TEXT,
        "__MUTED__": theme.MUTED,
        "__SANS__": theme.SANS,
    }
    html = _TEMPLATE
    for token, value in substitutions.items():
        html = html.replace(token, value)
    return html
