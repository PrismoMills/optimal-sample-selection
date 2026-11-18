# Optimal Sample Selection System

A Python desktop application for finding small families of sample groups that cover all required target combinations.

## Run

Requires Python 3.10 or later with Tkinter. Uses only the Python standard library.

```sh
python app.py
```

The application creates a local SQLite database named `results.db` beside the source files.

## Parameters

| Parameter | Meaning | Range |
| --- | --- | --- |
| m | Total number of sample labels | 45 to 54 |
| n | Number of distinct labels selected for the run | 7 to 25 |
| k | Number of labels per output group | 4 to 7 |
| j | Size of each target combination | s <= j <= k <= n |
| s | Required intersection with an output group | 3 to j |

Every j-element subset of the selected samples must share at least s elements with at least one output group. The objective is to reduce the number of output groups.

## Usage

1. Enter m, n, k, j, and s, then select **Solve and Save**.
2. The application randomly selects n distinct labels and displays the samples, groups, lower bound, and measured solve time.
3. Select a saved run in **History** and choose **View** or **Delete**.
4. Choose **Clear All** and confirm to delete all saved runs.

Results are paginated. A run is identified by `m-n-k-j-s-run_id`.

## Algorithms and limitations

The solver combines cyclic and XOR symmetry constructions, greedy covering, and time-bounded branch-and-bound. Small instances can use unrestricted exact search; larger instances use exact repairs of local residual covering models. The search budget is three seconds. Coverage verification and output preparation can extend total execution time.

For (k,j,s)=(6,5,5), the solver directly constructs the small Witt design at n=12 and its extension at n=13, producing 132 and 245 groups respectively. Both reach the recursive counting lower bound. The implementation generates these constructions rather than downloading block lists.

All returned solutions pass exhaustive coverage verification. **Proven optimal** appears only when the group count matches a valid lower bound. Other results are feasible covers whose group counts may exceed the optimum. Time-bounded runs can produce different group counts on different machines.

For some large k=j=s+1 instances, a modular-sum construction supplies a fallback cover. A short search may return this larger initial cover.

## Files

- `app.py` provides the Tkinter interface and SQLite history.
- `solver.py` constructs, improves, and verifies covers.
- `results.db` stores local run history and is excluded from version control.

## Reference

The small Witt design construction follows the projective-line description of the M12 design. The n=13 extension is constructed recursively from its derived designs.

[The M12 Design, University of Bayreuth](https://mathe2.uni-bayreuth.de/discreta/M12/m12_design.html)
