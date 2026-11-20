from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest

from tools.a_p2 import product
from tools.a_p2 import prepare as prepare_module
from tools.a_p2.prepare import PreparationError, prepare_development


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = ROOT / "docs/validation/A_P2_IDENTITY"
COHORTS = (
    "liu2019",
    "riaz_gse91061",
    "hugo_gse78220",
    "vanallen2015",
    "kim2018",
    "gide2019",
    "gse176307",
)
FEATURE_COLUMNS = (
    "P_ANTIGEN_PRESENTATION",
    "M2_CYTOTOXICITY",
    "M3_VIRAL_MIMICRY",
    "M4_EXCLUSION",
    "CYT",
)
_SYNTHETIC_GSE_PATIENT = "BACI_SYNTH_007"


def _gse_patient_token(source_patient_id: str) -> str:
    digest = hashlib.sha256(source_patient_id.encode("utf-8")).hexdigest()
    return f"STUDY:gse176307:PATIENT:{digest}"


def _write_synthetic_soft(inputs: Path, *, source_patient_ids: tuple[str, ...] = (_SYNTHETIC_GSE_PATIENT,),
                          therapies: tuple[tuple[str | None, ...], ...] | None = None) -> Path:
    path = inputs / "GSE176307_family.soft.gz"
    therapies = therapies or tuple(("Pembrolizumab",) for _ in source_patient_ids)
    samples = []
    sample_index = 0
    for patient_index, (source_patient_id, patient_therapies) in enumerate(zip(source_patient_ids, therapies), 1):
        for therapy in patient_therapies:
            sample_index += 1
            fields = [
                f"^SAMPLE = GSM_SYNTH_{sample_index}",
                f"!Sample_title = Patient sample {source_patient_id}",
                f"!Sample_geo_accession = GSM_SYNTH_{sample_index}",
            ]
            if therapy is not None:
                fields.append(f"!Sample_characteristics_ch1 = io.therapy: {therapy}")
            fields.extend((
                "!Sample_characteristics_ch1 = io.lot: first-line",
                "!Sample_characteristics_ch1 = io.response: NEVER_PARSE_THIS",
                "!Sample_table_begin",
                "!Sample_table_end",
            ))
            samples.extend(fields)
    soft = ("\n".join(samples) + "\n").encode("utf-8").replace(
        b"io.response: NEVER_PARSE_THIS", b"io.response: \xff"
    )
    with path.open("wb") as stream:
        with gzip.GzipFile(fileobj=stream, mode="wb", mtime=0) as zipped:
            zipped.write(soft)
    return path


def _prepare(inputs: Path, out: Path, **kwargs):
    previous_resolver = prepare_module._resolve_gse_soft_path
    previous_root = prepare_module.DEFAULT_SCRATCH_ROOT
    prepare_module.DEFAULT_SCRATCH_ROOT = kwargs.pop("scratch_root", previous_root)
    soft_path = inputs / "GSE176307_family.soft.gz"
    def resolve_synthetic_soft(inputs_dir, explicit_path):
        path = Path(explicit_path) if explicit_path is not None else soft_path
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    prepare_module._resolve_gse_soft_path = resolve_synthetic_soft
    try:
        return prepare_development(
            inputs,
            out,
            geo_soft_path=soft_path,
            **kwargs,
        )
    finally:
        prepare_module._resolve_gse_soft_path = previous_resolver
        prepare_module.DEFAULT_SCRATCH_ROOT = previous_root


def _registry_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def _built_inputs(root: Path, rows=None, *, gse_source_ids: tuple[str, ...] = (_SYNTHETIC_GSE_PATIENT,),
                  gse_therapies: tuple[tuple[str | None, ...], ...] | None = None) -> Path:
    inputs = root / "inputs"
    inputs.mkdir(parents=True)
    rows = rows or [
        {"cohort": cohort, "patient_id": f"invented_patient_{index}"}
        for index, cohort in enumerate(COHORTS, start=1)
    ]
    rows = [dict(row) for row in rows]
    gse_rows = [row for row in rows if row["cohort"] == "gse176307"]
    if len(gse_rows) != len(gse_source_ids):
        raise AssertionError("synthetic GSE176307 rows and source IDs must match")
    for row, source_patient_id in zip(gse_rows, gse_source_ids):
        row["patient_id"] = _gse_patient_token(source_patient_id)
    columns = [
        "cohort",
        "patient_id",
        "cancer",
        "orr_raw",
        "orr_class",
        *FEATURE_COLUMNS,
        "tpm_route",
    ]
    with (inputs / "features.tsv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "cancer": "invented",
                    "orr_raw": "OUTCOME_SENTINEL",
                    "orr_class": "OUTCOME_SENTINEL",
                    **{feature: "FEATURE_SENTINEL" for feature in FEATURE_COLUMNS},
                    "tpm_route": "invented",
                }
            )
    feature_hash = hashlib.sha256((inputs / "features.tsv").read_bytes()).hexdigest()
    source_rows = _registry_rows(REGISTRY_DIR / "SOURCE_REGISTRY.tsv")
    source_hashes = {
        f"invented-source/{row['cohort_id']}": row["expression_sha256"]
        for row in source_rows if row["cohort_id"] in COHORTS
    }
    receipt_inputs = {
        **source_hashes,
        "specs/amendments/2026-10-16-immune-programmes/programme_registry.v1.json": hashlib.sha256(
            (ROOT / "specs/amendments/2026-10-16-immune-programmes/programme_registry.v1.json").read_bytes()
        ).hexdigest(),
        "specs/amendments/2026-11-02-paper-a-validation/gene_aliases.tsv": hashlib.sha256(
            (ROOT / "specs/amendments/2026-11-02-paper-a-validation/gene_aliases.tsv").read_bytes()
        ).hexdigest(),
        "tools/a_dav/field_maps/gse176307.json": hashlib.sha256(
            (ROOT / "tools/a_dav/field_maps/gse176307.json").read_bytes()
        ).hexdigest(),
    }
    receipt_code = {
        "tools/a_p2/build.py": "6ea818d75b049b596222db4bd641861b5a2bed1b2679174a0487f427f044f7b9",
    }
    (inputs / "manifest.json").write_text(
        json.dumps(
            {
                "input_sha256": receipt_inputs,
                "code_sha256": receipt_code,
                "output_sha256": {"features.tsv": feature_hash},
            },
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    _write_synthetic_soft(
        inputs, source_patient_ids=gse_source_ids, therapies=gse_therapies
    )
    return inputs


def _replace_feature_bytes(inputs: Path, contents: bytes) -> None:
    features = inputs / "features.tsv"
    features.write_bytes(contents)
    receipt_path = inputs / "manifest.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["output_sha256"]["features.tsv"] = hashlib.sha256(contents).hexdigest()
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")


def _copy_registries(root: Path) -> Path:
    copy = root / "registries"
    copy.mkdir()
    for name in (
        "SOURCE_REGISTRY.tsv",
        "PUBLICATION_FAMILY_REGISTRY.tsv",
        "OVERLAP_REGISTRY.tsv",
    ):
        shutil.copyfile(REGISTRY_DIR / name, copy / name)
    return copy


def _resolve_all_test_overlaps(registry_dir: Path, *, unresolved_pair=None) -> None:
    path = registry_dir / "OVERLAP_REGISTRY.tsv"
    rows = _registry_rows(path)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=rows[0].keys(), delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        for row in rows:
            pair = tuple(sorted((row["cohort_a"], row["cohort_b"])))
            conservative_family = {
                "liu2019", "vanallen2015", "riaz_gse91061", "hugo_gse78220"
            }
            if pair == tuple(sorted(("liu2019", "vanallen2015"))):
                row["status"] = "OVERLAP_RISK_GROUPED"
            elif set(pair) <= conservative_family:
                row["status"] = "CONSERVATIVE_SENSITIVITY"
            elif pair == tuple(sorted(("gse176307", "imvigor210"))):
                row["status"] = "RESOLVED_BY_SOURCE_RULE"
                row["rule_id"] = "A_P2_ATEZO_FREEZE_EXCLUSION_V1"
            elif pair == tuple(sorted(("gse176307", "gse111636"))):
                row["status"] = "NOT_APPLICABLE_TO_A_P2"
            else:
                row["status"] = "NO_OVERLAP_DOCUMENTED"
            if unresolved_pair is not None and pair == tuple(sorted(unresolved_pair)):
                row["status"] = "UNRESOLVED"
            writer.writerow(row)


def _spy_on_feature_csv_parsing(monkeypatch):
    original_dict_reader = csv.DictReader
    original_reader = csv.reader
    parsed_features = []

    def dict_reader(stream, *args, **kwargs):
        if Path(getattr(stream, "name", "")).name == "features.tsv":
            parsed_features.append("DictReader")
        return original_dict_reader(stream, *args, **kwargs)

    def reader(stream, *args, **kwargs):
        if Path(getattr(stream, "name", "")).name == "features.tsv":
            parsed_features.append("reader")
        return original_reader(stream, *args, **kwargs)

    monkeypatch.setattr(prepare_module.csv, "DictReader", dict_reader)
    monkeypatch.setattr(prepare_module.csv, "reader", reader)
    return parsed_features


def test_prepare_and_check_only_never_parse_later_feature_or_outcome_fields(tmp_path, monkeypatch):
    inputs = _built_inputs(tmp_path)
    header = "\t".join(
        ["cohort", "patient_id", "cancer", "orr_raw", "orr_class", *FEATURE_COLUMNS, "tpm_route"]
    ).encode("utf-8")
    # The opaque suffix is both beyond csv's field-size limit and invalid UTF-8.
    opaque_suffix = b"\t" + (b"x" * 200_000) + b"\xff" + (b"\t" * 8) + b"tpm\n"
    rows = [header + b"\n"]
    for index, cohort in enumerate(COHORTS, start=1):
        patient = (
            _gse_patient_token(_SYNTHETIC_GSE_PATIENT).encode("ascii")
            if cohort == "gse176307" else b"patient_" + str(index).encode("ascii")
        )
        rows.append(cohort.encode("utf-8") + b"\t" + patient + opaque_suffix)
    _replace_feature_bytes(inputs, b"".join(rows))
    out = tmp_path / "scratch" / "prepared"
    parsed_features = _spy_on_feature_csv_parsing(monkeypatch)

    prepared = _prepare(
        inputs,
        out,
        registry_dir=REGISTRY_DIR,
        scratch_root=tmp_path / "scratch",
    )
    checked = _prepare(
        inputs,
        out,
        check_only=True,
        registry_dir=REGISTRY_DIR,
        scratch_root=tmp_path / "scratch",
    )

    manifest = json.loads((out / "a_p2_input_manifest.json").read_text(encoding="utf-8"))
    sidecar = json.loads((out / "identity_sidecar.json").read_text(encoding="utf-8"))
    assert prepared["structural_status"] == "PASS"
    assert checked["structural_status"] == "PASS"
    assert parsed_features == []
    assert Path(manifest["input_table"]).is_absolute() is True
    assert set(manifest["cohorts"]) == set(COHORTS)
    assert prepared["missing_adaptive_cohorts"] == ["braun2020"]
    assert prepared["cohort_adaptive_sensitivity_cohorts"] == sorted(COHORTS)
    assert sidecar["uniqueness_checks"]["within_cohort_canonical_identity_unique"] is True
    assert "not distinct people" in sidecar["uniqueness_checks"]["cross_cohort_identity_interpretation"]


def test_prepared_manifest_shape_is_accepted_by_existing_synthetic_preflight(tmp_path):
    inputs = _built_inputs(tmp_path)
    out = tmp_path / "scratch" / "prepared"
    _prepare(
        inputs,
        out,
        registry_dir=REGISTRY_DIR,
        scratch_root=tmp_path / "scratch",
    )
    manifest = json.loads((out / "a_p2_input_manifest.json").read_text(encoding="utf-8"))

    twin = tmp_path / "synthetic_twin"
    twin.mkdir()
    (twin / "A_P2_SYNTHETIC_FIXTURE").touch()
    table = twin / "synthetic_features.tsv"
    with table.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["cohort", "patient_id", "orr_class", *FEATURE_COLUMNS],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "cohort": "invented_cohort",
                "patient_id": "invented_patient",
                "orr_class": "R",
                **{feature: "0.25" for feature in FEATURE_COLUMNS},
            }
        )
    identity = twin / "synthetic_identity.json"
    identity_value = {
        "schema": "a_p2_identity_bindings_v1",
        "data_classification": "SYNTHETIC_ONLY",
        "provenance": {
            "kind": "generated_fixture",
            "fixture_id": "a_p2_preparation_synthetic_twin",
            "valid_as_real_identity_evidence": False,
        },
        "records": [],
    }
    identity.write_text(json.dumps(identity_value, sort_keys=True) + "\n", encoding="utf-8")
    manifest.update(
        {
            "data_classification": "SYNTHETIC_ONLY",
            "cohorts": {
                "invented_cohort": {
                    "study_family": "invented_family",
                    "cancer": "invented_cancer",
                    "representation": "invented TPM",
                    "feature_transform": "log2(TPM + 1)",
                    "primary_eligible": True,
                    "adaptive_eligible": True,
                    "cyt_available": True,
                }
            },
            "input_table": table.name,
            "input_sha256": hashlib.sha256(table.read_bytes()).hexdigest(),
            "identity_provenance": {
                "schema": "a_p2_identity_provenance_v1",
                "kind": "generated_fixture",
                "fixture_id": "a_p2_preparation_synthetic_twin",
                "sidecar": identity.name,
                "sidecar_sha256": hashlib.sha256(identity.read_bytes()).hexdigest(),
                "valid_as_real_identity_evidence": False,
            },
            "provenance": {
                "kind": "generated_fixture",
                "fixture_id": "a_p2_preparation_synthetic_twin",
                "authorization": "synthetic-test-authorization",
                "signatures_present": False,
                "valid_as_real_approval": False,
            },
        }
    )
    manifest_path = twin / "input_manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")

    accepted = product._preflight_manifest(manifest_path, "development", False)

    assert accepted[0]["data_classification"] == "SYNTHETIC_ONLY"


def test_feature_table_with_wrong_header_is_refused_before_reading_rows(tmp_path, monkeypatch):
    inputs = _built_inputs(tmp_path)
    _replace_feature_bytes(
        inputs,
        b"cohort\tpatient_id\tresponse\tfeature\n"
        b"liu2019\tinvented_patient\tUNREAD_OUTCOME\tUNREAD_FEATURE\n",
    )
    parsed_features = _spy_on_feature_csv_parsing(monkeypatch)

    with pytest.raises(PreparationError, match="not the expected A-P2 feature table"):
        _prepare(
            inputs,
            tmp_path / "scratch" / "prepared",
            registry_dir=REGISTRY_DIR,
            scratch_root=tmp_path / "scratch",
        )

    assert parsed_features == []


def test_tracked_registry_resolves_every_in_scope_pair(tmp_path):
    # Tier 3 user-confirmed and the A1 rule executed, 19 Nov 2026.
    inputs = _built_inputs(tmp_path)
    out = tmp_path / "scratch" / "prepared"
    report = _prepare(inputs, out, registry_dir=REGISTRY_DIR, scratch_root=tmp_path / "scratch")

    assert report["blocking_pairs"] == []
    assert report["structural_status"] == "PASS"
    manifest = json.loads((out / "a_p2_input_manifest.json").read_text(encoding="utf-8"))
    assert manifest["identity_provenance"]["resolution_status"] == "RESOLVED_NO_UNRESOLVED_OVERLAP"


def test_unresolved_overlap_pairs_block_resolution(tmp_path):
    registry_dir = _copy_registries(tmp_path)
    path = registry_dir / "OVERLAP_REGISTRY.tsv"
    rows = _registry_rows(path)
    for row in rows:
        if tuple(sorted((row["cohort_a"], row["cohort_b"]))) == ("gse176307", "imvigor210"):
            row["status"] = "UNRESOLVED"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    inputs = _built_inputs(tmp_path)
    out = tmp_path / "scratch" / "prepared"
    report = _prepare(
        inputs,
        out,
        registry_dir=registry_dir,
        scratch_root=tmp_path / "scratch",
    )

    assert report["structural_status"] == "BLOCKED"
    blocking = {tuple(pair["cohorts"]) for pair in report["blocking_pairs"]}
    assert ("gse176307", "imvigor210") in blocking
    assert ("imvigor210", "liu2019") not in blocking  # Tier 3, user-confirmed 19 Nov 2026
    assert not any(pair["cohorts"] == ["gse111636", "gse176307"] for pair in report["blocking_pairs"])
    assert any(
        pair["cohorts"] == ["gse111636", "gse176307"]
        for pair in report["unresolved_pairs_out_of_scope"]
    )
    manifest = json.loads((out / "a_p2_input_manifest.json").read_text(encoding="utf-8"))
    assert manifest["identity_provenance"]["resolution_status"] == "UNRESOLVED_OVERLAP"
    sidecar = json.loads((out / "identity_sidecar.json").read_text(encoding="utf-8"))
    # Only the bladder cohort has the reopened pair.
    for record in sidecar["records"]:
        expected = "UNRESOLVED_OVERLAP" if record["cohort"] == "gse176307" else "RESOLVED_AUTHORITATIVE"
        assert record["resolution_status"] == expected
    assert any(record["cohort"] == "gse176307" for record in sidecar["records"])
    assert all(record["overlap_registry_pairs"] for record in sidecar["records"])


def test_duplicate_canonical_identities_block_preparation(tmp_path):
    rows = [
        {"cohort": COHORTS[0], "patient_id": "same_invented_identity"},
        {"cohort": COHORTS[0], "patient_id": "same_invented_identity"},
        *[
            {"cohort": cohort, "patient_id": f"invented_patient_{index}"}
            for index, cohort in enumerate(COHORTS[1:], start=1)
        ],
    ]
    inputs = _built_inputs(tmp_path, rows)
    out = tmp_path / "scratch" / "prepared"

    with pytest.raises(PreparationError, match="duplicate canonical identity"):
        _prepare(
            inputs,
            out,
            registry_dir=REGISTRY_DIR,
            scratch_root=tmp_path / "scratch",
        )

    assert not out.exists()


def test_protected_input_path_is_refused_before_reading(tmp_path, monkeypatch):
    def forbidden_reader(*args, **kwargs):
        raise AssertionError("protected input was read")

    monkeypatch.setattr("tools.a_p2.prepare._read_identity_rows", forbidden_reader)
    protected_inputs = tmp_path / "imvigor210" / "inputs"

    with pytest.raises(PreparationError, match="protected"):
        _prepare(
            protected_inputs,
            tmp_path / "scratch" / "prepared",
            registry_dir=REGISTRY_DIR,
            scratch_root=tmp_path / "scratch",
        )


def test_protected_cohort_token_is_checked_before_patient_id_or_suffix(tmp_path):
    inputs = _built_inputs(tmp_path)
    header = "\t".join(
        ["cohort", "patient_id", "cancer", "orr_raw", "orr_class", *FEATURE_COLUMNS, "tpm_route"]
    ).encode("utf-8")
    _replace_feature_bytes(
        inputs,
        header + b"\n" + b"imvigor210\t\xff\t" + (b"z" * 200_000) + b"\xff\n",
    )

    with pytest.raises(PreparationError, match="protected cohort identity"):
        _prepare(
            inputs,
            tmp_path / "scratch" / "prepared",
            registry_dir=REGISTRY_DIR,
            scratch_root=tmp_path / "scratch",
        )


def test_resolved_policy_statuses_and_conservative_manifest_are_structurally_supported(tmp_path):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir)
    inputs, _ = _multi_patient_gse_inputs(tmp_path)
    out = tmp_path / "scratch" / "prepared"
    report = _prepare(
        inputs,
        out,
        registry_dir=registry_dir,
        scratch_root=tmp_path / "scratch",
    )

    assert report["structural_status"] == "PASS"
    assert report["blocking_pairs"] == []
    assert report["conservative_sensitivity"]["structural_status"] == "PASS"
    assert report["missing_adaptive_cohorts"] == ["braun2020"]
    assert report["cohort_adaptive_sensitivity_cohorts"] == sorted(COHORTS)
    main_manifest = json.loads((out / "a_p2_input_manifest.json").read_text(encoding="utf-8"))
    conservative = json.loads(
        (out / "a_p2_input_manifest_conservative_sensitivity.json").read_text(encoding="utf-8")
    )
    assert main_manifest["cohorts"]["liu2019"]["study_family"] == main_manifest["cohorts"]["vanallen2015"]["study_family"]
    assert main_manifest["cohorts"]["riaz_gse91061"]["study_family"] != main_manifest["cohorts"]["hugo_gse78220"]["study_family"]
    conservative_family_ids = {
        conservative["cohorts"][cohort]["study_family"]
        for cohort in ("liu2019", "vanallen2015", "riaz_gse91061", "hugo_gse78220")
    }
    assert len(conservative_family_ids) == 1
    assert report["input_manifest_sha256"] != report["conservative_sensitivity"]["input_manifest_sha256"]
    sidecar = json.loads((out / "identity_sidecar.json").read_text(encoding="utf-8"))
    accepted_statuses = {
        "NO_OVERLAP_DOCUMENTED",
        "OVERLAP_RISK_GROUPED",
        "CONSERVATIVE_SENSITIVITY",
        "RESOLVED_BY_SOURCE_RULE",
    }
    assert all(record["resolution_status"] == "RESOLVED_AUTHORITATIVE" for record in sidecar["records"])
    assert all(
        record["overlap_registry_pairs"]
        and all(pair["status"] in accepted_statuses for pair in record["overlap_registry_pairs"])
        for record in sidecar["records"]
    )
    freeze = json.loads((out / "a_p2_input_manifest_freeze.json").read_text(encoding="utf-8"))
    sensitivity = json.loads(
        (out / "a_p2_input_manifest_development_sensitivity.json").read_text(encoding="utf-8")
    )
    assert Path(freeze["input_table"]).resolve() == Path(sensitivity["input_table"]).resolve()
    assert freeze["input_sha256"] == sensitivity["input_sha256"]
    assert freeze["input_sha256"] != main_manifest["input_sha256"]
    checked = _prepare(
        inputs, out, check_only=True, registry_dir=registry_dir,
        scratch_root=tmp_path / "scratch",
    )
    assert checked["structural_status"] == "PASS"


@pytest.mark.parametrize(
    "unresolved_pair",
    [
        ("liu2019", "gide2019"),
        ("gse176307", "imvigor210"),
    ],
)
def test_any_unresolved_in_scope_pair_blocks_a_fully_resolved_registry(tmp_path, unresolved_pair):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir, unresolved_pair=unresolved_pair)
    inputs = _built_inputs(tmp_path)
    report = _prepare(
        inputs,
        tmp_path / "scratch" / "prepared",
        registry_dir=registry_dir,
        scratch_root=tmp_path / "scratch",
    )

    assert report["structural_status"] == "BLOCKED"
    assert any(tuple(item["cohorts"]) == tuple(sorted(unresolved_pair)) for item in report["blocking_pairs"])


def test_conservative_policy_emits_its_second_manifest_for_all_family_pairs(tmp_path):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir)
    inputs = _built_inputs(tmp_path)
    report = _prepare(
        inputs,
        tmp_path / "scratch" / "prepared",
        registry_dir=registry_dir,
        scratch_root=tmp_path / "scratch",
    )

    assert report["structural_status"] == "PASS"
    assert report["conservative_sensitivity"]["structural_status"] == "PASS"


@pytest.mark.parametrize(
    "lineage_mutation",
    [
        lambda lineage: lineage["receipt_input_sha256"].update({"invented-source/liu2019": "0" * 64}),
        lambda lineage: lineage["feature_membership_sha256"].update({"M2_CYTOTOXICITY": "0" * 64}),
        lambda lineage: lineage["alias_table_identity"].update({"sha256": "0" * 64}),
        lambda lineage: lineage["builder_identity"].update({"sha256": "0" * 64}),
    ],
    ids=["source-hashes", "memberships", "alias-identity", "builder-identity"],
)
def test_check_only_refuses_build_lineage_mismatch(tmp_path, lineage_mutation):
    inputs = _built_inputs(tmp_path)
    out = tmp_path / "scratch" / "prepared"
    _prepare(
        inputs, out, registry_dir=REGISTRY_DIR, scratch_root=tmp_path / "scratch"
    )
    manifest_path = out / "a_p2_input_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lineage_mutation(manifest["provenance"]["build_lineage"])
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(PreparationError, match="build receipt, source, membership, alias, or builder lineage"):
        _prepare(
            inputs,
            out,
            check_only=True,
            registry_dir=REGISTRY_DIR,
            scratch_root=tmp_path / "scratch",
        )


@pytest.mark.parametrize(
    "receipt_key",
    [
        "specs/amendments/2026-10-16-immune-programmes/programme_registry.v1.json",
        "specs/amendments/2026-11-02-paper-a-validation/gene_aliases.tsv",
        "tools/a_dav/field_maps/gse176307.json",
    ],
    ids=["panel-registry", "alias-table", "gse-field-map"],
)
def test_prepare_refuses_receipt_with_wrong_frozen_mapping_hash(tmp_path, receipt_key):
    inputs = _built_inputs(tmp_path)
    receipt_path = inputs / "manifest.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["input_sha256"][receipt_key] = "0" * 64
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(PreparationError, match="(frozen (panel registry|alias-table) identity|GSE176307 field-map identity)"):
        _prepare(
            inputs,
            tmp_path / "scratch" / "prepared",
            registry_dir=REGISTRY_DIR,
            scratch_root=tmp_path / "scratch",
        )


def test_prepare_refuses_builder_hash_without_a_reachable_historical_git_object(tmp_path):
    inputs = _built_inputs(tmp_path)
    receipt_path = inputs / "manifest.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["code_sha256"]["tools/a_p2/build.py"] = "0" * 64
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(PreparationError, match="no matching reachable historical git object"):
        _prepare(
            inputs,
            tmp_path / "scratch" / "prepared",
            registry_dir=REGISTRY_DIR,
            scratch_root=tmp_path / "scratch",
        )


def test_tracked_preparation_documents_contain_no_absolute_workspace_path():
    tracked = (
        ROOT / "docs/validation/A_P2_IDENTITY/README.md",
        ROOT / "docs/validation/A_P2_IDENTITY/SOURCE_REGISTRY.tsv",
        ROOT / "docs/validation/A_P2_IDENTITY/PUBLICATION_FAMILY_REGISTRY.tsv",
        ROOT / "docs/validation/A_P2_IDENTITY/OVERLAP_REGISTRY.tsv",
        ROOT / "docs/decisions/A_P2_DEVELOPMENT_RELEASE_PROPOSED_2026-11-14.md",
        ROOT / "docs/decisions/A_P2_OVERLAP_POLICY_PROPOSED_2026-11-14.md",
    )
    root_text = ROOT.resolve().as_posix()
    absolute_path = re.compile(r"(?<![A-Za-z0-9:/])/(?:Users|Volumes|private|tmp)/[^\s)\]>\"']+")
    for path in tracked:
        content = path.read_text(encoding="utf-8")
        assert root_text not in content
        assert absolute_path.search(content) is None


def test_quoted_multiline_suffix_is_refused_before_fake_identity_is_emitted(tmp_path):
    inputs = _built_inputs(tmp_path)
    header = "\t".join(
        ["cohort", "patient_id", "cancer", "orr_raw", "orr_class", *FEATURE_COLUMNS, "tpm_route"]
    ).encode("ascii")
    first_physical_row = b'liu2019\treal_identity\tinvented\t"multiline outcome\n'
    fake_identity_line = b"gide2019\tFAKE_IDENTITY\tinvented\tignored\n"
    _replace_feature_bytes(inputs, header + b"\n" + first_physical_row + fake_identity_line)
    out = tmp_path / "scratch" / "prepared"

    with pytest.raises(PreparationError, match="quoted or incorrectly framed"):
        _prepare(inputs, out, registry_dir=REGISTRY_DIR, scratch_root=tmp_path / "scratch")

    assert not out.exists()
    assert not list(tmp_path.glob("scratch/**/identity_sidecar*.json"))


def test_registry_must_include_all_21_selected_pairs_and_protected_final_pair(tmp_path):
    registry_dir = _copy_registries(tmp_path)
    path = registry_dir / "OVERLAP_REGISTRY.tsv"
    rows = [
        row for row in _registry_rows(path)
        if tuple(sorted((row["cohort_a"], row["cohort_b"])))
        != tuple(sorted(("kim2018", "gse176307")))
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(PreparationError, match="missing a required development pair"):
        prepare_module._load_registries(registry_dir)


def test_conservative_sensitivity_groups_any_separate_pair_in_the_declared_four_cohort_family(tmp_path):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir)
    inputs = _built_inputs(tmp_path)
    report = _prepare(
        inputs, tmp_path / "scratch" / "prepared", registry_dir=registry_dir,
        scratch_root=tmp_path / "scratch",
    )

    assert report["conservative_sensitivity"]["structural_status"] == "PASS"
    manifest = json.loads(
        (tmp_path / "scratch" / "prepared" / "a_p2_input_manifest_conservative_sensitivity.json")
        .read_text(encoding="utf-8")
    )
    families = {
        manifest["cohorts"][cohort]["study_family"]
        for cohort in ("liu2019", "vanallen2015", "riaz_gse91061", "hugo_gse78220")
    }
    assert len(families) == 1


def _multi_patient_gse_inputs(root: Path) -> tuple[Path, tuple[str, ...]]:
    source_ids = ("BACI_KEEP", "BACI_ATEZO", "BACI_MISSING", "BACI_CONFLICT", "BACI_NA")
    rows = [
        {"cohort": cohort, "patient_id": f"invented_{cohort}"}
        for cohort in COHORTS if cohort != "gse176307"
    ]
    rows.extend({"cohort": "gse176307", "patient_id": "placeholder"} for _ in source_ids)
    inputs = _built_inputs(
        root,
        rows,
        gse_source_ids=source_ids,
        gse_therapies=(
            ("Pembrolizumab",),
            ("aTeZoLiZuMaB",),
            (None,),
            ("Pembrolizumab", "Nivolumab"),
            ("NA",),
        ),
    )
    return inputs, source_ids


def test_a1_freeze_exclusion_drops_tokens_from_derived_table_and_sidecar(tmp_path):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir)
    inputs, source_ids = _multi_patient_gse_inputs(tmp_path)
    out = tmp_path / "scratch" / "prepared"
    report = _prepare(inputs, out, registry_dir=registry_dir, scratch_root=tmp_path / "scratch")

    artifact = json.loads((out / "a_p2_atezo_freeze_exclusions.json").read_text(encoding="utf-8"))
    excluded = {_gse_patient_token(source_ids[index]) for index in (1, 2, 3, 4)}
    assert report["a1_exclusion_count"] == 4
    assert artifact["rule_id"] == "A_P2_ATEZO_FREEZE_EXCLUSION_V1"
    assert set(artifact["excluded_tokens"]) == excluded
    assert artifact["excluded_tokens_sha256"] == hashlib.sha256(
        json.dumps(sorted(excluded), separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    derived = out / "a_p2_freeze_features.tsv"
    derived_bytes = derived.read_bytes()
    for token in excluded:
        assert token.encode("utf-8") not in derived_bytes
    freeze_sidecar = json.loads((out / "identity_sidecar_freeze.json").read_text(encoding="utf-8"))
    assert not (excluded & {record["patient_id"] for record in freeze_sidecar["records"]})
    freeze_manifest = json.loads((out / "a_p2_input_manifest_freeze.json").read_text(encoding="utf-8"))
    release = _load_json(out / prepare_module.RELEASE_TEMPLATE_NAME)
    freeze_run = next(run for run in release["runs"] if run["package_id"] == "freeze")
    assert Path(freeze_manifest["input_table"]).resolve() == derived.resolve()
    derived_hash = hashlib.sha256(derived_bytes).hexdigest()
    assert freeze_run["input_sha256"] == derived_hash
    original_hash = hashlib.sha256((inputs / "features.tsv").read_bytes()).hexdigest()
    for name in ("a_p2_input_manifest.json", "a_p2_input_manifest_conservative_sensitivity.json"):
        main = json.loads((out / name).read_text(encoding="utf-8"))
        assert main["input_sha256"] == original_hash
        assert main["provenance"]["a1_source_rule"]["derived_features_sha256"] == derived_hash
        assert main["provenance"]["a1_source_rule"]["exclusion_artifact_sha256"] == hashlib.sha256(
            (out / "a_p2_atezo_freeze_exclusions.json").read_bytes()
        ).hexdigest()
    assert release["record_status"] == "UNAPPROVED"


def test_freeze_template_cannot_be_rebound_to_original_table(tmp_path):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir)
    inputs, _ = _multi_patient_gse_inputs(tmp_path)
    out = tmp_path / "scratch" / "prepared"
    _prepare(inputs, out, registry_dir=registry_dir, scratch_root=tmp_path / "scratch")
    record_path = out / prepare_module.RELEASE_TEMPLATE_NAME
    record = _load_json(record_path)
    freeze_run = next(run for run in record["runs"] if run["package_id"] == "freeze")
    freeze_run["input_sha256"] = hashlib.sha256((inputs / "features.tsv").read_bytes()).hexdigest()
    _write_bound_json(record_path, record)

    with pytest.raises(PreparationError, match="release template must match all four packages"):
        _prepare(
            inputs, out, check_only=True, registry_dir=registry_dir,
            scratch_root=tmp_path / "scratch",
        )


def test_check_only_refuses_a_tampered_a1_exclusion_artifact(tmp_path):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir)
    inputs, _ = _multi_patient_gse_inputs(tmp_path)
    out = tmp_path / "scratch" / "prepared"
    _prepare(inputs, out, registry_dir=registry_dir, scratch_root=tmp_path / "scratch")
    artifact_path = out / "a_p2_atezo_freeze_exclusions.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["soft_sha256"] = "0" * 64
    artifact_path.write_text(json.dumps(artifact, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(PreparationError, match="artifact hashes do not match"):
        _prepare(
            inputs, out, check_only=True, registry_dir=registry_dir,
            scratch_root=tmp_path / "scratch",
        )


def test_every_built_gse_token_must_be_found_in_the_soft(tmp_path):
    inputs = _built_inputs(tmp_path)
    features = (inputs / "features.tsv").read_bytes()
    original = _gse_patient_token(_SYNTHETIC_GSE_PATIENT).encode("ascii")
    assert features.count(original) == 1
    _replace_feature_bytes(inputs, features.replace(original, b"STUDY:gse176307:PATIENT:" + b"0" * 64))

    with pytest.raises(PreparationError, match="recomputed GSE176307 patient tokens do not match"):
        _prepare(
            inputs, tmp_path / "scratch" / "prepared",
            registry_dir=REGISTRY_DIR, scratch_root=tmp_path / "scratch",
        )


def test_explicit_unpinned_gse_soft_object_is_refused(tmp_path):
    soft_path = _write_synthetic_soft(tmp_path)

    with pytest.raises(PreparationError, match="differs from its pinned field-map identity"):
        prepare_module._resolve_gse_soft_path(tmp_path, soft_path)


def test_only_the_exact_source_rule_can_close_protected_final_pair(tmp_path):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir)
    path = registry_dir / "OVERLAP_REGISTRY.tsv"
    rows = _registry_rows(path)
    for row in rows:
        if tuple(sorted((row["cohort_a"], row["cohort_b"]))) == tuple(sorted(("gse176307", "imvigor210"))):
            row["status"] = "RESOLVED_BY_SOURCE_RULE"
            row["rule_id"] = "WRONG_RULE"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    inputs = _built_inputs(tmp_path)
    report = _prepare(
        inputs, tmp_path / "scratch" / "prepared", registry_dir=registry_dir,
        scratch_root=tmp_path / "scratch",
    )
    blocker = next(
        item for item in report["blocking_pairs"]
        if item["cohorts"] == ["gse176307", "imvigor210"]
    )
    assert "exact A-P2 source-rule ID" in blocker["evidence_needed"]


def test_verified_a1_companion_closes_final_pair_for_all_packages(tmp_path):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir)
    path = registry_dir / "OVERLAP_REGISTRY.tsv"
    rows = _registry_rows(path)
    for row in rows:
        if tuple(sorted((row["cohort_a"], row["cohort_b"]))) == tuple(sorted(("gse176307", "imvigor210"))):
            row["status"] = "RESOLVED_BY_SOURCE_RULE"
            row["rule_id"] = "A_P2_ATEZO_FREEZE_EXCLUSION_V1"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    inputs = _built_inputs(tmp_path)
    report = _prepare(
        inputs, tmp_path / "scratch" / "prepared", registry_dir=registry_dir,
        scratch_root=tmp_path / "scratch",
    )

    assert report["structural_status"] == "PASS"
    assert report["conservative_sensitivity"]["structural_status"] == "PASS"
    assert not any(item["cohorts"] == ["gse176307", "imvigor210"] for item in report["blocking_pairs"])
    assert report["freeze"]["structural_status"] == "PASS"
    assert report["development_sensitivity"]["structural_status"] == "PASS"
    assert not any(
        item["cohorts"] == ["gse176307", "imvigor210"]
        for item in report["freeze"]["blocking_pairs"]
    )


def test_selected_selected_source_rule_status_always_blocks(tmp_path):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir)
    path = registry_dir / "OVERLAP_REGISTRY.tsv"
    rows = _registry_rows(path)
    for row in rows:
        if tuple(sorted((row["cohort_a"], row["cohort_b"]))) == tuple(sorted(("liu2019", "gide2019"))):
            row["status"] = "RESOLVED_BY_SOURCE_RULE"
            row["rule_id"] = "A_P2_ATEZO_FREEZE_EXCLUSION_V1"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    inputs = _built_inputs(tmp_path)
    report = _prepare(
        inputs, tmp_path / "scratch" / "prepared", registry_dir=registry_dir,
        scratch_root=tmp_path / "scratch",
    )

    assert report["structural_status"] == "BLOCKED"
    assert any(
        item["cohorts"] == ["gide2019", "liu2019"]
        and "selected-selected pair" in item["evidence_needed"]
        for item in report["blocking_pairs"]
    )


def test_soft_patients_absent_from_built_table_are_ignored(tmp_path):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir)
    inputs = _built_inputs(tmp_path)
    _write_synthetic_soft(
        inputs,
        source_patient_ids=(_SYNTHETIC_GSE_PATIENT, "SYNTH_ONLY_IN_GEO"),
        therapies=(("Pembrolizumab",), ("Atezolizumab",)),
    )
    out = tmp_path / "scratch" / "prepared"
    report = _prepare(inputs, out, registry_dir=registry_dir, scratch_root=tmp_path / "scratch")

    assert report["gse176307_patient_count"] == 1
    assert report["a1_exclusion_count"] == 0
    artifact = json.loads((out / "a_p2_atezo_freeze_exclusions.json").read_text(encoding="utf-8"))
    assert _gse_patient_token("SYNTH_ONLY_IN_GEO") not in artifact["excluded_tokens"]


def test_missing_final_test_pair_blocks_preparation(tmp_path):
    registry_dir = _copy_registries(tmp_path)
    path = registry_dir / "OVERLAP_REGISTRY.tsv"
    rows = [row for row in _registry_rows(path) if set((row["cohort_a"], row["cohort_b"])) != {"liu2019", "imvigor210"}]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(PreparationError, match="missing a required"):
        prepare_module._load_registries(registry_dir)


def test_bladder_final_pair_cannot_close_with_no_overlap_status(tmp_path):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir)
    path = registry_dir / "OVERLAP_REGISTRY.tsv"
    rows = _registry_rows(path)
    for row in rows:
        if {row["cohort_a"], row["cohort_b"]} == {"gse176307", "imvigor210"}:
            row["status"] = "NO_OVERLAP_DOCUMENTED"
            row["rule_id"] = ""
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    inputs = _built_inputs(tmp_path)
    report = _prepare(inputs, tmp_path / "scratch" / "prepared", registry_dir=registry_dir,
                      scratch_root=tmp_path / "scratch")
    assert report["structural_status"] == "BLOCKED"
    assert any(item["cohorts"] == ["gse176307", "imvigor210"] for item in report["blocking_pairs"])


def test_preparation_refuses_sibling_of_private_runtime(tmp_path, monkeypatch):
    inputs = _built_inputs(tmp_path)
    monkeypatch.setattr(prepare_module, "_read_identity_rows", lambda *_: pytest.fail("identity read occurred before output guard"))
    with pytest.raises(PreparationError, match="private .*runtime"):
        prepare_development(inputs, ROOT / ".scratch" / "prepare" / "invented", registry_dir=REGISTRY_DIR)


def test_preparation_refuses_symlink_escape_from_private_runtime(tmp_path, monkeypatch):
    inputs = _built_inputs(tmp_path)
    runtime = tmp_path / ".scratch" / "runtime"
    runtime.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (runtime / "escape").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(prepare_module, "DEFAULT_SCRATCH_ROOT", runtime)
    with pytest.raises(PreparationError, match="symlink"):
        prepare_development(inputs, runtime / "escape" / "prepared", registry_dir=REGISTRY_DIR)


def test_invented_package_never_reports_real_release_ready(tmp_path):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir)
    inputs, _ = _multi_patient_gse_inputs(tmp_path)
    report = _prepare(inputs, tmp_path / "scratch" / "prepared", registry_dir=registry_dir,
                      scratch_root=tmp_path / "scratch")
    assert report["structural_status"] == "PASS"
    assert report["release_readiness"] == "INDEPENDENT_BINDINGS_REQUIRED"
    assert report["blocking_pairs"] == []


_PACKAGE_MANIFESTS = (
    prepare_module.MANIFEST_NAME,
    prepare_module.CONSERVATIVE_MANIFEST_NAME,
    prepare_module.SENSITIVITY_MANIFEST_NAME,
    prepare_module.FREEZE_MANIFEST_NAME,
)
_PACKAGE_IDS = ("main", "conservative", "development_sensitivity", "freeze")


def _load_json(path):
    return json.loads(path.read_bytes())


def _write_bound_json(path, value):
    raw = prepare_module._json_bytes(value)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def test_prepare_emits_one_v3_record_binding_all_four_manifests(tmp_path):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir)
    inputs, _ = _multi_patient_gse_inputs(tmp_path)
    out = tmp_path / "scratch" / "prepared"
    report = _prepare(inputs, out, registry_dir=registry_dir, scratch_root=out.parent)

    template = out / "a_p2_release_v3.unapproved.json"
    assert list(out.glob("*release*.json")) == [template]
    record = _load_json(template)
    artifact = out / prepare_module.A1_EXCLUSIONS_NAME
    derived = out / prepare_module.FREEZE_TABLE_NAME
    assert record == {
        "record_type": "a_p2_user_release_v3",
        "record_status": "UNAPPROVED",
        "release_scope": "A_P2_REAL_OUTCOME_ACCESS",
        "data_classification": "PRIVATE_PATIENT_LEVEL",
        "execution_code_sha256": product._code_provenance(),
        "a1_source_rule": {
            "rule_id": prepare_module.A1_RULE_ID,
            "exclusion_artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            "derived_features_sha256": hashlib.sha256(derived.read_bytes()).hexdigest(),
        },
        "runs": record["runs"],
    }
    runs = {run["package_id"]: run for run in record["runs"]}
    assert len(record["runs"]) == 4
    assert set(runs) == set(_PACKAGE_IDS)
    registry_files = {
        "source_registry_sha256": prepare_module.SOURCE_REGISTRY_NAME,
        "publication_family_registry_sha256": prepare_module.FAMILY_REGISTRY_NAME,
        "overlap_registry_sha256": prepare_module.OVERLAP_REGISTRY_NAME,
    }
    for package_id, name in zip(_PACKAGE_IDS, _PACKAGE_MANIFESTS):
        manifest_bytes = (out / name).read_bytes()
        manifest = json.loads(manifest_bytes)
        identity = manifest["identity_provenance"]
        operation = "freeze" if package_id == "freeze" else "development"
        assert runs[package_id] == {
            "package_id": package_id,
            "operation": operation,
            "input_role": manifest["role"],
            "input_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "input_sha256": manifest["input_sha256"],
            "identity_sidecar_sha256": identity["sidecar_sha256"],
            **{field: identity[field] for field in registry_files},
            "cohorts": sorted(manifest["cohorts"]),
            "outcome_fields": ["orr_class"],
        }
        assert runs[package_id]["input_sha256"] == hashlib.sha256(Path(manifest["input_table"]).read_bytes()).hexdigest()
        assert runs[package_id]["identity_sidecar_sha256"] == hashlib.sha256((out / identity["sidecar"]).read_bytes()).hexdigest()
        for field, filename in registry_files.items():
            assert runs[package_id][field] == hashlib.sha256((registry_dir / filename).read_bytes()).hexdigest()
        assert "release_template_sha256" not in report["package_hashes"][package_id]
    assert report["release_decision_id"] == "A_P2_DEVELOPMENT_RELEASE_DRAFT_2026-11-19"
    assert report["release_record_status"] == "UNAPPROVED"
    assert report["release_template_name"] == template.name
    assert report["release_template_sha256"] == hashlib.sha256(template.read_bytes()).hexdigest()


@pytest.fixture
def bound_a1_package(tmp_path, monkeypatch):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir)
    inputs, source_ids = _multi_patient_gse_inputs(tmp_path)
    out = tmp_path / "scratch" / "prepared"
    _prepare(inputs, out, registry_dir=registry_dir, scratch_root=tmp_path / "scratch")
    monkeypatch.setattr(prepare_module, "DEFAULT_REGISTRY_DIR", registry_dir)
    soft = inputs / "GSE176307_family.soft.gz"
    monkeypatch.setattr(prepare_module, "_GSE176307_SOFT_SHA256", hashlib.sha256(soft.read_bytes()).hexdigest())
    main = _load_json(out / prepare_module.MANIFEST_NAME)
    binding = main["provenance"]["a1_source_rule"]
    # Use the known-good fixture bindings as the independent preflight reference.
    monkeypatch.setattr(prepare_module, "_MAIN_FEATURES_SHA256", main["input_sha256"])
    monkeypatch.setattr(prepare_module, "_HISTORICAL_BUILD_RECEIPT_SHA256", main["provenance"]["source_build_manifest_sha256"])
    monkeypatch.setattr(product, "_A1_ORIGINAL_SIDECAR_SHA256", main["identity_provenance"]["sidecar_sha256"])
    monkeypatch.setattr(product, "_A1_EXCLUDED_TOKENS_SHA256", binding["excluded_tokens_sha256"])
    monkeypatch.setattr(product, "_A1_DERIVED_FEATURES_SHA256", binding["derived_features_sha256"])
    monkeypatch.setattr(prepare_module, "_signed_dimension_errors", lambda **kwargs: [])
    return inputs, out, registry_dir, source_ids


@pytest.fixture
def development_release(bound_a1_package, tmp_path, monkeypatch):
    _, out, _, _ = bound_a1_package
    decisions = tmp_path / "decisions"
    decisions.mkdir()
    monkeypatch.setattr(product, "_DECISION_DIR", decisions)
    decision = decisions / "A_P2_DEVELOPMENT_RELEASE_DRAFT_2026-11-19.md"
    record = _load_json(out / prepare_module.RELEASE_TEMPLATE_NAME)
    pin = decisions / "invented_approval_pin.sha256"
    monkeypatch.setattr(product, "_DEVELOPMENT_APPROVAL_PIN", pin, raising=False)
    return out, decision, record, pin


def _mock_release_pin(pin, record):
    canonical = json.dumps(
        record, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    pin.write_text(digest + "\n", encoding="ascii")
    return digest


def _write_release_decision(decision, record, *, prose="Invented release fixture"):
    decision.write_text(
        prose + "\n\n```a-p2-release-v3\n" + json.dumps(record, indent=2) + "\n```\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize(("change", "message"), (
    ("unsigned", "must be APPROVED"),
    ("missing-run", "must list all four prepared runs"),
    ("wrong-input-hash", "does not match this exact A-P2 run"),
    ("different-package", "does not match this exact A-P2 run"),
    ("wrong-a1-hash", "does not match the A1 binding"),
    ("missing-block", "exactly one valid"),
    ("duplicate-block", "exactly one valid"),
    ("duplicate-key", "exactly one valid"),
))
def test_development_release_refuses_invalid_record(development_release, change, message):
    out, decision, record, pin = development_release
    main = next(run for run in record["runs"] if run["package_id"] == "main")
    if change != "unsigned":
        record["record_status"] = "APPROVED"
    if change == "missing-run":
        record["runs"].remove(main)
    elif change == "wrong-input-hash":
        main["input_sha256"] = "0" * 64
    elif change == "different-package":
        conservative = next(run for run in record["runs"] if run["package_id"] == "conservative")
        main.update(conservative, package_id="main")
    elif change == "wrong-a1-hash":
        record["a1_source_rule"]["exclusion_artifact_sha256"] = "0" * 64
    _mock_release_pin(pin, record)

    record_json = json.dumps(record)
    if change == "duplicate-key":
        record_json = '{"record_status": "UNAPPROVED", ' + record_json[1:]
    block = f"```a-p2-release-v3\n{record_json}\n```\n"
    if change == "missing-block":
        block = ""
    elif change == "duplicate-block":
        block = block + "\n" + block
    decision.write_text("Invented release fixture\n\n" + block, encoding="utf-8")

    manifest = out / prepare_module.MANIFEST_NAME
    with pytest.raises(PermissionError, match=message):
        product._authorize_development_real(manifest, _load_json(manifest), manifest.read_bytes(), "development")


@pytest.fixture
def invented_development_run(development_release, tmp_path, monkeypatch):
    out, decision, record, pin = development_release
    record["record_status"] = "APPROVED"
    _write_release_decision(decision, record)
    claims = tmp_path / "claims"
    monkeypatch.setattr(product, "_DEVELOPMENT_CLAIMS_DIR", claims, raising=False)

    # Enter the authorization stage with prepared, invented metadata. The CLI gate stays closed.
    def invented_preflight(path, operation, allow_outcomes):
        assert not allow_outcomes
        assert path.parent == out and path.name in _PACKAGE_MANIFESTS
        raw = path.read_bytes()
        manifest = json.loads(raw)
        payload, classification, digest = product._validate_manifest_shape(path, manifest, operation)
        return manifest, raw, payload, classification, digest, product._identity_path(path, manifest)

    def invented_bridge(operation, input_path, manifest, out_dir):
        assert input_path.is_file()
        if operation == "freeze":
            equation = out_dir / ".work" / "fitted.json"
            equation.write_text("{}", encoding="utf-8")
            diagnostics = out_dir / ".work" / "diagnostics.tsv"
            diagnostics.write_text("invented\n", encoding="utf-8")
            return {}, {"equation.json": equation, "fit_diagnostics.tsv": diagnostics}
        return {}, {}

    monkeypatch.setattr(product, "_preflight_manifest", invented_preflight)
    monkeypatch.setattr(product, "_bridge", invented_bridge)
    return out, decision, record, pin, claims


def test_development_release_without_pin_stays_locked(invented_development_run, tmp_path):
    out, _, _, _, claims = invented_development_run
    with pytest.raises(PermissionError, match="remains locked.*approval pin is missing"):
        product.run_development(out / prepare_module.MANIFEST_NAME, tmp_path / "locked")
    assert not claims.exists()


@pytest.mark.parametrize(("package_id", "field"), (
    ("conservative", "input_sha256"),
    ("main", "input_manifest_sha256"),
))
def test_development_release_refuses_edits_after_pinning(
    invented_development_run, tmp_path, package_id, field,
):
    out, decision, record, pin, claims = invented_development_run
    _mock_release_pin(pin, record)
    row = next(run for run in record["runs"] if run["package_id"] == package_id)
    row[field] = "0" * 64
    _write_release_decision(decision, record)

    with pytest.raises(PermissionError, match="does not match the approval pin"):
        product.run_development(out / prepare_module.MANIFEST_NAME, tmp_path / "edited")
    assert not claims.exists()


@pytest.mark.parametrize("contents", ["A" * 64, "a" * 63, "a" * 64 + "\n" + "b" * 64, "a" * 64 + " "])
def test_development_release_refuses_malformed_pin(invented_development_run, tmp_path, contents):
    out, _, _, pin, claims = invented_development_run
    pin.write_text(contents, encoding="ascii")
    with pytest.raises(PermissionError, match="exactly one lowercase SHA-256"):
        product.run_development(out / prepare_module.MANIFEST_NAME, tmp_path / "invalid_pin")
    assert not claims.exists()


def test_matching_pinned_development_release_accepts_all_packages_and_prose_edits(
    invented_development_run, tmp_path,
):
    out, decision, record, pin, claims = invented_development_run
    digest = _mock_release_pin(pin, record)
    _write_release_decision(decision, record, prose="Invented signature prose edited after pinning")
    for name, package_id in zip(_PACKAGE_MANIFESTS, _PACKAGE_IDS):
        runner = product.run_freeze if package_id == "freeze" else product.run_development
        result = runner(out / name, tmp_path / package_id)
        assert result["code_provenance"] == record["execution_code_sha256"]

    receipts = [_load_json(path) for path in claims.iterdir()]
    assert sorted(receipt["package_id"] for receipt in receipts) == sorted(_PACKAGE_IDS)
    for receipt in receipts:
        assert receipt == {
            "approved_block_sha256": digest,
            "package_id": receipt["package_id"],
            "claimed_at_utc": receipt["claimed_at_utc"],
            "execution_code_sha256": record["execution_code_sha256"],
        }
        assert receipt["claimed_at_utc"].endswith("+00:00")


def _refuse_payload_open(monkeypatch, manifest_path):
    manifest = _load_json(manifest_path)
    payload = product._input_path(manifest_path, manifest)
    original_open = Path.open

    def open_spy(path, *args, **kwargs):
        if path == payload:
            pytest.fail("A-P2 opened the payload before the release checks passed")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_spy)


def test_development_release_claim_refuses_a_second_run_before_payload_open(
    invented_development_run, tmp_path, monkeypatch,
):
    out, _, record, pin, _ = invented_development_run
    _mock_release_pin(pin, record)
    manifest = out / prepare_module.MANIFEST_NAME
    product.run_development(manifest, tmp_path / "first_run")
    _refuse_payload_open(monkeypatch, manifest)

    with pytest.raises(PermissionError, match="already executed"):
        product.run_development(manifest, tmp_path / "second_run")


def test_development_release_refuses_changed_execution_code(invented_development_run, tmp_path, monkeypatch):
    out, _, record, pin, claims = invented_development_run
    _mock_release_pin(pin, record)
    code = {**product._code_provenance(), "r_entrypoint": "0" * 64}
    monkeypatch.setattr(product, "_code_provenance", lambda: code)
    manifest = out / prepare_module.MANIFEST_NAME
    _refuse_payload_open(monkeypatch, manifest)

    with pytest.raises(PermissionError, match="execution code provenance"):
        product.run_development(manifest, tmp_path / "changed_code")
    assert not claims.exists()


def test_development_release_rejects_nonempty_output_before_payload_open_or_claim(
    invented_development_run, tmp_path, monkeypatch,
):
    out, _, record, pin, claims = invented_development_run
    _mock_release_pin(pin, record)
    manifest = out / prepare_module.MANIFEST_NAME
    output = tmp_path / "nonempty"
    output.mkdir()
    (output / "existing.txt").write_text("invented\n", encoding="utf-8")
    _refuse_payload_open(monkeypatch, manifest)

    with pytest.raises(FileExistsError, match="output directory is not empty"):
        product.run_development(manifest, output)
    assert not claims.exists()


def test_development_release_does_not_authorize_final_evaluation(development_release):
    out, _, record, _ = development_release
    record["record_status"] = "APPROVED"
    release = out / "invented_approved_development_record.json"
    _write_bound_json(release, record)
    with pytest.raises(PermissionError, match="not an approved real decision"):
        product._authorize_final_real({}, b"invented", release, "a" * 64)


@pytest.mark.parametrize("manifest_name, operation, signed_table, signed_grouping", (
    (prepare_module.MANIFEST_NAME, "development", "original", "main"),
    (prepare_module.CONSERVATIVE_MANIFEST_NAME, "development", "original", "conservative"),
    (prepare_module.SENSITIVITY_MANIFEST_NAME, "development", "derived", "main"),
    (prepare_module.FREEZE_MANIFEST_NAME, "freeze", "derived", "main"),
), ids=("main", "conservative", "bladder-sensitivity", "freeze"))
@pytest.mark.parametrize("table", ("original", "derived"))
@pytest.mark.parametrize("grouping", ("main", "conservative"))
def test_product_enforces_signed_table_and_grouping(
    bound_a1_package, manifest_name, operation, signed_table, signed_grouping, table, grouping,
):
    _, out, _, _ = bound_a1_package
    path = out / manifest_name
    manifest = _load_json(path)
    if (table, grouping) == (signed_table, signed_grouping):
        product._validate_bound_a1_metadata(path, manifest, operation)
        return

    original = _load_json(out / prepare_module.MANIFEST_NAME)
    conservative = _load_json(out / prepare_module.CONSERVATIVE_MANIFEST_NAME)
    derived = _load_json(out / prepare_module.FREEZE_MANIFEST_NAME)
    table_manifest = original if table == "original" else derived
    grouping_manifest = original if grouping == "main" else conservative
    manifest.update(input_table=table_manifest["input_table"], input_sha256=table_manifest["input_sha256"],
                    cohorts=grouping_manifest["cohorts"])
    sidecar_path = out / manifest["identity_provenance"]["sidecar"]
    sidecar = _load_json(out / table_manifest["identity_provenance"]["sidecar"])
    for row in sidecar["records"]:
        row["publication_family_id"] = manifest["cohorts"][row["cohort"]]["study_family"]
    manifest["identity_provenance"]["sidecar_sha256"] = _write_bound_json(sidecar_path, sidecar)
    _write_bound_json(path, manifest)

    with pytest.raises(PermissionError):
        product._validate_bound_a1_metadata(path, manifest, operation)


@pytest.mark.parametrize("manifest_name, operation", (
    ("a_p2_input_manifest_unknown.json", "development"),
    (prepare_module.SENSITIVITY_MANIFEST_NAME, "freeze"),
    (prepare_module.FREEZE_MANIFEST_NAME, "development"),
))
def test_product_refuses_unknown_package_or_wrong_operation(bound_a1_package, manifest_name, operation):
    _, out, _, _ = bound_a1_package
    path = out / manifest_name
    if not path.exists():
        shutil.copyfile(out / prepare_module.SENSITIVITY_MANIFEST_NAME, path)
    with pytest.raises(PermissionError):
        product._validate_bound_a1_metadata(path, _load_json(path), operation)


@pytest.mark.parametrize("manifest_name", _PACKAGE_MANIFESTS[:3], ids=("main", "conservative", "sensitivity"))
def test_product_refuses_sidecar_with_rehashed_identity_swap(bound_a1_package, manifest_name):
    _, out, _, source_ids = bound_a1_package
    kept_token = _gse_patient_token(source_ids[0])
    replacement = (_gse_patient_token(source_ids[1]) if manifest_name == prepare_module.SENSITIVITY_MANIFEST_NAME
                   else _gse_patient_token("BACI_INVENTED_REPLACEMENT"))
    names = [manifest_name]
    if manifest_name == prepare_module.MANIFEST_NAME:
        # Keep the companion consistent with the changed original sidecar.
        names.append(prepare_module.FREEZE_MANIFEST_NAME)
    for name in names:
        path = out / name
        manifest = _load_json(path)
        identity = manifest["identity_provenance"]
        sidecar_path = out / identity["sidecar"]
        sidecar = _load_json(sidecar_path)
        row = next(row for row in sidecar["records"] if row["patient_id"] == kept_token)
        row["patient_id"] = replacement
        row["canonical_patient_uid"] = "a_p2:gse176307:" + hashlib.sha256(replacement.encode()).hexdigest()
        identity["sidecar_sha256"] = _write_bound_json(sidecar_path, sidecar)
        _write_bound_json(path, manifest)

    path = out / manifest_name
    with pytest.raises(PermissionError, match="sidecar"):
        product._validate_bound_a1_metadata(path, _load_json(path), "development")


def test_check_only_and_product_refuse_same_size_a1_exclusion_swap(bound_a1_package, monkeypatch):
    inputs, out, registry_dir, source_ids = bound_a1_package
    original_sidecar = _load_json(out / prepare_module.SIDECAR_NAME)
    kept_token, excluded_token = map(_gse_patient_token, source_ids[:2])
    excluded_row = next(row for row in original_sidecar["records"] if row["patient_id"] == excluded_token)

    derived_path = out / prepare_module.FREEZE_TABLE_NAME
    original_bytes = derived_path.read_bytes()
    swapped_bytes = original_bytes.replace(kept_token.encode(), excluded_token.encode())
    assert swapped_bytes != original_bytes
    assert len(swapped_bytes) == len(original_bytes)
    derived_path.write_bytes(swapped_bytes)
    derived_digest = hashlib.sha256(swapped_bytes).hexdigest()

    artifact_path = out / prepare_module.A1_EXCLUSIONS_NAME
    artifact = _load_json(artifact_path)
    original_exclusions = set(artifact["excluded_tokens"])
    swapped = sorted((original_exclusions - {excluded_token}) | {kept_token})
    assert len(swapped) == len(original_exclusions)
    artifact["excluded_tokens"] = swapped
    artifact["excluded_tokens_sha256"] = hashlib.sha256(
        json.dumps(swapped, separators=(",", ":")).encode()
    ).hexdigest()
    artifact["derived_features_sha256"] = derived_digest
    artifact_digest = _write_bound_json(artifact_path, artifact)

    release_path = out / prepare_module.RELEASE_TEMPLATE_NAME
    release = _load_json(release_path)
    release["a1_source_rule"].update(exclusion_artifact_sha256=artifact_digest, derived_features_sha256=derived_digest)
    runs = {run["package_id"]: run for run in release["runs"]}
    for name, package_id in zip(_PACKAGE_MANIFESTS, _PACKAGE_IDS):
        manifest_path = out / name
        manifest = _load_json(manifest_path)
        identity = manifest["identity_provenance"]
        manifest["provenance"]["a1_source_rule"].update(
            exclusion_artifact_sha256=artifact_digest,
            excluded_tokens_sha256=artifact["excluded_tokens_sha256"],
            derived_features_sha256=derived_digest,
        )
        if name in (prepare_module.SENSITIVITY_MANIFEST_NAME, prepare_module.FREEZE_MANIFEST_NAME):
            manifest["input_sha256"] = derived_digest
            sidecar_path = out / identity["sidecar"]
            sidecar = _load_json(sidecar_path)
            sidecar["records"] = [excluded_row if row["patient_id"] == kept_token else row for row in sidecar["records"]]
            identity["sidecar_sha256"] = _write_bound_json(sidecar_path, sidecar)
        manifest_digest = _write_bound_json(manifest_path, manifest)
        runs[package_id].update(input_sha256=manifest["input_sha256"], input_manifest_sha256=manifest_digest,
                                identity_sidecar_sha256=identity["sidecar_sha256"])
    _write_bound_json(release_path, release)

    with monkeypatch.context() as preparation:
        # The product fixture's historical hash override applies only to product checks.
        preparation.setattr(prepare_module, "_MAIN_FEATURES_SHA256", "0" * 64)
        with pytest.raises(PreparationError, match="artifact hashes do not match the pinned source and code"):
            _prepare(inputs, out, check_only=True, registry_dir=registry_dir, scratch_root=out.parent)
    freeze_path = out / prepare_module.FREEZE_MANIFEST_NAME
    with pytest.raises(PermissionError, match="A1"):
        product._validate_bound_a1_metadata(freeze_path, _load_json(freeze_path), "freeze")


def test_product_metadata_checks_registry(bound_a1_package):
    _, out, registry_dir, _ = bound_a1_package
    main_path = out / prepare_module.MANIFEST_NAME
    main = _load_json(main_path)
    registry_path = registry_dir / "OVERLAP_REGISTRY.tsv"
    registry_path.write_bytes(registry_path.read_bytes() + b"\n")
    with pytest.raises(PermissionError, match="registry"):
        product._validate_bound_a1_metadata(main_path, main, "development")


def test_signed_dimensions_require_exact_roster_and_all_prespecified_counts():
    kwargs = dict(input_cohorts=set(COHORTS), input_count=408, bladder_count=87,
                  excluded_count=33, derived_count=375, main_families=6,
                  conservative_families=4)
    assert prepare_module._signed_dimension_errors(**kwargs) == []
    assert prepare_module._signed_dimension_errors(**{**kwargs, "input_cohorts": set(COHORTS) | {"braun2020"}})
    for field, value in (("input_count", 407), ("bladder_count", 86), ("excluded_count", 32),
                         ("derived_count", 374), ("main_families", 5), ("conservative_families", 5)):
        assert prepare_module._signed_dimension_errors(**{**kwargs, field: value})


def test_product_metadata_refuses_missing_nonexcluded_freeze_identity(bound_a1_package):
    _, out, _, _ = bound_a1_package
    main_path = out / "a_p2_input_manifest.json"
    main = json.loads(main_path.read_text())
    freeze_path = out / "a_p2_input_manifest_freeze.json"
    freeze = json.loads(freeze_path.read_text())
    sidecar_path = out / "identity_sidecar_freeze.json"
    sidecar = json.loads(sidecar_path.read_text())
    sidecar["records"] = sidecar["records"][1:]
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
    freeze["identity_provenance"]["sidecar_sha256"] = hashlib.sha256(sidecar_path.read_bytes()).hexdigest()
    freeze_path.write_text(json.dumps(freeze), encoding="utf-8")
    with pytest.raises(PermissionError, match="identities"):
        product._validate_bound_a1_metadata(main_path, main, "development")


def test_product_refuses_bladder_pair_with_wrong_status_even_when_registry_hash_matches(tmp_path, monkeypatch):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir)
    inputs = _built_inputs(tmp_path)
    out = tmp_path / "scratch" / "prepared"
    _prepare(inputs, out, registry_dir=registry_dir, scratch_root=tmp_path / "scratch")
    monkeypatch.setattr(prepare_module, "DEFAULT_REGISTRY_DIR", registry_dir)
    path = registry_dir / "OVERLAP_REGISTRY.tsv"
    rows = _registry_rows(path)
    for row in rows:
        if {row["cohort_a"], row["cohort_b"]} == {"gse176307", "imvigor210"}:
            row["status"] = "NO_OVERLAP_DOCUMENTED"
            row["rule_id"] = ""
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    manifest_path = out / "a_p2_input_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["identity_provenance"]["overlap_registry_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(PermissionError, match="overlap evidence"):
        product._validate_bound_a1_metadata(manifest_path, manifest, "development")


def test_product_cannot_promote_tiny_invented_package_as_real(tmp_path, monkeypatch):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir)
    inputs, _ = _multi_patient_gse_inputs(tmp_path)
    out = tmp_path / "scratch" / "prepared"
    _prepare(inputs, out, registry_dir=registry_dir, scratch_root=tmp_path / "scratch")
    monkeypatch.setattr(prepare_module, "DEFAULT_REGISTRY_DIR", registry_dir)
    soft = inputs / "GSE176307_family.soft.gz"
    monkeypatch.setattr(prepare_module, "_GSE176307_SOFT_SHA256", hashlib.sha256(soft.read_bytes()).hexdigest())
    main_path = out / "a_p2_input_manifest.json"
    with pytest.raises(PermissionError, match="historical|dimensions"):
        product._validate_bound_a1_metadata(main_path, json.loads(main_path.read_text()), "development")


def test_product_refuses_tampered_a1_artifact_before_payload_access(tmp_path, monkeypatch):
    registry_dir = _copy_registries(tmp_path)
    _resolve_all_test_overlaps(registry_dir)
    inputs, _ = _multi_patient_gse_inputs(tmp_path)
    out = tmp_path / "scratch" / "prepared"
    _prepare(inputs, out, registry_dir=registry_dir, scratch_root=tmp_path / "scratch")
    monkeypatch.setattr(prepare_module, "DEFAULT_REGISTRY_DIR", registry_dir)
    artifact_path = out / "a_p2_atezo_freeze_exclusions.json"
    artifact_path.write_bytes(artifact_path.read_bytes() + b" ")
    manifest_path = out / "a_p2_input_manifest.json"
    with pytest.raises(PermissionError, match="artifact"):
        product._validate_bound_a1_metadata(manifest_path, json.loads(manifest_path.read_text()), "development")


def test_product_rejects_unresolved_freeze_sidecar_before_payload_access(bound_a1_package):
    _, out, _, _ = bound_a1_package
    main_path = out / "a_p2_input_manifest.json"
    main = json.loads(main_path.read_text())
    freeze_path = out / "a_p2_input_manifest_freeze.json"
    freeze = json.loads(freeze_path.read_text())
    sidecar_path = out / "identity_sidecar_freeze.json"
    sidecar = json.loads(sidecar_path.read_text())
    sidecar["records"][0]["resolution_status"] = "UNRESOLVED_OVERLAP"
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
    freeze["identity_provenance"]["sidecar_sha256"] = hashlib.sha256(sidecar_path.read_bytes()).hexdigest()
    freeze_path.write_text(json.dumps(freeze), encoding="utf-8")
    with pytest.raises(PermissionError, match="sidecar"):
        product._validate_bound_a1_metadata(main_path, main, "development")
