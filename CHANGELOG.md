# Changelog

## Unreleased

- `receipts brief`: a brief on a company before you write to it. Code picks the pages from the
  company's own site, a model lists signals with quotes, and each signal goes through the code check
  and the reader. The reasons and the draft message cite the signals they rest on; a line that adds a
  fact, a figure or a person's name is cut. Not measured yet: the plan is
  `studies/BRIEF_PREREGISTRATION.md`, the harness `bench/brief/`.
- The fetcher can return a page's links, so further pages of a site are found in code.

## 0.2.0 (2026-10-06)

The rates in `EVALS.md` were measured on the reader of 0.1.0 (prompt f95a7623). The reader in this
version (prompt 3e63cca8) is put to the plan in `studies/ROUND3_PREREGISTRATION.md`. Its results are
not published yet, and the docs say which reader each number is for.

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
- `receipts mcp` without the mcp package says so in one line.
- The battle card's prompts ask for table lines in the order the page has them. They used to ask for
  the name first, and a page that puts the price above the plan name could not be quoted that way.

- `--backend openai` runs the reader on any API that speaks OpenAI's chat completions, such as OpenAI
  or xAI. Only the reader on claude-haiku-4-5 is measured.

### The fetcher

- The connection goes to the address that was checked: one lookup of the host name, not two.
- Proxies from the environment are not used.

### Evals

- Round 3 is pre-registered in `studies/ROUND3_PREREGISTRATION.md`: the changed reader on the earlier
  sets, a third red team on fresh pages, and a study of how often a model told to quote states
  something the page does not, with five arms scored on the same claims (`bench/study/`).
- An amendment to that plan, written before any run: extractors from three model families, a second
  error measure (a kept claim whose quote does not state it), intervals drawn over pages, the Citations
  API as a reported arm, a planted-instruction set, and the sentence each outcome puts in the README.
- `study.py freeze` records the code that decides a claim, and the suite fails if it changes mid-round.
- Property tests on the text functions the code check stands on, and a type check in CI.

## 0.1.0

The code check, the reader, the ledger, the battle card example, the MCP server, and the evals in
`bench/` and `studies/`.
