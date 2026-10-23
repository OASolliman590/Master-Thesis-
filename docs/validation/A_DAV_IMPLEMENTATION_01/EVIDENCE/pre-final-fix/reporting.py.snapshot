"""Strict public aggregate export boundary for synthetic DAV software."""
from __future__ import annotations
from typing import Any
from .core import FLAGS, SchemaStore, dependency, digest, finish, public_summary, require, stage_boundary

REASON_CODES = frozenset({'PUBLIC_PAYLOAD_REJECTED', 'SMALL_CELL_POLICY_UNKNOWN'})


@stage_boundary('public_report')
def build_public_report(packet: dict[str, Any], *, schemas: SchemaStore | None = None) -> dict[str, Any]:
    store = schemas or SchemaStore()
    deps = {name: dependency(packet,name,store) for name in ('admission','baseline','longitudinal','split')}
    cfg = packet['config'].get('public_report',{})
    require(type(cfg.get('minimum_cell_count')) is int and cfg['minimum_cell_count'] >= 2
            and type(cfg.get('include_counts')) is bool, 'SMALL_CELL_POLICY_UNKNOWN', blocked=True)
    require(set(cfg) <= {'minimum_cell_count','include_counts','payload'}, 'PUBLIC_PAYLOAD_REJECTED')
    # Caller-supplied content is never an export channel, even for synthetic inputs.
    require('payload' not in cfg, 'PUBLIC_PAYLOAD_REJECTED')
    summary: dict[str, Any] = {'classification':'SYNTHETIC_ONLY','status':'SYNTHETIC_READY',
        'stage_statuses':{name:r['status'] for name,r in sorted(deps.items())},
        'receipt_hashes':{name:r['receipt_id'] for name,r in sorted(deps.items())},
        'config_sha256':digest(packet['config']), 'actual_source_review':'NOT_RUN',
        'actual_statistical_review':'NOT_RUN',
        'gate_table':[{'gate':'SYNTHETIC_SOFTWARE','status':'SYNTHETIC_READY'},
            {'gate':'SOURCE_REVIEW','status':'NOT_RUN'},{'gate':'INDEPENDENT_REVIEW','status':'NOT_RUN'},
            {'gate':'ENVIRONMENT_VALIDATION','status':'NOT_RUN'},{'gate':'STATISTICAL_RELEASE','status':'NOT_RUN'}],
        'limitation_table':[{'code':code,'status':'NOT_RUN'} for code in
            ['ACTUAL_SOURCE_REVIEW','AUTHENTICATED_INDEPENDENT_REVIEW','TARGET_ENVIRONMENT_VALIDATION','SCIENTIFIC_STATISTICAL_ACCEPTANCE']],
        'count_table':[], **dict.fromkeys(FLAGS,False)}
    prat = dependency(packet,'prat_review',store) if 'prat_review' in packet.get('dependencies',{}) else None
    if prat is not None:
        summary.pop('count_table')
        summary['limitation_table'].append({'code':'PRAT_COUNT_FREE_EXPORT','status':'ENFORCED'})
    if cfg['include_counts'] and prat is None:
        # Suppression applies to entire small denominators and avoids complementary cells.
        patients=len(packet['records'].get('patient_registry',[]))
        summary['patient_count'] = patients if patients >= cfg['minimum_cell_count'] else None
        summary['count_table']=[{'metric':'PATIENTS','count':summary['patient_count'],
                                 'disclosure':'AGGREGATE' if summary['patient_count'] is not None else 'SUPPRESSED'}]
    audit: list[dict[str, Any]] = [{'public_report':summary}]
    # Prat's export remains count-free even when this report permits aggregate counts.
    if prat is not None:
        audit.append({'prat_summary':public_summary(prat,include_counts=False)})
    return finish('public_report',packet,packet['records'],audit=audit,schemas=store)
