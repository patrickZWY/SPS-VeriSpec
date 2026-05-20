1. Begin with a simple python project in directory `CutePetsBoston`.
Work on current existing tests. (Do we really this step if we start 
with LLM translating program into Datalog?)

2. Use LLM to translate the project into Datalog. Can we get compilable
Datalog programs? What aspects of the project should be translated to
Datalog (feed the whole program? model relations between objects? models 
based on some heuristics such as some properties we want to check? 
model for information-flow analysis? model for permission control?)?
We should start with something relatively easy: whole-program or model some simple
properties about our program then move to security/analysis specific ones to see if
we can generate security specific models (is there an error state where our program
or variables cannot access? if our program deals with money, is it possible to do
re-entrancy/replay attack?).

Check out this video, super related to what we do here: REBASE'25 from facts to theories:
deductive databases, they don't use Datalog for testing but more closely integrated with
their dev/build process

3. Explore by deducting relationships in our program.

4. Create new tests based on the deducted relationships by fuzzing.

5. Validate the tests by executing them.

6. Surface contradictions and report to users.

7. User makes decisions to modify their programs or Datalog programs.

8. Modify our programs and update knowledge base.