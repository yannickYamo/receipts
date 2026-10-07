# Results

Every number here is rebuilt by the test suite from files in `bench/`, with no model
(`tests/test_bench.py`). Runs that called a model saved the model's answers; the tables replay from those.

"Pass" is the positive class throughout: a true claim the check keeps is a true positive, an unsupported
claim the check cuts is a true negative. Every judgment is yes or no. There are no scores.

## Summary

| What was measured | Result |
|---|---|
| True claims kept, written for the test (round 2, 60 claims) | 52 of 60 |
| Unsupported claims cut, written for the test (round 2, 60 claims) | 60 of 60 |
| Same reader, three runs: claims whose verdict changed | 0 of 76 |
| Real pages: of the facts the check kept, how many the page states (two blind labellers) | 43 of 43 |
| Real pages: of the facts the page states, how many the check kept | 43 of 59 |
| Red team with the source code, first set: unsupported claims that got past both stages | 9 of 40, then 0 of 40 after a fix |
| Red team with the source code, fresh set after the fix | 15 of 40 got past both stages (16 of 40 on the code as shipped) |

Read together: against a careless model the check holds, and on real pages it kept nothing the page did
not state. It pays for that by cutting a quarter of the true facts. Against someone who writes claims to
beat it, it does not hold: 15 of 40 got through, and the ways they got through are listed below.

The check changed twice after the first runs (sections 3 and 5). Where a number was measured again on
the code as shipped, both are given.

## 1. Two pre-registered rounds on claims written for the test

Pre-registrations: `GATE_PREREGISTRATION.md`, `ROUND2_PREREGISTRATION.md`. Each round: 60 true claims
and 60 unsupported ones of six kinds, about six software companies, with Wikipedia text as the
evidence. The claims were written by agents that saw neither the check nor each other's file. Each
round was run once.

| | True claims kept | Bar | Unsupported claims cut | Bar |
|---|---|---|---|---|
| Round 1: code check alone | 58 of 60 | 51, met | 43 of 50 mechanical, 0 of 10 meaning changes | 45, **missed** |
| Round 2: code check, then the reader, fresh set | 52 of 60 | 51, met | 60 of 60 | 54, met |

**The code check alone failed its bar.** It stopped every changed figure and every invented quote. It
missed claims that keep the quote's words and figures and change what they mean: investors "approved"
a deal the quote says they rejected, the acquirer and the acquired swapped. The reader stage was added
for that, and round 2 tested both stages on a set neither had seen.

In round 2 the code check cut 36 of the 60 unsupported claims and the reader the other 24. All 8 true
claims that were cut were cut by the code check, none by the reader: 5 loose paraphrases under the
word-overlap bar, 2 negations the paraphrase introduced, and "two MIT students" where the quote names
two students without the word "two".

With 60 claims a side the intervals are wide (Wilson, 95%): 52 of 60 is 76% to 93%, and 60 of 60 is
94% to 100%. The bar on true claims was met by one claim.

The check changed after these rounds (sections 3 and 5). Both rounds were run again on the code as
shipped, with fresh reader calls: round 1 gives 58 of 60 and 58 of 60, round 2 gives 52 of 60 and 60
of 60. In round 1 the reader passed two meaning changes this time (inv-053, whose label is arguable,
and inv-059).

## 2. The reader, repeated

The reader is a model, so one run could be luck. Round 2's reader stage was run three times on the 76
claims that reach it. No claim got a different verdict in any run. In all three it cut 0 true claims
and passed 0 unsupported ones. Reader: claude-haiku-4-5, prompt version f95a7623.

## 3. A red team with the source code

Rounds 1 and 2 never met an adversary. The agents that wrote their false claims copied whole sentences
as quotes. Plan written before the run: `EVAL_PLAN.md`.

**First set.** An agent was given the source of the code check and asked for 40 unsupported claims
that the code accepts. All 40 it kept passed the code check, which is expected: code compares words and
figures and cannot judge meaning. The reader then cut 31 and passed 9.

All 9 used one move: a quote that is on the page, cut out of its sentence so the words around it are
lost. "acquire Five9 for $14.7 billion" out of "announced plans to acquire". "$425" out of "$425
million". A sentence about one company quoted without its subject and claimed for another.

**The fix.** The reader no longer sees the quote the model chose. Code widens the quote to the whole
sentences it sits in on the page (the passage), and both the code check and the reader read that. On
the same 40 claims afterwards: 0 pass both stages (and 3 no longer pass the code check). That is a
number on a set the fix was written against, so it is a regression test, not a measurement.

**Second set.** A fresh agent, given the fixed code and the reader's prompt, wrote 40 more on a
different corpus. 40 passed the code check, the reader cut 25, and **15 passed both stages**:

| How they got through | Passed both |
|---|---|
| The sentence is quoted faithfully and the next sentence on the page takes it back (a deal announced, then called off; a CEO named, who later left) | 6 of 6 |
| Lines of a table or list joined by an ellipsis that belong to different items | 2 of 6 |
| A part stated as the whole ("enterprise applications software" becomes "enterprise software") | 2 of 6 |
| Something the page states as past, claimed as current | 1 of 5 |
| A figure, a heading, an ambiguous phrase or a relative date read the other way | 4 of 5 |
| A plan stated as a fact; a hedge dropped; another entity in the same sentence; and others | 0 of 12 |

The same 40 on the code as shipped, after the second audit's fixes: 16 pass both stages. None of those
fixes was aimed at this set, and it shows: the reader's answers moved by a claim or two and the
result did not.

What this says: the check verifies that a sentence on a page says what the claim says. It does not
verify that the page, read whole, still stands behind that sentence. A reader that sees the sentences
on either side is the next thing to build, and it will need its own round.

Both red-team sets are in the repository and run in the test suite. A change that lets more of them
through fails the build.

## 4. Real pages, labelled blind

The first three sections use claims written for the test. This one uses what the pipeline actually
produced: the 59 facts a model proposed in a live run on Freshdesk and Zendesk pages (`bench/live/run3`).
Two labellers, on different models (Claude Opus and Claude Sonnet), each read every fact against the
full page without seeing what the check decided, and answered two yes/no questions: does the page
state this fact, and does the quote alone state it. The check as shipped then decided the same 59.

| | Labeller A | Labeller B |
|---|---|---|
| Of the 43 facts the check kept, the page states | 43 | 43 |
| Of the 59 facts proposed, the page states | 59 | 59 |
| Of the facts the page states, the check kept | 43 of 59 | 43 of 59 |
| Check kept it, of the facts whose quote states them | 38 of 39 | 43 of 50 |
| Check cut it, of the facts whose quote does not state them | 15 of 20 | 9 of 9 |

The promise on the card held: nothing was kept that the page does not state (bar: 95%). But on this
run the model proposed nothing false, so the check caught no invention here. What it did was cut 16
true facts, a quarter of them. For a guard that is the number that matters most: a guard that blocks a
valid answer has a bug, and this one blocks one true fact in four on pricing pages.

Why the 16 were cut, read one by one and grouped:

| Why a true fact was cut | Count |
|---|---|
| The quote holds the value and not what it belongs to (a price without its plan, "add-on" stated elsewhere on the page) | 8 |
| The fact adds a word the quote lacks ("free" trial, "API" endpoints, "requires") | 6 |
| A faithful paraphrase under the word-overlap bar | 1 |
| The negation rule fired on an unrelated "not" | 1 |

The two labellers agree on the first question for all 59 facts and on the second for 48. The 11 they
split on are one disagreement: whether a quote that does not name the product counts as stating a fact
about it when the page is the product's own. That is a rule to set before the next round: round 3 sets it (the title of the page may supply the subject, nothing else). The labellers are
models. Until a person has labelled a sample, these labels are provisional.

## 5. Two audits before publication

Twice, an independent reviewer was given the code and asked for defects and for ways past the check.
Everything below was confirmed by running it, is fixed, and has a regression test
(`tests/test_audit_findings.py`, `tests/test_core.py`, `tests/test_fetch.py`).

The first audit:

| Way past the code check | Now |
|---|---|
| A quote matched inside a longer word or number: "$19" on a page that says "$199" | A quote must be whole words and whole numbers |
| A quote clipped to drop a negation | Negations are read in the passage, not the quote |
| A loose match that accepted a reworded quote | Removed: a quote is on the page word for word, or it is not |
| An ellipsis that stitched words from two sentences | An ellipsis joins whole lines of a table, a few lines apart |
| A figure hidden in the product name the caller supplies | A number is part of a name only when the page writes it that way |
| A claim with no subject skipped the subject check | A claim with no subject is cut |
| "$19" accepted against "19 agents" | Money must match money, and a share a share |
| Advice lines on the card could state a new fact | A reader reads advice for facts beyond its citations. This use is not measured |
| The fetcher followed a model-supplied address anywhere | Public http(s) hosts only, checked again on every redirect |

The second audit, on the code after those fixes:

| Defect | Now |
|---|---|
| A sentence was cut at an abbreviation ("incl."), hiding a negation from the check | Sentence ends skip abbreviations and initials |
| "compliant" was found inside "non-compliant" | A hyphen joins a word like a letter does |
| "19 agents" accepted against "$19"; "$19" accepted against "€19" | A figure's kind must match both ways, and each currency is its own kind |
| Versions read as numbers ("1.2.3" equal to "1.2.9") | A version is a name, not a figure |
| A price equal to a number in the product's name was exempt ("Microsoft 365 costs $365") | Only a bare number can be part of a name |
| Text in other scripts had no words the check could compare, so nothing was ever "beyond the quote" | Words are read in any script |
| True claims cut: "5M users", "five percent", ranges such as "5-15%", a page's own ellipsis | Each is read as written |
| Names such as "3M" or "Any.do" could never be a subject; "Com" matched any .com address | Names keep digits and short words; an address ending names nothing |
| Two claims with one id could take each other's verdict | Claims are read by position |
| A malformed reply from the reader, a bad input file, a cut-off API reply: a crash | Each is handled: the claim is cut, or the command says what is wrong |
| A slow server could hold a fetch open past its deadline | The deadline is checked after every packet |

Left as a stated limit at the time: the fetcher resolved a host name once before the request and the
system resolved it again, so a host that changed its answer between the two was not caught. It was
closed later (section 7): the connection now goes to the address that was checked.

A third review, by an outside reader after publication:

| Defect | Now |
|---|---|
| `receipts check` and the MCP tool ran the code check alone, the stage that failed its bar in section 1. Probe: the page says a plan is offered in Europe and not in India, the claim says India, the quote is five words; the code check passed it | Both stages are the default in the command and the MCP server. `--code-only` has to be asked for, and its output says what it is. With both stages the probe is cut |
| The battle card's line check dropped the kind of a figure: "19 agents" was kept against a fact that says "$19" | Lines are held to the same figure rule as facts |
| `receipts check` printed the wrong text when two claims shared an id | Verdicts are printed by position |
| A ledger file edited after the fetch was accepted | Loading refuses text that no longer matches its hash. The file is still trusted input: whoever can edit the text can edit the hash |
| A page fetched again silently replaced the earlier text under the same id | A page read again with different text gets its own id; the earlier text stays |

Each has a regression test (`tests/test_review_findings.py`).

## 6. Live runs, and the example this started from

Request, from the upstream example's own README: "Help me compete against Zendesk, I sell Freshdesk".

**The upstream example.** The seven-agent sales example in Shubhamsaboo/awesome-llm-apps (commit
4b2ac4a), its prompts read from that commit and run in its order (`bench/baseline/run.py`). Two things
differ from upstream: the model was Claude Sonnet through the local `claude` command, not Gemini
through Google ADK, and stage 7 (an image) was left out.

| The card it wrote | |
|---|---|
| Pattern hits for specifics (prices, ratings, counts, dates, attributions) | 175, on 109 of 325 lines |
| Of a seeded sample of 40 hits, read by hand: checkable facts | 32, of which 28 distinct |
| On a line with a link | 0 |
| Times the card itself says VERIFY | 23 |

This does not show its figures are wrong. The Zendesk list prices it gives match Zendesk's pricing
page. It shows a rep cannot tell which are right: prose passes from stage to stage and no address
survives to the card. Counts and labels are in `bench/baseline/AUDIT.json`. The card itself is not in
the repository, since it is unverified text about two real companies.

**This pipeline, five runs of the same request.**

| | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| Pages read / refused | 5 / 3 | 5 / 2 | 6 / 2 | 5 / 2 | 5 / 2 |
| Facts kept, of those proposed | 36 of 58 | 40 of 52 | 44 of 59 | 37 of 48 | 34 of 48 |
| Card lines kept | 17 of 21 | 17 of 22 | 18 of 24 | 16 of 22 | 19 of 23 |
| Lines on the card without a source | 0 | 0 | 0 | 0 | 0 |

The check changed between runs: after run 1 the extraction prompt was told to quote a name with its
value; run 3 is on the code after the first audit; run 4 after the red-team fix; run 5 is on the code
as shipped. So the runs are a history, not five samples of one thing. G2 and Capterra refused the fetch every time, so no card has
review data, and each says which pages it could not read.

## 7. After these runs

Everything above was measured on reader prompt f95a7623, the reader of 0.1.0. Two things were built
afterwards and measured in round 3 (section 8): the reader is shown the page on either side of
the passage (prompt 3e63cca8, the reader of 0.2.0), and the battle card gives a fact one more quote
when its first quote did not carry it. A second outside review also found ten defects outside the
check's decisions (the API backend's model name, a reader reply that answers a claim twice, a
malformed ledger, the fetcher's second lookup of a host name, and others); each is fixed with a
regression test in `tests/test_second_review_findings.py`. The code check's decisions did not change:
sections 1 and 3 still rebuild from it.

The plan for measuring the changed reader, with its bars, is `ROUND3_PREREGISTRATION.md`.

## 8. Round 3

Plan: `ROUND3_PREREGISTRATION.md`, with its amendment and its dated additions. Measured code: `core.py`
59f710ad699d8fb9, `text.py` b0bae52357db889c, `reader.py` 24b0ee00c397867a, reader prompt 3e63cca8,
which is the code of 0.2.0. Reader: claude-haiku-4-5. Extractors: four models of three families
(two Claude, one GPT, one Grok).

**The files of these runs are not in this repository.** Sections 1 to 6 are rebuilt by the test suite
from saved files. This section is a report: the numbers below were written by `bench/round3_report.py`
from the run files where the runs were made, and cannot be rebuilt here.

| Measure | Bar | Result | |
|---|---|---|---|
| Round 2, true claims kept | at least 51 of 60 | 52 of 60 (87%) | met |
| Round 2, unsupported claims cut | at least 54 of 60 | 60 of 60 (100%) | met |
| Reader, three runs: verdicts that changed | at most 2 | 0 of 76 | met |
| Second red team, past both stages | at most 10 of 40 | 5 of 40 (12%) | met |
| Second red team, retractions past both | at most 2 of 6 | 1 of 6 | met |
| Real pages (run 3), true facts kept on the same quotes | at least 41 of 59 | not run | |
| Third red team, retractions past both | at most 2 | 0 of 7 | met |
| Third red team, joined lines past both | at most 2 | 0 of 10 | met |
| Third red team, all techniques, past both | none set | 1 of 40 (2%) | no bar |
| Planted instructions: passes, planted against plain | at most 1 more | 1 against 0, of 20 pairs | met |
| Delivered claims the page does not state | at most half, when the bare model has 20 | 9 of 864 (1%) before, 4 of 576 (1%) after; difference interval [-0.011, 0.0016]; fewer than 20, so no bar applies | no bar |
| Delivered claims whose quote does not state them | at most half, interval below zero | 296 of 864 (34%) before, 72 of 576 (12%) after; difference interval [-0.276, -0.1607] | met |
| True claims kept | at least 70% | 572 of 855 (67%), interval [0.5858, 0.7444] | **missed** |
| Claims their quote states, kept | at least 85% | 504 of 568 (89%), interval [0.8295, 0.9354] | met |
| Reader, list price per 100 claims | reported | $0.36, 5.52s a claim | no bar |
| Live battle card, true facts kept | at least 80%, and no second quote on a fact the page does not state | 43 of 56 (77%); 1 kept on a second quote, 0 of them not stated by the page | **missed** |

The Citations API arm was not run. The re-read of the facts of live run 3 was not run.

**Outcome 2**, because the share of delivered claims whose quote does not state them is at most half
the bare model's. The README's sentence for that outcome, filled from these numbers, is the second
paragraph of the README.

**Labels.** Two labellers of different model families labelled all 864 claims. A third model family,
not a person, settled 148 of them: the 98 the two disputed or marked unsupported, and a sample of 50.
The two labellers agree on "the page states it" for 838 of 864 (97%, kappa 0.177) and on "the quote
states it" for 788 of 864 (91%, kappa 0.793). Of the 50 agreed labels read as a check, 2 were
overturned. Because the labels were not settled by a person, this is not the pre-registered result.

By kind of page, and by model family:

| | Claims the page does not state, before | after | True claims kept |
|---|---|---|---|
| docs | 3 of 288 (1%) | 1 of 204 (0%) | 203 of 285 (71%) |
| encyclopedia | 4 of 288 (1%) | 3 of 238 (1%) | 235 of 284 (83%) |
| pricing | 2 of 288 (1%) | 0 of 134 (0%) | 134 of 286 (47%) |
| claude | 7 of 432 (2%) | 2 of 249 (1%) | 247 of 425 (58%) |
| gpt | 1 of 216 (0%) | 1 of 160 (1%) | 159 of 215 (74%) |
| grok | 1 of 216 (0%) | 1 of 167 (1%) | 166 of 215 (77%) |

Under each labelling. Strict says yes only where both labellers do; lenient says yes where either
does. Any settlement lies between them.

| Labels | Outcome | Quote does not state it, before to after | Page does not state it, before to after | True claims kept | Claims their quote states, kept |
|---|---|---|---|---|---|
| settled | 2 | 296 of 864 (34%) to 72 of 576 (12%) | 9 of 864 (1%) to 4 of 576 (1%) | 572 of 855 (67%) missed | 504 of 568 (89%) met |
| strict | 2 | 302 of 864 (35%) to 77 of 576 (13%) | 29 of 864 (3%) to 17 of 576 (3%) | 559 of 835 (67%) missed | 499 of 562 (89%) met |
| lenient | 2 | 226 of 864 (26%) to 45 of 576 (8%) | 3 of 864 (0%) to 2 of 576 (0%) | 574 of 861 (67%) missed | 531 of 638 (83%) missed |

The outcome is the same under each.

**The two misses have one cause.** True claims kept, and the live card, both fall short on pricing
pages: a value in a table quoted without its row or its column. Round 4 is planned for that.

## What is not measured

- **People.** One model family wrote the check, the reader prompt, the test claims and the labels. A
  test set and labels from people, or from another model family, come first.
- **Whether a page is right.** A wrong page yields a well-sourced wrong claim.
- **The reader on card lines and advice.** Measured only on facts against passages.
- **Whether the extraction misses facts** a rep would want. Nothing here measures what was never proposed.
- **Other subjects.** Software companies and their pricing pages only.
