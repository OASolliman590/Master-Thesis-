# Drug universe and identity contract

## Primary universe

The protocol-aligned primary universe contains directly acting compounds in:

- DNA methyltransferase inhibition;
- histone deacetylase inhibition, retaining isoform/class selectivity;
- EZH2/PRC2 modulation, distinguishing catalytic EZH2, EED and other PRC2 mechanisms.

This is not a claim that all members are clinically approved, biologically equivalent or suitable for the same exposure window.

## Conditional exploratory universe

BET, LSD1/KDM1A, G9a/GLP, other lysine methyltransferases/demethylases and chromatin regulators may enter only when:

1. a predeclared B barrier or programme supplies a plausible target link;
2. parent structure and mechanism are curated from primary/official sources;
3. a measured perturbation exists in an eligible context;
4. the compound answers the same restoration question;
5. inclusion is frozen before outcome ranking.

## Canonical identity

Every compound record preserves:

- source database and original ID;
- canonical parent molecule;
- canonical SMILES and InChIKey;
- salt, solvate and formulation;
- aliases and code names;
- direct targets and evidence source;
- indirect targets and polypharmacology;
- mechanism subclass;
- clinical/regulatory status with date and jurisdiction;
- experimental context and source;
- duplicate/overlap links;
- wet-lab product status as a separate field.

Fuzzy name matching is prohibited for merges. Structures, authoritative IDs and documented aliases control.

## Independent compound unit

The following are not independent compounds:

- multiple BRD or catalogue IDs for the same parent;
- salts or formulations of one parent unless the formulation is the scientific comparison;
- batches, wells, signatures or releases;
- the same experiment mirrored in multiple repositories.

## Mechanism corrections

Raw database MOA labels are retained as source fields but never accepted automatically. Known errors, including non-DNMT chromatin inhibitors appearing under broad DNMT labels, require explicit correction records rather than silent rewriting.

## Inclusion statuses

- `eligible_primary_universe`
- `eligible_exploratory_universe`
- `identity_pending`
- `mechanism_pending`
- `coverage_only`
- `excluded_out_of_scope`

Known drugs do not define success. A negative or unranked compound remains in the audit trail when it was eligible.
