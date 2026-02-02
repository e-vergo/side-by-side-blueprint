"""Auto-tagging engine with declarative rules and Python hooks."""

from __future__ import annotations

import fnmatch
import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable, Optional

import yaml

from sbs.archive.entry import ArchiveEntry
from sbs.archive.session_data import SessionData
from sbs.core.utils import log


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
            # Load module dynamically
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                return []

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
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

    # Add claude_data context if available
    if entry.claude_data:
        context["session_count"] = len(entry.claude_data.get("session_ids", []))
        context["tool_call_count"] = entry.claude_data.get("tool_call_count", 0)
        context["message_count"] = entry.claude_data.get("message_count", 0)
        context["plan_count"] = len(entry.claude_data.get("plan_files", []))

    return context
