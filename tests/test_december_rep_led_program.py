"""Rep-led Grinchmas preparation: training singles are not mandatory work."""
from pathlib import Path
from copy import deepcopy
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from powerlifting.programs import load_program_file
from powerlifting.program_workload import calculate_weekly_workload


class DecemberRepLedProgramTests(unittest.TestCase):
    def setUp(self):
        self.program = load_program_file(ROOT / "programs/december_2026_competition_v1.yaml")

    def exercise(self, week, day, name):
        workout = next(w for w in self.program["workouts"] if (w["week"], w["day"]) == (week, day))
        return next(e for e in workout["exercises"] if e["name"] == name)

    def test_no_single_repetition_training_work_is_prescribed(self):
        singles = [
            (w["week"], w["day"], e["name"], i + 1)
            for w in self.program["workouts"] if (w["week"], w["day"]) != (8, 5)
            for e in w["exercises"] for i, s in enumerate(e["sets"])
            if s["target"] == 1
        ]
        self.assertEqual(singles, [], "Only competition attempts may prescribe one rep")

    def test_accessory_set_policy_preserves_separate_primary_paths(self):
        families = {name for names in self.program["workload_summary"]["families"].values() for name in names}
        own_paths = {"Pull-Up (Weighted)", "Incline Bench Press (Dumbbell)"}
        wrong = []
        for workout in self.program["workouts"]:
            if (workout["week"], workout["day"]) == (8, 5):
                continue
            for exercise in workout["exercises"]:
                if exercise["name"] in families | own_paths:
                    continue
                expected = 2 if exercise["name"] == "Romanian Deadlift (Barbell)" or workout["week"] >= 7 else 3
                if len(exercise["sets"]) != expected:
                    wrong.append((workout["week"], workout["day"], exercise["name"], len(exercise["sets"]), expected))
        self.assertEqual(wrong, [], "Normal accessories: three sets; RDL: two; meet lead-in accessories: two")

    def test_week1_builds_rep_volume_without_harder_primary_top_sets(self):
        for day, name in ((1, "Bench Press (Barbell)"), (3, "Squat (Low Bar)"), (5, "Sumo Deadlift (Barbell)")):
            sets = self.exercise(1, day, name)["sets"]
            with self.subTest(name=name):
                self.assertEqual([s["target"] for s in sets], [3, 5, 5])
                self.assertEqual(sets[0]["rpe"], [6, 6.5])
                self.assertTrue(all(s["rpe"][-1] <= 7 for s in sets[1:]))
        self.assertEqual([(s["target"], s["target_weight_kg"]) for s in self.exercise(1, 3, "Bench Press (Barbell)")["sets"]], [(5, 105)] * 3)
        self.assertEqual([s["target"] for s in self.exercise(1, 5, "Squat (Low Bar)")["sets"]], [4, 4])
        self.assertEqual([s["target"] for s in self.exercise(1, 5, "Spoto Press")["sets"]], [5, 5])

    def test_week1_squat_intent_describes_later_doubles_not_singles(self):
        workout = next(w for w in self.program["workouts"] if (w["week"], w["day"]) == (1, 3))
        self.assertIn("controlled doubles", workout["intent"])
        self.assertNotIn("controlled singles", workout["intent"])

    def test_meet_week_wednesday_is_three_days_before_saturday(self):
        for name in ("Squat (Low Bar)", "Bench Press (Barbell)"):
            intent = self.exercise(8, 3, name)["intent"]
            with self.subTest(name=name):
                self.assertIn("three days before", intent)
                self.assertNotIn("two days before", intent)

    def test_requested_squat_first_weekly_order_and_exact_exercise_names(self):
        monday = ["Tempo Squat (Barbell)", "Bench Press (Barbell)", "Pull-Up (Weighted)",
                  "Leg Extension", "Hip Thrust (Machine)"]
        tuesday = ["Sumo Deadlift (Paused)", "Incline Bench Press (Dumbbell)", "Seated Row (Cable)"]
        completed_week1_tuesday = ["Sumo Deadlift (Paused)", "Romanian Deadlift (Barbell)",
                                   "Incline Bench Press (Dumbbell)", "Seated Row (Cable)"]
        thursday = ["Chest Fly (Machine)", "Lateral Raise (Cable)", "Rear Delt Fly (Dumbbell)",
                    "Tricep Pushdown (Cable)", "Bicep Curl (Dumbbell)"]
        saturday = ["Sumo Deadlift (Barbell)", "Squat (Low Bar)", "Spoto Press"]
        saturday_with_rdl = ["Sumo Deadlift (Barbell)", "Romanian Deadlift (Barbell)",
                             "Squat (Low Bar)", "Spoto Press"]
        expected = {}
        for week in range(1, 8):
            expected[(week, 1)] = monday
            expected[(week, 2)] = completed_week1_tuesday if week == 1 else tuesday
            expected[(week, 3)] = ["Squat (Low Bar)", "Bench Press (Barbell)", "Pull-Up (Weighted)",
                "Hip adductor (Rowerg)" if week in (2, 4, 6) else "Cable Crunch"]
            expected[(week, 4)] = thursday + (["Hip Adductor (Machine)"] if week in (1, 3, 5) else [])
            expected[(week, 5)] = saturday if week == 1 else saturday_with_rdl
        expected.update({(8, 1): monday,
                         (8, 2): ["Sumo Deadlift (Barbell)", "Incline Bench Press (Dumbbell)", "Seated Row (Cable)"],
                         (8, 3): ["Squat (Low Bar)", "Bench Press (Barbell)", "Pull-Up (Weighted)"],
                         (8, 5): ["Squat (Low Bar)", "Bench Press (Barbell)", "Sumo Deadlift (Barbell)"]})
        actual = {(w["week"], w["day"]): [e["name"] for e in w["exercises"]]
                  for w in self.program["workouts"]}
        self.assertEqual(actual, expected)
        self.assertEqual(len(self.program["workouts"]), 39)

    def test_double_loads_are_reselected_and_not_former_single_weights(self):
        expected = {6: [(1, "Bench Press (Barbell)", 127.5), (3, "Squat (Low Bar)", 160),
                        (5, "Sumo Deadlift (Barbell)", 175)],
                    7: [(1, "Bench Press (Barbell)", 130), (3, "Squat (Low Bar)", 162.5),
                        (5, "Sumo Deadlift (Barbell)", 177.5)],
                    8: [(1, "Bench Press (Barbell)", 122.5), (3, "Squat (Low Bar)", 155),
                        (2, "Sumo Deadlift (Barbell)", 170)]}
        for week, prescriptions in expected.items():
            for day, name, kg in prescriptions:
                with self.subTest(week=week, name=name):
                    top = self.exercise(week, day, name)["sets"][0]
                    self.assertEqual((top["target"], top["target_weight_kg"]), (2, kg))
                    self.assertLessEqual(top["rpe"][-1], 8.5)

    def test_week7_eases_accessories_without_tapering_main_lift_work(self):
        summary = calculate_weekly_workload(self.program)
        for family in summary[6]["lifts"]:
            a, b = summary[6]["lifts"][family], summary[7]["lifts"][family]
            self.assertEqual((a["sets"], a["reps"]), (b["sets"], b["reps"]))
            self.assertGreaterEqual(b["tonnage_low"], a["tonnage_high"])
        for week, expected_count in ((6, 61), (7, 52)):
            all_sets = sum(len(e["sets"]) for w in self.program["workouts"] if w["week"] == week
                           for e in w["exercises"])
            self.assertEqual(all_sets, expected_count)

    def test_sole_meet_week_taper_retains_half_of_revised_normal_week(self):
        broader = deepcopy(self.program)
        broader["workload_summary"]["families"]["Deadlift"].append("Romanian Deadlift (Barbell)")
        for program in (self.program, broader):
            summary = calculate_weekly_workload(program)
            a, b = summary[7]["total"], summary[8]["total"]
            for key in ("sets", "reps", "tonnage_low", "tonnage_high"):
                self.assertGreaterEqual(b[key], a[key] * .5, key)
                self.assertLess(b[key], a[key], key)
        counts = {week: sum(len(e["sets"]) for w in self.program["workouts"]
                           if w["week"] == week and (week, w["day"]) != (8, 5)
                           for e in w["exercises"]) for week in (7, 8)}
        self.assertGreaterEqual(counts[8], counts[7] * .5)
        self.assertEqual((counts[7], counts[8]), (52, 26))
        for w in self.program["workouts"]:
            if w["week"] == 8 and w["day"] != 5:
                self.assertTrue(all(s["rpe"][-1] <= 7.5 for e in w["exercises"] for s in e["sets"]))

    def test_taper_report_discloses_mixed_exercise_rep_reduction(self):
        reps = {week: sum(s["target"] for w in self.program["workouts"]
                          if w["week"] == week and (week, w["day"]) != (8, 5)
                          for e in w["exercises"] for s in e["sets"]) for week in (7, 8)}
        report = (ROOT / "coach_notes/planning/december_2026_rep_led_workload.md").read_text()
        self.assertIn(f"{reps[7]} → {reps[8]}", report)
        self.assertIn(f"{(1 - reps[8] / reps[7]) * 100:.1f}% cut", report)

    def test_relocated_rdl_and_tuesday_paused_sumos_preserve_dose(self):
        self.assertEqual(len(self.exercise(1, 2, "Romanian Deadlift (Barbell)")["sets"]), 2)
        self.assertNotIn("Romanian Deadlift (Barbell)",
                         [e["name"] for e in next(w for w in self.program["workouts"]
                                                   if (w["week"], w["day"]) == (1, 5))["exercises"]])
        for week in range(2, 8):
            sets = self.exercise(week, 5, "Romanian Deadlift (Barbell)")["sets"]
            self.assertEqual(len(sets), 2)
            self.assertTrue(all(s["target"] == 6 and s["rpe"][-1] <= 7 for s in sets))
            self.assertNotIn("Romanian Deadlift (Barbell)",
                             [e["name"] for e in next(w for w in self.program["workouts"]
                                                       if (w["week"], w["day"]) == (week, 2))["exercises"]])
            sets = self.exercise(week, 2, "Sumo Deadlift (Paused)")["sets"]
            self.assertEqual([s["target"] for s in sets], [3, 3, 3])
            self.assertTrue(all(s["rpe"][-1] <= 7 for s in sets))

    def test_secondary_command_bench_rises_without_changing_effort_or_completed_week1(self):
        self.assertEqual([s["target_weight_kg"] for s in self.exercise(1, 3, "Bench Press (Barbell)")["sets"]], [105]*3)
        for week, anchor in {2:112.5, 3:112.5, 4:115, 5:115, 6:117.5, 7:120, 8:105}.items():
            sets = self.exercise(week, 3, "Bench Press (Barbell)")["sets"]
            self.assertTrue(all(s["target_weight_kg"] == anchor and s["rpe"] == [6, 7] for s in sets))
            self.assertTrue(all(s["load_percent_of"] == "bench input (142.5kg)" and
                                abs(s["load_percent"] - round(anchor / 142.5 * 100, 2)) < .011 for s in sets))

    def test_meet_singles_remain_nine_unknown_attempts_not_training_volume(self):
        meet = next(w for w in self.program["workouts"] if (w["week"], w["day"]) == (8, 5))
        sets = [s for e in meet["exercises"] for s in e["sets"]]
        self.assertEqual(len(sets), 9)
        self.assertTrue(all(s["target"] == 1 and "target_weight_kg" not in s for s in sets))
        self.assertEqual(calculate_weekly_workload(self.program)[8]["excluded_workouts"][0]["sets"], 9)


if __name__ == "__main__":
    unittest.main()
