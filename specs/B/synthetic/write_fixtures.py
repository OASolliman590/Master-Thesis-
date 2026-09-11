"""Write tiny synthetic Paper B raw fixtures and the versioned workflow config."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def star(values: dict[str, str | None]) -> str:
    header = (
        "# gene-model: GENCODE v36 synthetic-fixture-only\n"
        "gene_id\tgene_name\tgene_type\tunstranded\tstranded_first\tstranded_second"
        "\ttpm_unstranded\tfpkm_unstranded\tfpkm_uq_unstranded\n"
        "N_unmapped\t\t\t10\t10\t10\t\t\t\n"
        "N_multimapping\t\t\t0\t0\t0\t\t\t\n"
        "N_noFeature\t\t\t1\t1\t1\t\t\t\n"
        "N_ambiguous\t\t\t0\t0\t0\t\t\t\n"
    )
    rows = []
    genes = [
        ("ENSG00000000001", "GENE_A", "10"),
        ("ENSG00000000002", "GENE_B", "10"),
        ("ENSG00000000003", "GENE_C", "30"),
        ("ENSG00000000004", "GENE_D", "5"),
        ("ENSG00000000005", "GENE_E", "20"),
        ("ENSG00000000006", "GENE_F", "999"),
    ]
    for gene_id, symbol, default in genes:
        tpm = values.get(symbol, default)
        if tpm is None:
            continue
        rows.append(
            f"{gene_id}\t{symbol}\tprotein_coding\t100\t50\t50\t{tpm}\t8\t8"
        )
    return header + "\n".join(rows) + "\n"


def meth(values: dict[str, str]) -> str:
    order = ["ch00000000", "cgA1", "cgA2", "cgA3", "cgB1", "cgB2", "cgX1"]
    defaults = {
        "ch00000000": "0.01",
        "cgA1": "0.2",
        "cgA2": "0.3",
        "cgA3": "0.9",
        "cgB1": "0.1",
        "cgB2": "0.8",
        "cgX1": "0.5",
    }
    lines = []
    for probe in order:
        lines.append(f"{probe}\t{values.get(probe, defaults[probe])}")
    return "\n".join(lines) + "\n"


def main() -> None:
    raw = OUT / "raw"
    ann = OUT / "annotations"
    ident = OUT / "identity"
    write(
        raw / "tcga_star_TCGA-0001.tsv",
        star({"GENE_A": "10", "GENE_B": "10", "GENE_C": "30", "GENE_D": "5", "GENE_E": "20", "GENE_F": "999"}),
    )
    write(
        raw / "tcga_star_TCGA-0002.tsv",
        star({"GENE_A": "1", "GENE_B": "2", "GENE_C": "3", "GENE_D": "4", "GENE_E": "5", "GENE_F": "9"}),
    )
    write(
        raw / "tcga_star_TCGA-0003.tsv",
        star({"GENE_A": "7", "GENE_B": "7", "GENE_C": "7", "GENE_D": "7", "GENE_E": "7", "GENE_F": "7"}),
    )
    write(
        raw / "tcga_star_TCGA-0004.tsv",
        star({"GENE_A": "10", "GENE_B": "10", "GENE_C": "30", "GENE_D": "5", "GENE_E": None, "GENE_F": "999"}),
    )
    write(raw / "tcga_meth_TCGA-0001.tsv", meth({"cgA1": "0.2", "cgA2": "0.3"}))
    write(raw / "tcga_meth_TCGA-0002.tsv", meth({"cgA1": "0.4", "cgA2": "NA"}))
    write(raw / "tcga_meth_TCGA-0003.tsv", meth({"cgA1": "0.6", "cgA2": "0.5"}))
    write(raw / "tcga_meth_TCGA-0004.tsv", meth({"cgA1": "0.2", "cgA2": "0.3"}))
    extra_patients = [
        {
            "id": "0005",
            "expr": {"GENE_A": "2", "GENE_B": "8", "GENE_C": "4", "GENE_D": "6", "GENE_E": "10", "GENE_F": "1"},
            "meth": {"cgA1": "0.10", "cgA2": "0.12"},
            "age": "51",
            "g1": "3",
            "g2": "3",
            "gsum": "6",
            "gcat": "<=6",
            "qpure": "0.55",
            "wgs": "0.81",
        },
        {
            "id": "0006",
            "expr": {"GENE_A": "12", "GENE_B": "3", "GENE_C": "9", "GENE_D": "4", "GENE_E": "6", "GENE_F": "2"},
            "meth": {"cgA1": "0.55", "cgA2": "0.50"},
            "age": "58",
            "g1": "3",
            "g2": "4",
            "gsum": "7",
            "gcat": "7",
            "qpure": "0.62",
            "wgs": "0.90",
        },
        {
            "id": "0007",
            "expr": {"GENE_A": "4", "GENE_B": "14", "GENE_C": "5", "GENE_D": "8", "GENE_E": "3", "GENE_F": "11"},
            "meth": {"cgA1": "0.25", "cgA2": "0.28"},
            "age": "72",
            "g1": "4",
            "g2": "5",
            "gsum": "9",
            "gcat": ">=8",
            "qpure": "0.48",
            "wgs": "0.77",
        },
        {
            "id": "0008",
            "expr": {"GENE_A": "9", "GENE_B": "1", "GENE_C": "11", "GENE_D": "2", "GENE_E": "8", "GENE_F": "4"},
            "meth": {"cgA1": "0.70", "cgA2": "NA"},
            "age": "63",
            "g1": "3",
            "g2": "4",
            "gsum": "7",
            "gcat": "7",
            "qpure": "0.73",
            "wgs": "0.86",
        },
        {
            "id": "0009",
            "expr": {"GENE_A": "6", "GENE_B": "6", "GENE_C": "6", "GENE_D": "12", "GENE_E": "2", "GENE_F": "7"},
            "meth": {"cgA1": "0.33", "cgA2": "0.31"},
            "age": "54",
            "g1": "4",
            "g2": "4",
            "gsum": "8",
            "gcat": ">=8",
            "qpure": "0.81",
            "wgs": "0.92",
        },
        {
            "id": "0010",
            "expr": {"GENE_A": "15", "GENE_B": "5", "GENE_C": "2", "GENE_D": "7", "GENE_E": "9", "GENE_F": "3"},
            "meth": {"cgA1": "0.05", "cgA2": "0.08"},
            "age": "69",
            "g1": "3",
            "g2": "3",
            "gsum": "6",
            "gcat": "<=6",
            "qpure": "0.44",
            "wgs": "0.71",
        },
        {
            "id": "0011",
            "expr": {"GENE_A": "3", "GENE_B": "11", "GENE_C": "8", "GENE_D": "1", "GENE_E": "14", "GENE_F": "5"},
            "meth": {"cgA1": "0.88", "cgA2": "0.84"},
            "age": "76",
            "g1": "4",
            "g2": "3",
            "gsum": "7",
            "gcat": "7",
            "qpure": "0.67",
            "wgs": "0.89",
        },
        {
            "id": "0012",
            "expr": {"GENE_A": "8", "GENE_B": "4", "GENE_C": "13", "GENE_D": "9", "GENE_E": "1", "GENE_F": "6"},
            "meth": {"cgA1": "0.41", "cgA2": "0.44"},
            "age": "57",
            "g1": "3",
            "g2": "3",
            "gsum": "6",
            "gcat": "<=6",
            "qpure": "0.58",
            "wgs": "0.83",
        },
        {
            "id": "0013",
            "expr": {"GENE_A": "11", "GENE_B": "9", "GENE_C": "1", "GENE_D": "5", "GENE_E": "7", "GENE_F": "8"},
            "meth": {"cgA1": "0.19", "cgA2": "0.22"},
            "age": "74",
            "g1": "4",
            "g2": "4",
            "gsum": "8",
            "gcat": ">=8",
            "qpure": "0.76",
            "wgs": "0.88",
        },
        {
            "id": "0014",
            "expr": {"GENE_A": "5", "GENE_B": "13", "GENE_C": "7", "GENE_D": "3", "GENE_E": "12", "GENE_F": "9"},
            "meth": {"cgA1": "0.63", "cgA2": "0.60"},
            "age": "61",
            "g1": "3",
            "g2": "4",
            "gsum": "7",
            "gcat": "7",
            "qpure": "0.64",
            "wgs": "0.84",
        },
        {
            "id": "0015",
            "expr": {"GENE_A": "14", "GENE_B": "2", "GENE_C": "10", "GENE_D": "11", "GENE_E": "4", "GENE_F": "7"},
            "meth": {"cgA1": "0.15", "cgA2": "0.17"},
            "age": "67",
            "g1": "4",
            "g2": "4",
            "gsum": "8",
            "gcat": ">=8",
            "qpure": "0.69",
            "wgs": "0.87",
        },
    ]
    extra_spec_rows: list[str] = []
    extra_cov_rows: list[str] = []
    extra_sources: list[str] = []
    for patient in extra_patients:
        pid = patient["id"]
        write(raw / f"tcga_star_TCGA-{pid}.tsv", star(patient["expr"]))
        write(raw / f"tcga_meth_TCGA-{pid}.tsv", meth(patient["meth"]))
        extra_spec_rows.extend(
            [
                f"TCGA-SYN\tTCGA-{pid}\tTCGA-{pid}-01A\tF1\tTCGA-{pid}-01A-RNA\tTCGA-{pid}-01A-RNA\tsyn.tcga.star.{pid}\tsyn.tcga.star.{pid}\tSTAR-synthetic\texpression\tsynthetic-map\tresolved\tsynthetic-fixture-v1\tinclude\tchosen-focus\ttrue",
                f"TCGA-SYN\tTCGA-{pid}\tTCGA-{pid}-01A\tF1\tTCGA-{pid}-01A-METH\tTCGA-{pid}-01A-METH\tsyn.tcga.meth.{pid}\tsyn.tcga.meth.{pid}\t450K-synthetic\tmethylation\tsynthetic-map\tresolved\tsynthetic-fixture-v1\tinclude\tchosen-focus\ttrue",
            ]
        )
        extra_cov_rows.append(
            f"TCGA-{pid}-01A\tTCGA-{pid}\t{patient['age']}\t{patient['g1']}\t{patient['g2']}\t"
            f"{patient['gsum']}\t{patient['gcat']}\t{patient['qpure']}\t{patient['wgs']}\ttrue"
        )
        extra_sources.extend([f"star.{pid}", f"meth.{pid}"])
    write(
        raw / "cpc_expression.tsv",
        "GeneID\tSymbol_UCSC\tName_UCSC\tChr_UCSC\tStart_UCSC\tEnd_UCSC\tRefSeq_UCSC\tCPCG0001\tCPCG0002\tCPCG0003\n"
        "1001\tGENE_A\tGene A synthetic\tchr1\t1\t10\tNM_A\t10\t1\t7\n"
        "1002\tGENE_B\tGene B synthetic\tchr1\t11\t20\tNM_B\t10\t2\t7\n"
        "1003\tGENE_C\tGene C synthetic\tchr1\t21\t30\tNM_C\t30\t3\t7\n"
        "1004\tGENE_D\tGene D synthetic\tchr1\t31\t40\tNM_D\t5\t4\t7\n"
        "1005\tGENE_E\tGene E synthetic\tchr1\t41\t50\tNM_E\t20\t5\t7\n",
    )
    write(
        raw / "cpc_methylation.tsv",
        "CPCG0001_rep1\tCPCG0001_rep1_Dectection_Pval\tCPCG0001_rep2\tCPCG0001_rep2_Dectection_Pval"
        "\tCPCG0002_rep1\tCPCG0002_rep1_Dectection_Pval\tCPCG0003_rep1\tCPCG0003_rep1_Dectection_Pval\n"
        "ch00000000\t0.01\t0.001\t0.01\t0.001\t0.01\t0.001\t0.01\t0.001\n"
        "cgA1\t0.2\t0.001\t0.4\t0.001\t0.4\t0.001\t0.6\t0.001\n"
        "cgA2\t0.3\t0.001\t0.3\t0.001\tNA\t0.001\t0.5\t0.001\n"
        "cgA3\t0.9\t0.001\t0.9\t0.001\t0.9\t0.001\t0.9\t0.001\n"
        "cgB1\t0.1\t0.001\t0.1\t0.001\t0.1\t0.001\t0.1\t0.001\n"
        "cgB2\t0.8\t0.001\t0.8\t0.001\t0.8\t0.5\t0.8\t0.001\n"
        "cgX1\t0.5\t0.001\t0.5\t0.001\t0.5\t0.001\t0.5\t0.9\n",
    )
    write(
        ann / "gene_universe.tsv",
        "stable_gene_id\tsymbol\tensembl_id\tannotation_release\tsynthetic\n"
        "SYN:GENE_A\tGENE_A\tENSG00000000001\tsynthetic-fixture-v1\ttrue\n"
        "SYN:GENE_B\tGENE_B\tENSG00000000002\tsynthetic-fixture-v1\ttrue\n"
        "SYN:GENE_C\tGENE_C\tENSG00000000003\tsynthetic-fixture-v1\ttrue\n"
        "SYN:GENE_D\tGENE_D\tENSG00000000004\tsynthetic-fixture-v1\ttrue\n"
        "SYN:GENE_E\tGENE_E\tENSG00000000005\tsynthetic-fixture-v1\ttrue\n",
    )
    write(
        ann / "gene_map.tsv",
        "raw_id\tcanonical_symbol\tstable_gene_id\tmapping_status\tsource\tsynthetic\n"
        "ENSG00000000001\tGENE_A\tSYN:GENE_A\tmapped\ttcga-star\ttrue\n"
        "ENSG00000000002\tGENE_B\tSYN:GENE_B\tmapped\ttcga-star\ttrue\n"
        "ENSG00000000003\tGENE_C\tSYN:GENE_C\tmapped\ttcga-star\ttrue\n"
        "ENSG00000000004\tGENE_D\tSYN:GENE_D\tmapped\ttcga-star\ttrue\n"
        "ENSG00000000005\tGENE_E\tSYN:GENE_E\tmapped\ttcga-star\ttrue\n"
        "ENSG00000000006\tGENE_F\tSYN:GENE_F\tmapped\ttcga-star\ttrue\n"
        "1001\tGENE_A\tSYN:GENE_A\tmapped\tcpc-expression\ttrue\n"
        "1002\tGENE_B\tSYN:GENE_B\tmapped\tcpc-expression\ttrue\n"
        "1003\tGENE_C\tSYN:GENE_C\tmapped\tcpc-expression\ttrue\n"
        "1004\tGENE_D\tSYN:GENE_D\tmapped\tcpc-expression\ttrue\n"
        "1005\tGENE_E\tSYN:GENE_E\tmapped\tcpc-expression\ttrue\n",
    )
    write(
        ann / "probe_map.tsv",
        "probe_id\ttarget_gene_id\tannotation_build\tpromoter_category\tmask_status\tmask_reason\tsource\tsynthetic\n"
        "cgA1\tSYN:GENE_A\tsynthetic-fixture-v1\tpromoter\tpass\tnone\tsynthetic\ttrue\n"
        "cgA2\tSYN:GENE_A\tsynthetic-fixture-v1\tpromoter\tpass\tnone\tsynthetic\ttrue\n"
        "cgA3\tSYN:GENE_A\tsynthetic-fixture-v1\tbody\tpass\tnone\tsynthetic\ttrue\n"
        "cgB1\tSYN:GENE_B\tsynthetic-fixture-v1\tpromoter\tpass\tnone\tsynthetic\ttrue\n"
        "cgB2\tSYN:GENE_B\tsynthetic-fixture-v1\tpromoter\tpass\tnone\tsynthetic\ttrue\n"
        "cgX1\tSYN:GENE_C\tsynthetic-fixture-v1\tpromoter\tmasked\tcross-reactive-synthetic-fixture\tsynthetic\ttrue\n",
    )
    spec_header = (
        "cohort\tpatient_id\tspecimen_id\tfocus_id\taliquot_id\tassay_id\tsource_id\t"
        "source_origin_id\tplatform\tmodality\tmatch_evidence\tmatch_status\trule_version\t"
        "inclusion\treason\tsynthetic\n"
    )
    spec_rows = [
        "TCGA-SYN\tTCGA-0001\tTCGA-0001-01A\tF1\tTCGA-0001-01A-RNA\tTCGA-0001-01A-RNA\tsyn.tcga.star.0001\tsyn.tcga.star.0001\tSTAR-synthetic\texpression\tsynthetic-map\tresolved\tsynthetic-fixture-v1\tinclude\tchosen-focus\ttrue",
        "TCGA-SYN\tTCGA-0001\tTCGA-0001-01A\tF1\tTCGA-0001-01A-METH\tTCGA-0001-01A-METH\tsyn.tcga.meth.0001\tsyn.tcga.meth.0001\t450K-synthetic\tmethylation\tsynthetic-map\tresolved\tsynthetic-fixture-v1\tinclude\tchosen-focus\ttrue",
        "TCGA-SYN\tTCGA-0002\tTCGA-0002-01A\tF1\tTCGA-0002-01A-RNA\tTCGA-0002-01A-RNA\tsyn.tcga.star.0002\tsyn.tcga.star.0002\tSTAR-synthetic\texpression\tsynthetic-map\tresolved\tsynthetic-fixture-v1\tinclude\tchosen-focus\ttrue",
        "TCGA-SYN\tTCGA-0002\tTCGA-0002-01A\tF1\tTCGA-0002-01A-METH\tTCGA-0002-01A-METH\tsyn.tcga.meth.0002\tsyn.tcga.meth.0002\t450K-synthetic\tmethylation\tsynthetic-map\tresolved\tsynthetic-fixture-v1\tinclude\tchosen-focus\ttrue",
        "TCGA-SYN\tTCGA-0003\tTCGA-0003-01A\tF1\tTCGA-0003-01A-RNA\tTCGA-0003-01A-RNA\tsyn.tcga.star.0003\tsyn.tcga.star.0003\tSTAR-synthetic\texpression\tsynthetic-map\tresolved\tsynthetic-fixture-v1\tinclude\tchosen-focus\ttrue",
        "TCGA-SYN\tTCGA-0003\tTCGA-0003-01A\tF1\tTCGA-0003-01A-METH\tTCGA-0003-01A-METH\tsyn.tcga.meth.0003\tsyn.tcga.meth.0003\t450K-synthetic\tmethylation\tsynthetic-map\tresolved\tsynthetic-fixture-v1\tinclude\tchosen-focus\ttrue",
        "TCGA-SYN\tTCGA-0004\tTCGA-0004-01A\tF1\tTCGA-0004-01A-RNA\tTCGA-0004-01A-RNA\tsyn.tcga.star.0004\tsyn.tcga.star.0004\tSTAR-synthetic\texpression\tsynthetic-map\tresolved\tsynthetic-fixture-v1\tinclude\tchosen-focus\ttrue",
        "TCGA-SYN\tTCGA-0004\tTCGA-0004-01A\tF1\tTCGA-0004-01A-METH\tTCGA-0004-01A-METH\tsyn.tcga.meth.0004\tsyn.tcga.meth.0004\t450K-synthetic\tmethylation\tsynthetic-map\tresolved\tsynthetic-fixture-v1\tinclude\tchosen-focus\ttrue",
        *extra_spec_rows,
        "CPC-SYN\tCPCG0001\tCPCG0001-F1\tF1\tCPCG0001-expr\tCPCG0001\tsyn.cpc.expression\tsyn.cpc.expression\tHuGene-synthetic\texpression\tsynthetic-map\tresolved\tsynthetic-fixture-v1\tinclude\tchosen-focus\ttrue",
        "CPC-SYN\tCPCG0001\tCPCG0001-F1\tF1\tCPCG0001-meth-rep1\tCPCG0001_rep1\tsyn.cpc.methylation\tsyn.cpc.methylation\t450K-synthetic\tmethylation\tsynthetic-map\tresolved\tsynthetic-fixture-v1\tinclude\tsynthetic-same-focus-replicate\ttrue",
        "CPC-SYN\tCPCG0001\tCPCG0001-F1\tF1\tCPCG0001-meth-rep2\tCPCG0001_rep2\tsyn.cpc.methylation\tsyn.cpc.methylation\t450K-synthetic\tmethylation\tsynthetic-map\tresolved\tsynthetic-fixture-v1\tinclude\tsynthetic-same-focus-replicate\ttrue",
        "CPC-SYN\tCPCG0002\tCPCG0002-F1\tF1\tCPCG0002-expr\tCPCG0002\tsyn.cpc.expression\tsyn.cpc.expression\tHuGene-synthetic\texpression\tsynthetic-map\tresolved\tsynthetic-fixture-v1\tinclude\tchosen-focus\ttrue",
        "CPC-SYN\tCPCG0002\tCPCG0002-F1\tF1\tCPCG0002-meth\tCPCG0002_rep1\tsyn.cpc.methylation\tsyn.cpc.methylation\t450K-synthetic\tmethylation\tsynthetic-map\tresolved\tsynthetic-fixture-v1\tinclude\tchosen-focus\ttrue",
        "CPC-SYN\tCPCG0003\tCPCG0003-F1\tF1\tCPCG0003-expr\tCPCG0003\tsyn.cpc.expression\tsyn.cpc.expression\tHuGene-synthetic\texpression\tsynthetic-map\tresolved\tsynthetic-fixture-v1\tinclude\tchosen-focus\ttrue",
        "CPC-SYN\tCPCG0003\tCPCG0003-F1\tF1\tCPCG0003-meth\tCPCG0003_rep1\tsyn.cpc.methylation\tsyn.cpc.methylation\t450K-synthetic\tmethylation\tsynthetic-map\tresolved\tsynthetic-fixture-v1\tinclude\tchosen-focus\ttrue",
    ]
    write(ident / "specimens.tsv", spec_header + "\n".join(spec_rows) + "\n")
    cov_lines = [
        "specimen_id\tpatient_id\tage_years\tgleason_primary\tgleason_secondary\tgleason_sum\t"
        "approved_grade_category\tqpure_cellularity\tWGS_BASED_PURITY_ESTIMATION\tsynthetic",
        "TCGA-0001-01A\tTCGA-0001\t60\t3\t4\t7\t7\t0.70\t0.99\ttrue",
        "TCGA-0002-01A\tTCGA-0002\t65\t4\t4\t8\t>=8\t0.60\t0.91\ttrue",
        "TCGA-0003-01A\tTCGA-0003\t70\t3\t3\t6\t<=6\t0.80\t0.95\ttrue",
        "TCGA-0004-01A\tTCGA-0004\t55\t3\t4\t7\t7\t0.50\t0.88\ttrue",
        *extra_cov_rows,
        "CPCG0001-F1\tCPCG0001\t62\t3\t4\t7\t7\t0.72\t0.97\ttrue",
        "CPCG0002-F1\tCPCG0002\t64\t4\t5\t9\t>=8\t0.66\t0.93\ttrue",
        "CPCG0003-F1\tCPCG0003\t68\t3\t3\t6\t<=6\t0.77\t0.94\ttrue",
    ]
    write(ident / "covariates.tsv", "\n".join(cov_lines) + "\n")

    def src(source_id, accession, rel, role, fmt):
        path = OUT / rel
        return {
            "source_id": source_id,
            "accession": accession,
            "exact_url": "file:specs/B/synthetic/" + Path(rel).as_posix(),
            "access_tier": "synthetic-fixture",
            "expected_sha256": sha256(path),
            "expected_size": path.stat().st_size,
            "compression": "none",
            "role": role,
            "format": fmt,
            "completeness": "full",
            "object_name": path.name,
        }

    sources = [
        src("syn.tcga.star.0001", "SYNTHETIC-TCGA-STAR-0001", "raw/tcga_star_TCGA-0001.tsv", "tcga-star-expression", "tcga-star-expression"),
        src("syn.tcga.star.0002", "SYNTHETIC-TCGA-STAR-0002", "raw/tcga_star_TCGA-0002.tsv", "tcga-star-expression", "tcga-star-expression"),
        src("syn.tcga.star.0003", "SYNTHETIC-TCGA-STAR-0003", "raw/tcga_star_TCGA-0003.tsv", "tcga-star-expression", "tcga-star-expression"),
        src("syn.tcga.star.0004", "SYNTHETIC-TCGA-STAR-0004", "raw/tcga_star_TCGA-0004.tsv", "tcga-star-expression", "tcga-star-expression"),
        src("syn.tcga.meth.0001", "SYNTHETIC-TCGA-METH-0001", "raw/tcga_meth_TCGA-0001.tsv", "tcga-methylation-beta", "tcga-methylation-beta"),
        src("syn.tcga.meth.0002", "SYNTHETIC-TCGA-METH-0002", "raw/tcga_meth_TCGA-0002.tsv", "tcga-methylation-beta", "tcga-methylation-beta"),
        src("syn.tcga.meth.0003", "SYNTHETIC-TCGA-METH-0003", "raw/tcga_meth_TCGA-0003.tsv", "tcga-methylation-beta", "tcga-methylation-beta"),
        src("syn.tcga.meth.0004", "SYNTHETIC-TCGA-METH-0004", "raw/tcga_meth_TCGA-0004.tsv", "tcga-methylation-beta", "tcga-methylation-beta"),
    ]
    for patient in extra_patients:
        pid = patient["id"]
        sources.append(
            src(
                f"syn.tcga.star.{pid}",
                f"SYNTHETIC-TCGA-STAR-{pid}",
                f"raw/tcga_star_TCGA-{pid}.tsv",
                "tcga-star-expression",
                "tcga-star-expression",
            )
        )
        sources.append(
            src(
                f"syn.tcga.meth.{pid}",
                f"SYNTHETIC-TCGA-METH-{pid}",
                f"raw/tcga_meth_TCGA-{pid}.tsv",
                "tcga-methylation-beta",
                "tcga-methylation-beta",
            )
        )
    sources.extend(
        [
        src("syn.cpc.expression", "SYNTHETIC-CPC-EXPR", "raw/cpc_expression.tsv", "cpc-expression", "cpc-expression"),
        src("syn.cpc.methylation", "SYNTHETIC-CPC-METH", "raw/cpc_methylation.tsv", "cpc-methylation", "cpc-methylation"),
        ]
    )
    config = {
        "schema_version": "B-workflow-config-v1",
        "purpose": "synthetic-test",
        "synthetic": True,
        "synthetic_label": "SYNTHETIC FIXTURE ONLY. Not a scientific default. Not real-cohort policy.",
        "interpreter": {"policy": "invoking-executable", "note": "Recorded at plan/run time. This fixture does not pin a host path."},
        "sources": sources,
        "w3": {
            "specimen_policy": {
                "label": "synthetic-fixture-only",
                "one_evaluation_row_per_patient": True,
                "ambiguous_focus": "fail",
                "unresolved_identifier": "fail",
                "technical_replicate_collapse": {
                    "same_focus_same_specimen": "median_beta_first_expression",
                    "distinct_or_unresolved_focus": "fail",
                },
                "forbid_wgs_agreement_as_purity": True,
                "development_cohort": "TCGA-SYN",
                "external_cohort": "CPC-SYN",
                "rule_version": "synthetic-fixture-v1",
            },
            "annotation": {
                "release": "synthetic-fixture-v1",
                "gene_universe_path": "specs/B/synthetic/annotations/gene_universe.tsv",
                "probe_map_path": "specs/B/synthetic/annotations/probe_map.tsv",
                "gene_map_path": "specs/B/synthetic/annotations/gene_map.tsv",
            },
            "identity": {
                "specimen_map_path": "specs/B/synthetic/identity/specimens.tsv",
                "covariate_path": "specs/B/synthetic/identity/covariates.tsv",
            },
        },
        "w4": {
            "policy_label": "synthetic-fixture-only",
            "program_p": ["SYN:GENE_A", "SYN:GENE_B"],
            "universe_u": ["SYN:GENE_A", "SYN:GENE_B", "SYN:GENE_C", "SYN:GENE_D", "SYN:GENE_E"],
            "abundance_column": {
                "tcga-star-expression": "tpm_unstranded",
                "cpc-expression": "author-processed-expression",
            },
            "detection_p": {
                "apply_when_present": True,
                "max_detection_p": 0.01,
                "missing_detection_p": "treat-as-missing-beta",
            },
            "probe_training_coverage": 0.95,
            "aggregate_min_coverage": 0.80,
            "aggregate_min_probes": 1,
            "missingness": {
                "na_token": "NA",
                "na_is_not_zero": True,
                "required_u_finite": True,
                "required_p_finite": True,
                "incomplete_score": "exclude",
            },
            "eligibility": {
                "require_age": True,
                "require_gleason": True,
                "require_purity": True,
                "require_score": True,
                "require_all_promoter_aggregates": True,
            },
            "covariate_policy": {
                "quarantine_fields": ["WGS_BASED_PURITY_ESTIMATION"],
                "purity_source_field": "qpure_cellularity",
                "purity_method": "synthetic-qpure-fixture",
                "purity_scale": "fraction-0-1",
            },
            "demo_folds": {
                "label": "synthetic-interface-demo-not-model-cv",
                "folds": [
                    {"fold_id": 0, "train": ["TCGA-0001", "TCGA-0002"], "heldout": ["TCGA-0003"]},
                    {"fold_id": 1, "train": ["TCGA-0001", "TCGA-0003"], "heldout": ["TCGA-0002"]},
                    {"fold_id": 2, "train": ["TCGA-0002", "TCGA-0003"], "heldout": ["TCGA-0001"]},
                ],
            },
        },
        "w5": {
            "policy_label": "synthetic-fixture-only",
            "min_development_n": 7,
            "never_use_w4_full_training_state_for_nested_cv": True,
            "continuous_baseline_columns": ["age_years", "purity_value"],
            "categorical_baseline_groups": [["gleason_7", "gleason_ge8"]],
            "extended_columns": ["promoter_SYN:GENE_A", "promoter_SYN:GENE_B"],
            "gleason_encoding": {
                "source_field": "approved_grade_category",
                "reference": "<=6",
                "dummies": {"7": "gleason_7", ">=8": "gleason_ge8"},
            },
        },
        "scientific_gates": {
            "real_feature_construction": ["E1-P", "E2-U", "E3-Q", "E4-specimen", "E6-precision"],
            "real_development": ["tcga-only-ids", "signed-lock"],
            "real_external_evaluation": ["frozen-training", "evaluation-release-receipt"],
            "w5": "synthetic-fold-local-development",
            "w6": "stage-not-implemented",
            "w7": "stage-not-implemented",
            "w8": "stage-not-implemented",
        },
    }
    cfg_path = ROOT / "specs" / "B" / "workflow.synthetic.json"
    cfg_path.write_bytes(
        (json.dumps(config, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    )
    print(f"wrote {cfg_path}")
    for source in sources:
        print(source["source_id"], source["expected_size"], source["expected_sha256"])


if __name__ == "__main__":
    main()
