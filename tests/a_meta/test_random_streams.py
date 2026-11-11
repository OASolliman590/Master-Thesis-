from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tools.a_meta.random_streams import RANDOM_STREAMS, derive_task_seed, seed_for_task
from tools.r_bridge import run_r


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "r/scripts/freeze_checks/random_streams.R"


@pytest.mark.requires_r
def test_r_and_python_random_stream_contracts_match_on_synthetic_indices(tmp_path):
    receipt_root = tmp_path / "synthetic-receipts"
    result = run_r(
        SCRIPT,
        {},
        {
            "receipt_dir": str(receipt_root),
            "expected_outputs": ["checks.tsv", "task_seeds.tsv", "random_stream_table.tsv"],
        },
        tmp_path / "random-stream-checks",
    )

    with result.outputs["random_stream_table.tsv"].open(newline="", encoding="utf-8") as stream:
        r_streams = {row["stream"]: row for row in csv.DictReader(stream, delimiter="\t")}
    assert set(r_streams) == set(RANDOM_STREAMS)
    for stream, contract in RANDOM_STREAMS.items():
        assert int(r_streams[stream]["seed"]) == contract.seed
        assert r_streams[stream]["task_id"] == contract.task_id
        assert (r_streams[stream]["reported_only"].casefold() == "true") is contract.reported_only
    assert seed_for_task("a_p2_bootstrap") == int(r_streams["a_p2_bootstrap"]["seed"])

    with result.outputs["task_seeds.tsv"].open(newline="", encoding="utf-8") as stream:
        task_rows = list(csv.DictReader(stream, delimiter="\t"))
    for row in task_rows:
        assert int(row["seed"]) == derive_task_seed(row["stream"], row["task_id"])

    with result.outputs["checks.tsv"].open(newline="", encoding="utf-8") as stream:
        checks = {row["check"]: row["value"] for row in csv.DictReader(stream, delimiter="\t")}
    assert checks["a_p2_repeat_identical"] == "TRUE"
    assert checks["a_p2_other_seed_differs"] == "TRUE"
    assert checks["a_p2_strata_order"] == "R,NR"
    assert checks["a_p1_strata_order"] == "O,SD,PD"
    assert checks["split_r_train_odd_n"] == "4"
    assert checks["split_nr_train_odd_n"] == "2"
    assert checks["a_p2_reordered_input_equivalent"] == "TRUE"
    assert checks["split_reordered_input_equivalent"] == "TRUE"
    assert checks["a_p2_tiny_expected_assignment"] == "TRUE"

    bootstrap_receipt = json.loads((receipt_root / "bootstrap" / "receipt.json").read_text())
    split_receipt = json.loads((receipt_root / "splits" / "receipt.json").read_text())
    assert bootstrap_receipt["stream"] == "a_p2_bootstrap"
    assert len(bootstrap_receipt["receipt_sha256"]) == 64
    assert split_receipt["stream"] == "a_p2_splits"
    assert len(split_receipt["receipt_sha256"]) == 64


@pytest.mark.requires_r
def test_study_stratified_a_p1_draws_match_one_seeded_nested_sample_int_pass(tmp_path):
    script = tmp_path / "joint-a-p1-bootstrap.R"
    script.write_text(
        r'''source("R/bridge.R")
bridge <- bridge_config()
source("R/random_streams.R")
data <- expand.grid(
  study = c("z-study", "a-study"),
  series = c("LEARNED", "CYT"),
  category = c("PD", "O", "SD"),
  member = 1:2,
  KEEP.OUT.ATTRS = FALSE,
  stringsAsFactors = FALSE
)
data$patient <- paste(data$study, data$series, data$category, data$member, sep = "-")
data <- data[rev(seq_len(nrow(data))), , drop = FALSE]
main <- bootstrap_indices_within_study(
  strata = data$category,
  row_key = data$patient,
  study = data$study,
  series = data$series,
  stream = "a_p1_bootstrap",
  repetitions = 5L
)

make_direct <- function(stream, task_id = NULL) {
  seed <- random_seed_for_task(stream, task_id)
  set.seed(seed, kind = "Mersenne-Twister", normal.kind = "Inversion", sample.kind = "Rejection")
  row_order <- order(enc2utf8(data$study), enc2utf8(data$patient), enc2utf8(data$series), method = "radix")
  studies <- unique(data$study[row_order])
  series <- unique(data$series[order(enc2utf8(data$series), method = "radix")])
  strata <- c("O", "SD", "PD")
  rows <- list()
  cursor <- 0L
  for (replicate in seq_len(5L)) {
    for (study_id in studies) {
      for (series_id in series) {
        for (category in strata) {
          members <- row_order[data$study[row_order] == study_id &
            data$series[row_order] == series_id & data$category[row_order] == category]
          if (!length(members)) next
          sampled <- members[sample.int(length(members), length(members), replace = TRUE)]
          cursor <- cursor + 1L
          rows[[cursor]] <- data.frame(
            replicate = replicate,
            series = series_id,
            study = study_id,
            stratum = category,
            draw = seq_along(sampled),
            row_index = sampled,
            stringsAsFactors = FALSE
          )
        }
      }
    }
  }
  do.call(rbind, rows)
}
direct <- make_direct("a_p1_bootstrap")
check <- bootstrap_indices_within_study(
  strata = data$category,
  row_key = data$patient,
  study = data$study,
  series = data$series,
  stream = "second_check",
  task_id = "a_p1_bootstrap",
  repetitions = 5L
)
check_direct <- make_direct("second_check", "a_p1_bootstrap")
checks <- data.frame(
  main_matches_sample_int = identical(main$indices, direct),
  check_matches_sample_int = identical(check$indices, check_direct),
  main_seed = main$seed,
  check_seed = check$seed,
  main_receipt_matches_direct = identical(main$receipt_sha256, .random_receipt_hash(direct)),
  stringsAsFactors = FALSE
)
utils::write.table(checks, file.path(bridge$output_dir, "checks.tsv"),
                   sep = "\t", row.names = FALSE, quote = FALSE)
bridge_write_session(bridge$output_dir)
''',
        encoding="utf-8",
    )
    result = run_r(
        script,
        {},
        {"expected_outputs": ["checks.tsv"]},
        tmp_path / "joint-a-p1-check",
    )

    with result.outputs["checks.tsv"].open(newline="", encoding="utf-8") as stream:
        check = next(csv.DictReader(stream, delimiter="\t"))
    assert check["main_matches_sample_int"] == "TRUE"
    assert check["check_matches_sample_int"] == "TRUE"
    assert check["main_seed"] == "20261108"
    assert check["check_seed"] == str(derive_task_seed("second_check", "a_p1_bootstrap"))
    assert check["main_receipt_matches_direct"] == "TRUE"
