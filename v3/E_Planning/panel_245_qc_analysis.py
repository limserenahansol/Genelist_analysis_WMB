"""Technical QC for the 245-gene ORBm/BMAp standalone Xenium panel.

Produces deterministic CSV/JSON inputs for the final QC workbook.  It does not
modify the order workbook.  Evidence streams are kept separate:

1. 10x Xenium v1 designability against the official mouse 2020-A list.
2. Current NCBI mouse gene symbols and gene types.
3. Transcript counts in the exact 10x mouse 2020-A GTF.
4. Allen WMB-10X detectability for all endogenous panel genes.
5. A whole-transcriptome marker screen against the 20 planned anchor subclasses.

The two exogenous targets (tdTomato and iCre) are reported separately because
they require exact construct FASTA files and 10x Advanced Custom Design.
"""
from __future__ import annotations

import gzip
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
SRC = OUT / "panel_245_qc_sources"
QC = OUT / "panel_245_qc_data"
QC.mkdir(parents=True, exist_ok=True)

PANEL = OUT / "PANEL_C_expanded_standalone_245genes.xlsx"
DETECT = OUT / "allen_detectability_all_candidates.xlsx"
GTF = SRC / "refdata-gex-mm10-2020-A" / "genes" / "genes.gtf"
DESIGNABLE = SRC / "xenium_v1_designable_2020A.csv"
NO_PROBE = SRC / "xenium_v1_mouse_no_probe_2020A.csv"
NCBI = SRC / "Mus_musculus.gene_info.gz"
GENOME = OUT / "allen_genomewide"

TRANSGENES = {"tdTomato", "iCre"}
MIN_SPEC = 0.5
MIN_PCT = 25.0
MIN_MEAN = 0.5


def parse_attrs(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in text.strip().rstrip(";").split(";"):
        item = item.strip()
        if not item:
            continue
        key, _, value = item.partition(" ")
        out[key] = value.strip().strip('"')
    return out


def load_gtf(panel_genes: set[str]) -> pd.DataFrame:
    """Return one row per requested symbol from the 10x 2020-A GTF."""
    ids: dict[str, set[str]] = defaultdict(set)
    types: dict[str, set[str]] = defaultdict(set)
    tx: dict[str, set[str]] = defaultdict(set)
    tx_types: dict[str, set[str]] = defaultdict(set)
    with GTF.open("rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9 or fields[2] not in {"gene", "transcript"}:
                continue
            a = parse_attrs(fields[8])
            gene = a.get("gene_name", "")
            if gene not in panel_genes:
                continue
            if a.get("gene_id"):
                ids[gene].add(a["gene_id"].split(".")[0])
            if a.get("gene_type"):
                types[gene].add(a["gene_type"])
            if fields[2] == "transcript":
                if a.get("transcript_id"):
                    tx[gene].add(a["transcript_id"])
                if a.get("transcript_type"):
                    tx_types[gene].add(a["transcript_type"])
    return pd.DataFrame(
        [
            {
                "gene": g,
                "gtf_ensembl_ids": "; ".join(sorted(ids[g])),
                "gtf_gene_types": "; ".join(sorted(types[g])),
                "gtf_transcript_count": len(tx[g]),
                "gtf_transcript_types": "; ".join(sorted(tx_types[g])),
            }
            for g in sorted(panel_genes)
        ]
    )


def load_ncbi(panel_genes: set[str]) -> pd.DataFrame:
    d = pd.read_csv(NCBI, sep="\t", dtype=str)
    d = d[d["Symbol"].isin(panel_genes)].copy()
    keep = ["GeneID", "Symbol", "description", "type_of_gene", "Nomenclature_status", "Modification_date"]
    d = d[keep].rename(
        columns={
            "Symbol": "gene",
            "GeneID": "ncbi_gene_id",
            "description": "ncbi_description",
            "type_of_gene": "ncbi_gene_type",
            "Nomenclature_status": "ncbi_nomenclature_status",
            "Modification_date": "ncbi_modified",
        }
    )
    return d


def load_10x(panel_genes: set[str]) -> pd.DataFrame:
    yes = pd.read_csv(DESIGNABLE)
    yes = yes[(yes["Species"] == "Mus musculus") & yes["Gene symbol"].isin(panel_genes)].copy()
    agg = yes.groupby("Gene symbol", as_index=False).agg(
        tenx_ensembl_ids=("Ensembl ID", lambda s: "; ".join(sorted(set(s.astype(str))))),
        tenx_designable_matches=("Ensembl ID", "nunique"),
    ).rename(columns={"Gene symbol": "gene"})
    no = pd.read_csv(NO_PROBE)
    no_set = set(no["gene_name"].astype(str))
    agg["tenx_on_no_probe_list"] = agg["gene"].isin(no_set)
    return agg


def merge_genomewide(anchors: pd.DataFrame) -> tuple[np.ndarray, list[str], dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    labels = anchors["allen_subclass_anchor"].tolist()
    nnz: dict[str, np.ndarray] = {}
    total: dict[str, np.ndarray] = {}
    ncell = {x: 0 for x in labels}
    genes: np.ndarray | None = None
    for f in sorted(GENOME.glob("*.npz")):
        z = np.load(f, allow_pickle=True)
        if genes is None:
            genes = z["genes"].astype(str)
            for lab in labels:
                nnz[lab] = np.zeros(len(genes), dtype=np.float64)
                total[lab] = np.zeros(len(genes), dtype=np.float64)
        elif not np.array_equal(genes, z["genes"].astype(str)):
            raise RuntimeError(f"gene order mismatch in {f.name}")
        shard_labels = z["subclass_labels"].astype(str)
        pos = {x: i for i, x in enumerate(shard_labels)}
        for lab in labels:
            if lab not in pos:
                continue
            i = pos[lab]
            nnz[lab] += z["subclass_nnz"][i]
            total[lab] += z["subclass_sum"][i]
            ncell[lab] += int(z["subclass_n"][i])
    if genes is None:
        raise RuntimeError("no genome-wide shard files")
    return genes, labels, nnz, total, ncell


def genomewide_check(panel_genes: set[str], anchors: pd.DataFrame) -> pd.DataFrame:
    genes, labels, nnz, total, ncell = merge_genomewide(anchors)
    pct = {lab: 100.0 * nnz[lab] / max(1, ncell[lab]) for lab in labels}
    mean = {lab: total[lab] / max(1, ncell[lab]) for lab in labels}
    rows: list[dict[str, object]] = []
    for region, sub in anchors.groupby("region", sort=False):
        region_labels = sub["allen_subclass_anchor"].tolist()
        for lab in region_labels:
            others = [x for x in region_labels if x != lab]
            competitor = np.max(np.vstack([mean[x] for x in others]), axis=0)
            spec = mean[lab] - competitor
            passing = (spec >= MIN_SPEC) & (pct[lab] >= MIN_PCT) & (mean[lab] >= MIN_MEAN)
            idx = np.flatnonzero(passing)
            for i in idx:
                rows.append(
                    {
                        "region": region,
                        "anchor": lab,
                        "gene": str(genes[i]),
                        "in_panel_245": str(genes[i]) in panel_genes,
                        "pct_expr": float(pct[lab][i]),
                        "mean_log2_expr": float(mean[lab][i]),
                        "specificity_log2_vs_other_anchors": float(spec[i]),
                    }
                )
    d = pd.DataFrame(rows)
    if d.empty:
        return d
    d["rank_key"] = d["specificity_log2_vs_other_anchors"] + np.log10(d["pct_expr"].clip(lower=1))
    d = d.sort_values(["region", "anchor", "rank_key"], ascending=[True, True, False])
    d["rank_within_anchor_all_genes"] = d.groupby(["region", "anchor"]).cumcount() + 1
    d["rank_within_anchor_panel_status"] = d.groupby(["region", "anchor", "in_panel_245"]).cumcount() + 1
    return d


def detectability_tier(x: float) -> str:
    if x < 5:
        return "VERY_LOW_<5pct"
    if x < 20:
        return "LOW_5-20pct"
    if x < 50:
        return "MODERATE_20-50pct"
    return "HIGH_ge50pct"


def main() -> None:
    order = pd.read_excel(PANEL, "SHARED_PANEL_ORDER")
    anchors = pd.read_excel(PANEL, "ANCHOR_COVERAGE")
    detect = pd.read_excel(DETECT, "summary").rename(
        columns={
            "max_pct": "allen_max_pct_full",
            "max_pct_anchor": "allen_max_pct_anchor",
            "median_pct_across_anchors": "allen_median_pct_across_anchors",
            "n_anchors_ge50": "allen_n_anchors_ge50",
            "max_pct_ORBm": "allen_max_pct_ORBm",
            "max_pct_BMAp": "allen_max_pct_BMAp",
        }
    )
    endogenous = set(order.loc[~order["gene"].isin(TRANSGENES), "gene"].astype(str))

    tenx = load_10x(endogenous)
    ncbi = load_ncbi(endogenous)
    gtf = load_gtf(endogenous)
    qc = order.merge(tenx, on="gene", how="left").merge(ncbi, on="gene", how="left").merge(gtf, on="gene", how="left")
    qc = qc.merge(
        detect[["gene", "allen_max_pct_full", "allen_max_pct_anchor", "allen_median_pct_across_anchors", "allen_n_anchors_ge50", "allen_max_pct_ORBm", "allen_max_pct_BMAp"]],
        on="gene",
        how="left",
    )
    qc["target_type"] = np.where(qc["gene"].isin(TRANSGENES), "ADVANCED_EXOGENOUS", "STANDARD_MOUSE_GENE")
    qc["symbol_qc"] = np.where(
        qc["gene"].isin(TRANSGENES),
        "NOT_APPLICABLE_EXOGENOUS",
        np.where(qc["ncbi_gene_id"].notna(), "PASS_CURRENT_NCBI_SYMBOL", "REVIEW_SYMBOL"),
    )
    qc["tenx_design_qc"] = np.where(
        qc["gene"].isin(TRANSGENES),
        "ADVANCED_FASTA_REQUIRED",
        np.where(
            qc["tenx_ensembl_ids"].notna() & ~qc["tenx_on_no_probe_list"].fillna(False),
            "PASS_V1_STANDARD_DESIGNABLE",
            "FAIL_OR_REVIEW_10X",
        ),
    )
    qc["isoform_qc"] = np.where(
        qc["gene"].isin(TRANSGENES),
        "EXACT_CONSTRUCT_SEQUENCE_REQUIRED",
        np.where(
            qc["gtf_transcript_count"].fillna(0).astype(int) <= 1,
            "SINGLE_TRANSCRIPT_GENE_LEVEL",
            "MULTI_TRANSCRIPT_GENE_LEVEL_OK",
        ),
    )
    qc["detectability_tier"] = ["NOT_IN_ALLEN" if pd.isna(x) else detectability_tier(float(x)) for x in qc["allen_max_pct_full"]]
    qc["overall_pre_vendor_status"] = "PASS_PRE_VENDOR_QC"
    qc.loc[qc["gene"].isin(TRANSGENES), "overall_pre_vendor_status"] = "BLOCKED_EXACT_FASTA_REQUIRED"
    qc.loc[(~qc["gene"].isin(TRANSGENES)) & (qc["allen_max_pct_full"] < 5), "overall_pre_vendor_status"] = "PASS_DESIGN_REVIEW_SPARSE_SIGNAL"
    qc.loc[qc["tenx_design_qc"] == "FAIL_OR_REVIEW_10X", "overall_pre_vendor_status"] = "FAIL_OR_REVIEW_10X"

    reporter = pd.DataFrame(
        [
            {
                "target": "tdTomato",
                "planned_line": "Ai14; JAX 007914 (confirm against colony record)",
                "construct": "Rosa-CAG-LSL-tdTomato-WPRE",
                "sequence_status": "BLOCKED_EXACT_FASTA_NOT_IN_WORKSPACE",
                "required_action": "Download/obtain the exact Ai14 tdTomato coding sequence (Addgene Ai9 plasmid 22799 is the construct reference) and submit sense-strand CDS FASTA, >=80 bp. Do not substitute a generic red-fluorescent-protein sequence.",
                "source_url": "https://www.addgene.org/22799/",
            },
            {
                "target": "iCre",
                "planned_line": "TRAP2; JAX 030323",
                "construct": "Fos-2A-iCreERT2 knock-in",
                "sequence_status": "BLOCKED_EXACT_FASTA_NOT_IN_WORKSPACE",
                "required_action": "Obtain the exact iCreERT2 coding sequence used in Fos tm2.1(icre/ERT2)Luo from JAX/originating lab and submit sense-strand CDS FASTA, >=80 bp. Do not substitute conventional Cre or a different CreERT2 codon variant.",
                "source_url": "https://www.jax.org/strain/30323",
            },
        ]
    )

    genome = genomewide_check(endogenous, anchors)
    top_omitted = genome[~genome["in_panel_245"]].copy()
    top_omitted = top_omitted[top_omitted["rank_within_anchor_panel_status"] <= 10]
    coverage = []
    for (region, anchor), g in genome.groupby(["region", "anchor"], sort=False):
        coverage.append(
            {
                "region": region,
                "anchor": anchor,
                "qualifying_panel_genes": int(g["in_panel_245"].sum()),
                "qualifying_omitted_genes": int((~g["in_panel_245"]).sum()),
                "best_panel_gene": g[g["in_panel_245"]].iloc[0]["gene"] if g["in_panel_245"].any() else "",
                "best_panel_specificity": float(g[g["in_panel_245"]].iloc[0]["specificity_log2_vs_other_anchors"]) if g["in_panel_245"].any() else np.nan,
                "best_omitted_gene": g[~g["in_panel_245"]].iloc[0]["gene"] if (~g["in_panel_245"]).any() else "",
                "best_omitted_specificity": float(g[~g["in_panel_245"]].iloc[0]["specificity_log2_vs_other_anchors"]) if (~g["in_panel_245"]).any() else np.nan,
            }
        )
    coverage = pd.DataFrame(coverage)

    qc.to_csv(QC / "panel_245_probe_qc.csv", index=False)
    reporter.to_csv(QC / "reporter_sequence_qc.csv", index=False)
    genome.to_csv(QC / "genomewide_passing_markers.csv", index=False)
    top_omitted.to_csv(QC / "genomewide_top_omitted.csv", index=False)
    coverage.to_csv(QC / "genomewide_anchor_coverage.csv", index=False)

    summary = {
        "panel_total": int(len(qc)),
        "endogenous_total": int((qc.target_type == "STANDARD_MOUSE_GENE").sum()),
        "advanced_exogenous_total": int((qc.target_type == "ADVANCED_EXOGENOUS").sum()),
        "tenx_standard_designable": int((qc.tenx_design_qc == "PASS_V1_STANDARD_DESIGNABLE").sum()),
        "ncbi_current_symbols": int((qc.symbol_qc == "PASS_CURRENT_NCBI_SYMBOL").sum()),
        "all_endogenous_allen_scored": bool(qc.loc[qc.target_type == "STANDARD_MOUSE_GENE", "allen_max_pct_full"].notna().all()),
        "detectability_high_ge50": int((qc.detectability_tier == "HIGH_ge50pct").sum()),
        "detectability_moderate_20_50": int((qc.detectability_tier == "MODERATE_20-50pct").sum()),
        "detectability_low_5_20": int((qc.detectability_tier == "LOW_5-20pct").sum()),
        "detectability_very_low_lt5": int((qc.detectability_tier == "VERY_LOW_<5pct").sum()),
        "very_low_genes": qc.loc[qc.detectability_tier == "VERY_LOW_<5pct", "gene"].tolist(),
        "reporter_fasta_blockers": reporter.target.tolist(),
        "anchors_with_zero_qualifying_panel_genes_genomewide_rule": int((coverage.qualifying_panel_genes == 0).sum()),
        "genomewide_rule": {"min_specificity_log2": MIN_SPEC, "min_pct": MIN_PCT, "min_mean_log2": MIN_MEAN},
    }
    (QC / "qc_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {QC}")


if __name__ == "__main__":
    main()
