#!/usr/bin/env python3
"""
scorer - Score extracted answers against correct answers

Compares scan results with question orders to generate scores.
This is a dependent tool that requires scan_result.json and question_order.json.

Usage:
    scorer scan_result.json question_order.json --output scores.json

Input: scan_result.json + question_order.json
Output: scores.json with grades and statistics
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import statistics


class Scorer:
    """Scorer for grading extracted answers"""

    # Tier configurations
    TIER_CONFIGS = {
        "free": {
            "scoring_models": ["basic_correct_incorrect"],
            "allow_partial_credit": False,
            "allow_question_weighting": False,
            "allow_curved_grading": False
        },
        "pro": {
            "scoring_models": ["basic_correct_incorrect", "partial_credit"],
            "allow_partial_credit": True,
            "allow_question_weighting": True,
            "allow_curved_grading": False
        },
        "enterprise": {
            "scoring_models": ["basic_correct_incorrect", "partial_credit", "rubric_based", "curved"],
            "allow_partial_credit": True,
            "allow_question_weighting": True,
            "allow_curved_grading": True
        }
    }

    # Standard grading scale
    GRADING_SCALE = {
        "A": {"min": 90, "max": 100},
        "B": {"min": 80, "max": 89.99},
        "C": {"min": 70, "max": 79.99},
        "D": {"min": 60, "max": 69.99},
        "F": {"min": 0, "max": 59.99}
    }

    def __init__(self, tier: str = "free"):
        """Initialize scorer with tier configuration"""
        if tier not in self.TIER_CONFIGS:
            raise ValueError(f"Invalid tier: {tier}. Must be one of: {list(self.TIER_CONFIGS.keys())}")
        self.tier = tier
        self.config = self.TIER_CONFIGS[tier]
        self.version = "scorer-1.0.0"

    def score_scan(
        self,
        scan_result: Dict[str, Any],
        question_order: Dict[str, Any],
        scoring_model: str = "basic_correct_incorrect"
    ) -> Dict[str, Any]:
        """
        Score a single scan result

        Args:
            scan_result: Scan result data
            question_order: Question order data with correct answers
            scoring_model: Scoring model to use

        Returns:
            Scores dictionary for this student
        """
        # Validate scoring model
        if scoring_model not in self.config["scoring_models"]:
            raise ValueError(
                f"Scoring model '{scoring_model}' not available in tier '{self.tier}'. "
                f"Available: {self.config['scoring_models']}"
            )

        # Get student and version info
        student_id = scan_result["identification"]["student_id"]
        version_id = scan_result["identification"]["version_id"]

        # Get correct answers for this version
        version_data = question_order["versions"].get(version_id)
        if not version_data:
            raise ValueError(f"Version '{version_id}' not found in question_order")

        # Build question lookup
        correct_answers = {}
        question_info = {}
        for q in version_data["questions"]:
            q_id = q["question_id"]
            correct_answers[q_id] = q["correct_answer"]
            question_info[q_id] = q

        # Score each answer
        question_scores = []
        for answer in scan_result["answers"]:
            q_id = answer["question_id"]

            if q_id not in correct_answers:
                print(f"Warning: Question {q_id} not found in question_order", file=sys.stderr)
                continue

            q_info = question_info[q_id]
            correct_answer = correct_answers[q_id]
            student_answer = answer.get("extracted_answer")
            points_possible = q_info.get("points", 1)

            # Determine if correct
            is_correct = self._check_answer(
                student_answer,
                correct_answer,
                q_info["question_type"]
            )

            # Calculate points earned
            if is_correct:
                points_earned = points_possible
            elif self.config["allow_partial_credit"] and scoring_model == "partial_credit":
                points_earned = self._calculate_partial_credit(
                    student_answer,
                    correct_answer,
                    points_possible,
                    q_info
                )
            else:
                points_earned = 0

            # Build question score
            q_score = {
                "question_id": q_id,
                "question_number": answer.get("question_number", 0),
                "question_type": answer.get("question_type"),
                "student_answer": student_answer,
                "correct_answer": correct_answer,
                "points_earned": points_earned,
                "points_possible": points_possible,
                "is_correct": is_correct,
                "partial_credit": points_earned > 0 and not is_correct,
                "confidence": answer.get("confidence", 0.0)
            }

            # Add flags if any
            if "flags" in answer:
                q_score["flags"] = answer["flags"]
            elif answer.get("confidence", 1.0) < 0.7:
                q_score["flags"] = ["low_confidence"]

            question_scores.append(q_score)

        # Calculate summary statistics
        total_points_earned = sum(q["points_earned"] for q in question_scores)
        total_points_possible = sum(q["points_possible"] for q in question_scores)
        percentage = (total_points_earned / total_points_possible * 100) if total_points_possible > 0 else 0

        summary = {
            "total_points_earned": round(total_points_earned, 2),
            "total_points_possible": round(total_points_possible, 2),
            "percentage": round(percentage, 2),
            "letter_grade": self._calculate_letter_grade(percentage),
            "questions_correct": sum(1 for q in question_scores if q["is_correct"]),
            "questions_incorrect": sum(1 for q in question_scores if not q["is_correct"]),
            "questions_unanswered": 0,  # Would check for null answers
            "questions_flagged": sum(1 for q in question_scores if q.get("flags")),
            "average_confidence": round(
                sum(q["confidence"] for q in question_scores) / len(question_scores), 3
            ) if question_scores else 0.0
        }

        return {
            "student_id": student_id,
            "student_name": None,  # Would get from config if available
            "version_id": version_id,
            "scan_reference": scan_result["scan_metadata"]["image_source"],
            "question_scores": question_scores,
            "summary": summary
        }

    def score_batch(
        self,
        scan_results: List[Dict[str, Any]],
        question_order: Dict[str, Any],
        scoring_model: str = "basic_correct_incorrect",
        calculate_class_stats: bool = False
    ) -> Dict[str, Any]:
        """
        Score multiple scan results

        Args:
            scan_results: List of scan result data
            question_order: Question order data
            scoring_model: Scoring model to use
            calculate_class_stats: Whether to calculate class statistics

        Returns:
            Complete scores dictionary with all students
        """
        # Score each student
        student_results = []
        for scan_result in scan_results:
            try:
                result = self.score_scan(scan_result, question_order, scoring_model)
                student_results.append(result)
            except Exception as e:
                print(f"Error scoring student: {e}", file=sys.stderr)
                continue

        # Build complete result
        test_info = question_order.get("test_info", {})

        scores = {
            "version": "1.0.0",
            "scoring_metadata": {
                "scoring_timestamp": datetime.utcnow().isoformat() + 'Z',
                "scorer_version": self.version,
                "scoring_model": scoring_model,
                "test_info": test_info
            },
            "student_results": student_results
        }

        # Add class statistics if enabled
        if calculate_class_stats and student_results:
            scores["class_statistics"] = self._calculate_class_statistics(student_results)

        # Add grading scale
        scores["grading_scale"] = self.GRADING_SCALE

        return scores

    def _check_answer(self, student_answer: Any, correct_answer: Any, question_type: str) -> bool:
        """Check if answer is correct"""
        if student_answer is None:
            return False

        # Normalize for comparison
        if isinstance(student_answer, str) and isinstance(correct_answer, str):
            # Case-insensitive, strip whitespace
            return student_answer.strip().lower() == correct_answer.strip().lower()

        return student_answer == correct_answer

    def _calculate_partial_credit(
        self,
        student_answer: Any,
        correct_answer: Any,
        points_possible: float,
        question_info: Dict[str, Any]
    ) -> float:
        """Calculate partial credit (if tier allows)"""
        # Check if question has partial credit rules
        if "partial_credit" in question_info:
            pc_config = question_info["partial_credit"]
            if pc_config.get("enabled"):
                for rule in pc_config.get("rules", []):
                    if self._check_answer(student_answer, rule["answer"], question_info["question_type"]):
                        return points_possible * rule["points"]

        # No partial credit applicable
        return 0.0

    def _calculate_letter_grade(self, percentage: float) -> str:
        """Calculate letter grade from percentage"""
        for grade, range_data in self.GRADING_SCALE.items():
            if range_data["min"] <= percentage <= range_data["max"]:
                return grade
        return "F"

    def _calculate_class_statistics(self, student_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate class-level statistics (pro/enterprise tier)"""
        if not student_results:
            return {}

        percentages = [s["summary"]["percentage"] for s in student_results]

        # Grade distribution
        grade_dist = {}
        for student in student_results:
            grade = student["summary"]["letter_grade"]
            grade_dist[grade] = grade_dist.get(grade, 0) + 1

        stats = {
            "total_students": len(student_results),
            "mean_score": round(statistics.mean(percentages), 2),
            "median_score": round(statistics.median(percentages), 2),
            "std_dev": round(statistics.stdev(percentages), 2) if len(percentages) > 1 else 0.0,
            "min_score": round(min(percentages), 2),
            "max_score": round(max(percentages), 2),
            "grade_distribution": grade_dist
        }

        return stats


def main():
    parser = argparse.ArgumentParser(
        description='Score extracted answers against correct answers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Score single scan
    scorer scan_result.json question_order.json --output scores.json

    # Score multiple scans with class statistics
    scorer scans/*.json --question-order question_order.json \\
        --class-stats --output scores.json

    # Use partial credit model (pro tier)
    scorer scan_result.json question_order.json \\
        --tier pro --model partial_credit --output scores.json
        """
    )

    parser.add_argument('scans', nargs='+', type=str,
                        help='Scan result JSON file(s)')
    parser.add_argument('--question-order', type=str, required=True,
                        help='Question order JSON file')
    parser.add_argument('--tier', type=str, default='free',
                        choices=['free', 'pro', 'enterprise'],
                        help='Tier level (default: free)')
    parser.add_argument('--model', type=str, default='basic_correct_incorrect',
                        choices=['basic_correct_incorrect', 'partial_credit', 'rubric_based', 'curved'],
                        help='Scoring model (default: basic_correct_incorrect)')
    parser.add_argument('--class-stats', action='store_true',
                        help='Calculate class statistics (pro/enterprise tier)')
    parser.add_argument('--output', '-o', type=str,
                        help='Output JSON file (default: stdout)')

    args = parser.parse_args()

    # Load question order
    try:
        with open(args.question_order, 'r') as f:
            question_order = json.load(f)
    except FileNotFoundError:
        print(f"Error: Question order file '{args.question_order}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing question order JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Load scan results
    scan_results = []
    for scan_file in args.scans:
        try:
            with open(scan_file, 'r') as f:
                scan_result = json.load(f)
                scan_results.append(scan_result)
        except FileNotFoundError:
            print(f"Warning: Scan file '{scan_file}' not found, skipping", file=sys.stderr)
        except json.JSONDecodeError as e:
            print(f"Warning: Error parsing '{scan_file}': {e}, skipping", file=sys.stderr)

    if not scan_results:
        print("Error: No valid scan results loaded", file=sys.stderr)
        sys.exit(1)

    # Score
    try:
        scorer = Scorer(tier=args.tier)

        scores = scorer.score_batch(
            scan_results,
            question_order,
            scoring_model=args.model,
            calculate_class_stats=args.class_stats
        )

        print(f"Scored {len(scores['student_results'])} students", file=sys.stderr)

        if args.class_stats and "class_statistics" in scores:
            stats = scores["class_statistics"]
            print(f"Class mean: {stats['mean_score']:.1f}%", file=sys.stderr)

    except Exception as e:
        print(f"Error scoring: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Output
    json_output = json.dumps(scores, indent=2, ensure_ascii=False)

    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"Successfully wrote scores to {args.output}", file=sys.stderr)
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(json_output)


if __name__ == '__main__':
    main()
