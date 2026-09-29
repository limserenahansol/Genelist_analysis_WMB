# Validation of the tdTom candidate-subtype module

These are software-validation results, not biological findings.

## Positive synthetic control

A four-mouse, 640-cell dataset contained one planted tdTom-enriched subtype with three non-state
markers. The module recovered three stable markers and one candidate cluster. The cluster appeared
in all four mice, had median log2 tdTom odds of 12.82, recovered at 0.98 and 0.99 across the two
alternate resolutions, and had leave-one-mouse-out marker AUC 1.00 in all four mice.

## Shuffled-reporter negative control

The same expression data were retained, but tdTom counts were shuffled within each mouse. The module
then returned zero stable tdTom-associated identity markers, zero candidate clusters, and
`no_reproducible_reporter_subtype_evidence`.

## Current pilot

The current 247-feature pilot returns `SKIPPED.md` because `tdTomato` is absent. This is the expected
result; no reporter conclusion can be drawn from that pilot.

## Remaining biological validation

Real candidate calls still require spatial coherence, comparison against an external reference atlas,
and orthogonal validation before naming a new subtype. The targeted panel can only test genes that it
measures, so a negative screen cannot exclude an unmeasured subtype.
