import pytest

from tools.a_dav.raw_question import build_raw_question



def s02_filelist_record():
    return {
        "study_id": "QR-GSE188249",
        "access_route": "PUBLIC_DIRECT",
        "exact_file_name": "filelist.txt",
    }




def test_controlled_rows_are_not_treated_as_filenames():
    records = {
        "records": [
            s02_filelist_record(),
            {
                "study_id": "QR-GSE198052",
                "access_route": "CONTROLLED",
                "exact_file_name": "",
            },
            {
                "study_id": "QR-GSE198052",
                "access_route": "PUBLIC_DIRECT",
                "exact_file_name": "GSE198052_RAW.tar",
            },
            {
                "study_id": "QR-GSE198052",
                "access_route": "PUBLIC_DIRECT",
                "exact_file_name": "filelist.txt",
            },
        ]
    }

    result = build_raw_question(records)
    s03 = next(row for row in result["questions"] if row["entry_id"] == "S03")

    assert s03["file_name_class_counts"] == {
        "RAW_ARCHIVE": 1,
        "FILELIST": 1,
        "MATRIX_NAME": 0,
    }


@pytest.mark.parametrize(
    "file_name,expected_class",
    [
        ("GSE000001_RAW.tar", "RAW_ARCHIVE"),
        ("filelist.txt", "FILELIST"),
        ("series_matrix.txt.gz", "MATRIX_NAME"),
    ],
)
def test_matrix_like_suffixes_are_classified_without_claiming_admission(
    file_name, expected_class
):
    records = {
        "records": [
            s02_filelist_record(),
            {
                "study_id": "QR-GSE198052",
                "access_route": "PUBLIC_DIRECT",
                "exact_file_name": file_name,
            }
        ]
    }

    result = build_raw_question(records)
    s03 = next(row for row in result["questions"] if row["entry_id"] == "S03")

    assert s03["file_names"] == [
        {"exact_file_name": file_name, "classification": expected_class}
    ]
    assert s03["matrix_name_present"] is (expected_class == "MATRIX_NAME")
    assert result["admitted_count"] == 0


def test_unrecognized_public_filename_fails_closed():
    records = {
        "records": [
            {
                "study_id": "QR-GSE198052",
                "access_route": "PUBLIC_DIRECT",
                "exact_file_name": "GSE198052_unexpected.bin",
            }
        ]
    }

    with pytest.raises(ValueError, match="unrecognized exact_file_name"):
        build_raw_question(records)
