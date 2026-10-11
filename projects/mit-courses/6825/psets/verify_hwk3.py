#!/usr/bin/env python3
"""Verification arithmetic for hwk3.md (6.825 HW3), stdlib + numpy-free:
solves the Bellman linear systems by Gaussian elimination and runs value
iteration exactly as written in the notes. Run: python3 verify_hwk3.py
Expected output matches every number quoted in hwk3.md."""

def solve(A, b):
    """Gaussian elimination with partial pivoting; returns x with A x = b."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[piv] = M[piv], M[col]
        for r in range(col + 1, n):
            f = M[r][col] / M[col][col]
            for c in range(col, n + 1):
                M[r][c] -= f * M[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (M[r][n] - sum(M[r][c] * x[c] for c in range(r + 1, n))) / M[r][r]
    return x

def chain_values(gamma):
    # (I - gamma*P) v = R
    P = [[0.8, 0.1, 0.1], [0.2, 0.1, 0.7], [0.9, 0.1, 0.0]]
    R = [1.0, 3.0, -1.0]
    A = [[(1 if i == j else 0) - gamma * P[i][j] for j in range(3)] for i in range(3)]
    return solve(A, R)

P1 = [[0.8, 0.1, 0.1], [0.2, 0.1, 0.7], [0.9, 0.1, 0.0]]
P2 = [[0.1, 0.1, 0.8], [0.7, 0.1, 0.2], [0.9, 0.0, 0.1]]
R = [1.0, 3.0, -1.0]

def vi(gamma, iters):
    V = [0.0, 0.0, 0.0]
    table = []
    for _ in range(iters):
        V = [R[i] + gamma * max(sum(P1[i][j] * V[j] for j in range(3)),
                                sum(P2[i][j] * V[j] for j in range(3)))
             for i in range(3)]
        table.append(tuple(round(v, 4) for v in V))
    return V, table

def q1_counts():
    rows = [(1,1,1,.6),(0,0,0,.3),(0,0,1,.7),(0,1,1,.9),(1,1,1,.6),
            (0,0,0,.3),(1,0,1,.5),(1,1,0,.4),(0,1,1,.9),(0,0,1,.7),
            (0,0,1,.7),(0,1,0,.1),(0,1,1,.9),(0,1,1,.9),(1,0,0,.2),
            (1,0,1,.5),(1,1,1,.6)]
    n = len(rows)
    E_A = sum(1 for r in rows if r[0] == 1)
    E_DA = sum(r[3] for r in rows if r[0] == 1)
    E_D = sum(r[3] for r in rows)
    E_BD = sum(r[3] for r in rows if r[1] == 1)
    E_CD = sum(r[3] for r in rows if r[2] == 1)
    return dict(n=n, E_A=E_A, E_DA=E_DA, E_D=E_D, E_BD=E_BD, E_CD=E_CD,
                PrA=E_A / n, PrDA=E_DA / E_A, PrBD=E_BD / E_D, PrCD=E_CD / E_D)

if __name__ == "__main__":
    import math
    c = q1_counts()
    print("Q1:", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in c.items()})
    print("Q3 gamma=0.9:", [round(v, 3) for v in chain_values(0.9)])
    print("Q3 gamma=0.1:", [round(v, 3) for v in chain_values(0.1)])
    V9, t9 = vi(0.9, 10)
    print("Q4 gamma=0.9 iter10:", [round(v, 4) for v in V9])
    V1, t1 = vi(0.1, 10)
    print("Q4 gamma=0.1 iter10:", [round(v, 4) for v in V1])
    V9c, _ = vi(0.9, 200)
    print("Q4 gamma=0.9 converged(200):", [round(v, 3) for v in V9c])
    # policy check at convergence
    for i in range(3):
        a1 = sum(P1[i][j] * V9c[j] for j in range(3))
        a2 = sum(P2[i][j] * V9c[j] for j in range(3))
        print(f"  s{i+1}: a1={a1:.4f} a2={a2:.4f} -> action {1 if a1 >= a2 else 2}")
    u = lambda x: math.sqrt(x + 20)
    print("Q5 EV:", round(.7*2 + .3*(-2), 3), round(.2*20 + .8*(-2), 3),
          round(.7*0 + .2*9 + .1*(-2), 3))
    print("Q5 EU:", round(.7*u(2) + .3*u(-2), 3), round(.2*u(20) + .8*u(-2), 3),
          round(.7*u(0) + .2*u(9) + .1*u(-2), 3), "no-bet:", round(u(0), 3))
