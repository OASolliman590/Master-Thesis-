from __future__ import annotations

import csv
import json
import math
import subprocess
from pathlib import Path


class FakeBridge:
    """Fast subprocess fake for the existing R bridge public interfaces."""

    def __call__(self, command, *, cwd, env, capture_output, text, check=False):
        script_name = Path(command[-2]).name
        bridge_path = Path(command[-1])
        bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
        config = bridge["config"]
        inputs = bridge["inputs"]
        output_dir = Path(bridge["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        if script_name == "meta_rma.R":
            self._meta(inputs, output_dir)
        elif script_name == "singscore.R":
            self._singscore(config, inputs, output_dir)
        elif script_name in {"de_limma.R", "de_deseq2.R"}:
            self._de(inputs, output_dir)
        else:
            for name in bridge["expected_outputs"]:
                path = output_dir / name
                if name.endswith(".json"):
                    path.write_text(json.dumps(self._summary(name)), encoding="utf-8")
                elif name.endswith(".tsv"):
                    path.write_text("placeholder\n", encoding="utf-8")
                elif name.endswith(".png"):
                    path.write_bytes(b"invented fake bridge image\n")
                else:
                    path.write_text("invented fake bridge output\n", encoding="utf-8")

        (output_dir / "sessionInfo.txt").write_text("FakeBridge sessionInfo()\n", encoding="utf-8")
        (output_dir / "bridge-runtime.json").write_text(json.dumps({
            "r_version": "FakeR 4.6.1",
            "bioconductor_version": "FakeBioconductor 3.23",
            "r_library": "synthetic-test-library",
            "package_versions": {"jsonlite": "synthetic-test-pin"},
        }), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    @staticmethod
    def _summary(name):
        return {
            "sample_count": 8,
            "outlier_count": 0,
            "score_count": 11,
            "status": "synthetic_fake_bridge",
            "gene_count": 8,
            "endpoint": "orr",
        }

    @staticmethod
    def _meta(inputs, output_dir):
        groups = _read_tsv(inputs["groups"])
        effects = _read_tsv(inputs["effects"])
        subgroups = _read_tsv(inputs["subgroups"])
        effects_by_id = {}
        for row in effects:
            effects_by_id.setdefault(row["analysis_id"], []).append(row)

        with (output_dir / "meta.tsv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=("analysis_id", "k", "n_cancers", "n_studies", "estimate", "se",
                            "ci_lb", "ci_ub", "tau2", "I2", "Q", "p", "fixed_estimate",
                            "fixed_ci_lb", "fixed_ci_ub", "status", "reason"),
                delimiter="\t", lineterminator="\n",
            )
            writer.writeheader()
            for group in groups:
                members = effects_by_id.get(group["analysis_id"], [])
                values = [float(row["yi"]) for row in members]
                k = len(values)
                status = "not_estimable" if k == 0 else "single_study" if k == 1 else "pooled"
                if group.get("unit_family") in {"gene", "m5m6_gene"} and 1 < k < 3:
                    status = "not_pooled"
                estimate = sum(values) / k if k else ""
                se = math.sqrt(sum(float(row["vi"]) for row in members)) / k if k else ""
                writer.writerow({
                    "analysis_id": group["analysis_id"], "k": k,
                    "n_cancers": min(k, 1), "n_studies": k,
                    "estimate": estimate, "se": se,
                    "ci_lb": (float(estimate) - 1.96 * float(se)) if k else "",
                    "ci_ub": (float(estimate) + 1.96 * float(se)) if k else "",
                    "tau2": 0 if k > 1 else "", "I2": 0 if k > 1 else "",
                    "Q": 0 if k > 1 else "", "p": 1 if k > 1 else "",
                    "fixed_estimate": estimate, "fixed_ci_lb": "", "fixed_ci_ub": "",
                    "status": status, "reason": "" if k else "no_estimable_studies",
                })

        with (output_dir / "subgroups.tsv").open("w", newline="", encoding="utf-8") as stream:
            columns = ("test_id", "total_k", "n_levels", "F", "p", "status", "reason")
            writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for test_id in sorted({row["test_id"] for row in subgroups}):
                rows = [row for row in subgroups if row["test_id"] == test_id]
                writer.writerow({
                    "test_id": test_id, "total_k": rows[0]["total_k"],
                    "n_levels": len({row["stratum"] for row in rows}),
                    "F": 0, "p": 1, "status": "ok", "reason": "",
                })

    @staticmethod
    def _singscore(config, inputs, output_dir):
        expression_path = Path(inputs["expression"])
        with expression_path.open(newline="", encoding="utf-8") as stream:
            expression = list(csv.reader(stream, delimiter="\t"))
        sample_ids = expression[0][1:]
        available = {row[0] for row in expression[1:]}
        memberships = {}
        if config["family"] == "pathway_common":
            with Path(inputs["common_gene_table"]).open(newline="", encoding="utf-8") as stream:
                for row in csv.DictReader(stream, delimiter="\t"):
                    memberships[row["hallmark_set"]] = row["common_genes"].split(";")
        else:
            with Path(inputs["gene_sets"]).open(encoding="utf-8") as stream:
                for line in stream:
                    fields = line.rstrip("\r\n").split("\t")
                    memberships[fields[0]] = fields[2:]

        with (output_dir / "coverage.tsv").open("w", newline="", encoding="utf-8") as stream:
            columns = ("unit", "n_found", "n_total", "missing_genes", "complete", "scorable", "reason", "fixed_subset")
            writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            coverage = {}
            for unit, members in memberships.items():
                found = [gene for gene in members if gene in available]
                missing = [gene for gene in members if gene not in available]
                complete = len(found) == len(members)
                if config["family"] == "pathway_coverage90":
                    complete = len(found) * 10 >= len(members) * 9
                    subset = found
                else:
                    subset = members
                if config["family"] == "pathway_common":
                    scorable = complete and len(members) >= 10
                else:
                    scorable = complete
                reason = "" if scorable else "synthetic_fixture_coverage_incomplete"
                coverage[unit] = (scorable, len(found), len(members))
                writer.writerow({
                    "unit": unit, "n_found": len(found), "n_total": len(members),
                    "missing_genes": ";".join(missing), "complete": str(complete).lower(),
                    "scorable": str(scorable).lower(), "reason": reason,
                    "fixed_subset": ";".join(subset),
                })

        with (output_dir / "scores.tsv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
            writer.writerow(("patient_row", "unit", "value"))
            for unit_index, unit in enumerate(memberships):
                scorable = coverage[unit][0]
                for row_index, sample_id in enumerate(sample_ids):
                    score = f"{row_index * 0.1 + unit_index * 0.01:.4f}" if scorable else "NA"
                    writer.writerow((row_index, unit, score))

    @staticmethod
    def _de(inputs, output_dir):
        with Path(inputs["expression"]).open("r", newline="", encoding="utf-8") as stream:
            expression = list(csv.reader(stream, delimiter="\t"))
        genes = [row[0] for row in expression[1:]]
        with (output_dir / "de.tsv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=("gene", "log2FC", "SE", "statistic", "p", "q"),
                delimiter="\t", lineterminator="\n",
            )
            writer.writeheader()
            for index, gene in enumerate(genes):
                writer.writerow({
                    "gene": gene, "log2FC": 0.5, "SE": 0.25,
                    "statistic": index + 1, "p": 0.05, "q": 0.1,
                })
        (output_dir / "de_summary.json").write_text(json.dumps({
            "engine": "limma-trend", "endpoint": "invented", "sample_count": len(expression[0]) - 1,
            "gene_count": len(genes), "batch_adjusted": False,
            "status": "invented_fake_bridge",
        }), encoding="utf-8")
        (output_dir / "volcano.png").write_bytes(b"invented fake bridge image\n")


def _read_tsv(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))
