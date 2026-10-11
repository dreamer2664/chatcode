#!/usr/bin/env python3
"""Independent keys for the 6.036 blind battery (M4+, t-20261011-8577).

Every key is computed here from scratch (closed forms, no reference to the
notes' text or to any answer sheet), so the battery has two independent
derivations: these keys, and the answers written at test time from the
questions alone."""
import json
import math

# b1: least squares w1 for (0,1),(1,3),(2,4) via the normal equations
xs, ys = [0.0, 1.0, 2.0], [1.0, 3.0, 4.0]
n = len(xs)
sxx, sx, sy, sxy = (sum(a * b for a, b in zip(xs, xs)), sum(xs), sum(ys),
                    sum(a * b for a, b in zip(xs, ys)))
# [[sxx, sx],[sx, n]] w = [sxy, sy]
det = sxx * n - sx * sx
w1 = (sxy * n - sx * sy) / det
q1 = f"{w1:.1f}"

# b2: kernel trick K(x,z)=(x.z+1)^2, x=(1,2), z=(0,1)
q2 = str((1 * 0 + 2 * 1 + 1) ** 2)

# b3: entropy of 4/10 vs 6/10
p = 0.4
q3 = f"{-(p * math.log2(p) + (1 - p) * math.log2(1 - p)):.3f}"

# b4: one GD step for w1 from (0,0), lr 0.1, grad (2/3) X^T (Xw - y)
# gradient at w=0: (2/3) * (sum x_i*(0 - y_i), ...) -> w1-comp = (2/3)*(-sxy)
gw1 = (2.0 / 3.0) * (-sxy)
q4 = f"{0.0 - 0.1 * gw1:.3f}"

# b5: ridge w1, lambda=1: solve (X^T X + I) w = X^T y in 2D
a11, a12, a22 = sxx + 1, sx, n + 1
b1v, b2v = sxy, sy
det2 = a11 * a22 - a12 * a12
rw1 = (b1v * a22 - a12 * b2v) / det2
q5 = f"{rw1:.3f}"

print(json.dumps({"b6036-1": q1, "b6036-2": q2, "b6036-3": q3,
                  "b6036-4": q4, "b6036-5": q5}, indent=2))
