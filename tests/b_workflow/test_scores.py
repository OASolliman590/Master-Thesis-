"""Hand-calculated rank, tie and promoter fixtures."""

from __future__ import annotations

import unittest

from tools.b_features.scores import midranks, percentile_from_rank, program_score


UNIVERSE = ["SYN:GENE_A", "SYN:GENE_B", "SYN:GENE_C", "SYN:GENE_D", "SYN:GENE_E"]
PROGRAM = ["SYN:GENE_A", "SYN:GENE_B"]


class TestHandCalculatedScores(unittest.TestCase):
    def test_midranks_and_ties(self) -> None:
        # values 10,10,30,5,20 -> ranks 2.5, 2.5, 5, 1, 4
        ranks = midranks([10.0, 10.0, 30.0, 5.0, 20.0])
        self.assertEqual(ranks, [2.5, 2.5, 5.0, 1.0, 4.0])

    def test_all_tied_midrank(self) -> None:
        ranks = midranks([7.0, 7.0, 7.0, 7.0, 7.0])
        self.assertEqual(ranks, [3.0, 3.0, 3.0, 3.0, 3.0])

    def test_y_tied_sample(self) -> None:
        y = program_score(
            {
                "SYN:GENE_A": 10.0,
                "SYN:GENE_B": 10.0,
                "SYN:GENE_C": 30.0,
                "SYN:GENE_D": 5.0,
                "SYN:GENE_E": 20.0,
            },
            UNIVERSE,
            PROGRAM,
        )
        self.assertEqual(y, 0.375)

    def test_y_untied_sample(self) -> None:
        y = program_score(
            {
                "SYN:GENE_A": 1.0,
                "SYN:GENE_B": 2.0,
                "SYN:GENE_C": 3.0,
                "SYN:GENE_D": 4.0,
                "SYN:GENE_E": 5.0,
            },
            UNIVERSE,
            PROGRAM,
        )
        self.assertEqual(y, 0.125)

    def test_y_all_tied(self) -> None:
        y = program_score({gene: 7.0 for gene in UNIVERSE}, UNIVERSE, PROGRAM)
        self.assertEqual(y, 0.5)

    def test_gene_outside_universe_does_not_change_score(self) -> None:
        base = {
            "SYN:GENE_A": 10.0,
            "SYN:GENE_B": 10.0,
            "SYN:GENE_C": 30.0,
            "SYN:GENE_D": 5.0,
            "SYN:GENE_E": 20.0,
        }
        with_extra = dict(base)
        with_extra["SYN:GENE_F"] = 999.0
        self.assertEqual(program_score(base, UNIVERSE, PROGRAM), program_score(with_extra, UNIVERSE, PROGRAM))

    def test_missing_universe_gene_fails(self) -> None:
        values = {
            "SYN:GENE_A": 10.0,
            "SYN:GENE_B": 10.0,
            "SYN:GENE_C": 30.0,
            "SYN:GENE_D": 5.0,
        }
        with self.assertRaises(ValueError) as ctx:
            program_score(values, UNIVERSE, PROGRAM)
        self.assertIn("incomplete-universe", str(ctx.exception))

    def test_percentile_formula(self) -> None:
        self.assertEqual(percentile_from_rank(1.0, 5), 0.0)
        self.assertEqual(percentile_from_rank(5.0, 5), 1.0)
        self.assertEqual(percentile_from_rank(2.5, 5), 0.375)


if __name__ == "__main__":
    unittest.main()
