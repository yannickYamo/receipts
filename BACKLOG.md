# Backlog

What is deliberately not in 0.2.0. Each needs a measurement of its own before it ships.

- A decision model as the reader. The reader's job is one yes/no question, and models built to decide
  answer it with a probability, which turns the reader's strictness into a number the caller sets.
  `receipts.decision` has the reader and a client for TypeSafe AI's Jev; `bench/bakeoff/` scores it
  against the measured reader on the saved sets (`studies/BAKEOFF_PREREGISTRATION.md`). Not run yet.
  OpenAI's Decisions API is the same kind of thing; an adapter waits for its request format to be
  published. If a decision reader is level, offer it on the command line, with fixed cut reasons
  (swapped actor, wrong figure, wrong company, reversal, added claim, part for whole) chosen by the
  model in place of free text.
- Other chat readers. The reader can be any model the backends reach, and only claude-haiku-4-5 is
  measured. The bake-off harness scores any of them on the saved sets.
- Other support judges on the same pairs: MiniCheck, HHEM, AlignScore.
- The Citations API as a source of quotes: accept its cited text as a claim's quote directly.
- A test set written by people, not only labelled by them.
- The table check in code: a quote that joins lines of different rows is cut by the reader today,
  not by the code check.
- The second quote on the battle card, measured on more than one card.
- The battle card's advice lines: the reader's reading of them is not measured.
- The reader at volume: calls in parallel, a cache keyed on claim, passage and prompt version,
  rate-limit handling.
- Pages that are not in English, and pages that are not about software.
- The brief on more than one seller, and on companies whose news lives on another site (a job board,
  a press wire): today only the company's own pages are read.
- The browser fetcher cannot promise that the address it checked is the address it dialled, as the
  plain fetcher can. It checks every request and throws the page away if any went somewhere private,
  and it is kept out of the MCP server. Pinning the address inside the browser is not done.
