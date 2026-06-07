# Metamorphic findings

## Finding 1 — soundness bug in `inferLam` (substitution not idempotent)

**Discovered by:** MR-DEADLET (wrapping an expression in an unused `let` binding
must not change its type), Phase 1. 44 violations across the size-9 corpus, all
this one bug class.

**Confirmed against the original Haskell** (`cs4820/type-checker`), so this is a
bug in the subject checker, not the Python port:

```
\x.\y. x (x y)          standalone : (a -> b) -> (b -> b)      -- UNSOUND
let w = True in (...)               : (a -> a) -> (a -> a)      -- correct
```

Both the Python oracle and `runghc` on the original produce these.

**Why the standalone type is wrong.** In `x (x y)`, `x` is applied to its own
output, so the domain and codomain of `x` must be equal: the principal type is
`(a -> a) -> (a -> a)`. The reported `(a -> b) -> (b -> b)` is strictly more
general than is sound — it claims `a` and `b` are independent when the program
forces `a = b`.

**Root cause.** `inferLam` builds the function type as

```haskell
funTy = mkTFun (applySubstTy subst paramTy) bodyTy
```

It applies the substitution to the parameter type but returns `bodyTy` as-is, and
`applySubstTy` does not chase chains (`applySubstTy` of `TVar n` returns the bound
type without re-substituting inside it). During inference of the nested body the
substitution becomes non-idempotent — e.g. `t0 ↦ (t1 -> t2)` while `t1 ↦ t2` —
so `applySubstTy subst paramTy` yields `t1 -> t2` instead of the fully-resolved
`t2 -> t2`. The dangling `t1` survives into the result.

`inferLet` happens to mask the bug: it returns `applySubstTy subst bodyTy`,
re-applying the *whole* substitution to the body type, which resolves the
dangling variable. That is why the same expression types correctly under a dead
`let` and incorrectly on its own — and why MR-DEADLET, which routes one side
through the `let` path, is the relation that catches it. MR-LAM does *not* catch
it: both its sides go through the buggy `inferLam`, so they are wrong
consistently and the relation still appears to hold. Having multiple independent
relations is what made the bug observable.

**Suggested fix (in the subject checker).** Either:

1. make substitution composition idempotent (resolve chains so `applySubstTy`
   fully normalizes), or
2. in `inferLam`, apply the final substitution to the whole function type:
   `funTy = applySubstTy subst (mkTFun paramTy bodyTy)`.

Both make `inferLam` agree with `inferLet`.

**Also caught by MR-KPROJ.** The EMI-style K-projection relation (`K e junk` has
the same type as `e`) independently flags the same 44 expressions: the K
application re-applies the full substitution to its result, just as `inferLet`
does. Two independent relations agreeing on the same 44 cases is corroboration.

**Status in this repo.** Not fixed — the oracle is a faithful port and the bug is
the finding. It is pinned by `tests/test_metamorphic.py::test_dead_let_preserves_type_apply_twice`
(strict xfail) and documented in the generated suite
(`test_generated_metamorphic.py`, the xfail-marked cases). A fix to the subject
checker will flip those to failures and alert us.

## Finding 2 — over-acceptance: the checker accepts ill-typed programs

**Discovered by:** MR-LETLAM (if the application form `(\x.body) v` type-checks,
the let form `let x=v in body` must too, and the app-form type must be an
*instance* of the more-general let-form type). Added in the Phase-1.5 batch from
the related-work scan. 136 violations across the size-9 corpus.

**Confirmed against the original Haskell:**

```
(\x. (x True) True) (\i. i)        : a   (Python)  /  Just (TVar 0)  (Haskell)
let x = (\i. i) in (x True) True   : type error   (both)
```

**Why the application form is wrong.** `x` is bound (monomorphically) to the
identity `\i.i`, so `x : t -> t`. The body `(x True) True` applies `x` to `True`
(forcing `t = Bool`, result `Bool`) then applies *that `Bool` result* to `True`
— applying a `Bool` as a function. The program is ill-typed and must be rejected.
The checker instead accepts it with a fully general type `a`. This is worse than
Finding 1: it is **unsoundness** (accepting an ill-typed program), not merely an
over-general type.

**Relation to Finding 1.** Same defect family: `inferLam` builds the function
type from a non-idempotent substitution, so a constraint discovered while
checking the body (here, that the first application's result must itself be a
function) is left dangling and never enforced against the later binding of the
same variable. The `let` form re-applies the full substitution and correctly
rejects the program; the bare application does not. MR-LETLAM exposes the
acceptance symptom; MR-DEADLET / MR-KPROJ expose the wrong-type symptom.

**Status.** Not fixed (faithful port). Pinned by
`tests/test_metamorphic.py::test_app_form_should_reject_self_inconsistent_use`
(strict xfail) and the xfail-marked MR-LETLAM cases in the generated suite.

## Relations added from the related-work scan (Phase 1.5)

From `metamorphic-related-work.md` (full citations there). All three are sound
and now in the pipeline:

- **MR-CLASH** — type-overwriting mutation, after Chaliasos et al., "Finding
  Typing Compiler Bugs", PLDI 2022 (doi:10.1145/3519939.3523427). Grafting a
  closed term of a ground type into a slot unified to a *different* ground type
  must be rejected. **0 violations / 2,600 applications** — a pure soundness
  check the checker passes, evidence the relation has no false positives.
- **MR-KPROJ** — equivalence modulo inputs, after Le, Afshari, Su, PLDI 2014
  (doi:10.1145/2594291.2594334). Corroborates Finding 1 (44 violations).
- **MR-LETLAM** — soundness+precision testing, after Kaindlstorfer, Isychev,
  Wüstholz, Christakis, "Interrogation Testing of Program Analyzers ...", ASE
  2024 (doi:10.1145/3691620.3695034). Finding 2 (136 violations).
