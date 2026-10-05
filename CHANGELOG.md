# Changelog

## 0.2.0 (not released: the reader in this version is not measured yet)

### The check

- The reader sees the page around a quote: up to three sentences or lines on each side, and every
  line a table quote skipped. That text can only cut a claim. It is for the sentence that takes the
  quote back and the price that sits in another plan's row. The reader prompt version is now 3e63cca8.
- The reader reads one page to a call, so the text of one page cannot reach a claim about another.
- A reader reply that answers a claim twice counts as no answer, and the claim is cut.
- A reader call that fails is tried once more. Claims it still cannot read are cut with the reason.

### The battle card

- A fact cut because its quote did not carry it gets one more quote from the same page, then the
  same two stages. Its words cannot change. The card says how many facts were kept this way.

### The command line and the MCP server

- `--backend anthropic` works with the short model names (`haiku`, `sonnet`, `opus`). A name the API
  would refuse stops the command before any work.
- `receipts check` exits 3, and says why, when the reader gave no answer. 1 still means a claim was cut.
- A file that is not a ledger is refused in words. A page with its hash removed is refused.
- `read_page` returns a long page in parts and says when there is more.

### The fetcher

- The connection goes to the address that was checked: one lookup of the host name, not two.
- Proxies from the environment are not used.

### Evals

- Round 3 is pre-registered in `studies/ROUND3_PREREGISTRATION.md`: the changed reader on the earlier
  sets, a third red team on fresh pages, and a study of how often a model told to quote states
  something the page does not, with five arms scored on the same claims (`bench/study/`).
- Property tests on the text functions the code check stands on.

## 0.1.0

The code check, the reader, the ledger, the battle card example, the MCP server, and the evals in
`bench/` and `studies/`.
