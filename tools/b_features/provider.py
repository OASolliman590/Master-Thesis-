"""Fold-local feature-state provider for W4 and the W5 seam."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from tools.b_features.scores import mean_or_none, program_score
from tools.b_workflow.io import (
    PipelineFailure,
    atomic_write_json,
    atomic_write_tsv,
    canonical_json_bytes,
    json_no_dups,
    parse_optional_float,
    publish_directory,
    read_tsv,
    remove_tree,
    sha256_bytes,
    sha256_file,
    utc_stamp,
)

STATE_SCHEMA = "B-W4-feature-state-v1"
MANIFEST_SCHEMA = "B-W4-manifest-v1"
OUTCOME_FIELDS = {"y", "Y", "outcome", "target", "delta_r2", "gleason_outcome"}


def _fail(message: str, code: int = 3) -> None:
    raise PipelineFailure(f"stage=W4 {message}", code, "W4")


def _assert_fixture_policy(policy: dict[str, Any]) -> None:
    if policy.get("policy_label") != "synthetic-fixture-only":
        _fail("reason=non-fixture-policy-rejected")
    required = [
        "program_p",
        "universe_u",
        "detection_p",
        "probe_training_coverage",
        "aggregate_min_coverage",
        "aggregate_min_probes",
        "missingness",
        "eligibility",
        "covariate_policy",
    ]
    for key in required:
        if key not in policy:
            _fail(f"reason=missing-explicit-policy {key}")
    if policy["probe_training_coverage"] is None or policy["aggregate_min_coverage"] is None:
        _fail("reason=scientific-default-inferred")
    if any(field in policy for field in OUTCOME_FIELDS):
        _fail("reason=outcome-in-feature-policy")


def _load_expr(path: Path) -> dict[str, dict[str, float | None]]:
    header, rows = read_tsv(path)
    idx = {name: i for i, name in enumerate(header)}
    by_patient: dict[str, dict[str, float | None]] = defaultdict(dict)
    for row_no, row in enumerate(rows, start=2):
        patient = row[idx["patient_id"]]
        gene = row[idx["stable_gene_id"]]
        if gene in by_patient[patient]:
            _fail(f"reason=duplicate-expression-row patient_id={patient} gene={gene}")
        by_patient[patient][gene] = parse_optional_float(row[idx["value"]], field="value", row=row_no)
    return dict(by_patient)


def _load_meth(path: Path) -> dict[str, dict[str, dict[str, float | None]]]:
    header, rows = read_tsv(path)
    idx = {name: i for i, name in enumerate(header)}
    by_patient: dict[str, dict[str, dict[str, float | None]]] = defaultdict(dict)
    for row_no, row in enumerate(rows, start=2):
        patient = row[idx["patient_id"]]
        probe = row[idx["probe_id"]]
        if probe in by_patient[patient]:
            _fail(f"reason=duplicate-methylation-row patient_id={patient} probe={probe}")
        by_patient[patient][probe] = {
            "beta": parse_optional_float(row[idx["beta"]], field="beta", row=row_no),
            "detection_p": parse_optional_float(
                row[idx["detection_p"]], field="detection_p", row=row_no
            ),
        }
    return dict(by_patient)


def _load_cov(path: Path) -> dict[str, dict[str, str]]:
    header, rows = read_tsv(path)
    idx = {name: i for i, name in enumerate(header)}
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        rec = {name: row[i] for i, name in enumerate(header)}
        out[rec["patient_id"]] = rec
    return out


def _load_probe_map(path: Path) -> list[dict[str, str]]:
    header, rows = read_tsv(path)
    probes = []
    for row in rows:
        probes.append({name: row[i] for i, name in enumerate(header)})
    return probes


def _load_detection_p_presence(
    cohort_dir: Path,
    methylation_header: list[str],
    methylation_rows: list[list[str]],
) -> dict[str, bool]:
    """Resolve assay capability from W3 provenance, never from observed P values."""
    manifest = json_no_dups((cohort_dir / "manifest.json").read_bytes())
    format_by_source: dict[str, str] = {}
    for meta in manifest.get("parse_meta", []):
        source_id = meta.get("source_id")
        format_name = meta.get("format")
        if not isinstance(source_id, str) or not isinstance(format_name, str):
            _fail("reason=invalid-w3-parse-metadata")
        previous = format_by_source.setdefault(source_id, format_name)
        if previous != format_name:
            _fail(f"reason=conflicting-source-format source_id={source_id}")

    specimen_header, specimen_rows = read_tsv(cohort_dir / "specimens.tsv")
    specimen_idx = {name: i for i, name in enumerate(specimen_header)}
    required_specimen_fields = {"assay_id", "source_id", "modality", "inclusion"}
    if not required_specimen_fields.issubset(specimen_idx):
        _fail("reason=invalid-w3-specimen-schema")
    capability_by_assay: dict[str, bool] = {}
    for row in specimen_rows:
        if row[specimen_idx["modality"]] != "methylation":
            continue
        if row[specimen_idx["inclusion"]] != "include":
            continue
        assay_id = row[specimen_idx["assay_id"]]
        source_id = row[specimen_idx["source_id"]]
        format_name = format_by_source.get(source_id)
        if format_name not in {"tcga-methylation-beta", "cpc-methylation"}:
            _fail(f"reason=unknown-methylation-source-format source_id={source_id}")
        supports_detection_p = format_name == "cpc-methylation"
        previous = capability_by_assay.setdefault(assay_id, supports_detection_p)
        if previous != supports_detection_p:
            _fail(f"reason=conflicting-detection-p-capability assay_id={assay_id}")

    methylation_idx = {name: i for i, name in enumerate(methylation_header)}
    if not {"patient_id", "assay_id"}.issubset(methylation_idx):
        _fail("reason=invalid-w3-methylation-schema")
    capability_by_patient: dict[str, bool] = {}
    for row in methylation_rows:
        patient_id = row[methylation_idx["patient_id"]]
        assay_ids = row[methylation_idx["assay_id"]].split(",")
        capabilities = set()
        for assay_id in assay_ids:
            if assay_id not in capability_by_assay:
                _fail(f"reason=missing-detection-p-provenance assay_id={assay_id}")
            capabilities.add(capability_by_assay[assay_id])
        if len(capabilities) != 1:
            _fail(f"reason=mixed-detection-p-capability patient_id={patient_id}")
        supports_detection_p = capabilities.pop()
        previous = capability_by_patient.setdefault(patient_id, supports_detection_p)
        if previous != supports_detection_p:
            _fail(f"reason=conflicting-detection-p-capability patient_id={patient_id}")
    return capability_by_patient


def _apply_detection_p(
    beta: float | None,
    detection_p: float | None,
    policy: dict[str, Any],
) -> float | None:
    if beta is None:
        return None
    apply = policy["detection_p"]["apply_when_present"]
    max_p = policy["detection_p"]["max_detection_p"]
    missing_rule = policy["detection_p"]["missing_detection_p"]
    if detection_p is None:
        if missing_rule == "treat-as-missing-beta" and apply:
            # TCGA files have no detection-P; missing_detection_p applies only
            # when the assay actually carries the column. Callers pass a flag.
            return beta
        return beta
    if apply and detection_p > max_p:
        return None
    return beta


@dataclass(frozen=True)
class FeatureState:
    payload: dict[str, Any]

    @property
    def sha256(self) -> str:
        body = {k: v for k, v in self.payload.items() if k != "state_sha256"}
        return sha256_bytes(canonical_json_bytes(body))

    def to_json(self) -> dict[str, Any]:
        payload = dict(self.payload)
        payload["state_sha256"] = self.sha256
        return payload


class FoldFeatureProvider:
    """Fit probe eligibility from training assay values only; transform without refit."""

    def __init__(
        self,
        *,
        expression: dict[str, dict[str, float | None]],
        methylation: dict[str, dict[str, dict[str, float | None]]],
        covariates: dict[str, dict[str, str]],
        probes: list[dict[str, str]],
        policy: dict[str, Any],
        parent_hashes: dict[str, str],
        code_identity_sha256: str,
        detection_p_present_by_patient: dict[str, bool] | None = None,
    ) -> None:
        _assert_fixture_policy(policy)
        self.expression = expression
        self.methylation = methylation
        self.covariates = covariates
        self.probes = probes
        self.policy = policy
        self.parent_hashes = parent_hashes
        self.code_identity_sha256 = code_identity_sha256
        self.detection_p_present_by_patient = detection_p_present_by_patient or {}

    @classmethod
    def from_cohort(
        cls,
        cohort_dir: Path,
        policy: dict[str, Any],
        *,
        probe_map_path: Path,
        parent_hashes: dict[str, str],
        code_identity_sha256: str,
    ) -> "FoldFeatureProvider":
        expression = _load_expr(cohort_dir / "expression.tsv")
        methylation = _load_meth(cohort_dir / "methylation.tsv")
        covariates = _load_cov(cohort_dir / "covariates.tsv")
        probes = _load_probe_map(probe_map_path)
        header, rows = read_tsv(cohort_dir / "methylation.tsv")
        present = _load_detection_p_presence(cohort_dir, header, rows)
        return cls(
            expression=expression,
            methylation=methylation,
            covariates=covariates,
            probes=probes,
            policy=policy,
            parent_hashes=parent_hashes,
            code_identity_sha256=code_identity_sha256,
            detection_p_present_by_patient=present,
        )

    def _usable_beta(
        self,
        patient_id: str,
        probe_id: str,
        detection_p_policy: dict[str, Any],
    ) -> float | None:
        rec = self.methylation.get(patient_id, {}).get(probe_id)
        if rec is None:
            return None
        beta = rec["beta"]
        det = rec["detection_p"]
        if not self.detection_p_present_by_patient.get(patient_id, False):
            return beta
        if det is None:
            if detection_p_policy["missing_detection_p"] == "treat-as-missing-beta":
                return None
            return beta
        if detection_p_policy["apply_when_present"] and det > detection_p_policy["max_detection_p"]:
            return None
        return beta

    def fit(self, training_patient_ids: Sequence[str]) -> FeatureState:
        ids = tuple(sorted({pid for pid in training_patient_ids}))
        if not ids:
            _fail("reason=empty-training-ids")
        for pid in ids:
            if pid not in self.expression:
                _fail(f"reason=unknown-training-patient {pid}")
        universe = list(self.policy["universe_u"])
        program = list(self.policy["program_p"])
        eligible: dict[str, list[str]] = defaultdict(list)
        exclusions: list[dict[str, Any]] = []
        annotation_exclusions: list[dict[str, Any]] = []
        coverage_cut = float(self.policy["probe_training_coverage"])
        n_train = len(ids)
        for probe in self.probes:
            probe_id = probe["probe_id"]
            gene = probe["target_gene_id"]
            category = probe["promoter_category"]
            mask_status = probe["mask_status"]
            if category != "promoter":
                annotation_exclusions.append(
                    {
                        "probe_id": probe_id,
                        "target_gene_id": gene,
                        "reason": "not-promoter",
                        "promoter_category": category,
                    }
                )
                continue
            if mask_status != "pass":
                annotation_exclusions.append(
                    {
                        "probe_id": probe_id,
                        "target_gene_id": gene,
                        "reason": "masked",
                        "mask_status": mask_status,
                        "mask_reason": probe.get("mask_reason", ""),
                    }
                )
                continue
            finite = 0
            for pid in ids:
                if self._usable_beta(pid, probe_id, self.policy["detection_p"]) is not None:
                    finite += 1
            coverage = finite / float(n_train)
            if coverage >= coverage_cut:
                eligible[gene].append(probe_id)
            else:
                exclusions.append(
                    {
                        "probe_id": probe_id,
                        "target_gene_id": gene,
                        "reason": "training-coverage-below-threshold",
                        "finite_training": finite,
                        "training_n": n_train,
                        "coverage": coverage,
                        "threshold": coverage_cut,
                    }
                )
        for gene in eligible:
            eligible[gene] = sorted(set(eligible[gene]))
        payload = {
            "schema_version": STATE_SCHEMA,
            "synthetic": True,
            "synthetic_label": "SYNTHETIC FIXTURE ONLY. Not a scientific U/Q/P freeze.",
            "training_patient_ids": list(ids),
            "training_patient_set_hash": sha256_bytes(
                canonical_json_bytes(list(ids))
            ),
            "program_p": program,
            "universe_u": universe,
            "eligible_probes_by_gene": {gene: eligible[gene] for gene in sorted(eligible)},
            "probe_exclusions": sorted(exclusions, key=lambda r: r["probe_id"]),
            "annotation_exclusions": sorted(annotation_exclusions, key=lambda r: r["probe_id"]),
            "detection_p_policy": deepcopy(self.policy["detection_p"]),
            "missingness_policy": deepcopy(self.policy["missingness"]),
            "eligibility_policy": deepcopy(self.policy["eligibility"]),
            "probe_training_coverage": coverage_cut,
            "aggregate_min_coverage": float(self.policy["aggregate_min_coverage"]),
            "aggregate_min_probes": int(self.policy["aggregate_min_probes"]),
            "policy_label": self.policy["policy_label"],
            "parent_hashes": deepcopy(self.parent_hashes),
            "code_identity_sha256": self.code_identity_sha256,
        }
        state = FeatureState(payload)
        return FeatureState(state.to_json())

    def transform(
        self,
        patient_ids: Sequence[str],
        state: FeatureState,
        *,
        refit: bool = False,
    ) -> list[dict[str, Any]]:
        if refit:
            _fail("reason=refit-forbidden")
        payload = state.payload
        if payload.get("schema_version") != STATE_SCHEMA:
            _fail("reason=unsupported-feature-state-schema")
        recorded_hash = payload.get("state_sha256")
        if not isinstance(recorded_hash, str) or recorded_hash != state.sha256:
            _fail("reason=feature-state-hash-mismatch")
        universe = list(payload["universe_u"])
        program = list(payload["program_p"])
        eligible = payload["eligible_probes_by_gene"]
        min_cov = float(payload["aggregate_min_coverage"])
        min_probes = int(payload["aggregate_min_probes"])
        elig = payload["eligibility_policy"]
        detection_p_policy = payload["detection_p_policy"]
        rows: list[dict[str, Any]] = []
        for patient_id in patient_ids:
            expr = self.expression.get(patient_id, {})
            cov = self.covariates.get(patient_id, {})
            exclusion = None
            gene_values: dict[str, float] = {}
            missing_u = []
            for gene in universe:
                value = expr.get(gene)
                if value is None:
                    missing_u.append(gene)
                else:
                    gene_values[gene] = value
            y = None
            if missing_u:
                exclusion = f"incomplete-universe:{missing_u[0]}"
            else:
                try:
                    y = program_score(gene_values, universe, program)
                except ValueError as exc:
                    exclusion = str(exc)
            promoter: dict[str, float | None] = {}
            promoter_coverage: dict[str, float] = {}
            for gene in program:
                probes = list(eligible.get(gene, []))
                usable = []
                for probe_id in probes:
                    beta = self._usable_beta(patient_id, probe_id, detection_p_policy)
                    if beta is not None:
                        usable.append(beta)
                coverage = (len(usable) / float(len(probes))) if probes else 0.0
                promoter_coverage[gene] = coverage
                if len(probes) < min_probes or coverage < min_cov or not usable:
                    promoter[gene] = None
                    if exclusion is None and elig.get("require_all_promoter_aggregates"):
                        exclusion = f"promoter-aggregate-ineligible:{gene}"
                else:
                    promoter[gene] = mean_or_none(usable)
            if elig.get("require_age") and parse_optional_float(cov.get("age_years", "NA"), field="age_years", row=1) is None:
                exclusion = exclusion or "missing-age"
            if elig.get("require_gleason") and parse_optional_float(cov.get("gleason_sum", "NA"), field="gleason_sum", row=1) is None:
                exclusion = exclusion or "missing-gleason"
            if elig.get("require_purity") and parse_optional_float(cov.get("purity_value", "NA"), field="purity_value", row=1) is None:
                exclusion = exclusion or "missing-purity"
            if elig.get("require_score") and y is None:
                exclusion = exclusion or "missing-score"
            rows.append(
                {
                    "patient_id": patient_id,
                    "cohort": cov.get("cohort", "NA"),
                    "specimen_id": cov.get("specimen_id", "NA"),
                    "Y": y,
                    "promoter": promoter,
                    "promoter_coverage": promoter_coverage,
                    "age_years": parse_optional_float(cov.get("age_years", "NA"), field="age_years", row=1),
                    "gleason_sum": parse_optional_float(cov.get("gleason_sum", "NA"), field="gleason_sum", row=1),
                    "purity_value": parse_optional_float(cov.get("purity_value", "NA"), field="purity_value", row=1),
                    "eligible": exclusion is None,
                    "exclusion_reason": exclusion,
                    "feature_state_sha256": payload["state_sha256"],
                    "synthetic": True,
                }
            )
        return rows


def _score_rows(rows: list[dict[str, Any]], program: Sequence[str]) -> tuple[list[str], list[list[Any]]]:
    headers = [
        "patient_id",
        "cohort",
        "specimen_id",
        "Y",
        "eligible",
        "exclusion_reason",
        "feature_state_sha256",
        "synthetic",
    ]
    out = []
    for row in rows:
        out.append(
            [
                row["patient_id"],
                row["cohort"],
                row["specimen_id"],
                row["Y"],
                row["eligible"],
                row["exclusion_reason"],
                row["feature_state_sha256"],
                True,
            ]
        )
    return headers, out


def _promoter_rows(rows: list[dict[str, Any]], program: Sequence[str]) -> tuple[list[str], list[list[Any]]]:
    headers = [
        "patient_id",
        "gene",
        "promoter_mean_beta",
        "promoter_coverage",
        "feature_state_sha256",
        "synthetic",
    ]
    out = []
    for row in rows:
        for gene in program:
            out.append(
                [
                    row["patient_id"],
                    gene,
                    row["promoter"].get(gene),
                    row["promoter_coverage"].get(gene),
                    row["feature_state_sha256"],
                    True,
                ]
            )
    return headers, out


def run_features(
    config: dict[str, Any],
    *,
    repo_root: Path,
    w3_dir: Path,
    stage_dir: Path,
    parent_hashes: dict[str, str],
    code_identity: str,
    interpreter: str,
) -> dict[str, Any]:
    policy = config["w4"]
    _assert_fixture_policy(policy)
    probe_map_path = repo_root / config["w3"]["annotation"]["probe_map_path"]
    provider = FoldFeatureProvider.from_cohort(
        w3_dir,
        policy,
        probe_map_path=probe_map_path,
        parent_hashes=parent_hashes,
        code_identity_sha256=code_identity,
    )
    development = config["w3"]["specimen_policy"]["development_cohort"]
    cov = provider.covariates
    train_ids = sorted(pid for pid, rec in cov.items() if rec.get("cohort") == development)
    if not train_ids:
        _fail("reason=no-development-patients")
    full_state = provider.fit(train_ids)
    all_ids = sorted(provider.expression)
    transformed = provider.transform(all_ids, full_state)

    work = stage_dir.parent / f"{stage_dir.name}.work"
    if work.exists():
        remove_tree(work)
    work.mkdir(parents=True)
    (work / "fold_states").mkdir()
    hashes: dict[str, str] = {}
    atomic_write_json(work / "full_training_feature_state.json", full_state.to_json())
    hashes["full_training_feature_state.json"] = sha256_file(work / "full_training_feature_state.json")
    score_h, score_r = _score_rows(transformed, policy["program_p"])
    hashes["score_features.tsv"] = atomic_write_tsv(work / "score_features.tsv", score_h, score_r)
    prom_h, prom_r = _promoter_rows(transformed, policy["program_p"])
    hashes["promoter_features.tsv"] = atomic_write_tsv(work / "promoter_features.tsv", prom_h, prom_r)

    demo = policy.get("demo_folds") or {}
    fold_hashes: dict[str, str] = {}
    for fold in demo.get("folds", []):
        fold_id = str(fold["fold_id"])
        train = list(fold["train"])
        heldout = list(fold["heldout"])
        state = provider.fit(train)
        held_rows = provider.transform(heldout, state)
        fold_dir = work / "fold_states" / f"fold_{fold_id}"
        fold_dir.mkdir()
        atomic_write_json(fold_dir / "feature_state.json", state.to_json())
        h, r = _score_rows(held_rows, policy["program_p"])
        atomic_write_tsv(fold_dir / "heldout_scores.tsv", h, r)
        fold_hashes[f"fold_states/fold_{fold_id}/feature_state.json"] = sha256_file(
            fold_dir / "feature_state.json"
        )
        note = {
            "synthetic": True,
            "label": demo.get("label", "synthetic-interface-demo-not-model-cv"),
            "fold_id": fold_id,
            "train": train,
            "heldout": heldout,
            "state_sha256": state.sha256,
            "note": "W5 nested CV must call fit() on each training fold; this demo is not model selection.",
        }
        atomic_write_json(fold_dir / "note.json", note)

    api = {
        "schema_version": "B-W4-w5-seam-v1",
        "synthetic": True,
        "import": "tools.b_features.provider.FoldFeatureProvider",
        "fit": "fit(training_patient_ids) -> FeatureState from training assay values only",
        "transform": "transform(patient_ids, state, refit=False) applies frozen probes without refit",
        "leakage_protections": [
            "Probe eligibility uses only training patient assay values.",
            "Held-out, external, outcome and globally selected probes cannot enter fit().",
            "Changing an inner-validation beta cannot change the inner-training FeatureState hash.",
            "Existing tools.b_prediction table interface remains for fixed-feature regression tests.",
        ],
        "full_training_state_sha256": full_state.sha256,
        "full_training_state_note": (
            "Fitted on all development patients. W5 must not feed this global state "
            "into nested CV probe selection."
        ),
    }
    atomic_write_json(work / "w5_interface.json", api)
    hashes["w5_interface.json"] = sha256_file(work / "w5_interface.json")
    hashes.update(fold_hashes)

    scientific = {
        "schema_version": MANIFEST_SCHEMA,
        "stage": "W4",
        "synthetic": True,
        "synthetic_label": "SYNTHETIC FIXTURE ONLY. Not a scientific P/U/Q freeze.",
        "parent_hashes": parent_hashes,
        "code_identity_sha256": code_identity,
        "interpreter": interpreter,
        "full_training_state_sha256": full_state.sha256,
        "n_patients_scored": len(transformed),
        "n_eligible": sum(1 for row in transformed if row["eligible"]),
        "artifact_hashes": hashes,
        "policy_label": policy["policy_label"],
        "program_p": policy["program_p"],
        "universe_u": policy["universe_u"],
    }
    atomic_write_json(work / "checksums.json", scientific)
    hashes["checksums.json"] = sha256_file(work / "checksums.json")
    manifest = dict(scientific)
    manifest["created_utc"] = utc_stamp()
    manifest["artifact_hashes"] = hashes
    atomic_write_json(work / "manifest.json", manifest)
    complete = {
        "stage": "W4",
        "status": "complete",
        "synthetic": True,
        "checksums_sha256": hashes["checksums.json"],
        "manifest_sha256": sha256_file(work / "manifest.json"),
        "parent_hashes": parent_hashes,
        "code_identity_sha256": code_identity,
        "full_training_state_sha256": full_state.sha256,
    }
    atomic_write_json(work / "COMPLETE.json", complete)
    publish_directory(work, stage_dir)
    return json_no_dups((stage_dir / "manifest.json").read_bytes())
