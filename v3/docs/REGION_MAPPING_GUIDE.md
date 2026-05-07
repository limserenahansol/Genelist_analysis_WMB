# Region Mapping Guide

Before computing GPCRs, confirm exact Allen region labels.

| User label | Intended mouse region | Risk | Required check |
|---|---|---|---|
| BMAp | Basomedial amygdalar nucleus, posterior part | Moderate | Confirm Allen acronym/name and spatial cells in posterior BMA |
| LM | Lateral mammillary nucleus/body | High | Confirm LM is not lateral/medial visual area or another acronym |
| RE | Nucleus reuniens | Moderate | Confirm midline thalamic ROI and avoid neighboring thalamic/reticular cells |
| CP | Caudoputamen | Low | Confirm striatal subregion and D1/D2/patch/matrix annotations |
| ORBm | Orbital area, medial part | Moderate | Confirm cortical area and layer labels |
| AId | Agranular insular area, dorsal part | Moderate | Confirm original `Ald` is actually `AId` |

## Region mapping method

1. Load Allen region/ROI metadata.
2. Search both acronym and full name.
3. Inspect all matching labels.
4. Use MERFISH/CCF spatial coordinates to identify cells in the target region.
5. Join MERFISH cells to taxonomy cluster/supertype/subclass.
6. Export `Region_Mapping_Final.csv`.

## Do not finalize probes if

```text
LM is still ambiguous.
Ald vs AId is not confirmed.
BMAp clusters are mixed with MEA/BMA/BLA without spatial validation.
RE includes reticular/inhibitory thalamic exclusion populations as target cells.
```
