#!/usr/bin/env python3
"""
docgen - Generate test documents from questions and configuration

Creates test PDFs (via Typst), template layouts, and question orders.
This is a dependent tool that requires questions.json and config.json.

Usage:
    docgen questions.json config.json --output ./output/

Input: questions.json + config.json
Output: Typst files, template_layout.json, question_order.json
"""

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional


class DocumentGenerator:
    """Generator for test documents and layouts"""

    # Page size definitions (in mm)
    PAGE_SIZES = {
        "A4": (210, 297),
        "Letter": (215.9, 279.4),
        "Legal": (215.9, 355.6)
    }

    def __init__(self):
        self.questions = []
        self.config = {}
        self.version_questions = {}  # version_id -> list of questions
        self.student_assignments = {}  # student_id -> version_id

    def generate(
        self,
        questions_data: Dict[str, Any],
        config_data: Dict[str, Any],
        output_dir: Path
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate all test documents and metadata

        Args:
            questions_data: Parsed questions.json
            config_data: Parsed config.json
            output_dir: Output directory for generated files

        Returns:
            Tuple of (template_layout, question_order)
        """
        self.questions = questions_data["questions"]
        self.config = config_data

        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Distribute questions across versions
        print(f"Distributing {len(self.questions)} questions across {self.config['distribution']['versions']} versions...", file=sys.stderr)
        self._distribute_questions()

        # 2. Assign students to versions
        print(f"Assigning {self.config['distribution']['students']} students to versions...", file=sys.stderr)
        self._assign_students()

        # 3. Generate template layout (same for all versions)
        print("Generating template layout...", file=sys.stderr)
        template_layout = self._generate_template_layout()

        # 4. Generate question order mapping
        print("Generating question order mapping...", file=sys.stderr)
        question_order = self._generate_question_order()

        # 5. Generate Typst source files for each student
        print("Generating Typst documents...", file=sys.stderr)
        self._generate_typst_documents(output_dir)

        # 6. Save metadata files
        with open(output_dir / "template_layout.json", "w") as f:
            json.dump(template_layout, f, indent=2)
        print(f"  Saved template_layout.json", file=sys.stderr)

        with open(output_dir / "question_order.json", "w") as f:
            json.dump(question_order, f, indent=2)
        print(f"  Saved question_order.json", file=sys.stderr)

        return template_layout, question_order

    def _distribute_questions(self):
        """Distribute questions across test versions based on strategy"""
        num_versions = self.config["distribution"]["versions"]
        strategy = self.config["distribution"].get("strategy", "round_robin")
        randomize = self.config["distribution"].get("randomize_questions", False)

        # Create versions
        for v in range(num_versions):
            self.version_questions[f"v{v+1}"] = []

        if strategy == "round_robin":
            # Each version gets questions in order, rotated
            for v in range(num_versions):
                version_id = f"v{v+1}"
                # Rotate questions for this version
                rotated = self.questions[v:] + self.questions[:v]
                self.version_questions[version_id] = rotated[:]

        elif strategy == "random":
            # Each version gets randomly shuffled questions
            for version_id in self.version_questions:
                shuffled = self.questions[:]
                random.shuffle(shuffled)
                self.version_questions[version_id] = shuffled

        elif strategy in ["difficulty_balanced", "adaptive"]:
            # For now, same as round_robin (proper implementation would need difficulty tags)
            for v in range(num_versions):
                version_id = f"v{v+1}"
                rotated = self.questions[v:] + self.questions[:v]
                self.version_questions[version_id] = rotated[:]

        # Apply additional randomization if requested
        if randomize:
            for version_id in self.version_questions:
                random.shuffle(self.version_questions[version_id])

        # Randomize options within questions if requested
        if self.config["distribution"].get("randomize_options", False):
            for version_id in self.version_questions:
                for question in self.version_questions[version_id]:
                    if "options" in question and question.get("type") == "multiple_choice":
                        self._randomize_question_options(question)

    def _randomize_question_options(self, question: Dict[str, Any]):
        """Randomize answer options for a multiple choice question"""
        if "options" not in question:
            return

        # Get correct answer
        correct_answer = question["correct_answer"]

        # Find the correct option text
        correct_text = None
        for opt in question["options"]:
            if opt["label"] == correct_answer:
                correct_text = opt["text"]
                break

        # Shuffle options
        options = question["options"][:]
        random.shuffle(options)

        # Re-label and update correct answer
        for i, opt in enumerate(options):
            new_label = chr(65 + i)  # A, B, C, ...
            opt["label"] = new_label
            if opt["text"] == correct_text:
                question["correct_answer"] = new_label

        question["options"] = options

    def _assign_students(self):
        """Assign students to test versions"""
        num_students = self.config["distribution"]["students"]
        versions = list(self.version_questions.keys())

        # Get student list or generate placeholders
        if "students_list" in self.config:
            students = self.config["students_list"][:num_students]
        else:
            students = [{"id": f"s{i+1:03d}", "name": f"Student {i+1}"} for i in range(num_students)]

        # Round-robin assignment
        for i, student in enumerate(students):
            version_id = versions[i % len(versions)]
            self.student_assignments[student["id"]] = version_id

    def _generate_template_layout(self) -> Dict[str, Any]:
        """Generate template layout JSON"""
        page_size_name = self.config["scanning"].get("page_size", "A4")
        width_mm, height_mm = self.PAGE_SIZES[page_size_name]
        dpi = self.config["scanning"].get("dpi", 300)

        layout = {
            "version": "1.0.0",
            "page_info": {
                "width_mm": width_mm,
                "height_mm": height_mm,
                "dpi": dpi,
                "page_size": page_size_name,
                "orientation": "portrait"
            },
            "registration_marks": [
                {"id": "top_left", "x_mm": 10, "y_mm": 10, "type": "circle", "size_mm": 5, "fill": True},
                {"id": "top_right", "x_mm": width_mm - 10, "y_mm": 10, "type": "circle", "size_mm": 5, "fill": True},
                {"id": "bottom_left", "x_mm": 10, "y_mm": height_mm - 10, "type": "circle", "size_mm": 5, "fill": True},
                {"id": "bottom_right", "x_mm": width_mm - 10, "y_mm": height_mm - 10, "type": "circle", "size_mm": 5, "fill": True}
            ],
            "id_fields": {
                "version_id": {
                    "x_mm": 20,
                    "y_mm": 20,
                    "width_mm": 40,
                    "height_mm": 10,
                    "type": "barcode"
                },
                "student_id": {
                    "x_mm": width_mm - 60,
                    "y_mm": 20,
                    "width_mm": 40,
                    "height_mm": 10,
                    "type": "barcode"
                }
            },
            "questions": []
        }

        # Add question layout info (using first version as template)
        first_version = list(self.version_questions.values())[0]
        y_position = 80  # Start position for questions

        for i, question in enumerate(first_version):
            q_layout = {
                "question_id": question["id"],
                "type": question["type"],
                "page": 1,
                "answer_region": {
                    "x_mm": 25,
                    "y_mm": y_position,
                    "width_mm": 160,
                    "height_mm": 20
                }
            }

            # Add answer fields for MC/TF questions
            if question["type"] in ["multiple_choice", "true_false"]:
                q_layout["answer_fields"] = []
                num_options = len(question.get("options", []))

                for j in range(num_options):
                    field = {
                        "label": chr(65 + j),  # A, B, C, ...
                        "x_mm": 30 + (j * 20),
                        "y_mm": y_position + 10,
                        "field_type": self.config["scanning"].get("answer_field_type", "circle"),
                        "radius_mm": 3
                    }
                    q_layout["answer_fields"].append(field)

            # Add OCR region for short answer/essay
            elif question["type"] in ["short_answer", "essay"]:
                q_layout["ocr_region"] = {
                    "x_mm": 25,
                    "y_mm": y_position,
                    "width_mm": 160,
                    "height_mm": 15 if question["type"] == "short_answer" else 40,
                    "expected_lines": 1 if question["type"] == "short_answer" else 5
                }

            layout["questions"].append(q_layout)
            y_position += 25  # Space between questions

        # Add fill detection parameters
        layout["fill_detection"] = {
            "threshold": 0.6,
            "noise_tolerance": "standard",
            "edge_detection": True
        }

        return layout

    def _generate_question_order(self) -> Dict[str, Any]:
        """Generate question order mapping"""
        order = {
            "version": "1.0.0",
            "test_info": self.config.get("test_info", {}),
            "versions": {}
        }

        # For each version, store question order and answers
        for version_id, questions in self.version_questions.items():
            order["versions"][version_id] = {
                "version_id": version_id,
                "questions": []
            }

            for i, question in enumerate(questions):
                q_info = {
                    "question_number": i + 1,
                    "question_id": question["id"],
                    "question_type": question["type"],
                    "question_text": question["text"],
                    "correct_answer": question["correct_answer"],
                    "points": question.get("points", 1)
                }

                # Include options for MC questions
                if "options" in question:
                    q_info["options"] = question["options"]

                order["versions"][version_id]["questions"].append(q_info)

        # Add student assignments
        order["student_assignments"] = self.student_assignments

        return order

    def _generate_typst_documents(self, output_dir: Path):
        """Generate Typst source files for each student"""
        typst_dir = output_dir / "typst"
        typst_dir.mkdir(exist_ok=True)

        # Get student list
        if "students_list" in self.config:
            students = self.config["students_list"][:self.config["distribution"]["students"]]
        else:
            num_students = self.config["distribution"]["students"]
            students = [{"id": f"s{i+1:03d}", "name": f"Student {i+1}"} for i in range(num_students)]

        for student in students:
            student_id = student["id"]
            student_name = student.get("name", student_id)
            version_id = self.student_assignments[student_id]

            # Generate Typst document
            typst_content = self._generate_typst_content(student_id, student_name, version_id)

            # Save to file
            filename = f"{student_id}_{version_id}.typ"
            with open(typst_dir / filename, "w") as f:
                f.write(typst_content)

        print(f"  Generated {len(students)} Typst files in {typst_dir}/", file=sys.stderr)

    def _generate_typst_content(self, student_id: str, student_name: str, version_id: str) -> str:
        """Generate Typst markup for a test document"""
        questions = self.version_questions[version_id]
        test_info = self.config.get("test_info", {})

        typst = []

        # Document setup
        typst.append("#set page(paper: \"a4\", margin: (x: 2cm, y: 2cm))")
        typst.append("#set text(font: \"Liberation Sans\", size: 11pt)")
        typst.append("#set par(justify: true)")
        typst.append("")

        # Header with registration marks
        typst.append("// Registration marks (corners)")
        typst.append("#place(top + left, dx: 10mm, dy: 10mm, circle(radius: 2.5mm, fill: black))")
        typst.append("#place(top + right, dx: -10mm, dy: 10mm, circle(radius: 2.5mm, fill: black))")
        typst.append("#place(bottom + left, dx: 10mm, dy: -10mm, circle(radius: 2.5mm, fill: black))")
        typst.append("#place(bottom + right, dx: -10mm, dy: -10mm, circle(radius: 2.5mm, fill: black))")
        typst.append("")

        # Title and student info
        typst.append(f"#align(center)[")
        typst.append(f"  #text(size: 16pt, weight: \"bold\")[{test_info.get('title', 'Test')}]")
        if "subtitle" in test_info:
            typst.append(f"  \\\\ #text(size: 12pt)[{test_info['subtitle']}]")
        typst.append(f"]")
        typst.append("")

        typst.append(f"#grid(")
        typst.append(f"  columns: (1fr, 1fr),")
        typst.append(f"  gutter: 10mm,")
        typst.append(f"  [*Student:* {student_name}],")
        typst.append(f"  [*ID:* `{student_id}`],")
        typst.append(f")")
        typst.append("")
        typst.append(f"#grid(")
        typst.append(f"  columns: (1fr, 1fr),")
        typst.append(f"  gutter: 10mm,")
        typst.append(f"  [*Version:* `{version_id}`],")
        typst.append(f"  [*Date:* {test_info.get('date', 'N/A')}],")
        typst.append(f")")
        typst.append("")

        if "instructions" in test_info:
            typst.append(f"#block(fill: luma(240), inset: 8pt, radius: 4pt)[")
            typst.append(f"  *Instructions:* {test_info['instructions']}")
            typst.append(f"]")
            typst.append("")

        typst.append("#v(1em)")
        typst.append("")

        # Questions
        for i, question in enumerate(questions):
            q_num = i + 1
            points = question.get("points", 1)

            typst.append(f"// Question {q_num}")
            typst.append(f"#block()[")
            typst.append(f"  *{q_num}.* {question['text']} _({points} point{'s' if points != 1 else ''})_")
            typst.append("")

            # Multiple choice/True-False options
            if question["type"] in ["multiple_choice", "true_false"] and "options" in question:
                typst.append(f"  #v(0.5em)")
                for option in question["options"]:
                    # Add bubble for scanning
                    typst.append(f"  #grid(")
                    typst.append(f"    columns: (8mm, 1fr),")
                    typst.append(f"    circle(radius: 3mm, stroke: 0.5pt) #text(weight: \"bold\")[{option['label']}],")
                    typst.append(f"    [{option['text']}]")
                    typst.append(f"  )")

            # Short answer
            elif question["type"] == "short_answer":
                typst.append(f"  #v(0.5em)")
                typst.append(f"  #box(width: 100%, height: 15mm, stroke: 0.5pt)[")
                typst.append(f"    #v(0.5em)")
                typst.append(f"  ]")

            # Essay
            elif question["type"] == "essay":
                typst.append(f"  #v(0.5em)")
                typst.append(f"  #box(width: 100%, height: 40mm, stroke: 0.5pt)[")
                typst.append(f"    #v(0.5em)")
                typst.append(f"  ]")

            typst.append(f"]")
            typst.append("")
            typst.append(f"#v(0.8em)")
            typst.append("")

        return "\n".join(typst)


def main():
    parser = argparse.ArgumentParser(
        description='Generate test documents from questions and configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate test documents
    docgen questions.json config.json --output ./output/

    # Specify output directory
    docgen questions.json config.json -o ./tests/midterm/
        """
    )

    parser.add_argument('questions', type=str, help='Input questions JSON file')
    parser.add_argument('config', type=str, help='Input config JSON file')
    parser.add_argument('--output', '-o', type=str, required=True,
                        help='Output directory for generated files')
    parser.add_argument('--seed', type=int, help='Random seed for reproducibility')

    args = parser.parse_args()

    # Set random seed if provided
    if args.seed:
        random.seed(args.seed)

    # Load questions
    try:
        with open(args.questions, 'r') as f:
            questions_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Questions file '{args.questions}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing questions JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Load config
    try:
        with open(args.config, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file '{args.config}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing config JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate documents
    try:
        generator = DocumentGenerator()
        output_path = Path(args.output)

        template_layout, question_order = generator.generate(
            questions_data,
            config_data,
            output_path
        )

        print(f"\nSuccess! Generated test documents in {output_path}/", file=sys.stderr)
        print(f"  - {len(question_order['student_assignments'])} Typst source files", file=sys.stderr)
        print(f"  - template_layout.json", file=sys.stderr)
        print(f"  - question_order.json", file=sys.stderr)
        print(f"\nTo compile PDFs, run: typst compile <file>.typ", file=sys.stderr)

    except Exception as e:
        print(f"Error generating documents: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
