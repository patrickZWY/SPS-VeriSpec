1. Begin with a simple python project in directory `CutePetsBoston`.
Work on current existing tests. (Do we really this step if we start 
with LLM translating program into Souffle?)

2. Use LLM to translate the project into Souffle. Can we get compilable
Souffle programs? What aspects of the project should be translated to
Souffle (feed the whole program? model relations between objects? models 
based on some heuristics such as some properties we want to check? 
model for information-flow analysis? model for permission control?)?
We should start with something relatively easy: whole-program or model some simple
properties about our program then move to security/analysis specific ones to see if
we can generate security specific models (is there an error state where our program
or variables cannot access? if our program deals with money, is it possible to do
re-entrancy/replay attack?).
Current: Model python dataclasses, then model the effects on the dataclasses (read/write/exception/return)
Potential: Model dataflow
Potential future refinements:
- alias analysis so dataclass values can still be tracked after reassignment to local aliases
- cross-function flow analysis so dataclass field usage can be connected through helper functions and method calls
- derive tests from theorems / derived relations, for example by turning surfaced relations into fuzzing targets and generated property checks

Check out this video, super related to what we do here: REBASE'25 from facts to theories:
deductive databases, they don't use Souffle for testing but more closely integrated with
their dev/build process

3. Explore by deducting relationships in our program. (How do we do this? Handwrite for each kind of model we want to do or is it possible to generate them on the fly?)

4. Create new tests based on the deducted relationships by fuzzing.
(Again, what we want to fuzz about
the properties depend on what we want
to achieve?)

5. Validate the tests by executing them.

6. Surface contradictions and report to users.

7. User makes decisions to modify their programs or Souffle programs.

8. Modify our programs and update knowledge base.
