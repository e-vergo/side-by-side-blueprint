"""
Validator registry for plugin discovery and registration.

Provides a centralized registry where validators register themselves,
enabling dynamic discovery and loading based on task requirements.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Callable, Optional, Type, TypeVar

from .base import Validator

# Type variable for the decorator
V = TypeVar("V", bound=Type[Validator])


class ValidatorRegistry:
    """Registry for validator plugins.

    Manages registration, lookup, and discovery of validators.
    Validators register via the @register_validator decorator or
    by calling registry.register() directly.
    """

    def __init__(self) -> None:
        self._validators: dict[str, Validator] = {}
        self._by_category: dict[str, list[str]] = {}

    def register(self, validator: Validator) -> None:
        """Register a validator instance.

        Args:
            validator: Validator instance to register. Must implement
                the Validator protocol (have name, category, validate).

        Raises:
            TypeError: If validator doesn't implement the Validator protocol.
            ValueError: If a validator with the same name is already registered.
        """
        # Validate implements protocol
        if not isinstance(validator, Validator):
            raise TypeError(
                f"Validator must implement the Validator protocol. "
                f"Got {type(validator).__name__} which is missing required "
                f"attributes/methods (name, category, validate)."
            )

        name = validator.name
        category = validator.category

        # Check for duplicate registration
        if name in self._validators:
            existing = self._validators[name]
            raise ValueError(
                f"Validator '{name}' is already registered "
                f"(existing: {type(existing).__name__}, "
                f"new: {type(validator).__name__})"
            )

        # Validate category
        valid_categories = {"visual", "timing", "code", "git"}
        if category not in valid_categories:
            raise ValueError(
                f"Invalid category '{category}' for validator '{name}'. "
                f"Must be one of: {', '.join(sorted(valid_categories))}"
            )

        # Register
        self._validators[name] = validator

        # Index by category
        if category not in self._by_category:
            self._by_category[category] = []
        self._by_category[category].append(name)

    def get(self, name: str) -> Optional[Validator]:
        """Get a validator by name.

        Args:
            name: Unique identifier of the validator.

        Returns:
            The validator instance, or None if not found.
        """
        return self._validators.get(name)

    def get_by_category(self, category: str) -> list[Validator]:
        """Get all validators in a category.

        Args:
            category: Category to filter by ('visual', 'timing', 'code', 'git').

        Returns:
            List of validators in that category (may be empty).
        """
        names = self._by_category.get(category, [])
        return [self._validators[name] for name in names]

    def list_all(self) -> list[Validator]:
        """Get all registered validators.

        Returns:
            List of all validator instances.
        """
        return list(self._validators.values())

    def list_names(self) -> list[str]:
        """Get names of all registered validators.

        Returns:
            List of validator names, sorted alphabetically.
        """
        return sorted(self._validators.keys())

    def list_categories(self) -> list[str]:
        """Get all categories that have registered validators.

        Returns:
            List of category names with at least one validator.
        """
        return sorted(self._by_category.keys())

    def clear(self) -> None:
        """Clear all registered validators. Primarily for testing."""
        self._validators.clear()
        self._by_category.clear()

    def __len__(self) -> int:
        """Return the number of registered validators."""
        return len(self._validators)

    def __contains__(self, name: str) -> bool:
        """Check if a validator is registered by name."""
        return name in self._validators


# Module-level singleton instance
registry = ValidatorRegistry()


def register_validator(cls: V) -> V:
    """Decorator to register a validator class.

    The decorated class is instantiated (with no arguments) and registered
    with the global registry. The class must implement the Validator protocol.

    Usage:
        @register_validator
        class MyValidator(BaseValidator):
            def __init__(self):
                super().__init__("my-validator", "visual")

            def validate(self, context):
                ...

    Args:
        cls: Validator class to register.

    Returns:
        The class unchanged (for use as a decorator).

    Raises:
        TypeError: If the class doesn't implement the Validator protocol.
    """
    # Instantiate and register
    instance = cls()
    registry.register(instance)
    return cls


def discover_validators() -> int:
    """Import all validator modules to trigger registration.

    Scans the validators package for modules and imports them. Each module
    using @register_validator will have its validators registered upon import.

    Also recursively scans subpackages (e.g., sbs.tests.validators.design).

    Returns:
        Number of validators discovered and registered.

    Note:
        This function is idempotent - calling it multiple times won't
        re-register validators (they'll raise ValueError on duplicate).
    """
    import sbs.tests.validators as validators_pkg

    initial_count = len(registry)

    # Get the package path
    package_path = validators_pkg.__path__

    # Modules to skip at any level
    skip_modules = {"__init__", "base", "registry"}
    # Also skip test modules
    skip_prefixes = {"test_", "conftest"}

    def _import_recursive(package_name: str, package_path: list[str]) -> None:
        """Recursively import modules from a package."""
        for module_info in pkgutil.iter_modules(package_path):
            if module_info.name in skip_modules:
                continue
            # Skip test files
            if any(module_info.name.startswith(prefix) for prefix in skip_prefixes):
                continue

            full_name = f"{package_name}.{module_info.name}"

            try:
                module = importlib.import_module(full_name)

                # If it's a package, recurse into it
                if module_info.ispkg and hasattr(module, "__path__"):
                    _import_recursive(full_name, module.__path__)

            except ImportError as e:
                # Log but don't fail - allows partial discovery
                import warnings

                warnings.warn(
                    f"Failed to import validator module '{full_name}': {e}"
                )

    _import_recursive("sbs.tests.validators", list(package_path))

    return len(registry) - initial_count
