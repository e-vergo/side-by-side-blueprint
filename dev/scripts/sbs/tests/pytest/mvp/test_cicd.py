"""
CI/CD Tests (88-95) + Extended CI/CD Tests (179-186)

Verifies GitHub Action configuration, expected inputs, and
deployed asset structure.
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


# =========================================================================
# Extended: Action Input Coverage
# =========================================================================


@pytest.mark.evergreen
class TestActionInputs:
    """Tests for documented action inputs."""

    @pytest.fixture(autouse=True)
    def _load_action(self):
        """Load action.yml data."""
        action_file = ACTION_PATH / "action.yml"
        if not action_file.exists():
            pytest.skip("action.yml not found")
        self.action_data = yaml.safe_load(action_file.read_text())
        self.inputs = self.action_data.get("inputs", {})

    def test_lean_version_input(self):
        """179. Action has lean-version input."""
        assert "lean-version" in self.inputs, \
            "Action should have lean-version input"

    def test_docgen4_mode_input(self):
        """180. Action has docgen4-mode input."""
        assert "docgen4-mode" in self.inputs, \
            "Action should have docgen4-mode input"

    def test_deploy_pages_input(self):
        """181. Action has deploy-pages input."""
        assert "deploy-pages" in self.inputs, \
            "Action should have deploy-pages input"

    def test_all_four_documented_inputs_present(self):
        """182. All 4 documented inputs exist."""
        expected = ["project-directory", "lean-version", "docgen4-mode", "deploy-pages"]
        for input_name in expected:
            assert input_name in self.inputs, \
                f"Documented input '{input_name}' missing from action.yml"

    def test_inputs_have_descriptions(self):
        """183. All inputs have description fields."""
        for name, config in self.inputs.items():
            assert "description" in config, \
                f"Input '{name}' should have a description"


# =========================================================================
# Extended: Action Assets
# =========================================================================


@pytest.mark.evergreen
class TestActionAssets:
    """Tests that CI/CD action includes all required assets."""

    ASSETS_DIR = ACTION_PATH / "assets"

    def test_assets_dir_exists(self):
        """184. Assets directory exists in action repo."""
        assert self.ASSETS_DIR.exists(), \
            "dress-blueprint-action/assets/ should exist"

    def test_assets_has_all_css(self):
        """185. Action assets include all 4 CSS files."""
        for name in ["common.css", "blueprint.css", "paper.css", "dep_graph.css"]:
            path = self.ASSETS_DIR / name
            assert path.exists(), f"Action assets missing CSS: {name}"

    def test_assets_has_all_js(self):
        """186. Action assets include both JS files."""
        for name in ["plastex.js", "verso-code.js"]:
            path = self.ASSETS_DIR / name
            assert path.exists(), f"Action assets missing JS: {name}"
