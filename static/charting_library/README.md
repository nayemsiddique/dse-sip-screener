# TradingView Charting Library goes here

This folder is intentionally empty in the repo. TradingView's Charting Library
("Advanced Charts") is free but licensed to you, not redistributable, so it
cannot be committed here — `.gitignore` keeps everything in this folder out of
git except this note.

## Getting it

1. Request access at <https://www.tradingview.com/advanced-charts/> ("Get the
   library"). They grant your GitHub account access to a private repo.
2. Clone it and copy the `charting_library/` folder's **contents** into this
   folder, so that this path exists:

   ```
   static/charting_library/charting_library.standalone.js
   ```

3. Rerun the app. `tvchart.available()` checks for exactly that file; the Price
   chart tab switches from the built-in canvas chart to Advanced Charts on the
   next rerun, with no other change.

Streamlit serves this folder at `/app/static/charting_library/` because
`.streamlit/config.toml` sets `server.enableStaticServing = true`.

## Why this route and not the embed widget

TradingView does carry DSE — the exchange is `DSEBD`, e.g. `DSEBD:SQURPHARMA`.
Its free embeddable widget refuses those symbols, though: it answers "This
symbol is only available on TradingView", because the DSE feed is not licensed
for embedding. The same widget renders `NASDAQ:AAPL` fine, so it is the data,
not the widget.

The Charting Library ships no data at all — you supply it — so the app feeds it
the series `dse_history.py` already scrapes, and the licensing question does
not arise. See `tvchart.py`.
