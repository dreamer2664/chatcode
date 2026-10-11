#!/usr/bin/env python3
"""DPLL and WalkSAT for CNF satisfiability (6.825 Project 1a, solved in Python).

Representation: a clause is a frozenset of ints; literal l = variable v if l>0
else -v negated. A CNF sentence is a tuple of clauses.

Metric: per the assignment's collection rule, speed is reported as the
number of complete variable assignments examined (DPLL: leaves of the
search reached; WalkSAT: assignment candidates scored). Seeded; stdlib only.
"""
import random
import time

# ---------------------------------------------------------------- DPLL
class DPLL:
    def __init__(self):
        self.assignments_checked = 0

    def solve(self, clauses):
        self.assignments_checked = 0
        return self._dpll(set(), clauses)

    def _unit_propagate(self, clauses, assignment):
        changed = True
        clauses = set(clauses)
        while changed:
            changed = False
            for c in list(clauses):
                unassigned = [l for l in c if abs(l) not in assignment]
                satisfied = any(assignment.get(abs(l), None) == (l > 0) for l in c)
                if satisfied:
                    continue
                if not unassigned:
                    return None, None  # conflict
                if len(unassigned) == 1:  # forced literal
                    l = unassigned[0]
                    assignment[abs(l)] = l > 0
                    changed = True
        return clauses, assignment

    def _dpll(self, assignment, clauses):
        clauses, assignment = self._unit_propagate(clauses, dict(assignment))
        if clauses is None:
            return None
        # all clauses satisfied? (none left unsatisfied and no conflict)
        remaining = []
        for c in clauses:
            if not any(abs(l) in assignment and assignment[abs(l)] == (l > 0) for l in c):
                remaining.append(c)
        if not remaining:
            self.assignments_checked += 1
            return assignment
        # pure-literal elimination
        signs = {}
        for c in remaining:
            for l in c:
                if abs(l) not in assignment:
                    signs.setdefault(abs(l), set()).add(l > 0)
        for v, s in signs.items():
            if len(s) == 1:
                assignment[v] = True in s
        clauses2, assignment = self._unit_propagate(set(remaining), assignment)
        if clauses2 is None:
            return None
        remaining = [c for c in clauses2
                     if not any(abs(l) in assignment and assignment[abs(l)] == (l > 0) for l in c)]
        if not remaining:
            self.assignments_checked += 1
            return assignment
        # branch on the variable in the shortest clause
        v = min((abs(l) for c in remaining for l in c if abs(l) not in assignment),
                key=lambda x: (min(len(c) for c in remaining if x in [abs(l) for l in c]), x))
        for val in (True, False):
            a2 = dict(assignment); a2[v] = val
            self.assignments_checked += 1
            r = self._dpll(a2, clauses2)
            if r is not None:
                return r
        return None

# ---------------------------------------------------------------- WalkSAT
def walksat(clauses, max_flips=1000, p=0.5, rng=None):
    rng = rng or random.Random(0)
    vars_ = sorted({abs(l) for c in clauses for l in c})
    assignment = {v: rng.choice([True, False]) for v in vars_}
    checks = 0

    def broken(a):
        out = []
        for i, c in enumerate(clauses):
            if not any(a[abs(l)] == (l > 0) for l in c):
                out.append(i)
        return out

    for _ in range(max_flips):
        checks += 1
        unsat = broken(assignment)
        if not unsat:
            return assignment, checks
        c = clauses[rng.choice(unsat)]
        if rng.random() < p:  # random flip
            v = abs(rng.choice(list(c)))
        else:  # best flip: minimise newly broken clauses
            best, best_n = None, None
            for l in c:
                v = abs(l)
                assignment[v] = not assignment[v]
                n = len(broken(assignment))
                assignment[v] = not assignment[v]
                if best_n is None or n < best_n:
                    best, best_n = v, n
            v = best
        assignment[v] = not assignment[v]
    return None, checks

# ---------------------------------------------------------------- generator
def random_3sat(n_vars, m_clauses, rng):
    clauses = []
    for _ in range(m_clauses):
        vs = rng.sample(range(1, n_vars + 1), 3)
        clauses.append(frozenset(v if rng.random() < 0.5 else -v for v in vs))
    return tuple(clauses)

# ---------------------------------------------------------------- debug instances
DEBUG = {
    "satisfiable1":   ((1,),),
    "satisfiable2":   ((1, 2), (-1, 2), (1, -2)),
    "unsatisfiable1": ((1,), (-1,)),
    "unsatisfiable2": ((1, 2), (-1, 2), (1, -2), (-1, -2)),
}

def check_debug():
    lines = []
    d = DPLL()
    for name, cnf in DEBUG.items():
        a = d.solve(cnf)
        ok = "SAT" if a is not None else "UNSAT"
        lines.append(f"  {name:14s} -> {ok} (checks={d.assignments_checked}) "
                     f"assignment={dict(sorted(a.items())) if a else '{}'}")
    # walksat cross-check on the satisfiable ones
    for name in ("satisfiable1", "satisfiable2"):
        a, checks = walksat(DEBUG[name], max_flips=2000, rng=random.Random(7))
        lines.append(f"  walksat({name}) -> {'SAT' if a else 'fail'} (checks={checks})")
    return "\n".join(lines)

# ---------------------------------------------------------------- experiment
def experiment():
    out = []
    for n in (15, 20):
        for ratio in [x / 10 for x in range(30, 61, 5)]:
            m = int(round(ratio * n))
            row_d, row_w = [], []
            for trial in range(5):
                rng = random.Random(1000 * n + int(ratio * 10) * 10 + trial)
                cnf = random_3sat(n, m, rng)
                d = DPLL()
                t0 = time.perf_counter()
                a = d.solve(cnf)
                td = time.perf_counter() - t0
                row_d.append((d.assignments_checked, td, a is not None))
                aw, cw = walksat(cnf, max_flips=20000, p=0.5,
                                 rng=random.Random(5000 + trial))
                row_w.append((cw, aw is not None))
            d_checks = [r[0] for r in row_d]
            d_sat = sum(r[2] for r in row_d)
            w_checks = [r[0] for r in row_w]
            w_sat = sum(r[1] for r in row_w)
            out.append((n, ratio, m, d_sat, sum(d_checks) / 5, w_sat, sum(w_checks) / 5))
    return out

if __name__ == "__main__":
    import sys
    print("debug instances (DPLL, exact):")
    print(check_debug())
    print("\nexperiment: n_vars, ratio, m_clauses, dpll_sat/5, avg_dpll_checks, "
          "walksat_sat/5, avg_walksat_checks")
    for row in experiment():
        print("  n=%-3d r=%.1f m=%-3d | DPLL sat %d/5 checks %10.0f | "
              "WalkSAT sat %d/5 checks %10.0f" % row)
