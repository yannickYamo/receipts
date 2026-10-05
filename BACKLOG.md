# Backlog

What is deliberately not in 0.2.0. Each needs a measurement of its own before it ships.

- Other readers. The reader can be any model the backends reach, and only claude-haiku-4-5 is
  measured. Measure a second reader on the round 3 claims.
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
- A fetcher for pages that need JavaScript, or a documented hand-off to one.
