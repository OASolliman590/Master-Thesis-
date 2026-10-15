# Dependency-aware restart

```mermaid
flowchart TD
  DAV[Shared identity and episode intake] --> AB[A-BIO development evidence]
  DAV --> AP[A-PRED own release gates]
  DAV --> A1[A.1 paired analysis]
  AB --> BB[B broad A-anchored modules]
  BP[B fixed APM independent gates] --> BC[B frozen TCGA query]
  BB --> BC
  BC --> C[C measured matched-query evaluation]
  CP[C source and scorer preparation] --> C
  EP[E public evidence and model recovery] --> E[E public core]
  DS[D source and checkpoint compatibility] --> D1[D1 own benchmark gates]
  DM[D measured observables] --> D2[D2 measured-driver model]
  D1 --> DL[Optional learned coupling gates]
  D2 --> DL
  E --> EL[E_LAST optional activation]
  O[Admitted original observations and approvals] --> EL
```

Arrows denote scientific dependencies, not permission to start production. E has no dependency on D or original experiments. A.1 does not wait for B/C. A-P2 final-test availability does not block properly frozen development evidence. Measured D2 does not wait for STATE superiority. Only one production paper runs at once; no live job is interrupted.
