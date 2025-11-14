#!/usr/bin/env python3
"""
Tests for imagescan tool
"""

import json
import sys
import unittest
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))

from imagescan import ImageScanner


class TestImageScanner(unittest.TestCase):
    """Test image scanner functionality"""

    def setUp(self):
        """Set up test cases"""
        self.scanner = ImageScanner(tier="free")

        # Sample template layout
        self.template_layout = {
            "version": "1.0.0",
            "page_info": {"width_mm": 210, "height_mm": 297, "dpi": 300},
            "registration_marks": [],
            "id_fields": {},
            "questions": [
                {"question_id": "q1", "type": "multiple_choice"},
                {"question_id": "q2", "type": "short_answer"}
            ]
        }

        # Sample question order
        self.question_order = {
            "version": "1.0.0",
            "test_info": {"title": "Test"},
            "versions": {
                "v1": {
                    "version_id": "v1",
                    "questions": [
                        {
                            "question_id": "q1",
                            "question_number": 1,
                            "question_type": "multiple_choice",
                            "correct_answer": "B",
                            "options": [
                                {"label": "A", "text": "Wrong"},
                                {"label": "B", "text": "Correct"},
                                {"label": "C", "text": "Wrong"}
                            ]
                        },
                        {
                            "question_id": "q2",
                            "question_number": 2,
                            "question_type": "short_answer",
                            "correct_answer": "Paris"
                        }
                    ]
                }
            }
        }

    def test_synthetic_scan_basic(self):
        """Test basic synthetic scan generation"""
        result = self.scanner.scan_synthetic(
            "s001",
            "v1",
            self.template_layout,
            self.question_order,
            accuracy=1.0  # Perfect accuracy
        )

        # Check structure
        self.assertIn("version", result)
        self.assertIn("scan_metadata", result)
        self.assertIn("identification", result)
        self.assertIn("answers", result)

        # Check identification
        self.assertEqual(result["identification"]["student_id"], "s001")
        self.assertEqual(result["identification"]["version_id"], "v1")

        # Check answers generated
        self.assertEqual(len(result["answers"]), 2)

    def test_synthetic_scan_perfect_accuracy(self):
        """Test synthetic scan with perfect accuracy"""
        result = self.scanner.scan_synthetic(
            "s001",
            "v1",
            self.template_layout,
            self.question_order,
            accuracy=1.0
        )

        # All answers should be correct
        for answer in result["answers"]:
            q_id = answer["question_id"]
            # Find correct answer
            for q in self.question_order["versions"]["v1"]["questions"]:
                if q["question_id"] == q_id:
                    self.assertEqual(answer["extracted_answer"], q["correct_answer"])

    def test_scan_result_structure(self):
        """Test scan result has correct structure"""
        result = self.scanner.scan_synthetic(
            "s001",
            "v1",
            self.template_layout,
            self.question_order
        )

        # Check metadata
        self.assertIn("scan_timestamp", result["scan_metadata"])
        self.assertIn("image_source", result["scan_metadata"])
        self.assertIn("scanner_version", result["scan_metadata"])

        # Check rectification
        self.assertIn("rectification", result)
        self.assertIn("markers_detected", result["rectification"])

        # Check quality metrics
        self.assertIn("quality_metrics", result)
        self.assertIn("overall_confidence", result["quality_metrics"])

    def test_answer_confidence_scores(self):
        """Test answers have confidence scores"""
        result = self.scanner.scan_synthetic(
            "s001",
            "v1",
            self.template_layout,
            self.question_order
        )

        for answer in result["answers"]:
            self.assertIn("confidence", answer)
            self.assertGreaterEqual(answer["confidence"], 0.0)
            self.assertLessEqual(answer["confidence"], 1.0)

    def test_extraction_methods(self):
        """Test extraction methods are set correctly"""
        result = self.scanner.scan_synthetic(
            "s001",
            "v1",
            self.template_layout,
            self.question_order
        )

        # Find MC question
        mc_answer = next(a for a in result["answers"] if a["question_type"] == "multiple_choice")
        self.assertEqual(mc_answer["extraction_method"], "bubble_detection")

        # Find short answer question
        sa_answer = next(a for a in result["answers"] if a["question_type"] == "short_answer")
        self.assertEqual(sa_answer["extraction_method"], "ocr")


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    run_tests()
