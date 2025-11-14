#!/usr/bin/env python3
"""
configgen - Generate test configuration JSON

Creates configuration files for test generation with tier-aware settings.
This tool generates config.json files matching the config schema.

Usage:
    configgen --title "Exam Title" --versions 3 --students 30 [options]

Input: Command-line parameters
Output: config.json matching schema
"""

import argparse
import json
import sys
from datetime import datetime, date
from typing import Dict, List, Any, Optional
from pathlib import Path


class ConfigGenerator:
    """Generator for test configuration"""

    # Tier configurations matching the README
    TIER_CONFIGS = {
        "free": {
            "distribution_strategies": ["round_robin"],
            "allow_randomize_questions": False,
            "allow_randomize_options": False,
            "allow_difficulty_balancing": False,
            "allow_type_balancing": False,
            "version_limits": 3,
            "student_limits": 30,
            "question_types_allowed": ["multiple_choice", "true_false"],
            "distribution_strategies_allowed": ["round_robin"],
            "templates_available": ["basic"],
            "allow_student_name_personalization": False,
            "allow_custom_header_footer": False,
            "allow_timestamp_embedding": False
        },
        "pro": {
            "distribution_strategies": ["round_robin", "random", "difficulty_balanced"],
            "allow_randomize_questions": True,
            "allow_randomize_options": True,
            "allow_difficulty_balancing": True,
            "allow_type_balancing": True,
            "version_limits": 10,
            "student_limits": 100,
            "question_types_allowed": ["multiple_choice", "short_answer", "true_false"],
            "distribution_strategies_allowed": ["round_robin", "random", "difficulty_balanced"],
            "templates_available": ["basic", "branded"],
            "allow_student_name_personalization": True,
            "allow_custom_header_footer": True,
            "allow_timestamp_embedding": True
        },
        "enterprise": {
            "distribution_strategies": ["round_robin", "random", "difficulty_balanced", "adaptive"],
            "allow_randomize_questions": True,
            "allow_randomize_options": True,
            "allow_difficulty_balancing": True,
            "allow_type_balancing": True,
            "version_limits": None,
            "student_limits": None,
            "question_types_allowed": ["multiple_choice", "short_answer", "essay", "matching", "true_false"],
            "distribution_strategies_allowed": ["round_robin", "random", "difficulty_balanced", "adaptive"],
            "templates_available": ["basic", "branded", "watermarked"],
            "allow_student_name_personalization": True,
            "allow_custom_header_footer": True,
            "allow_timestamp_embedding": True
        }
    }

    def __init__(self, tier: str = "free"):
        """Initialize config generator with tier"""
        if tier not in self.TIER_CONFIGS:
            raise ValueError(f"Invalid tier: {tier}. Must be one of: {list(self.TIER_CONFIGS.keys())}")
        self.tier = tier
        self.config = self.TIER_CONFIGS[tier]

    def generate(
        self,
        title: str,
        versions: int,
        students: int,
        date_str: Optional[str] = None,
        subtitle: Optional[str] = None,
        duration_minutes: Optional[int] = None,
        instructions: Optional[str] = None,
        strategy: str = "round_robin",
        randomize_questions: bool = False,
        randomize_options: bool = False,
        students_list: Optional[List[Dict[str, Any]]] = None,
        template_name: str = "basic",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate configuration dictionary

        Args:
            title: Test title
            versions: Number of test versions
            students: Number of students
            date_str: Test date (ISO format)
            subtitle: Optional subtitle
            duration_minutes: Duration in minutes
            instructions: Student instructions
            strategy: Distribution strategy
            randomize_questions: Whether to randomize question order
            randomize_options: Whether to randomize answer options
            students_list: Optional list of student objects
            template_name: Template name
            **kwargs: Additional options

        Returns:
            Configuration dictionary matching schema
        """
        # Validate tier limits
        self._validate_tier_limits(versions, students, strategy, template_name)

        # Build test_info
        test_info = {
            "title": title,
            "date": date_str if date_str else date.today().isoformat()
        }

        if subtitle:
            test_info["subtitle"] = subtitle
        if duration_minutes:
            test_info["duration_minutes"] = duration_minutes
        if instructions:
            test_info["instructions"] = instructions

        # Build distribution
        distribution = {
            "versions": versions,
            "students": students,
            "strategy": strategy
        }

        # Add randomization options if allowed
        if randomize_questions and self.config["allow_randomize_questions"]:
            distribution["randomize_questions"] = True
        elif randomize_questions:
            print(f"Warning: randomize_questions not available in tier '{self.tier}'", file=sys.stderr)

        if randomize_options and self.config["allow_randomize_options"]:
            distribution["randomize_options"] = True
        elif randomize_options:
            print(f"Warning: randomize_options not available in tier '{self.tier}'", file=sys.stderr)

        # Build config
        config = {
            "version": "1.0.0",
            "tier": self.tier,
            "test_info": test_info,
            "distribution": distribution
        }

        # Add students list if provided
        if students_list:
            config["students_list"] = students_list
        elif kwargs.get("generate_student_placeholders", False):
            config["students_list"] = self._generate_student_placeholders(students)

        # Add template configuration
        config["template"] = self._build_template_config(
            template_name,
            kwargs.get("header"),
            kwargs.get("footer"),
            kwargs.get("logo_url"),
            kwargs.get("include_student_name", False),
            kwargs.get("include_timestamp", False)
        )

        # Add scanning configuration
        config["scanning"] = {
            "registration_mark_density": kwargs.get("mark_density", "standard"),
            "answer_field_type": kwargs.get("answer_field_type", "circle"),
            "page_size": kwargs.get("page_size", "A4"),
            "dpi": kwargs.get("dpi", 300)
        }

        # Add tier restrictions
        config["tier_restrictions"] = {
            "question_types_allowed": self.config["question_types_allowed"],
            "distribution_strategies_allowed": self.config["distribution_strategies_allowed"]
        }

        if self.config["version_limits"]:
            config["tier_restrictions"]["max_versions"] = self.config["version_limits"]
        if self.config["student_limits"]:
            config["tier_restrictions"]["max_students"] = self.config["student_limits"]

        return config

    def _validate_tier_limits(self, versions: int, students: int, strategy: str, template_name: str):
        """Validate parameters against tier limits"""
        # Check version limits
        if self.config["version_limits"] and versions > self.config["version_limits"]:
            raise ValueError(
                f"Tier '{self.tier}' allows maximum {self.config['version_limits']} versions. "
                f"Requested: {versions}"
            )

        # Check student limits
        if self.config["student_limits"] and students > self.config["student_limits"]:
            raise ValueError(
                f"Tier '{self.tier}' allows maximum {self.config['student_limits']} students. "
                f"Requested: {students}"
            )

        # Check distribution strategy
        if strategy not in self.config["distribution_strategies_allowed"]:
            raise ValueError(
                f"Strategy '{strategy}' not available in tier '{self.tier}'. "
                f"Available: {self.config['distribution_strategies_allowed']}"
            )

        # Check template
        if template_name not in self.config["templates_available"]:
            raise ValueError(
                f"Template '{template_name}' not available in tier '{self.tier}'. "
                f"Available: {self.config['templates_available']}"
            )

    def _build_template_config(
        self,
        template_name: str,
        header: Optional[str],
        footer: Optional[str],
        logo_url: Optional[str],
        include_student_name: bool,
        include_timestamp: bool
    ) -> Dict[str, Any]:
        """Build template configuration"""
        template = {"name": template_name}

        personalization = {}
        if include_student_name and self.config["allow_student_name_personalization"]:
            personalization["include_student_name"] = True
        if include_timestamp and self.config["allow_timestamp_embedding"]:
            personalization["include_timestamp"] = True

        if personalization:
            template["personalization"] = personalization

        if header and self.config["allow_custom_header_footer"]:
            template["header"] = header
        if footer and self.config["allow_custom_header_footer"]:
            template["footer"] = footer
        if logo_url and self.tier in ["pro", "enterprise"]:
            template["logo_url"] = logo_url

        return template

    def _generate_student_placeholders(self, count: int) -> List[Dict[str, str]]:
        """Generate placeholder student list"""
        students = []
        for i in range(1, count + 1):
            student = {
                "id": f"s{i:03d}",
                "name": f"Student {i}"
            }
            students.append(student)
        return students


def load_students_from_file(file_path: str) -> List[Dict[str, Any]]:
    """Load students from JSON or CSV file"""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Students file not found: {file_path}")

    if path.suffix == '.json':
        with open(path) as f:
            students = json.load(f)
        return students
    elif path.suffix == '.csv':
        import csv
        students = []
        with open(path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                student = {
                    "id": row.get("id", row.get("student_id", "")),
                    "name": row.get("name", row.get("student_name", ""))
                }
                if "email" in row:
                    student["email"] = row["email"]
                students.append(student)
        return students
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}. Use .json or .csv")


def main():
    parser = argparse.ArgumentParser(
        description='Generate test configuration JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic configuration
    configgen --title "Midterm Exam" --versions 3 --students 30

    # With tier and options
    configgen --title "Final Exam" --versions 5 --students 50 \\
        --tier pro --strategy random --randomize-questions

    # Load students from file
    configgen --title "Quiz 1" --versions 2 --students 20 \\
        --students-file students.csv

    # Full configuration
    configgen --title "Midterm" --subtitle "Fall 2025" \\
        --versions 3 --students 30 --tier pro \\
        --date 2025-11-20 --duration 90 \\
        --strategy difficulty_balanced --randomize-questions \\
        --template branded --header "CS Department" \\
        --output config.json
        """
    )

    # Required arguments
    parser.add_argument('--title', type=str, required=True, help='Test title')
    parser.add_argument('--versions', type=int, required=True, help='Number of test versions')
    parser.add_argument('--students', type=int, required=True, help='Number of students')

    # Optional test info
    parser.add_argument('--subtitle', type=str, help='Test subtitle')
    parser.add_argument('--date', type=str, help='Test date (YYYY-MM-DD)')
    parser.add_argument('--duration', type=int, help='Duration in minutes')
    parser.add_argument('--instructions', type=str, help='Student instructions')

    # Distribution options
    parser.add_argument('--tier', type=str, default='free',
                        choices=['free', 'pro', 'enterprise'],
                        help='Tier level (default: free)')
    parser.add_argument('--strategy', type=str, default='round_robin',
                        choices=['round_robin', 'random', 'difficulty_balanced', 'adaptive'],
                        help='Distribution strategy (default: round_robin)')
    parser.add_argument('--randomize-questions', action='store_true',
                        help='Randomize question order')
    parser.add_argument('--randomize-options', action='store_true',
                        help='Randomize answer options')

    # Students
    parser.add_argument('--students-file', type=str,
                        help='Load students from JSON/CSV file')
    parser.add_argument('--generate-placeholders', action='store_true',
                        help='Generate placeholder student list')

    # Template
    parser.add_argument('--template', type=str, default='basic',
                        choices=['basic', 'branded', 'watermarked'],
                        help='Template name (default: basic)')
    parser.add_argument('--header', type=str, help='Custom header text')
    parser.add_argument('--footer', type=str, help='Custom footer text')
    parser.add_argument('--logo-url', type=str, help='Logo URL')
    parser.add_argument('--include-student-name', action='store_true',
                        help='Include student name on test')
    parser.add_argument('--include-timestamp', action='store_true',
                        help='Include generation timestamp')

    # Scanning
    parser.add_argument('--page-size', type=str, default='A4',
                        choices=['A4', 'Letter', 'Legal'],
                        help='Page size (default: A4)')
    parser.add_argument('--dpi', type=int, default=300,
                        choices=[150, 200, 300, 600],
                        help='Scan DPI (default: 300)')

    # Output
    parser.add_argument('--output', '-o', type=str,
                        help='Output JSON file (default: stdout)')

    args = parser.parse_args()

    # Load students if file provided
    students_list = None
    if args.students_file:
        try:
            students_list = load_students_from_file(args.students_file)
            print(f"Loaded {len(students_list)} students from {args.students_file}", file=sys.stderr)
        except Exception as e:
            print(f"Error loading students file: {e}", file=sys.stderr)
            sys.exit(1)

    # Generate configuration
    try:
        generator = ConfigGenerator(tier=args.tier)
        config = generator.generate(
            title=args.title,
            versions=args.versions,
            students=args.students,
            date_str=args.date,
            subtitle=args.subtitle,
            duration_minutes=args.duration,
            instructions=args.instructions,
            strategy=args.strategy,
            randomize_questions=args.randomize_questions,
            randomize_options=args.randomize_options,
            students_list=students_list,
            template_name=args.template,
            header=args.header,
            footer=args.footer,
            logo_url=args.logo_url,
            include_student_name=args.include_student_name,
            include_timestamp=args.include_timestamp,
            page_size=args.page_size,
            dpi=args.dpi,
            generate_student_placeholders=args.generate_placeholders
        )
    except Exception as e:
        print(f"Error generating configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Output
    json_output = json.dumps(config, indent=2, ensure_ascii=False)

    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"Successfully wrote configuration to {args.output}", file=sys.stderr)
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(json_output)


if __name__ == '__main__':
    main()
