"""Local coaching ranges must be visible without changing training doses."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from powerlifting.programs import format_program_set, load_program_file
from program_cli.generate_program_docs import render_program
from program_cli.validate_programs import validate_set


class DecemberTripleRangeTests(unittest.TestCase):
    def test_all_fifteen_top_triples_show_workbook_ranges(self):
        program = load_program_file(ROOT / "programs/december_2026_competition_v1.yaml")
        expected = {
            (3, "Squat (Low Bar)"): [
                [145, 150], [147.5, 152.5], [150, 155], [155, 157.5], [157.5, 160],
            ],
            (3, "Bench Press (Barbell)"): [
                [115, 120], [117.5, 120], [120, 122.5], [122.5, 125], [125, 127.5],
            ],
            (5, "Sumo Deadlift (Barbell)"): [
                [162.5, 167.5], [165, 170], [167.5, 172.5], [170, 175], [175, 180],
            ],
        }
        seen = 0
        for workout in program["workouts"]:
            for exercise in workout["exercises"]:
                key = (3 if exercise["name"] == "Bench Press (Barbell)" else workout["day"], exercise["name"])
                eligible = (workout["week"] <= 5 and key in expected and
                            (exercise["name"] != "Bench Press (Barbell)" or
                             workout["day"] == (1 if workout["week"] == 1 else 3)))
                if eligible:
                    top = exercise["sets"][0]
                    with self.subTest(week=workout["week"], lift=exercise["name"]):
                        self.assertEqual(
                            top.get("target_weight_range_kg"),
                            expected[key][workout["week"] - 1],
                        )
                        self.assertEqual(validate_set(top, exercise["name"], workout["name"]), [])
                    seen += 1
                for index, set_data in enumerate(exercise["sets"]):
                    if not (eligible and index == 0):
                        self.assertNotIn("target_weight_range_kg", set_data)
        self.assertEqual(seen, 15)
        range_rows = [
            [cell.strip() for cell in line.strip("|").split("|")]
            for line in render_program(program).splitlines() if line.startswith("| ")
        ]
        range_rows = [row for row in range_rows if len(row) == 8 and row[1] == "1" and row[6] != "—"]
        self.assertEqual(len(range_rows), 15)
        actual = sorted((row[0], row[6]) for row in range_rows)
        expected_display = sorted(
            (name, f"{low:g}–{high:g}")
            for (_, name), ranges in expected.items() for low, high in ranges
        )
        self.assertEqual(actual, expected_display)


class AnchorRangeValidationTests(unittest.TestCase):
    def test_rejects_invalid_ranges_or_suggested_start_outside_range(self):
        invalid = [
            "145-150", [145], [145, 147.5, 150], [150, 145],
            [0, 150], [-1, 150], [True, 150], ["145", 150],
            [float("nan"), 150], [145, float("inf")], [145, 146],
        ]
        for weight_range in invalid:
            with self.subTest(weight_range=weight_range):
                errors = validate_set({
                    "target": 3, "rpe": [6, 6.5],
                    "target_weight_kg": 147.5,
                    "target_weight_range_kg": weight_range,
                }, "Squat (Low Bar)", "Wednesday")
                self.assertTrue(errors, "Malformed or incompatible range must be rejected")

    def test_accepts_ordered_range_containing_suggested_start(self):
        self.assertEqual(validate_set({
            "target": 3, "rpe": [6, 6.5], "target_weight_kg": 147.5,
            "target_weight_range_kg": [145, 150],
        }, "Squat (Low Bar)", "Wednesday"), [])


class AnchorRangeFormattingTests(unittest.TestCase):
    def test_shows_range_with_existing_anchor_as_suggested_start(self):
        prescription = format_program_set({
            "target": 3,
            "rpe": [6, 6.5],
            "target_weight_kg": 147.5,
            "target_weight_range_kg": [145, 150],
        })
        self.assertEqual(
            prescription,
            "3 reps @ RPE 6-6.5 · 145–150kg anchor range (147.5kg suggested start)",
        )


if __name__ == "__main__":
    unittest.main()
