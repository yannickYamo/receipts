"""receipts: every claim carries a quote from a page that code fetched, or it is cut."""

from .core import Claim, Evidence, Report, Verdict, check_claim, check_claims
from .ledger import Ledger

__all__ = ["Claim", "Evidence", "Ledger", "Report", "Verdict", "check_claim", "check_claims"]
__version__ = "0.1.0"
