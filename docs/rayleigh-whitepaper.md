# Rayleigh: Dimensional Inference for Unannotated Scientific Python

**Version:** 0.1.0

**Status:** Open research / engineering project. Not peer-reviewed.

**DOI:** *coming soon*

**Repository:** `https://github.com/<user>/rayleigh`

---

## 1. Abstract

Scientific software encodes physical quantities in ordinary numeric variables. The
arithmetic is checked by the language; the physics is not. A program that adds a
velocity to an acceleration is syntactically valid, type-correct under Python's
type system, and silently wrong.

Existing unit safety libraries solve this by requiring the author to annotate
quantities with explicit units. This works, and is almost never applied to code
that already exists. The annotation burden falls on precisely the codebases that
most need checking: large, old, inherited, and written by people who have moved on.

Rayleigh takes a different position. It reconstructs dimensional constraints from
unmodified source code by treating units as an inference problem rather than a
declaration problem. Each variable is assigned a vector of SI base-dimension
exponents; the abstract syntax tree is walked to emit linear constraints over those
vectors; numeric literals matching known physical constants seed the system; and the
resulting linear system is solved exactly over the rationals. A variable resolves to
a dimension, resolves to a contradiction, or remains unknown. Contradictions are
reported as findings. Unknowns are reported as unknown.

This document describes the representation, the constraint algebra, the inference
pipeline, the current limitations, and the evaluation work required before any
claim of general effectiveness can be made.

---

## 2. Problem

Consider a fragment typical of simulation code:

```python
velocity = distance / time
```

Python evaluates this correctly as arithmetic. It has no representation of the fact
that the result carries dimension **L T⁻¹**, that adding it to `time` would be
meaningless, or that passing it to `math.sin` would be a category error.

The consequences are not hypothetical. The loss of the Mars Climate Orbiter in 1999
is the widely cited example: one component produced impulse in pound-force seconds
while the consuming component expected newton-seconds. The arithmetic was valid
throughout. Less dramatic instances — degrees where radians were expected, joules
where electronvolts were intended, kilometres where metres were assumed — are a
routine source of error in scientific and engineering codebases, and are typically
found by inspecting anomalous output rather than by any automated check.

The structural problem is that the physical meaning of a variable lives in three
places, none of which the interpreter can see: the variable's name, a comment, and
the author's memory. Only the first two survive in the source, and neither is
reliable.

---

## 3. Core Thesis

**Dimensional information is recoverable from unannotated source code, because the
operations performed on a quantity constrain what that quantity can be.**

The claim rests on two observations.

First, arithmetic operations are dimensionally constrained. Addition requires its
operands to share a dimension. Multiplication combines dimensions additively in the
exponent space. Transcendental functions require dimensionless arguments. Every such
operation in a program is therefore a *constraint*, not merely a computation, and a
program is a large system of them.

Second, some quantities are dimensionally self-identifying. A literal `9.81`
appearing in a gravitational context is almost certainly **L T⁻²**. The value
`6.674e-11` is the gravitational constant, **M⁻¹ L³ T⁻²**. `299792458` is the speed
of light. These act as anchors: they pin specific nodes of the constraint graph to
known dimensions, from which the rest can propagate.

Given enough anchors and enough constraints, a substantial fraction of a program's
variables become determined. Where the system is over-determined and inconsistent,
a bug has been proven. Where it is under-determined, nothing is claimed.

Rayleigh does not require the programmer to describe their intent. It infers what
the code has already committed to.

---

## 4. Representation

A dimension is represented as a seven-element vector of exponents over the SI base
dimensions:

```
M   mass                 (kilogram)
L   length               (metre)
T   time                 (second)
I   electric current     (ampere)
Θ   thermodynamic temp   (kelvin)
N   amount of substance  (mole)
J   luminous intensity   (candela)
```

Velocity is `(0, 1, -1, 0, 0, 0, 0)`. Force is `(1, 1, -2, 0, 0, 0, 0)`. A
dimensionless quantity is the zero vector.

Exponents are stored as exact rationals rather than floating-point values. This is
not a stylistic choice. Physical expressions routinely produce fractional exponents —
the period of a pendulum involves the square root of a length divided by an
acceleration — and floating-point exponents accumulate error that eventually
manifests as a spurious contradiction or, worse, a spurious agreement. Exact
rational arithmetic makes the solver's verdicts reliable.

Units are deliberately *not* modelled. Rayleigh reasons about dimensions, not about
metres versus feet. This is a real limitation, discussed in §10: the Mars Climate
Orbiter failure was a unit mismatch within a single dimension, and dimensional
analysis alone would not have caught it. What dimensional analysis does catch is the
larger and more common class of errors in which incompatible physical quantities are
combined at all.

---

## 5. Inference Pipeline

```
Python source
     │
     ▼
Python AST                     (ast.parse)
     │
     ▼
Constraint extraction          (walker.py)
     │
     ▼
Seeding: constants + priors    (constants.py, priors.py)
     │
     ▼
Exact linear solve             (solver.py)
     │
     ▼
Dimensional diagnosis          (report.py)
```

Each stage is separable and independently testable. The walker emits constraints
without attempting to solve them; the solver has no knowledge of Python. This
separation matters for the evaluation work in §11, where the correctness of
constraint extraction and the correctness of the solve must be assessed
independently.

**Constraint extraction** walks the AST and emits one constraint per dimensionally
meaningful operation, each tagged with its source line and the originating
expression text. Provenance is captured at emission time; reconstructing it after
the solve is impractical, because a contradiction is a property of a *set* of
constraints and the report must be able to name every member of that set.

**Seeding** resolves unknowns from two sources. Numeric literals are matched against
a table of physical constants within a relative tolerance. Variable names are matched
against a prior table (`dt`, `mass_kg`, `velocity`, `radius`, `theta`, and similar).
These two sources carry very different confidence, and the distinction is preserved
through to the report.

**Solving** treats each of the seven base dimensions as an independent linear system
over the rationals, since the constraint algebra acts componentwise on the exponent
vector. Gaussian elimination with exact fractions yields, for each variable, one of
three outcomes: a determined exponent, an inconsistent system, or an
under-determined system.

---

## 6. Constraint Algebra

| Construct | Constraint emitted |
|---|---|
| `a + b`, `a - b` | `dim(a) = dim(b)`; result takes that dimension |
| `a * b` | `dim(result) = dim(a) + dim(b)` |
| `a / b` | `dim(result) = dim(a) − dim(b)` |
| `a ** n`, literal `n` | `dim(result) = n · dim(a)` |
| `a ** b`, non-literal `b` | `dim(a) = 0` and `dim(b) = 0` |
| `a < b`, `a == b`, etc. | `dim(a) = dim(b)` |
| `sin`, `cos`, `tan`, `exp`, `log` | `dim(arg) = 0`; result dimensionless |
| `sqrt(a)` | `dim(result) = ½ · dim(a)` |
| `abs(a)`, unary `-a` | `dim(result) = dim(a)` |
| Assignment | binds the target to the expression's dimension |

Two subtleties are worth stating explicitly.

**Assignment is not identity.** Python permits a name to be rebound to a value of a
different dimension, and this is legal and common:

```python
x = 5.0          # metres
x = x / t        # now metres per second
```

Treating `x` as a single dimensional entity would produce an immediate false
positive. Rayleigh versions each binding, so the constraint system refers to
`x@line3` and `x@line4` as distinct variables. Without this, the tool is unusable on
real code.

**Power with a non-literal exponent forces both operands dimensionless.** `a ** b`
where `b` is itself a variable cannot produce a well-defined dimension unless `a` is
dimensionless, since the exponent would vary at runtime.

---

## 7. Unknowns and Uncertainty

The design commitment that most shapes Rayleigh's output is this: **when the
constraint system does not determine a variable's dimension, the tool reports
`unknown` and makes no further claim.**

This is a deliberate rejection of the alternative, which is to guess from context and
present the guess with hedged language. A static analysis tool is adopted or
abandoned on its false-positive rate. A tool that reports a plausible-looking
dimension for an under-determined variable will eventually contradict a user who
knows their own code, and will be uninstalled that afternoon.

Findings are therefore tiered by the provenance of the evidence that produced them:

- **High confidence** — the contradiction follows from constraints seeded by matched
  physical constants and structural operations alone. No name heuristics involved.
- **Suggested** — the contradiction depends on one or more variable-name priors.
  Reported separately, phrased as a question rather than an assertion.
- **Unknown** — the system is under-determined. Reported as coverage information,
  not as a finding.

Coverage — the fraction of variables resolved — is itself reported, because a run
that resolves 15% of a file is providing much weaker assurance than one that resolves
80%, and the user is entitled to know which they received.

---

## 8. Worked Example

```python
speed = 10.0
acceleration = speed + 9.81
```

Constraint extraction emits:

```
c1:  dim(speed@1)        = ?                      [line 1]
c2:  dim(speed@2)        = dim(9.81)              [line 2, from '+']
c3:  dim(acceleration@2) = dim(speed@2)           [line 2]
```

Seeding contributes:

```
s1:  dim(9.81)           = (0, 1, -2, 0, 0, 0, 0)   L T⁻²   [constant match]
s2:  dim(speed@1)        = (0, 1, -1, 0, 0, 0, 0)   L T⁻¹   [name prior]
```

The solve finds `c2` and `s1` require `speed@2` to be **L T⁻²**, while `s2` requires
**L T⁻¹**. The system is inconsistent.

```
rayleigh sim.py

sim.py:2  suggested  dimensional inconsistency in addition
    acceleration = speed + 9.81
                   ^^^^^   ^^^^
    speed        inferred as  L T⁻¹   (from variable name 'speed')
    9.81         inferred as  L T⁻²   (matches standard gravity)
    addition requires operands to share a dimension

    2 variables resolved, 0 unknown  (coverage 100%)
```

This finding is tiered *suggested* rather than *high confidence*, because one side of
the contradiction rests on a name prior. Had `speed` been derived from a division of
a length by a time elsewhere in the file, the same finding would be reported as high
confidence.

---

## 9. Architecture

```
rayleigh/
├── dimension.py     Dimension type: 7-vector of Fractions, with algebra
├── constraints.py   Constraint representation and provenance records
├── walker.py        ast.NodeVisitor → constraint set
├── constants.py     Physical constant fingerprint table
├── priors.py        Variable-name heuristics
├── solver.py        Exact Gaussian elimination over the rationals
└── report.py        Findings, tiering, and coverage output
```

`dimension.py` and `solver.py` have no dependency on Python's `ast` module and are
testable in isolation against hand-written constraint systems. `walker.py` is
testable by asserting on emitted constraints without invoking the solver. This
matters because the two failure modes — extracting the wrong constraints, and
solving a correct system incorrectly — produce identical symptoms at the CLI and
must be distinguishable during development.

---

## 10. Current Limitations

These are stated plainly because the tool's credibility depends on it.

**Dimensions, not units.** Rayleigh cannot distinguish metres from feet, or joules
from electronvolts. The Mars Climate Orbiter error, which motivates this work, was a
unit error within a consistent dimension and would not be caught. Unit-level
inference requires scale factors alongside exponents and is not implemented.

**Single-file analysis.** Cross-module inference, imported function signatures, and
class attribute dimensions are not yet handled. Real scientific codebases span many
files, so this is the most consequential limitation for practical use.

**No runtime values.** Quantities read from files, arrays whose elements carry
different dimensions per column, and values derived from configuration are opaque.

**Container elements are unmodelled.** A NumPy array or list is treated as a single
entity; a state vector mixing position and velocity components is a common pattern
that Rayleigh currently cannot represent.

**Incomplete constant table.** The fingerprint table covers common constants.
Coincidental numeric matches are possible — a literal `9.81` need not be gravity —
and the tolerance window trades false anchors against missed ones.

**Name priors are heuristic and culture-bound.** They encode conventions common in
English-language physics code and will be less effective elsewhere.

**No evaluation yet.** The tool has not been benchmarked. Precision and recall are
unmeasured. §11 describes what would be required to make any claim about
effectiveness.

---

## 11. Evaluation Plan

No performance claims are made in this version. The following is what would be
required to support them.

**Corpus.** Three categories of Python programs are needed: (a) *valid* programs
known to be dimensionally correct; (b) *invalid* programs with deliberately injected
dimensional errors at known locations; (c) *ambiguous* programs where the correct
answer is genuinely `unknown`. The third category matters most, because a tool that
achieves high recall by guessing is not useful, and only category (c) exposes that.

**Metrics.**

- *Precision* on category (b): of reported findings, the fraction that are real.
- *Recall* on category (b): of injected errors, the fraction found.
- *False positive rate* on category (a): findings reported on correct code. This is
  the number that determines adoption; a rate above a few percent makes the tool
  unusable in CI.
- *Coverage*: fraction of variables resolved, reported separately per category.
- *Silence on ambiguity*: fraction of category (c) variables correctly reported as
  unknown rather than assigned a dimension.

**Ablations.** Coverage and precision should be measured with name priors disabled,
to separate what the structural constraint algebra achieves on its own from what the
heuristics contribute. If the priors are carrying most of the result, the central
thesis of §3 is weaker than claimed and should be restated.

**External validation.** Findings on public scientific repositories should be
submitted to their maintainers, and the maintainers' verdicts — real bug, false
positive, or intentional — recorded as ground truth. This is slower than synthetic
benchmarking and considerably more informative.

---

## 12. Related Work

Rayleigh's contribution is not dimensional analysis, which is old, nor unit checking
in programming languages, which is well explored. It is the removal of the annotation
requirement.

**Annotation-based unit libraries.** `pint`, `astropy.units`, and `unyt` attach units
to values at runtime and raise on incompatible operations. They are correct, mature,
and widely available. They require the author to annotate every quantity at its
origin, which is why they are used in new code and rarely retrofitted onto existing
code. Rayleigh addresses the complementary case and is not a replacement for them;
where a codebase already uses one of these libraries, it provides stronger guarantees
than inference can.

**Unit types in language design.** F# supports units of measure in its type system.
Fortress, Ada, and several research languages have offered dimensional types. These
approaches are sound but require the language, or at minimum the declarations, to
change.

**Static dimensional inference in the literature.** Type-inference approaches to
units have been studied since Kennedy's work on dimension types in ML, which
establishes that dimensional types admit principal types and can be inferred in the
Hindley–Milner setting. Subsequent work has applied similar ideas to C, Fortran, and
MATLAB, and to spreadsheet formulas. Rayleigh's contribution relative to this body of
work is pragmatic rather than theoretical: it targets dynamically typed Python
without declarations, uses numeric constant fingerprinting as an inference seed, and
prioritises reporting `unknown` over achieving completeness.

*A full literature review has not been completed. This section should be treated as
an orientation, not a survey, and the positioning claims above should be revisited
once it has been.*

---

## 13. Future Work

**Scale factors alongside exponents.** Extending the representation from dimensions
to units — carrying a rational scale factor per quantity — would make the Mars
Climate Orbiter class of error detectable. This is the single highest-value extension.

**Cross-module inference.** Building function summaries — a dimensional signature per
function, inferred once and reused at call sites — extends the analysis across a
codebase without whole-program solving.

**Library models.** Hand-written dimensional signatures for NumPy, SciPy, `astropy`,
and orbital mechanics libraries would substantially raise coverage, since scientific
code spends most of its time in library calls.

**Probabilistic priors.** Replacing the current binary name-matching with learned
priors over identifier vocabulary, calibrated so that stated confidence matches
observed accuracy.

**Provenance graphs.** Rendering the constraint chain that produced a finding, so a
user can inspect the inference rather than trust it.

**Editor integration.** Language Server Protocol support, surfacing inferred
dimensions on hover. Inferred dimensions are useful documentation even when no bug is
present, and this may prove the more compelling use.

---

## 14. Reproducibility

**Version.** Rayleigh v0.1.0
**Python.** 3.10 or later (uses `ast` features and structural pattern matching)
**Dependencies.** Standard library only for the core; `pytest` for the test suite.

```bash
git clone https://github.com/<user>/rayleigh
cd rayleigh
pip install -e .

# run the test suite
pytest

# analyse a file
rayleigh examples/orbit.py

# show inferred dimensions for all variables, not only findings
rayleigh --show-all examples/orbit.py

# suppress name-prior-based findings
rayleigh --no-priors examples/orbit.py

# emit machine-readable output
rayleigh --json examples/orbit.py
```

Test fixtures under `tests/fixtures/` include a dimensionally clean program, a
program with an injected error at a known line, and a program that should report
`unknown` rather than resolve. These correspond to the three corpus categories in
§11 and are the seed of the evaluation set.

---

## Citation

```
Rayleigh: Dimensional Inference for Unannotated Scientific Python. v0.1.0.
DOI: coming soon
```

A DOI will be issued by archiving the repository through Zenodo once the evaluation
in §11 has been carried out.

---

## Status and Positioning

Rayleigh is an open research and engineering project exploring automatic dimensional
inference for unannotated scientific Python. It has not been peer-reviewed, has not
been benchmarked, and makes no claim of novelty relative to the existing literature
on dimensional type inference. Findings it reports should be verified by someone who
knows the code.
