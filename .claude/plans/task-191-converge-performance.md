# Task #191: Converge Performance Investigation

## Objective
Identify optimization opportunities to cut converge iteration time by 50%+ and remove user-blocking waits while preserving archival integrity, validation gates, and UX quality.

## Scope
**Investigation focus:**
- Baseline timing quantification across all converge operations
- Async/background operation opportunities (user-blocking waits)
- Redundant work detection (unnecessary rebuilds, revalidations)
- Quick wins vs longer-term improvements

**Data sources:**
- Archive entries (timing structure, phase durations)
- Build logs (Lake output, artifact generation, screenshot capture)
- Session JSONL (agent decision patterns, API latency, context usage)
- Validator execution logs (pytest, T1-T8 timings)
- Git operation timings (porcelain checks, commits, pushes, iCloud sync)

**Deliverables:**
1. Timing baseline metrics (current iteration time breakdown)
2. Top 3-5 optimization opportunities ranked by impact vs effort
3. Concrete proposals ready to spawn as follow-up issues
4. Prioritization framework for implementation order

## Execution Plan

### Wave 1: Baseline Timing Analysis (4 parallel agents)

**Agent A: Archive Timing Extraction**
- Query recent archive entries (last 50-100) for converge skill sessions
- Extract timing breakdowns from `archive_timing` fields
- Compute percentiles (p50, p90, p95) for each operation category
- Output: `archive_timing_analysis.json`

**Agent B: Build Timing Analysis**
- Analyze build logs from `dev/storage/{project}/build_logs/`
- Extract Lake build times, artifact generation, screenshot capture
- Identify projects with slowest builds
- Detect incremental build effectiveness (cache hits vs full rebuilds)
- Output: `build_timing_analysis.json`

**Agent C: Session JSONL Analysis**
- Parse session JSONL files for converge-related sessions
- Extract API latency patterns (time between tool calls)
- Analyze agent decision patterns (thinking time, tool call sequences)
- Quantify context usage (cache read ratios, prompt tokens)
- Output: `session_timing_analysis.json`

**Agent D: Validator + Git Timing Analysis**
- Parse validator logs for T1-T8 execution times
- Extract pytest timing data (test discovery, execution, teardown)
- Analyze git operation timings from archive entries (porcelain checks, commits, pushes)
- Quantify iCloud sync overhead
- Output: `validator_git_timing_analysis.json`

**Validator:** All 4 agents complete successfully with JSON output files

---

### Wave 2: Opportunity Identification (1 agent)

**Agent: Synthesis & Opportunity Analysis**
- Load all 4 JSON outputs from Wave 1
- Compute overall baseline: total iteration time, phase breakdown
- Identify async opportunities:
  - Operations that block user but could run in background
  - Operations that could run in parallel
  - Operations that could be deferred
- Find redundant work:
  - Unnecessary rebuilds (unchanged source)
  - Redundant validations (same inputs)
  - Repeated analysis (cached results available)
- Calculate potential impact for each opportunity (time saved)
- Output: `optimization_opportunities.md` with ranked list

**Validator:** Markdown file contains baseline metrics + ranked opportunities

---

### Wave 3: Prioritization & Proposals (1 agent)

**Agent: Concrete Proposals**
- Review `optimization_opportunities.md`
- Select top 3-5 opportunities balancing quick wins vs long-term impact
- For each opportunity, draft:
  - Concrete implementation proposal
  - Estimated impact (time saved, UX improvement)
  - Implementation complexity (effort estimate)
  - Dependencies and risks
  - Ready-to-spawn GitHub issue content
- Create prioritization framework (decision matrix)
- Output: `optimization_proposals.md` + draft issue content

**Validator:** Proposals document contains actionable next steps

---

## Gates

```yaml
gates:
  tests: none               # Investigation task, no test requirements
  deliverables:
    - baseline_metrics: present
    - ranked_opportunities: 3-5 items minimum
    - concrete_proposals: actionable and specific
    - prioritization_framework: defined
```

## Success Criteria
- Baseline metrics quantify current state (iteration time breakdown)
- Top 3-5 opportunities identified with estimated impact
- Concrete proposals ready to spawn as follow-up issues
- Prioritization framework enables implementation decisions
- Quick wins highlighted (async operations, redundant work elimination)

## Constraints
- Preserve archival integrity (completeness, fidelity)
- Validation gates cannot be weakened
- User experience quality must not degrade
- Creative solutions encouraged within these boundaries

## Affected Components
- `/converge` skill (primary)
- `/task` skill (gate validation, phase transitions)
- `/introspect` skill (async candidate)
- `/update-and-archive` skill (async candidate)
- Archive upload system (`dev/scripts/sbs/archive/upload.py`)
- Build pipeline (`dev/scripts/build.py`)
- Validator framework (`dev/scripts/sbs/validators/`)

## Notes
- First optimization effort focused on clock time
- Many quick wins likely available (low-hanging fruit)
- User example: running `/introspect N` in background during work
- Pain point: accumulation of many waits, not single bottleneck
- Target: 50%+ iteration time reduction + remove user-blocking waits
