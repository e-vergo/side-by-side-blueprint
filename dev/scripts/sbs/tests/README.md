# sbs.tests - Testing Infrastructure

All testing and validation infrastructure for Side-by-Side Blueprint.

## Structure

```
tests/
├── compliance/     # Visual compliance validation
├── validators/     # Validator implementations
│   ├── base.py     # Base validator classes
│   ├── registry.py # @register_validator decorator
│   └── design/     # Design validators (color, clarity, etc.)
├── rubrics/        # Quality rubrics (definitions, CLI)
└── pytest/         # Pytest test suite
```

## Subpackages

### compliance/

Visual compliance validation loop that:
1. Captures screenshots from running site
2. Runs AI vision analysis against criteria
3. Tracks pass/fail in persistent ledger
4. Loops until 100% compliance

See [compliance/README.md](compliance/README.md) for details.

### validators/

Reusable validation components:
- **base.py** - `Validator` abstract base class, `ValidationResult`
- **registry.py** - `@register_validator` decorator, `get_validator()`
- **design/** - Design-focused validators (color match, dashboard clarity, etc.)

### rubrics/

Quality rubric system:
- **rubric.py** - `Rubric`, `RubricCriterion`, `RubricEvaluation` dataclasses
- **cmd.py** - CLI commands (create, show, list, evaluate, delete)

### pytest/

Pytest test suite:
- **conftest.py** - Shared fixtures
- **test_cli.py** - CLI integration tests
- **test_ledger_health.py** - Ledger validation tests
- **validators/** - Validator unit tests

## Usage

```python
from sbs.tests.validators import ValidationContext, get_validator
from sbs.tests.rubrics import Rubric, RubricEvaluation
from sbs.tests.compliance import ComplianceLedger, load_ledger
```

## Running Tests

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python -m pytest sbs/tests/pytest -v
```
