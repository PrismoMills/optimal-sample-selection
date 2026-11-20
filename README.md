<div align="center">

<h1>Optimal Sample Selection</h1>
<p><strong>Cover every target combination with fewer sample groups.</strong></p>
<p>A desktop tool for constructing, checking and comparing combinatorial covers.</p>

<p>
<img alt="Python 3.10 or later" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white">
<img alt="Tkinter desktop interface" src="https://img.shields.io/badge/UI-Tkinter-5A67D8">
<img alt="Standard library only" src="https://img.shields.io/badge/Dependencies-Standard_library-428563">
</p>

<p><a href="#the-problem-in-one-example">The problem</a> · <a href="#try-it">Try it</a> · <a href="#what-the-result-tells-you">Reading results</a> · <a href="#how-it-finds-a-cover">Algorithms</a></p>

</div>

---

Suppose you have selected a set of samples and want to arrange them into smaller groups. Every required target combination needs enough overlap with at least one group. This application builds that cover, checks it, and tries to reduce the number of groups you need.

## The problem in one example

Choose **12 samples**, place them into groups of **6**, and require every **5-sample combination** to be fully contained in a group.

For this case, the app constructs **132 groups**. They cover all 792 five-sample targets and reach the theoretical lower bound.

| You choose | The app returns |
| --- | --- |
| Sample counts and overlap requirement | Selected sample labels and output groups |
| A valid set of five parameters | A complete coverage check |
| A run to inspect | Group count, lower bound and actual solve time |

## Try it

Requires **Python 3.10+ with Tkinter**. Uses the Python standard library.

```sh
python app.py
```

Enter the five parameters, select **Solve and Save**, and browse the result. Saved runs can be reopened, deleted individually or cleared together after confirmation.

| Parameter | What it controls | Range |
| --- | --- | --- |
| `m` | Total sample labels, numbered 1 to m | 45–54 |
| `n` | Distinct labels drawn for this run | 7–25 |
| `k` | Labels in each output group | 4–7 |
| `j` | Labels in each target combination | s ≤ j ≤ k ≤ n |
| `s` | Minimum overlap with an output group | 3–j |

The program automatically draws the labels. Changing their values changes the labels shown in the output; the covering problem is determined by `n`, `k`, `j` and `s`.

## What the result tells you

**Coverage verified** means every j-element target shares at least s elements with an output group.

**Proven optimal** means the group count also matches a valid lower bound. A feasible cover can still have room for improvement.

Two directly constructed cases reach their lower bounds:

| n | k | j | s | Groups | Result |
| --- | --- | --- | --- | --- | --- |
| 12 | 6 | 5 | 5 | 132 | Proven optimal |
| 13 | 6 | 5 | 5 | 245 | Proven optimal |

Results are paginated and saved in `results.db` beside the application. Each run is labeled `m-n-k-j-s-run_id`.

<details>
<summary><strong>How it finds a cover</strong></summary>

The solver combines cyclic and XOR symmetry constructions, greedy covering and time-bounded branch-and-bound. Small problems can search all candidates; larger problems improve a cover through exact repairs of smaller residual models.

For `(k,j,s)=(6,5,5)`, the 12-point small Witt design and its 13-point extension produce the two results above. These are generated from the construction.

The search budget is three seconds. Coverage verification and output preparation add to measured runtime. Large inputs may retain a larger initial cover when time runs out, and time-bounded results can vary between machines.

`app.py` contains the Tkinter interface and SQLite history. `solver.py` constructs, improves and verifies covers. The generated database is excluded from Git.

[Small Witt design construction, University of Bayreuth](https://mathe2.uni-bayreuth.de/discreta/M12/m12_design.html)

</details>

## Where it fits

Use the app to explore sample covering problems, compare group counts and inspect valid solutions. Many parameter combinations still have unproven optimality.
