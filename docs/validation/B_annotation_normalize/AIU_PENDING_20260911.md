# B-G2 AIU Python 3.11 portability gate pending

**Attempted:** 11 September 2026
**Status:** connectivity passed; payload transfer and execution did not occur

The existing authenticated `omics` SSH alias reached the AIU interpreter, which reported Python 3.11.16. A new empty isolated scratch directory was created under the approved planning root.

Transfer of the private-repository B-G2 code, B-G1 compatibility module, proposed plan/schema and synthetic tests was then rejected by the local security review as sensitive egress requiring more specific payload authorization. The rejection was respected. No file was transferred, no remote command used the new implementation, no test or cohort job started, and no result is claimed. The remote scratch directory contains no copied project payload from this attempt.

This is a deferral receipt, not a failed software test and not a scientific-analysis result. The exact-hash Python 3.11/POSIX portability gate remains pending; the parent-accepted local Python 3.12 synthetic checkpoint is unaffected.
