<div align="center">

# Rayleigh

**Finds unit bugs in scientific Python. No annotations required.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status: research](https://img.shields.io/badge/status-research-orange.svg)](docs/rayleigh-whitepaper.md)

[Whitepaper](docs/rayleigh-whitepaper.md) · [How it works](#how-it-works) · [Limitations](#what-rayleigh-cannot-do)

</div>

---

```python
speed = 10.0
acceleration = speed + 9.81
```

Python runs this happily. It is physically meaningless.

```console
$ rayleigh sim.py

sim.py:2  dimensional inconsistency in addition
    acceleration = speed + 9.81
                   ^^^^^   ^^^^
    speed   inferred as  L T⁻¹    (from variable name)
    9.81    inferred as  L T⁻²    (matches standard gravity)
    addition requires operands to share a dimension

2 variables resolved, 0 unknown  (coverage 100%)
```

Rayleigh read that file. Nobody annotated anything.

---

## The problem

Scientific code carries physical meaning that the interpreter cannot see. A velocity
and an acceleration are both `float`. Adding them is valid Python, passes type
checking, and is wrong.

The existing answer is to annotate every quantity with its units using `pint`,
`astropy.units`, or `unyt`. These libraries are excellent and you should use them in
new code. But they require the author to declare units at every origin point — which
is why they are almost never retrofitted onto the codebases that need them most: the
large, old, inherited ones written by someone who left in 2019.

Rayleigh takes the opposite approach. **It infers dimensions instead of asking for
them.**

## How it works

Units are treated as a linear algebra problem.

Every variable is assigned a vector of seven SI base-dimension exponents
(mass, length, time, current, temperature, amount, luminosity). Velocity is
`(0, 1, -1, 0, 0, 0, 0)`. Force is `(1, 1, -2, 0, 0, 0, 0)`.

Then the source is walked, and **every arithmetic operation becomes a constraint**:

| In your code | What it proves |
|---|---|
| `a + b` | `a` and `b` have the same dimension |
| `a * b` | exponents add |
| `a / b` | exponents subtract |
| `a ** 2` | exponents scale |
| `sin(x)`, `log(x)` | `x` must be dimensionless |

Some numbers identify themselves. `9.81` is standard gravity. `6.674e-11` is the
gravitational constant. `299792458` is the speed of light. These act as **anchors**,
pinning known dimensions into the constraint graph so the rest can propagate outward.

What remains is a linear system, solved exactly over the rationals — not floats,
because real physics produces fractional exponents and floating-point error becomes
a false verdict. Each variable comes back as one of three things:

- **determined** — its dimension is now known
- **contradictory** — the code is provably inconsistent, and you have a bug
- **unknown** — not enough information

## Rayleigh says "unknown"

This is the design decision that matters most.

When the constraint system does not determine a variable, Rayleigh reports `unknown`
and stops. It does not guess from context and dress the guess in hedged language.

A static analysis tool lives or dies on its false-positive rate. One that invents a
plausible dimension will eventually contradict someone who knows their own code, and
will be uninstalled that afternoon.

Findings are tiered by the strength of the evidence behind them:

- **High confidence** — follows from matched physical constants and structural
  operations alone
- **Suggested** — depends on a variable-name heuristic, so it is phrased as a
  question
- **Unknown** — reported as coverage information, never as a finding

Coverage is always printed. A run resolving 15% of a file is a much weaker assurance
than one resolving 85%, and you are entitled to know which one you got.

## Install

```bash
pip install rayleigh
```

Python 3.10+. Core has no dependencies beyond the standard library.

## Usage

```bash
# analyse a file
rayleigh sim.py

# show every inferred dimension, not just the problems
rayleigh --show-all sim.py

# structural inference only — disable name heuristics
rayleigh --no-priors sim.py

# machine-readable, for CI
rayleigh --json sim.py
```

Exit code is non-zero when high-confidence findings are present, so it drops into CI
without a wrapper.

## What Rayleigh cannot do

Stated plainly, because a tool that oversells itself is worse than no tool.

**It checks dimensions, not units.** It cannot tell metres from feet, or joules from
electronvolts. The Mars Climate Orbiter failure — pound-force seconds against
newton-seconds — was a unit error inside a consistent dimension, and Rayleigh would
**not** have caught it. Unit-level inference requires scale factors alongside
exponents and is the top item in [future work](docs/rayleigh-whitepaper.md#13-future-work).

**Single-file only.** Cross-module inference and imported function signatures are not
yet handled.

**Containers are opaque.** A NumPy state vector mixing position and velocity
components cannot currently be represented.

**No benchmarks yet.** Precision and recall are unmeasured. The
[evaluation plan](docs/rayleigh-whitepaper.md#11-evaluation-plan) describes what is
required before any effectiveness claim can be made.

## Architecture

```
Python source → AST → constraints → seeding → exact solve → diagnosis
```

```
rayleigh/
├── dimension.py     7-vector of exact Fractions, with algebra
├── constraints.py   constraint records with source provenance
├── walker.py        ast.NodeVisitor → constraint set
├── constants.py     physical constant fingerprints
├── priors.py        variable-name heuristics
├── solver.py        exact Gaussian elimination over ℚ
└── report.py        tiering, coverage, output
```

`dimension.py` and `solver.py` never import `ast`. `walker.py` never solves anything.
The two failure modes — extracting wrong constraints, and solving a correct system
wrongly — look identical at the CLI, so they are kept separable and independently
testable.

## Contributing

The most useful contributions right now:

- **Real code that breaks it.** False positives are the highest-priority bug class.
- **Physical constants** missing from the fingerprint table.
- **Test fixtures** — especially *ambiguous* programs where `unknown` is the correct
  answer. These are the hardest to write and the most valuable.
- **Library dimensional signatures** for NumPy, SciPy, and `astropy`.

## Status

Rayleigh is an open research and engineering project exploring automatic dimensional
inference for unannotated scientific Python. It is not peer-reviewed, has not been
benchmarked, and makes no novelty claim against the existing literature on
dimensional type inference — see
[Related Work](docs/rayleigh-whitepaper.md#12-related-work).

## License

MIT
