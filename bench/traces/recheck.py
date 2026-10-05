"""Decide live run 3's 59 facts again with the check as shipped (code, then the reader). Calls a model.

Needs the pages of run 3 (bench/live/run3/ledger.json), which are kept out of the repository because
they are other people's web pages. The verdicts it writes are in the repository, and score.py reads them.

    python bench/traces/recheck.py           writes verdicts_shipped.json, the file score.py and the tests read
    python bench/traces/recheck.py v2        writes verdicts_v2.json beside it and leaves the first alone

--reader-model=<name> picks the reader (default haiku). The result names the model it was read with.
"""

import json
import sys
from pathlib import Path

from receipts import Claim, Ledger
from receipts.backends import ClaudeCodeBackend
from receipts.reader import READER_VERSION, check_with_reader

HERE = Path(__file__).parent
RUN = HERE.parent / "live" / "run3"

card = json.loads((RUN / "card.json").read_text())
ledger = Ledger.load(RUN / "ledger.json")
claims = [Claim(f["id"], f["text"], f["quote"], f["evidence_id"], f["subject"]) for f in card["facts"]]
ARGS = [x for x in sys.argv[1:] if not x.startswith("--")]
backend = ClaudeCodeBackend(
    next((x.split("=", 1)[1] for x in sys.argv[1:] if x.startswith("--reader-model=")), "haiku")
)
report = check_with_reader(claims, ledger, backend)
out = {
    "reader": f"{backend.name}, prompt {READER_VERSION}",
    "cost_usd_list_price": round(backend.cost_usd, 4),
    "verdicts": {v.claim_id: {"kept": v.supported, "reason": v.reason, "detail": v.detail} for v in report.verdicts},
}
(HERE / f"verdicts_{ARGS[0] if ARGS else 'shipped'}.json").write_text(json.dumps(out, indent=1))
print(len(report.supported), "kept of", len(claims), report.by_reason)
