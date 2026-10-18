"""Coaching metadata must not alter the Boostcamp reps/RPE payload."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from powerlifting.boostcamp_program_manager import yaml_to_boostcamp_format
from powerlifting.programs import load_program_file


class BoostcampMetadataRegressionTests(unittest.TestCase):
    def test_local_percentage_and_anchor_fields_do_not_change_api_payload(self):
        annotated = load_program_file(ROOT / "programs/december_2026_competition_v1.yaml")
        plain = deepcopy(annotated)
        for workout in plain["workouts"]:
            for exercise in workout["exercises"]:
                for prescription in exercise["sets"]:
                    for key in ("load_percent", "load_percent_of",
                                "target_weight_kg", "target_weight_range_kg"):
                        prescription.pop(key, None)

        def without_generated_ids(value):
            if isinstance(value, dict):
                return {key: without_generated_ids(item) for key, item in value.items()
                        if key != "id"}
            if isinstance(value, list):
                return [without_generated_ids(item) for item in value]
            return value

        first = yaml_to_boostcamp_format(annotated, existing_id="offline", existing_slug="offline")
        second = yaml_to_boostcamp_format(plain, existing_id="offline", existing_slug="offline")
        self.assertEqual(without_generated_ids(first), without_generated_ids(second))
        workouts = first["variations"][0]["workouts"]
        self.assertEqual(len(workouts), 39)
        for workout in workouts:
            for exercise in workout["exercises"]:
                for prescription in exercise["sets"]:
                    self.assertEqual(prescription["intensity_unit"], "RPE_range")
                    self.assertNotIn("load_percent", prescription)
                    self.assertNotIn("target_weight_range_kg", prescription)


if __name__ == "__main__":
    unittest.main()
