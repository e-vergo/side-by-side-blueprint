"""
Pluggable validator system for compliance checking.

This module provides the base types and protocols for implementing validators.
Validators can be visual (screenshot-based), timing-based, code-based, or git-based.

Usage:
    from sbs.tests.validators import register_validator, BaseValidator, registry

    @register_validator
    class MyValidator(BaseValidator):
        def __init__(self):
            super().__init__("my-validator", "visual")

        def validate(self, context):
            # ... validation logic ...
            return self._make_pass()

    # Later, to run validators:
    from sbs.tests.validators import discover_validators, registry

    discover_validators()  # Import all validator modules
    for validator in registry.get_by_category("visual"):
        result = validator.validate(context)
"""

from .base import (
    BaseValidator,
    CriteriaProvider,
    ValidationContext,
    Validator,
    ValidatorResult,
)
from .registry import discover_validators, register_validator, registry

__all__ = [
    # Base types
    "ValidationContext",
    "ValidatorResult",
    # Protocols
    "Validator",
    "CriteriaProvider",
    # Base class
    "BaseValidator",
    # Registry
    "registry",
    "register_validator",
    "discover_validators",
]
