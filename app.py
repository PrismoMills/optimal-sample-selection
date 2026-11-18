"""Tkinter interface and SQLite storage for the sample selection system."""

import json
import random
import sqlite3
import time
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import messagebox, ttk

from solver import solve_timed, validate


class History:
    def __init__(self, database):
        self.connection = sqlite3.connect(database)
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parameters TEXT NOT NULL,
                samples TEXT NOT NULL,
                groups_json TEXT NOT NULL,
                group_count INTEGER NOT NULL,
                elapsed REAL NOT NULL,
                lower_bound INTEGER
            )
        """)
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(runs)")}
        if "lower_bound" not in columns:
            self.connection.execute("ALTER TABLE runs ADD COLUMN lower_bound INTEGER")

    def save(self, parameters, samples, groups, elapsed, lower_bound):
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO runs (parameters, samples, groups_json, group_count, elapsed, lower_bound) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (parameters, json.dumps(samples), json.dumps(groups), len(groups), elapsed, lower_bound),
            )
        return cursor.lastrowid

    def list(self):
        return self.connection.execute(
            "SELECT id, parameters, group_count FROM runs ORDER BY id DESC"
        ).fetchall()

    def load(self, run_id):
        row = self.connection.execute(
            "SELECT samples, groups_json, elapsed, lower_bound FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
        return json.loads(row[0]), json.loads(row[1]), row[2], row[3]

    def delete(self, run_id):
        with self.connection:
            self.connection.execute("DELETE FROM runs WHERE id = ?", (run_id,))

    def clear(self):
        with self.connection:
            self.connection.execute("DELETE FROM runs")


def calculate(samples, k, j, s):
    start = time.perf_counter()
    solution = solve_timed(samples, k, j, s)
    return solution.groups, time.perf_counter() - start, solution.lower_bound


class Application:
    def __init__(self, root, history):
        self.root = root
        self.history = history
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.future = None
        self.groups = []
        self.page = 0
        root.title("Optimal Sample Selection System")
        root.geometry("840x620")
        root.minsize(700, 530)
        root.protocol("WM_DELETE_WINDOW", self.close)
        frame = ttk.Frame(root, padding=16)
        frame.pack(fill="both", expand=True)

        inputs = ttk.Frame(frame)
        inputs.pack(fill="x")
        self.values = []
        for name, default in zip("mnkjs", (45, 9, 6, 5, 4)):
            ttk.Label(inputs, text=name).pack(side="left", padx=(0, 4))
            value = tk.StringVar(value=str(default))
            self.values.append(value)
            ttk.Entry(inputs, width=5, textvariable=value).pack(side="left", padx=(0, 14))
        self.run_button = ttk.Button(inputs, text="Solve and Save", command=self.start)
        self.run_button.pack(side="right")

        self.status = tk.StringVar(value="Enter parameters to solve, or view a saved run.")
        ttk.Label(frame, textvariable=self.status).pack(anchor="w", pady=10)

        controls = ttk.Frame(frame)
        controls.pack(fill="x")
        ttk.Label(controls, text="History").pack(side="left")
        self.runs = ttk.Combobox(controls, state="readonly", width=34)
        self.runs.pack(side="left", padx=8)
        ttk.Button(controls, text="View", command=self.show_saved).pack(side="left", padx=4)
        ttk.Button(controls, text="Delete", command=self.delete_saved).pack(side="left", padx=4)
        self.clear_history_button = ttk.Button(controls, text="Clear All", command=self.clear_history)
        self.clear_history_button.pack(side="left", padx=4)

        self.output = tk.Text(frame, height=17, wrap="word", state="disabled")
        self.output.pack(fill="both", expand=True, pady=(10, 6))
        pages = ttk.Frame(frame)
        pages.pack(fill="x")
        self.prev = ttk.Button(pages, text="Previous", command=lambda: self.show_page(self.page-1))
        self.next = ttk.Button(pages, text="Next", command=lambda: self.show_page(self.page+1))
        self.prev.pack(side="left")
        self.next.pack(side="right")
        self.page_info = tk.StringVar()
        ttk.Label(pages, textvariable=self.page_info).pack()
        self.samples = []
        self.refresh()
        self.show_page(0)

    def start(self):
        try:
            m, n, k, j, s = (int(value.get()) for value in self.values)
            validate(m, n, k, j, s)
            samples = sorted(random.sample(range(1, m+1), n))
        except ValueError as error:
            messagebox.showerror("Invalid Parameters", str(error))
            return
        parameters = f"{m}-{n}-{k}-{j}-{s}"
        self.run_button.state(["disabled"])
        self.status.set("Solving and verifying coverage...")
        self.future = self.executor.submit(calculate, samples, k, j, s)
        self.root.after(100, self.finish, parameters, samples)

    def finish(self, parameters, samples):
        if not self.future.done():
            self.root.after(100, self.finish, parameters, samples)
            return
        try:
            groups, elapsed, lower_bound = self.future.result()
            run_id = self.history.save(parameters, samples, groups, elapsed, lower_bound)
            self.refresh(run_id)
            self.display(samples, groups, elapsed, lower_bound)
        except (ValueError, RuntimeError, sqlite3.Error) as error:
            self.status.set("Run failed.")
            messagebox.showerror("Run Failed", str(error))
        finally:
            self.future = None
            self.run_button.state(["!disabled"])

    def refresh(self, selected=None):
        rows = self.history.list()
        self.ids = [run_id for run_id, _, _ in rows]
        self.runs["values"] = [f"{parameters}-{run_id}  |  {count} groups" for run_id, parameters, count in rows]
        if rows:
            self.runs.current(self.ids.index(selected) if selected in self.ids else 0)
        else:
            self.runs.set("")
        self.clear_history_button.state(["!disabled"] if rows else ["disabled"])

    def show_saved(self):
        index = self.runs.current()
        if index >= 0:
            self.display(*self.history.load(self.ids[index]))

    def delete_saved(self):
        index = self.runs.current()
        if index >= 0 and messagebox.askyesno("Delete Run", f"Delete {self.runs.get()}?"):
            self.history.delete(self.ids[index])
            self.reset_history_display("Run deleted.")

    def clear_history(self):
        if self.ids and messagebox.askyesno(
            "Clear History", "Delete all saved runs? This action cannot be undone.", parent=self.root
        ):
            self.history.clear()
            self.reset_history_display("All history cleared.")

    def reset_history_display(self, status):
        self.refresh()
        self.samples, self.groups = [], []
        self.status.set(status)
        self.show_page(0)

    def display(self, samples, groups, elapsed, lower_bound):
        self.samples, self.groups = samples, groups
        quality = ""
        if lower_bound is not None:
            quality = " | Proven optimal" if lower_bound == len(groups) else f" | Feasible (lower bound: {lower_bound} groups)"
        self.status.set(f"Coverage verified | {len(groups)} groups{quality} | Actual solve time: {elapsed:.4f} s")
        self.show_page(0)

    def show_page(self, page):
        page_size = 100
        pages = max(1, (len(self.groups) + page_size - 1) // page_size)
        self.page = page = max(0, min(page, pages-1))
        start = page * page_size
        text = ""
        if self.samples:
            text = "Selected samples: " + "  ".join(f"{x:02d}" for x in self.samples) + "\n\n"
            text += "\n".join(
                f"{index:>5}.  " + "  ".join(f"{x:02d}" for x in group)
                for index, group in enumerate(self.groups[start:start+page_size], start+1)
            )
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")
        self.page_info.set(f"Page {page+1} / {pages}")
        self.prev.state(["!disabled"] if page > 0 else ["disabled"])
        self.next.state(["!disabled"] if page+1 < pages else ["disabled"])

    def close(self):
        if self.future is not None:
            messagebox.showinfo("Solving", "Please wait for the current run to finish before closing.")
            return
        self.executor.shutdown(wait=False)
        self.history.connection.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    Application(root, History(Path(__file__).with_name("results.db")))
    root.mainloop()
