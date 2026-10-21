"""Percentages are per-set local guidance, with an explicit reference load."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from powerlifting.programs import format_program_set, load_program_file
from program_cli.generate_program_docs import render_program
from program_cli.validate_programs import validate_set


class DecemberPercentageTests(unittest.TestCase):
    def test_every_applicable_barbell_set_has_a_labelled_percentage(self):
        program = load_program_file(ROOT / "programs/december_2026_competition_v1.yaml")
        bases = {
            "Squat (Low Bar)": (180, "squat input (180kg)"),
            "Tempo Squat (Barbell)": (180, "squat input (180kg)"),
            "Bench Press (Barbell)": (142.5, "bench input (142.5kg)"),
            "Spoto Press": (142.5, "bench input (142.5kg)"),
            "Sumo Deadlift (Barbell)": (200, "sumo input (200kg)"),
            "Sumo Deadlift (Paused)": (200, "sumo input (200kg)"),
        }
        primary_days = {"Squat (Low Bar)": 3, "Sumo Deadlift (Barbell)": 5}
        guidance = program["loading_guidance"]["top_triples_weeks_1_to_5"]
        seen = 0
        for workout in program["workouts"]:
            for exercise in workout["exercises"]:
                name = exercise["name"]
                for index, prescription in enumerate(exercise["sets"]):
                    with self.subTest(week=workout["week"], day=workout["day"],
                                      exercise=name, set=index + 1):
                        eligible = name in bases and "target_weight_kg" in prescription
                        if not eligible:
                            self.assertNotIn("load_percent", prescription)
                            continue
                        proxy, basis = bases[name]
                        primary_day = ((1 if workout["week"] == 1 else 3)
                                       if name == "Bench Press (Barbell)" else primary_days.get(name))
                        primary = workout["week"] <= 5 and workout["day"] == primary_day
                        if primary and index == 0:
                            expected = [round(p * 100, 3) for p in
                                        guidance[workout["week"] - 1]["e1rm_pct_range"]]
                        elif primary:
                            expected = round(guidance[workout["week"] - 1][
                                "backoff_multiplier_of_actual_top_set"] * 100, 3)
                            basis = "actual top triple"
                        else:
                            expected = round(prescription["target_weight_kg"] / proxy * 100, 2)
                        self.assertEqual(prescription.get("load_percent"), expected)
                        self.assertEqual(prescription.get("load_percent_of"), basis)
                        self.assertIn("% of " + basis, format_program_set(prescription))
                        seen += 1
        self.assertGreater(seen, 100)


class PercentageValidationTests(unittest.TestCase):
    def test_rejects_ambiguous_or_invalid_percentage_guidance(self):
        invalid = [
            {"load_percent": 90},
            {"load_percent": 90, "load_percent_of": " "},
            {"load_percent": 90, "load_percent_of": 180},
            {"load_percent_of": "actual top triple"},
        ]
        invalid += [
            {"load_percent": value, "load_percent_of": "squat input (180kg)"}
            for value in (None, True, "81-83.5", 0, -2, float("inf"),
                          float("nan"), [], [81], [81, 82, 83.5],
                          [83.5, 81], [0, 83.5], [True, 83.5], [81, "83.5"],
                          [81, float("nan")], [81, float("inf")])
        ]
        for metadata in invalid:
            with self.subTest(metadata=metadata):
                errors = validate_set({"target": 3, "rpe": [6, 7], **metadata},
                                      "Squat (Low Bar)", "Wednesday")
                self.assertTrue(errors)

    def test_accepts_scalar_or_range_with_explicit_percentage_basis(self):
        for value in (90, [81, 83.5]):
            with self.subTest(value=value):
                self.assertEqual(validate_set({
                    "target": 3, "rpe": [6, 7], "load_percent": value,
                    "load_percent_of": "squat input (180kg)",
                }, "Squat (Low Bar)", "Wednesday"), [])


class PercentageFormattingTests(unittest.TestCase):
    def test_displays_percentage_range_with_its_basis_and_kg_range(self):
        self.assertEqual(format_program_set({
            "target": 3, "rpe": [6, 6.5],
            "load_percent": [81, 83.5],
            "load_percent_of": "squat input (180kg)",
            "target_weight_range_kg": [145, 150],
            "target_weight_kg": 147.5,
        }), "3 reps @ RPE 6-6.5 · 81–83.5% of squat input (180kg) · "
            "145–150kg anchor range (147.5kg suggested start)")

    def test_rendered_program_explains_percentage_and_range_basis(self):
        rendered = render_program({
            "name": "Example", "weeks": 1, "days_per_week": 1, "workouts": [],
            "loading_guidance": {
                "anchor_range_rule": "Choose the top triple from warm-ups, then recalculate backoffs.",
                "percentage_display_rule": "Variation percentages reference the competition input, not a variation max.",
            },
        })
        self.assertIn("Choose the top triple from warm-ups, then recalculate backoffs.", rendered)
        self.assertIn("Variation percentages reference the competition input, not a variation max.", rendered)

    def test_scalar_only_prescriptions_keep_their_legacy_display(self):
        self.assertEqual(format_program_set({
            "target": 5, "rpe": [7, 7.5], "target_weight_kg": 150,
        }), "5 reps @ RPE 7-7.5 · 150kg anchor")

    def test_displays_fixed_percentage_of_actual_top_set(self):
        self.assertEqual(format_program_set({
            "target": 3, "rpe": [6, 7.5],
            "load_percent": 90,
            "load_percent_of": "actual top triple",
            "target_weight_kg": 105,
        }), "3 reps @ RPE 6-7.5 · 90% of actual top triple · 105kg anchor")


if __name__ == "__main__":
    unittest.main()
