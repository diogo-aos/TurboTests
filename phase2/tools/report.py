#!/usr/bin/env python3
"""
report - Generate reports from scoring results

Generates human-readable reports in various formats (HTML, Markdown, PDF)
from scores.json files.

Usage:
    report scores.json --format html --output report.html

Input: scores.json matching schema
Output: Formatted report (HTML/Markdown/PDF)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class ReportGenerator:
    """Generator for test scoring reports"""

    # Tier configurations
    TIER_CONFIGS = {
        "free": {
            "report_templates_available": ["basic"],
            "analytics_level": "none",
            "include_metrics": ["score", "grade"],
            "export_formats": ["html", "markdown"],
            "visualization_types": [],
            "include_item_analysis": False,
            "include_learning_curves": False,
            "include_peer_comparison": False,
            "class_report_enabled": False
        },
        "pro": {
            "report_templates_available": ["basic", "detailed"],
            "analytics_level": "basic",
            "include_metrics": ["score", "grade", "mean", "std_dev", "percentile"],
            "export_formats": ["html", "markdown", "csv"],
            "visualization_types": ["bar_chart"],
            "include_item_analysis": False,
            "include_learning_curves": False,
            "include_peer_comparison": True,
            "class_report_enabled": True
        },
        "enterprise": {
            "report_templates_available": ["basic", "detailed", "comprehensive"],
            "analytics_level": "advanced",
            "include_metrics": ["score", "grade", "mean", "std_dev", "percentile", "quartiles"],
            "export_formats": ["html", "markdown", "csv", "pdf"],
            "visualization_types": ["bar_chart", "histogram", "scatter"],
            "include_item_analysis": True,
            "include_learning_curves": True,
            "include_peer_comparison": True,
            "class_report_enabled": True
        }
    }

    def __init__(self, tier: str = "free"):
        """Initialize report generator with tier"""
        if tier not in self.TIER_CONFIGS:
            raise ValueError(f"Invalid tier: {tier}. Must be one of: {list(self.TIER_CONFIGS.keys())}")
        self.tier = tier
        self.config = self.TIER_CONFIGS[tier]

    def generate_html(self, scores: Dict[str, Any], template: str = "basic") -> str:
        """Generate HTML report"""
        self._validate_tier_support("html", template)

        html = []
        html.append("<!DOCTYPE html>")
        html.append("<html lang='en'>")
        html.append("<head>")
        html.append("    <meta charset='UTF-8'>")
        html.append("    <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
        html.append(f"    <title>Test Results Report</title>")
        html.append(self._get_css())
        html.append("</head>")
        html.append("<body>")
        html.append("    <div class='container'>")

        # Header
        html.append(self._generate_html_header(scores))

        # Class statistics (if enabled for tier)
        if self.config["class_report_enabled"] and "class_statistics" in scores:
            html.append(self._generate_html_class_stats(scores["class_statistics"]))

        # Student results
        html.append(self._generate_html_student_results(scores["student_results"]))

        # Question analysis (enterprise tier)
        if self.config["include_item_analysis"] and "class_statistics" in scores:
            if "question_analysis" in scores["class_statistics"]:
                html.append(self._generate_html_question_analysis(
                    scores["class_statistics"]["question_analysis"]
                ))

        html.append("    </div>")
        html.append("</body>")
        html.append("</html>")

        return "\n".join(html)

    def generate_markdown(self, scores: Dict[str, Any]) -> str:
        """Generate Markdown report"""
        self._validate_tier_support("markdown", "basic")

        md = []

        # Header
        metadata = scores.get("scoring_metadata", {})
        test_info = metadata.get("test_info", {})

        md.append(f"# Test Results Report")
        md.append("")
        md.append(f"**Test:** {test_info.get('title', 'N/A')}")
        md.append(f"**Date:** {test_info.get('date', 'N/A')}")
        md.append(f"**Scored:** {metadata.get('scoring_timestamp', 'N/A')}")
        md.append("")

        # Class statistics
        if self.config["class_report_enabled"] and "class_statistics" in scores:
            md.append("## Class Statistics")
            md.append("")
            stats = scores["class_statistics"]
            md.append(f"- **Total Students:** {stats.get('total_students', 0)}")
            md.append(f"- **Mean Score:** {stats.get('mean_score', 0):.2f}%")
            md.append(f"- **Median Score:** {stats.get('median_score', 0):.2f}%")
            md.append(f"- **Std Dev:** {stats.get('std_dev', 0):.2f}")
            md.append(f"- **Min Score:** {stats.get('min_score', 0):.2f}%")
            md.append(f"- **Max Score:** {stats.get('max_score', 0):.2f}%")
            md.append("")

        # Student results
        md.append("## Student Results")
        md.append("")

        for result in scores["student_results"]:
            student_name = result.get("student_name", result["student_id"])
            summary = result["summary"]

            md.append(f"### {student_name}")
            md.append("")
            md.append(f"- **Score:** {summary['percentage']:.1f}% ({summary['total_points_earned']}/{summary['total_points_possible']})")
            if "letter_grade" in summary:
                md.append(f"- **Grade:** {summary['letter_grade']}")
            md.append(f"- **Correct:** {summary.get('questions_correct', 0)}")
            md.append(f"- **Incorrect:** {summary.get('questions_incorrect', 0)}")
            md.append("")

            # Question details (if detailed template)
            if "detailed" in self.config["report_templates_available"]:
                md.append("#### Question Details")
                md.append("")
                md.append("| Q# | Type | Answer | Correct | Points |")
                md.append("|---|---|---|---|---|")

                for q in result["question_scores"]:
                    q_num = q.get("question_number", "?")
                    q_type = q.get("question_type", "?")[:15]
                    answer = str(q.get("student_answer", "N/A"))[:20]
                    correct = "✓" if q["is_correct"] else "✗"
                    points = f"{q['points_earned']}/{q['points_possible']}"

                    md.append(f"| {q_num} | {q_type} | {answer} | {correct} | {points} |")

                md.append("")

        return "\n".join(md)

    def _generate_html_header(self, scores: Dict[str, Any]) -> str:
        """Generate HTML header section"""
        metadata = scores.get("scoring_metadata", {})
        test_info = metadata.get("test_info", {})

        html = []
        html.append("        <header>")
        html.append(f"            <h1>Test Results Report</h1>")
        html.append(f"            <div class='test-info'>")
        html.append(f"                <p><strong>Test:</strong> {test_info.get('title', 'N/A')}</p>")
        html.append(f"                <p><strong>Date:</strong> {test_info.get('date', 'N/A')}</p>")
        html.append(f"                <p><strong>Total Points:</strong> {test_info.get('total_points', 'N/A')}</p>")
        html.append(f"                <p><strong>Scored:</strong> {metadata.get('scoring_timestamp', 'N/A')}</p>")
        html.append(f"            </div>")
        html.append("        </header>")
        return "\n".join(html)

    def _generate_html_class_stats(self, stats: Dict[str, Any]) -> str:
        """Generate HTML class statistics section"""
        html = []
        html.append("        <section class='class-stats'>")
        html.append("            <h2>Class Statistics</h2>")
        html.append("            <div class='stats-grid'>")
        html.append(f"                <div class='stat-box'>")
        html.append(f"                    <div class='stat-label'>Students</div>")
        html.append(f"                    <div class='stat-value'>{stats.get('total_students', 0)}</div>")
        html.append(f"                </div>")
        html.append(f"                <div class='stat-box'>")
        html.append(f"                    <div class='stat-label'>Mean</div>")
        html.append(f"                    <div class='stat-value'>{stats.get('mean_score', 0):.1f}%</div>")
        html.append(f"                </div>")
        html.append(f"                <div class='stat-box'>")
        html.append(f"                    <div class='stat-label'>Median</div>")
        html.append(f"                    <div class='stat-value'>{stats.get('median_score', 0):.1f}%</div>")
        html.append(f"                </div>")
        html.append(f"                <div class='stat-box'>")
        html.append(f"                    <div class='stat-label'>Std Dev</div>")
        html.append(f"                    <div class='stat-value'>{stats.get('std_dev', 0):.2f}</div>")
        html.append(f"                </div>")
        html.append("            </div>")

        # Grade distribution (if available)
        if "grade_distribution" in stats:
            html.append("            <h3>Grade Distribution</h3>")
            html.append("            <div class='grade-dist'>")
            for grade, count in sorted(stats["grade_distribution"].items()):
                html.append(f"                <div class='grade-bar'>{grade}: {count}</div>")
            html.append("            </div>")

        html.append("        </section>")
        return "\n".join(html)

    def _generate_html_student_results(self, results: List[Dict[str, Any]]) -> str:
        """Generate HTML student results section"""
        html = []
        html.append("        <section class='student-results'>")
        html.append("            <h2>Student Results</h2>")

        for result in results:
            student_name = result.get("student_name", result["student_id"])
            summary = result["summary"]

            html.append(f"            <div class='student-card'>")
            html.append(f"                <h3>{student_name}</h3>")
            html.append(f"                <div class='score-summary'>")
            html.append(f"                    <div class='score-main'>")
            html.append(f"                        <span class='percentage'>{summary['percentage']:.1f}%</span>")
            if "letter_grade" in summary:
                html.append(f"                        <span class='grade'>{summary['letter_grade']}</span>")
            html.append(f"                    </div>")
            html.append(f"                    <div class='score-detail'>")
            html.append(f"                        Points: {summary['total_points_earned']}/{summary['total_points_possible']}")
            html.append(f"                    </div>")
            html.append(f"                </div>")

            # Question breakdown
            html.append(f"                <div class='question-summary'>")
            html.append(f"                    <span class='correct'>✓ {summary.get('questions_correct', 0)} correct</span>")
            html.append(f"                    <span class='incorrect'>✗ {summary.get('questions_incorrect', 0)} incorrect</span>")
            if summary.get('questions_unanswered', 0) > 0:
                html.append(f"                    <span class='unanswered'>○ {summary['questions_unanswered']} unanswered</span>")
            html.append(f"                </div>")

            html.append(f"            </div>")

        html.append("        </section>")
        return "\n".join(html)

    def _generate_html_question_analysis(self, analysis: List[Dict[str, Any]]) -> str:
        """Generate HTML question analysis section (enterprise tier)"""
        html = []
        html.append("        <section class='question-analysis'>")
        html.append("            <h2>Question Analysis</h2>")
        html.append("            <table>")
        html.append("                <thead>")
        html.append("                    <tr>")
        html.append("                        <th>Question</th>")
        html.append("                        <th>% Correct</th>")
        html.append("                        <th>Difficulty</th>")
        html.append("                        <th>Discrimination</th>")
        html.append("                    </tr>")
        html.append("                </thead>")
        html.append("                <tbody>")

        for q in analysis:
            html.append("                    <tr>")
            html.append(f"                        <td>{q['question_id']}</td>")
            html.append(f"                        <td>{q['percent_correct']:.1f}%</td>")
            html.append(f"                        <td>{q['difficulty']}</td>")
            html.append(f"                        <td>{q.get('discrimination_index', 'N/A')}</td>")
            html.append("                    </tr>")

        html.append("                </tbody>")
        html.append("            </table>")
        html.append("        </section>")
        return "\n".join(html)

    def _get_css(self) -> str:
        """Get CSS styles for HTML report"""
        return """    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        header {
            border-bottom: 3px solid #007bff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        h1 {
            margin: 0 0 15px 0;
            color: #007bff;
        }
        .test-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
        }
        .test-info p {
            margin: 5px 0;
        }
        .class-stats {
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 6px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .stat-box {
            background: white;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .stat-label {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }
        .stat-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #007bff;
        }
        .student-card {
            border: 1px solid #ddd;
            padding: 20px;
            margin: 15px 0;
            border-radius: 6px;
            background: #fafafa;
        }
        .student-card h3 {
            margin-top: 0;
            color: #333;
        }
        .score-summary {
            margin: 15px 0;
        }
        .score-main {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .percentage {
            font-size: 2em;
            font-weight: bold;
            color: #28a745;
        }
        .grade {
            font-size: 1.5em;
            font-weight: bold;
            color: #007bff;
            padding: 5px 15px;
            background: white;
            border-radius: 4px;
        }
        .question-summary {
            display: flex;
            gap: 20px;
            margin-top: 10px;
            font-size: 0.95em;
        }
        .correct { color: #28a745; }
        .incorrect { color: #dc3545; }
        .unanswered { color: #ffc107; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #007bff;
            color: white;
        }
        tr:hover {
            background: #f5f5f5;
        }
    </style>"""

    def _validate_tier_support(self, format_type: str, template: str):
        """Validate format and template are supported in current tier"""
        if format_type not in self.config["export_formats"]:
            raise ValueError(
                f"Format '{format_type}' not available in tier '{self.tier}'. "
                f"Available: {self.config['export_formats']}"
            )

        if template not in self.config["report_templates_available"]:
            raise ValueError(
                f"Template '{template}' not available in tier '{self.tier}'. "
                f"Available: {self.config['report_templates_available']}"
            )


def main():
    parser = argparse.ArgumentParser(
        description='Generate test results report',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate HTML report
    report scores.json --format html --output report.html

    # Generate Markdown report
    report scores.json --format markdown --output report.md

    # Use specific tier
    report scores.json --format html --tier pro --output report.html
        """
    )

    parser.add_argument('input', type=str, help='Input scores JSON file')
    parser.add_argument('--format', '-f', type=str, default='html',
                        choices=['html', 'markdown', 'csv', 'pdf'],
                        help='Output format (default: html)')
    parser.add_argument('--template', type=str, default='basic',
                        choices=['basic', 'detailed', 'comprehensive'],
                        help='Report template (default: basic)')
    parser.add_argument('--tier', type=str, default='free',
                        choices=['free', 'pro', 'enterprise'],
                        help='Tier level (default: free)')
    parser.add_argument('--output', '-o', type=str,
                        help='Output file (default: stdout)')

    args = parser.parse_args()

    # Read input file
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            scores = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate report
    try:
        generator = ReportGenerator(tier=args.tier)

        if args.format == 'html':
            output = generator.generate_html(scores, template=args.template)
        elif args.format == 'markdown':
            output = generator.generate_markdown(scores)
        elif args.format == 'csv':
            print("CSV format not yet implemented", file=sys.stderr)
            sys.exit(1)
        elif args.format == 'pdf':
            print("PDF format not yet implemented", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"Error: Unsupported format '{args.format}'", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        sys.exit(1)

    # Output
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Successfully wrote report to {args.output}", file=sys.stderr)
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)


if __name__ == '__main__':
    main()
