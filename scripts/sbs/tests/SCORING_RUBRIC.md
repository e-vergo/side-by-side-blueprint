# Quality Score Rubric

Version: 1.0
Created: 2026-02-01
Baseline Score: 87.21/100

## Score Calculation

```
quality_score = Σ(test_score × weight)
```

## Test Weights

### Deterministic Tests (50% total)

| Test | Name | Weight | Scoring Formula |
|------|------|--------|-----------------|
| T1 | CLI Execution | 10% | Pass=100, Fail=0 |
| T2 | Ledger Population | 10% | `population_rate × 100` |
| T5 | Status Color Match | 15% | Pass=100, Fail=0 |
| T6 | CSS Variable Coverage | 15% | `coverage × 100` |

### Heuristic Tests (50% total)

| Test | Name | Weight | Scoring Formula |
|------|------|--------|-----------------|
| T3 | Dashboard Clarity | 10% | Pass=100, Fail=0 |
| T4 | Toggle Discoverability | 10% | `score × 10` (0-10 scale) |
| T7 | Jarring-Free Check | 15% | Pass=100, Fail=0 |
| T8 | Professional Score | 15% | `score × 10` (0-10 scale) |

## Thresholds

| Test | Metric | Threshold | Current | Status |
|------|--------|-----------|---------|--------|
| T1 | CLI execution | Pass | Pass | ✅ |
| T2 | Population rate | ≥70% | 63.4% | ❌ |
| T5 | Colors matched | 6/6 | 6/6 | ✅ |
| T6 | CSS coverage | ≥95% | 73.4% | ❌ |
| T3 | Questions answerable | 3/3 | 3/3 | ✅ |
| T4 | Discovery score | ≥7.0 | 7.0 | ✅ |
| T7 | Jarring-free | Pass | Pass | ✅ |
| T8 | Professional score | ≥8.5 | 8.57 | ✅ |

## Baseline (2026-02-01)

```
Deterministic:
  T1: 100 × 0.10 = 10.00
  T2:  63 × 0.10 =  6.34
  T5: 100 × 0.15 = 15.00
  T6:  73 × 0.15 = 11.01
  ─────────────────────
  Subtotal:       42.35/50

Heuristic:
  T3: 100 × 0.10 = 10.00
  T4:  70 × 0.10 =  7.00
  T7: 100 × 0.15 = 15.00
  T8:  86 × 0.15 = 12.86
  ─────────────────────
  Subtotal:       44.86/50

TOTAL: 87.21/100
```

## Improvement Opportunities

### High Impact (Large Score Gains)

1. **T6 CSS Coverage** (73.4% → 95%+)
   - Current: 73.4% = 11.01 points
   - Target: 95% = 14.25 points
   - **Gain: +3.24 points**
   - Fix: Remove 14 hardcoded color violations

2. **T2 Ledger Population** (63.4% → 100%)
   - Current: 63.4% = 6.34 points
   - Target: 100% = 10.00 points
   - **Gain: +3.66 points**
   - Fix: Populate or remove 4 dead fields

### Medium Impact

3. **T4 Toggle Discoverability** (7.0 → 8.5)
   - Current: 7.0 = 7.00 points
   - Target: 8.5 = 8.50 points
   - **Gain: +1.50 points**
   - Fix: Add toggle icon, improve visibility

4. **T8 Professional Score** (8.57 → 9.5)
   - Current: 8.57 = 12.86 points
   - Target: 9.5 = 14.25 points
   - **Gain: +1.39 points**
   - Fix: Improve alignment, polish details

## Maximum Achievable Score

If all improvements implemented:
- T6: 73.4% → 99% = +3.84 points
- T2: 63.4% → 100% = +3.66 points
- T4: 7.0 → 9.0 = +2.00 points
- T8: 8.57 → 9.5 = +1.39 points

**Theoretical Maximum: 98.10/100**

## Score History

| Date | Score | Changes |
|------|-------|---------|
| 2026-02-01 | 87.21 | Baseline |
| 2026-02-01 | 89.69 | +2.48: Fixed 20 CSS violations, removed 3 dead ledger fields |

## Running Tests

```bash
# Run all deterministic tests
cd /Users/eric/GitHub/Side-By-Side-Blueprint/scripts
/opt/homebrew/bin/pytest sbs/tests/ -v

# Run specific validator
python -c "
from pathlib import Path
from sbs.validators import ValidationContext, discover_validators, registry
discover_validators()
validator = registry.get('ledger-health')
ctx = ValidationContext(project='SBSTest', project_root=Path('.'), commit='test')
result = validator.validate(ctx)
print(result.metrics)
"
```

## Notes

- T6 raw coverage (73.4%) includes intentional Lean syntax highlighting colors
- Adjusted coverage excluding syntax colors: 84.4%
- 14 true violations identified for fixing
- Heuristic tests require screenshots + AI evaluation
