"""One-off builder for the trading-code -> company-name cache.

DSE publishes no listing page that carries company names for every instrument
(marginable_securities.php has them, but only for ~188 codes, and it 404s
intermittently). The company page itself always has the name, so this fetches
each one once and fills symbol_names.json.

Re-running it only fetches codes that are missing, so it is safe to repeat.

    python3 build_names.py            # fill in whatever is missing
    python3 build_names.py --refresh  # re-fetch everything
"""

import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import requests

import dse

NAME_RE = re.compile(
    r'<h2[^>]*class="[^"]*BodyHead[^"]*"[^>]*>\s*Company Name\s*:\s*<i>(.*?)</i>',
    re.I | re.S,
)
WORKERS = 6

_lock = threading.Lock()


def scrape_name(session, symbol):
    try:
        response = session.get(
            dse.COMPANY_URL.format(symbol=symbol),
            timeout=30,
            verify=dse.ca_bundle(),
        )
        if response.status_code != 200:
            return None
        match = NAME_RE.search(response.text)
        if not match:
            return None
        name = re.sub(r"\s+", " ", match.group(1)).strip()
        return name or None
    except Exception:
        return None


def main():
    refresh = "--refresh" in sys.argv

    symbols, err = dse.fetch_symbols()
    if err:
        print(err)
        return 1

    names = {} if refresh else dse.load_names()
    todo = [s for s in symbols if s not in names]
    print(f"{len(symbols)} codes listed, {len(names)} already known, {len(todo)} to fetch")
    if not todo:
        return 0

    session = requests.Session()
    session.headers.update({**dse.HEADERS, "Referer": "https://www.dsebd.org/"})
    done = [0]

    def work(symbol):
        name = scrape_name(session, symbol)
        with _lock:
            done[0] += 1
            if name:
                names[symbol] = name
            if done[0] % 25 == 0 or done[0] == len(todo):
                print(f"  {done[0]}/{len(todo)} ({len(names)} names held)", flush=True)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(work, todo))

    dse.save_names(names)
    missing = [s for s in symbols if s not in names]
    print(f"wrote {len(names)} names to {dse.NAME_CACHE}")
    if missing:
        print(f"{len(missing)} had no name on their page: {', '.join(missing[:12])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
