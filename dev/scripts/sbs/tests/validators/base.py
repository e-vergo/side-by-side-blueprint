"""
Base types and protocols for the pluggable validator system.

Defines the contract that all validators must follow, plus data containers
for validation context and results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

from sbs.tests.compliance.criteria import Criterion


# =============================================================================
# Data Containers
# =============================================================================


@dataclass
class ValidationContext:
    """Context provided to validators for execution.

    Contains all information a validator might need to perform its checks,
    including project metadata, file paths, and optional build artifacts.
    """

    project: str
    """Project identifier (e.g., 'SBSTest', 'GCR')."""

    project_root: Path
    """Absolute path to project directory containing lakefile.toml."""

    commit: str
    """Git commit hash of the project being validated."""

    screenshots_dir: Optional[Path] = None
    """Path to directory containing captured screenshots, if available."""

    build_log: Optional[Path] = None
    """Path to build log file, if available."""

    manifest_path: Optional[Path] = None
    """Path to manifest.json, if available."""

    site_dir: Optional[Path] = None
    """Path to generated site directory (.lake/build/runway/)."""

    repo_commits: dict[str, str] = field(default_factory=dict)
    """Commit hashes for toolchain repos (SubVerso, Dress, Runway, etc.)."""

    extra: dict[str, Any] = field(default_factory=dict)
    """Extension point for validator-specific context data."""


@dataclass
class ValidatorResult:
    """Result returned by a validator after execution.

    Captures pass/fail status, detailed findings, optional metrics,
    and a confidence score for the validation.
    """

    validator: str
    """Name of the validator that produced this result."""

    passed: bool
    """Whether the validation passed."""

    findings: list[str] = field(default_factory=list)
    """Human-readable descriptions of issues found (empty if passed)."""

    metrics: dict[str, Any] = field(default_factory=dict)
    """Optional metrics: timing data, counts, measurements, etc."""

    confidence: float = 1.0
    """Confidence in the result (0.0-1.0). Lower for heuristic checks."""

    criteria_results: dict[str, bool] = field(default_factory=dict)
    """Per-criterion pass/fail results, keyed by criterion ID."""

    details: dict[str, Any] = field(default_factory=dict)
    """Additional structured data for debugging or reporting."""


# =============================================================================
# Protocols (Interfaces)
# =============================================================================


@runtime_checkable
class Validator(Protocol):
    """Protocol for validators.

    Validators perform specific checks against a project and return results.
    Each validator has a name, category, and implements the validate method.

    Categories:
        - "visual": Screenshot-based validation (AI vision, pixel comparison)
        - "timing": Build time and performance checks
        - "code": Static analysis of generated artifacts
        - "git": Repository state and history checks
    """

    @property
    def name(self) -> str:
        """Unique identifier for this validator."""
        ...

    @property
    def category(self) -> str:
        """Validator category: 'visual', 'timing', 'code', or 'git'."""
        ...

    def validate(self, context: ValidationContext) -> ValidatorResult:
        """Execute validation and return results.

        Args:
            context: Validation context with project info and paths.

        Returns:
            ValidatorResult with pass/fail status and findings.
        """
        ...


@runtime_checkable
class CriteriaProvider(Protocol):
    """Protocol for validators that define their own criteria.

    Validators implementing this protocol can contribute criteria definitions
    that get merged with the static criteria in criteria.py.
    """

    def get_criteria(self) -> list[Criterion]:
        """Return the criteria this validator checks.

        Returns:
            List of Criterion objects defining what this validator checks.
        """
        ...


# =============================================================================
# Base Classes (Optional Implementations)
# =============================================================================


class BaseValidator:
    """Optional base class providing common validator functionality.

    Validators can inherit from this for convenience, or implement the
    Validator protocol directly. This base class provides sensible defaults
    and helper methods.
    """

    def __init__(self, name: str, category: str) -> None:
        self._name = name
        self._category = category

    @property
    def name(self) -> str:
        return self._name

    @property
    def category(self) -> str:
        return self._category

    def validate(self, context: ValidationContext) -> ValidatorResult:
        """Override this method in subclasses."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement validate()"
        )

    def _make_result(
        self,
        passed: bool,
        findings: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> ValidatorResult:
        """Helper to create a ValidatorResult with this validator's name."""
        return ValidatorResult(
            validator=self.name,
            passed=passed,
            findings=findings or [],
            **kwargs,
        )

    def _make_pass(self, **kwargs: Any) -> ValidatorResult:
        """Helper to create a passing result."""
        return self._make_result(passed=True, **kwargs)

    def _make_fail(self, findings: list[str], **kwargs: Any) -> ValidatorResult:
        """Helper to create a failing result."""
        return self._make_result(passed=False, findings=findings, **kwargs)
