"""README staleness detection based on git state."""
from .check import check_all_repos, format_report, format_json, RepoStatus

__all__ = ["check_all_repos", "format_report", "format_json", "RepoStatus"]
