# Security

## Reporting a problem

Please report a security problem privately, through "Report a vulnerability" on the repository's
Security tab. Do not open a public issue for it. You will get an answer, and a fix is credited to you
unless you ask otherwise.

## What receipts is built to withstand

receipts reads web pages whose addresses a model may have chosen, and shows page text to a model.
It treats both as hostile.

- **Addresses.** Only http and https, and only hosts on the public internet: no localhost, no private
  or link-local ranges, checked again on every redirect. The plain fetcher opens its connection to the
  address it checked, so a host name cannot answer one thing to the check and another to the fetch.
- **Size and time.** A page is capped at 3 MB and one overall deadline.
- **Refusals.** A site's robots.txt is honoured. A 401, a 403 or a bot check is never taken for a
  page, and nothing here is built to get past one.
- **Page text in a prompt.** It cannot open or close a tag of the prompt, and the reader reads one
  page to a call, so one page cannot speak to the reading of a claim about another. The reader can
  only cut: the most a hostile page can win is the result of the code check alone.
- **The ledger.** A page whose text no longer matches its hash, or whose hash was removed, is refused.

## What it does not promise

- A ledger file is trusted input. Whoever can edit the text can edit the hash.
- The reader is a model. It is not a security boundary: `EVALS.md` gives how often planted
  instructions and claims written to get through did get through.
- The browser fetcher checks every request a page makes and throws the page away if any went
  somewhere private, but it cannot open its connections to an address it checked itself. It is for
  addresses a person chose, and the MCP server never uses it.
- A page supplied with `receipts add`, or returned by a hosted service, is what you or that service
  gave it. The ledger records which, and a card shows it.

## Keys

receipts stores no keys. Backends read them from the environment (`ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`, `FIRECRAWL_API_KEY`, `TYPESAFE_API_KEY`) and send them only to the service they
belong to. No key, page text of other sites, or ledger is committed to this repository.
