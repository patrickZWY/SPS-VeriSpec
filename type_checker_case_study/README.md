# Type-checker case study: progressive, test-validated composition

This is the milestone from the top of the repo `README.md`:

> Try the type checker case study where more advanced expressions composed from
> simpler expressions expose errors. First investigate by hand what parts of an
> expression should be analyzed and extracted. Make it a policy and see if we
> can deduce a more complex test that is similar to the one that exposed the bug.

The subject is the Hindley-Milner type checker in `../cs4820/type-checker`
(Haskell). Its test suite is built almost entirely from five elementary
expression forms (`Var`, `Lam`, `App`, `If`, `Let`, plus the leaves `Lit`,
`True`, `False`) composed into combinators (I, K, B, C, W, S) and
let-polymorphism cases. The interesting bugs only surface under composition:
self-application triggers the occurs check, mismatched `if` branches fail, and a
`Lam`-bound variable used at two types fails where the *same shape* under a
`Let` succeeds.

## The idea

Rather than statically proving what composite expressions are well-typed
(conservative), we **progressively** grow expressions from the elementary forms
and let a cheap test -- the type checker itself -- tell us what actually holds.
A Datalog **policy** predicts outcomes structurally; the gap between the policy
and the validated ground truth is the feedback signal.

```
elementary forms ──grow/mutate──▶ composite expressions
                                        │
                                        ├─▶ oracle (ported Algorithm W) ─▶ ground truth
                                        │
                                        └─▶ Datalog policy (structural) ─▶ prediction
                                                                              │
                          prediction vs ground truth ◀────────────────────────┘
```

## Layout

| Path | Role |
| --- | --- |
| `oracle/syntax.py` | `Expr` AST -- port of `Syntax.hs`. The elementary forms. |
| `oracle/types.py` | Types, unification, Algorithm W -- port of `Type.hs`. The trusted oracle. |
| `outcome.py` | Classify a closed expression: principal-type shape or error class. |
| `compose.py` | Scope-aware progressive composition + mutation engine. |
| `facts.py` | Emit elementary-form facts (node/child/var_ref) for Datalog. |
| `policy/expr_policy.dl` | Souffle policy: structural outcome prediction. |
| `policy_eval.py` | Run the policy and measure it against the oracle. |
| `groundtruth.py` | Validate all composites; write the ground-truth summary. |
| `generate_flip_tests.py` | Promote discriminating mutations into a strict-oracle pytest suite. |
| `mutation_drive.py` | Mutate the checker logic; score how well the suites kill the mutants. |
| `metamorphic.py` | Phase-1 metamorphic transforms + relation checkers. |
| `metamorphic_eval.py` | Run metamorphic relations over the corpus; report violations. |
| `generate_metamorphic_tests.py` | Emit the metamorphic pytest suite (xfail the known bug). |
| `tests/` | Parity suite (vs `TypeTest.hs`) + engine tests. |
| `out/` | Generated reports and CSV catalogs. |

## How to run

```bash
# 1. Confirm the oracle matches the Haskell test suite (42 parity cases).
.venv/bin/python -m pytest type_checker_case_study/tests -q

# 2. Progressive composition: build composites, validate, summarize ground truth.
.venv/bin/python -m type_checker_case_study.groundtruth
#   -> out/ground_truth.md, out/catalog.csv, out/flips.csv

# 3. Datalog policy vs oracle (requires `souffle` on PATH).
.venv/bin/python -m type_checker_case_study.policy_eval
#   -> out/policy_report.md

# 4. Promote the discriminating mutations into strict-oracle pytest suites.
.venv/bin/python -m type_checker_case_study.generate_flip_tests
#   -> generated_tests/type_checker_case_study/test_generated_composition_boundaries.py
#   -> generated_tests/type_checker_case_study/test_generated_composition_chains.py
pytest generated_tests/type_checker_case_study

# 5. Repo-wide evaluation lane: validate the generated suite and mutation-test it.
.venv/bin/python tools/validate_generated_tests.py \
    generated_tests/type_checker_case_study --target-project .
#   -> generated_tests/type_checker_case_study/validation_report.md
.venv/bin/python -m type_checker_case_study.mutation_drive
#   -> generated_tests/type_checker_case_study/mutation_eval.md (+ .json)

# 6. Metamorphic oracles (reference-free): run relations over the corpus, emit a suite.
.venv/bin/python -m type_checker_case_study.metamorphic_eval
#   -> out/metamorphic_report.md   (currently 44 MR-DEADLET violations = a real bug)
.venv/bin/python -m type_checker_case_study.generate_metamorphic_tests
#   -> generated_tests/type_checker_case_study/test_generated_metamorphic.py
```

See [metamorphic-oracle-plan.md](metamorphic-oracle-plan.md) for the full plan
and [METAMORPHIC_FINDINGS.md](METAMORPHIC_FINDINGS.md) for the bug Phase 1 found.

Search budget is configurable: `--max-size`, `--max-rounds`, `--cap-per-round`.

## What the current run shows

With size <= 9 and 4 mutation rounds (~5,600 distinct closed expressions):

- **Ground truth** (`out/ground_truth.md`): ~47% well-typed across a rich set of
  principal-type shapes (all the combinator shapes appear), ~53% ill-typed
  across four error classes. ~3,000 *discriminating mutations* -- single growth
  steps that flip the outcome, e.g. `\x. x` (`a -> a`) mutated to `\x. (x x)`
  (occurs-check). These flips are the combinator-style bug probes.

- **Policy vs oracle** (`out/policy_report.md`): the structural policy is
  **sound for the ill-typed decision** (zero false positives) and decides ~85%
  of occurs-check cases exactly. Two findings fall out:
  1. **Lam-vs-Let is decisive.** Lambda self-application *always* fails the
     occurs check; let-bound self-application is fine under polymorphism. The
     policy only fires on the `Lam` binder, which is why it stays sound.
  2. **Error class is a whole-composition property.** Lambda self-application
     soundly predicts *failure* but not *which* failure: when the same variable
     is also used as an `if` condition, that constraint fires first and the
     checker reports `application-mismatch`/`non-bool-condition` instead of
     `occurs-check`. These reclassifications are catalogued, not hidden.

The **residual** -- ~2,100 ill-typed expressions the structural policy cannot
claim (application-mismatch, non-bool-condition, heterogeneous-if, and
context-reclassified occurs-check) -- is the quantified argument for progressive,
test-based validation: their outcome depends on unification, let-generalization,
or branch agreement, not on syntax alone.

## Generated suite

`generate_flip_tests.py` now emits two generated suites, mirroring the repo's
`generate_pytest_from_properties` lane while keeping a strict oracle:

- `generated_tests/type_checker_case_study/test_generated_composition_boundaries.py`
  keeps the one-step discriminating mutations. Each case pins a parent
  expression, the mutated child, and both validated outcomes with **strict
  equality** on the normalized outcome label.
- `generated_tests/type_checker_case_study/test_generated_composition_chains.py`
  keeps deeper four-expression paths `expr0 -> expr1 -> expr2 -> expr3`, so the
  suite can assert "do this, then one more time, then again" progressions
  instead of only isolated flips.

The default run currently emits up to 25 boundary cases per flip kind (75
total) plus up to 5 chain cases per chain kind (20 total with the current
search budget).

## Evaluation lane

The suite participates in the repo-wide evaluation lane:

- **Validation.** `tools/validate_generated_tests.py` (unmodified -- it is
  project-agnostic) runs the suite with the repo root on `PYTHONPATH` and writes
  `validation_report.md`.
- **Mutation.** `mutation_drive.py` reuses the report machinery from
  `tools/mutation_eval.py` but supplies its own operators: deliberate breakages
  of the checker logic (disable the occurs check, skip branch/condition/
  application unification, corrupt the lambda type). It scores the handwritten
  parity suite, the generated boundary suite, and their combination. In the
  current run the boundary suite **kills all five mutants on its own**, evidence
  that the strict-equality oracle is meaningful and not vacuous.

## Metamorphic oracles (Phase 1)

The label-based suites above pin behavior the oracle itself defined, so they
cannot catch a bug in the oracle. Metamorphic relations check a property
*between* a source expression and a transform of it, with no recorded answer, so
a violation indicts the checker even though the checker produced the corpus.

Phase 1 relations: MR-LIT (literal interchange), MR-ALPHA (bound-variable
renaming), MR-DEADLET (unused `let` wrap; an EMI-style dead-code relation after
Le, Afshari, and Su, PLDI 2014, doi:10.1145/2594291.2594334), MR-LAM (lambda
wrap → `fresh -> T`), MR-ERRPROP (a closed ill-typed subterm keeps any
enclosing term ill-typed).

Phase 1.5 added three relations from a recent-literature scan
([metamorphic-related-work.md](metamorphic-related-work.md)):

- **MR-CLASH** (Hephaestus type-overwriting; Chaliasos et al., PLDI 2022,
  doi:10.1145/3519939.3523427): a closed term of one ground type grafted into a
  slot pinned to a different ground type must be rejected. Sound, zero
  violations — validates the rejection machinery.
- **MR-KPROJ** (EMI dead context; Le, Afshari, and Su, PLDI 2014,
  doi:10.1145/2594291.2594334): `K e junk` must have the same type as `e`.
- **MR-LETLAM** (Interrogation-Testing precision; Kaindlstorfer, Isychev,
  Wuestholz, and Christakis, ASE 2024, doi:10.1145/3691620.3695034): app-form
  well-typed ⟹ let-form well-typed and the app-form type is an instance of the
  let-form type.

Over the size-9 corpus (~67k applications) three relations found **real,
Haskell-confirmed bugs**: MR-DEADLET and MR-KPROJ the wrong-type substitution bug
(Finding 1), and **MR-LETLAM a new over-acceptance bug** where the checker accepts
the ill-typed `(\x. (x True) True) (\i. i)` (Finding 2). MR-CLASH stays at zero
violations. See [METAMORPHIC_FINDINGS.md](METAMORPHIC_FINDINGS.md).

This is the README's original goal realized: composing simpler expressions
exposed type-checker bugs the 42 hand-written tests missed, found reference-free.

## Next steps

- Metamorphic Phase 2/3: ground-substitution and eta (with side conditions),
  then the `is_instance_of` subsumption check + MR-LETLAM (the `Lam`-vs-`Let`
  generality relation). Wire the metamorphic suite into `mutation_drive`.
- Richer policy predictors (non-bool condition where the condition is a literal
  `Lam`; heterogeneous-if where both branches have incompatible ground shapes)
  and re-measure soundness/coverage.
- Predict *principal-type shapes* for well-typed composites, not just error
  classes, and measure exact-shape agreement.
- Add equivalent/edge mutants (e.g. reorder substitution composition) to probe
  whether the boundary suite can distinguish behavior-preserving changes.
