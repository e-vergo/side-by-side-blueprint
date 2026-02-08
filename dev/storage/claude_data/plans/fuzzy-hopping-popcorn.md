# Plan: Complete Remaining Proofs in Lcm.lean

## Summary
Clear 3 remaining `sorry` statements in `/Users/eric/GitHub/PrimeNumberTheoremAnd/PrimeNumberTheoremAnd/Lcm.lean` using parallel agent orchestration.

## Remaining Sorry Statements

| # | Line | Theorem | Type | Independent? |
|---|------|---------|------|--------------|
| 1 | 648-650 | `Criterion.σnorm_M_ge_σnorm_L'_mul` | Lower bound on σnorm(M) | YES |
| 2 | 1081-1085 | `pq_ratio_ge` | Ratio bound ∏p_i/∏q_i | YES |
| 3 | 1336 | `Criterion.mk'` field `h_crit` | Main criterion inequality | NO (depends on #2) |

## Execution Strategy

### Phase 1: Parallel Independent Proofs
Launch 2 agents in parallel:

**Agent A: `σnorm_M_ge_σnorm_L'_mul` (lines 648-650)**
- Goal: `σnorm c.M ≥ σnorm c.L' * (∏ i, (1 + 1 / (c.p i * (c.p i + 1)))) * (1 + 3 / (8 * c.n))`
- Approach per blueprint:
  1. Use multiplicativity: σ(M)/M = σ(L')/L' * ∏_p [contribution from prime p]
  2. For p = p_i: contribution is (1 + p_i^(-1) + p_i^(-2))/(1 + p_i^(-1)) = 1 + 1/(p_i(p_i+1))
  3. For p = 2: contribution involves geometric series, yields ≥ 1 + 3/(8n)
  4. Other primes contribute ≥ 1
- Key lemmas to use: `σnorm_ln_eq`, properties of `c.M` definition, divisor sum multiplicativity

**Agent B: `pq_ratio_ge` (lines 1081-1085)**
- Goal: `1 - 4*(∏p_i)/(∏q_i) ≥ 1 - 4*(1 + 1/log³√n)^12 / n^(3/2)`
- Approach per blueprint:
  1. Use bounds: p_i ≤ √n*(1+ε)^i where ε = 1/log³√n
  2. Use bounds: q_i ≥ n*(1+ε)^(-(3-i))
  3. Multiply: ∏p_i ≤ n^(3/2)*(1+ε)^6
  4. Multiply: ∏q_i ≥ n³*(1+ε)^(-6)
  5. Combine: ratio ≤ (1+ε)^12/n^(3/2)
- Key lemmas: `exists_p_primes`, `exists_q_primes`, their `.choose_spec` properties

### Phase 2: Dependent Proof (after Phase 1)
**Agent C: `h_crit` in `Criterion.mk'` (line 1336)**
- Goal: `∏ i, (1 + 1/q_i) ≤ (∏ i, (1 + 1/(p_i(p_i+1)))) * (1 + 3/(8n)) * (1 - 4*∏p_i/∏q_i)`
- Approach per blueprint (prop:ineq-holds-large-n):
  1. Use `prod_q_ge` (line 937): bounds ∏(1+1/q_i)
  2. Use `prod_p_ge` (line 1014): bounds ∏(1+1/(p_i(p_i+1)))
  3. Use `pq_ratio_ge` (completed in Phase 1): bounds the ratio term
  4. Use `prod_epsilon_le` and `prod_epsilon_ge` (lines 1212, 1247): polynomial bounds
  5. Use `final_comparison` (line 1278): verifies numerical inequality
  6. Set ε = 1/n and combine all bounds

## File Locations
- Main file: `/Users/eric/GitHub/PrimeNumberTheoremAnd/PrimeNumberTheoremAnd/Lcm.lean`
- Supporting helper lemmas already proven:
  - `prod_q_ge` (line 913-979)
  - `prod_p_ge` (line 981-1048)
  - `inv_cube_log_sqrt_le` (line 1091-1117)
  - `inv_n_pow_3_div_2_le` (line 1119-1145)
  - `prod_epsilon_le` (line 1182-1215)
  - `prod_epsilon_ge` (line 1217-1251)
  - `final_comparison` (line 1253-1280)

## Verification
After completing all proofs:
1. Run `lean_diagnostic_messages` on entire file to confirm no errors
2. Check that the main theorem `L_not_HA_of_ge` (line 1342-1352) compiles without sorry
3. Verify no remaining sorry statements in the file

## Agent Instructions Template

Each agent should:
1. Read the relevant section and all imported files first
2. Use `lean_goal` frequently to check proof state
3. Search for relevant Mathlib lemmas using `lean_leansearch`, `lean_loogle`, `lean_local_search`
4. Use `lean_multi_attempt` to test multiple tactic approaches
5. Never replace working partial proofs with sorry
6. Use `norm_cast`, `field_simp`, `ring`, `nlinarith`, `gcongr` for arithmetic goals
7. Check `lean_diagnostic_messages` after each significant change
