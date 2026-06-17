Track 2 asks how we can check if a spec captures the system's intended behaviors. Specification Driven Development says our spec is the basis of our program and our program should be a subset of our spec. But this does not work irl. Why? Because people simply don't develop programs in this way. You do some fast prototyping, ship, and fix problems iteratively. Your program will almost always change faster than your spec unless you are only specifying a tiny section of your codebase. And let's talk about about specs themselves. Do we currently have the right tools to create good specs that are composable, maintainable, and easy to use? TLA? Lean/Coq/insert-your-favorite-proof-assistant? Some kind of structured or semi-structured language that is in-between your business needs and programming languages? These are good for certain parts of your program (proofs) or particular situations (dsl) but not your entire codebase.
Test Driven Development is the more popular and natural choice for developers. The totality of your test cases represents what your program should/shouldn't do. You write comprehensive tests first then your program should meet the expectations of your tests. But but but developers don't like to write tests or just don't like tests in general. 
But Dijkstra famous said that "program testing can be used to show the presence of bugs, but never to show their absence!" This is true for testing in general and it is also true that formal verification gives a stronger guarantee about our programs. But again for people who have done and seen verifications irl, this statement is largely irrelevant. Why?
What do we need to verify a program? Well, we need a model of that program and we need (safety) invariants. Finally we need a tool to check that model against the invariants and see if we can find violations of our (safety) invariants. Simple, right? Except it's not! Do we, the developers, really know what properties we need to guarantee when we are quickly coming up with a solution to our problems? Some programmers have to, but they are few (kernel, safety-critical, optimization, and of course the proof engineer who think about invariants all day etc). Researchers have in the past tried to extract properties from programs but it is difficult and we still don't have a good solution to this problem. Now the models and this is getting worse because your models will almost always be abstractions. And guess what most models are useless and maybe out of 100 you can find one good model that is written by a professional. This is not a scalable and practical solution. When developers talk about the correctness of a program, they are not talking about the formal properties of a data structure but imaging a vague and ambiguous specification which will only get clearer when they put them into code and start running the program.
This is what this project is about. On the one hand, we want the formal part of theorems, on the other hand, we want the ease, speed, and executable nature of testing. Property-based testing? It's good that it prevents a class of bugs instead single instances but it's not enough. Remember in the beginning where I mention the reality of development? People don't come up a perfect product or even the idea of a perfect product from the get-go (so you, no matter how closely you follow the doctrine of Test Driven Development, can't test everything unless you are elite programmers). Your program becomes perfect over time and testing should be part of this process of improvement. Testing should be more automated and formal than what we currently have. We want testing to be incorporated into the iterative loop of programming.
So what can we do? Most of this stuff is not news. In the past, people have worked on turning theorems into test cases (Property-based testing, QuickCheck in haskell, Hypothesis in python for examples), turning test cases into theorems (acl2 internals), theorems that can be combined(mutate?) (Logic programming where theorems are related to each other, knowledge graph?), but they mostly work independently to solve a particular problem. We want a unified testing framework (also not news, think refinement as some kind of composable iterative design to gradually create a formal model of a program. Consider also the use of knowledge graph or RAG to reduce hallucination in LLMs, but the former is too hard, how many passes of refinement do you need to have a satisfying model and how to compose them. The latter kinda useless otherwise why are people just dumping a repo so that LLM can learn it, e.g. effect for typescript, instead of using some structured
constraints for LLM) that can be part of the whole LLM workflow. Essentially we want a loop where we go from informal (tests) to formal (theorems) then back to informal while at the same time find ways to create/find new theorems/tests, keep the theorems that survive testings: they become the expanded correctness of our program. The basis for the correctness of our program is then a collection of theorems (where and how do they exist? Logic programming? some kind of graph?) and their instantiation (tests).
The difficulties then are:
1) Do we need a first set of tests or theorems as some kind of bootstraps.
2) How do we go from tests to theorems? Imitate what theorem provers do? LLM summaries?
3) Where do these theorems live? Can we manipulate/change them? How are they
related? Can logic programming help us with this, check out Souffle/pydatalog? 
4) How do we generate tests from theorems? What should the verification process of the newly created theorems look like?
5) How do we present the new findings to developers? Instantiated representative test case? What freedom does the developer have during this process? When there is conflict/contradiction between theorems and testing results, does the developer get to interfere? What happens when our program evolves over time?
6) a potential workflow: initial bootstrapping tests -> llm summaries -> souffle encoding -> tests -> verification through execution -> resolve conflicts/save tests/properties -> find new relations (can static analysis via souffle helps us here) -> new round (tests -> verification)

7) How does designing modeling with souffle look like?
Example of Configuration from https://goteleport.com/blog/testing-access-datalog/
(See a similar use case at Cloudflare with Racket's Rosette)
Collect facts about our system, predicates with parameters, and what they mean.
determine access based on the rules.

Examples of doing static analysis: https://souffle-lang.github.io/examples
pointer analysis: alias and extend aliasing with load and store
e.g. if x := a.f, a := b, b.f = y then x := y

Data-modeling at Michelin: https://blogit.michelin.io/an-introduction-to-datalog/
Use it like SQL, but with more abstraction capability, semi-structured data querying/manipulation

8) Let's start a minimal program and come up with some tests/properties about this minimal program.
Then let's abstract this process of coming up with properties and think about what tools are suitable for this
process. Then let's think about what can we do with the properties we now have. And then let's abstract this
process and think about what tools are suitable for this process.

9) Since Souffle is good for static analysis, can we also do mini static analysis on our
program and the result of this analysis can be presented to users to understand their generated program. What kind of analysis is adaptable/useful for an everyday program.
The current prototype answer is yes, with a limited but useful scope: dataclass
schema/effect modeling, interprocedural field summaries, program slices,
small abstract-state candidates, and typestate/protocol-order candidates help
target generated tests and review findings. They do not prove correctness, but
they identify which fields, branches, calls, and protocol steps deserve tests or
human inspection.

Current experiment conclusion: the Python-to-Datalog analysis layer is useful,
but executable oracle generation must not be overfit to one application. The
first generator mostly found CutePetsBoston-style formatter tests; that was too
narrow for dataclass-heavy libraries. The better loop is to keep Datalog as the
relation engine, then build generic oracle families on top of it: runtime
dataclass schema checks, constructor/default checks, default-factory checks, and
common conversion API checks. The dacite experiment is the clean near-term proof
target because it is small and dataclass-centered; Transformers is useful as a
scale and dependency stress target after runtime dependencies are installed.

10) To better understand how to leverage LLM in debugging system, do a case study of: Specula (LLM + TLA+ Spec) and midspiral (Dafny + LLM + React)

11) AI companies care about quality of code more than safety of code: make no mistake more than safety policies. 

12) DOMAIN MODELING WITH DATALOG by Norbert Wojtowicz
stream, tree, and mesh matter only
stream, semantics of order
tree, hierarchy, ui a set of tree, ruby stack a tree
graph, your entire business domain, a mesh
spotify, artist/listener/song, any you build is a new relationship
of what exists already, artist and song for a new album,
a playlist, a new relationship between user and song
user subscribes to playlist, ...
with every new feature, just create new relationships

why a lot of projects fail, if your main database is relational,
new implicit join between existing things and relational database
terrible at implicit joins, move to nosql when giving up.
datalog is a good in that you only need three: entity/attribute/value
RDF semantic web stuff
github
append only database that represents github
add new attributes to database, relations 
polymorphism in database, owner of repo can be user or organization
recursive rules, helpful for graph, or asking how many loops do we jump to get to what we want
