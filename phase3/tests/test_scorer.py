#!/usr/bin/env python3
"""
Tests for scorer tool
"""

import json
import sys
import unittest
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))

from scorer import Scorer


class TestScorer(unittest.TestCase):
    """Test scorer functionality"""

    def setUp(self):
        """Set up test cases"""
        self.scorer_free = Scorer(tier="free")
        self.scorer_pro = Scorer(tier="pro")

        # Sample question order
        self.question_order = {
            "version": "1.0.0",
            "test_info": {"title": "Test", "date": "2025-11-14"},
            "versions": {
                "v1": {
                    "version_id": "v1",
                    "questions": [
                        {
                            "question_id": "q1",
                            "question_number": 1,
                            "question_type": "multiple_choice",
                            "correct_answer": "B",
                            "points": 2
                        },
                        {
                            "question_id": "q2",
                            "question_number": 2,
                            "question_type": "short_answer",
                            "correct_answer": "Paris",
                            "points": 1
                        }
                    ]
                }
            }
        }

        # Sample scan result - all correct
        self.scan_all_correct = {
            "version": "1.0.0",
            "scan_metadata": {
                "scan_timestamp": "2025-11-14T10:00:00Z",
                "image_source": "test.jpg"
            },
            "identification": {
                "student_id": "s001",
                "version_id": "v1",
                "confidence": {"version_id": 0.99, "student_id": 0.99}
            },
            "answers": [
                {
                    "question_id": "q1",
                    "question_number": 1,
                    "question_type": "multiple_choice",
                    "extracted_answer": "B",
                    "confidence": 0.95
                },
                {
                    "question_id": "q2",
                    "question_number": 2,
                    "question_type": "short_answer",
                    "extracted_answer": "Paris",
                    "confidence": 0.90
                }
            ]
        }

        # Sample scan result - some wrong
        self.scan_partial = {
            "version": "1.0.0",
            "scan_metadata": {
                "scan_timestamp": "2025-11-14T10:00:00Z",
                "image_source": "test.jpg"
            },
            "identification": {
                "student_id": "s002",
                "version_id": "v1",
                "confidence": {"version_id": 0.99, "student_id": 0.99}
            },
            "answers": [
                {
                    "question_id": "q1",
                    "question_number": 1,
                    "question_type": "multiple_choice",
                    "extracted_answer": "A",  # Wrong
                    "confidence": 0.85
                },
                {
                    "question_id": "q2",
                    "question_number": 2,
                    "question_type": "short_answer",
                    "extracted_answer": "Paris",  # Correct
                    "confidence": 0.90
                }
            ]
        }

    def test_score_all_correct(self):
        """Test scoring when all answers are correct"""
        result = self.scorer_free.score_scan(self.scan_all_correct, self.question_order)

        summary = result["summary"]
        self.assertEqual(summary["total_points_earned"], 3)
        self.assertEqual(summary["total_points_possible"], 3)
        self.assertEqual(summary["percentage"], 100.0)
        self.assertEqual(summary["letter_grade"], "A")
        self.assertEqual(summary["questions_correct"], 2)
        self.assertEqual(summary["questions_incorrect"], 0)

    def test_score_partial_correct(self):
        """Test scoring with some correct, some incorrect"""
        result = self.scorer_free.score_scan(self.scan_partial, self.question_order)

        summary = result["summary"]
        self.assertEqual(summary["total_points_earned"], 1)  # Only q2 correct (1 point)
        self.assertEqual(summary["total_points_possible"], 3)
        self.assertAlmostEqual(summary["percentage"], 33.33, places=1)
        self.assertEqual(summary["letter_grade"], "F")
        self.assertEqual(summary["questions_correct"], 1)
        self.assertEqual(summary["questions_incorrect"], 1)

    def test_question_scores_structure(self):
        """Test question scores have correct structure"""
        result = self.scorer_free.score_scan(self.scan_all_correct, self.question_order)

        for q_score in result["question_scores"]:
            self.assertIn("question_id", q_score)
            self.assertIn("question_number", q_score)
            self.assertIn("student_answer", q_score)
            self.assertIn("correct_answer", q_score)
            self.assertIn("points_earned", q_score)
            self.assertIn("points_possible", q_score)
            self.assertIn("is_correct", q_score)
            self.assertIn("confidence", q_score)

    def test_letter_grade_calculation(self):
        """Test letter grade calculation"""
        self.assertEqual(self.scorer_free._calculate_letter_grade(95), "A")
        self.assertEqual(self.scorer_free._calculate_letter_grade(85), "B")
        self.assertEqual(self.scorer_free._calculate_letter_grade(75), "C")
        self.assertEqual(self.scorer_free._calculate_letter_grade(65), "D")
        self.assertEqual(self.scorer_free._calculate_letter_grade(55), "F")

    def test_batch_scoring(self):
        """Test batch scoring multiple scans"""
        scans = [self.scan_all_correct, self.scan_partial]

        result = self.scorer_pro.score_batch(
            scans,
            self.question_order,
            calculate_class_stats=True
        )

        self.assertIn("version", result)
        self.assertIn("scoring_metadata", result)
        self.assertIn("student_results", result)
        self.assertEqual(len(result["student_results"]), 2)

    def test_class_statistics(self):
        """Test class statistics calculation"""
        scans = [self.scan_all_correct, self.scan_partial]

        result = self.scorer_pro.score_batch(
            scans,
            self.question_order,
            calculate_class_stats=True
        )

        self.assertIn("class_statistics", result)
        stats = result["class_statistics"]

        self.assertEqual(stats["total_students"], 2)
        self.assertIn("mean_score", stats)
        self.assertIn("median_score", stats)
        self.assertIn("std_dev", stats)
        self.assertIn("grade_distribution", stats)

    def test_case_insensitive_matching(self):
        """Test that answer matching is case-insensitive"""
        scan_upper = self.scan_all_correct.copy()
        scan_upper["answers"] = [
            {
                "question_id": "q2",
                "question_number": 2,
                "question_type": "short_answer",
                "extracted_answer": "PARIS",  # Uppercase
                "confidence": 0.90
            }
        ]

        # Should match despite case difference
        result = self.scorer_free._check_answer("PARIS", "Paris", "short_answer")
        self.assertTrue(result)

    def test_confidence_flags(self):
        """Test low confidence answers are flagged"""
        scan_low_conf = self.scan_all_correct.copy()
        scan_low_conf["answers"] = [
            {
                "question_id": "q1",
                "question_number": 1,
                "question_type": "multiple_choice",
                "extracted_answer": "B",
                "confidence": 0.65  # Low confidence
            }
        ]

        result = self.scorer_free.score_scan(scan_low_conf, self.question_order)

        # Should have low_confidence flag
        q_score = result["question_scores"][0]
        self.assertIn("flags", q_score)
        self.assertIn("low_confidence", q_score["flags"])

    def test_tier_validation(self):
        """Test tier validation"""
        with self.assertRaises(ValueError):
            Scorer(tier="invalid")


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    run_tests()
