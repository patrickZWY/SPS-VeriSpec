# Metamorphic oracle report (Phase 1)

Each source expression from the composition corpus is transformed by every applicable metamorphic relation, and the relation is checked against the oracle. Zero violations is the expected, meaningful result: an independent cross-check that the relations and the port agree.

## Coverage

- Source expressions: 5617
- Total MR applications: 58121
- Violations: 44

### Applications per relation

- `MR-ALPHA`: 15529
- `MR-DEADLET`: 5617
- `MR-ERRPROP`: 20804
- `MR-LAM`: 5617
- `MR-LIT`: 10554

## Violations

Each row is a checker bug or an MR bug; treat as a review record, not a trusted-suite failure.

- `MR-DEADLET`: 44

- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (\y. (x (x y))))` : `((a -> b) -> (b -> b))`
  - transformed `(let w0 = True in (\x. (\y. (x (x y)))))` : `((a -> a) -> (a -> a))`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (\y. (y (y x))))` : `(a -> ((b -> a) -> a))`
  - transformed `(let w0 = True in (\x. (\y. (y (y x)))))` : `(a -> ((a -> a) -> a))`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (((x True) True) True))` : `((Bool -> (Bool -> a)) -> b)`
  - transformed `(let w0 = True in (\x. (((x True) True) True)))` : `((Bool -> (Bool -> (Bool -> a))) -> a)`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (((x True) True) x))` : `((Bool -> (Bool -> a)) -> b)`
  - transformed `(let w0 = True in (\x. (((x True) True) x)))` : `((Bool -> (Bool -> ((Bool -> (Bool -> a)) -> b))) -> b)`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (x ((x True) True)))` : `((Bool -> (Bool -> a)) -> b)`
  - transformed `(let w0 = True in (\x. (x ((x True) True))))` : `((Bool -> (Bool -> Bool)) -> a)`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (if ((x True) True) then True else False))` : `((Bool -> (Bool -> a)) -> Bool)`
  - transformed `(let w0 = True in (\x. (if ((x True) True) then True else False)))` : `((Bool -> (Bool -> Bool)) -> Bool)`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (((x True) True) 0))` : `((Bool -> (Bool -> a)) -> b)`
  - transformed `(let w0 = True in (\x. (((x True) True) 0)))` : `((Bool -> (Bool -> (Int -> a))) -> a)`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (((x True) True) False))` : `((Bool -> (Bool -> a)) -> b)`
  - transformed `(let w0 = True in (\x. (((x True) True) False)))` : `((Bool -> (Bool -> (Bool -> a))) -> a)`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (\x. (\y. (x (x y)))))` : `(a -> ((b -> c) -> (c -> c)))`
  - transformed `(let w0 = True in (\x. (\x. (\y. (x (x y))))))` : `(a -> ((b -> b) -> (b -> b)))`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (\x. (\y. (y (y x)))))` : `(a -> (b -> ((c -> b) -> b)))`
  - transformed `(let w0 = True in (\x. (\x. (\y. (y (y x))))))` : `(a -> (b -> ((b -> b) -> b)))`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (\y. (\z. (x (x y)))))` : `((a -> b) -> (b -> (c -> b)))`
  - transformed `(let w0 = True in (\x. (\y. (\z. (x (x y))))))` : `((a -> a) -> (a -> (b -> a)))`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (\y. (\z. (x (x z)))))` : `((a -> b) -> (c -> (b -> b)))`
  - transformed `(let w0 = True in (\x. (\y. (\z. (x (x z))))))` : `((a -> a) -> (b -> (a -> a)))`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (\y. (\z. (y (y x)))))` : `(a -> ((b -> a) -> (c -> a)))`
  - transformed `(let w0 = True in (\x. (\y. (\z. (y (y x))))))` : `(a -> ((a -> a) -> (b -> a)))`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (\y. (\z. (y (y z)))))` : `(a -> ((b -> c) -> (c -> c)))`
  - transformed `(let w0 = True in (\x. (\y. (\z. (y (y z))))))` : `(a -> ((b -> b) -> (b -> b)))`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (\y. (\z. (z (z x)))))` : `(a -> (b -> ((c -> a) -> a)))`
  - transformed `(let w0 = True in (\x. (\y. (\z. (z (z x))))))` : `(a -> (b -> ((a -> a) -> a)))`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (\y. (\z. (z (z y)))))` : `(a -> (b -> ((c -> b) -> b)))`
  - transformed `(let w0 = True in (\x. (\y. (\z. (z (z y))))))` : `(a -> (b -> ((b -> b) -> b)))`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (\y. (x (\z. (x y)))))` : `(((a -> b) -> c) -> ((a -> c) -> c))`
  - transformed `(let w0 = True in (\x. (\y. (x (\z. (x y))))))` : `(((a -> b) -> b) -> ((a -> b) -> b))`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (\y. (y (\z. (y x)))))` : `((a -> b) -> (((a -> c) -> b) -> b))`
  - transformed `(let w0 = True in (\x. (\y. (y (\z. (y x))))))` : `((a -> b) -> (((a -> b) -> b) -> b))`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (((\y. (x y)) True) True))` : `((Bool -> a) -> b)`
  - transformed `(let w0 = True in (\x. (((\y. (x y)) True) True)))` : `((Bool -> (Bool -> a)) -> a)`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (((\y. (x True)) True) True))` : `((Bool -> a) -> b)`
  - transformed `(let w0 = True in (\x. (((\y. (x True)) True) True)))` : `((Bool -> (Bool -> a)) -> a)`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (((\y. (x y)) True) x))` : `((Bool -> a) -> b)`
  - transformed `(let w0 = True in (\x. (((\y. (x y)) True) x)))` : `((Bool -> ((Bool -> a) -> b)) -> b)`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (((\y. (x True)) True) x))` : `((Bool -> a) -> b)`
  - transformed `(let w0 = True in (\x. (((\y. (x True)) True) x)))` : `((Bool -> ((Bool -> a) -> b)) -> b)`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (((\y. (x True)) x) True))` : `((Bool -> a) -> b)`
  - transformed `(let w0 = True in (\x. (((\y. (x True)) x) True)))` : `((Bool -> (Bool -> a)) -> a)`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (((\y. (y True)) x) True))` : `((Bool -> a) -> b)`
  - transformed `(let w0 = True in (\x. (((\y. (y True)) x) True)))` : `((Bool -> (Bool -> a)) -> a)`
- **MR-DEADLET** (`equal_outcome`)
  - source `(\x. (((\y. (x True)) x) x))` : `((Bool -> a) -> b)`
  - transformed `(let w0 = True in (\x. (((\y. (x True)) x) x)))` : `((Bool -> ((Bool -> a) -> b)) -> b)`
