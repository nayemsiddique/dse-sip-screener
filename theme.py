"""Design tokens and CSS for the DSE Screener shell.

Ported from the `DSE Stock Analyzer.dc.html` design-system file: the palette,
type scale and component shapes are the design's, expressed as Streamlit CSS.
"""

ACCENT = "oklch(0.78 0.14 165)"
ACCENT_BRIGHT = "oklch(0.84 0.14 165)"
ACCENT_TEXT = "oklch(0.85 0.13 165)"
WARN = "oklch(0.8 0.12 85)"
FAIL = "oklch(0.7 0.16 25)"

BG = "#0b0c0e"
PANEL = "#0f1013"
CARD = "#101216"
FIELD = "#15171b"
LINE = "#1d1f24"
LINE_SOFT = "#16181c"
BORDER = "#272a31"
TEXT = "#e8e9ec"
TEXT_DIM = "#b9bec7"
MUTED = "#8b909a"
MUTED_2 = "#787d87"
MUTED_3 = "#5f636b"
FAINT = "#4f535a"

SANS = "'IBM Plex Sans',system-ui,sans-serif"
MONO = "'IBM Plex Mono',ui-monospace,monospace"


def tint(color: str, pct: float) -> str:
    """The design's `color-mix` helper, used for pill and bar washes."""
    return f"color-mix(in oklch, {color} {pct}%, transparent)"


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
  --accent: oklch(0.78 0.14 165);
  --accent-bright: oklch(0.84 0.14 165);
  --warn: oklch(0.8 0.12 85);
  --fail: oklch(0.7 0.16 25);
  --bg: #0b0c0e;
  --panel: #0f1013;
  --card: #101216;
  --field: #15171b;
  --line: #1d1f24;
  --line-soft: #16181c;
  --border: #272a31;
  --text: #e8e9ec;
  --text-dim: #b9bec7;
  --muted: #8b909a;
  --muted-2: #787d87;
  --muted-3: #5f636b;
  --sans: 'IBM Plex Sans', system-ui, sans-serif;
  --mono: 'IBM Plex Mono', ui-monospace, monospace;
}

html, body, [data-testid="stAppViewContainer"] {
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  -webkit-font-smoothing: antialiased;
}
* { box-sizing: border-box; }

/* Streamlit chrome: the design has its own header bar, so collapse the default
   one to nothing. It can't be display:none — the button that re-opens a
   collapsed sidebar lives inside it, so the header stays as a zero-height,
   click-through overlay and only its actions are hidden. */
[data-testid="stHeader"] {
  background: transparent;
  height: 0;
  min-height: 0;
  pointer-events: none;
}
[data-testid="stToolbar"] { pointer-events: none; }
[data-testid="stToolbarActions"],
[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"] { display: none; }
footer { display: none; }

button[data-testid="stExpandSidebarButton"] {
  pointer-events: auto;
  position: fixed;
  top: 12px;
  left: 12px;
  z-index: 1000;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-dim);
}
button[data-testid="stExpandSidebarButton"]:hover {
  background: var(--field);
  border-color: #3a3e46;
  color: var(--text);
}
/* That button exists only while the sidebar is collapsed; keep it clear of the
   breadcrumb by indenting the page for exactly that case. */
body:has(button[data-testid="stExpandSidebarButton"]) [data-testid="stMainBlockContainer"] {
  padding-left: 62px;
}
[data-testid="stMainBlockContainer"] {
  padding: 0 34px 40px;
  max-width: 1240px;
}
[data-testid="stVerticalBlock"] { gap: 0.55rem; }

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: #26282d; border-radius: 6px; }
::-webkit-scrollbar-track { background: transparent; }

a { color: oklch(0.82 0.11 190); text-decoration: none; }
a:hover { color: oklch(0.9 0.11 190); text-decoration: underline; }

/* ---------------------------------------------------------------- sidebar */
[data-testid="stSidebar"] {
  background: var(--panel);
  border-right: 1px solid var(--line);
  width: 272px !important;
  min-width: 272px !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 22px 18px; }
[data-testid="stSidebarCollapseButton"] { color: var(--muted-2); }

[data-testid="stSidebar"] [data-testid="stTextInputRootElement"] {
  background: var(--field);
  border: 1px solid var(--border);
  border-radius: 9px;
}
[data-testid="stSidebar"] [data-testid="stTextInputRootElement"]:focus-within {
  border-color: var(--accent);
  background: #171a1e;
}
[data-testid="stSidebar"] input {
  background: transparent !important;
  color: var(--text) !important;
  font-family: var(--mono) !important;
  font-size: 13px !important;
  padding: 11px 12px !important;
}
[data-testid="stSidebar"] input::placeholder { color: var(--muted-3) !important; }
[data-testid="stSidebar"] label { display: none; }
[data-testid="stSidebar"] [data-testid="stTextInputRootElement"] { margin-bottom: 6px; }

/* Trading-code combobox: BaseWeb select, restyled to the design's field. */
[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background: var(--field);
  border: 1px solid var(--border);
  border-radius: 9px;
  min-height: 42px;
  font-family: var(--mono);
  font-size: 13px;
  color: var(--text);
}
[data-testid="stSidebar"] [data-baseweb="select"] > div:focus-within {
  border-color: var(--accent);
  background: #171a1e;
  box-shadow: none;
}
[data-testid="stSidebar"] [data-baseweb="select"] input {
  font-family: var(--mono) !important;
  font-size: 13px !important;
  color: var(--text) !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] svg { color: var(--muted-2); }

/* The popover renders at the document root, so it is not scoped to the sidebar.
   Left at the select's width it clips company names, so let it run wider. */
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="popover"] ul {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 4px;
}
/* Streamlit renders the option list as a react-window virtual list with a
   fixed row height and an inline pixel width, so the labels can neither wrap
   nor fit. Override that width; the list is absolutely positioned, so nothing
   else reflows. */
[data-testid="stSelectboxVirtualDropdown"],
[data-testid="stSelectboxVirtualDropdown"] > div,
[data-testid="stSelectboxVirtualDropdown"] > div > div,
[data-testid="stSelectboxVirtualDropdown"] [role="option"] {
  width: 372px !important;
  min-width: 372px !important;
  max-width: 372px !important;
}
[data-testid="stSelectboxVirtualDropdown"] {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"],
[data-baseweb="popover"] li {
  background: transparent;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  border-radius: 7px;
  padding: 7px 10px;
  font-family: var(--mono);
  font-size: 12px;
  color: var(--text-dim);
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover,
[data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"] {
  background: color-mix(in oklch, var(--accent) 14%, transparent);
  color: var(--text);
}
[data-baseweb="popover"] li:hover,
[data-baseweb="popover"] li[aria-selected="true"] {
  background: color-mix(in oklch, var(--accent) 14%, transparent);
  color: var(--text);
}

/* Result rows: the design's two-line code + name buttons. */
[data-testid="stSidebar"] [data-testid="stButton"] > button {
  width: 100%;
  text-align: left;
  justify-content: flex-start;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 7px 10px;
  min-height: 0;
  line-height: 1.35;
}
/* Streamlit nests the label as button > div(flex) > span > span > div > p;
   every wrapper shrink-wraps, so the text centres unless each is widened. */
[data-testid="stSidebar"] [data-testid="stButton"] > button > div,
[data-testid="stSidebar"] [data-testid="stButton"] > button span,
[data-testid="stSidebar"] [data-testid="stButton"] > button [data-testid="stMarkdownContainer"] {
  display: block;
  width: 100%;
  text-align: left !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button p {
  margin: 0 !important;
  text-align: left !important;
  font-family: var(--sans);
  font-size: 11px;
  line-height: 1.3;
  color: var(--muted-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* `**CODE**  \n name` renders as a block <strong> plus a <br>; the <br> would
   add an empty line on top of the block break. */
[data-testid="stSidebar"] [data-testid="stButton"] > button p br { display: none; }
[data-testid="stSidebar"] [data-testid="stButton"] > button p strong {
  display: block;
  margin: 0 0 1px;
  line-height: 1.25;
  font-family: var(--mono);
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-dim);
}
/* The design stacks result rows 2px apart; Streamlit's default block gap is 9px. */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.15rem; }
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"] p strong { color: var(--text); }
[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
  background: #1a1d22;
  color: var(--text);
  border-color: transparent;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button:focus {
  box-shadow: none;
  color: var(--text);
}
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"],
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"]:hover {
  background: color-mix(in oklch, var(--accent) 14%, transparent);
  border: 1px solid color-mix(in oklch, var(--accent) 40%, transparent);
  color: var(--text);
}

/* ------------------------------------------------------------------- tabs */
.stTabs [data-baseweb="tab-list"] {
  gap: 4px;
  border-bottom: 1px solid var(--line);
  background: transparent;
}
.stTabs [data-baseweb="tab"] {
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  padding: 11px 14px;
  margin-bottom: -1px;
  color: var(--muted-2);
  font-family: var(--sans);
  font-size: 13px;
  font-weight: 500;
}
.stTabs [aria-selected="true"] {
  color: var(--text) !important;
  font-weight: 600;
  border-bottom: 2px solid var(--accent) !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none; }
.stTabs [data-testid="stTabPanel"] { padding-top: 22px; }

/* ------------------------------------------------------- design fragments */
/* The focus-clearing script rides in a component iframe with no visible output. */
[data-testid="stIFrame"] { display: none; }

.sec-label {
  display: block;
  margin-bottom: 8px;
  font-size: 10.5px;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--muted-2);
  font-weight: 600;
}
.mono { font-family: var(--mono); }
.side-note { font-size: 11px; color: var(--muted-3); font-family: var(--mono); margin-top: 10px; }

.brand { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
.brand-mark {
  width: 28px; height: 28px; border-radius: 7px; background: var(--accent);
  display: flex; align-items: center; justify-content: center;
  color: #07100c; font-weight: 700; font-size: 13px; font-family: var(--mono);
}
.brand-name { font-size: 13px; font-weight: 600; letter-spacing: 0.02em; }
.brand-ver {
  margin-left: auto; font-family: var(--mono); font-size: 10px;
  color: #6b6f78; border: 1px solid #23262c; border-radius: 4px; padding: 2px 5px;
}

.side-divider { border-top: 1px solid var(--line); margin: 20px 0 16px; }
[data-testid="stSidebar"] p.side-body {
  margin: 0 0 12px;
  font-size: 12px !important;
  line-height: 1.55;
  color: var(--muted);
}
.tally { display: flex; justify-content: space-between; font-size: 11.5px; color: var(--muted); padding: 3px 0; }
.tally b { font-family: var(--mono); font-weight: 500; }
.side-foot { font-size: 11px; color: #4f535a; line-height: 1.5; margin-top: 18px; }

.topbar { display: flex; align-items: center; gap: 14px; padding: 6px 0; }
.topbar-rule { border-bottom: 1px solid var(--line); margin: 10px 0 26px; }
.crumb { font-family: var(--mono); font-size: 12px; color: #6b6f78; }
.crumb b { color: var(--text); font-weight: 500; }

h1.co-name {
  margin: 0; font-size: 30px; font-weight: 600;
  letter-spacing: -0.02em; line-height: 1.15; color: var(--text);
}
.chips { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 12px; }
.chip {
  font-size: 11px; color: var(--muted); border: 1px solid var(--border);
  border-radius: 999px; padding: 4px 10px;
}
.chip.code { font-family: var(--mono); color: var(--text-dim); }

.verdict {
  display: flex; align-items: center; gap: 14px; background: var(--card);
  border-radius: 14px; padding: 14px 18px;
}
.donut { width: 52px; height: 52px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex: 0 0 52px; }
.donut-in {
  width: 40px; height: 40px; border-radius: 50%; background: var(--card);
  display: flex; align-items: center; justify-content: center;
  font-family: var(--mono); font-size: 14px; font-weight: 600;
}
.verdict-title { font-size: 13px; font-weight: 600; }
.verdict-sub { font-size: 11.5px; color: var(--muted); margin-top: 3px; }

.metrics {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1px; background: var(--line); border: 1px solid var(--line);
  border-radius: 14px; overflow: hidden; margin: 26px 0;
}
.metric { background: var(--card); padding: 16px 18px; }
.metric-k {
  font-size: 10.5px; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--muted-2); font-weight: 600;
}
.metric-v { font-family: var(--mono); font-size: 27px; margin-top: 8px; letter-spacing: -0.02em; }
.metric-s { font-size: 11.5px; color: var(--muted-2); margin-top: 5px; font-family: var(--mono); }

.notice {
  display: flex; gap: 12px; align-items: flex-start;
  background: color-mix(in oklch, var(--warn) 7%, transparent);
  border: 1px solid color-mix(in oklch, var(--warn) 28%, transparent);
  border-radius: 12px; padding: 13px 16px; margin-bottom: 18px;
}
.notice span { color: var(--warn); font-size: 13px; line-height: 1.5; }
.notice p { margin: 0; font-size: 12.5px; line-height: 1.6; color: #c2c7d0; }

.grid-table { border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }
.grid-head, .grid-row {
  display: grid;
  grid-template-columns: minmax(0, 2.4fr) minmax(0, 1fr) minmax(0, 1fr) 110px;
  gap: 16px;
}
.grid-head {
  padding: 11px 18px; background: var(--card); border-bottom: 1px solid var(--line);
  font-size: 10.5px; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--muted-2); font-weight: 600;
}
.grid-row { padding: 14px 18px; border-bottom: 1px solid var(--line-soft); align-items: center; }
.grid-row:last-child { border-bottom: none; }
.grid-row:hover { background: var(--panel); }
.crit-name { font-size: 13.5px; color: var(--text); }
.crit-note { font-size: 11.5px; color: var(--muted-2); margin-top: 3px; }
.crit-val { font-family: var(--mono); font-size: 14px; color: var(--text); }
.crit-thr { font-family: var(--mono); font-size: 13px; color: var(--muted-2); }
.pill {
  display: inline-block; font-size: 11px; font-weight: 600;
  padding: 4px 10px; border-radius: 999px;
}

.panel { border: 1px solid var(--line); border-radius: 14px; padding: 24px 26px; background: var(--card); }
.panel-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 22px; flex-wrap: wrap; }
.panel-head h2 {
  margin: 0 !important;
  padding: 0 !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  letter-spacing: -0.01em;
  color: var(--text) !important;
  font-family: var(--sans);
  scroll-margin-top: 0;
}
.panel-head span { font-size: 11.5px; color: var(--muted-2); }
.bars { display: flex; flex-direction: column; gap: 20px; }
.bar-row { display: grid; grid-template-columns: 150px minmax(0, 1fr) 84px; gap: 16px; align-items: center; }
.bar-label { font-size: 12.5px; color: var(--text-dim); }
.bar-track { position: relative; height: 26px; background: var(--field); border-radius: 6px; overflow: hidden; }
.bar-fill { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 6px; }
.bar-mark { position: absolute; top: 3px; bottom: 3px; width: 2px; background: var(--text); opacity: 0.75; }
.bar-val { font-family: var(--mono); font-size: 13.5px; text-align: right; }

.raw { border: 1px solid var(--line); border-radius: 14px; background: var(--card); overflow: hidden; }
.raw-head { padding: 13px 18px; border-bottom: 1px solid var(--line); display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.raw-head .req { font-family: var(--mono); font-size: 11px; color: var(--muted-3); }
.raw-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); }
.raw-cell { padding: 13px 18px; border-bottom: 1px solid var(--line-soft); border-right: 1px solid var(--line-soft); }
.raw-k { font-family: var(--mono); font-size: 11px; color: var(--muted-2); }
.raw-v { font-family: var(--mono); font-size: 13.5px; margin-top: 4px; word-break: break-word; }

@media (max-width: 760px) {
  [data-testid="stMainBlockContainer"] { padding: 0 16px 40px; }
  .grid-head { display: none; }
  .grid-row { grid-template-columns: 1fr; gap: 6px; }
  .bar-row { grid-template-columns: 1fr; gap: 8px; }
  .bar-val { text-align: left; }
}
</style>
"""
