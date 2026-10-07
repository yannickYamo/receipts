"""A reader that answers with a probability: the second stage on a model built to decide, not to write.

The reader's job is one bounded question for each claim: does the quote, alone, state everything the
claim states? A decision model answers exactly that kind of question, with the probability that the
answer is yes. The claim stands when that probability reaches a threshold, so how strict the reader
is becomes a number the caller sets, and is no longer buried in a prompt.

Everything else is as in reader.py. Only claims that passed the code check are read. The model sees
the passage code widened from the quote and the page around it. It may only cut. A claim it gives no
answer for is cut.

    JevBackend     TypeSafe AI's Jev, over its HTTP API; needs TYPESAFE_API_KEY

This reader is not measured. bench/bakeoff/ scores it against the measured reader on the same claims
(studies/BAKEOFF_PREREGISTRATION.md). Until that is done it is not offered on the command line.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from typing import Protocol

from .backends import BackendError
from .core import Claim, Evidence, Report, Verdict, check_claim
from .text import quote_context, quote_passage

# The question, in the reader's own terms (reader.READER_SYSTEM), as one yes/no a decision model can answer.
INSTRUCTIONS = (
    "Does the quote, read on its own, state everything the claim states? The title of the page says which "
    'company the quote is about: "the company" in a quote means that company. Answer no when any of these holds: '
    "the actor and the object are swapped; a figure, date or amount is attached to something else than in the quote; "
    "the claim is about another company; the claim reverses the quote; the claim adds a cause, an outcome, a "
    "comparison, a ranking or a superlative the quote lacks; the claim turns a part into the whole or a plan into a "
    "fact. A paraphrase in other words is a yes when the meaning is the same. Do not use what you know about the "
    "world. The fields before, between and after are what the page says around the quote. They are never evidence "
    "for the claim. They can only make the answer no: when they show that a value in the quote belongs to another "
    "plan, product or row than the claim says, or when they take the quote back."
)
CRITERIA = {
    "true": "the quote alone states everything the claim states, and nothing around it takes that back",
    "false": "some part of the claim is not stated by the quote, or the surrounding text counts against it",
}
DECISION_VERSION = hashlib.sha256((INSTRUCTIONS + json.dumps(CRITERIA, sort_keys=True)).encode()).hexdigest()[:8]


class Decider(Protocol):
    """What a decision reader needs from a model: the probability that a yes/no question about some data is true."""

    name: str
    calls: int

    def probability(self, state: dict, instructions: str, criteria: dict[str, str]) -> float:
        """The probability, from 0 to 1, that the answer to `instructions` about `state` is yes."""
        ...


class JevBackend:
    """TypeSafe AI's Jev over HTTP. The key is read from TYPESAFE_API_KEY. One question to a call."""

    URL = "https://api.typesafe.ai/v1/systemone"

    def __init__(
        self,
        model: str = "jev-latest",
        api_key: str | None = None,
        timeout: int = 60,
        post: Callable[[str, dict, dict], dict] | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("TYPESAFE_API_KEY") or ""
        if not self.api_key and post is None:
            raise BackendError("no key for the TypeSafe API: set TYPESAFE_API_KEY")
        self.timeout = timeout
        self.name = f"jev ({model})"
        self.calls = 0
        self.served_by = ""  # the exact model version the API says answered
        self.tokens = {"input": 0, "output": 0}
        self._post = post or self._http_post

    def _http_post(self, url: str, headers: dict, body: dict) -> dict:
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310 - a fixed https address
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            raise BackendError(f"the API answered {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from e
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            raise BackendError(f"the API call failed: {e}") from e

    def probability(self, state: dict, instructions: str, criteria: dict[str, str]) -> float:
        """The probability that the answer is yes, from one "noul" question."""
        body = {
            "model": self.model,
            "state": state,
            "questions": {"stated": {"type": "noul", "instructions": instructions, "criteria": criteria}},
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        reply = self._post(self.URL, headers, body)
        self.calls += 1
        try:
            p = reply["answers"]["stated"]["noul"]
            usage = reply.get("usage") or {}
            self.tokens["input"] += int(usage.get("input_tokens") or 0)
            self.tokens["output"] += int(usage.get("output_tokens") or 0)
            self.served_by = str(reply.get("model") or self.served_by)
        except (KeyError, TypeError, ValueError) as e:
            raise BackendError(f"the API returned no answer: {str(reply)[:300]}") from e
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not 0 <= p <= 1:
            raise BackendError(f"the API returned something that is not a probability: {p!r}")
        return float(p)


def state_of(claim: Claim, ev: Evidence) -> dict:
    """What the model is shown for one claim: the title, the claim, the passage, and the page around it."""
    before, between, after = quote_context(claim.quote, ev.text) or ("", "", "")
    shown = {
        "page_title": ev.title,
        "claim": claim.text,
        "quote": quote_passage(claim.quote, ev.text) or claim.quote,
        "before": before,
        "between": between,
        "after": after,
    }
    return {k: v for k, v in shown.items() if v}


def read_probabilities(
    claims: Sequence[Claim], ledger: Mapping[str, Evidence], decider: Decider, errors: list[str] | None = None
) -> dict[str, float]:
    """claim id -> the probability that its quote states it. A claim the model did not answer is absent.

    One claim to a call, each call tried twice. A page's text meets only the claim that quotes it.
    """
    out: dict[str, float] = {}
    for c in claims:
        for attempt in (1, 2):
            try:
                out[c.id] = decider.probability(state_of(c, ledger[c.evidence_id]), INSTRUCTIONS, CRITERIA)
                break
            except BackendError as e:
                if attempt == 2 and errors is not None:
                    errors.append(str(e))
    return out


def check_with_decider(
    claims: Sequence[Claim], ledger: Mapping[str, Evidence], decider: Decider, threshold: float = 0.5, **kw
) -> Report:
    """Both stages, the second on a decision model: a claim stands when the probability reaches `threshold`."""
    if not 0 < threshold <= 1:
        raise ValueError("the threshold is a probability above 0 and at most 1")
    verdicts = [check_claim(c, ledger, **kw) for c in claims]
    standing = [i for i, v in enumerate(verdicts) if v.supported]
    errors: list[str] = []
    numbered = [
        Claim(str(i), claims[i].text, claims[i].quote, claims[i].evidence_id, claims[i].subject) for i in standing
    ]
    read = read_probabilities(numbered, ledger, decider, errors)
    for i in standing:
        v = verdicts[i]
        if str(i) not in read:
            verdicts[i] = Verdict(
                v.claim_id, False, "unread", errors[0][:300] if errors else "", match=v.match, url=v.url
            )
        elif read[str(i)] < threshold:
            why = f"probability {read[str(i)]:.2f} that the quote states it, under {threshold:.2f}"
            verdicts[i] = Verdict(v.claim_id, False, "not_stated", why, match=v.match, url=v.url)
    return Report(verdicts)
