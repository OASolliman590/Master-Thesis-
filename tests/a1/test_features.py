from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import replace

import pytest

from tools.a1.authorization import read_released_inputs
from tools.a1.features import build_pair_analysis_rows, fixed_long_feature_memberships, score_long_features
from tools.a_meta.provenance import canonical_sha256
from tools.a_scoring.core import DEFAULT_PANELS


def _contract():
    value = fixed_long_feature_memberships()
    return value.ap2_panels, value.custom_panels, value.m5m6_genes, value.aliases


def _matrix_inputs(ap2, custom, m5m6, aliases, *, missing=()):
    members = {gene for panel in (*ap2.values(), *custom.values()) for gene in panel}
    members.update(m5m6)
    members.update(("GZMA", "PRF1"))
    symbols = sorted(members - set(missing))
    return symbols, [[3.0, 7.0] for _ in symbols]


def _score(ap2, custom, m5m6, aliases, symbols, matrix, *, representation=None, source_scale=None, **kwargs):
    representation = representation or {"platform": "rnaseq", "unit": "tpm", "transform": "linear"}
    source_scale = source_scale or "rnaseq:tpm:linear"
    tpm_route = kwargs.pop("tpm_route", "invented-qualified-tpm-route")
    tpm_qualified = kwargs.pop("tpm_qualified", True)
    return score_long_features(
        symbols,
        ("sample-a", "sample-b"),
        matrix,
        representation=representation,
        source_scale=source_scale,
        ap2_panels=ap2,
        custom_panels=custom,
        m5m6_genes=m5m6,
        aliases=aliases,
        tpm_route=tpm_route,
        tpm_qualified=tpm_qualified,
        fixture_only=True,
        **kwargs,
    )


def test_all_fixed_units_survive_overlaps_with_distinct_methods_and_scales():
    ap2, custom, m5m6, aliases = _contract()
    symbols, matrix = _matrix_inputs(ap2, custom, m5m6, aliases)
    result = _score(ap2, custom, m5m6, aliases, symbols, matrix)

    assert len(ap2) == 4
    assert len(custom) == 11
    assert len(m5m6) == 21
    assert set(result.values_by_unit) == {
        *(f"AP2:{panel}" for panel in ap2), "CYT",
        *(f"CUSTOM:{panel}" for panel in custom),
        *(f"M5M6:{gene}" for gene in m5m6),
    }
    for panel in DEFAULT_PANELS:
        assert result.values_by_unit[f"AP2:{panel}"] == pytest.approx((2.0, 3.0))
        assert result.method_id_by_unit[f"AP2:{panel}"] != result.method_id_by_unit[f"CUSTOM:{panel}"]
        assert result.effect_scale_by_unit[f"AP2:{panel}"] == "LOG2_TPMPLUS1_PANEL_MEAN"
        assert result.effect_scale_by_unit[f"CUSTOM:{panel}"] == "SOURCE_SCALE_PANEL_MEAN:rnaseq:tpm:linear"
    assert result.values_by_unit["CYT"] == pytest.approx((3.0, 7.0))
    assert result.metadata["representation"] == {"platform": "rnaseq", "unit": "tpm", "transform": "linear"}


def test_aliases_are_resolved_before_strict_coverage_and_membership_is_exact():
    ap2, custom, m5m6, aliases = _contract()
    member_units = {
        gene: f"AP2:{panel}"
        for panel, members in ap2.items()
        for gene in members
    }
    member_units.update({
        gene: f"CUSTOM:{panel}"
        for panel, members in custom.items()
        for gene in members
    })
    member_units.update({gene: f"M5M6:{gene}" for gene in m5m6})
    alias_pair = next((source, target) for source, target in aliases.items() if target in member_units and source != target)
    symbols, matrix = _matrix_inputs(ap2, custom, m5m6, aliases)
    canonical = alias_pair[1]
    index = symbols.index(canonical)
    symbols[index] = alias_pair[0]
    result = _score(ap2, custom, m5m6, aliases, symbols, matrix)
    expected = 2.0 if member_units[canonical].startswith("AP2:") else 3.0
    assert result.values_by_unit[member_units[canonical]][0] == expected

    changed = dict(custom)
    panel = next(iter(changed))
    changed[panel] = changed[panel][:-1] + ("ALTERED_GENE",)
    with pytest.raises(ValueError, match="cannot override frozen"):
        score_long_features(
            symbols,
            ("sample-a", "sample-b"),
            matrix,
            representation={"platform": "rnaseq", "unit": "tpm", "transform": "linear"},
            source_scale="rnaseq:tpm:linear",
            ap2_panels=ap2,
            custom_panels=changed,
            m5m6_genes=m5m6,
            aliases=aliases,
            tpm_route="fixture-route",
            tpm_qualified=True,
        )


def test_strict_coverage_and_scale_declaration_refuse_inconsistent_inputs():
    ap2, custom, m5m6, aliases = _contract()
    missing_gene = custom[next(iter(custom))][0]
    symbols, matrix = _matrix_inputs(ap2, custom, m5m6, aliases, missing=(missing_gene,))
    result = _score(ap2, custom, m5m6, aliases, symbols, matrix)
    missing_panel = next(name for name, members in custom.items() if missing_gene in members)
    assert result.values_by_unit[f"CUSTOM:{missing_panel}"] == (None, None)
    assert result.coverage_by_unit[f"CUSTOM:{missing_panel}"]["complete"] is False
    assert result.coverage_by_unit[f"CUSTOM:{missing_panel}"]["missing"] == (missing_gene,)

    with pytest.raises(ValueError, match="does not match the expression representation"):
        score_long_features(
            symbols,
            ("sample-a", "sample-b"),
            matrix,
            representation={"platform": "rnaseq", "unit": "tpm", "transform": "linear"},
            source_scale="log2_normalised_counts",
            fixture_only=True,
            ap2_panels=ap2,
            custom_panels=custom,
            m5m6_genes=m5m6,
            aliases=aliases,
        )


def test_raw_count_route_is_refused_and_ap2_requires_qualified_linear_tpm():
    ap2, custom, m5m6, aliases = _contract()
    symbols, matrix = _matrix_inputs(ap2, custom, m5m6, aliases)
    with pytest.raises(ValueError, match="voom/dream"):
        score_long_features(
            symbols,
            ("sample-a", "sample-b"),
            matrix,
            representation={"platform": "rnaseq", "unit": "counts", "transform": "linear"},
            source_scale="rnaseq:counts:linear",
            fixture_only=True,
            ap2_panels=ap2,
            custom_panels=custom,
            m5m6_genes=m5m6,
            aliases=aliases,
        )

    unqualified = _score(
        ap2, custom, m5m6, aliases, symbols, matrix,
        representation={"platform": "microarray", "unit": "log2_intensity", "transform": "identity"},
        source_scale="microarray:log2_intensity:identity",
        tpm_route=None,
        tpm_qualified=False,
    )
    assert all(unqualified.values_by_unit[f"AP2:{panel}"] == (None, None) for panel in DEFAULT_PANELS)
    assert unqualified.coverage_by_unit["CYT"]["reason"] == "qualified_linear_rnaseq_tpm_route_required"


def _write_tsv(path, rows, columns):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_scoped_pair_feature_endpoint_join_keeps_all_fixed_units_and_scales(tmp_path):
    root = tmp_path / "root"
    decisions = root / "docs" / "decisions"
    decisions.mkdir(parents=True)
    decision = decisions / "INVENTED_FEATURE_JOIN.md"
    decision.write_text("invented feature join decision\n", encoding="utf-8")
    fixed = fixed_long_feature_memberships()
    representation = {"platform": "rnaseq", "unit": "tpm", "transform": "linear"}
    policy = {
        "analysis_method_id": "lm_change_response_covariates_v1",
        "assay_id": "invented-qualified-bulk-rnaseq",
        "covariates": [],
        "endpoint_id": "invented-response",
        "regimen_id": "invented-ici-only",
        "representation": representation,
        "source_scale": "rnaseq:tpm:linear",
        "tpm_qualified": True,
        "tpm_route": "invented-linear-tpm-contract",
        "window_id": "invented-on-window",
        "unit_identities": {},
    }
    all_units = {
        *(f"AP2:{panel}" for panel in fixed.ap2_panels), "CYT",
        *(f"CUSTOM:{panel}" for panel in fixed.custom_panels),
        *(f"M5M6:{gene}" for gene in fixed.m5m6_genes),
    }
    for unit in all_units:
        if unit.startswith("AP2:"):
            family = "panel"
            panel_family = "A_P2"
            multiplicity = "A_P2_PANELS"
        elif unit.startswith("CUSTOM:"):
            family = "custom_panel"
            panel_family = "A_LONG_CUSTOM"
            multiplicity = "A_LONG_CUSTOM_PANELS"
        elif unit.startswith("M5M6:"):
            family = "m5m6_gene"
            panel_family = "M5M6"
            multiplicity = "M5M6_GENES"
        else:
            family = "comparator"
            panel_family = "CYT"
            multiplicity = "CYT_SINGLETON"
        policy["unit_identities"][unit] = {
            "unit_family": family,
            "panel_family": panel_family,
            "multiplicity_family_id": multiplicity,
        }

    study = "invented-release-cohort"
    pairs = [{
        "study_id": study, "patient_id": "invented-patient", "pair_id": "opaque-pair-1",
        "selected": "true", "pre_specimen_id": "opaque-pre", "on_specimen_id": "opaque-on",
        "pre_assay_id": "pre-assay", "on_assay_id": "on-assay",
        "endpoint_id": "invented-response", "regimen_id": "invented-ici-only",
        "window_id": "invented-on-window", "same_lesion": "true", "pair_day_distance": "10",
        "pre_day_precision": "exact", "on_day_precision": "exact",
        "pre_day_numeric": "-2", "on_day_numeric": "8",
        "day_distance_to_target": "2", "timing_ambiguity": "none",
        "source_family_id": "invented-source-family",
        "overlap_receipt_id": hashlib.sha256(b"invented-overlap-receipt").hexdigest(),
        "overlap_status": "UNRESOLVED",
        "admission_receipt": "invented-admission-receipt",
        "pre_source_locator": "invented://pre", "on_source_locator": "invented://on",
        "pre_source_confidence": "invented-high", "on_source_confidence": "invented-high",
        "pre_annotation_id": "invented-annotation", "on_annotation_id": "invented-annotation",
        "pre_measurement_comparability_id": "invented-tpm-v1",
        "on_measurement_comparability_id": "invented-tpm-v1",
        "pre_day_origin": "invented-first-dose", "on_day_origin": "invented-first-dose",
    }]
    expression_rows = []
    genes = sorted({gene for members in (*fixed.ap2_panels.values(), *fixed.custom_panels.values()) for gene in members} | set(fixed.m5m6_genes) | {"GZMA", "PRF1"})
    for sample_id, value in (("opaque-pre", "3"), ("opaque-on", "7")):
        for gene in genes:
            expression_rows.append({
                "study_id": study, "sample_id": sample_id,
                "assay_id": "pre-assay" if sample_id == "opaque-pre" else "on-assay",
                "gene_id": gene, "value": value,
            })
    endpoints = [{
        "study_id": study, "patient_id": "invented-patient",
        "endpoint_id": "invented-response", "response": "R",
    }]
    source_rows = {"pairs": pairs, "expression": expression_rows, "endpoint": endpoints}
    source_paths = {}
    field_maps = {}
    identity_fields = {}
    permitted_fields = []
    for name, rows in source_rows.items():
        columns = list(rows[0])
        path = tmp_path / f"{name}.tsv"
        _write_tsv(path, rows, columns)
        source_paths[name] = path
        field_maps[name] = {column: column for column in columns}
        identity_fields[name] = (
            ["study_id", "sample_id"] if name == "expression"
            else ["study_id", "patient_id"]
        )
        permitted_fields.extend(f"{name}:{column}" for column in columns)
    bindings = {
        "feature_membership_sha256": fixed.membership_sha256,
        "pair_manifest_sha256": hashlib.sha256(source_paths["pairs"].read_bytes()).hexdigest(),
        "representation_sha256": canonical_sha256(representation),
    }
    manifest = {
        "schema": "a_long_release_input_manifest_v1",
        "data_classification": "PRIVATE_PATIENT_LEVEL",
        "cohort_ids": [study],
        "source_files": {name: path.name for name, path in source_paths.items()},
        "field_maps": field_maps,
        "identity_fields": identity_fields,
        "permitted_fields": sorted(permitted_fields),
        "scope_bindings": bindings,
    }
    manifest_path = tmp_path / "input-manifest.json"
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    manifest_path.write_bytes(manifest_bytes)
    policy_sha = canonical_sha256(policy)
    record = {
        "record_type": "a_long_user_release_v1",
        "record_status": "APPROVED",
        "data_classification": "PRIVATE_PATIENT_LEVEL",
        "release_scope": "N13_FEATURE_JOIN",
        "operation": "pair_to_analysis",
        "policy_sha256": policy_sha,
        "input_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "source_sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in source_paths.items()},
        "cohorts": [study],
        "permitted_fields": sorted(permitted_fields),
        **bindings,
        "decision": {
            "identity": decision.stem,
            "path": "docs/decisions/INVENTED_FEATURE_JOIN.md",
            "sha256": hashlib.sha256(decision.read_bytes()).hexdigest(),
        },
    }
    release_path = tmp_path / "user-release.json"
    release_path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
    released = read_released_inputs(
        manifest_path, release_path,
        release_scope="N13_FEATURE_JOIN", operation="pair_to_analysis",
        policy_sha256=policy_sha, root=root, decisions_dir=decisions,
        allow_outcomes=True,
    )

    rows, coverage = build_pair_analysis_rows(released, policy=policy, allow_outcomes=True)

    assert len(rows) == 37
    by_unit = {row["unit"]: row for row in rows}
    assert len(fixed.ap2_panels) == 4 and len(fixed.custom_panels) == 11 and len(fixed.m5m6_genes) == 21
    for panel in fixed.ap2_panels:
        assert by_unit[f"AP2:{panel}"]["pre_value"] == pytest.approx(2.0)
        assert by_unit[f"AP2:{panel}"]["on_value"] == pytest.approx(3.0)
    assert by_unit["CYT"]["pre_value"] == pytest.approx(3.0)
    assert by_unit[next(unit for unit in by_unit if unit.startswith("CUSTOM:"))]["pre_value"] == pytest.approx(3.0)
    assert by_unit[f"M5M6:{fixed.m5m6_genes[0]}"]["pre_value"] == pytest.approx(3.0)
    assert all(row["response"] == "R" for row in rows)
    assert all(row["endpoint_id"] == "invented-response" for row in rows)
    assert len(coverage) == 37

    mismatched_tables = {name: [dict(row) for row in table] for name, table in released.tables.items()}
    mismatched_tables["endpoint"][0]["endpoint_id"] = "other-invented-endpoint"
    table_digest = hashlib.sha256(json.dumps(
        mismatched_tables, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")).hexdigest()
    mismatched_release = replace(released, tables=mismatched_tables, tables_sha256=table_digest)
    with pytest.raises(ValueError, match="endpoint identity|source identity differs"):
        build_pair_analysis_rows(mismatched_release, policy=policy, allow_outcomes=True)


def test_pair_to_analysis_api_defaults_locked_before_release_object_access():
    with pytest.raises(PermissionError, match="allow_outcomes=True"):
        build_pair_analysis_rows(object(), policy={})
