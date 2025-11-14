#!/usr/bin/env python3
"""
Tests for configgen tool
"""

import json
import sys
import unittest
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))

from configgen import ConfigGenerator


class TestConfigGenerator(unittest.TestCase):
    """Test config generator functionality"""

    def setUp(self):
        """Set up test cases"""
        self.gen_free = ConfigGenerator(tier="free")
        self.gen_pro = ConfigGenerator(tier="pro")
        self.gen_enterprise = ConfigGenerator(tier="enterprise")

    def test_basic_config_generation(self):
        """Test basic configuration generation"""
        config = self.gen_free.generate(
            title="Test Exam",
            versions=2,
            students=10
        )

        self.assertEqual(config["version"], "1.0.0")
        self.assertEqual(config["tier"], "free")
        self.assertEqual(config["test_info"]["title"], "Test Exam")
        self.assertEqual(config["distribution"]["versions"], 2)
        self.assertEqual(config["distribution"]["students"], 10)

    def test_tier_version_limits(self):
        """Test tier version limits are enforced"""
        # Free tier allows max 3 versions
        with self.assertRaises(ValueError) as cm:
            self.gen_free.generate(
                title="Test",
                versions=5,
                students=10
            )
        self.assertIn("maximum 3 versions", str(cm.exception))

    def test_tier_student_limits(self):
        """Test tier student limits are enforced"""
        # Free tier allows max 30 students
        with self.assertRaises(ValueError) as cm:
            self.gen_free.generate(
                title="Test",
                versions=2,
                students=50
            )
        self.assertIn("maximum 30 students", str(cm.exception))

    def test_tier_strategy_restrictions(self):
        """Test tier strategy restrictions"""
        # Free tier only allows round_robin
        with self.assertRaises(ValueError) as cm:
            self.gen_free.generate(
                title="Test",
                versions=2,
                students=10,
                strategy="difficulty_balanced"
            )
        self.assertIn("not available in tier", str(cm.exception))

        # Pro tier allows difficulty_balanced
        config = self.gen_pro.generate(
            title="Test",
            versions=2,
            students=10,
            strategy="difficulty_balanced"
        )
        self.assertEqual(config["distribution"]["strategy"], "difficulty_balanced")

    def test_randomization_options_tier_restricted(self):
        """Test randomization options are tier-restricted"""
        # Free tier should not include randomization even if requested
        config = self.gen_free.generate(
            title="Test",
            versions=2,
            students=10,
            randomize_questions=True
        )
        # Should not have randomize_questions in output
        self.assertNotIn("randomize_questions", config["distribution"])

        # Pro tier should include it
        config = self.gen_pro.generate(
            title="Test",
            versions=2,
            students=10,
            randomize_questions=True
        )
        self.assertTrue(config["distribution"]["randomize_questions"])

    def test_template_tier_restrictions(self):
        """Test template tier restrictions"""
        # Free tier only allows basic template
        with self.assertRaises(ValueError) as cm:
            self.gen_free.generate(
                title="Test",
                versions=2,
                students=10,
                template_name="branded"
            )
        self.assertIn("not available in tier", str(cm.exception))

        # Pro tier allows branded
        config = self.gen_pro.generate(
            title="Test",
            versions=2,
            students=10,
            template_name="branded"
        )
        self.assertEqual(config["template"]["name"], "branded")

    def test_metadata_fields(self):
        """Test optional metadata fields"""
        config = self.gen_pro.generate(
            title="Midterm Exam",
            versions=3,
            students=20,
            subtitle="Fall 2025",
            duration_minutes=90,
            instructions="Answer all questions"
        )

        self.assertEqual(config["test_info"]["subtitle"], "Fall 2025")
        self.assertEqual(config["test_info"]["duration_minutes"], 90)
        self.assertEqual(config["test_info"]["instructions"], "Answer all questions")

    def test_tier_restrictions_included(self):
        """Test that tier_restrictions are included in output"""
        config = self.gen_free.generate(
            title="Test",
            versions=2,
            students=10
        )

        self.assertIn("tier_restrictions", config)
        restrictions = config["tier_restrictions"]
        self.assertIn("question_types_allowed", restrictions)
        self.assertIn("distribution_strategies_allowed", restrictions)
        self.assertIn("max_versions", restrictions)
        self.assertIn("max_students", restrictions)

    def test_student_placeholders_generation(self):
        """Test student placeholder generation"""
        config = self.gen_free.generate(
            title="Test",
            versions=2,
            students=5,
            generate_student_placeholders=True
        )

        self.assertIn("students_list", config)
        self.assertEqual(len(config["students_list"]), 5)
        self.assertEqual(config["students_list"][0]["id"], "s001")
        self.assertEqual(config["students_list"][0]["name"], "Student 1")

    def test_custom_students_list(self):
        """Test custom students list"""
        students = [
            {"id": "s1", "name": "Alice"},
            {"id": "s2", "name": "Bob"}
        ]

        config = self.gen_free.generate(
            title="Test",
            versions=2,
            students=2,
            students_list=students
        )

        self.assertEqual(config["students_list"], students)

    def test_template_personalization_options(self):
        """Test template personalization options"""
        # Free tier should not include personalization
        config = self.gen_free.generate(
            title="Test",
            versions=2,
            students=10,
            include_student_name=True
        )
        # Should not have personalization or should be empty
        if "personalization" in config["template"]:
            self.assertNotIn("include_student_name", config["template"]["personalization"])

        # Pro tier should include it
        config = self.gen_pro.generate(
            title="Test",
            versions=2,
            students=10,
            include_student_name=True
        )
        self.assertIn("personalization", config["template"])
        self.assertTrue(config["template"]["personalization"]["include_student_name"])

    def test_scanning_configuration(self):
        """Test scanning configuration"""
        config = self.gen_free.generate(
            title="Test",
            versions=2,
            students=10,
            page_size="Letter",
            dpi=300
        )

        self.assertIn("scanning", config)
        self.assertEqual(config["scanning"]["page_size"], "Letter")
        self.assertEqual(config["scanning"]["dpi"], 300)

    def test_invalid_tier(self):
        """Test invalid tier raises error"""
        with self.assertRaises(ValueError):
            ConfigGenerator(tier="invalid")

    def test_enterprise_unlimited_limits(self):
        """Test enterprise tier has no limits"""
        # Enterprise tier should allow large numbers
        config = self.gen_enterprise.generate(
            title="Test",
            versions=50,
            students=500
        )
        self.assertEqual(config["distribution"]["versions"], 50)
        self.assertEqual(config["distribution"]["students"], 500)

    def test_output_structure_matches_schema(self):
        """Test output structure matches expected schema"""
        config = self.gen_pro.generate(
            title="Test",
            versions=3,
            students=20,
            subtitle="Subtitle",
            duration_minutes=60
        )

        # Check required top-level fields
        self.assertIn("version", config)
        self.assertIn("tier", config)
        self.assertIn("test_info", config)
        self.assertIn("distribution", config)
        self.assertIn("template", config)
        self.assertIn("scanning", config)
        self.assertIn("tier_restrictions", config)

        # Check test_info structure
        self.assertIn("title", config["test_info"])
        self.assertIn("date", config["test_info"])

        # Check distribution structure
        self.assertIn("versions", config["distribution"])
        self.assertIn("students", config["distribution"])
        self.assertIn("strategy", config["distribution"])


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    run_tests()
