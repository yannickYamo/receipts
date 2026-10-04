"""Build the bench corpus: the plain text of six more Wikipedia articles, for the second round.

Wikipedia text is CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). Each file keeps
its source address and the time it was read. Run from the repository root: python bench/corpus2/build.py
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path

from receipts import Ledger

TITLES = ["Slack Technologies", "Atlassian", "Shopify", "Twilio", "Dropbox", "Zoom Communications"]
HERE = Path(__file__).parent

ledger = Ledger()
index = []
for title in TITLES:
    q = urllib.parse.urlencode(
        {"action": "query", "prop": "extracts", "explaintext": 1, "format": "json", "redirects": 1, "titles": title}
    )
    req = urllib.request.Request(
        f"https://en.wikipedia.org/w/api.php?{q}", headers={"User-Agent": "claim-receipts-bench/0.1 (corpus build)"}
    )
    page = next(iter(json.load(urllib.request.urlopen(req, timeout=30))["query"]["pages"].values()))
    url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(page["title"].replace(" ", "_"))
    company = page["title"].split(",")[0]
    ev = ledger.add_text(url, page["extract"], f"{page['title']} - Wikipedia")
    name = company.lower().replace(".", "") + ".txt"
    (HERE / name).write_text(page["extract"])
    index.append({"company": company, "evidence_id": ev.id, "url": url, "file": name, "chars": len(page["extract"])})
    print(company, ev.id, len(page["extract"]))
ledger.save(HERE / "ledger.json")
(HERE / "index.json").write_text(json.dumps(index, indent=1))
