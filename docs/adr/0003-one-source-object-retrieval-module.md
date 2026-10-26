# One source object retrieval module; the per-packet fetchers are deleted

By October 2026 the A-DAV packets had produced five urllib fetchers, five host allowlists, seven object allowlists hard-coded in code, four rate limiters and two resume-and-hash implementations. The modules involved were object_verification, private_retrieval, filelist_fetch, listing_fetch, their planners and lane_crosswalk.

We decided on 25 Oct 2026 to replace them with one retrieval module:
- It owns host policy, request caps, request spacing, retry with backoff on transient errors, bounded reads, resume, SHA-256, and atomic publishing into the content-addressed store.
- Fetch plans and allowlists are data files.
- Each repository (GEO, ENA, GitHub at a pinned commit, cBioPortal) gets one thin URL adapter.

Once their callers have moved, the old fetchers are deleted rather than kept alongside the new module, because keeping two retrieval paths is how the duplication arose. Their evidence remains in git history and in docs/validation.
