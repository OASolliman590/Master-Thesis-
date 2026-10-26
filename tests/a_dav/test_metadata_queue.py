from collections import Counter

import pytest

from tools.a_dav.metadata_queue import build_metadata_queue



def synthetic_crosswalk(rows):
    return {"lanes": {"I": rows, "E": []}}






@pytest.mark.parametrize(
    "crosswalk, message",
    [
        ({"lanes": {"I": []}}, "missing lane"),
        (
            synthetic_crosswalk(
                [
                    {"entry_id": "SYN-1", "public_series_accessions": ["GSE000001"]},
                    {"entry_id": "SYN-1", "public_series_accessions": ["GSE000002"]},
                ]
            ),
            "duplicate",
        ),
        (
            synthetic_crosswalk(
                [
                    {
                        "entry_id": "SYN-1",
                        "public_series_accessions": ["G" + "SM0000001"],
                    }
                ]
            ),
            "accession",
        ),
        (
            synthetic_crosswalk(
                [
                    {
                        "entry_id": "SYN-1",
                        "public_series_accessions": ["GSE000001-G" + "SM0000002"],
                    }
                ]
            ),
            "accession",
        ),
    ],
)
def test_invalid_crosswalk_fails_closed(crosswalk, message):
    with pytest.raises(ValueError, match=message):
        build_metadata_queue(crosswalk)


def test_supported_accession_shapes_and_controlled_precedence():
    crosswalk = {
        "lanes": {
            "I": [
                {"entry_id": "GEO", "public_series_accessions": ["GSE000001"]},
                {
                    "entry_id": "EGA",
                    "public_series_accessions": ["GSE000002", "EGAS00000000001"],
                },
                {"entry_id": "PRJ", "public_series_accessions": ["PRJEB23709"]},
                {
                    "entry_id": "LABEL",
                    "public_series_accessions": ["EGAD00000000001", "IMvigor210CoreBiologies"],
                },
            ],
            "E": [],
        }
    }

    records = build_metadata_queue(crosswalk)["queue"]
    assert [record["queue_class"] for record in records] == [
        "PUBLIC_GEO_FILELIST",
        "CONTROLLED_LANDING_ONLY",
        "NON_GEO_PUBLIC",
        "CONTROLLED_LANDING_ONLY",
    ]

