#!/usr/bin/env python3
"""
Tests for docgen tool
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))

from docgen import DocumentGenerator


class TestDocumentGenerator(unittest.TestCase):
    """Test document generator functionality"""

    def setUp(self):
        """Set up test cases"""
        self.generator = DocumentGenerator()

        # Sample questions data
        self.sample_questions = {
            "version": "1.0.0",
            "questions": [
                {
                    "id": "q1",
                    "type": "multiple_choice",
                    "text": "What is 2+2?",
                    "points": 1,
                    "options": [
                        {"label": "A", "text": "3"},
                        {"label": "B", "text": "4"},
                        {"label": "C", "text": "5"}
                    ],
                    "correct_answer": "B"
                },
                {
                    "id": "q2",
                    "type": "true_false",
                    "text": "The sky is blue.",
                    "points": 1,
                    "options": [
                        {"label": "A", "text": "True"},
                        {"label": "B", "text": "False"}
                    ],
                    "correct_answer": "A"
                },
                {
                    "id": "q3",
                    "type": "short_answer",
                    "text": "What is the capital of France?",
                    "points": 1,
                    "correct_answer": "Paris"
                }
            ]
        }

        # Sample config data
        self.sample_config = {
            "version": "1.0.0",
            "tier": "pro",
            "test_info": {
                "title": "Sample Test",
                "date": "2025-11-14"
            },
            "distribution": {
                "versions": 2,
                "students": 4,
                "strategy": "round_robin",
                "randomize_questions": False,
                "randomize_options": False
            },
            "scanning": {
                "page_size": "A4",
                "dpi": 300,
                "answer_field_type": "circle"
            }
        }

    def test_basic_generation(self):
        """Test basic document generation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)

            template_layout, question_order = self.generator.generate(
                self.sample_questions,
                self.sample_config,
                output_path
            )

            # Check that files were created
            self.assertTrue((output_path / "template_layout.json").exists())
            self.assertTrue((output_path / "question_order.json").exists())
            self.assertTrue((output_path / "typst").exists())

    def test_template_layout_structure(self):
        """Test template layout has correct structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)

            template_layout, _ = self.generator.generate(
                self.sample_questions,
                self.sample_config,
                output_path
            )

            # Check required fields
            self.assertIn("version", template_layout)
            self.assertIn("page_info", template_layout)
            self.assertIn("registration_marks", template_layout)
            self.assertIn("id_fields", template_layout)
            self.assertIn("questions", template_layout)

            # Check page info
            self.assertEqual(template_layout["page_info"]["page_size"], "A4")
            self.assertEqual(template_layout["page_info"]["dpi"], 300)

            # Check registration marks (should have 4 corners)
            self.assertEqual(len(template_layout["registration_marks"]), 4)

            # Check questions match input
            self.assertEqual(len(template_layout["questions"]), len(self.sample_questions["questions"]))

    def test_question_order_structure(self):
        """Test question order has correct structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)

            _, question_order = self.generator.generate(
                self.sample_questions,
                self.sample_config,
                output_path
            )

            # Check required fields
            self.assertIn("version", question_order)
            self.assertIn("test_info", question_order)
            self.assertIn("versions", question_order)
            self.assertIn("student_assignments", question_order)

            # Check number of versions
            self.assertEqual(len(question_order["versions"]), self.sample_config["distribution"]["versions"])

            # Check student assignments
            self.assertEqual(len(question_order["student_assignments"]), self.sample_config["distribution"]["students"])

    def test_round_robin_distribution(self):
        """Test round-robin distribution strategy"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)

            _, question_order = self.generator.generate(
                self.sample_questions,
                self.sample_config,
                output_path
            )

            # Each version should have all questions
            for version_id, version_data in question_order["versions"].items():
                self.assertEqual(len(version_data["questions"]), len(self.sample_questions["questions"]))

            # Versions should have different orderings (rotated)
            v1_first = question_order["versions"]["v1"]["questions"][0]["question_id"]
            v2_first = question_order["versions"]["v2"]["questions"][0]["question_id"]
            self.assertNotEqual(v1_first, v2_first)

    def test_student_assignment(self):
        """Test students are assigned to versions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)

            _, question_order = self.generator.generate(
                self.sample_questions,
                self.sample_config,
                output_path
            )

            # All students should be assigned
            assignments = question_order["student_assignments"]
            self.assertEqual(len(assignments), 4)

            # Assignments should be balanced
            version_counts = {}
            for student_id, version_id in assignments.items():
                version_counts[version_id] = version_counts.get(version_id, 0) + 1

            # With 4 students and 2 versions, each version should get 2 students
            self.assertEqual(version_counts["v1"], 2)
            self.assertEqual(version_counts["v2"], 2)

    def test_typst_files_generated(self):
        """Test Typst source files are generated"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)

            self.generator.generate(
                self.sample_questions,
                self.sample_config,
                output_path
            )

            typst_dir = output_path / "typst"
            typst_files = list(typst_dir.glob("*.typ"))

            # Should have one file per student
            self.assertEqual(len(typst_files), self.sample_config["distribution"]["students"])

            # Check file naming
            for typst_file in typst_files:
                # Should be in format: s001_v1.typ
                self.assertRegex(typst_file.name, r"s\d+_v\d+\.typ")

    def test_typst_content_structure(self):
        """Test Typst content has basic structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)

            self.generator.generate(
                self.sample_questions,
                self.sample_config,
                output_path
            )

            # Read one Typst file
            typst_file = list((output_path / "typst").glob("*.typ"))[0]
            with open(typst_file) as f:
                content = f.read()

            # Should contain page setup
            self.assertIn("#set page", content)

            # Should contain registration marks
            self.assertIn("circle(radius:", content)
            self.assertIn("fill: black", content)

            # Should contain test title
            self.assertIn("Sample Test", content)

            # Should contain questions
            self.assertIn("What is 2+2?", content)

    def test_answer_fields_in_layout(self):
        """Test answer fields are included for MC questions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)

            template_layout, _ = self.generator.generate(
                self.sample_questions,
                self.sample_config,
                output_path
            )

            # Find MC question in layout
            mc_question = None
            for q in template_layout["questions"]:
                if q["type"] == "multiple_choice":
                    mc_question = q
                    break

            self.assertIsNotNone(mc_question)
            self.assertIn("answer_fields", mc_question)
            self.assertEqual(len(mc_question["answer_fields"]), 3)  # A, B, C

    def test_ocr_region_for_short_answer(self):
        """Test OCR region is included for short answer questions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)

            template_layout, _ = self.generator.generate(
                self.sample_questions,
                self.sample_config,
                output_path
            )

            # Find short answer question in layout
            sa_question = None
            for q in template_layout["questions"]:
                if q["type"] == "short_answer":
                    sa_question = q
                    break

            self.assertIsNotNone(sa_question)
            self.assertIn("ocr_region", sa_question)
            self.assertIn("expected_lines", sa_question["ocr_region"])

    def test_with_custom_students_list(self):
        """Test with custom students list"""
        config = self.sample_config.copy()
        config["students_list"] = [
            {"id": "alice", "name": "Alice Smith"},
            {"id": "bob", "name": "Bob Jones"},
            {"id": "carol", "name": "Carol White"},
            {"id": "dave", "name": "Dave Brown"}
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)

            _, question_order = self.generator.generate(
                self.sample_questions,
                config,
                output_path
            )

            # Check student IDs in assignments
            self.assertIn("alice", question_order["student_assignments"])
            self.assertIn("bob", question_order["student_assignments"])

            # Check Typst files use custom IDs
            typst_files = [f.name for f in (output_path / "typst").glob("*.typ")]
            self.assertTrue(any("alice" in f for f in typst_files))
            self.assertTrue(any("bob" in f for f in typst_files))

    def test_page_size_letter(self):
        """Test generation with Letter page size"""
        config = self.sample_config.copy()
        config["scanning"]["page_size"] = "Letter"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)

            template_layout, _ = self.generator.generate(
                self.sample_questions,
                config,
                output_path
            )

            self.assertEqual(template_layout["page_info"]["page_size"], "Letter")
            self.assertAlmostEqual(template_layout["page_info"]["width_mm"], 215.9, places=1)


class TestDocumentGeneratorIntegration(unittest.TestCase):
    """Integration tests using real fixtures"""

    def test_with_phase2_outputs(self):
        """Test using actual Phase 2 outputs"""
        questions_path = Path(__file__).parent.parent.parent / "phase2" / "fixtures" / "test_output.json"
        config_path = Path(__file__).parent.parent.parent / "phase2" / "fixtures" / "test_config.json"

        if not questions_path.exists() or not config_path.exists():
            self.skipTest("Phase 2 fixtures not found")

        with open(questions_path) as f:
            questions = json.load(f)

        with open(config_path) as f:
            config = json.load(f)

        generator = DocumentGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)

            template_layout, question_order = generator.generate(
                questions,
                config,
                output_path
            )

            # Verify outputs
            self.assertIn("version", template_layout)
            self.assertIn("version", question_order)
            self.assertTrue((output_path / "typst").exists())


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    run_tests()
