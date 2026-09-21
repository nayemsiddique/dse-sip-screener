"""The Price chart panel from `DSE Stock Analyzer.dc.html`, with teeth.

The panel's chrome is the design's: toolbar, 42px tool rail, overlaid OHLC
header and legend, bottom bar. Its geometry is the design's too — PAD_R 64,
AXIS_H 22, GAP 8, sub-panes 70-82px, and a PRICE_H that keeps the panel a
constant 470px however the studies are toggled.

The design draws SVG over 260 synthetic bars; this draws on a canvas, because
the real series runs to ~4,000 daily bars and `1D` over `5y` would otherwise
put ~2,500 candles into the DOM.

Everything beyond the design — chart types, drawings that actually draw, the
indicator menu, screenshots, keyboard shortcuts, persistence — is here because
the TradingView chart has it. What it does not have is the long tail: 100+
indicators, 110+ drawing tools, replay, alerts, compare, server-side layouts.
That is what `tvchart.py` and the licensed Charting Library are for.
"""

import json

import theme

# The chart body is a constant 470px — the price pane absorbs whatever the
# sub-panes give back — so the panel has a fixed height and the iframe can be
# sized once.
CHART_H = 470
HEIGHT = 552

INTERVALS = [
    {"label": "1D", "key": "D"},
    {"label": "1W", "key": "W"},
    {"label": "1M", "key": "M"},
    {"label": "3M", "key": "Q"},
]
DEFAULT_INTERVAL = "1W"

# The design's chips are 1y/2y/3y/5y; it counts them in weekly bars, and this
# counts them in days because the interval is chosen separately.
RANGES = [
    {"label": "1y", "days": 365},
    {"label": "2y", "days": 730},
    {"label": "3y", "days": 1095},
    {"label": "5y", "days": 1825},
]
DEFAULT_RANGE = "3y"

# TradingView's time-based styles. Renko, Kagi, Point & Figure, Line Break and
# Range are left out on purpose: they re-bucket the series by price rather than
# by time, so they cannot share an x-axis with the volume and RSI panes below.
CHART_TYPES = [
    {"key": "candles", "label": "Candles"},
    {"key": "hollow", "label": "Hollow candles"},
    {"key": "bars", "label": "Bars"},
    {"key": "line", "label": "Line"},
    {"key": "step", "label": "Step line"},
    {"key": "area", "label": "Area"},
    {"key": "baseline", "label": "Baseline"},
    {"key": "hilo", "label": "High-low"},
    {"key": "columns", "label": "Columns"},
    {"key": "heikin", "label": "Heikin-Ashi"},
]
DEFAULT_TYPE = "candles"

# Overlays draw on the price pane; panes get a strip of their own beneath it.
STUDIES = [
    {"key": "bb", "label": "BB", "name": "Bollinger Bands", "where": "overlay",
     "inputs": [{"key": "n", "label": "Length", "value": 20},
                {"key": "k", "label": "Mult", "value": 2}]},
    {"key": "sma", "label": "SMA", "name": "Moving average", "where": "overlay",
     "inputs": [{"key": "n", "label": "Length", "value": 50}]},
    {"key": "ema", "label": "EMA", "name": "Exponential MA", "where": "overlay",
     "inputs": [{"key": "n", "label": "Length", "value": 21}]},
    {"key": "vwap", "label": "VWAP", "name": "VWAP (rolling)", "where": "overlay",
     "inputs": [{"key": "n", "label": "Length", "value": 20}]},
    {"key": "volume", "label": "Vol", "name": "Volume", "where": "pane",
     "height": 70, "inputs": []},
    {"key": "rsi", "label": "RSI", "name": "Relative Strength Index", "where": "pane",
     "height": 82, "inputs": [{"key": "n", "label": "Length", "value": 14}]},
    {"key": "macd", "label": "MACD", "name": "MACD", "where": "pane",
     "height": 82, "inputs": [{"key": "fast", "label": "Fast", "value": 12},
                              {"key": "slow", "label": "Slow", "value": 26},
                              {"key": "signal", "label": "Signal", "value": 9}]},
    {"key": "stoch", "label": "Stoch", "name": "Stochastic", "where": "pane",
     "height": 82, "inputs": [{"key": "n", "label": "%K", "value": 14},
                              {"key": "d", "label": "%D", "value": 3}]},
    {"key": "atr", "label": "ATR", "name": "Average True Range", "where": "pane",
     "height": 70, "inputs": [{"key": "n", "label": "Length", "value": 14}]},
    {"key": "obv", "label": "OBV", "name": "On-Balance Volume", "where": "pane",
     "height": 70, "inputs": []},
    {"key": "keltner", "label": "KC", "name": "Keltner Channels", "where": "overlay",
     "inputs": [{"key": "n", "label": "Length", "value": 20},
                {"key": "k", "label": "Mult", "value": 2}]},
    {"key": "donchian", "label": "DC", "name": "Donchian Channels", "where": "overlay",
     "inputs": [{"key": "n", "label": "Length", "value": 20}]},
    {"key": "supertrend", "label": "ST", "name": "Supertrend", "where": "overlay",
     "inputs": [{"key": "n", "label": "ATR", "value": 10},
                {"key": "k", "label": "Mult", "value": 3}]},
    {"key": "psar", "label": "SAR", "name": "Parabolic SAR", "where": "overlay",
     "inputs": [{"key": "step", "label": "Step/100", "value": 2},
                {"key": "max", "label": "Max/100", "value": 20}]},
    {"key": "ichimoku", "label": "Ichi", "name": "Ichimoku Cloud", "where": "overlay",
     "inputs": [{"key": "conv", "label": "Conv", "value": 9},
                {"key": "base", "label": "Base", "value": 26},
                {"key": "span", "label": "Span B", "value": 52}]},
    {"key": "adx", "label": "ADX", "name": "ADX / DMI", "where": "pane",
     "height": 82, "inputs": [{"key": "n", "label": "Length", "value": 14}]},
    {"key": "cci", "label": "CCI", "name": "Commodity Channel Index", "where": "pane",
     "height": 78, "inputs": [{"key": "n", "label": "Length", "value": 20}]},
    {"key": "willr", "label": "%R", "name": "Williams %R", "where": "pane",
     "height": 78, "inputs": [{"key": "n", "label": "Length", "value": 14}]},
    {"key": "mfi", "label": "MFI", "name": "Money Flow Index", "where": "pane",
     "height": 78, "inputs": [{"key": "n", "label": "Length", "value": 14}]},
    {"key": "roc", "label": "ROC", "name": "Rate of Change", "where": "pane",
     "height": 70, "inputs": [{"key": "n", "label": "Length", "value": 12}]},
    {"key": "stddev", "label": "SD", "name": "Standard Deviation", "where": "pane",
     "height": 70, "inputs": [{"key": "n", "label": "Length", "value": 20}]},
]
# The design shows these three pressed; the rest live in the indicator menu.
DEFAULT_STUDIES = ["bb", "volume", "rsi"]

# The design's seven, all of which now draw. Vertical line and rectangle are
# additions — the rail is a column, and two more buttons cost nothing.
TOOLS = [
    {"key": "cross", "glyph": "\u271b", "name": "Crosshair"},
    {"key": "trend", "glyph": "\u2571", "name": "Trend line"},
    {"key": "ray", "glyph": "\u2197", "name": "Ray"},
    {"key": "extended", "glyph": "\u2194", "name": "Extended line"},
    {"key": "hray", "glyph": "\u2500", "name": "Horizontal line"},
    {"key": "vline", "glyph": "\u2502", "name": "Vertical line"},
    {"key": "channel", "glyph": "\u2225", "name": "Parallel channel"},
    {"key": "rect", "glyph": "\u25ad", "name": "Rectangle"},
    {"key": "ellipse", "glyph": "\u25cb", "name": "Ellipse"},
    {"key": "arrow", "glyph": "\u2192", "name": "Arrow"},
    {"key": "fib", "glyph": "\u2261", "name": "Fib retracement"},
    {"key": "fibext", "glyph": "\u2263", "name": "Fib extension"},
    {"key": "brush", "glyph": "\u270e", "name": "Brush"},
    {"key": "text", "glyph": "T", "name": "Text"},
    {"key": "measure", "glyph": "\u2317", "name": "Measure"},
    {"key": "magnet", "glyph": "\u25ce", "name": "Magnet (snap to OHLC)"},
]

# The palette a selected drawing can be restyled with.
DRAW_COLORS = ["#9aa3b0", "#49d3a1", "#e55458", "#e1b75c", "#7190d6", "#c494fa", "#e8e9ec"]


def ranges_for(span_days):
    """The design's chips, minus any the source could not cover.

    The DSE fallback only reaches two years back, and a chip that opens an empty
    window is worse than a missing chip. The first preset that overruns the data
    is kept so there is always one that shows everything.
    """
    offered = []
    for preset in RANGES:
        offered.append(preset)
        if preset["days"] >= span_days:
            break
    return offered

_MARKUP = r"""
<!doctype html>
<meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0; background: __BG__; color: __TEXT__;
  font-family: __SANS__; -webkit-font-smoothing: antialiased;
}
#panel {
  border: 1px solid __LINE__; border-radius: 14px; background: __PANEL__;
  overflow: hidden; position: relative; outline: none;
}

/* ---- top toolbar ---- */
#toolbar { display: flex; align-items: stretch; border-bottom: 1px solid __LINE__; background: __CARD__; }
#sym { display: flex; align-items: center; gap: 10px; padding: 9px 14px; border-right: 1px solid __LINE__; }
#sym .code { font-family: __MONO__; font-size: 13px; font-weight: 600; letter-spacing: .01em; }
#sym .badge {
  font-size: 10.5px; color: __MUTED_2__; border: 1px solid __BORDER__;
  border-radius: 4px; padding: 2px 6px;
}
#intervals { display: flex; align-items: center; border-right: 1px solid __LINE__; }
.group { display: flex; align-items: center; gap: 2px; padding: 0 8px; border-right: 1px solid __LINE__; }
#status {
  margin-left: auto; display: flex; align-items: center; gap: 10px; padding: 0 12px;
  font-family: __MONO__; font-size: 11px; color: __AXIS__;
}
#status .live { display: flex; align-items: center; gap: 6px; }
#status .dot { width: 6px; height: 6px; border-radius: 50%; background: __AXIS__; }
#status .dot.open { background: __UP__; }
#actions { display: flex; align-items: center; gap: 2px; padding: 0 8px; border-left: 1px solid __LINE__; }

button.chip {
  background: transparent; border: none; cursor: pointer; padding: 5px 11px;
  border-radius: 6px; font-family: __MONO__; font-size: 11px; color: __MUTED_2__;
}
button.chip:hover { color: __TEXT_DIM__; background: __HOVER__; }
button.chip[aria-pressed="true"] { background: __ACCENT_WASH__; color: __ACCENT__; }
button.chip:disabled { opacity: .35; cursor: default; }
#intervals button.chip { border-radius: 0; padding: 8px 12px; }
button.icon {
  width: 26px; height: 26px; display: flex; align-items: center; justify-content: center;
  background: transparent; border: none; border-radius: 6px; cursor: pointer;
  color: __MUTED_2__; font-size: 13px; font-family: __MONO__;
}
button.icon:hover { color: __TEXT_DIM__; background: __HOVER__; }
button.icon:disabled { opacity: .3; cursor: default; }

/* ---- body: tool rail + plot ---- */
/* The body is pinned to the chart height so a long tool rail scrolls inside it
   rather than pushing the bottom bar out of the iframe. */
#body { display: flex; align-items: stretch; height: __CHART_H__px; }
#rail {
  width: 42px; flex: 0 0 42px; border-right: 1px solid __LINE__; background: __CARD__;
  display: flex; flex-direction: column; align-items: center; gap: 1px; padding: 6px 0;
  overflow-y: auto; overflow-x: hidden; scrollbar-width: none;
}
#rail::-webkit-scrollbar { width: 0; }
#rail button {
  width: 26px; height: 26px; flex: 0 0 26px; display: flex; align-items: center;
  justify-content: center; background: transparent; border: none; border-radius: 6px;
  cursor: pointer; font-size: 13px; color: __MUTED_2__;
}
#rail button:hover { background: __HOVER__; color: __TEXT_DIM__; }
#rail button[aria-pressed="true"] { background: __ACCENT_WASH_15__; color: __ACCENT__; }
#rail .sep { width: 18px; height: 1px; flex: 0 0 1px; background: __LINE__; margin: 4px 0; }

#plot { flex: 1; min-width: 0; position: relative; }
#overlay {
  position: absolute; top: 10px; left: 12px; z-index: 2; display: flex;
  flex-direction: column; gap: 3px; font-family: __MONO__; font-size: 11px;
  pointer-events: none;
}
#head { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; white-space: nowrap; }
#head .ctx { color: __TEXT_DIM__; }
#head .k { color: __MUTED_2__; }
#head .k b { color: __TEXT__; font-weight: 400; }
#legend { display: flex; flex-direction: column; gap: 3px; }
#legend .row { display: flex; align-items: center; gap: 7px; white-space: nowrap; pointer-events: auto; }
#legend .sw { width: 9px; height: 9px; border-radius: 2px; flex: 0 0 9px; }
#legend .lb { color: __MUTED_2__; }
#legend .vl { color: __LEGEND_VALUE__; }
#legend .x {
  color: __MUTED_3__; cursor: pointer; padding: 0 3px; opacity: 0; font-size: 12px;
}
#legend .row:hover .x { opacity: 1; }
#legend .x:hover { color: __TEXT__; }
#cv { display: block; width: 100%; cursor: crosshair; touch-action: none; }
#cv.drag { cursor: grabbing; }
#cv.draw { cursor: copy; }
#cv.move { cursor: move; }

/* ---- bottom bar ---- */
#bottom {
  display: flex; align-items: center; gap: 4px; border-top: 1px solid __LINE__;
  padding: 7px 10px 7px 46px; background: __CARD__;
}
#caption { margin-left: 14px; font-family: __MONO__; font-size: 11px; color: __MUTED_3__; }
#scales { margin-left: auto; display: flex; gap: 4px; }

/* ---- menus ---- */
.menu {
  position: absolute; z-index: 20; background: __CARD__; border: 1px solid __BORDER__;
  border-radius: 10px; padding: 6px; display: none; box-shadow: 0 12px 30px rgba(0,0,0,.55);
  max-height: 330px; overflow: auto; min-width: 210px;
}
.menu.on { display: block; }
.menu .item {
  display: flex; align-items: center; gap: 9px; width: 100%; text-align: left;
  background: transparent; border: none; border-radius: 7px; cursor: pointer;
  padding: 7px 9px; font-size: 12px; color: __TEXT_DIM__; font-family: __SANS__;
}
.menu .item:hover { background: __HOVER__; color: __TEXT__; }
.menu .item .tick { width: 12px; color: __ACCENT__; }
.menu .grp {
  font-size: 10px; letter-spacing: .08em; text-transform: uppercase; color: __MUTED_3__;
  padding: 9px 9px 5px; font-weight: 600;
}
.menu .inputs { display: flex; gap: 6px; padding: 0 9px 8px 30px; }
.menu .inputs label { font-size: 10.5px; color: __MUTED_3__; display: flex; align-items: center; gap: 4px; }
.menu .inputs input {
  width: 46px; background: __FIELD__; border: 1px solid __BORDER__; border-radius: 5px;
  color: __TEXT__; font-family: __MONO__; font-size: 11px; padding: 3px 5px;
}
#stylebar {
  position: absolute; z-index: 25; display: none; align-items: center; gap: 6px;
  background: __CARD__; border: 1px solid __BORDER__; border-radius: 9px; padding: 5px 8px;
  box-shadow: 0 10px 26px rgba(0,0,0,.5);
}
#stylebar.on { display: flex; }
#stylebar .sw {
  width: 15px; height: 15px; border-radius: 4px; cursor: pointer;
  border: 1px solid __BORDER__;
}
#stylebar .sw[aria-pressed="true"] { outline: 2px solid __TEXT__; outline-offset: 1px; }
#stylebar .div { width: 1px; height: 16px; background: __LINE__; }

#datawin {
  width: 196px; flex: 0 0 196px; border-left: 1px solid __LINE__; background: __CARD__;
  padding: 10px 12px; font-family: __MONO__; font-size: 11px; overflow: auto;
  display: none;
}
#datawin.on { display: block; }
#datawin h4 {
  margin: 0 0 8px; font-size: 10px; letter-spacing: .08em; text-transform: uppercase;
  color: __MUTED_3__; font-family: __SANS__; font-weight: 600;
}
#datawin .r { display: flex; justify-content: space-between; gap: 8px; padding: 2px 0; }
#datawin .r span:first-child { color: __MUTED_2__; }
#datawin .r span:last-child { color: __TEXT_DIM__; }
#datawin .sec { margin-top: 10px; }

#replay { display: none; align-items: center; gap: 3px; margin-left: 10px; }
#replay.on { display: flex; }

#toast {
  position: absolute; left: 50%; bottom: 52px; transform: translateX(-50%); z-index: 30;
  background: __FIELD__; border: 1px solid __BORDER__; border-radius: 8px; padding: 7px 13px;
  font-size: 11.5px; color: __TEXT_DIM__; display: none;
}
#toast.on { display: block; }
</style>

<div id="panel" tabindex="0">
  <div id="toolbar">
    <div id="sym"><span class="code">__SYMBOL__</span><span class="badge">DSE</span></div>
    <div id="intervals"></div>
    <div class="group"><button class="chip" id="typeBtn">Candles &#9662;</button></div>
    <div class="group"><button class="chip" id="indBtn">Indicators &#9662;</button></div>
    <div class="group" id="studies"></div>
    <div id="status">
      <span class="live"><span class="dot" id="dot"></span><span id="mkt">Market closed</span></span>
      <span id="clock"></span>
    </div>
    <div id="actions">
      <button class="icon" id="undoBtn" title="Undo (Ctrl+Z)">&#8630;</button>
      <button class="icon" id="redoBtn" title="Redo (Ctrl+Y)">&#8631;</button>
      <button class="icon" id="shotBtn" title="Save chart image (S)">&#9974;</button>
      <button class="icon" id="fitBtn" title="Fit price scale (Shift+F)">&#9707;</button>
      <button class="icon" id="dataBtn" title="Data window (D)">&#9636;</button>
      <button class="icon" id="treeBtn" title="Objects">&#9776;</button>
      <button class="icon" id="setBtn" title="Settings">&#9881;</button>
      <button class="icon" id="replayBtn" title="Bar replay (P)">&#9654;</button>
      <button class="icon" id="fullBtn" title="Fullscreen (F)">&#9974;</button>
    </div>
  </div>

  <div id="body">
    <div id="rail"></div>
    <div id="plot">
      <div id="overlay"><div id="head"></div><div id="legend"></div></div>
      <canvas id="cv"></canvas>
      <div id="stylebar"></div>
    </div>
    <div id="datawin"></div>
  </div>

  <div id="bottom">
    <div id="ranges" style="display:flex; gap:4px"></div>
    <div id="replay">
      <button class="chip" id="rwBtn" title="Step back (left arrow)">&#9664;&#9664;</button>
      <button class="chip" id="playBtn" title="Play / pause (Space)">&#9654;</button>
      <button class="chip" id="ffBtn" title="Step forward (right arrow)">&#9654;&#9654;</button>
      <button class="chip" id="speedBtn" title="Speed">1&#215;</button>
      <button class="chip" id="exitBtn" title="Leave replay">&#10005;</button>
    </div>
    <span id="caption"></span>
    <div id="scales"></div>
  </div>

  <div class="menu" id="typeMenu"></div>
  <div class="menu" id="indMenu"></div>
  <div class="menu" id="treeMenu"></div>
  <div class="menu" id="setMenu"></div>
  <div id="toast"></div>
</div>
"""

_SCRIPT = r"""
<script>
const RAW = __BARS__;
const RANGES = __RANGES__, INTERVALS = __INTERVALS__, TYPES = __TYPES__;
const STUDY_DEFS = __STUDIES__, TOOL_DEFS = __TOOLS__;
const C = __COLORS__;
const SYMBOL = __SYMBOL_JSON__, SOURCE = __SOURCE__;
const CHART_H = __CHART_H__;
const DEF = __DEFAULTS__;

const DAY = 86400000, MIN_SPAN = 25 * DAY;
// The design's geometry.
const PAD_L = 0, PAD_R = 64, AXIS_H = 22, GAP = 8, MIN_PRICE_H = 180;

const $ = (id) => document.getElementById(id);
const cv = $("cv"), ctx = cv.getContext("2d");
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const near = (a, b, t) => Math.abs(a - b) <= t;

// ================================================================= series ===
const daily = RAW.map((b) => [...b, Date.parse(b[0] + "T00:00:00Z")]);

function rollup(bars, keyOf) {
  const out = [];
  let key = null;
  for (const b of bars) {
    const k = keyOf(b[6]);
    if (k !== key) { key = k; out.push([...b]); }
    else {
      const c = out[out.length - 1];
      c[2] = Math.max(c[2], b[2]);
      c[3] = Math.min(c[3], b[3]);
      c[4] = b[4];
      c[5] += b[5];
    }
  }
  return out;
}
const weekKey = (t) => {
  const d = new Date(t);
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
  return d.toISOString().slice(0, 10);
};
const monthKey = (t) => new Date(t).toISOString().slice(0, 7);
const quarterKey = (t) => {
  const d = new Date(t);
  return d.getUTCFullYear() + "Q" + Math.floor(d.getUTCMonth() / 3);
};

function makeSeries(bars) {
  const gap = bars.length > 1
    ? (bars[bars.length - 1][6] - bars[0][6]) / (bars.length - 1) : DAY;
  return { bars, gap: gap || DAY };
}
const SER = {
  D: makeSeries(daily),
  W: makeSeries(rollup(daily, weekKey)),
  M: makeSeries(rollup(daily, monthKey)),
  Q: makeSeries(rollup(daily, quarterKey)),
};
const FIRST_T = daily[0][6], LAST_T = daily[daily.length - 1][6];

// Heikin-Ashi is a redraw of the same bars, so it is derived per interval and
// cached; every indicator still reads the real closes.
const HA = {};
function heikin(iv) {
  if (HA[iv]) return HA[iv];
  const out = [];
  let po = null, pc = null;
  for (const b of SER[iv].bars) {
    const c = (b[1] + b[2] + b[3] + b[4]) / 4;
    const o = po === null ? (b[1] + b[4]) / 2 : (po + pc) / 2;
    out.push([b[0], o, Math.max(b[2], o, c), Math.min(b[3], o, c), c, b[5], b[6]]);
    po = o; pc = c;
  }
  HA[iv] = makeSeries(out);
  return HA[iv];
}

function idxAt(s, t) {
  const bars = s.bars;
  let lo = 0, hi = bars.length - 1;
  if (t <= bars[0][6]) return (t - bars[0][6]) / s.gap;
  if (t >= bars[hi][6]) return hi + (t - bars[hi][6]) / s.gap;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (bars[mid][6] <= t) lo = mid; else hi = mid;
  }
  const dt = bars[hi][6] - bars[lo][6];
  return lo + (dt ? (t - bars[lo][6]) / dt : 0);
}
function timeAt(s, idx) {
  const bars = s.bars, n = bars.length;
  if (idx <= 0) return bars[0][6] + idx * s.gap;
  if (idx >= n - 1) return bars[n - 1][6] + (idx - (n - 1)) * s.gap;
  const i = Math.floor(idx), f = idx - i;
  return bars[i][6] + (bars[i + 1][6] - bars[i][6]) * f;
}

// ============================================================= indicators ===
function smaArr(v, n) {
  const out = new Array(v.length).fill(null);
  let sum = 0;
  for (let i = 0; i < v.length; i++) {
    sum += v[i];
    if (i >= n) sum -= v[i - n];
    if (i >= n - 1) out[i] = sum / n;
  }
  return out;
}
function emaArr(v, n) {
  const out = new Array(v.length).fill(null);
  const k = 2 / (n + 1);
  let prev = null;
  for (let i = 0; i < v.length; i++) {
    if (v[i] == null) continue;
    prev = prev === null ? v[i] : v[i] * k + prev * (1 - k);
    if (i >= n - 1) out[i] = prev;
  }
  return out;
}
function bollingerArr(c, n, k) {
  const up = [], mid = [], lo = [];
  let sum = 0, sq = 0;
  for (let i = 0; i < c.length; i++) {
    sum += c[i]; sq += c[i] * c[i];
    if (i >= n) { sum -= c[i - n]; sq -= c[i - n] ** 2; }
    if (i < n - 1) { up.push(null); mid.push(null); lo.push(null); continue; }
    const m = sum / n;
    const sd = Math.sqrt(Math.max(0, sq / n - m * m));
    up.push(m + k * sd); mid.push(m); lo.push(m - k * sd);
  }
  return { up, mid, lo };
}
function rsiArr(c, n) {
  const out = new Array(c.length).fill(null);
  if (c.length <= n) return out;
  let g = 0, l = 0;
  for (let i = 1; i <= n; i++) {
    const d = c[i] - c[i - 1];
    if (d >= 0) g += d; else l -= d;
  }
  g /= n; l /= n;
  out[n] = l === 0 ? 100 : 100 - 100 / (1 + g / l);
  for (let i = n + 1; i < c.length; i++) {
    const d = c[i] - c[i - 1];
    g = (g * (n - 1) + Math.max(d, 0)) / n;
    l = (l * (n - 1) + Math.max(-d, 0)) / n;
    out[i] = l === 0 ? 100 : 100 - 100 / (1 + g / l);
  }
  return out;
}
function macdArr(c, f, s, g) {
  const fast = emaArr(c, f), slow = emaArr(c, s);
  const line = c.map((_, i) => (fast[i] == null || slow[i] == null) ? null : fast[i] - slow[i]);
  const seed = line.map((v) => v == null ? 0 : v);
  const sig = emaArr(seed, g).map((v, i) => line[i] == null ? null : v);
  const hist = line.map((v, i) => (v == null || sig[i] == null) ? null : v - sig[i]);
  return { line, sig, hist };
}
function stochArr(bars, n, d) {
  const k = new Array(bars.length).fill(null);
  for (let i = n - 1; i < bars.length; i++) {
    let hh = -Infinity, ll = Infinity;
    for (let j = i - n + 1; j <= i; j++) { hh = Math.max(hh, bars[j][2]); ll = Math.min(ll, bars[j][3]); }
    k[i] = hh === ll ? 50 : ((bars[i][4] - ll) / (hh - ll)) * 100;
  }
  const seed = k.map((v) => v == null ? 0 : v);
  const dl = smaArr(seed, d).map((v, i) => k[i] == null ? null : v);
  return { k, d: dl };
}
function atrArr(bars, n) {
  const tr = bars.map((b, i) => i === 0 ? b[2] - b[3]
    : Math.max(b[2] - b[3], Math.abs(b[2] - bars[i - 1][4]), Math.abs(b[3] - bars[i - 1][4])));
  const out = new Array(bars.length).fill(null);
  let prev = null;
  for (let i = 0; i < bars.length; i++) {
    if (i === n - 1) { prev = tr.slice(0, n).reduce((a, b) => a + b, 0) / n; out[i] = prev; }
    else if (i >= n) { prev = (prev * (n - 1) + tr[i]) / n; out[i] = prev; }
  }
  return out;
}
function obvArr(bars) {
  const out = [0];
  for (let i = 1; i < bars.length; i++) {
    const d = bars[i][4] - bars[i - 1][4];
    out.push(out[i - 1] + (d > 0 ? bars[i][5] : d < 0 ? -bars[i][5] : 0));
  }
  return out;
}
function vwapArr(bars, n) {
  // Rolling, not session-anchored: DSE day-end bars carry no intraday session
  // to anchor to, so an n-bar rolling VWAP is the honest version.
  const out = new Array(bars.length).fill(null);
  let pv = 0, vv = 0;
  const tp = bars.map((b) => (b[2] + b[3] + b[4]) / 3);
  for (let i = 0; i < bars.length; i++) {
    pv += tp[i] * bars[i][5]; vv += bars[i][5];
    if (i >= n) { pv -= tp[i - n] * bars[i - n][5]; vv -= bars[i - n][5]; }
    if (i >= n - 1) out[i] = vv ? pv / vv : null;
  }
  return out;
}

function trueRange(bars) {
  return bars.map((b, i) => i === 0 ? b[2] - b[3]
    : Math.max(b[2] - b[3], Math.abs(b[2] - bars[i - 1][4]), Math.abs(b[3] - bars[i - 1][4])));
}
function keltnerArr(bars, n, k) {
  const c = bars.map((b) => b[4]);
  const mid = emaArr(c, n), a = atrArr(bars, n);
  return {
    mid,
    up: mid.map((m, i) => (m == null || a[i] == null) ? null : m + k * a[i]),
    lo: mid.map((m, i) => (m == null || a[i] == null) ? null : m - k * a[i]),
  };
}
function donchianArr(bars, n) {
  const up = new Array(bars.length).fill(null), lo = up.slice(), mid = up.slice();
  for (let i = n - 1; i < bars.length; i++) {
    let hh = -Infinity, ll = Infinity;
    for (let j = i - n + 1; j <= i; j++) { hh = Math.max(hh, bars[j][2]); ll = Math.min(ll, bars[j][3]); }
    up[i] = hh; lo[i] = ll; mid[i] = (hh + ll) / 2;
  }
  return { up, lo, mid };
}
function supertrendArr(bars, n, k) {
  const a = atrArr(bars, n);
  const line = new Array(bars.length).fill(null);
  const dir = new Array(bars.length).fill(1);
  let upper = null, lower = null, trend = 1;
  for (let i = 0; i < bars.length; i++) {
    if (a[i] == null) continue;
    const hl2 = (bars[i][2] + bars[i][3]) / 2;
    let u = hl2 + k * a[i], l = hl2 - k * a[i];
    if (upper !== null) {
      u = (u < upper || bars[i - 1][4] > upper) ? u : upper;
      l = (l > lower || bars[i - 1][4] < lower) ? l : lower;
      trend = bars[i][4] > upper ? 1 : bars[i][4] < lower ? -1 : trend;
    }
    upper = u; lower = l;
    dir[i] = trend;
    line[i] = trend > 0 ? l : u;
  }
  return { line, dir };
}
function psarArr(bars, step, max) {
  const out = new Array(bars.length).fill(null);
  const dir = new Array(bars.length).fill(1);
  if (bars.length < 3) return { line: out, dir };
  let up = true, sar = bars[0][3], ep = bars[0][2], af = step;
  for (let i = 1; i < bars.length; i++) {
    sar = sar + af * (ep - sar);
    if (up) {
      sar = Math.min(sar, bars[i - 1][3], bars[Math.max(0, i - 2)][3]);
      if (bars[i][2] > ep) { ep = bars[i][2]; af = Math.min(af + step, max); }
      if (bars[i][3] < sar) { up = false; sar = ep; ep = bars[i][3]; af = step; }
    } else {
      sar = Math.max(sar, bars[i - 1][2], bars[Math.max(0, i - 2)][2]);
      if (bars[i][3] < ep) { ep = bars[i][3]; af = Math.min(af + step, max); }
      if (bars[i][2] > sar) { up = true; sar = ep; ep = bars[i][2]; af = step; }
    }
    out[i] = sar;
    dir[i] = up ? 1 : -1;
  }
  return { line: out, dir };
}
function ichimokuArr(bars, cn, bn, sn) {
  const hl = (n) => {
    const o = new Array(bars.length).fill(null);
    for (let i = n - 1; i < bars.length; i++) {
      let hh = -Infinity, ll = Infinity;
      for (let j = i - n + 1; j <= i; j++) { hh = Math.max(hh, bars[j][2]); ll = Math.min(ll, bars[j][3]); }
      o[i] = (hh + ll) / 2;
    }
    return o;
  };
  const conv = hl(cn), base = hl(bn), spanB = hl(sn);
  // The spans are plotted forward by `bn` bars, as Ichimoku intends; anything
  // past the last bar simply has nowhere to draw and is dropped.
  const a = new Array(bars.length).fill(null), b = a.slice();
  for (let i = 0; i < bars.length; i++) {
    const j = i - bn;
    if (j >= 0) {
      a[i] = (conv[j] == null || base[j] == null) ? null : (conv[j] + base[j]) / 2;
      b[i] = spanB[j];
    }
  }
  return { conv, base, spanA: a, spanB: b };
}
function adxArr(bars, n) {
  const tr = trueRange(bars);
  const pdm = [], ndm = [];
  for (let i = 0; i < bars.length; i++) {
    if (i === 0) { pdm.push(0); ndm.push(0); continue; }
    const up = bars[i][2] - bars[i - 1][2], dn = bars[i - 1][3] - bars[i][3];
    pdm.push(up > dn && up > 0 ? up : 0);
    ndm.push(dn > up && dn > 0 ? dn : 0);
  }
  const wilder = (v) => {
    const o = new Array(v.length).fill(null);
    let sum = 0;
    for (let i = 0; i < v.length; i++) {
      if (i < n) { sum += v[i]; if (i === n - 1) o[i] = sum; }
      else { o[i] = o[i - 1] - o[i - 1] / n + v[i]; }
    }
    return o;
  };
  const trs = wilder(tr), ps = wilder(pdm), ns = wilder(ndm);
  const pdi = [], ndi = [], dx = [];
  for (let i = 0; i < bars.length; i++) {
    if (trs[i] == null || !trs[i]) { pdi.push(null); ndi.push(null); dx.push(null); continue; }
    const p = (ps[i] / trs[i]) * 100, q = (ns[i] / trs[i]) * 100;
    pdi.push(p); ndi.push(q);
    dx.push((p + q) ? (Math.abs(p - q) / (p + q)) * 100 : null);
  }
  const adx = new Array(bars.length).fill(null);
  let acc = 0, seen = 0;
  for (let i = 0; i < dx.length; i++) {
    if (dx[i] == null) continue;
    seen++;
    if (seen <= n) { acc += dx[i]; if (seen === n) adx[i] = acc / n; }
    else adx[i] = (adx[i - 1] * (n - 1) + dx[i]) / n;
  }
  return { adx, pdi, ndi };
}
function cciArr(bars, n) {
  const tp = bars.map((b) => (b[2] + b[3] + b[4]) / 3);
  const ma = smaArr(tp, n);
  return tp.map((v, i) => {
    if (ma[i] == null) return null;
    let md = 0;
    for (let j = i - n + 1; j <= i; j++) md += Math.abs(tp[j] - ma[i]);
    md /= n;
    return md ? (v - ma[i]) / (0.015 * md) : 0;
  });
}
function willrArr(bars, n) {
  const o = new Array(bars.length).fill(null);
  for (let i = n - 1; i < bars.length; i++) {
    let hh = -Infinity, ll = Infinity;
    for (let j = i - n + 1; j <= i; j++) { hh = Math.max(hh, bars[j][2]); ll = Math.min(ll, bars[j][3]); }
    o[i] = hh === ll ? -50 : ((hh - bars[i][4]) / (hh - ll)) * -100;
  }
  return o;
}
function mfiArr(bars, n) {
  const tp = bars.map((b) => (b[2] + b[3] + b[4]) / 3);
  const o = new Array(bars.length).fill(null);
  for (let i = n; i < bars.length; i++) {
    let pos = 0, neg = 0;
    for (let j = i - n + 1; j <= i; j++) {
      const flow = tp[j] * bars[j][5];
      if (tp[j] > tp[j - 1]) pos += flow; else if (tp[j] < tp[j - 1]) neg += flow;
    }
    o[i] = neg === 0 ? 100 : 100 - 100 / (1 + pos / neg);
  }
  return o;
}
function rocArr(c, n) {
  return c.map((v, i) => i < n ? null : (c[i - n] ? ((v - c[i - n]) / c[i - n]) * 100 : null));
}
function stddevArr(c, n) {
  const m = smaArr(c, n);
  return c.map((_, i) => {
    if (m[i] == null) return null;
    let sq = 0;
    for (let j = i - n + 1; j <= i; j++) sq += (c[j] - m[i]) ** 2;
    return Math.sqrt(sq / n);
  });
}

const indCache = new Map();
function study(key, iv) {
  const st = studies[key];
  const ck = iv + "|" + key + "|" + JSON.stringify(st.inputs);
  if (indCache.has(ck)) return indCache.get(ck);
  const bars = SER[iv].bars;
  const c = bars.map((b) => b[4]);
  const p = st.inputs;
  let val;
  if (key === "bb") val = bollingerArr(c, p.n, p.k);
  else if (key === "sma") val = { line: smaArr(c, p.n) };
  else if (key === "ema") val = { line: emaArr(c, p.n) };
  else if (key === "vwap") val = { line: vwapArr(bars, p.n) };
  else if (key === "rsi") val = { line: rsiArr(c, p.n) };
  else if (key === "macd") val = macdArr(c, p.fast, p.slow, p.signal);
  else if (key === "stoch") val = stochArr(bars, p.n, p.d);
  else if (key === "atr") val = { line: atrArr(bars, p.n) };
  else if (key === "obv") val = { line: obvArr(bars) };
  else if (key === "keltner") val = keltnerArr(bars, p.n, p.k);
  else if (key === "donchian") val = donchianArr(bars, p.n);
  else if (key === "supertrend") val = supertrendArr(bars, p.n, p.k);
  else if (key === "psar") val = psarArr(bars, p.step / 100, p.max / 100);
  else if (key === "ichimoku") val = ichimokuArr(bars, p.conv, p.base, p.span);
  else if (key === "adx") val = adxArr(bars, p.n);
  else if (key === "cci") val = { line: cciArr(bars, p.n) };
  else if (key === "willr") val = { line: willrArr(bars, p.n) };
  else if (key === "mfi") val = { line: mfiArr(bars, p.n) };
  else if (key === "roc") val = { line: rocArr(c, p.n) };
  else if (key === "stddev") val = { line: stddevArr(c, p.n) };
  else val = {};
  indCache.set(ck, val);
  return val;
}

// ================================================================== state ===
let interval = DEF.interval, chartType = DEF.type, scale = "auto";
let range = RANGES.find((r) => r.label === DEF.range) || RANGES[RANGES.length - 1];
let studies = {};
for (const d of STUDY_DEFS) {
  const inputs = {};
  for (const i of d.inputs) inputs[i.key] = i.value;
  studies[d.key] = { on: DEF.studies.indexOf(d.key) >= 0, inputs };
}
let tool = "cross", magnet = false;
let drawings = [], draft = null, selected = null, grab = null;
let undoStack = [], redoStack = [];
let vp = null, preset = null, hover = null, box = null;
let dragging = false, drag = null, scaleDrag = null;
let manualScale = null, invert = false, showGrid = true, crossMode = "normal";
let dataWin = false;
// Bar replay walks a cutoff through the series; it is held as a timestamp so it
// survives an interval change.
let replay = false, replayT = null, playing = false, speed = 1, playTimer = null;

const PREF_KEY = "dse-chart-prefs", DRAW_KEY = "dse-chart-draw:" + SYMBOL;
function loadStore() {
  try {
    const p = JSON.parse(localStorage.getItem(PREF_KEY) || "{}");
    if (p.interval && INTERVALS.some((i) => i.label === p.interval)) interval = p.interval;
    if (p.type && TYPES.some((t) => t.key === p.type)) chartType = p.type;
    if (p.scale) scale = p.scale;
    if (p.invert != null) invert = !!p.invert;
    if (p.showGrid != null) showGrid = !!p.showGrid;
    if (p.crossMode) crossMode = p.crossMode;
    if (p.dataWin != null) dataWin = !!p.dataWin;
    if (p.studies) {
      for (const k in p.studies) if (studies[k]) Object.assign(studies[k], p.studies[k]);
    }
    const d = JSON.parse(localStorage.getItem(DRAW_KEY) || "[]");
    if (Array.isArray(d)) drawings = d;
  } catch (e) { /* private window, blocked storage: defaults are fine */ }
}
function savePrefs() {
  try {
    localStorage.setItem(PREF_KEY, JSON.stringify(
      { interval, type: chartType, scale, invert, showGrid, crossMode, dataWin, studies }));
  } catch (e) {}
}
function saveDrawings() {
  try { localStorage.setItem(DRAW_KEY, JSON.stringify(drawings)); } catch (e) {}
}
function pushUndo() {
  undoStack.push(JSON.stringify(drawings));
  if (undoStack.length > 60) undoStack.shift();
  redoStack.length = 0;
}

function windowFor(r) {
  return { from: Math.max(FIRST_T, LAST_T - r.days * DAY), to: LAST_T };
}
function setRange(r) {
  range = r;
  preset = windowFor(r);
  vp = { ...preset };
  clampViewport();
  hover = null;
}
function clampViewport() {
  const total = Math.max(LAST_T - FIRST_T, MIN_SPAN);
  const span = clamp(vp.to - vp.from, MIN_SPAN, total);
  if (span !== vp.to - vp.from) {
    const mid = (vp.from + vp.to) / 2;
    vp.from = mid - span / 2;
    vp.to = mid + span / 2;
  }
  if (vp.from < FIRST_T) { vp.from = FIRST_T; vp.to = FIRST_T + span; }
  if (vp.to > LAST_T) { vp.to = LAST_T; vp.from = LAST_T - span; }
  if (vp.from < FIRST_T) vp.from = FIRST_T;
}
const atPreset = () => vp && preset &&
  Math.abs(vp.from - preset.from) < DAY && Math.abs(vp.to - preset.to) < DAY;

const ivKey = () => (INTERVALS.find((i) => i.label === interval) || INTERVALS[1]).key;
const dispSeries = () => chartType === "heikin" ? heikin(ivKey()) : SER[ivKey()];

// ============================================================= formatting ===
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const shortDate = (iso) => `${MONTHS[+iso.slice(5, 7) - 1]} '${iso.slice(2, 4)}`;
const fullDate = (iso) => `${+iso.slice(8, 10)} ${MONTHS[+iso.slice(5, 7) - 1]} '${iso.slice(2, 4)}`;
const fmt = (v, d = 2) =>
  v === null || v === undefined || !isFinite(v) ? "—" : v.toFixed(d);
function volUnit(max) {
  if (max >= 1e6) return { div: 1e6, suffix: "mn" };
  if (max >= 1e3) return { div: 1e3, suffix: "k" };
  return { div: 1, suffix: "" };
}
function compact(v) {
  const a = Math.abs(v);
  if (a >= 1e9) return (v / 1e9).toFixed(1) + "bn";
  if (a >= 1e6) return (v / 1e6).toFixed(1) + "mn";
  if (a >= 1e3) return (v / 1e3).toFixed(1) + "k";
  return v.toFixed(1);
}

// DSE trades Sunday to Thursday, 10:00-14:30 Bangladesh time; no DST, so a
// fixed +06:00 offset is exact.
const bstNow = () => new Date(Date.now() + 6 * 3600000);
function marketOpen(d) {
  const day = d.getUTCDay();
  if (day === 5 || day === 6) return false;
  const m = d.getUTCHours() * 60 + d.getUTCMinutes();
  return m >= 600 && m <= 870;
}
function tickClock() {
  const d = bstNow(), open = marketOpen(d);
  $("mkt").textContent = open ? "Market open" : "Market closed";
  $("dot").classList.toggle("open", open);
  $("clock").textContent = d.toISOString().slice(11, 19) + " BST";
}
let toastTimer = null;
function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("on");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("on"), 1600);
}
</script>
"""

_SCRIPT2 = r"""
<script>
// ================================================================ drawing ===
function line(pts, color, width, dash) {
  ctx.save();
  ctx.strokeStyle = color; ctx.lineWidth = width || 1;
  ctx.setLineDash(dash || []);
  ctx.beginPath();
  let open = false;
  for (const p of pts) {
    if (p === null) { open = false; continue; }
    if (!open) { ctx.moveTo(p[0], p[1]); open = true; } else ctx.lineTo(p[0], p[1]);
  }
  ctx.stroke();
  ctx.restore();
}
function tag(x, y, w, h, text, bg, fg, align) {
  ctx.save();
  ctx.fillStyle = bg;
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, 3);
  ctx.fill();
  ctx.fillStyle = fg;
  ctx.textBaseline = "middle";
  ctx.textAlign = align || "left";
  ctx.fillText(text, align === "center" ? x + w / 2 : x + 6, y + h / 2 + 0.5);
  ctx.textAlign = "left";
  ctx.restore();
}

function layout() {
  const panes = STUDY_DEFS.filter((d) => d.where === "pane" && studies[d.key].on);
  let hs = panes.map((p) => p.height);
  const totalGap = panes.length * GAP;
  let priceH = CHART_H - AXIS_H - totalGap - hs.reduce((a, b) => a + b, 0);
  if (priceH < MIN_PRICE_H && panes.length) {
    // Too many panes for the fixed body: share the shortfall out rather than
    // letting the price pane collapse.
    const over = MIN_PRICE_H - priceH;
    hs = hs.map((h) => Math.max(34, h - over / panes.length));
    priceH = CHART_H - AXIS_H - totalGap - hs.reduce((a, b) => a + b, 0);
  }
  const tops = [];
  let y = priceH + GAP;
  panes.forEach((p, i) => { tops.push(y); y += hs[i] + GAP; });
  return { panes, hs, tops, priceH };
}

function draw() {
  const dpr = window.devicePixelRatio || 1;
  const W = cv.clientWidth, H = CHART_H;
  if (!W) return;
  cv.style.height = H + "px";
  cv.width = W * dpr; cv.height = H * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);

  const iv = ivKey();
  const s = dispSeries(), real = SER[iv];
  const bars = s.bars;
  if (!bars.length) return;
  if (hover && hover.iv !== iv) hover = null;

  const L = layout();
  const axisTop = H - AXIS_H;
  const iw = W - PAD_L - PAD_R;
  const startF = idxAt(s, vp.from), endF = idxAt(s, vp.to);
  const bw = iw / Math.max(endF - startF, 1e-6);
  const cw = Math.max(1.5, Math.min(9, bw * 0.62));
  const cx = (i) => PAD_L + (i - startF + 0.5) * bw;
  const i0 = clamp(Math.floor(startF), 0, bars.length - 1);
  let i1 = clamp(Math.ceil(endF), 0, bars.length - 1);
  if (replay && replayT != null) {
    i1 = clamp(Math.min(i1, Math.floor(idxAt(s, replayT))), i0, bars.length - 1);
  }

  // --- price scale ---
  let lo = Infinity, hi = -Infinity, maxV = 1;
  for (let i = i0; i <= i1; i++) {
    hi = Math.max(hi, bars[i][2]); lo = Math.min(lo, bars[i][3]);
    maxV = Math.max(maxV, bars[i][5]);
  }
  for (const d of STUDY_DEFS) {
    if (d.where !== "overlay" || !studies[d.key].on) continue;
    const v = study(d.key, iv);
    for (const k in v) {
      const arr = v[k];
      if (!Array.isArray(arr) || k === "dir") continue;
      for (let i = i0; i <= i1; i++) {
        if (arr[i] == null) continue;
        hi = Math.max(hi, arr[i]); lo = Math.min(lo, arr[i]);
      }
    }
  }
  if (manualScale) { lo = manualScale.lo; hi = manualScale.hi; }
  const span = hi - lo || 1;
  const basis = bars[i0][4];
  const tf = (v) => scale === "log" ? Math.log(Math.max(1e-6, v))
                  : scale === "percent" ? (v / basis - 1) * 100 : v;
  const tfInv = (x) => scale === "log" ? Math.exp(x)
                     : scale === "percent" ? basis * (1 + x / 100) : x;
  const tLo = tf(lo), tHi = tf(hi), tSpan = (tHi - tLo) || 1;
  const priceH = L.priceH;
  const frac = (v) => (tf(v) - tLo) / tSpan;
  const py = (v) => invert ? 8 + frac(v) * (priceH - 16)
                           : priceH - frac(v) * (priceH - 16) - 8;
  const pyInv = (y) => tfInv(tLo + (invert ? (y - 8) / (priceH - 16)
                                           : (priceH - 8 - y) / (priceH - 16)) * tSpan);
  const axisText = (v) => scale === "percent"
    ? ((v / basis - 1) * 100).toFixed(1) + "%" : v.toFixed(1);

  box = { PAD_L, iw, bw, startF, i0, i1, iv, s, real, maxV, py, pyInv, cx,
          axisTop, priceH, L, lo, hi, W, axisText };

  ctx.font = "10.5px " + C.mono;
  ctx.textBaseline = "middle";

  // --- price grid ---
  for (let k = 0; k <= 4; k++) {
    const v = lo + (span * k) / 4;
    if (showGrid) line([[PAD_L, py(v)], [W - PAD_R, py(v)]], C.grid, 1);
    ctx.fillStyle = C.axisText;
    ctx.fillText(axisText(v), W - PAD_R + 8, py(v));
  }

  ctx.save();
  ctx.beginPath();
  ctx.rect(PAD_L, 0, iw, H);
  ctx.clip();

  drawOverlays(iv, i0, i1, cx, py);
  drawPrice(bars, i0, i1, cx, py, cw, bw, priceH);
  drawPanes(iv, L, i0, i1, cx, cw, W, maxV);

  // --- last close ---
  const last = bars[i1];
  ctx.save();
  ctx.globalAlpha = 0.7;
  line([[PAD_L, py(last[4])], [W - PAD_R, py(last[4])]], C.accent, 1, [3, 4]);
  ctx.restore();

  drawDrawings(cx, py);

  const h = hover && hover.iv === iv && crossMode !== "none" ? hover.i : null;
  if (h !== null && bars[h]) {
    const x = Math.round(cx(h)) + 0.5;
    line([[x, 0], [x, axisTop]], C.crosshair, 1, [2, 3]);
    const hy = hover.y != null ? hover.y : py(bars[h][4]);
    line([[PAD_L, hy], [W - PAD_R, hy]], C.crosshair, 1, [2, 3]);
  }
  ctx.restore();

  drawPaneLabels(iv, L, W, maxV);

  // --- axes ---
  ctx.font = "10.5px " + C.mono;
  line([[0, axisTop], [W, axisTop]], C.grid, 1);
  line([[W - PAD_R, 0], [W - PAD_R, axisTop]], C.grid, 1);

  const visible = i1 - i0 + 1;
  const slots = Math.max(3, Math.min(9, Math.floor(iw / 110)));
  ctx.textAlign = "center";
  let lastRight = -Infinity;
  for (let k = 0; k < slots; k++) {
    const i = i0 + Math.round((visible - 1) * (k / (slots - 1)));
    if (showGrid) line([[cx(i), 0], [cx(i), axisTop]], C.gridTime, 1);
    const label = shortDate(bars[i][0]);
    const w = ctx.measureText(label).width;
    const x = clamp(cx(i), 26, W - PAD_R - 26);
    if (x - w / 2 < lastRight + 10) continue;
    ctx.fillStyle = C.axisText;
    ctx.fillText(label, x, axisTop + 11);
    lastRight = x + w / 2;
  }
  ctx.textAlign = "left";

  // --- tags ---
  tag(W - PAD_R + 4, py(last[4]) - 9, 54, 18, axisText(last[4]), C.accent, C.accentInk);
  if (replay) {
    const x = Math.round(cx(i1)) + 0.5;
    line([[x, 0], [x, axisTop]], C.accent, 1.4, [5, 3]);
  }
  if (h !== null && bars[h]) {
    const hy = hover.y != null ? hover.y : py(bars[h][4]);
    tag(W - PAD_R + 3, hy - 9, 58, 18, axisText(pyInv(hy)), C.crosshairTag, C.text);
    const lw = 76;
    tag(clamp(cx(h) - lw / 2, 0, W - PAD_R - lw), axisTop + 2, lw, 17,
        fullDate(bars[h][0]), C.crosshairTag, C.text, "center");
  }

  readout(s, real, (hover && hover.iv === iv ? hover.i : i1), maxV, i0, i1, iv);
}

// ------------------------------------------------------------- price pane --
function drawPrice(bars, i0, i1, cx, py, cw, bw, priceH) {
  const t = chartType;
  if (t === "line" || t === "step" || t === "area" || t === "baseline") {
    const pts = [];
    for (let i = i0; i <= i1; i++) {
      if (t === "step" && pts.length) pts.push([cx(i), pts[pts.length - 1][1]]);
      pts.push([cx(i), py(bars[i][4])]);
    }
    if (t === "baseline") {
      const base = bars[i0][4];
      const by = py(base);
      ctx.save();
      for (const side of [1, -1]) {
        ctx.save();
        ctx.beginPath();
        ctx.rect(PAD_L, side > 0 ? 0 : by, cx(i1) + bw, side > 0 ? by : priceH - by);
        ctx.clip();
        ctx.beginPath();
        ctx.moveTo(pts[0][0], by);
        for (const p of pts) ctx.lineTo(p[0], p[1]);
        ctx.lineTo(pts[pts.length - 1][0], by);
        ctx.closePath();
        ctx.fillStyle = side > 0 ? C.upFill : C.downFill;
        ctx.fill();
        ctx.restore();
      }
      ctx.restore();
      line([[PAD_L, by], [cx(i1) + bw, by]], C.axisText, 1, [4, 4]);
      for (let i = i0; i < i1; i++) {
        const a = [cx(i), py(bars[i][4])], b = [cx(i + 1), py(bars[i + 1][4])];
        line([a, b], bars[i + 1][4] >= base ? C.up : C.down, 1.6);
      }
      return;
    }
    if (t === "area") {
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(pts[0][0], priceH);
      for (const p of pts) ctx.lineTo(p[0], p[1]);
      ctx.lineTo(pts[pts.length - 1][0], priceH);
      ctx.closePath();
      const g = ctx.createLinearGradient(0, 0, 0, priceH);
      g.addColorStop(0, C.areaTop);
      g.addColorStop(1, C.areaBottom);
      ctx.fillStyle = g;
      ctx.fill();
      ctx.restore();
    }
    line(pts, C.accent, 1.6);
    return;
  }

  for (let i = i0; i <= i1; i++) {
    const b = bars[i];
    const up = b[4] >= b[1];
    const col = up ? C.up : C.down;
    const x = cx(i);
    const xr = Math.round(x) + 0.5;
    ctx.strokeStyle = col;
    ctx.lineWidth = 1;

    if (t === "columns") {
      ctx.fillStyle = col;
      const y0 = py(b[4]), y1 = py(b[1]);
      ctx.fillRect(x - cw / 2, Math.min(y0, y1), cw, Math.max(1, Math.abs(y1 - y0)));
      continue;
    }
    if (t === "hilo") {
      ctx.beginPath();
      ctx.moveTo(xr, py(b[2])); ctx.lineTo(xr, py(b[3]));
      ctx.stroke();
      ctx.fillStyle = col;
      ctx.fillRect(x - cw / 2, py(b[4]) - 0.75, cw, 1.5);
      continue;
    }
    if (t === "bars") {
      ctx.beginPath();
      ctx.moveTo(xr, py(b[2])); ctx.lineTo(xr, py(b[3]));
      ctx.moveTo(xr - cw / 2, py(b[1])); ctx.lineTo(xr, py(b[1]));
      ctx.moveTo(xr, py(b[4])); ctx.lineTo(xr + cw / 2, py(b[4]));
      ctx.stroke();
      continue;
    }
    // candles, hollow candles, Heikin-Ashi
    ctx.beginPath();
    ctx.moveTo(xr, py(b[2])); ctx.lineTo(xr, py(b[3]));
    ctx.stroke();
    const top = py(Math.max(b[1], b[4]));
    const bh = Math.max(1, Math.abs(py(b[1]) - py(b[4])));
    const hollow = t === "hollow" ? true : up;
    if (hollow) {
      ctx.strokeRect(Math.round(x - cw / 2) + 0.5, Math.round(top) + 0.5,
                     Math.round(cw), Math.round(bh));
    } else {
      ctx.fillStyle = col;
      ctx.fillRect(x - cw / 2, top, cw, bh);
    }
  }
}

// --------------------------------------------------------------- overlays --
function drawOverlays(iv, i0, i1, cx, py) {
  if (studies.bb.on) {
    const v = study("bb", iv);
    const up = [], low = [], mid = [];
    for (let i = i0; i <= i1; i++) {
      up.push(v.up[i] == null ? null : [cx(i), py(v.up[i])]);
      low.push(v.lo[i] == null ? null : [cx(i), py(v.lo[i])]);
      mid.push(v.mid[i] == null ? null : [cx(i), py(v.mid[i])]);
    }
    const from = up.findIndex((p) => p !== null);
    if (from >= 0) {
      ctx.save();
      ctx.beginPath();
      for (let i = from; i < up.length; i++) ctx.lineTo(up[i][0], up[i][1]);
      for (let i = low.length - 1; i >= from; i--) ctx.lineTo(low[i][0], low[i][1]);
      ctx.closePath();
      ctx.fillStyle = C.bandFill;
      ctx.fill();
      ctx.restore();
    }
    line(up, C.band, 1.2); line(low, C.band, 1.2);
    line(mid, C.bandMid, 1.2, [4, 3]);
  }
  for (const [key, col] of [["sma", C.sma], ["ema", C.ema], ["vwap", C.vwap]]) {
    if (!studies[key].on) continue;
    const arr = study(key, iv).line;
    const pts = [];
    for (let i = i0; i <= i1; i++) pts.push(arr[i] == null ? null : [cx(i), py(arr[i])]);
    line(pts, col, 1.4);
  }

  // Keltner and Donchian are channels: two edges and a dashed middle.
  for (const [key, col] of [["keltner", C.ema], ["donchian", C.sma]]) {
    if (!studies[key].on) continue;
    const v = study(key, iv);
    for (const [arr, dash] of [[v.up, null], [v.lo, null], [v.mid, [4, 3]]]) {
      const pts = [];
      for (let i = i0; i <= i1; i++) pts.push(arr[i] == null ? null : [cx(i), py(arr[i])]);
      line(pts, col, 1.2, dash);
    }
  }

  if (studies.supertrend.on) {
    // One polyline per trend leg, so the colour flips where the trend does.
    const v = study("supertrend", iv);
    let run = [], dir = null;
    const flush = () => { if (run.length > 1) line(run, dir > 0 ? C.up : C.down, 1.8); run = []; };
    for (let i = i0; i <= i1; i++) {
      if (v.line[i] == null) { flush(); continue; }
      if (dir !== v.dir[i]) { flush(); dir = v.dir[i]; }
      run.push([cx(i), py(v.line[i])]);
    }
    flush();
  }

  if (studies.psar.on) {
    const v = study("psar", iv);
    for (let i = i0; i <= i1; i++) {
      if (v.line[i] == null) continue;
      ctx.beginPath();
      ctx.fillStyle = v.dir[i] > 0 ? C.up : C.down;
      ctx.arc(cx(i), py(v.line[i]), 1.6, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  if (studies.ichimoku.on) {
    const v = study("ichimoku", iv);
    const a = [], b = [];
    for (let i = i0; i <= i1; i++) {
      a.push(v.spanA[i] == null ? null : [cx(i), py(v.spanA[i])]);
      b.push(v.spanB[i] == null ? null : [cx(i), py(v.spanB[i])]);
    }
    // The cloud: filled green where span A leads, red where span B does.
    for (let i = 0; i < a.length - 1; i++) {
      if (!a[i] || !b[i] || !a[i + 1] || !b[i + 1]) continue;
      ctx.save();
      ctx.globalAlpha = 0.12;
      ctx.fillStyle = v.spanA[i0 + i] >= v.spanB[i0 + i] ? C.up : C.down;
      ctx.beginPath();
      ctx.moveTo(a[i][0], a[i][1]);
      ctx.lineTo(a[i + 1][0], a[i + 1][1]);
      ctx.lineTo(b[i + 1][0], b[i + 1][1]);
      ctx.lineTo(b[i][0], b[i][1]);
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    }
    line(a, C.up, 1); line(b, C.down, 1);
    for (const [arr, col] of [[v.conv, C.rsi], [v.base, C.band]]) {
      const pts = [];
      for (let i = i0; i <= i1; i++) pts.push(arr[i] == null ? null : [cx(i), py(arr[i])]);
      line(pts, col, 1.2);
    }
  }
}

// ------------------------------------------------------------------ panes --
function drawPanes(iv, L, i0, i1, cx, cw, W, maxV) {
  L.panes.forEach((p, pi) => {
    const top = L.tops[pi], h = L.hs[pi];
    const bars = SER[iv].bars;
    if (p.key === "volume") {
      for (let i = i0; i <= i1; i++) {
        const vh = (bars[i][5] / maxV) * (h - 6);
        ctx.save();
        ctx.globalAlpha = 0.45;
        ctx.fillStyle = bars[i][4] >= bars[i][1] ? C.up : C.down;
        ctx.fillRect(cx(i) - cw / 2, top + h - vh, cw, vh);
        ctx.restore();
      }
      return;
    }
    const v = study(p.key, iv);
    if (p.key === "willr" || p.key === "mfi" || p.key === "adx") {
      const bounds = p.key === "willr" ? [-100, 0] : [0, 100];
      const guides = p.key === "willr" ? [-80, -50, -20] : p.key === "adx" ? [20, 50] : [20, 50, 80];
      const ry = (x) => top + h - ((x - bounds[0]) / (bounds[1] - bounds[0])) * h;
      for (const lv of guides) {
        ctx.save(); ctx.globalAlpha = 0.5;
        line([[PAD_L, ry(lv)], [W - PAD_R, ry(lv)]], C.rsiGuide, 1, [4, 4]);
        ctx.restore();
      }
      const set = p.key === "adx"
        ? [[v.adx, C.rsi], [v.pdi, C.up], [v.ndi, C.down]] : [[v.line, C.rsi]];
      for (const [arr, col] of set) {
        const pts = [];
        for (let i = i0; i <= i1; i++) pts.push(arr[i] == null ? null : [cx(i), ry(arr[i])]);
        line(pts, col, 1.4);
      }
      return;
    }
    if (p.key === "rsi" || p.key === "stoch") {
      const ry = (x) => top + h - (x / 100) * h;
      ctx.save();
      ctx.globalAlpha = 0.07;
      ctx.fillStyle = C.rsiZone;
      ctx.fillRect(PAD_L, ry(70), W - PAD_R - PAD_L, ry(30) - ry(70));
      ctx.restore();
      for (const lv of [30, 50, 70]) {
        if (lv === 50) line([[PAD_L, ry(lv)], [W - PAD_R, ry(lv)]], C.grid, 1);
        else {
          ctx.save(); ctx.globalAlpha = 0.5;
          line([[PAD_L, ry(lv)], [W - PAD_R, ry(lv)]], C.rsiGuide, 1, [4, 4]);
          ctx.restore();
        }
      }
      const series = p.key === "rsi" ? [[v.line, C.rsi]] : [[v.k, C.rsi], [v.d, C.ema]];
      for (const [arr, col] of series) {
        const pts = [];
        for (let i = i0; i <= i1; i++) pts.push(arr[i] == null ? null : [cx(i), ry(arr[i])]);
        line(pts, col, 1.4);
      }
      return;
    }
    // MACD, ATR and OBV all autoscale to whatever is on screen.
    let lo = Infinity, hi = -Infinity;
    const arrays = p.key === "macd" ? [v.line, v.sig, v.hist] : [v.line];
    for (const a of arrays) for (let i = i0; i <= i1; i++) {
      if (a[i] == null) continue;
      lo = Math.min(lo, a[i]); hi = Math.max(hi, a[i]);
    }
    if (!isFinite(lo)) return;
    if (p.key === "macd" || p.key === "cci" || p.key === "roc") {
      const m = Math.max(Math.abs(lo), Math.abs(hi)) || 1;
      lo = -m; hi = m;
    }
    const sp = (hi - lo) || 1;
    const qy = (x) => top + h - ((x - lo) / sp) * (h - 6) - 3;
    if (p.key === "macd") {
      line([[PAD_L, qy(0)], [W - PAD_R, qy(0)]], C.grid, 1);
      for (let i = i0; i <= i1; i++) {
        if (v.hist[i] == null) continue;
        ctx.save(); ctx.globalAlpha = 0.5;
        ctx.fillStyle = v.hist[i] >= 0 ? C.up : C.down;
        const y0 = qy(0), y1 = qy(v.hist[i]);
        ctx.fillRect(cx(i) - cw / 2, Math.min(y0, y1), cw, Math.max(1, Math.abs(y1 - y0)));
        ctx.restore();
      }
      for (const [arr, col] of [[v.line, C.rsi], [v.sig, C.ema]]) {
        const pts = [];
        for (let i = i0; i <= i1; i++) pts.push(arr[i] == null ? null : [cx(i), qy(arr[i])]);
        line(pts, col, 1.3);
      }
      return;
    }
    if (p.key === "cci" || p.key === "roc") line([[PAD_L, qy(0)], [W - PAD_R, qy(0)]], C.grid, 1);
    const pts = [];
    for (let i = i0; i <= i1; i++) pts.push(v.line[i] == null ? null : [cx(i), qy(v.line[i])]);
    line(pts, p.key === "obv" ? C.vwap : C.sma, 1.4);
  });
}

function drawPaneLabels(iv, L, W, maxV) {
  ctx.font = "10px " + C.mono;
  L.panes.forEach((p, pi) => {
    const top = L.tops[pi], h = L.hs[pi];
    ctx.fillStyle = C.axisText;
    let label = p.name;
    if (p.key === "volume") {
      const u = volUnit(maxV).suffix;
      label = u ? "Vol · " + u : "Vol";
      line([[PAD_L, top + h], [W - PAD_R, top + h]], C.grid, 1);
    } else if (p.key === "rsi") label = "RSI " + studies.rsi.inputs.n;
    else if (p.key === "macd") label = "MACD";
    else if (p.key === "stoch") label = "Stoch " + studies.stoch.inputs.n;
    else if (p.key === "atr") label = "ATR " + studies.atr.inputs.n;
    else if (p.key === "obv") label = "OBV";
    else label = p.name + (studies[p.key].inputs.n ? " " + studies[p.key].inputs.n : "");
    ctx.fillText(label, PAD_L + 8, top + 12);
    if (p.key === "rsi" || p.key === "stoch") {
      const ry = (x) => top + h - (x / 100) * h;
      for (const lv of [30, 70]) ctx.fillText(String(lv), W - PAD_R + 8, ry(lv));
    } else if (p.key === "willr" || p.key === "mfi" || p.key === "adx") {
      const bounds = p.key === "willr" ? [-100, 0] : [0, 100];
      const ticks = p.key === "willr" ? [-80, -20] : [20, 80];
      const ry = (x) => top + h - ((x - bounds[0]) / (bounds[1] - bounds[0])) * h;
      for (const lv of ticks) ctx.fillText(String(lv), W - PAD_R + 8, ry(lv));
    }
  });
}
</script>
"""

_SCRIPT3 = r"""
<script>
// =============================================================== drawings ===
// Anchors are stored as {t, p} — a timestamp and a price — so a drawing stays
// pinned to the same bar and level through zoom, pan and interval changes.
const FIBS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];

function toScreen(a) { return [box.cx(idxAt(box.s, a.t)), box.py(a.p)]; }
function toAnchor(x, y) {
  const idx = box.startF + (x - box.PAD_L) / box.bw;
  return { t: timeAt(box.s, idx), p: box.pyInv(y) };
}
function snapAnchor(x, y) {
  const a = toAnchor(x, y);
  if (!magnet) return a;
  const i = clamp(Math.round(box.startF + (x - box.PAD_L) / box.bw - 0.5), box.i0, box.i1);
  const b = box.s.bars[i];
  let best = a.p, bd = Infinity;
  for (const v of [b[1], b[2], b[3], b[4]]) {
    const d = Math.abs(box.py(v) - y);
    if (d < bd) { bd = d; best = v; }
  }
  return { t: b[6], p: best };
}

function geom(d) {
  const W = box.W, right = W - PAD_R;
  if (d.type === "hray") { const y = box.py(d.pts[0].p); return { kind: "h", y }; }
  if (d.type === "vline") { const x = toScreen(d.pts[0])[0]; return { kind: "v", x }; }
  if (d.type === "brush") return { kind: "path", pts: d.pts.map(toScreen), right };
  const a = toScreen(d.pts[0]);
  const b = d.pts[1] ? toScreen(d.pts[1]) : a;
  const c = d.pts[2] ? toScreen(d.pts[2]) : null;
  return { kind: "seg", a, b, c, right };
}

// A ray stops at the right edge; an extended line runs off both.
function project(a, b, right, both) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  if (!dx && !dy) return [a, b];
  const far = (p, sign) => {
    const t = dx ? (sign > 0 ? (right - p[0]) / dx : (0 - p[0]) / dx) : sign * 4000;
    return [p[0] + dx * t, p[1] + dy * t];
  };
  const end = dx > 0 ? far(a, 1) : dx < 0 ? far(a, -1) : [a[0], a[1] + dy * 4000];
  if (!both) return [a, end];
  const back = dx > 0 ? far(a, -1) : dx < 0 ? far(a, 1) : [a[0], a[1] - dy * 4000];
  return [back, end];
}
const FIB_EXT = [0, 0.618, 1, 1.272, 1.618, 2, 2.618];
const dashOf = (d) => d.dash ? [6, 4] : null;
const widthOf = (d, on) => (d.width || 1.3) + (on ? 0.6 : 0);

function drawDrawings(cx, py) {
  const all = draft ? drawings.concat([draft]) : drawings;
  for (const d of all) {
    if (d.hidden) continue;
    const on = d === selected;
    const col = on ? C.text : (d.color || C.drawing);
    const g = geom(d);
    if (g.kind === "h") {
      line([[PAD_L, g.y], [box.W - PAD_R, g.y]], col, on ? 1.8 : 1.3);
      tag(box.W - PAD_R + 3, g.y - 9, 58, 18, box.axisText(d.pts[0].p), col, C.bg);
      continue;
    }
    if (g.kind === "v") {
      line([[g.x, 0], [g.x, box.axisTop]], col, on ? 1.8 : 1.3);
      continue;
    }
    if (g.kind === "path") {
      line(g.pts, col, widthOf(d, on), dashOf(d));
      if (on && g.pts.length) handle(g.pts[0]);
      continue;
    }
    const [a, b] = [g.a, g.b];
    if (d.type === "ray" || d.type === "extended") {
      const [p, q] = project(a, b, g.right, d.type === "extended");
      line([p, q], col, widthOf(d, on), dashOf(d));
      if (on) for (const h of [a, b]) handle(h);
      continue;
    }
    if (d.type === "arrow") {
      line([a, b], col, widthOf(d, on), dashOf(d));
      const ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
      const hl = 11;
      ctx.save();
      ctx.fillStyle = col;
      ctx.beginPath();
      ctx.moveTo(b[0], b[1]);
      ctx.lineTo(b[0] - hl * Math.cos(ang - 0.4), b[1] - hl * Math.sin(ang - 0.4));
      ctx.lineTo(b[0] - hl * Math.cos(ang + 0.4), b[1] - hl * Math.sin(ang + 0.4));
      ctx.closePath();
      ctx.fill();
      ctx.restore();
      if (on) for (const h of [a, b]) handle(h);
      continue;
    }
    if (d.type === "channel") {
      const off = g.c ? g.c[1] - b[1] : 0;
      line([a, b], col, widthOf(d, on), dashOf(d));
      line([[a[0], a[1] + off], [b[0], b[1] + off]], col, widthOf(d, on), dashOf(d));
      ctx.save();
      ctx.globalAlpha = 0.08;
      ctx.fillStyle = col;
      ctx.beginPath();
      ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]);
      ctx.lineTo(b[0], b[1] + off); ctx.lineTo(a[0], a[1] + off);
      ctx.closePath(); ctx.fill();
      ctx.restore();
      if (on) { handle(a); handle(b); if (g.c) handle([b[0], b[1] + off]); }
      continue;
    }
    if (d.type === "ellipse") {
      ctx.save();
      ctx.beginPath();
      ctx.ellipse((a[0] + b[0]) / 2, (a[1] + b[1]) / 2,
                  Math.abs(b[0] - a[0]) / 2, Math.abs(b[1] - a[1]) / 2, 0, 0, Math.PI * 2);
      ctx.globalAlpha = 0.1; ctx.fillStyle = col; ctx.fill();
      ctx.globalAlpha = 1; ctx.strokeStyle = col; ctx.lineWidth = widthOf(d, on);
      ctx.setLineDash(dashOf(d) || []);
      ctx.stroke();
      ctx.restore();
      if (on) for (const h of [a, b]) handle(h);
      continue;
    }
    if (d.type === "fibext") {
      const p0 = d.pts[0].p, p1 = d.pts[1].p;
      const x0 = Math.min(a[0], b[0]), xe = Math.max(Math.max(a[0], b[0]), x0 + 40);
      ctx.font = "10px " + C.mono;
      FIB_EXT.forEach((f, k) => {
        const v = p0 + (p1 - p0) * f;
        const y = box.py(v);
        line([[x0, y], [xe, y]], C.fib[k % C.fib.length], on ? 1.6 : 1.1);
        ctx.fillStyle = C.fib[k % C.fib.length];
        ctx.fillText(f.toFixed(3) + "  " + v.toFixed(1), x0 + 4, y - 6);
      });
      line([a, b], col, 1, [3, 3]);
      if (on) for (const h of [a, b]) handle(h);
      continue;
    }
    if (d.type === "trend" || d.type === "measure") {
      line([a, b], col, widthOf(d, on), dashOf(d));
      if (d.type === "measure") {
        const dp = d.pts[1].p - d.pts[0].p;
        const pct = d.pts[0].p ? (dp / d.pts[0].p) * 100 : 0;
        const nb = Math.abs(Math.round(idxAt(box.s, d.pts[1].t) - idxAt(box.s, d.pts[0].t)));
        ctx.save();
        ctx.globalAlpha = 0.12;
        ctx.fillStyle = dp >= 0 ? C.up : C.down;
        ctx.fillRect(Math.min(a[0], b[0]), Math.min(a[1], b[1]),
                     Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1]));
        ctx.restore();
        const label = `${dp >= 0 ? "+" : ""}${dp.toFixed(2)} (${pct.toFixed(2)}%) · ${nb} bars`;
        ctx.font = "10.5px " + C.mono;
        const w = ctx.measureText(label).width + 12;
        tag(clamp((a[0] + b[0]) / 2 - w / 2, 0, box.W - PAD_R - w), Math.min(a[1], b[1]) - 22,
            w, 18, label, dp >= 0 ? C.up : C.down, C.bg, "center");
      }
      if (on) for (const p of [a, b]) handle(p);
      continue;
    }
    if (d.type === "rect") {
      const x = Math.min(a[0], b[0]), y = Math.min(a[1], b[1]);
      const w = Math.abs(b[0] - a[0]), h = Math.abs(b[1] - a[1]);
      ctx.save();
      ctx.globalAlpha = 0.1;
      ctx.fillStyle = col;
      ctx.fillRect(x, y, w, h);
      ctx.restore();
      ctx.save();
      ctx.strokeStyle = col; ctx.lineWidth = widthOf(d, on);
      ctx.setLineDash(dashOf(d) || []);
      ctx.strokeRect(x, y, w, h);
      ctx.restore();
      if (on) for (const p of [a, b]) handle(p);
      continue;
    }
    if (d.type === "fib") {
      const p0 = d.pts[0].p, p1 = d.pts[1].p;
      const x0 = Math.min(a[0], b[0]), x1 = Math.max(a[0], b[0]);
      ctx.font = "10px " + C.mono;
      FIBS.forEach((f, k) => {
        const v = p1 + (p0 - p1) * f;
        const y = box.py(v);
        const xe = Math.max(x1, x0 + 40);
        line([[x0, y], [xe, y]], C.fib[k % C.fib.length], on ? 1.6 : 1.1);
        ctx.fillStyle = C.fib[k % C.fib.length];
        ctx.fillText(f.toFixed(3) + "  " + v.toFixed(1), x0 + 4, y - 6);
      });
      line([a, b], col, 1, [3, 3]);
      if (on) for (const p of [a, b]) handle(p);
      continue;
    }
    if (d.type === "text") {
      ctx.font = "12px " + C.sans;
      ctx.fillStyle = col;
      ctx.textBaseline = "middle";
      ctx.fillText(d.text || "", a[0] + 6, a[1]);
      if (on) handle(a);
      continue;
    }
  }
}
function handle(p) {
  ctx.save();
  ctx.fillStyle = C.text;
  ctx.strokeStyle = C.bg;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(p[0], p[1], 3.5, 0, Math.PI * 2);
  ctx.fill(); ctx.stroke();
  ctx.restore();
}

function distToSeg(px, py2, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const len = dx * dx + dy * dy;
  const t = len ? clamp(((px - a[0]) * dx + (py2 - a[1]) * dy) / len, 0, 1) : 0;
  return Math.hypot(px - (a[0] + t * dx), py2 - (a[1] + t * dy));
}
function hitTest(x, y) {
  for (let i = drawings.length - 1; i >= 0; i--) {
    const d = drawings[i];
    if (d.hidden) continue;
    const g = geom(d);
    if (g.kind === "h" && near(y, g.y, 6)) return d;
    if (g.kind === "v" && near(x, g.x, 6)) return d;
    if (g.kind === "path") {
      for (let k = 1; k < g.pts.length; k++) {
        if (distToSeg(x, y, g.pts[k - 1], g.pts[k]) <= 6) return d;
      }
      continue;
    }
    if (g.kind !== "seg") continue;
    if (d.type === "ray" || d.type === "extended") {
      const [p, q] = project(g.a, g.b, g.right, d.type === "extended");
      if (distToSeg(x, y, p, q) <= 6) return d;
      continue;
    }
    if (d.type === "channel") {
      const off = g.c ? g.c[1] - g.b[1] : 0;
      if (distToSeg(x, y, g.a, g.b) <= 6) return d;
      if (distToSeg(x, y, [g.a[0], g.a[1] + off], [g.b[0], g.b[1] + off]) <= 6) return d;
      continue;
    }
    if (d.type === "ellipse") {
      const rx = Math.abs(g.b[0] - g.a[0]) / 2, ry = Math.abs(g.b[1] - g.a[1]) / 2;
      const mx = (g.a[0] + g.b[0]) / 2, my = (g.a[1] + g.b[1]) / 2;
      if (rx > 0 && ry > 0) {
        const t = ((x - mx) / rx) ** 2 + ((y - my) / ry) ** 2;
        if (t > 0.75 && t < 1.35) return d;
      }
      continue;
    }
    if (d.type === "fibext") {
      const x0 = Math.min(g.a[0], g.b[0]), x1 = Math.max(g.a[0], g.b[0]);
      const y0 = Math.min(g.a[1], g.b[1]), y1 = Math.max(g.a[1], g.b[1]);
      if (x >= x0 - 6 && x <= x1 + 6 && y >= y0 - 6 && y <= y1 + 6) return d;
      continue;
    }
    if (d.type === "text") {
      ctx.font = "12px " + C.sans;
      const w = ctx.measureText(d.text || "").width;
      if (x >= g.a[0] && x <= g.a[0] + w + 10 && near(y, g.a[1], 10)) return d;
      continue;
    }
    if (d.type === "rect" || d.type === "fib") {
      const x0 = Math.min(g.a[0], g.b[0]), x1 = Math.max(g.a[0], g.b[0]);
      const y0 = Math.min(g.a[1], g.b[1]), y1 = Math.max(g.a[1], g.b[1]);
      const onEdge = (near(x, x0, 6) || near(x, x1, 6)) && y >= y0 - 6 && y <= y1 + 6
                  || (near(y, y0, 6) || near(y, y1, 6)) && x >= x0 - 6 && x <= x1 + 6;
      if (onEdge) return d;
      if (d.type === "fib" && x >= x0 && x <= x1 && y >= y0 && y <= y1) return d;
      continue;
    }
    if (distToSeg(x, y, g.a, g.b) <= 6) return d;
  }
  return null;
}

const ONE_POINT = { hray: 1, vline: 1, text: 1 };
const THREE_POINT = { channel: 1 };
function startDraft(x, y) {
  const a = snapAnchor(x, y);
  const id = Date.now() + "-" + Math.random().toString(36).slice(2, 7);
  if (tool === "text") {
    const t = window.prompt("Text");
    if (!t) return;
    pushUndo();
    drawings.push({ id, type: "text", pts: [a], text: t });
    saveDrawings();
    setTool("cross");
    return;
  }
  if (ONE_POINT[tool]) {
    pushUndo();
    drawings.push({ id, type: tool, pts: [a] });
    saveDrawings();
    setTool("cross");
    return;
  }
  draft = { id, type: tool, pts: tool === "brush" ? [a] : [a, a] };
}

// A handle of the selected drawing, if the pointer is on one.
function handleAt(x, y) {
  if (!selected) return -1;
  const g = geom(selected);
  const pts = g.kind === "path" ? [g.pts[0]]
            : g.kind === "seg" ? [g.a, g.b].concat(g.c ? [[g.b[0], g.c[1]]] : [])
            : [];
  for (let i = 0; i < pts.length; i++) {
    if (Math.hypot(x - pts[i][0], y - pts[i][1]) <= 7) return i;
  }
  return -1;
}

// ============================================================= interaction ==
function barAt(px) {
  if (!box) return null;
  const i = Math.round(box.startF + (px - box.PAD_L) / box.bw - 0.5);
  return { i: clamp(i, box.i0, box.i1), iv: box.iv };
}
const DRAW_TOOLS = {
  trend: 1, ray: 1, extended: 1, hray: 1, vline: 1, channel: 1, rect: 1,
  ellipse: 1, arrow: 1, fib: 1, fibext: 1, brush: 1, text: 1, measure: 1,
};

cv.addEventListener("pointerdown", (e) => {
  if (e.button !== 0 || !box) return;
  $("panel").focus();
  const r = cv.getBoundingClientRect();
  const x = e.clientX - r.left, y = e.clientY - r.top;
  cv.setPointerCapture(e.pointerId);

  if (x > box.W - PAD_R) {                 // the price scale scales by dragging
    scaleDrag = { y, lo: box.lo, hi: box.hi };
    return;
  }
  if (DRAW_TOOLS[tool]) { startDraft(x, y); render(); return; }

  const hIdx = handleAt(x, y);
  if (hIdx >= 0) {
    pushUndo();
    grab = { x, y, pts: selected.pts.map((p) => ({ ...p })), handle: hIdx };
    render();
    return;
  }
  const hit = hitTest(x, y);
  if (hit) {
    selected = hit;
    pushUndo();
    grab = { x, y, pts: hit.pts.map((p) => ({ ...p })), handle: -1 };
    render();
    return;
  }
  selected = null;
  drag = { px: e.clientX, from: vp.from, to: vp.to };
});

cv.addEventListener("pointermove", (e) => {
  if (!box) return;
  const r = cv.getBoundingClientRect();
  const x = e.clientX - r.left, y = e.clientY - r.top;

  if (scaleDrag) {
    const k = Math.exp((y - scaleDrag.y) / 160);
    const mid = (scaleDrag.lo + scaleDrag.hi) / 2;
    const half = ((scaleDrag.hi - scaleDrag.lo) / 2) * k;
    manualScale = { lo: mid - half, hi: mid + half };
    render();
    return;
  }
  if (draft) {
    if (draft.type === "brush") draft.pts.push(toAnchor(x, y));
    else draft.pts[1] = snapAnchor(x, y);
    render();
    return;
  }
  if (grab) {
    const da = toAnchor(x, y), o = toAnchor(grab.x, grab.y);
    if (grab.handle >= 0) {
      const pts = grab.pts.map((p) => ({ ...p }));
      // The channel's third anchor only carries its width, so it tracks price.
      if (selected.type === "channel" && grab.handle === 2) pts[2] = { t: pts[1].t, p: da.p };
      else pts[grab.handle] = snapAnchor(x, y);
      selected.pts = pts;
    } else {
      selected.pts = grab.pts.map((p) => ({ t: p.t + (da.t - o.t), p: p.p + (da.p - o.p) }));
    }
    render();
    return;
  }
  if (drag) {
    const moved = e.clientX - drag.px;
    if (!dragging && Math.abs(moved) < 3) return;
    dragging = true;
    cv.classList.add("drag");
    const shift = (moved / box.iw) * (drag.to - drag.from);
    vp = { from: drag.from - shift, to: drag.to - shift };
    clampViewport();
    hover = null;
    render();
    return;
  }
  const next = barAt(x);
  if (next) { next.y = y; }
  hover = next;
  render();
});

function endPointer(e) {
  if (draft) {
    if (draft.type === "measure") { draft = null; }      // measure is transient
    else {
      const a = draft.pts[0], b = draft.pts[draft.pts.length - 1];
      const moved = Math.abs(idxAt(box.s, a.t) - idxAt(box.s, b.t)) > 0.3
                 || Math.abs(a.p - b.p) > 1e-9;
      if (moved && (draft.type !== "brush" || draft.pts.length > 2)) {
        if (THREE_POINT[draft.type]) {
          // Open the channel with a visible default width; its handle tunes it.
          draft.pts.push({ t: draft.pts[1].t, p: draft.pts[1].p - (box.hi - box.lo) * 0.08 });
        }
        pushUndo();
        drawings.push(draft);
        selected = draft;
        saveDrawings();
      }
      draft = null;
      setTool("cross");
    }
  }
  if (grab) { saveDrawings(); grab = null; }
  scaleDrag = null;
  drag = null; dragging = false;
  cv.classList.remove("drag");
  if (e && cv.hasPointerCapture(e.pointerId)) cv.releasePointerCapture(e.pointerId);
  render();
}
cv.addEventListener("pointerup", endPointer);
cv.addEventListener("pointercancel", endPointer);
cv.addEventListener("pointerleave", () => {
  if (!dragging && !draft && !grab && hover !== null) { hover = null; render(); }
});

cv.addEventListener("wheel", (e) => {
  e.preventDefault();
  if (!box) return;
  const px = e.clientX - cv.getBoundingClientRect().left;
  const span = vp.to - vp.from;
  if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
    const shift = (e.deltaX / box.iw) * span;
    vp = { from: vp.from + shift, to: vp.to + shift };
  } else {
    const at = vp.from + clamp((px - box.PAD_L) / box.iw, 0, 1) * span;
    const f = e.deltaY > 0 ? 1.15 : 1 / 1.15;
    vp = { from: at - (at - vp.from) * f, to: at + (vp.to - at) * f };
  }
  clampViewport();
  render();
  hover = barAt(px);
  render();
}, { passive: false });

cv.addEventListener("dblclick", (e) => {
  const x = e.clientX - cv.getBoundingClientRect().left;
  if (box && x > box.W - PAD_R) { manualScale = null; render(); return; }
  vp = { ...preset }; hover = null; render();
});

window.addEventListener("keydown", (e) => {
  const k = e.key.toLowerCase();
  if (e.ctrlKey || e.metaKey) {
    if (k === "z") { e.preventDefault(); undo(); }
    else if (k === "y") { e.preventDefault(); redo(); }
    return;
  }
  if (k === "escape") { draft = null; selected = null; setTool("cross"); render(); }
  else if (k === "delete" || k === "backspace") {
    if (selected) {
      e.preventDefault();
      pushUndo();
      drawings = drawings.filter((d) => d !== selected);
      selected = null; saveDrawings(); render();
    }
  }
  else if (k === "t") setTool("trend");
  else if (k === "h") setTool("hray");
  else if (k === "v") setTool("vline");
  else if (k === "r") setTool("rect");
  else if (k === "f" && e.shiftKey) { manualScale = null; render(); }
  else if (k === "f") toggleFullscreen();
  else if (k === "m") { magnet = !magnet; crossMode = magnet ? "magnet" : "normal"; savePrefs(); syncChips(); toast("Magnet " + (magnet ? "on" : "off")); }
  else if (k === "s") screenshot();
  else if (k === "d") { dataWin = !dataWin; savePrefs(); render(); }
  else if (k === "p") setReplay(!replay);
  else if (k === " ") { e.preventDefault(); togglePlay(); }
  else if (k === "arrowleft" && replay) { e.preventDefault(); stepReplay(-1); }
  else if (k === "arrowright" && replay) { e.preventDefault(); stepReplay(1); }
  else if (k === "l") { scale = scale === "log" ? "auto" : "log"; savePrefs(); render(); }
});

function undo() {
  if (!undoStack.length) return;
  redoStack.push(JSON.stringify(drawings));
  drawings = JSON.parse(undoStack.pop());
  selected = null; saveDrawings(); render();
}
function redo() {
  if (!redoStack.length) return;
  undoStack.push(JSON.stringify(drawings));
  drawings = JSON.parse(redoStack.pop());
  selected = null; saveDrawings(); render();
}
function toggleFullscreen() {
  const el = document.documentElement;
  if (document.fullscreenElement) document.exitFullscreen();
  else if (el.requestFullscreen) el.requestFullscreen().catch(() => toast("Fullscreen blocked"));
}
function screenshot() {
  const W = cv.clientWidth, pad = 12, headH = 34;
  const out = document.createElement("canvas");
  const dpr = window.devicePixelRatio || 1;
  out.width = (W + pad * 2) * dpr;
  out.height = (CHART_H + headH + pad * 2) * dpr;
  const o = out.getContext("2d");
  o.scale(dpr, dpr);
  o.fillStyle = C.panel;
  o.fillRect(0, 0, W + pad * 2, CHART_H + headH + pad * 2);
  o.fillStyle = C.text;
  o.font = "600 13px " + C.mono;
  o.textBaseline = "middle";
  o.fillText(`${SYMBOL} · ${interval} · DSE`, pad, pad + 13);
  o.fillStyle = C.axisText;
  o.font = "11px " + C.mono;
  o.fillText($("caption").textContent, pad, pad + 29);
  o.drawImage(cv, 0, 0, cv.width, cv.height, pad, pad + headH, W, CHART_H);
  const a = document.createElement("a");
  a.download = `${SYMBOL}-${interval}-${new Date().toISOString().slice(0, 10)}.png`;
  a.href = out.toDataURL("image/png");
  a.click();
  toast("Chart image saved");
}
</script>
"""

_SCRIPT4 = r"""
<script>
// ================================================================ readout ===
function readout(s, real, i, maxV, i0, i1, iv) {
  const bars = s.bars;
  const cur = bars[i], prev = bars[i - 1] || cur;
  const chg = cur[4] - prev[4];
  const tone = chg >= 0 ? C.up : C.down;
  const typeName = (TYPES.find((t) => t.key === chartType) || {}).label || "";

  $("head").innerHTML =
    `<span class="ctx">${SYMBOL} · ${interval} · DSE · ${typeName}</span>` +
    `<span class="k">O <b>${fmt(cur[1])}</b></span>` +
    `<span class="k">H <b>${fmt(cur[2])}</b></span>` +
    `<span class="k">L <b>${fmt(cur[3])}</b></span>` +
    `<span class="k">C <b>${fmt(cur[4])}</b></span>` +
    `<span style="color:${tone}">${chg >= 0 ? "+" : ""}${fmt(chg)} ` +
    `(${fmt(prev[4] ? (chg / prev[4]) * 100 : 0)}%)</span>`;

  const u = volUnit(maxV);
  const rows = [];
  for (const d of STUDY_DEFS) {
    if (!studies[d.key].on) continue;
    const p = studies[d.key].inputs;
    if (d.key === "volume") { rows.push([d.key, C.up, "Volume", `${fmt(real.bars[i][5] / u.div, 2)}${u.suffix}`]); continue; }
    const v = study(d.key, iv);
    if (d.key === "bb") rows.push([d.key, C.band, `BB ${p.n} ${p.k}`,
      `${fmt(v.up[i], 1)} · ${fmt(v.mid[i], 1)} · ${fmt(v.lo[i], 1)}`]);
    else if (d.key === "sma") rows.push([d.key, C.sma, `SMA ${p.n}`, fmt(v.line[i], 1)]);
    else if (d.key === "ema") rows.push([d.key, C.ema, `EMA ${p.n}`, fmt(v.line[i], 1)]);
    else if (d.key === "vwap") rows.push([d.key, C.vwap, `VWAP ${p.n}`, fmt(v.line[i], 1)]);
    else if (d.key === "rsi") rows.push([d.key, C.rsi, `RSI ${p.n}`, fmt(v.line[i])]);
    else if (d.key === "macd") rows.push([d.key, C.rsi, `MACD ${p.fast} ${p.slow} ${p.signal}`,
      `${fmt(v.line[i])} · ${fmt(v.sig[i])}`]);
    else if (d.key === "stoch") rows.push([d.key, C.rsi, `Stoch ${p.n} ${p.d}`,
      `${fmt(v.k[i])} · ${fmt(v.d[i])}`]);
    else if (d.key === "atr") rows.push([d.key, C.sma, `ATR ${p.n}`, fmt(v.line[i])]);
    else if (d.key === "obv") rows.push([d.key, C.vwap, "OBV", compact(v.line[i])]);
    else if (d.key === "keltner") rows.push([d.key, C.ema, `KC ${p.n} ${p.k}`,
      `${fmt(v.up[i], 1)} \u00b7 ${fmt(v.lo[i], 1)}`]);
    else if (d.key === "donchian") rows.push([d.key, C.sma, `DC ${p.n}`,
      `${fmt(v.up[i], 1)} \u00b7 ${fmt(v.lo[i], 1)}`]);
    else if (d.key === "supertrend") rows.push([d.key, v.dir[i] > 0 ? C.up : C.down,
      `Supertrend ${p.n} ${p.k}`, fmt(v.line[i], 1)]);
    else if (d.key === "psar") rows.push([d.key, C.sma, "PSAR", fmt(v.line[i], 1)]);
    else if (d.key === "ichimoku") rows.push([d.key, C.band, "Ichimoku",
      `${fmt(v.conv[i], 1)} \u00b7 ${fmt(v.base[i], 1)}`]);
    else if (d.key === "adx") rows.push([d.key, C.rsi, `ADX ${p.n}`,
      `${fmt(v.adx[i])} \u00b7 +${fmt(v.pdi[i], 1)} \u00b7 -${fmt(v.ndi[i], 1)}`]);
    else if (d.key === "cci") rows.push([d.key, C.sma, `CCI ${p.n}`, fmt(v.line[i])]);
    else if (d.key === "willr") rows.push([d.key, C.rsi, `%R ${p.n}`, fmt(v.line[i])]);
    else if (d.key === "mfi") rows.push([d.key, C.rsi, `MFI ${p.n}`, fmt(v.line[i])]);
    else if (d.key === "roc") rows.push([d.key, C.sma, `ROC ${p.n}`, fmt(v.line[i]) + "%"]);
    else if (d.key === "stddev") rows.push([d.key, C.sma, `SD ${p.n}`, fmt(v.line[i])]);
  }
  $("legend").innerHTML = rows.map(([key, c, l, v]) =>
    `<div class="row"><span class="sw" style="background:${c}"></span>` +
    `<span class="lb">${l}</span><span class="vl">${v}</span>` +
    `<span class="x" data-off="${key}" title="Remove">×</span></div>`).join("");
  for (const x of $("legend").querySelectorAll(".x")) {
    x.addEventListener("click", () => { studies[x.dataset.off].on = false; savePrefs(); render(); });
  }

  renderDataWindow(rows, cur, prev, real.bars[i], iv);
  renderStyleBar();

  const bits = [`${fullDate(bars[i0][0])} → ${fullDate(bars[i1][0])}`, `${i1 - i0 + 1} bars`];
  if (!atPreset()) bits.push("panned");
  if (manualScale) bits.push("manual scale");
  if (drawings.length) bits.push(`${drawings.length} drawing${drawings.length > 1 ? "s" : ""}`);
  if (SOURCE) bits.push(SOURCE);
  if (replay) bits.push("replay");
  $("caption").textContent = bits.join(" · ");
}

// The data window is TradingView's idea: every number under the cursor, in one
// column, instead of squinting at the legend.
function renderDataWindow(rows, cur, prev, realBar, iv) {
  const w = $("datawin");
  w.classList.toggle("on", dataWin);
  if (!dataWin) return;
  const chg = cur[4] - prev[4];
  const pct = prev[4] ? (chg / prev[4]) * 100 : 0;
  const u = volUnit(realBar[5]);
  const row = (k, v, col) =>
    `<div class="r"><span>${k}</span><span${col ? ` style="color:${col}"` : ""}>${v}</span></div>`;
  w.innerHTML =
    `<h4>${SYMBOL} · ${interval}</h4>` +
    row("Date", fullDate(cur[0])) +
    row("Open", fmt(cur[1])) + row("High", fmt(cur[2])) +
    row("Low", fmt(cur[3])) + row("Close", fmt(cur[4])) +
    row("Change", `${chg >= 0 ? "+" : ""}${fmt(chg)}`, chg >= 0 ? C.up : C.down) +
    row("Change %", `${fmt(pct)}%`, chg >= 0 ? C.up : C.down) +
    row("Volume", `${fmt(realBar[5] / u.div, 2)}${u.suffix}`) +
    (rows.length ? `<div class="sec"><h4>Indicators</h4>` +
      rows.map((r) => row(r[2], r[3], r[1])).join("") + `</div>` : "");
}

// The style bar follows the selected drawing, the way TradingView's does.
function renderStyleBar() {
  const bar = $("stylebar");
  if (!selected || !box) { bar.classList.remove("on"); return; }
  const g = geom(selected);
  const anchor = g.kind === "h" ? [box.iw / 2, g.y]
               : g.kind === "v" ? [g.x, 30]
               : g.kind === "path" ? g.pts[0]
               : [(g.a[0] + g.b[0]) / 2, Math.min(g.a[1], g.b[1])];
  bar.innerHTML =
    C.drawColors.map((c) =>
      `<span class="sw" data-col="${c}" style="background:${c}" ` +
      `aria-pressed="${(selected.color || C.drawing) === c}"></span>`).join("") +
    `<span class="div"></span>` +
    [1, 2, 3].map((w) =>
      `<button class="chip" data-w="${w}" aria-pressed="${(selected.width || 1.3) === w}">${w}px</button>`).join("") +
    `<span class="div"></span>` +
    `<button class="chip" data-dash="1" aria-pressed="${!!selected.dash}">dash</button>` +
    `<button class="chip" data-del="1" title="Delete (Del)">✕</button>`;
  bar.style.left = clamp(anchor[0] - 110, 4, Math.max(4, box.iw - 230)) + "px";
  bar.style.top = clamp(anchor[1] - 44, 4, CHART_H - 40) + "px";
  bar.classList.add("on");
  for (const el of bar.querySelectorAll("[data-col]")) {
    el.addEventListener("click", () => { pushUndo(); selected.color = el.dataset.col; saveDrawings(); render(); });
  }
  for (const el of bar.querySelectorAll("[data-w]")) {
    el.addEventListener("click", () => { pushUndo(); selected.width = +el.dataset.w; saveDrawings(); render(); });
  }
  bar.querySelector("[data-dash]").addEventListener("click",
    () => { pushUndo(); selected.dash = !selected.dash; saveDrawings(); render(); });
  bar.querySelector("[data-del]").addEventListener("click", () => {
    pushUndo();
    drawings = drawings.filter((d) => d !== selected);
    selected = null; saveDrawings(); render();
  });
}

function render() { draw(); syncChips(); }

// ================================================================= chrome ===
function setTool(t) {
  tool = t;
  cv.classList.toggle("draw", !!DRAW_TOOLS[t]);
  syncChips();
}

function syncChips() {
  for (const b of $("intervals").children) b.setAttribute("aria-pressed", String(b.dataset.key === interval));
  for (const b of $("ranges").children) b.setAttribute("aria-pressed", String(atPreset() && b.dataset.key === range.label));
  for (const b of $("studies").children) b.setAttribute("aria-pressed", String(!!studies[b.dataset.study].on));
  for (const b of $("scales").children) b.setAttribute("aria-pressed", String(b.dataset.scale === scale));
  for (const b of $("rail").querySelectorAll("button")) {
    const k = b.dataset.tool;
    b.setAttribute("aria-pressed", String(k === "magnet" ? magnet : k === tool));
  }
  $("typeBtn").innerHTML = ((TYPES.find((t) => t.key === chartType) || {}).label || "") + " ▾";
  $("undoBtn").disabled = !undoStack.length;
  $("redoBtn").disabled = !redoStack.length;
}

function closeMenus(except) {
  for (const id of ["typeMenu", "indMenu", "treeMenu", "setMenu"]) if (id !== except) $(id).classList.remove("on");
}
function openMenu(id, anchor) {
  const m = $(id);
  const was = m.classList.contains("on");
  closeMenus();
  if (was) return;
  const r = anchor.getBoundingClientRect(), pr = $("panel").getBoundingClientRect();
  m.classList.add("on");
  // Menus anchored to the right-hand action icons would otherwise run off the
  // panel, so the left edge is clamped once the menu has a measurable width.
  const w = m.offsetWidth || 220;
  m.style.left = clamp(r.left - pr.left, 6, Math.max(6, pr.width - w - 6)) + "px";
  m.style.top = (r.bottom - pr.top + 4) + "px";
}
document.addEventListener("pointerdown", (e) => {
  if (!e.target.closest(".menu") && !e.target.closest("#actions") && !e.target.closest("#typeBtn") && !e.target.closest("#indBtn")) closeMenus();
}, true);

// chart-type menu
$("typeMenu").innerHTML = TYPES.map((t) =>
  `<button class="item" data-type="${t.key}"><span class="tick"></span>${t.label}</button>`).join("");
for (const b of $("typeMenu").querySelectorAll("[data-type]")) {
  b.addEventListener("click", () => {
    chartType = b.dataset.type;
    closeMenus(); savePrefs(); render();
  });
}
$("typeBtn").addEventListener("click", () => {
  for (const b of $("typeMenu").querySelectorAll("[data-type]")) {
    b.querySelector(".tick").textContent = b.dataset.type === chartType ? "✓" : "";
  }
  openMenu("typeMenu", $("typeBtn"));
});

// indicator menu, with each study's inputs inline
function buildIndMenu() {
  const groups = { overlay: "Overlays", pane: "Oscillators & volume" };
  let html = "";
  for (const where of ["overlay", "pane"]) {
    html += `<div class="grp">${groups[where]}</div>`;
    for (const d of STUDY_DEFS.filter((x) => x.where === where)) {
      const on = studies[d.key].on;
      html += `<button class="item" data-study="${d.key}">` +
              `<span class="tick">${on ? "✓" : ""}</span>${d.name}</button>`;
      if (d.inputs.length) {
        html += `<div class="inputs">` + d.inputs.map((i) =>
          `<label>${i.label}<input type="number" min="1" data-in="${d.key}:${i.key}" ` +
          `value="${studies[d.key].inputs[i.key]}"></label>`).join("") + `</div>`;
      }
    }
  }
  $("indMenu").innerHTML = html;
  for (const b of $("indMenu").querySelectorAll("[data-study]")) {
    b.addEventListener("click", () => {
      const k = b.dataset.study;
      studies[k].on = !studies[k].on;
      savePrefs(); buildIndMenu(); $("indMenu").classList.add("on"); render();
    });
  }
  for (const inp of $("indMenu").querySelectorAll("[data-in]")) {
    inp.addEventListener("change", () => {
      const [k, field] = inp.dataset.in.split(":");
      const v = Math.max(1, Math.round(+inp.value || 1));
      inp.value = v;
      studies[k].inputs[field] = v;
      savePrefs(); render();
    });
    inp.addEventListener("pointerdown", (e) => e.stopPropagation());
  }
}
$("indBtn").addEventListener("click", () => { buildIndMenu(); openMenu("indMenu", $("indBtn")); });

// interval / range / quick-study / scale chips
function chipRow(host, items, onPick) {
  host.innerHTML = "";
  for (const it of items) {
    const b = document.createElement("button");
    b.className = "chip";
    b.textContent = it.label;
    b.dataset.key = it.label;
    b.addEventListener("click", () => { onPick(it); render(); });
    host.appendChild(b);
  }
}
chipRow($("intervals"), INTERVALS, (it) => { interval = it.label; hover = null; savePrefs(); });
chipRow($("ranges"), RANGES, (it) => setRange(it));

for (const key of ["bb", "volume", "rsi"]) {
  const d = STUDY_DEFS.find((x) => x.key === key);
  const b = document.createElement("button");
  b.className = "chip";
  b.textContent = d.label;
  b.dataset.study = key;
  b.title = d.name;
  b.addEventListener("click", () => { studies[key].on = !studies[key].on; savePrefs(); render(); });
  $("studies").appendChild(b);
}

for (const [label, mode] of [["%", "percent"], ["log", "log"], ["auto", "auto"]]) {
  const b = document.createElement("button");
  b.className = "chip";
  b.textContent = label;
  b.dataset.scale = mode;
  b.addEventListener("click", () => { scale = mode; manualScale = null; savePrefs(); render(); });
  $("scales").appendChild(b);
}

// tool rail
for (const t of TOOL_DEFS) {
  const b = document.createElement("button");
  b.title = t.name;
  b.textContent = t.glyph;
  b.dataset.tool = t.key;
  b.addEventListener("click", () => {
    if (t.key === "magnet") { magnet = !magnet; crossMode = magnet ? "magnet" : "normal"; savePrefs(); syncChips(); toast("Magnet " + (magnet ? "on" : "off")); }
    else setTool(t.key);
  });
  $("rail").appendChild(b);
}
const sep = document.createElement("div");
sep.className = "sep";
$("rail").appendChild(sep);
const clearBtn = document.createElement("button");
clearBtn.title = "Remove all drawings";
clearBtn.textContent = "⌦";
clearBtn.dataset.tool = "clear";
clearBtn.addEventListener("click", () => {
  if (!drawings.length) return;
  pushUndo();
  drawings = []; selected = null; saveDrawings(); render();
  toast("Drawings cleared");
});
$("rail").appendChild(clearBtn);

// ================================================================= replay ===
function replayIndex() {
  const s2 = dispSeries();
  return clamp(Math.floor(idxAt(s2, replayT)), 0, s2.bars.length - 1);
}
function setReplay(on) {
  replay = on;
  $("replay").classList.toggle("on", on);
  $("replayBtn").setAttribute("aria-pressed", String(on));
  if (on) {
    // Start where the crosshair is, or midway through the window.
    const s2 = dispSeries();
    const i = hover && hover.iv === ivKey() ? hover.i
            : Math.floor((idxAt(s2, vp.from) + idxAt(s2, vp.to)) / 2);
    replayT = s2.bars[clamp(i, 0, s2.bars.length - 1)][6];
    toast("Replay from " + fullDate(s2.bars[clamp(i, 0, s2.bars.length - 1)][0]));
  } else {
    stopPlay();
    replayT = null;
  }
  render();
}
function stepReplay(n) {
  if (!replay) return;
  const s2 = dispSeries();
  const i = clamp(replayIndex() + n, 0, s2.bars.length - 1);
  replayT = s2.bars[i][6];
  if (i >= s2.bars.length - 1) stopPlay();
  render();
}
function stopPlay() {
  playing = false;
  clearInterval(playTimer);
  playTimer = null;
  $("playBtn").innerHTML = "▶";
}
function togglePlay() {
  if (!replay) setReplay(true);
  if (playing) { stopPlay(); return; }
  playing = true;
  $("playBtn").innerHTML = "‖";
  playTimer = setInterval(() => stepReplay(1), 700 / speed);
}
$("replayBtn").addEventListener("click", () => setReplay(!replay));
$("rwBtn").addEventListener("click", () => stepReplay(-1));
$("ffBtn").addEventListener("click", () => stepReplay(1));
$("playBtn").addEventListener("click", togglePlay);
$("exitBtn").addEventListener("click", () => setReplay(false));
$("speedBtn").addEventListener("click", () => {
  speed = speed === 1 ? 2 : speed === 2 ? 4 : 1;
  $("speedBtn").textContent = speed + "×";
  if (playing) { stopPlay(); togglePlay(); }
});

// ============================================================ object tree ===
function buildTree() {
  const m = $("treeMenu");
  if (!drawings.length) {
    m.innerHTML = `<div class="grp">Objects</div><div class="item">No drawings yet</div>`;
    return;
  }
  const label = (d) => (TOOL_DEFS.find((t) => t.key === d.type) || {}).name || d.type;
  m.innerHTML = `<div class="grp">Objects</div>` + drawings.map((d, i) =>
    `<button class="item" data-pick="${i}">` +
    `<span class="tick" style="color:${d.color || C.drawing}">●</span>` +
    `${label(d)} <span style="margin-left:auto; color:${C.axisText}">` +
    `${d.hidden ? "hidden" : ""}</span></button>` +
    `<div class="inputs" style="padding-left:30px">` +
    `<button class="chip" data-hide="${i}">${d.hidden ? "show" : "hide"}</button>` +
    `<button class="chip" data-drop="${i}">delete</button></div>`).join("");
  for (const b of m.querySelectorAll("[data-pick]")) {
    b.addEventListener("click", () => { selected = drawings[+b.dataset.pick]; closeMenus(); render(); });
  }
  for (const b of m.querySelectorAll("[data-hide]")) {
    b.addEventListener("click", () => {
      const d = drawings[+b.dataset.hide];
      pushUndo(); d.hidden = !d.hidden; saveDrawings(); buildTree(); render();
    });
  }
  for (const b of m.querySelectorAll("[data-drop]")) {
    b.addEventListener("click", () => {
      pushUndo();
      const d = drawings[+b.dataset.drop];
      drawings = drawings.filter((x) => x !== d);
      if (selected === d) selected = null;
      saveDrawings(); buildTree(); render();
    });
  }
}
$("treeBtn").addEventListener("click", () => { buildTree(); openMenu("treeMenu", $("treeBtn")); });

// =============================================================== settings ===
function buildSettings() {
  $("setMenu").innerHTML =
    `<div class="grp">Chart</div>` +
    `<button class="item" data-set="grid"><span class="tick">${showGrid ? "✓" : ""}</span>Grid lines</button>` +
    `<button class="item" data-set="invert"><span class="tick">${invert ? "✓" : ""}</span>Invert price scale</button>` +
    `<button class="item" data-set="data"><span class="tick">${dataWin ? "✓" : ""}</span>Data window</button>` +
    `<div class="grp">Crosshair</div>` +
    ["normal", "magnet", "none"].map((mode) =>
      `<button class="item" data-cross="${mode}"><span class="tick">` +
      `${crossMode === mode ? "✓" : ""}</span>${mode[0].toUpperCase() + mode.slice(1)}</button>`).join("") +
    `<div class="grp">Go to</div>` +
    `<div class="inputs"><label>Date<input type="date" data-goto="1" style="width:120px"></label></div>`;
  for (const b of $("setMenu").querySelectorAll("[data-set]")) {
    b.addEventListener("click", () => {
      const k = b.dataset.set;
      if (k === "grid") showGrid = !showGrid;
      else if (k === "invert") invert = !invert;
      else if (k === "data") dataWin = !dataWin;
      savePrefs(); buildSettings(); render();
    });
  }
  for (const b of $("setMenu").querySelectorAll("[data-cross]")) {
    b.addEventListener("click", () => {
      crossMode = b.dataset.cross;
      magnet = crossMode === "magnet";
      savePrefs(); buildSettings(); render();
    });
  }
  const go = $("setMenu").querySelector("[data-goto]");
  go.addEventListener("pointerdown", (e) => e.stopPropagation());
  go.addEventListener("change", () => {
    const t = Date.parse(go.value + "T00:00:00Z");
    if (!isFinite(t)) return;
    const span = vp.to - vp.from;
    vp = { from: t - span / 2, to: t + span / 2 };
    clampViewport();
    closeMenus();
    render();
  });
}
$("setBtn").addEventListener("click", () => { buildSettings(); openMenu("setMenu", $("setBtn")); });
$("dataBtn").addEventListener("click", () => { dataWin = !dataWin; savePrefs(); render(); });

$("undoBtn").addEventListener("click", undo);
$("redoBtn").addEventListener("click", redo);
$("shotBtn").addEventListener("click", screenshot);
$("fullBtn").addEventListener("click", toggleFullscreen);
$("fitBtn").addEventListener("click", () => { manualScale = null; render(); });

// =================================================================== boot ===
loadStore();
setRange(range);
setTool("cross");
render();
tickClock();
setInterval(tickClock, 1000);
new ResizeObserver(() => render()).observe(cv);
// Streamlit keeps inactive tab panels in the DOM, so this iframe can be laid
// out at zero width and revealed later. Retry until one draw actually lands.
const kick = setInterval(() => { if (box) clearInterval(kick); else render(); }, 250);
if (document.fonts) document.fonts.ready.then(render);
</script>
"""

_TEMPLATE = _MARKUP + _SCRIPT + _SCRIPT2 + _SCRIPT3 + _SCRIPT4


def render(symbol, bars, source=None):
    """HTML for the chart component, with the bars inlined as compact arrays."""
    payload = [
        [b["date"], b["open"], b["high"], b["low"], b["close"], b["volume"]]
        for b in bars
    ]
    span_days = 0
    if len(bars) > 1:
        span_days = (_to_date(bars[-1]["date"]) - _to_date(bars[0]["date"])).days

    offered = ranges_for(span_days)
    default_range = DEFAULT_RANGE
    if not any(r["label"] == default_range for r in offered):
        default_range = offered[-1]["label"]

    ch = theme.CHART
    colors = {
        "up": ch["up"], "down": ch["down"],
        "upFill": ch["up"] + "26", "downFill": ch["down"] + "26",
        "areaTop": ch["up"] + "4d", "areaBottom": ch["up"] + "00",
        "band": ch["band"], "bandMid": ch["band_mid"], "bandFill": ch["band_fill"] + "1a",
        "rsi": ch["rsi"], "rsiGuide": ch["rsi_guide"], "rsiZone": ch["rsi_zone"],
        "sma": ch["sma"], "ema": ch["ema"], "vwap": ch["vwap"],
        "fib": ch["fib"],
        "drawing": ch["drawing"],
        "drawColors": DRAW_COLORS,
        "grid": ch["grid"], "gridTime": ch["grid_time"], "axisText": ch["axis_text"],
        "crosshair": ch["crosshair"], "crosshairTag": ch["crosshair_tag"],
        "accent": "#49d3a1",      # ACCENT in sRGB
        "accentInk": "#07100c",   # the design's ink on accent
        "panel": ch["panel"],
        "text": theme.TEXT, "bg": theme.BG,
        "mono": theme.MONO, "sans": theme.SANS,
    }
    defaults = {
        "interval": DEFAULT_INTERVAL,
        "range": default_range,
        "type": DEFAULT_TYPE,
        "studies": DEFAULT_STUDIES,
    }
    substitutions = {
        "__SYMBOL_JSON__": json.dumps(symbol),
        "__SYMBOL__": symbol,
        "__BARS__": json.dumps(payload, separators=(",", ":")),
        "__RANGES__": json.dumps(offered),
        "__INTERVALS__": json.dumps(INTERVALS),
        "__TYPES__": json.dumps(CHART_TYPES),
        "__STUDIES__": json.dumps(STUDIES),
        "__TOOLS__": json.dumps(TOOLS),
        "__COLORS__": json.dumps(colors),
        "__DEFAULTS__": json.dumps(defaults),
        "__SOURCE__": json.dumps(source or ""),
        "__CHART_H__": str(CHART_H),
        "__SANS__": theme.SANS,
        "__MONO__": theme.MONO,
        "__BG__": theme.BG,
        "__PANEL__": theme.CHART["panel"],
        "__CARD__": theme.CARD,
        "__FIELD__": theme.FIELD,
        "__LINE__": theme.LINE,
        "__BORDER__": theme.BORDER,
        "__HOVER__": theme.LINE_SOFT,
        "__TEXT__": theme.TEXT,
        "__TEXT_DIM__": theme.TEXT_DIM,
        "__MUTED_2__": theme.MUTED_2,
        "__MUTED_3__": theme.MUTED_3,
        "__AXIS__": theme.CHART["axis_text"],
        "__LEGEND_VALUE__": theme.CHART["legend_value"],
        "__UP__": theme.CHART["up"],
        "__ACCENT__": theme.ACCENT,
        "__ACCENT_WASH__": theme.tint(theme.ACCENT, 13),
        "__ACCENT_WASH_15__": theme.tint(theme.ACCENT, 15),
    }
    html = _TEMPLATE
    for token, value in substitutions.items():
        html = html.replace(token, value)
    return html


def _to_date(iso):
    from datetime import date
    return date(int(iso[0:4]), int(iso[5:7]), int(iso[8:10]))
