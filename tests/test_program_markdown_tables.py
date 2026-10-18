"""Readable program tables preserve ordered per-set prescriptions."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from powerlifting.programs import iter_program_files, load_program_file
from program_cli.generate_program_docs import render_program


def sample_program(sets):
    return {
        "name": "Example", "weeks": 1, "days_per_week": 1,
        "workouts": [{"week": 1, "day": 1, "name": "Squat day",
                      "exercises": [{"name": "Squat (Low Bar)", "sets": sets}]}],
    }


class ReadableProgramTableTests(unittest.TestCase):
    def test_optional_loads_stay_blank_and_table_guide_explains_set_ranges(self):
        program = sample_program([{"target": 12, "rpe": [6, 7]}] * 2)
        program["workouts"][0]["exercises"][0].update({
            "name": "Leg Extension", "intent": "One familiar condo machine.",
        })
        rendered = render_program(program)
        self.assertIn("| Exercise | Sets | Reps | RPE |", rendered)
        self.assertIn("| Leg Extension | 1–2 | 12 | 6–7 |", rendered)
        self.assertNotIn("Anchor kg", rendered)
        self.assertNotIn("% reference", rendered)
        self.assertIn("**Table guide:**", rendered)
        self.assertIn("original set numbers", rendered)
        self.assertIn("(example)", rendered)
        self.assertIn("One familiar condo machine.", rendered)

    def test_escapes_table_delimiters_without_changing_source_names(self):
        program = sample_program([{
            "target": 3, "rpe": [6, 7], "load_percent": 80,
            "load_percent_of": "bench | planning\ninput",
        }])
        program["workouts"][0]["exercises"][0]["name"] = "Row | machine\nsetup"
        original = deepcopy(program)
        rendered = render_program(program)
        self.assertIn(r"| Row \| machine<br>setup | 1 | 3 | 6–7 | 80% | bench \| planning<br>input |", rendered)
        self.assertEqual(program, original)

    def test_groups_only_identical_consecutive_sets_without_mutating_source(self):
        first = {"target": 3, "rpe": [6, 7], "target_weight_kg": 140}
        different = {"target": 2, "rpe": [6, 7], "target_weight_kg": 140}
        program = sample_program([deepcopy(first), deepcopy(first), different, deepcopy(first)])
        original = deepcopy(program)
        rendered = render_program(program)
        rows = [line for line in rendered.splitlines() if line.startswith("| Squat (Low Bar) |")]
        self.assertEqual(rows, [
            "| Squat (Low Bar) | 1–2 | 3 | 6–7 | 140 |",
            "| Squat (Low Bar) | 3 | 2 | 6–7 | 140 |",
            "| Squat (Low Bar) | 4 | 3 | 6–7 | 140 |",
        ])
        self.assertEqual(program, original)
        self.assertIn("| Squat | 4 | 11 |", rendered)

    def test_all_program_rows_expand_back_to_every_original_set(self):
        def number(value):
            if value is None:
                return "—"
            if isinstance(value, list):
                return "–".join(f"{item:g}" for item in value)
            return f"{value:g}"

        for path in iter_program_files(ROOT / "programs"):
            program = load_program_file(path)
            original = deepcopy(program)
            rendered = render_program(program)
            blocks = rendered.split("#### Day ")[1:]
            workouts = sorted(program["workouts"], key=lambda item: (item["week"], item["day"]))
            self.assertEqual(len(blocks), len(workouts))
            for block, workout in zip(blocks, workouts):
                with self.subTest(program=path.name, week=workout["week"], day=workout["day"]):
                    table = block.split("| Exercise |", 1)[1].split("\n\n", 1)[0]
                    lines = ("| Exercise |" + table).splitlines()
                    headings = [cell.strip() for cell in lines[0].strip("|").split("|")]
                    expanded = []
                    for line in lines[2:]:
                        cells = [cell.strip() for cell in line.strip("|").split("|")]
                        self.assertEqual(len(cells), len(headings))
                        row = dict(zip(headings, cells))
                        indices = row["Sets"].split("–")
                        for index in range(int(indices[0]), int(indices[-1]) + 1):
                            expanded.append((row["Exercise"], index, row))
                    expected = [(exercise["name"], index, prescription)
                                for exercise in workout["exercises"]
                                for index, prescription in enumerate(exercise["sets"], 1)]
                    self.assertEqual(len(expanded), len(expected))
                    for (name, index, row), (expected_name, expected_index, source) in zip(expanded, expected):
                        self.assertEqual((name, index), (expected_name, expected_index))
                        anchor = number(source.get("target_weight_kg"))
                        if source.get("target_weight_kg") is not None:
                            if source.get("target_weight_range_kg") is not None:
                                anchor += " (start)"
                            elif source.get("load_percent_of") == "actual top triple":
                                anchor += " (example)"
                        fields = {
                            "Reps": number(source["target"]), "RPE": number(source["rpe"]),
                            "Load %": number(source["load_percent"]) + "%" if "load_percent" in source else "—",
                            "% reference": source.get("load_percent_of", "—"),
                            "Range kg": number(source.get("target_weight_range_kg")),
                            "Anchor kg": anchor,
                        }
                        for heading, value in fields.items():
                            self.assertEqual(row.get(heading, "—"), value)
            self.assertEqual(program, original)

    def test_splits_prescription_into_explicit_columns(self):
        rendered = render_program(sample_program([
            {"target": 3, "rpe": [6, 6.5], "load_percent": [81, 83.5],
             "load_percent_of": "squat input (180kg)",
             "target_weight_range_kg": [145, 150], "target_weight_kg": 147.5},
            {"target": 3, "rpe": [6, 7.5], "load_percent": 90,
             "load_percent_of": "actual top triple", "target_weight_kg": 132.5},
        ]))
        self.assertIn("| Exercise | Sets | Reps | RPE | Load % | % reference | Range kg | Anchor kg |", rendered)
        self.assertIn("| Squat (Low Bar) | 1 | 3 | 6–6.5 | 81–83.5% | squat input (180kg) | 145–150 | 147.5 (start) |", rendered)
        self.assertIn("| Squat (Low Bar) | 2 | 3 | 6–7.5 | 90% | actual top triple | — | 132.5 (example) |", rendered)
        self.assertNotIn("| # | Exercise | Prescription |", rendered)


if __name__ == "__main__":
    unittest.main()
