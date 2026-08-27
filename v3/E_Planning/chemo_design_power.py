#!/usr/bin/env python
"""Sample sizes for the three claims in the chemogenetics hypothesis.

The hypothesis has three parts and they do NOT cost the same number of mice:

  H1  DCZ reduces seeking in Active hM4Di mice          -> simple effect
  H2  DCZ does nothing in Active mCherry mice           -> ligand control, equivalence
  H3  the effect is Active-specific, absent in Passive  -> Group x Drug interaction

H3 is the claim the deck has to be honest about, because a between-group
comparison of within-subject effects always costs more than the simple effect it
is built from.

Two test designs are compared for the relapse session, because a cue-induced
seeking test is extinction-like: testing itself lowers seeking, so a within-
subject DCZ/vehicle crossover confounds drug with test order.
"""
from __future__ import annotations

from scipy import stats

ALPHA = 0.05
TARGET = 0.80


def power_paired(n: int, dz: float) -> float:
    df = n - 1
    crit = stats.t.ppf(1 - ALPHA / 2, df)
    ncp = dz * n**0.5
    return 1 - stats.nct.cdf(crit, df, ncp) + stats.nct.cdf(-crit, df, ncp)


def power_two_sample(n: int, d: float) -> float:
    df = 2 * n - 2
    crit = stats.t.ppf(1 - ALPHA / 2, df)
    ncp = d * (n / 2) ** 0.5
    return 1 - stats.nct.cdf(crit, df, ncp) + stats.nct.cdf(-crit, df, ncp)


def smallest_n(fn, eff: float, cap: int = 200) -> int | None:
    for n in range(3, cap + 1):
        if fn(n, eff) >= TARGET:
            return n
    return None


def main() -> None:
    effects = (0.8, 1.0, 1.2, 1.5)

    print("n per group for 80% power, two-tailed alpha=0.05\n")
    print(f"{'effect size':<14}{'H1 simple effect':<20}{'H3 interaction':<18}{'cost of H3'}")
    print(f"{'':<14}{'(paired, crossover)':<20}{'(between groups)':<18}")
    for eff in effects:
        n1 = smallest_n(power_paired, eff)
        n3 = smallest_n(power_two_sample, eff)
        ratio = f"{n3 / n1:.1f}x" if n1 and n3 else "-"
        print(f"dz = d = {eff:<6}{str(n1):<20}{str(n3):<18}{ratio}")

    print("\nIf the relapse test must be a SINGLE session (extinction-like), the")
    print("drug factor is between-subject too, so even H1 costs the two-sample n:")
    for eff in effects:
        n = smallest_n(power_two_sample, eff)
        print(f"  d = {eff}:  n = {n} per group")

    print("\nCohort arithmetic for the recommended design (ORBm, one region)")
    groups = [
        "Active  hM4Di  DCZ",
        "Active  hM4Di  vehicle",
        "Active  mCherry DCZ",
        "Passive hM4Di  DCZ",
        "Passive hM4Di  vehicle",
    ]
    for n in (8, 10, 12):
        total = n * len(groups)
        with_attrition = round(total * 1.25)
        print(f"  n={n:<3} {len(groups)} groups -> {total:>3} mice, "
              f"{with_attrition:>3} ordered at 25% attrition")

    print("\nWhat the pilot buys: variance, not a p-value.")
    print("  With n=4 per group the CI on a standardised effect is roughly +/-1.0,")
    print("  which is too wide to size a cohort from a point estimate. The pilot's")
    print("  job is the tdTomato->hM4Di conversion rate and the DCZ->Fos suppression,")
    print("  both of which are proportions measured over hundreds of cells per mouse.")


if __name__ == "__main__":
    main()
