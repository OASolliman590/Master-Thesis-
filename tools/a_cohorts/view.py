"""Typed cohort metadata and validated views of loaded cohort tables."""
from __future__ import annotations

import csv
import os
import re
import threading
from contextlib import contextmanager
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from . import core

ROOT = Path(__file__).resolve().parents[2]
REPRESENTATION_FILE = ROOT / 'docs/cohorts/REPRESENTATION.tsv'

Cancer = Literal['melanoma', 'lung', 'kidney', 'bladder', 'gastric', 'liver', 'head_and_neck', 'multi']
Platform = Literal['rnaseq', 'microarray', 'nanostring', 'targeted_rna']
Unit = Literal['counts', 'tpm', 'fpkm', 'rpkm', 'probe_intensity', 'normalised_counts', 'cpm']
Transform = Literal['linear', 'log2', 'log2p1', 'other']
FeatureId = Literal['symbol', 'ensembl', 'entrez', 'probe']
DEEngine = Literal['deseq2', 'limma']
DrugClass = Literal['ANTI_PD_L1_AXIS', 'ANTI_CTLA4', 'DUAL_PD1_CTLA4', 'OTHER_EXCLUDED']
EndpointFamily = Literal['orr', 'clinical_benefit', 'source_label']

_CANCERS = {'melanoma', 'lung', 'kidney', 'bladder', 'gastric', 'liver', 'head_and_neck', 'multi'}
_PLATFORMS = {'rnaseq', 'microarray', 'nanostring', 'targeted_rna'}
_UNITS = {'counts', 'tpm', 'fpkm', 'rpkm', 'probe_intensity', 'normalised_counts', 'cpm'}
_TRANSFORMS = {'linear', 'log2', 'log2p1', 'other'}
_FEATURE_IDS = {'symbol', 'ensembl', 'entrez', 'probe'}
_DE_ENGINES = {'deseq2', 'limma'}
_DRUG_CLASSES = {'ANTI_PD_L1_AXIS', 'ANTI_CTLA4', 'DUAL_PD1_CTLA4', 'OTHER_EXCLUDED'}
_ENDPOINT_ORDER = ('orr', 'clinical_benefit', 'source_label')
_VALIDATION_LOCK = threading.RLock()


@dataclass(frozen=True)
class MeasurementRepresentation:
    platform: Platform
    unit: Unit
    transform: Transform
    feature_id: FeatureId


@dataclass(frozen=True)
class CohortMetadata:
    cohort_id: str
    cancer: Cancer
    representation: MeasurementRepresentation
    de_engine: DEEngine
    endpoint_families: tuple[EndpointFamily, ...]
    uniform_drug_class: DrugClass | None


@dataclass(frozen=True)
class CohortView:
    metadata: CohortMetadata
    expression_path: Path
    clinical_rows: list[dict[str, str]]


def _representation_rows() -> dict[str, dict[str, str]]:
    with REPRESENTATION_FILE.open(newline='') as stream:
        return {row['cohort_id']: row for row in csv.DictReader(stream, delimiter='\t')}


def _cancer(value: str) -> Cancer:
    key = value.strip().casefold()
    mapping = {
        'melanoma': 'melanoma',
        'lung': 'lung', 'lung (nsclc)': 'lung',
        'kidney': 'kidney', 'kidney (ccrcc)': 'kidney',
        'urothelial': 'bladder', 'bladder': 'bladder',
        'gastric': 'gastric',
        'liver': 'liver', 'liver (hcc)': 'liver',
        'head and neck': 'head_and_neck',
        'hnscc / melanoma / lung': 'multi',
    }
    result = mapping.get(key)
    if result not in _CANCERS:
        raise ValueError(f'Unmapped cancer: {value!r}')
    return result  # type: ignore[return-value]


def _endpoint_families(registry_row: dict[str, str]) -> tuple[EndpointFamily, ...]:
    text = registry_row['endpoints'].casefold()
    families = set()
    if ((re.search(r'\borr\b', text) and not re.search(r'\bnot\s+orr\b', text))
            or ('best response' in text and 'recist' in text)):
        families.add('orr')
    if 'clinical benefit' in text or 'clinical_benefit' in text or 'dcb/ndb' in text:
        families.add('clinical_benefit')
    if not families and ('source_binary' in text or 'treatment outcome' in text or 'treatment response' in text):
        families.add('source_label')
    return tuple(family for family in _ENDPOINT_ORDER if family in families)  # type: ignore[return-value]


def cohort_metadata(cohort: str) -> CohortMetadata:
    registry_row = core.check_allowed(cohort)
    if registry_row['role'].casefold() != 'development' or not registry_row['status'].startswith('SIGNED'):
        raise ValueError(f'{cohort} is not a signed development cohort')
    representation_row = _representation_rows().get(cohort)
    if representation_row is None:
        raise ValueError(f'{cohort} has no representation metadata')

    cancer = _cancer(registry_row['cancer'])
    representation_cancer = representation_row['cancer']
    platform = representation_row['platform']
    unit = representation_row['unit']
    transform = representation_row['transform']
    feature_id = representation_row['feature_id']
    de_engine = representation_row['de_engine']
    uniform_text = representation_row.get('uniform_drug_class', '').strip()
    uniform_drug_class = uniform_text or None
    if representation_cancer != cancer:
        raise ValueError(f'{cohort} cancer metadata disagrees with REGISTRY')
    if platform not in _PLATFORMS or unit not in _UNITS or transform not in _TRANSFORMS:
        raise ValueError(f'{cohort} has an uncontrolled representation value')
    if feature_id not in _FEATURE_IDS or de_engine not in _DE_ENGINES:
        raise ValueError(f'{cohort} has an uncontrolled feature ID or DE engine')
    if uniform_drug_class is not None and uniform_drug_class not in _DRUG_CLASSES:
        raise ValueError(f'{cohort} has an uncontrolled uniform drug class')
    expected_engine = 'deseq2' if platform == 'rnaseq' and unit == 'counts' else 'limma'
    if de_engine != expected_engine:
        raise ValueError(f'{cohort} DE engine does not match its measurement representation')
    endpoint_families = _endpoint_families(registry_row)
    if not endpoint_families:
        raise ValueError(f'{cohort} has no declared endpoint family')
    return CohortMetadata(
        cohort_id=cohort,
        cancer=cancer,
        representation=MeasurementRepresentation(platform, unit, transform, feature_id),
        de_engine=de_engine,  # type: ignore[arg-type]
        endpoint_families=endpoint_families,
        uniform_drug_class=uniform_drug_class,  # type: ignore[arg-type]
    )


_DRUG_CLASS_ALIASES: dict[str, DrugClass] = {
    'ANTIPDL1AXIS': 'ANTI_PD_L1_AXIS',
    'ANTIPD1': 'ANTI_PD_L1_AXIS', 'ANTIPDL1': 'ANTI_PD_L1_AXIS',
    'ANTIPD1PDL1': 'ANTI_PD_L1_AXIS', 'ANTIPD1ORPDL1': 'ANTI_PD_L1_AXIS',
    'ANTIPD1ORANTIPDL1': 'ANTI_PD_L1_AXIS', 'PD1ORPDL1UNSPECIFIED': 'ANTI_PD_L1_AXIS',
    'ANTIPD1ORPDL1UNSPECIFIED': 'ANTI_PD_L1_AXIS', 'ANTIPD1NIVOLUMAB': 'ANTI_PD_L1_AXIS',
    'NIVOLUMAB': 'ANTI_PD_L1_AXIS', 'OPDIVO': 'ANTI_PD_L1_AXIS',
    'PEMBROLIZUMAB': 'ANTI_PD_L1_AXIS', 'KEYTRUDA': 'ANTI_PD_L1_AXIS',
    'ATEZOLIZUMAB': 'ANTI_PD_L1_AXIS', 'TECENTRIQ': 'ANTI_PD_L1_AXIS',
    'DURVALUMAB': 'ANTI_PD_L1_AXIS', 'IMFINZI': 'ANTI_PD_L1_AXIS',
    'AVELUMAB': 'ANTI_PD_L1_AXIS', 'BAVENCIO': 'ANTI_PD_L1_AXIS',
    'CEMIPLIMAB': 'ANTI_PD_L1_AXIS', 'LIBTAYO': 'ANTI_PD_L1_AXIS',
    'DOSTARLIMAB': 'ANTI_PD_L1_AXIS', 'JEMPERLI': 'ANTI_PD_L1_AXIS',
    'RETIFANLIMAB': 'ANTI_PD_L1_AXIS', 'SINTILIMAB': 'ANTI_PD_L1_AXIS',
    'TORIPALIMAB': 'ANTI_PD_L1_AXIS', 'TISLELIZUMAB': 'ANTI_PD_L1_AXIS',
    'CAMRELIZUMAB': 'ANTI_PD_L1_AXIS', 'PDR001': 'ANTI_PD_L1_AXIS',
    'ANTICTLA4': 'ANTI_CTLA4', 'IPILIMUMAB': 'ANTI_CTLA4', 'YERVOY': 'ANTI_CTLA4',
    'TREMELIMUMAB': 'ANTI_CTLA4', 'IMJUDO': 'ANTI_CTLA4',
    'DUALPD1CTLA4': 'DUAL_PD1_CTLA4',
    'ANTIPD1PLUSANTICTLA4': 'DUAL_PD1_CTLA4',
    'ANTICTLA4PLUSANTIPD1': 'DUAL_PD1_CTLA4',
    'NIVOLUMABPLUSIPILIMUMAB': 'DUAL_PD1_CTLA4',
    'IPILIMUMABPLUSNIVOLUMAB': 'DUAL_PD1_CTLA4',
    'ANTIPD1NIVOLUMABPLUSIPILIMUMAB': 'DUAL_PD1_CTLA4',
    'ANTIPD1PLUSANTITIM3': 'OTHER_EXCLUDED', 'ANTIPD1PLUSANTICTLA4PLUSANTITIM3': 'OTHER_EXCLUDED',
    'ANTITIM3': 'OTHER_EXCLUDED', 'MBG453': 'OTHER_EXCLUDED', 'COBOLIMAB': 'OTHER_EXCLUDED',
    'CHEMO': 'OTHER_EXCLUDED', 'CHEMOTHERAPY': 'OTHER_EXCLUDED',
    'CARBOPLATIN': 'OTHER_EXCLUDED', 'CISPLATIN': 'OTHER_EXCLUDED',
    'PACLITAXEL': 'OTHER_EXCLUDED', 'NABPACLITAXEL': 'OTHER_EXCLUDED',
    'AXITINIB': 'OTHER_EXCLUDED', 'BEVACIZUMAB': 'OTHER_EXCLUDED',
    'METFORMIN': 'OTHER_EXCLUDED', 'ENTINOSTAT': 'OTHER_EXCLUDED',
    'VORINOSTAT': 'OTHER_EXCLUDED', 'SUNITINIB': 'OTHER_EXCLUDED',
    'LEUPROLIDE': 'OTHER_EXCLUDED', 'ADT': 'OTHER_EXCLUDED',
    'RADIATION': 'OTHER_EXCLUDED', 'RADIOTHERAPY': 'OTHER_EXCLUDED',
    'OTHEREXCLUDED': 'OTHER_EXCLUDED',
}
_DRUG_SEPARATOR = re.compile(r'\s*(?:\+|&|,|;|/|\bAND\b|\bPLUS\b)\s*', re.IGNORECASE)


def _drug_key(value: str) -> str:
    return re.sub(r'[^A-Z0-9]', '', value.upper())


def normalise_drug_class(raw: str) -> DrugClass:
    value = str(raw).strip()
    key = _drug_key(value)
    direct = _DRUG_CLASS_ALIASES.get(key)
    if direct is not None:
        return direct
    parts = [part.strip().strip("{}[]()\"' ") for part in _DRUG_SEPARATOR.split(value)]
    if len(parts) == 1:
        raise ValueError(f'Unmapped drug class: {raw!r}')
    classes = set()
    for part in parts:
        if not part:
            continue
        drug_class = _DRUG_CLASS_ALIASES.get(_drug_key(part))
        if drug_class is None:
            raise ValueError(f'Unmapped drug class: {raw!r}')
        classes.add(drug_class)
    if 'OTHER_EXCLUDED' in classes:
        return 'OTHER_EXCLUDED'
    if classes == {'ANTI_PD_L1_AXIS'}:
        return 'ANTI_PD_L1_AXIS'
    if classes == {'ANTI_CTLA4'}:
        return 'ANTI_CTLA4'
    if classes == {'ANTI_PD_L1_AXIS', 'ANTI_CTLA4'}:
        return 'DUAL_PD1_CTLA4'
    raise ValueError(f'Unmapped drug class: {raw!r}')


def _normalise_row_drug(raw: str, cohort: str, uniform_drug_class: DrugClass | None) -> DrugClass:
    raw_text = str(raw)
    try:
        drug_class = normalise_drug_class(raw_text)
    except ValueError:
        if raw_text.strip().upper() in {'', 'UNKNOWN', 'ICI'} and uniform_drug_class is not None:
            return uniform_drug_class
        raise ValueError(f'{cohort}: unmapped drug label {raw_text!r}') from None
    if uniform_drug_class is not None and drug_class != uniform_drug_class:
        raise ValueError(f'{cohort}: raw drug label {raw_text!r} contradicts uniform drug class')
    return drug_class


def _runtime_path(runtime: Path | None) -> Path:
    selected = runtime if runtime is not None else os.environ.get('THESIS_RUNTIME', core.RUNTIME)
    return Path(selected).expanduser().resolve()


def _runtime_root(runtime: Path) -> Path:
    if runtime.name == 'runtime' and runtime.parent.name == '.scratch':
        return runtime.parent.parent
    if runtime.is_relative_to(ROOT):
        return ROOT
    return runtime.parent


@contextmanager
def _loader_runtime(runtime: Path):
    root = _runtime_root(runtime)
    loader_path = root / 'tools/a_cohorts/core.py'
    registry_path = root / 'docs/cohorts/REGISTRY.tsv'
    originals = {
        'RUNTIME': core.RUNTIME,
        'ROOT': core.ROOT,
        'REGISTRY': core.REGISTRY,
        '__file__': core.__file__,
    }
    core.RUNTIME = runtime
    core.ROOT = root
    if registry_path.is_file():
        core.REGISTRY = registry_path
    if loader_path.is_file():
        core.__file__ = str(loader_path)
    try:
        yield
    finally:
        core.RUNTIME = originals['RUNTIME']
        core.ROOT = originals['ROOT']
        core.REGISTRY = originals['REGISTRY']
        core.__file__ = originals['__file__']


def _validated_manifest(cohort: str, runtime: Path) -> dict:
    with _VALIDATION_LOCK:
        with _loader_runtime(runtime):
            return core.validate(cohort)


def _normalise_cancer_row(raw: str) -> str:
    key = raw.strip().casefold()
    mapping = {
        'melanoma': 'melanoma',
        'lung': 'lung', 'lung non-squamous': 'lung', 'lung squamous': 'lung',
        'head and neck': 'head_and_neck', 'headneck': 'head_and_neck',
        'kidney': 'kidney', 'kidney (ccrcc)': 'kidney',
        'bladder': 'bladder', 'urothelial': 'bladder',
        'gastric': 'gastric', 'liver': 'liver', 'liver (hcc)': 'liver',
    }
    try:
        return mapping[key]
    except KeyError:
        raise ValueError(f'Unmapped per-patient cancer: {raw!r}') from None


def cohort_view(cohort: str, runtime: Path | None = None) -> CohortView:
    """Read `<runtime>/<cohort>/simple/` after the loader's strict validation.

    The selected runtime root is temporarily assigned to the loader while its
    own `validate` function checks manifests, output hashes, and alignment.
    """
    metadata = cohort_metadata(cohort)
    runtime_path = _runtime_path(runtime)
    _validated_manifest(cohort, runtime_path)
    output = runtime_path / cohort / 'simple'
    with (output / 'clinical.tsv').open(newline='') as stream:
        rows = [dict(row) for row in csv.DictReader(stream, delimiter='\t')]
    for row in rows:
        row['drug_class_normalised'] = _normalise_row_drug(
            row.get('drug_class', ''), cohort, metadata.uniform_drug_class)
        if metadata.cancer == 'multi':
            row['cancer_normalised'] = _normalise_cancer_row(row.get('cancer', ''))
    return CohortView(metadata, output / 'expression.tsv', rows)


def view_summary(view: CohortView) -> list[dict[str, str | int]]:
    counts = Counter()
    for row in view.clinical_rows:
        drug_class = row['drug_class_normalised']
        for family in view.metadata.endpoint_families:
            if family == 'orr':
                category = row.get('orr', '') or 'UNKNOWN'
            elif family == 'clinical_benefit':
                category = row.get('clinical_benefit', '') or 'UNKNOWN'
            else:
                category = (row.get('treatment_outcome') or row.get('raw_orr')
                            or row.get('raw_clinical_benefit') or 'UNKNOWN')
            counts[(drug_class, family, category)] += 1
    return [
        {'drug_class_normalised': drug_class, 'endpoint_family': family,
         'endpoint_category': category, 'patients': patients}
        for (drug_class, family, category), patients in sorted(counts.items())
    ]


def view_dict(view: CohortView) -> dict:
    return {'metadata': asdict(view.metadata), 'strata': view_summary(view)}
