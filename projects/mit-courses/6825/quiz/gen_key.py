#!/usr/bin/env python3
"""Independent key generation for attempt-2 questions (M4).

Each key is computed here from first principles (not copied from any
answer sheet), so attempt 2 has two independent derivations: the key
from this script, and the answer given at test time. If they disagree,
a real mistake exists somewhere and the mismatch is the signal."""
import json
from pathlib import Path

# q1 search: optimal A* cost on S-A(2), S-B(1), A-C(2), B-C(4), C-G(2)
edges = {"S": {"A": 2, "B": 1}, "A": {"C": 2}, "B": {"C": 4}, "C": {"G": 2}}
import heapq
def dijkstra(src="S", dst="G"):
    dist = {src: 0}; pq = [(0, src)]; seen = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in seen: continue
        seen.add(u)
        for v, c in edges.get(u, {}).items():
            if d + c < dist.get(v, 1e9):
                dist[v] = d + c; heapq.heappush(pq, (dist[v], v))
    return dist[dst]
q1 = str(dijkstra())

# q2 games: minimax of root MAX over MIN nodes B{8,4}, C{3,7}
q2 = str(max(min(8, 4), min(3, 7)))

# q3 logic: resolution steps to empty clause from
# (~P(x)vQ(x)), (~Q(y)vR(y)), P(a), goal R(a) [negated: ~R(a)]
# P(a)+clause1 {x/a} -> Q(a);  Q(a)+clause2 {y/a} -> R(a);  R(a)+~R(a) -> []
q3 = "3"

# q4 probability: chain X->Y->Z, binary
px = 0.3
py = px * 0.8 + (1 - px) * 0.2
pz = py * 0.7 + (1 - py) * 0.1
q4 = f"{pz:.3f}"

# q5 learning: perceptron one epoch, A(1,2)+ B(1,-1)- C(1,0.5)-
w = [0.0, 0.0]
data = [((1, 2), 1), ((1, -1), -1), ((1, 0.5), -1)]
for x, t in data:
    dot = w[0] * x[0] + w[1] * x[1]
    if t * dot <= 0:
        w = [w[0] + t * x[0], w[1] + t * x[1]]
q5 = f"{w[0]:g},{w[1]:g}"

key = {"b-search-1": q1, "b-games-1": q2, "b-logic-1": q3,
       "b-prob-1": q4, "b-learn-1": q5}
print(json.dumps(key, indent=2))
