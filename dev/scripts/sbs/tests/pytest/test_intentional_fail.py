"""Intentional failure test for gate validation.

This test exists ONLY to validate that the gate enforcement mechanism works.
It should be deleted after the validation exercise is complete.

DO NOT COMMIT THIS FILE.
"""

import pytest


@pytest.mark.temporary
def test_intentional_gate_failure():
    """This test intentionally fails to validate gate enforcement."""
    assert False, "Intentional failure for gate validation - this proves gates work"
