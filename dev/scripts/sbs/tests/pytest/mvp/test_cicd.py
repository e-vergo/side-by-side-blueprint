"""
CI/CD Tests (88-95)

Verifies GitHub Action and deployment configuration.
"""

from __future__ import annotations

import pytest
import yaml

from .conftest import MONOREPO_ROOT


ACTION_PATH = MONOREPO_ROOT / "toolchain" / "dress-blueprint-action"


@pytest.mark.evergreen
class TestGitHubAction:
    """Tests for GitHub Action configuration."""

    def test_action_yml_exists(self):
        """88. action.yml file exists."""
        action_file = ACTION_PATH / "action.yml"
        assert action_file.exists(), "action.yml should exist"

    def test_action_yml_valid_yaml(self):
        """89. action.yml is valid YAML."""
        action_file = ACTION_PATH / "action.yml"
        if not action_file.exists():
            pytest.skip("action.yml not found")

        content = action_file.read_text()
        try:
            data = yaml.safe_load(content)
            assert data is not None, "YAML should parse to non-null"
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML: {e}")

    def test_action_has_name(self):
        """90. Action has name field."""
        action_file = ACTION_PATH / "action.yml"
        if not action_file.exists():
            pytest.skip("action.yml not found")

        data = yaml.safe_load(action_file.read_text())
        assert "name" in data, "Action should have name"

    def test_action_has_inputs(self):
        """91. Action defines inputs."""
        action_file = ACTION_PATH / "action.yml"
        if not action_file.exists():
            pytest.skip("action.yml not found")

        data = yaml.safe_load(action_file.read_text())
        assert "inputs" in data, "Action should have inputs"
        assert len(data["inputs"]) > 0, "Action should have at least one input"

    def test_action_project_directory_input(self):
        """92. Action has project-directory input."""
        action_file = ACTION_PATH / "action.yml"
        if not action_file.exists():
            pytest.skip("action.yml not found")

        data = yaml.safe_load(action_file.read_text())
        inputs = data.get("inputs", {})
        assert "project-directory" in inputs, "Should have project-directory input"

    def test_action_has_runs(self):
        """93. Action has runs configuration."""
        action_file = ACTION_PATH / "action.yml"
        if not action_file.exists():
            pytest.skip("action.yml not found")

        data = yaml.safe_load(action_file.read_text())
        assert "runs" in data, "Action should have runs configuration"

    def test_action_uses_composite(self):
        """94. Action uses composite type."""
        action_file = ACTION_PATH / "action.yml"
        if not action_file.exists():
            pytest.skip("action.yml not found")

        data = yaml.safe_load(action_file.read_text())
        runs = data.get("runs", {})
        assert runs.get("using") == "composite", "Action should use composite"

    def test_action_has_steps(self):
        """95. Action has execution steps."""
        action_file = ACTION_PATH / "action.yml"
        if not action_file.exists():
            pytest.skip("action.yml not found")

        data = yaml.safe_load(action_file.read_text())
        runs = data.get("runs", {})
        steps = runs.get("steps", [])
        assert len(steps) > 5, "Action should have multiple steps"
