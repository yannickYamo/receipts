"""How many pages each way of fetching can read, on one fixed list. No model.

    python bench/reach/reach.py code browser      writes bench/reach/RESULT_reach.json
    python bench/reach/reach.py firecrawl         adds a column (needs FIRECRAWL_API_KEY)

For each page: whether it could be read, how many characters of text came back, and how many prices
are in it, as a rough sign of whether the text is all there. A refusal is recorded with its reason:
the point of the list is to say plainly what cannot be read, not to find a way round it.
"""

import json
import sys
from pathlib import Path

from receipts.fetch import FETCHERS, FetchError, fetch_page

HERE = Path(__file__).parent


def main() -> None:
    """Fetch every page of urls.json by each way named on the command line, and merge into the result file."""
    ways = [w for w in sys.argv[1:] if w in FETCHERS] or ["code"]
    out = HERE / "RESULT_reach.json"
    result = json.loads(out.read_text()) if out.exists() else {}
    for kind, urls in json.loads((HERE / "urls.json").read_text()).items():
        for url in urls:
            row = result.setdefault(url, {"kind": kind})
            for way in ways:
                try:
                    _, text, _ = fetch_page(url, way)
                    row[way] = {"read": True, "characters": len(text), "prices": text.count("$")}
                except FetchError as e:
                    row[way] = {"read": False, "why": str(e)}
                print(
                    f"{way:9} {'ok  ' if row[way]['read'] else 'FAIL'} {row[way].get('characters', row[way].get('why'))!s:>40}  {url}",
                    flush=True,
                )
    out.write_text(json.dumps(result, indent=1) + "\n")
    for way in sorted({w for r in result.values() for w in r if w != "kind"}):
        by_kind: dict[str, list[int]] = {}
        for r in result.values():
            if way in r:
                k = by_kind.setdefault(r["kind"], [0, 0])
                k[0] += r[way]["read"]
                k[1] += 1
        print(way, {k: f"{a} of {b}" for k, (a, b) in by_kind.items()})


if __name__ == "__main__":
    main()
