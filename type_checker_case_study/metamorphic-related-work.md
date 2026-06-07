# Related work scan: ideas worth adding to our metamorphic oracles

> **Status (implemented):** all three ranked recommendations below were built,
> tested for soundness, and kept in the pipeline as MR-CLASH, MR-KPROJ, and
> MR-LETLAM. MR-CLASH is sound with zero violations; MR-KPROJ corroborates the
> Finding-1 substitution bug; MR-LETLAM found a new **over-acceptance** bug
> (Finding 2), confirmed against the original Haskell. See METAMORPHIC_FINDINGS.md.


A scan of recent (≈2020–2025) automated-testing papers relevant to testing a
type checker / verifier with metamorphic oracles, and what transfers to this
case study. The short version: our approach is well-aligned with the state of
the art, and the bug we found is exactly the class the most productive line of
work targets. There are three concrete additions worth making, ranked below.

## What we already do, and how it maps

| Our lane | Closest literature |
| --- | --- |
| MR-DEADLET (dead `let` must preserve type) found our bug | EMI / dead-code mutation -- the single most productive compiler-testing methodology |
| MR-ALPHA, MR-LIT, MR-DEADLET, MR-LAM (semantics-preserving → equal/structured output) | Statfier's semantic-preserving program transformations |
| MR-ERRPROP (closed ill-typed subterm keeps the whole ill-typed) | sound "must still reject" oracles |
| Souffle policy engine (`expr_policy.dl`) | DLSmith metamorphic testing of Datalog engines |

So nothing here is off-trend. The gaps are specific and fillable.

## The papers (what transfers)

- **Finding Typing Compiler Bugs (Hephaestus), PLDI 2022.** Tests JVM type
  checkers with two transformations: *type-erasure mutation* (drop annotations,
  the inferred type must still match) and *type-overwriting mutation* (replace a
  type with an incompatible one, the checker must now reject). The
  overwriting/rejection direction is the engine behind their soundness-bug
  finds. **This is our biggest gap: every current MR is a "preserve" relation; we
  have no "this edit must cause rejection" relation.**
- **Equivalence Modulo Inputs (EMI), PLDI 2014 + ongoing variants.** Mutate code
  in regions that don't affect the result; output must be unchanged. Our
  MR-DEADLET is literally a type-level EMI instance, and EMI is *why* it works:
  "dead code changes the result" is the most fruitful bug class in compiler
  testing. Suggests generalizing dead-context replacement into a family.
- **Statfier, ESEC/FSE 2023.** Tests static analyzers with a catalog of
  semantic-preserving transformations (incl. class/AST-shape changes), comparing
  analyzer output on seed vs. variant. Validates and broadens our transform set.
- **Interrogation Testing (Sherlock), ASE 2024.** Tests a *single* analyzer for
  **soundness AND precision**, using a knowledge base of accumulated queries to
  build stronger oracles. Precision maps to *principal-type generality* for us:
  the checker should infer the most general type, not merely a correct one.
- **Dependency-Aware Metamorphic Testing of Datalog Engines (DLSmith), ISSTA
  2023.** Semantics-preserving Datalog rewrites (rule reordering, predicate
  renaming) must give identical query results. Directly applicable to our
  `policy/expr_policy.dl` -- a way to test *our tooling*, not the subject.
- **MR-Scout, TOSEM 2024.** Auto-synthesizes metamorphic relations from existing
  test cases. Could mine MRs from our parity suite / ground-truth catalog later.
- **Navigating the Python Type Jungle, arXiv 2509.13022 (2025); typing-spec
  conformance suites (ty/pyrefly/Zuban).** More about formalizing Python's type
  system than transferable MRs, but the *conformance-suite* framing (curated
  programs with expected error/no-error) mirrors our generated suites, and the
  multi-checker comparison is a differential-testing angle complementary to ours.

## Recommended additions, ranked

### 1. Type-overwriting / negative substitution MRs  (highest value)

*From Hephaestus's type-overwriting; the rejection direction we lack.* Build
contexts that pin a slot to a known ground type, then graft a closed term of a
**different** ground type and require the checker to **reject**:

- `If(ETrue(), s_bool, t_int)` must be `heterogeneous-if` (branches disagree).
- `If(t_int, a, b)` must be `non-bool-condition`.
- `App(f_bool_to_bool, t_int)` must be `application-mismatch`.

Reference-free: we know `X ≠ Y` by construction, so the result *must* be
ill-typed regardless of the oracle's specific answer. This is the sound dual of
the planned MR-GSUB and tests the soundness machinery that MR-ERRPROP only
touches indirectly. Cheap to build from the existing corpus (we already classify
many closed ground-typed expressions).

### 2. EMI-style dead-context family  (generalize the bug-finder)

*From EMI.* Generalize MR-DEADLET + the planned MR-CONST into one relation: *the
type is invariant under replacing any type-irrelevant well-typed subterm with
any other well-typed closed term.* Type-irrelevant positions: the bound
expression of an unused `let`; the discarded argument of a K-projection
`App(App(\a.\b.a, real), junk)`; nested/stacked dead bindings. This widens the
exact net that already caught the substitution bug, so it is likely to surface
more manifestations and any sibling bugs.

### 3. Precision (principal-type) MRs  (soundness's other half)

*From Interrogation Testing's soundness+precision split.* Add relations that the
inferred type is the *most general* one, not just *a* correct one:

- **Monotonicity:** specializing a variable's use (adding a constraint) yields a
  type no more general than before.
- **let ≥ lambda generality (MR-LETLAM, already Phase 3):** reframe explicitly as
  a *precision* check and add the `is_instance_of` subsumption helper it needs.

A precision MR is notable because the bug we found is *exactly* a precision/
soundness failure (the inferred type was too general), so this family targets the
same fault class from the general-vs-specific direction.

### Also worth doing (lower priority)

- **Metamorphic-test our Souffle policy** (DLSmith): reorder rules / rename
  predicates in `expr_policy.dl`, require identical predictions. Tests our
  tooling, not the subject.
- **Differential cross-check** against the original Haskell, systematized
  (we already use `runghc` to confirm findings). A reference-*ful* complement to
  the reference-free MRs.

## Bottom line

The literature endorses the path: semantics-preserving transforms as oracles
(Statfier/EMI/DLSmith) and single-tool soundness+precision testing
(Interrogation). The one technique we are clearly missing is the
**type-overwriting / rejection** direction (Hephaestus), which is also the most
productive for soundness bugs -- recommend implementing it next (Phase 1.5),
ahead of the remaining Phase 2/3 preserve-relations.

## References

1. Stefanos Chaliasos, Thodoris Sotiropoulos, Diomidis Spinellis, Arthur Gervais,
   Benjamin Livshits, and Dimitris Mitropoulos. "Finding Typing Compiler Bugs."
   PLDI 2022. doi:10.1145/3519939.3523427.
   <https://theosotr.github.io/assets/pdf/pldi22.pdf>
   *(MR-CLASH — type-overwriting mutation.)*
2. Vu Le, Mehrdad Afshari, and Zhendong Su. "Compiler Validation via Equivalence
   Modulo Inputs." PLDI 2014. doi:10.1145/2594291.2594334.
   <https://www.vuminhle.com/pdf/pldi14-emi.pdf>
   *(MR-DEADLET, MR-KPROJ — dead-code / EMI.)*
3. David Kaindlstorfer, Anastasia Isychev, Valentin Wüstholz, and Maria Christakis.
   "Interrogation Testing of Program Analyzers for Soundness and Precision Issues."
   ASE 2024. doi:10.1145/3691620.3695034.
   <https://mariachris.github.io/Pubs/ASE-2024-Sherlock.pdf>
   *(MR-LETLAM — soundness + precision testing of a single analyzer.)*
4. Huaien Zhang, Yu Pei, Junjie Chen, and Shin Hwei Tan. "Statfier: Automated
   Testing of Static Analyzers via Semantic-Preserving Program Transformations."
   ESEC/FSE 2023. doi:10.1145/3611643.3616272.
   <https://www.shinhwei.com/statfier.pdf>
5. Muhammad Numair Mansur, Valentin Wüstholz, and Maria Christakis.
   "Dependency-Aware Metamorphic Testing of Datalog Engines." ISSTA 2023.
   doi:10.1145/3597926.3598052.
   <https://mariachris.github.io/Pubs/ISSTA-2023-DLSmith.pdf>
6. Congying Xu, Valerio Terragni, Hengcheng Zhu, Jiarong Wu, and Shing-Chi Cheung.
   "MR-Scout: Automated Synthesis of Metamorphic Relations from Existing Test
   Cases." TOSEM 2024. doi:10.1145/3656340. <https://arxiv.org/abs/2304.07548>
7. "Navigating the Python Type Jungle." arXiv:2509.13022, 2025.
   <https://arxiv.org/abs/2509.13022>
8. (context) "Differentially Testing Soundness and Precision of Program
   Analyzers." arXiv:1812.05033, 2018. <https://arxiv.org/abs/1812.05033>
