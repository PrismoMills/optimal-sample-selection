# Optimal Sample Selection System

**A sample covering tool built with Python, Tkinter and SQLite.**

The application selects sample groups that cover every required target combination while trying to reduce the number of groups. Users enter five parameters, run the solver and inspect verified results in a desktop interface. Each run is saved locally for later review.

## What you can do

- Configure the sample population, selected sample count, output group size and coverage requirement.
- Automatically draw distinct sample labels for a run.
- Generate groups and verify that every target combination is covered.
- Inspect the group count, theoretical lower bound and measured solve time.
- Browse large results page by page.
- View or delete a saved run, or clear all history after confirmation.

## How selection works

The program selects `n` distinct labels from `1` to `m`. Each output group contains `k` labels. Every `j`-element combination of the selected labels must share at least `s` elements with an output group. The objective is to use fewer output groups while preserving complete coverage.

| Parameter | Meaning | Supported range |
| --- | --- | --- |
| m | Total number of sample labels | 45 to 54 |
| n | Number of labels selected for the run | 7 to 25 |
| k | Labels in each output group | 4 to 7 |
| j | Labels in each target combination | s <= j <= k <= n |
| s | Minimum required intersection | 3 to j |

The solver combines symmetry constructions, greedy covering and time-bounded branch-and-bound. Small instances can search all candidates; larger instances use exact repairs of smaller residual covering problems. The search budget is three seconds, with additional time needed for coverage verification and output preparation.

For `(k,j,s)=(6,5,5)`, a small Witt design and its extension directly produce 132 groups at `n=12` and 245 groups at `n=13`. Both match the recursive counting lower bound.

Every returned solution passes exhaustive coverage verification. **Proven optimal** appears when the group count matches a valid lower bound. Other results are feasible covers whose counts may exceed the optimum.

## Run locally

Requirements are Python 3.10 or later with Tkinter. The application uses the Python standard library.

```sh
python app.py
```

1. Enter `m`, `n`, `k`, `j` and `s`, then select **Solve and Save**.
2. Review the selected labels, output groups, lower bound and actual solve time.
3. Select a run from **History** to view or delete it. Choose **Clear All** to delete all saved runs after confirmation.

The application creates `results.db` beside the source files. Run labels use `m-n-k-j-s-run_id`.

## Project layout

```text
app.py       Desktop interface and SQLite history
solver.py    Cover construction, optimization, lower bounds and verification
results.db   Local run history, created at runtime and excluded from Git
```

## Current scope

The application is a desktop tool for exploring combinatorial sample coverage. Time-bounded results can vary between machines. Large inputs may return a larger initial cover when the search budget expires. Complete coverage is checked before results are returned, while optimality remains unproven for many parameter combinations.

## Reference

The small Witt design uses the projective-line description of the M12 design. Its extension to 13 points is constructed recursively from derived designs.

[The M12 Design, University of Bayreuth](https://mathe2.uni-bayreuth.de/discreta/M12/m12_design.html)
