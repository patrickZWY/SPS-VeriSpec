# Metamorphic oracle report (Phase 1)

Each source expression from the composition corpus is transformed by every applicable metamorphic relation, and the relation is checked against the oracle. Violations are documented findings (real checker bugs); see METAMORPHIC_FINDINGS.md. MR-CLASH is a pure soundness check and is expected to stay at zero.

## Coverage

- Source expressions: 5617
- Total MR applications: 67351
- Violations: 224

### Applications per relation

- `MR-ALPHA`: 15529
- `MR-CLASH`: 2600
- `MR-DEADLET`: 5617
- `MR-ERRPROP`: 20804
- `MR-KPROJ`: 5617
- `MR-LAM`: 5617
- `MR-LETLAM`: 1013
- `MR-LIT`: 10554

## Violations

Each row is a checker bug or an MR bug; treat as a review record, not a trusted-suite failure.

- `MR-LETLAM`: 136
- `MR-DEADLET`: 44
- `MR-KPROJ`: 44

- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. ((x True) True)) (\i. i))` : `a`
  - transformed `(let x = (\i. i) in ((x True) True))` : `error:application-mismatch`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. ((x True) 0)) (\i. i))` : `a`
  - transformed `(let x = (\i. i) in ((x True) 0))` : `error:application-mismatch`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. ((\x. x) (x True))) (\i. i))` : `a`
  - transformed `(let x = (\i. i) in ((\x. x) (x True)))` : `Bool`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. ((x True) False)) (\i. i))` : `a`
  - transformed `(let x = (\i. i) in ((x True) False))` : `error:application-mismatch`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. ((\y. (x y)) True)) (\i. i))` : `a`
  - transformed `(let x = (\i. i) in ((\y. (x y)) True))` : `Bool`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. ((\y. (x True)) True)) (\i. i))` : `a`
  - transformed `(let x = (\i. i) in ((\y. (x True)) True))` : `Bool`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. ((\y. (x True)) x)) (\i. i))` : `a`
  - transformed `(let x = (\i. i) in ((\y. (x True)) x))` : `Bool`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. ((\y. (y True)) x)) (\i. i))` : `a`
  - transformed `(let x = (\i. i) in ((\y. (y True)) x))` : `Bool`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. ((\y. y) (x True))) (\i. i))` : `a`
  - transformed `(let x = (\i. i) in ((\y. y) (x True)))` : `Bool`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. (\y. ((x y) True))) (\i. i))` : `(a -> b)`
  - transformed `(let x = (\i. i) in (\y. ((x y) True)))` : `((Bool -> a) -> a)`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. (\y. ((x True) True))) (\i. i))` : `(a -> b)`
  - transformed `(let x = (\i. i) in (\y. ((x True) True)))` : `error:application-mismatch`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (\y. (x (x y))))` : `((a -> b) -> (b -> b))`
  - transformed `(let w0 = True in (\x. (\y. (x (x y)))))` : `((a -> a) -> (a -> a))`
- **MR-KPROJ** (`equal_outcome`)
  - source `(\x. (\y. (x (x y))))` : `((a -> b) -> (b -> b))`
  - transformed `(((\a. (\b. a)) (\x. (\y. (x (x y))))) True)` : `((a -> a) -> (a -> a))`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. (\y. (x (x y)))) (\i. i))` : `(a -> b)`
  - transformed `(let x = (\i. i) in (\y. (x (x y))))` : `(a -> a)`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. (\y. ((x y) y))) (\i. i))` : `(a -> b)`
  - transformed `(let x = (\i. i) in (\y. ((x y) y)))` : `error:occurs-check`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. (\y. ((x True) y))) (\i. i))` : `(a -> b)`
  - transformed `(let x = (\i. i) in (\y. ((x True) y)))` : `error:application-mismatch`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. (\y. (y (x y)))) (\i. i))` : `((a -> b) -> b)`
  - transformed `(let x = (\i. i) in (\y. (y (x y))))` : `error:occurs-check`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (\y. (y (y x))))` : `(a -> ((b -> a) -> a))`
  - transformed `(let w0 = True in (\x. (\y. (y (y x)))))` : `(a -> ((a -> a) -> a))`
- **MR-KPROJ** (`equal_outcome`)
  - source `(\x. (\y. (y (y x))))` : `(a -> ((b -> a) -> a))`
  - transformed `(((\a. (\b. a)) (\x. (\y. (y (y x))))) True)` : `(a -> ((a -> a) -> a))`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. (\y. (y (y x)))) (\i. i))` : `((a -> (b -> b)) -> a)`
  - transformed `(let x = (\i. i) in (\y. (y (y x))))` : `(((a -> a) -> (a -> a)) -> (a -> a))`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. (if True then (x True) else 0)) (\i. i))` : `Int`
  - transformed `(let x = (\i. i) in (if True then (x True) else 0))` : `error:heterogeneous-if`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. (if True then 0 else (x True))) (\i. i))` : `Int`
  - transformed `(let x = (\i. i) in (if True then 0 else (x True)))` : `error:heterogeneous-if`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. ((x True) (\y. True))) (\i. i))` : `a`
  - transformed `(let x = (\i. i) in ((x True) (\y. True)))` : `error:application-mismatch`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. ((x True) (\y. y))) (\i. i))` : `a`
  - transformed `(let x = (\i. i) in ((x True) (\y. y)))` : `error:application-mismatch`
- **MR-LETLAM** (`app_instance_of_let`)
  - source `((\x. ((x True) (\x. x))) (\i. i))` : `a`
  - transformed `(let x = (\i. i) in ((x True) (\x. x)))` : `error:application-mismatch`
