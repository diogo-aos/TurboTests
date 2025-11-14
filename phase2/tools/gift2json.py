#!/usr/bin/env python3
"""
gift2json - Convert GIFT format questions to JSON

GIFT (General Import Format Template) is a text-based format for quiz questions.
This tool parses GIFT files and outputs structured JSON matching the questions schema.

Usage:
    gift2json input.gift [--output output.json] [--tier free|pro|enterprise]

Input: GIFT format file
Output: questions.json matching schema
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class GIFTParser:
    """Parser for GIFT format questions"""

    # Tier configurations
    TIER_CONFIGS = {
        "free": {
            "question_types_supported": ["multiple_choice", "true_false"],
            "allow_question_metadata": False,
            "allow_custom_attributes": False,
            "allow_difficulty_tagging": False,
            "allow_standards_mapping": False,
            "max_questions": None
        },
        "pro": {
            "question_types_supported": ["multiple_choice", "short_answer", "true_false"],
            "allow_question_metadata": True,
            "allow_custom_attributes": False,
            "allow_difficulty_tagging": True,
            "allow_standards_mapping": False,
            "max_questions": None
        },
        "enterprise": {
            "question_types_supported": ["multiple_choice", "short_answer", "essay", "matching", "true_false"],
            "allow_question_metadata": True,
            "allow_custom_attributes": True,
            "allow_difficulty_tagging": True,
            "allow_standards_mapping": True,
            "max_questions": None
        }
    }

    def __init__(self, tier: str = "free"):
        """Initialize parser with tier configuration"""
        if tier not in self.TIER_CONFIGS:
            raise ValueError(f"Invalid tier: {tier}. Must be one of: {list(self.TIER_CONFIGS.keys())}")
        self.tier = tier
        self.config = self.TIER_CONFIGS[tier]
        self.question_counter = 0

    def parse(self, gift_content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Parse GIFT format content and return structured questions

        Args:
            gift_content: GIFT format text
            metadata: Optional metadata for the question set

        Returns:
            Dictionary matching questions schema
        """
        questions = []

        # Split into individual questions (separated by blank lines)
        raw_questions = self._split_questions(gift_content)

        for raw_q in raw_questions:
            if not raw_q.strip():
                continue

            try:
                question = self._parse_question(raw_q)
                if question:
                    questions.append(question)
            except Exception as e:
                print(f"Warning: Failed to parse question: {e}", file=sys.stderr)
                print(f"Content: {raw_q[:100]}...", file=sys.stderr)
                continue

        # Enforce tier limits
        if self.config["max_questions"] and len(questions) > self.config["max_questions"]:
            raise ValueError(f"Tier '{self.tier}' allows maximum {self.config['max_questions']} questions")

        result = {
            "version": "1.0.0",
            "questions": questions
        }

        if metadata:
            result["metadata"] = metadata

        return result

    def _split_questions(self, content: str) -> List[str]:
        """Split GIFT content into individual questions"""
        # Remove comments (lines starting with //)
        lines = []
        for line in content.split('\n'):
            if not line.strip().startswith('//'):
                lines.append(line)

        content = '\n'.join(lines)

        # Split by double newlines
        questions = re.split(r'\n\s*\n', content)
        return [q.strip() for q in questions if q.strip()]

    def _parse_question(self, raw_question: str) -> Optional[Dict[str, Any]]:
        """Parse a single GIFT question"""
        # Extract question metadata (if in format ::title::)
        title_match = re.match(r'::(.*?)::', raw_question)
        question_id = None
        if title_match:
            question_id = self._sanitize_id(title_match.group(1))
            raw_question = raw_question[title_match.end():].strip()

        # Auto-generate ID if not provided
        if not question_id:
            self.question_counter += 1
            question_id = f"q{self.question_counter}"

        # Extract question text and answer block
        # Answer block is in {}
        match = re.match(r'(.*?)\s*\{(.*?)\}\s*$', raw_question, re.DOTALL)
        if not match:
            # Try to handle questions without explicit answer block
            return None

        question_text = match.group(1).strip()
        answer_block = match.group(2).strip()

        # Parse based on answer block format
        question = self._parse_answer_block(question_id, question_text, answer_block)

        return question

    def _parse_answer_block(self, question_id: str, question_text: str, answer_block: str) -> Optional[Dict[str, Any]]:
        """Parse the answer block to determine question type and extract answers"""

        # True/False question (T or F or TRUE or FALSE)
        if answer_block.upper() in ['T', 'TRUE', 'F', 'FALSE']:
            return self._parse_true_false(question_id, question_text, answer_block)

        # Count the number of answer markers
        has_tilde = '~' in answer_block
        has_equals = '=' in answer_block
        num_markers = answer_block.count('~') + answer_block.count('=')

        # Multiple choice: has multiple options (with ~ and/or multiple =)
        # OR has at least one ~ (indicating wrong answers)
        if has_tilde or num_markers > 1:
            return self._parse_multiple_choice(question_id, question_text, answer_block)

        # Short answer: single = or no marker
        if has_equals or not has_tilde:
            return self._parse_short_answer(question_id, question_text, answer_block)

        # Default to short answer
        return self._parse_short_answer(question_id, question_text, answer_block)

    def _parse_true_false(self, question_id: str, question_text: str, answer: str) -> Dict[str, Any]:
        """Parse true/false question"""
        self._check_tier_support("true_false")

        is_true = answer.upper() in ['T', 'TRUE']

        return {
            "id": question_id,
            "type": "true_false",
            "text": question_text,
            "points": 1,
            "options": [
                {"label": "A", "text": "True"},
                {"label": "B", "text": "False"}
            ],
            "correct_answer": "A" if is_true else "B"
        }

    def _parse_multiple_choice(self, question_id: str, question_text: str, answer_block: str) -> Dict[str, Any]:
        """Parse multiple choice question"""
        self._check_tier_support("multiple_choice")

        options = []
        correct_answer = None
        label_counter = 0

        # Split by ~ or = while keeping the delimiter
        parts = re.split(r'([~=])', answer_block)

        i = 0
        while i < len(parts):
            if parts[i] in ['~', '=']:
                if i + 1 < len(parts):
                    option_text = parts[i + 1].strip()
                    if option_text:
                        label = chr(65 + label_counter)  # A, B, C, ...
                        options.append({
                            "label": label,
                            "text": option_text
                        })

                        if parts[i] == '=':
                            correct_answer = label

                        label_counter += 1
                i += 2
            else:
                i += 1

        if not correct_answer:
            raise ValueError(f"No correct answer found for question {question_id}")

        return {
            "id": question_id,
            "type": "multiple_choice",
            "text": question_text,
            "points": 1,
            "options": options,
            "correct_answer": correct_answer
        }

    def _parse_short_answer(self, question_id: str, question_text: str, answer: str) -> Dict[str, Any]:
        """Parse short answer question"""
        self._check_tier_support("short_answer")

        # Handle = prefix for correct answer
        answer = answer.lstrip('=').strip()

        return {
            "id": question_id,
            "type": "short_answer",
            "text": question_text,
            "points": 1,
            "correct_answer": answer
        }

    def _check_tier_support(self, question_type: str):
        """Check if question type is supported in current tier"""
        if question_type not in self.config["question_types_supported"]:
            raise ValueError(
                f"Question type '{question_type}' not supported in tier '{self.tier}'. "
                f"Supported types: {self.config['question_types_supported']}"
            )

    def _sanitize_id(self, title: str) -> str:
        """Convert title to valid ID format"""
        # Replace spaces and special chars with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', title)
        # Remove consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        return sanitized if sanitized else f"q{self.question_counter + 1}"


def validate_json_schema(data: Dict[str, Any], schema_path: Optional[Path] = None) -> bool:
    """
    Validate output against JSON schema (if jsonschema is available)

    Args:
        data: Data to validate
        schema_path: Path to schema file

    Returns:
        True if valid or validation not available
    """
    try:
        import jsonschema

        if schema_path and schema_path.exists():
            with open(schema_path) as f:
                schema = json.load(f)
            jsonschema.validate(data, schema)
            return True
        else:
            print("Warning: Schema file not found, skipping validation", file=sys.stderr)
            return True
    except ImportError:
        print("Warning: jsonschema not installed, skipping validation", file=sys.stderr)
        return True
    except jsonschema.ValidationError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Convert GIFT format questions to JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Convert GIFT to JSON
    gift2json questions.gift --output questions.json

    # Use specific tier
    gift2json questions.gift --tier pro --output questions.json

    # Pipe to stdout
    gift2json questions.gift

    # Add metadata
    gift2json questions.gift --title "Midterm Exam" --author "Dr. Smith"
        """
    )

    parser.add_argument('input', type=str, help='Input GIFT file')
    parser.add_argument('--output', '-o', type=str, help='Output JSON file (default: stdout)')
    parser.add_argument('--tier', type=str, default='free',
                        choices=['free', 'pro', 'enterprise'],
                        help='Tier level (default: free)')
    parser.add_argument('--title', type=str, help='Question set title')
    parser.add_argument('--author', type=str, help='Question set author')
    parser.add_argument('--subject', type=str, help='Subject area')
    parser.add_argument('--validate', action='store_true',
                        help='Validate output against schema')

    args = parser.parse_args()

    # Read input file
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            gift_content = f.read()
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)

    # Build metadata if provided
    metadata = {}
    if args.title:
        metadata['title'] = args.title
    if args.author:
        metadata['author'] = args.author
    if args.subject:
        metadata['subject'] = args.subject
    if metadata:
        metadata['created_at'] = datetime.utcnow().isoformat() + 'Z'

    # Parse GIFT
    try:
        gift_parser = GIFTParser(tier=args.tier)
        result = gift_parser.parse(gift_content, metadata if metadata else None)
    except Exception as e:
        print(f"Error parsing GIFT: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate if requested
    if args.validate:
        # Try to find schema file
        schema_path = Path(__file__).parent.parent.parent / 'phase1' / 'schemas' / 'questions_schema.json'
        if not validate_json_schema(result, schema_path):
            print("Error: Output does not match schema", file=sys.stderr)
            sys.exit(1)

    # Output
    json_output = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"Successfully wrote {len(result['questions'])} questions to {args.output}", file=sys.stderr)
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(json_output)


if __name__ == '__main__':
    main()
