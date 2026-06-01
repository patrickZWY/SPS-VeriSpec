# Datalog policy vs. oracle ground truth

The structural policy predicts only what follows soundly from the elementary forms and their binding. Everything else is left to the oracle. This report quantifies the gap -- the residual that justifies progressive, test-based validation.

## Soundness of the ill-typed decision

- Expressions the policy decided: 828 / 5617
- False positives (policy said ill-typed, oracle says well-typed): 0
- Zero false positives: every expression the policy flags is genuinely ill-typed. The structural policy is sound for the well-typed/ill-typed decision on this set.

## Error-class precision under composition

- Reclassified (ill-typed both ways, but a different error fires first): 82
  Finding: lambda self-application is a sound predictor of *failure*, but not of *which* failure. When the same variable is also constrained elsewhere -- e.g. used as an `if` condition -- that constraint fires first and the checker reports `application-mismatch`/`non-bool-condition` instead of `occurs-check`. The error class is a property of the whole composition, not of the self-application alone.

  - `(\x. (if x then (x x) else False))` predicted `occurs-check`, oracle `error:application-mismatch`
  - `(\x. (if x then True else (x x)))` predicted `occurs-check`, oracle `error:application-mismatch`
  - `(\x. ((x True) (x x)))` predicted `occurs-check`, oracle `error:application-mismatch`
  - `(\x. (\x. (if x then (x x) else False)))` predicted `occurs-check`, oracle `error:application-mismatch`
  - `(\x. (\x. (if x then True else (x x))))` predicted `occurs-check`, oracle `error:application-mismatch`
  - `(\x. (\y. (if x then (x x) else False)))` predicted `occurs-check`, oracle `error:application-mismatch`
  - `(\x. (\y. (if x then True else (x x))))` predicted `occurs-check`, oracle `error:application-mismatch`
  - `(\x. (\y. (if y then (y y) else False)))` predicted `occurs-check`, oracle `error:application-mismatch`
  - `(\x. (\y. (if y then True else (y y))))` predicted `occurs-check`, oracle `error:application-mismatch`
  - `(\x. (if (\y. True) then (x x) else False))` predicted `occurs-check`, oracle `error:non-bool-condition`
  - `(\x. (if (\y. True) then True else (x x)))` predicted `occurs-check`, oracle `error:non-bool-condition`
  - `(\x. (if (\y. y) then (x x) else False))` predicted `occurs-check`, oracle `error:non-bool-condition`

## Coverage of ill-typed expressions

- Oracle ill-typed total: 2972
- `application-mismatch`: policy decided exactly 0 / 910 (0.0%)
- `occurs-check`: policy decided exactly 746 / 877 (85.1%)
- `non-bool-condition`: policy decided exactly 0 / 707 (0.0%)
- `heterogeneous-if`: policy decided exactly 0 / 478 (0.0%)

## Residual (only the oracle/tests can decide)

Ill-typed expressions the structural policy does not claim. These are the cases where composition outcome genuinely depends on unification, let-generalization, or branch agreement -- not on syntax alone.

- `application-mismatch`: 868
- `non-bool-condition`: 667
- `heterogeneous-if`: 478
- `occurs-check`: 131
