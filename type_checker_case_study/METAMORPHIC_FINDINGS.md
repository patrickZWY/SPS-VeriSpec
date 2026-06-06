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

**Status in this repo.** Not fixed — the oracle is a faithful port and the bug is
the finding. It is pinned by `tests/test_metamorphic.py::test_dead_let_preserves_type_apply_twice`
(strict xfail) and documented in the generated suite
(`test_generated_metamorphic.py`, the xfail-marked cases). A fix to the subject
checker will flip those to failures and alert us.
