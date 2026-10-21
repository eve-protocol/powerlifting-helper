"""Weekly workload summaries must be transparent, comparable and range-aware."""

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from powerlifting.program_workload import calculate_weekly_workload, format_change
from powerlifting.programs import load_program_file
from program_cli.generate_program_docs import render_program
from program_cli.validate_programs import validate_program


def two_week_program():
    workouts = []
    for week, factor in [(1, 1), (2, 1.1)]:
        workouts.append({
            "week": week, "day": 1, "name": "Training",
            "exercises": [
                {"name": "Squat (Low Bar)", "sets": [
                    {"target": 3, "rpe": [6, 7], "target_weight_kg": 100 * factor},
                    {"target": 3, "rpe": [6, 7], "target_weight_kg": 100 * factor},
                ]},
                {"name": "Bench Press (Barbell)", "sets": [
                    {"target": 4, "rpe": [6, 7], "target_weight_kg": 50 * factor},
                ]},
                {"name": "Sumo Deadlift (Barbell)", "sets": [
                    {"target": 2, "rpe": [6, 7], "target_weight_kg": 150 * factor},
                ]},
            ],
        })
    return {
        "name": "Example", "weeks": 2, "days_per_week": 1, "workouts": workouts,
        "workload_summary": {
            "families": {
                "Squat": ["Squat (Low Bar)"],
                "Bench": ["Bench Press (Barbell)"],
                "Deadlift": ["Sumo Deadlift (Barbell)"],
            },
            "exclude_workouts": [], "plate_increment_kg": 2.5,
        },
    }


class WeeklyWorkloadOverviewTests(unittest.TestCase):
    def test_invalid_workload_scope_configuration_is_rejected(self):
        valid = two_week_program()["workload_summary"]
        duplicate = deepcopy(valid)
        duplicate["families"]["Bench"].append("Squat (Low Bar)")
        unknown = deepcopy(valid)
        unknown["families"]["Bench"] = ["Typo bench"]
        missing_family = deepcopy(valid)
        del missing_family["families"]["Deadlift"]
        invalid_exclusion = deepcopy(valid)
        invalid_exclusion["exclude_workouts"] = [{"week": 2, "day": 9, "reason": "No such workout"}]
        blank_reason = deepcopy(valid)
        blank_reason["exclude_workouts"] = [{"week": 2, "day": 1, "reason": " "}]
        invalid = [None, [], {}, duplicate, unknown, missing_family, invalid_exclusion, blank_reason]
        invalid += [{**deepcopy(valid), "plate_increment_kg": value}
                    for value in (0, True, float("nan"), float("inf"))]
        for config in invalid:
            with self.subTest(config=config), tempfile.TemporaryDirectory() as directory:
                program = two_week_program()
                program["description"] = "Validation fixture"
                program["workload_summary"] = config
                path = Path(directory) / "program.yaml"
                path.write_text(yaml.safe_dump(program))
                errors = validate_program(path)
                self.assertTrue(any("workload_summary" in error for error in errors), errors)

    def test_tonnage_range_recalculates_actual_top_backoffs_with_plate_rounding(self):
        program = two_week_program()
        squat = program["workouts"][0]["exercises"][0]
        squat["sets"] = [
            {"target": 3, "rpe": [7, 8], "target_weight_kg": 162.5,
             "target_weight_range_kg": [160, 162.5]},
            {"target": 3, "rpe": [6, 7], "target_weight_kg": 145,
             "load_percent": 90, "load_percent_of": "actual top triple"},
            {"target": 3, "rpe": [6, 7], "target_weight_kg": 145,
             "load_percent": 90, "load_percent_of": "actual top triple"},
        ]
        metrics = calculate_weekly_workload(program)[1]["lifts"]["Squat"]
        self.assertEqual((metrics["sets"], metrics["reps"]), (3, 9))
        self.assertEqual((metrics["tonnage_low"], metrics["tonnage_high"]), (1350, 1372.5))
        self.assertIn("1,350–1,372.5", render_program(program))

    def test_range_changes_use_cross_bounds_not_midpoint_or_matched_endpoints(self):
        self.assertEqual(format_change((220, 240), (200, 210)), "+4.8% to +20.0%")
        self.assertEqual(format_change((0, 0), (200, 210)), "-100.0%")
        self.assertEqual(format_change((10, 20), (0, 0)), "—")
        self.assertEqual(format_change((10, 20), None), "—")

    def test_excluded_meet_attempts_do_not_inflate_pre_meet_totals(self):
        program = two_week_program()
        expected = calculate_weekly_workload(program)[2]["total"]
        meet = {
            "week": 2, "day": 2, "name": "Competition attempts",
            "exercises": [{"name": name, "sets": [{"target": 1, "rpe": [8, 10]}]}
                          for name in ("Squat (Low Bar)", "Bench Press (Barbell)", "Sumo Deadlift (Barbell)")],
        }
        program["workouts"].append(meet)
        program["workload_summary"]["exclude_workouts"] = [
            {"week": 2, "day": 2, "reason": "Competition attempts are separate from training"},
        ]
        row = calculate_weekly_workload(program)[2]
        self.assertEqual(row["total"], expected)
        self.assertEqual(len(row["excluded_workouts"]), 1)
        rendered = render_program(program)
        self.assertIn("2 (training only)", rendered)
        self.assertIn("Excluded from training totals", rendered)
        self.assertIn("Competition attempts are separate from training", rendered)

    def test_unanchored_training_loads_are_reported_not_silently_zeroed(self):
        program = two_week_program()
        del program["workouts"][1]["exercises"][1]["sets"][0]["target_weight_kg"]
        row = calculate_weekly_workload(program)[2]
        self.assertEqual(row["total"]["unanchored_sets"], 1)
        self.assertIn("+ unknown (1 set)", render_program(program))

    def test_non_family_accessories_are_not_mislabeled_as_big_three_work(self):
        program = two_week_program()
        expected = calculate_weekly_workload(program)
        program["workouts"][0]["exercises"].extend([
            {"name": "Incline Bench Press (Dumbbell)", "sets": [
                {"target": 5, "rpe": [7, 8], "target_weight_kg": 50}]},
            {"name": "Romanian Deadlift (Barbell)", "sets": [
                {"target": 6, "rpe": [6, 7], "target_weight_kg": 125}]},
        ])
        self.assertEqual(calculate_weekly_workload(program), expected)

    def test_weekly_footer_uses_the_same_scoped_metrics_as_overview(self):
        program = two_week_program()
        program["workouts"][0]["exercises"].append({
            "name": "Incline Bench Press (Dumbbell)", "sets": [
                {"target": 5, "rpe": [7, 8], "target_weight_kg": 50}],
        })
        rendered = render_program(program)
        footer = rendered.split("#### Weekly Big 3 Volume", 1)[1].split("### Week 2", 1)[0]
        self.assertIn("| Lift | Sets | Δ sets | Reps | Δ reps | Tonnage kg | Δ tonnage |", footer)
        self.assertIn("| Bench | 1 | — | 4 | — | 200 | — |", footer)
        second_footer = rendered.split("#### Weekly Big 3 Volume")[2]
        self.assertIn("| Bench | 1 | 0.0% | 4 | 0.0% | 220 | +10.0% |", second_footer)

    def test_december_summary_has_all_eight_weeks_and_excludes_nine_meet_slots(self):
        program = load_program_file(ROOT / "programs/december_2026_competition_v1.yaml")
        summary = calculate_weekly_workload(program)
        self.assertEqual(list(summary), list(range(1, 9)))
        expected = {
            "Squat": [(7,31),(8,36),(8,36),(8,34),(8,31),(8,32),(8,32),(6,20)],
            "Bench": [(8,38),(10,48),(10,48),(9,40),(9,40),(10,37),(10,37),(6,21)],
            "Deadlift": [(5,19),(6,22),(6,22),(6,20),(6,20),(6,21),(6,21),(3,12)],
        }
        expected_total_ranges = [
            (10662.5, 10832.5), (13177.5, 13352.5), (13402.5, 13552.5), (12312.5, 12412.5),
            (11260, 11407.5), (11857.5, 11857.5), (12105, 12105), (6707.5, 6707.5),
        ]
        for week, row in summary.items():
            self.assertEqual((row["total"]["tonnage_low"], row["total"]["tonnage_high"]),
                             expected_total_ranges[week - 1])
            for family, counts in expected.items():
                metric = row["lifts"][family]
                self.assertEqual((metric["sets"], metric["reps"]), counts[week - 1])
                self.assertEqual(metric["unanchored_sets"], 0)
            for key in row["total"]:
                self.assertEqual(row["total"][key], sum(lift[key] for lift in row["lifts"].values()))
        self.assertEqual(summary[8]["excluded_workouts"][0]["sets"], 9)
        overview = render_program(program).split("## Program Structure", 1)[0]
        self.assertIn("8 (training only)", overview)
        self.assertEqual(overview.count("| 1 |"), 4)

    def test_overview_shows_total_and_lift_metrics_with_week_on_week_changes(self):
        program = two_week_program()
        original = deepcopy(program)
        rendered = render_program(program)
        self.assertIn("### Weekly expected SBD workload", rendered)
        self.assertLess(rendered.index("### Weekly expected SBD workload"),
                        rendered.index("## Program Structure"))
        self.assertIn("| Week | Expected SBD tonnage kg | Δ vs previous week |", rendered)
        self.assertIn("| 1 | 1,100 | — |", rendered)
        self.assertIn("| 2 | 1,210 | +10.0% |", rendered)
        self.assertIn("#### Squat workload by week", rendered)
        self.assertIn("#### Bench workload by week", rendered)
        self.assertIn("#### Deadlift workload by week", rendered)
        self.assertIn("| Week | Sets | Δ sets | Reps | Δ reps | Tonnage kg | Δ tonnage |", rendered)
        self.assertIn("| 1 | 2 | — | 6 | — | 600 | — |", rendered)
        self.assertIn("| 2 | 2 | 0.0% | 6 | 0.0% | 660 | +10.0% |", rendered)
        self.assertEqual(program, original)


if __name__ == "__main__":
    unittest.main()
