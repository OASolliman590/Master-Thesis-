import os
from pathlib import Path

import pytest

from tools.a_dav.ingest import run_ingest


@pytest.mark.skipif(not os.environ.get("DAV_REAL_STORE"), reason="DAV_REAL_STORE is not configured")
def test_pinned_riaz_source_tracer(tmp_path):
    result = run_ingest("riaz_gse91061", "A_BASELINE_BIO", Path(os.environ["DAV_REAL_STORE"]),
                        tmp_path / "real-source-tracer", allow_external_out=True)
    counts = result["summary"]["counts"]
    assert counts["geo_samples"] == 109
    assert counts["pre_samples"] == 51
    assert counts["on_samples"] == 58
    assert counts["unique_patients"] == 65
    assert counts["baseline_samples_linked_to_patient"] == 51
