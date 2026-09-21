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
| `dse_news.py` | NOCFPS from DSE's news archive |
| `theme.py` | design tokens and CSS |
| `build_names.py` | one-off builder for the trading-code → company-name cache |
| `symbol_names.json` | that cache, committed so a fresh deploy has names immediately |
| `certs_dsebd_intermediate.pem` | TLS intermediate dsebd.org fails to send |

## Live prices

The price tile refreshes itself every 5 seconds via `st.fragment(run_every=5)`.
It reads `datafile/quotes_script.php` — a ~6 KB plain-text feed of every
instrument's last trade price, served in about 0.1s — rather than re-fetching
the ~330 KB company page. The 5-second `st.cache_data` on that fetch is shared
across viewers, so the app makes one small request per 5s regardless of how many
people have it open.

Everything else on the page is quarterly or annual data and stays on the
30-minute company-page cache. Treasury bonds and untraded scrips are absent
from the quote feed; those fall back to the company-page price and are labelled
"page value".

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
