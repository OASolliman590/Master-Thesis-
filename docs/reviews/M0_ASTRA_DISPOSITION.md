# M0 final integration review

Reviewer: Astra orchestrator. Date: 5 September 2026. Scope: setup and first evidence audit, explicitly work-in-progress. No primary endpoint, complete spec, production workflow or biological result is approved by this milestone.

## Independent consultation and its limits

Opus was actually invoked through Antigravity using `claude-opus-4-6-thinking`. The initial run read documents but stopped on a denied git command without substantive findings. A resumed read-only run produced the attached review in Antigravity's internal artifact store. The orchestrator retrieved that artifact; the relay's short final response alone was insufficient. Both runs reported no repository changes. The second helper reported CLI 1.1.27 versus initial 1.1.22; record observed versions rather than assume a fixed binary. No permission-bypass flag was used.

M0_OPUS_RAW.md preserves the reviewer text, including errors. Its local file links and line references are historical. M0_OPUS_RUN.json records run provenance. This disposition takes precedence over reviewer recommendations.

## Findings accepted and tracked

- A and D lacked evidence reports in the reviewed snapshot. Separate bounded audits are now in progress outside the canonical repository. Their reports and new findings require a subsequent review.
- Preserve unresolved primary estimands for all four papers. Finish factual acquisition gates before seeking material design decisions.
- B needs CPC-GENE replicate/reanalysis accounting, specimen matching, covariate coverage and a cross-platform endpoint contract.
- C needs release-specific drug/line/condition QC, measured versus inferred gene coverage, local scoring/null contracts, and actual eligible immune-context units. Missing drug signatures are missing evidence, not zero biological effect.
- Add figure-to-claim boundaries to every specification. DrugBank access and clinical PK fields remain explicit acquisition questions.

## Reviewer corrections and rejected suggestions

1. The reviewer estimates 430 hours. The user's four months at five hours daily yields approximately 600 hours; 430 would implicitly assume fewer working days. Neither estimate guarantees four publishable studies, and laboratory time must be accounted for separately.
2. Finding 5 says no LNCaP chemical signatures were found without restricting the statement to the three drugs. The metadata contains 707 LNCAP chemical signatures overall. The three named drugs have only the stated PC3 coverage in the inspected Phase II file. Tazemetostat is present in the 2020 compound dictionary; 2020 signature coverage remains unresolved. No source-wide absence claim is accepted.
3. Finding 4 suggests an arbitrary percentage threshold before discussing alternative mechanisms. Reject that success-conditioned rule. Claim boundaries and relevant alternative mechanisms apply regardless of significance or direction.
4. Frangieh genetic perturbations in melanoma are functional annotations; they are not direct validation of drug-induced expression restoration in prostate. Specific RNA/protein gene coverage still requires matrix inspection.
5. GSE107298's 300 reanalysis-linked records and 108 records beyond unique patient codes are different quantities, not necessarily conflicting arithmetic. Resolve their exact relationship in an explicit provenance table before selecting specimens.
6. Not every unresolved technical choice requires a user interview. Research facts and routine implementation choices autonomously; present only material scientific tradeoffs or institutional decisions for approval.
7. The review's proposed multiweek gate durations are not adopted as measured estimates. Keep the existing four-month constraint and use bounded evidence tasks.

## Verification actually performed

The orchestrator independently recounted the cached GEO/GDC and LINCS signature metadata and checked 20 source-file SHA-256 hashes against saved manifests. Results: 210 CPC-GENE patient-code pairs; 497 matched TCGA cases across 501 sample IDs; 118,050 Phase II signatures; PC3 12,031 and LNCAP 707 chemical signatures; named-drug PC3 counts 15, 15 and 0 in that release. See M0_LOCAL_VERIFICATION.json. No matrices, clinical models, drug rankings or biological endpoints were evaluated.

The source audit scripts and manifests are research utilities, not production implementations. Full source caches are excluded from Git; their retrieval manifests preserve provenance. Root integration also checks staged JSON/Python syntax, file sizes, whitespace and credential patterns before committing.

## Disposition

Proceed with an explicitly labelled M0 work-in-progress commit after the staged-artifact checks pass. No ready-for-agent scientific ticket, validated milestone tag, or production analysis is authorized by this review. Continue evidence-grounded grilling, then complete and independently review all four spec packages.
