"""Auto-tagging engine with declarative rules and Python hooks."""

from __future__ import annotations

import fnmatch
import importlib.util
import sys
import types
from pathlib import Path
from typing import Any, Callable, Optional

import yaml

from sbs.archive.entry import ArchiveEntry
from sbs.archive.session_data import SessionData
from sbs.core.utils import log

# ---------------------------------------------------------------------------
# Agent-state taxonomy loader (cached)
# ---------------------------------------------------------------------------

_TAXONOMY_CACHE: Optional[dict[str, dict]] = None
_TAXONOMY_PATH = Path(__file__).resolve().parent.parent.parent.parent / "storage" / "tagging" / "agent_state_taxonomy.yaml"


def load_agent_state_taxonomy(
    path: Optional[Path] = None,
) -> dict[str, dict]:
    """Load and cache the agent-state taxonomy.

    Returns a flat dict of ``{tag_name: {"description": str, "dimension": str}}``
    for every tag defined in the taxonomy YAML.
    """
    global _TAXONOMY_CACHE
    if _TAXONOMY_CACHE is not None:
        return _TAXONOMY_CACHE

    taxonomy_path = path or _TAXONOMY_PATH
    if not taxonomy_path.exists():
        raise FileNotFoundError(f"Agent-state taxonomy not found at {taxonomy_path}")

    with open(taxonomy_path) as f:
        data = yaml.safe_load(f)

    result: dict[str, dict] = {}
    for dim_name, dim_data in data.get("dimensions", {}).items():
        for tag_entry in dim_data.get("tags", []):
            tag_name = tag_entry["name"]
            result[tag_name] = {
                "description": tag_entry.get("description", ""),
                "dimension": dim_name,
            }

    _TAXONOMY_CACHE = result
    return result


def _reset_taxonomy_cache() -> None:
    """Reset the taxonomy cache (for testing)."""
    global _TAXONOMY_CACHE
    _TAXONOMY_CACHE = None


class TaggingEngine:
    """
    Evaluate declarative rules and execute Python hooks to generate tags.

    Rules are defined in YAML format with conditions that match against
    entry context. Hooks are Python modules that can perform complex analysis.
    """

    def __init__(self, rules_path: Optional[Path] = None, hooks_dir: Optional[Path] = None):
        self.rules_path = rules_path
        self.hooks_dir = hooks_dir
        self.rules: list[dict] = []
        self.hooks: list[dict] = []

        if rules_path and rules_path.exists():
            self._load_rules(rules_path)

    def _load_rules(self, path: Path) -> None:
        """Load rules from YAML file."""
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
            self.rules = data.get("rules", [])
            self.hooks = data.get("hooks", [])
            log.dim(f"Loaded {len(self.rules)} rules and {len(self.hooks)} hooks")
        except Exception as e:
            log.warning(f"Failed to load rules from {path}: {e}")

    def evaluate(
        self,
        entry: ArchiveEntry,
        context: dict[str, Any],
        sessions: Optional[list[SessionData]] = None,
    ) -> list[str]:
        """
        Evaluate all rules and hooks against entry context.

        Args:
            entry: The archive entry being tagged
            context: Dict of field values to evaluate rules against
            sessions: Optional list of session data for hook analysis

        Returns:
            List of tags to apply
        """
        tags = []

        # Evaluate declarative rules
        for rule in self.rules:
            rule_tags = self._evaluate_rule(rule, context)
            if rule_tags:
                tags.extend(rule_tags)
                log.dim(f"Rule '{rule.get('name', 'unnamed')}' matched: {rule_tags}")

        # Execute Python hooks
        if self.hooks_dir and sessions:
            for hook in self.hooks:
                hook_tags = self._execute_hook(hook, entry, sessions)
                if hook_tags:
                    tags.extend(hook_tags)
                    log.dim(f"Hook '{hook.get('name', 'unnamed')}' returned: {hook_tags}")

        # Deduplicate while preserving order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)

        return unique_tags

    def _evaluate_rule(self, rule: dict, context: dict[str, Any]) -> list[str]:
        """Evaluate a single rule against context."""
        condition = rule.get("condition", {})
        if not condition:
            return []

        field = condition.get("field")
        if not field or field not in context:
            return []

        value = context[field]

        # Evaluate condition operators
        if "equals" in condition:
            if value == condition["equals"]:
                return rule.get("tags", [])

        if "not_equals" in condition:
            if value != condition["not_equals"]:
                return rule.get("tags", [])

        if "greater_than" in condition:
            try:
                if float(value) > float(condition["greater_than"]):
                    return rule.get("tags", [])
            except (TypeError, ValueError):
                pass

        if "less_than" in condition:
            try:
                if float(value) < float(condition["less_than"]):
                    return rule.get("tags", [])
            except (TypeError, ValueError):
                pass

        if "contains" in condition:
            if isinstance(value, str) and condition["contains"] in value:
                return rule.get("tags", [])
            if isinstance(value, list) and condition["contains"] in value:
                return rule.get("tags", [])

        if "matches_any" in condition:
            patterns = condition["matches_any"]
            if isinstance(value, list):
                for item in value:
                    for pattern in patterns:
                        if fnmatch.fnmatch(str(item), pattern):
                            return rule.get("tags", [])
            elif isinstance(value, str):
                for pattern in patterns:
                    if fnmatch.fnmatch(value, pattern):
                        return rule.get("tags", [])

        if "is_empty" in condition:
            is_empty = not value or (isinstance(value, (list, dict, str)) and len(value) == 0)
            if is_empty == condition["is_empty"]:
                return rule.get("tags", [])

        return []

    def _execute_hook(
        self,
        hook: dict,
        entry: ArchiveEntry,
        sessions: list[SessionData],
    ) -> list[str]:
        """Execute a Python hook module."""
        if not self.hooks_dir:
            return []

        module_name = hook.get("module")
        function_name = hook.get("function")

        if not module_name or not function_name:
            return []

        module_path = self.hooks_dir / f"{module_name}.py"
        if not module_path.exists():
            log.warning(f"Hook module not found: {module_path}")
            return []

        try:
            # Register hooks directory as a package so relative imports work
            hooks_pkg_name = "tagging_hooks"
            if hooks_pkg_name not in sys.modules:
                hooks_pkg = types.ModuleType(hooks_pkg_name)
                hooks_pkg.__path__ = [str(self.hooks_dir)]
                hooks_pkg.__package__ = hooks_pkg_name
                sys.modules[hooks_pkg_name] = hooks_pkg

            # Load module with package-qualified name
            qualified_name = f"{hooks_pkg_name}.{module_name}"
            spec = importlib.util.spec_from_file_location(
                qualified_name, module_path, submodule_search_locations=[]
            )
            if spec is None or spec.loader is None:
                return []

            module = importlib.util.module_from_spec(spec)
            module.__package__ = hooks_pkg_name
            sys.modules[qualified_name] = module
            spec.loader.exec_module(module)

            # Get and call the function
            func = getattr(module, function_name, None)
            if func is None:
                log.warning(f"Hook function not found: {function_name} in {module_name}")
                return []

            # Call hook with entry and sessions
            result = func(entry, sessions)

            # Ensure result is a list of strings
            if isinstance(result, list):
                return [str(t) for t in result]
            return []

        except Exception as e:
            log.warning(f"Hook execution failed for {module_name}.{function_name}: {e}")
            return []


def build_tagging_context(
    entry: ArchiveEntry,
    build_success: Optional[bool] = None,
    build_duration_seconds: Optional[float] = None,
    repos_changed: Optional[list[str]] = None,
    files_modified: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Build a context dict for rule evaluation.

    Combines entry data with additional build context.
    """
    context = {
        "project": entry.project,
        "trigger": entry.trigger,
        "has_notes": bool(entry.notes),
        "tag_count": len(entry.tags),
        "screenshot_count": len(entry.screenshots),
        "repo_count": len(entry.repo_commits),
        "issue_refs": entry.issue_refs,
        "pr_refs": entry.pr_refs,
    }

    # Add build context
    if build_success is not None:
        context["build_success"] = build_success

    if build_duration_seconds is not None:
        context["build_duration_seconds"] = build_duration_seconds

    if repos_changed is not None:
        context["repos_changed"] = repos_changed
        context["repos_changed_count"] = len(repos_changed)

    if files_modified is not None:
        context["files_modified"] = files_modified
        context["files_modified_count"] = len(files_modified)

    # ---- State machine (from entry directly) ----
    context["skill"] = entry.global_state.get("skill") if entry.global_state else None
    context["substate"] = entry.global_state.get("substate") if entry.global_state else None
    context["state_transition"] = entry.state_transition
    context["has_epoch_summary"] = entry.epoch_summary is not None
    context["gate_passed"] = entry.gate_validation.get("passed") if entry.gate_validation else None

    # ---- Claude data (load from sidecar if needed) ----
    claude_data = entry.claude_data or entry.load_claude_data()
    if claude_data:
        context["session_count"] = len(claude_data.get("session_ids", []))
        context["tool_call_count"] = claude_data.get("tool_call_count", 0)
        context["message_count"] = claude_data.get("message_count", 0)
        context["plan_count"] = len(claude_data.get("plan_files", []))

        # Token counts
        context["total_input_tokens"] = claude_data.get("total_input_tokens", 0)
        context["total_output_tokens"] = claude_data.get("total_output_tokens", 0)
        context["total_tokens"] = context["total_input_tokens"] + context["total_output_tokens"]
        context["cache_read_tokens"] = claude_data.get("cache_read_tokens", 0)

        # Thinking and tool diversity
        context["thinking_block_count"] = claude_data.get("thinking_block_count", 0)
        context["unique_tools_count"] = len(claude_data.get("unique_tools_used", []))
        context["model_versions"] = claude_data.get("model_versions_used", [])
    else:
        # Ensure token fields exist even without claude_data
        context["total_input_tokens"] = 0
        context["total_output_tokens"] = 0
        context["total_tokens"] = 0
        context["cache_read_tokens"] = 0
        context["thinking_block_count"] = 0
        context["unique_tools_count"] = 0
        context["model_versions"] = []

    # ---- Quality (from entry) ----
    context["quality_overall"] = (
        entry.quality_scores.get("overall") if entry.quality_scores else None
    )
    context["quality_delta"] = (
        entry.quality_delta.get("overall") if entry.quality_delta else None
    )

    return context
