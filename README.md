# Rayleigh

### Dimensional Inference for Unannotated Scientific Python

Rayleigh is a static-analysis engine that infers physical dimensions from ordinary scientific Python code and detects dimensional inconsistencies **without requiring unit annotations**.

```python
distance = 100
time = 5
speed = distance / time

acceleration = speed + 9.81
```

Rayleigh can reason that:

```text
speed      → L T⁻¹
9.81       → L T⁻²
```

and report:

```text
✗ DIMENSIONAL CONTRADICTION

Line 5: addition/subtraction requires matching dimensions

    acceleration = speed + 9.81

Left:  L T^-1
Right: L T^-2
```

---

## Why Rayleigh?

Python can tell you whether an expression is syntactically valid.

It cannot tell you whether that expression is **physically meaningful**.

Scientific programs often encode units implicitly through variable names, constants, and mathematical relationships:

```python
velocity = distance / time
force = mass * acceleration
```

This creates a class of bugs where the code executes perfectly but the underlying physics is wrong.

Rayleigh attempts to make those hidden physical constraints **machine-readable and statically checkable**.

---

## How it works

Rayleigh represents every physical quantity using the seven SI base dimensions:

```text
[M, L, T, I, Θ, N, J]
```

corresponding to:

```text
Mass
Length
Time
Electric current
Temperature
Amount of substance
Luminous intensity
```

It then walks the Python AST and converts mathematical operations into dimensional constraints.

### Constraint algebra

| Operation | Dimensional rule                |
| --------- | ------------------------------- |
| `a + b`   | `dim(a) = dim(b)`               |
| `a - b`   | `dim(a) = dim(b)`               |
| `a * b`   | exponents are added             |
| `a / b`   | exponents are subtracted        |
| `a ** n`  | exponents are multiplied by `n` |
| `sin(x)`  | `x` must be dimensionless       |
| `cos(x)`  | `x` must be dimensionless       |
| `exp(x)`  | `x` must be dimensionless       |
| `log(x)`  | `x` must be dimensionless       |

These constraints are then solved as linear systems over the seven SI dimensions.

---

## Inference without annotations

Rayleigh does not require code like:

```python
distance = 100 * meters
```

Instead, it can use multiple sources of evidence.

### Variable-name priors

```text
distance     → L
mass         → M
velocity     → L T⁻¹
acceleration → L T⁻²
time         → T
```

These are treated as **priors**, not absolute truth.

### Physical constants

Rayleigh can recognize known numerical fingerprints such as:

```text
9.80665       → standard gravity
299792458     → speed of light
6.67430e-11   → gravitational constant
```

Constants are matched with numerical tolerance and assigned their corresponding dimensional fingerprints.

### Mathematical relationships

Even without useful names, relationships can constrain unknowns:

```python
speed = distance / time
```

becomes:

```text
dim(speed) = dim(distance) - dim(time)
```

---

## Unknown means unknown

Rayleigh deliberately avoids pretending to know something it cannot infer.

If the available information is insufficient:

```text
? UNKNOWN
```

is reported instead of inventing a dimension.

This distinction is fundamental:

```text
✓ CONSISTENT
✗ CONTRADICTION
? UNKNOWN
```

---

## Architecture

```text
                    Python Source
                         │
                         ▼
                     AST Parser
                         │
                         ▼
                 Constraint Walker
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
          Name Priors  Constants   Algebra
              │          │          │
              └──────────┼──────────┘
                         ▼
                  Linear Constraint
                       Solver
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
          CONSISTENT  CONTRADICTION  UNKNOWN
                         │
                         ▼
                  Human Diagnostics
```

### Repository structure

```text
rayleigh/
├── rayleigh/
│   ├── dimension.py
│   ├── constants.py
│   ├── priors.py
│   ├── constraints.py
│   ├── walker.py
│   ├── solver.py
│   ├── report.py
│   └── cli.py
│
├── tests/
│   ├── test_dimension.py
│   ├── test_constraints.py
│   ├── test_walker.py
│   ├── test_solver.py
│   └── fixtures/
│
├── examples/
├── .github/
│   └── workflows/
└── pyproject.toml
```

---

## Installation

### From source

```bash
git clone https://github.com/kavya5cloud/Rayleigh.git
cd Rayleigh

python -m venv .venv
source .venv/bin/activate

pip install -e .
```

### Development dependencies

```bash
pip install pytest
```

---

## Usage

Check a Python file:

```bash
rayleigh check examples/constraint_demo.py
```

Rayleigh reports:

```text
✗ DIMENSIONAL CONTRADICTION

Line 5: addition/subtraction requires matching dimensions

    acceleration = speed + 9.81

Left:  L T^-1
Right: L T^-2
```

---

## Example

Input:

```python
distance = 100
time = 5
speed = distance / time

acceleration = speed + 9.81
```

Rayleigh reconstructs:

```text
distance
  → L

time
  → T

speed
  → distance / time
  → L T⁻¹

9.81
  → standard gravity
  → L T⁻²
```

The final operation requires:

```text
L T⁻¹ = L T⁻²
```

which is impossible.

Rayleigh therefore reports the dimensional contradiction.

---

## Design principles

### Physics before presentation

The core of Rayleigh is the inference engine, not a UI.

### Static before runtime

Rayleigh aims to identify dimensional errors from source code without executing the scientific program.

### Exact when possible

The solver uses exact rational arithmetic for dimensional exponents instead of relying on floating-point approximations.

### Honest uncertainty

When the available evidence does not uniquely determine a dimension, Rayleigh reports `UNKNOWN`.

### Explain the contradiction

A useful diagnostic should show not only **what failed**, but also the dimensional reasoning that led to the failure.

---

## Current scope

Rayleigh currently focuses on **single-file Python analysis**.

The current engine supports:

* SI base-dimension vectors
* symbolic dimensional expressions
* AST-based constraint extraction
* arithmetic dimensional algebra
* dimensional requirements for mathematical functions
* physical constant fingerprints
* variable-name priors
* linear constraint solving
* contradiction detection
* underdetermination detection
* source-line diagnostics

Cross-module semantic inference and broader scientific-library awareness are intentionally outside the initial scope.

---

## Development

Run the test suite:

```bash
python -m pytest
```

Rayleigh's CI runs the same tests automatically through GitHub Actions.

The project is being developed incrementally around a simple principle:

```text
source code
    ↓
hidden physical constraints
    ↓
formal representation
    ↓
inference
    ↓
scientific diagnosis
```

---

## Roadmap

* [x] SI dimensional representation
* [x] Symbolic dimension expressions
* [x] AST constraint extraction
* [x] Physical constant fingerprints
* [x] Variable-name priors
* [x] Linear constraint solver
* [x] Contradiction detection
* [x] Source-level diagnostics
* [ ] Richer provenance explanations
* [ ] JSON diagnostics
* [ ] CI-friendly machine-readable output
* [ ] More scientific function semantics
* [ ] Cross-module inference
* [ ] IDE integration
* [ ] Larger benchmark suite

---

## Status

**Early research / engineering prototype**

Rayleigh is an evolving project. The current implementation demonstrates the core idea: **physical dimensions can be inferred from otherwise unannotated scientific Python by treating code as a system of dimensional constraints.**

---

## License

MIT License

---

## Author

Built by **Kavya Shree**.

GitHub: [kavya5cloud/Rayleigh](https://github.com/kavya5cloud/Rayleigh)

---

> **Rayleigh turns implicit physics into explicit constraints.**
