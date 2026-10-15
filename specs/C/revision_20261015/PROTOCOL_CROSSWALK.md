# Protocol, internal plan and Paper C crosswalk

## Status vocabulary

- **University commitment:** explicitly present in the submitted protocol.
- **Later internal design:** proposed or approved after submission; not automatically an institutional amendment.
- **Computational sentinel:** retained for a defined analytical purpose.
- **Physical inventory:** requires receipt, lot, source and formulation evidence.
- **Research suitable:** requires a cell-culture-appropriate form and quality documentation.
- **UNKNOWN:** not verified from available records.

## Crosswalk

| Topic | Submitted MSc protocol | Later wet-lab plan v2 | September C draft | Approved revision | Prospective wet lab |
|---|---|---|---|---|---|
| Scientific chain | Clinical signatures → prostate methylation/expression → drug treatment → molecular/possible functional assessment | Mechanism-matched lesion → target engagement → restoration after washout → antigen-specific function → anti-PD-1 interaction | Disease-query reversal plus context/pharmacology | Matched `Q_M` vs `Q_E` independent responsiveness plus bounded discovery and transparent prioritisation | Tests the nominated mechanism and function prospectively |
| Drug scope | Computationally selected epigenetic drugs; accessible text gives DNMT/HDAC inhibitors as examples | Decitabine and entinostat core; tazemetostat conditional on EZH2/H3K27me3 gate | Decitabine, entinostat and tazemetostat sentinel set | Curated DNMT/HDAC/PRC2 primary universe; named drugs are not automatic winners | One or two pharmacodynamically qualified regimens |
| Models | Commercial human prostate cancer cells selected using molecular profiles | PC3/22Rv1 molecular qualification; LNCaP functional model subject to HLA/antigen checks | PC3 anchor with other lines contextual | Model chosen by B-barrier fit, target expression, chromatin state and assay tractability | STR/mycoplasma/baseline qualification required |
| Exposure | Not fixed in accessible protocol text | Mechanism-aware: repeated DNMTi, 24–48 h HDACi, delayed EZH2i | Common 24 h anchor | C1 common anchor is calibration; mechanism-aware contexts retained without superiority claims | Local target-engagement calibration determines final regimen |
| Endpoint | qPCR/Western; possible RNA-seq and immune co-culture | Target engagement, post-washout molecular restoration, HLA/antigen-specific killing and priming×anti-PD-1 interaction | Negative WTCS at common condition | Paired independent measured molecular responsiveness; functional claims reserved | Molecular and functional validation |
| Regulatory wording | Uses “FDA-approved epigenetic drugs” generically | Compound-specific status not sufficient to select regimen | Could be misread as applying to all three | Exact molecule/formulation/status required; no class-wide approval statement | Experimental source and suitability documented |

## Compound provenance table

| Compound | Protocol provenance | Computational role | Regulatory status as of 15 Oct 2026 | Physical inventory | Cell-culture suitability |
|---|---|---|---|---|---|
| Decitabine | DNMTi class fits submitted scope; later v2 core agent | Sentinel and candidate universe | FDA-approved for MDS formulations/indications; prostate use is not approved | UNKNOWN | UNKNOWN until exact product/lot/formulation is recorded |
| Azacitidine | DNMTi class fits submitted scope; user previously reported access | Candidate and pragmatic feasibility layer | Approved for defined haematologic indications, not prostate cancer | User-reported; not receipt-verified here | UNKNOWN; commercial formulation is not automatic research reagent |
| Entinostat | Later v2 core class-I HDAC agent | C1 sentinel and C2 candidate | Investigational; NCI describes it as being studied | UNKNOWN | UNKNOWN |
| Vorinostat | HDACi class fits submitted scope; user previously reported tablet access | Candidate and possible pragmatic pilot | FDA-approved for selected CTCL use, not prostate cancer | User-reported; not receipt-verified here | Commercial tablet suitability UNKNOWN |
| Ricolinostat | Later inventory discussion | Exploratory HDAC6-focused candidate | Research/clinical-stage HDAC6 inhibitor; not treated as class-I or pan-HDAC equivalent | User-reported; not receipt-verified here | Commercial tablet suitability UNKNOWN |
| Tazemetostat | Later v2 conditional EZH2 agent | C1 sentinel and mechanistic comparator | US accelerated-approval indications withdrawn 22 Jun 2026; not currently described as FDA-approved | UNKNOWN | UNKNOWN |

## Inventory rule

No compound receives a favourable computational rank because it is available. Availability is appended after the scientific evidence is frozen and may create a separately labelled **feasible pilot** nomination.

Before any wet-lab handoff is marked executable, record:

- exact active molecule and salt;
- supplier and catalogue;
- research-grade or commercial status;
- lot and certificate of analysis;
- purity;
- excipients;
- sterility/endotoxin where relevant;
- solvent and stock preparation;
- stability and storage;
- receipt and expiry;
- institutional safety approval.
