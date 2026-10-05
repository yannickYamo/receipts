"""receipts: every claim carries a quote from a page that code fetched, or it is cut."""

from importlib.metadata import PackageNotFoundError, version

from .core import Claim, Evidence, Report, Verdict, check_claim, check_claims
from .ledger import Ledger

__all__ = ["Claim", "Evidence", "Ledger", "Report", "Verdict", "check_claim", "check_claims"]
try:
    __version__ = version("claim-receipts")  # the one place it is written is pyproject.toml
except PackageNotFoundError:  # run from a checkout that was never installed
    __version__ = "0+unknown"
