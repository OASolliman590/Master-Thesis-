# Foundation equation and measurement interface

The released foundation supplies the actual executable states/equations and uncertainties. This annex records the minimum expected interface, not permission to refit an incomplete core.

Small molecule: amount-based gut/central/peripheral PK or audited PBPK; positive volumes; events with exact amount, formulation, time and route. Culture nominal/free/intracellular exposures and systemic plasma/tumour exposures have separate context IDs. Antibody pharmacokinetics, occupancy and functional blockade are not identical states.

PD: a proximal engagement state and a separately observed phenotype/protein state may use `dP/dt = kP * (P_inf(exposure, engagement) - P)` only if that structure is qualified. Initial conditions come from baseline/history. Washout changes exposure; it does not instantaneously reset P. DNMT incorporation/cell-cycle assumptions are not inherited from an HDAC turnover fit.

QSP: the foundation must expose tumour/target count T, immune count E and any separate immune-function state F; direct tumour growth/toxicity is separated from immune-mediated killing. The observation interface accepts assay-scale requests, not gene-list-to-parameter guesses. A culture model does not gain human trafficking simply because the extension has donor data.

Mappings: qPCR normalized log expression with reference-gene/error handling; flow normalized fluorescence or counts with tumour/immune gates, not uncalibrated receptor copies; Western relative protein with dynamic-range/loading controls; secreted concentration with actual medium volume; functional target counts/death fractions distinct from mixed immune/tumour assay signals. Their full actual implementations and versions are required in the frozen foundation, and X1 verifies comparability before use.

A compatible adapter imports the released `simulate/observe/read_uncertainty` interfaces. It never reconstructs a new foundation silently from this annex. Different compound, context, assay scale or recognition mechanism requires an explicit adaptation decision and a new version.
