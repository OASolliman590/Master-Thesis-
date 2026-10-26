"""Historical evidence checks run only when explicitly requested."""
import os
import pytest


def pytest_collection_modifyitems(items):
    if os.environ.get("DAV_EVIDENCE") == "1":
        return
    skip = pytest.mark.skip(reason="historical evidence suite; set DAV_EVIDENCE=1 to run")
    for item in items:
        if "tests/evidence" in str(item.fspath):
            item.add_marker(skip)
