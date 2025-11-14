#!/usr/bin/env python3
"""
Tests for report tool
"""

import json
import sys
import unittest
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))

from report import ReportGenerator


class TestReportGenerator(unittest.TestCase):
    """Test report generator functionality"""

    def setUp(self):
        """Set up test cases"""
        self.gen_free = ReportGenerator(tier="free")
        self.gen_pro = ReportGenerator(tier="pro")
        self.gen_enterprise = ReportGenerator(tier="enterprise")

        # Sample scores data
        self.sample_scores = {
            "version": "1.0.0",
            "scoring_metadata": {
                "scoring_timestamp": "2025-11-14T10:00:00Z",
                "scorer_version": "1.0.0",
                "scoring_model": "basic_correct_incorrect",
                "test_info": {
                    "title": "Sample Test",
                    "date": "2025-11-14",
                    "total_points": 10
                }
            },
            "student_results": [
                {
                    "student_id": "s001",
                    "student_name": "Alice",
                    "version_id": "v1",
                    "question_scores": [
                        {
                            "question_id": "q1",
                            "question_number": 1,
                            "question_type": "multiple_choice",
                            "student_answer": "A",
                            "correct_answer": "A",
                            "points_earned": 1,
                            "points_possible": 1,
                            "is_correct": True,
                            "confidence": 0.95
                        }
                    ],
                    "summary": {
                        "total_points_earned": 8,
                        "total_points_possible": 10,
                        "percentage": 80.0,
                        "letter_grade": "B",
                        "questions_correct": 8,
                        "questions_incorrect": 2,
                        "questions_unanswered": 0
                    }
                },
                {
                    "student_id": "s002",
                    "student_name": "Bob",
                    "version_id": "v1",
                    "question_scores": [
                        {
                            "question_id": "q1",
                            "question_number": 1,
                            "question_type": "multiple_choice",
                            "student_answer": "B",
                            "correct_answer": "A",
                            "points_earned": 0,
                            "points_possible": 1,
                            "is_correct": False,
                            "confidence": 0.90
                        }
                    ],
                    "summary": {
                        "total_points_earned": 6,
                        "total_points_possible": 10,
                        "percentage": 60.0,
                        "letter_grade": "D",
                        "questions_correct": 6,
                        "questions_incorrect": 4,
                        "questions_unanswered": 0
                    }
                }
            ],
            "class_statistics": {
                "total_students": 2,
                "mean_score": 70.0,
                "median_score": 70.0,
                "std_dev": 10.0,
                "min_score": 60.0,
                "max_score": 80.0,
                "grade_distribution": {
                    "B": 1,
                    "D": 1
                }
            }
        }

    def test_html_generation_basic(self):
        """Test basic HTML report generation"""
        html = self.gen_free.generate_html(self.sample_scores)

        # Check basic structure
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("<html", html)
        self.assertIn("</html>", html)
        self.assertIn("Test Results Report", html)
        self.assertIn("Sample Test", html)

    def test_markdown_generation_basic(self):
        """Test basic Markdown report generation"""
        md = self.gen_free.generate_markdown(self.sample_scores)

        # Check basic structure
        self.assertIn("# Test Results Report", md)
        self.assertIn("Sample Test", md)
        self.assertIn("Alice", md)
        self.assertIn("80.0%", md)

    def test_tier_format_restrictions(self):
        """Test tier format restrictions"""
        # Free tier doesn't support CSV
        with self.assertRaises(ValueError) as cm:
            # This would fail validation
            self.gen_free._validate_tier_support("csv", "basic")
        self.assertIn("not available", str(cm.exception))

        # Pro tier supports CSV
        try:
            self.gen_pro._validate_tier_support("csv", "basic")
        except ValueError:
            self.fail("Pro tier should support CSV")

    def test_tier_template_restrictions(self):
        """Test tier template restrictions"""
        # Free tier doesn't support detailed template
        with self.assertRaises(ValueError) as cm:
            self.gen_free._validate_tier_support("html", "detailed")
        self.assertIn("not available", str(cm.exception))

        # Pro tier supports detailed template
        try:
            self.gen_pro._validate_tier_support("html", "detailed")
        except ValueError:
            self.fail("Pro tier should support detailed template")

    def test_class_statistics_in_html(self):
        """Test class statistics are included in pro tier HTML"""
        html = self.gen_pro.generate_html(self.sample_scores)

        # Pro tier should include class stats
        self.assertIn("Class Statistics", html)
        self.assertIn("70.0%", html)  # Mean score
        self.assertIn("10.00", html)  # Std dev

        # Free tier should not include class stats
        html_free = self.gen_free.generate_html(self.sample_scores)
        self.assertNotIn("Class Statistics", html_free)

    def test_class_statistics_in_markdown(self):
        """Test class statistics in markdown"""
        md = self.gen_pro.generate_markdown(self.sample_scores)

        # Pro tier should include class stats
        self.assertIn("## Class Statistics", md)
        self.assertIn("Mean Score:", md)
        self.assertIn("70.00%", md)

    def test_student_results_included(self):
        """Test student results are included"""
        html = self.gen_free.generate_html(self.sample_scores)

        # Should include both students
        self.assertIn("Alice", html)
        self.assertIn("Bob", html)
        self.assertIn("80.0%", html)
        self.assertIn("60.0%", html)

    def test_html_contains_css(self):
        """Test HTML contains CSS styles"""
        html = self.gen_free.generate_html(self.sample_scores)

        self.assertIn("<style>", html)
        self.assertIn("</style>", html)
        self.assertIn("font-family", html)

    def test_invalid_tier(self):
        """Test invalid tier raises error"""
        with self.assertRaises(ValueError):
            ReportGenerator(tier="invalid")

    def test_score_display_format(self):
        """Test score is displayed in correct format"""
        md = self.gen_free.generate_markdown(self.sample_scores)

        # Should show percentage and fraction
        self.assertIn("80.0% (8/10)", md)
        self.assertIn("60.0% (6/10)", md)

    def test_letter_grades_displayed(self):
        """Test letter grades are displayed when available"""
        html = self.gen_free.generate_html(self.sample_scores)

        self.assertIn("B", html)  # Alice's grade
        self.assertIn("D", html)  # Bob's grade

    def test_question_breakdown(self):
        """Test question breakdown is included"""
        html = self.gen_free.generate_html(self.sample_scores)

        # Should show correct/incorrect counts
        self.assertIn("8 correct", html)
        self.assertIn("2 incorrect", html)
        self.assertIn("6 correct", html)
        self.assertIn("4 incorrect", html)


class TestReportGeneratorIntegration(unittest.TestCase):
    """Integration tests using fixture files"""

    def test_generate_from_scores_example(self):
        """Test generating report from scores example file"""
        scores_path = Path(__file__).parent.parent.parent / 'phase1' / 'examples' / 'scores_example.json'

        if scores_path.exists():
            with open(scores_path) as f:
                scores = json.load(f)

            generator = ReportGenerator(tier="pro")

            # Test HTML generation
            html = generator.generate_html(scores)
            self.assertIn("<!DOCTYPE html>", html)
            self.assertIn("Test Results Report", html)

            # Test Markdown generation
            md = generator.generate_markdown(scores)
            self.assertIn("# Test Results Report", md)


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    run_tests()
