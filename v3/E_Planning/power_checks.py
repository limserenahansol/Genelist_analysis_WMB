#!/usr/bin/env python
"""Sample-size arithmetic behind the group sizes quoted in the planning deck.

Two separate questions, which the deck keeps apart on purpose:

  Experiment 1 (Xenium) is a between-group comparison of Active vs Passive with
  very few mice, so the binding constraint is the exact rank-sum null. At 3 vs 3
  no result of any magnitude can reach p<0.05, which is the argument for n=4.

  Experiment 2 (chemogenetics) uses a within-subject drug crossover, so the
  relevant curve is paired-t power.
"""
from __future__ import annotations

from math import comb

from scipy import stats

ALPHA = 0.05


def ranksum_floor(n_max: int = 6) -> None:
    """Smallest two-tailed Mann-Whitney p attainable at n vs n (perfect separation)."""
    print("Exact rank-sum floor, n vs n, two-tailed")
    print("  n     best possible p    orderings   can reach p<0.05?")
    for n in range(3, n_max + 1):
        x, y = list(range(1, n + 1)), list(range(n + 1, 2 * n + 1))
        p = stats.mannwhitneyu(x, y, alternative="two-sided").pvalue
        print(f"  {n}     {p:>8.4f}         {comb(2 * n, n):>6}      "
              f"{'yes' if p < ALPHA else 'NO'}")


def paired_power(ns=(3, 4, 5, 6, 8, 10, 12), dzs=(0.8, 1.0, 1.2, 1.5, 2.0)) -> None:
    """Power of a two-tailed paired t-test, i.e. the within-subject DCZ crossover."""
    print(f"\nPaired t-test power, two-tailed alpha={ALPHA}")
    print("  n   " + "".join(f"dz={d:<7}" for d in dzs))
    for n in ns:
        df = n - 1
        crit = stats.t.ppf(1 - ALPHA / 2, df)
        cells = []
        for dz in dzs:
            ncp = dz * n**0.5
            power = 1 - stats.nct.cdf(crit, df, ncp) + stats.nct.cdf(-crit, df, ncp)
            cells.append(f"{power * 100:>4.0f}%     ")
        print(f"  {n:<3} " + "".join(cells))


def tagged_cell_yield() -> None:
    """Order-of-magnitude check that cells, unlike mice, are not the limiting factor."""
    cells_per_section = 130_870  # 10x fresh-frozen mouse brain coronal demo, full section
    roi_frac = 0.02             # ORBm or BMAp as a fraction of a coronal section
    trap_frac = 0.03            # tdTomato+ fraction among ROI neurons
    roi = cells_per_section * roi_frac
    print("\nTagged-cell yield (why the cell-level census is not n-limited)")
    print(f"  cells per full coronal section      {cells_per_section:>8,}")
    print(f"  cells inside a ~2% ROI              {roi:>8,.0f}")
    print(f"  tdTomato+ at ~3% TRAP density       {roi * trap_frac:>8,.0f}  per section")
    print(f"  pooled over 4 mice x 3 sections     {roi * trap_frac * 12:>8,.0f}  tagged cells")


if __name__ == "__main__":
    ranksum_floor()
    paired_power()
    tagged_cell_yield()
