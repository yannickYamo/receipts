"""Build the fourth bench corpus: six Wikipedia pages that are mostly tables, read as HTML.

The earlier corpora are prose. This one is for claims about a value in a table: each row is one line
of text, and a value carries the header of its column (text.row_line). The pages are fetched with the
package's own fetcher, so the text is what the check reads on any table page.

Wikipedia text is CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). Each file keeps
its source address and the time it was read. Run from the repository root: python bench/corpus4/build.py
"""

import json
from pathlib import Path

from receipts import Ledger

PAGES = {
    "Issue trackers": "https://en.wikipedia.org/wiki/Comparison_of_issue-tracking_systems",
    "Project management": "https://en.wikipedia.org/wiki/Comparison_of_project_management_software",
    "Web conferencing": "https://en.wikipedia.org/wiki/Comparison_of_web_conferencing_software",
    "Time tracking": "https://en.wikipedia.org/wiki/Comparison_of_time-tracking_software",
    "Help desk": "https://en.wikipedia.org/wiki/Comparison_of_help_desk_issue_tracking_software",
    "Source code hosting": "https://en.wikipedia.org/wiki/Comparison_of_source-code-hosting_facilities",
}
HERE = Path(__file__).parent

ledger = Ledger()
index = []
for name, url in PAGES.items():
    ev = ledger.add_url(url)
    rows = sum(" | " in line for line in ev.text.split("\n"))
    file = name.lower().replace(" ", "-") + ".txt"
    (HERE / file).write_text(ev.text)
    index.append({"name": name, "evidence_id": ev.id, "url": url, "file": file, "chars": len(ev.text), "table_rows": rows})
    print(name, ev.id, f"{len(ev.text):,} characters, {rows} table rows")
ledger.save(HERE / "ledger.json")
(HERE / "index.json").write_text(json.dumps(index, indent=1))
