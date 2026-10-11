#!/usr/bin/env python3
"""Held-out replay of S6 phase 1+2 (scott's review tool for superocr PR #12).

Barry's gains (+1.6 combine, +5.4 augment) come from picking the per-family
winner ON the same seed-7 images the numbers are reported on. This replays the
SAME selection rule but evaluates the winners on a DIFFERENT seed (default 3),
so the gap between in-sample and held-out gain is measured, not argued.

    python3 heldout_replay.py --count 3 --eval-seed 3
"""
import json, time, sys
from pathlib import Path
import generator as G

import augment_search as A
import ensemble_select as E
from readers.glyphcnn import GlyphCNN

W = json.loads(Path("reports/augment-search.json").read_text())
P = json.loads(Path("reports/ensemble-select.json").read_text())

def exact_rate(fam, seed, n, fn):
    ok = 0
    for i in range(n):
        img, label = G.generate_one(fam, seed=seed, index=i)
        try:
            ok += fn(img) == label
        except Exception:
            pass
    return ok

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=3)
    ap.add_argument("--eval-seed", type=int, default=3)
    ap.add_argument("--phase", default="both", choices=("augment", "ensemble", "both"))
    a = ap.parse_args()
    n, es = a.count, a.eval_seed
    out = {"eval_seed": es, "count": n, "augment": {}, "ensemble": {}}

    if a.phase in ("augment", "both"):
        base_tot = win_tot = tot = 0
        fams_checked = 0
        for row in W["per_family"]:
            fam, win = row["family"], row["winner"]
            ident = exact_rate(fam, es, n, lambda im: A.B.read_text(im)[0])
            trans = dict(A.AUGS)[win]
            w = exact_rate(fam, es, n, lambda im: A.B.read_text(trans(im))[0])
            base_tot += ident; win_tot += w; tot += n; fams_checked += 1
            out["augment"][fam] = {"seed7_pick": win, "eval_identity": ident,
                                   "eval_winner": w, "n": n}
            print(f"aug  {fam:14s} seed7 pick={win:12s} eval: identity {ident}/{n} winner {w}/{n}")
        g_base = base_tot / tot * 100; g_win = win_tot / tot * 100
        out["augment_totals"] = {"identity_pct": round(g_base,1), "winner_pct": round(g_win,1),
                                 "gain_points": round(g_win-g_base,1), "n": tot}
        print(f"AUGMENT held-out(seed {es}): identity {g_base:.1f}% -> winner-following {g_win:.1f}%  gain {g_win-g_base:+.1f} pts (in-sample claim: +{W['gain_points']})")

    if a.phase in ("ensemble", "both"):
        net = GlyphCNN.load("models/glyphcnn.npz")
        def cnn(im): return E.cnn_read(im, net)
        def strategy(im, fam): return E.strategy_read(im, family=fam)
        base_tot = win_tot = tot = 0
        for row in P["per_family"]:
            fam, win = row["family"], row["winner"]
            cb = exact_rate(fam, es, n, E.classic_read)
            if win == "classic": w = cb
            elif win == "cnn": w = exact_rate(fam, es, n, cnn)
            else: w = exact_rate(fam, es, n, lambda im, f=fam: strategy(im, f))
            base_tot += cb; win_tot += w; tot += n
            out["ensemble"][fam] = {"seed7_pick": win, "eval_classic": cb, "eval_winner": w, "n": n}
            print(f"ens  {fam:14s} seed7 pick={win:8s} eval: classic {cb}/{n} winner-following {w}/{n}")
        g_base = base_tot / tot * 100; g_win = win_tot / tot * 100
        out["ensemble_totals"] = {"classic_pct": round(g_base,1), "winner_pct": round(g_win,1),
                                  "gain_points": round(g_win-g_base,1), "n": tot}
        print(f"ENSEMBLE held-out(seed {es}): classic {g_base:.1f}% -> winner-following {g_win:.1f}%  gain {g_win-g_base:+.1f} pts (in-sample claim: +{P['best_of_combined'] and ''}{1.6})")

    Path("reports/heldout-replay.json").write_text(json.dumps(out, indent=1))
    print("written reports/heldout-replay.json")

if __name__ == "__main__":
    sys.exit(main())
