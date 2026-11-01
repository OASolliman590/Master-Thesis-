"""Command line entry point."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from .core import ADAPTERS, Client, Lead, adapter_for, draft_plan, save_fastq, save_packets, resolve_lead, ChallengeError, Record


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover public source metadata; outputs are proposals")
    sub = parser.add_subparsers(dest="command", required=True)
    search = sub.add_parser("search")
    search.add_argument("--queries", required=True)
    search.add_argument("--out", required=True)
    resolve = sub.add_parser("resolve")
    resolve.add_argument("--id", required=True)
    resolve.add_argument("--out", required=True)
    fastq = sub.add_parser("fastq")
    fastq.add_argument("--project", required=True)
    fastq.add_argument("--out", required=True)
    fastq.add_argument("--strategy", default="RNA-Seq")
    draft = sub.add_parser("draft-fetch-plan")
    draft.add_argument("--packet", required=True)
    draft.add_argument("--cohort", required=True)
    draft.add_argument("--out", required=True)
    args = parser.parse_args()
    if args.command == "draft-fetch-plan":
        draft_plan(Path(args.packet), args.cohort, Path(args.out))
        return 0
    client = Client()
    if args.command == "resolve":
        rec = resolve_lead(adapter_for(args.id, client), args.id, client)
        save_packets(Path(args.out), [(rec, [])], client)
    elif args.command == "fastq":
        try:
            save_fastq(args.project, Path(args.out), client, args.strategy)
        except ChallengeError:
            client.blocked = True
            save_packets(Path(args.out), [(Record(args.project, "ena", status="BLOCKED_BY_CHALLENGE"), [])], client)
    else:
        raw = Path(args.queries).read_bytes()
        queries = json.loads(raw)
        if not isinstance(queries, list):
            raise ValueError("queries must be a JSON array")
        leads: dict[tuple[str, str], list[str]] = {}
        blocked_records = []
        for q in queries:
            name, term, qid = q["adapter"], q["query"], q["id"]
            try:
                for lead in ADAPTERS[name](client).search(term):
                    leads.setdefault((lead.adapter, lead.identifier), []).append(qid)
            except ChallengeError:
                client.blocked = True
                blocked_records.append((Record(qid, name, status="BLOCKED_BY_CHALLENGE"), [qid]))
                break
        records = blocked_records
        if not blocked_records:
            blocked_adapters: set[str] = set()
            for (name, identifier), ids in leads.items():
                if name in blocked_adapters:
                    continue
                record = resolve_lead(ADAPTERS[name](client), identifier, client)
                records.append((record, ids))
                if record.status == "BLOCKED_BY_CHALLENGE":
                    blocked_adapters.add(name)
        save_packets(Path(args.out), records, client, hashlib.sha256(raw).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
