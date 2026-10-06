# Pre-registration: the brief on a company

Written on 2026-10-06, before any model wrote a brief. Nothing below has been run.

## What is tested

`receipts brief`: a brief on a company for someone about to write to it. Code reads the company's home
page and follows its own links to its news, careers, about and customer pages. A model lists signals,
each with a quote. Each signal goes through the code check and the reader, as every claim does. A
model then writes why the company might need the seller now and a first message, one sentence at a
time, each citing the signals it rests on. Code and the reader cut a line that adds a figure, flips a
negation, names a person, or states a fact its signals do not.

The check and the reader are the ones of 0.2.0: `core.py`, `text.py` and `reader.py` do not change, so
the rates published for them are not touched by this. What is new, and what this round measures, is
the brief built on them: the signal prompt, the pages code picks, and the reader's reading of lines.

## The set

Twelve software companies (`bench/brief/companies.json`), chosen because code could read their home
page and find further pages from it, and for no other reason. None of their press, careers or about
pages was read by a model before this file was written. The seller is made up ("Deskly, a help desk
for support teams of 10 to 200 agents"), so no brief is a claim about a real product.

One run: `python bench/brief/study.py run`. Extraction and writing on Claude Sonnet, the reader on
claude-haiku-4-5, through the local `claude` command.

## Labels

Two labellers, one of them not a Claude model, label two blind sheets (`study.py sheet`): for every
proposed signal, whether the page, read whole, states it; for every written line, whether it states a
fact that neither the signals it cites nor the seller's words state. Both also say whether the item
names a person. Where the two differ, a person decides. The result is `labels_final.jsonl`.

## Bars

1. Of the signals the brief keeps, the page states at least 95%.
2. Of the proposed signals the page states, the brief keeps at least 70%.
3. No kept line adds a fact.
4. No kept signal and no kept line names a person.

Reported with them, no bar: how many lines were cut, and how many of those added no fact; how many
signals were left out for naming a person; pages that could not be read; cost at list price.

## What a miss means

A missed bar is written into `EVALS.md` and the README's limits with its number. It does not change
the code before the brief is released. A fix comes after, with a set of its own.

Bar 3 is strict on purpose. The reader's reading of lines has never been measured, on the battle card
or here, and a first message is where an unsupported fact does the most harm. If it is missed, the
README says how often a kept sentence added a fact, and that the message is a draft to read before
it is sent.

## Limits

Twelve companies, all software, all in English, one seller, one run. The companies were chosen for
being readable, which leaves out every site that needs JavaScript or refuses a plain request. The
guard against naming a person recognises the common shapes of a press page; it is not a detector of
every name. Whether a reason or a message is a good one is not measured at all.
