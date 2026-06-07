# Plan: metamorphic oracles for the type-checker case study

> **Status.** Phase 1 shipped (MR-LIT/ALPHA/DEADLET/LAM/ERRPROP). A Phase-1.5
> batch from the related-work scan (`metamorphic-related-work.md`) added
> MR-CLASH, MR-KPROJ, and MR-LETLAM -- all sound and in the pipeline. MR-LETLAM
> realizes the precision idea below (it uses the `is_instance_of` check) and
> found Finding 2. Remaining Phase 2/3 items: ground-substitution and eta
> preserve-relations, and wiring the metamorphic suite into `mutation_drive`.

## Why

The generated boundary suite (`test_generated_composition_boundaries.py`) asserts
*exact outcome labels that the oracle itself produced*. That makes it a strong
**characterization** suite -- it pins current behavior and kills logic mutants
(5/5) -- but it is **circular**: it can never catch a bug in the oracle, because
the oracle defined the expected answers. Every "ground truth" we have is only as
trustworthy as the port.

A **metamorphic relation (MR)** is a property that must hold between the outputs
of related inputs, independent of what the "correct" output for any single input
is. Checking an MR needs no reference answer, so:

1. **It breaks the circularity.** An MR violation indicts the checker even though
   the checker generated the corpus -- exactly the "expose the bug I had" goal in
   the repo README.
2. **It is a sound policy, by construction.** Unlike the structural Datalog
   policy (sound only for the ill-typed decision, blind to the well-typed side),
   MRs validate the ~2,645 well-typed composites *relationally* without a second
   implementation.
3. **It composes with what exists.** Source expressions come from `compose.grow`;
   outcomes from `outcome.classify`; test emission mirrors
   `generate_flip_tests.py`; mutant scoring mirrors `mutation_drive.py`.

Differential testing against the original Haskell checker is the complementary
reference-*ful* option, but it needs GHC in the loop. Metamorphic testing is
lighter and tests a single implementation, so it is the first target; differential
is noted as a later cross-check.

## The metamorphic relations

Each MR is `(transform T, relation R)`: for a source expression `e`,
`R(classify(e), classify(T(e)))` must hold. All type comparisons are on the
**normalized** principal type (`normalize_ty`), and all generated names are
**fresh** (not occurring anywhere in `e`) to avoid capture. Graded by
soundness-confidence and implementation cost.

### Tier 1 -- equality / implication relations (cheap, unconditionally sound)

| ID | Transform `T(e)` | Relation `R` | Notes |
| --- | --- | --- | --- |
| MR-DET | identity (run twice) | exact equal | catches nondeterminism; trivial |
| MR-LIT | replace any `Lit` with another `Lit`; swap `ETrue`/`EFalse` | exact equal | special case of ground substitution; trivially sound |
| MR-ALPHA | consistently rename one bound variable to a fresh name (respecting shadowing) | exact equal | α-equivalence; **risk: capture** -- rename target must be globally fresh |
| MR-DEADLET | wrap as `Let(z_fresh, v, e)` for a closed well-typed `v`, `z` unused in `e` | exact equal | unused binding does not change the type |
| MR-LAM | wrap as `Lam(z_fresh, e)` | `cod(R) == classify(e)` and `dom` is a free var | result must be `fresh -> T` |
| MR-ERRPROP | for a **closed ill-typed** `e`, embed into any closed context slot that types its subterm: `Lam(z,e)`, `App(e,·)`, `App(·,e)`, `If(e,·,·)`/`If(·,e,·)`/`If(·,·,e)`, `Let(z,e,·)` | error ⟹ error | the milestone's "compose to expose errors", made sound by requiring `e` closed |

MR-ERRPROP is the sound, reference-free form of the structural Datalog policy's
key insight (`Lam`-self-application always fails), generalized to *any* closed
ill-typed subterm. It is the highest-value Tier-1 relation.

### Tier 2 -- ground substitution and eta (sound under a side condition)

| ID | Transform `T(e)` | Relation `R` | Side condition |
| --- | --- | --- | --- |
| MR-GSUB | replace a closed subterm `s` of **ground** type (no `TVar`) with another closed term `s'` of the *same* ground type | exact equal | both closed; identical normalized ground type |
| MR-CONST | `App(App(\a.\b.a, e), junk)` for closed well-typed `junk` | exact equal | `e` well-typed |
| MR-ETA | `Lam(x_fresh, App(e, Var(x_fresh)))` | exact equal | `e` closed with an **arrow** principal type |

The ground restriction on MR-GSUB matters: two closed terms of the *same
polymorphic* type can still instantiate differently in context, so equality is
only guaranteed when the shared type has no variables.

### Tier 3 -- generality / subsumption (the crown jewel)

| ID | Transform `T(e)` | Relation `R` |
| --- | --- | --- |
| MR-LETLAM | rewrite an application redex `App(Lam(x, body), v)` into `Let(x, v, body)` | `classify(App(...))` is an **instance of** `classify(Let(...))`, and error ⟹ error |

This formalizes the exact `Lam`-vs-`Let` distinction that produced the policy
finding: `let` generalizes the binding, so the let-form's principal type is more
general and the application-form's type is an instance of it. It requires an
`is_instance(general, specific)` check (one-directional matching / subsumption),
which is the only new piece of inference machinery in the whole plan.

## Architecture

```
compose.grow ──▶ source expressions
                      │
            metamorphic.py: T(e) transforms + R relation checkers
                      │
        ┌─────────────┴──────────────┐
        ▼                            ▼
generate_metamorphic_tests.py   metamorphic_eval (run MRs over the corpus)
        │                            │
 pytest suite                violations ─▶ quarantine (review records)
```

New modules (mirroring existing names so the lane stays uniform):

- `metamorphic.py` -- pure functions: the transforms (`alpha_rename`,
  `wrap_dead_let`, `wrap_lambda`, `swap_ground_subterm`, `eta_expand`,
  `redex_to_let`, ...) and the relation checkers (`equal_type`,
  `error_implies_error`, `is_instance_of`). Reuses `compose.positions` /
  `compose.replace_at` for site selection and `outcome.classify` for outcomes.
- `generate_metamorphic_tests.py` -- emit a parametrized pytest suite to
  `generated_tests/type_checker_case_study/test_generated_metamorphic.py`. Each
  case embeds `(source, transform_name, relation, expected_detail)` and the test
  applies the transform and asserts the relation. Deterministic sampling per MR,
  like `select_flips`.
- `metamorphic_eval.py` -- run every applicable MR over the `grow` corpus, count
  applications and violations per MR, and write `out/metamorphic_report.md`.
  Reuse `mutation_drive`'s temp-copy harness to also score MR mutant-kills.

## Validation strategy

- **On the faithful oracle, expect zero violations.** Zero is itself meaningful:
  it is an independent cross-check that the Python port and the relations agree,
  over thousands of expressions the relations were not tuned to.
- **Any violation** is either a checker bug or an MR bug -- route it to a
  quarantine manifest as a review record (reuse the repo's
  `oracle_candidates`/`validate_generated_tests` quarantine convention; failures
  are review records, not trusted-suite failures).
- **Mutation evidence.** Add the MR suite to `mutation_drive`. The key metric is
  *mutants killed by the MR suite that the label-based boundary suite needs the
  oracle to define*. Because MR kills are reference-free, they are stronger
  evidence than label-equality kills. Expect MR-ERRPROP and MR-LETLAM to kill the
  occurs-check / branch-unify / let-generalization mutants.

## Risks and subtleties

- **Capture.** Every introduced name (`z_fresh`, eta's `x_fresh`, α-rename
  target) must be globally fresh in `e`. Use a name not in `free_vars(e)` and not
  bound anywhere in `e`.
- **Normalization.** Compare types only after `normalize_ty`; raw `TVar` ids
  differ across runs.
- **`let` ≥ `lambda` is inequality, not equality.** MR-LETLAM must use
  `is_instance_of`, never `equal_type`. Getting this wrong would manufacture
  false violations.
- **Polymorphism breaks naive substitutivity.** MR-GSUB is sound only for ground
  types; do not extend it to type-variable types without an instance check.
- **Eta only preserves type for arrow-typed `e`.** For a type-variable result,
  eta-expansion *specializes* the type. Gate MR-ETA on an arrow principal type.
- **Error propagation needs closed subterms.** Open subterms can become
  well-typed once a context binds their free variables, so MR-ERRPROP applies
  only to closed ill-typed seeds.

## Phasing

1. **Phase 1 (sound, no new inference):** MR-DET, MR-LIT, MR-ALPHA, MR-DEADLET,
   MR-LAM, MR-ERRPROP. Ships `metamorphic.py` + `generate_metamorphic_tests.py` +
   the report. Success = 0 violations on the corpus, MR-ERRPROP kills the
   occurs-check/branch mutants reference-free.
2. **Phase 2:** MR-GSUB, MR-CONST, MR-ETA (with side conditions).
3. **Phase 3:** `is_instance_of` subsumption check + MR-LETLAM -- the
   generality relation that formalizes the `Lam`-vs-`Let` finding.
4. **Phase 4:** quarantine wiring + `mutation_drive` integration + a differential
   cross-check against the Haskell checker (optional, needs GHC).

## Success metrics

- MR count and total `(source × MR)` applications exercised.
- Violations on the current oracle (target: 0; any non-zero is a finding).
- Mutants killed by the MR suite, especially any killed reference-free that the
  label suite can only catch via oracle-defined labels.
- Fraction of the well-typed corpus covered by at least one equality MR (the part
  the structural Datalog policy could not touch).
