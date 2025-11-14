#!/usr/bin/env python3
"""
testscan - Extract answers from scanned test images

Processes scanned test images and extracts answers based on template layout.
Implements actual computer vision algorithms using pure Python (no external dependencies).

Usage:
    testscan scan.json --layout template_layout.json --output scan_result.json
    testscan --synthetic student_id version_id --layout template_layout.json --question-order question_order.json

Input: Image file (JSON/PGM) + template_layout.json
Output: scan_result.json with extracted answers
"""

import argparse
import json
import math
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


class ImageScanner:
    """Scanner for extracting answers from test images using pure Python CV"""

    def __init__(self, tier: str = "free"):
        """Initialize scanner with tier configuration"""
        self.tier = tier
        self.version = "testscan-1.0.0"

    def load_image(self, image_path: str) -> List[List[int]]:
        """
        Load image from JSON or PGM format

        Args:
            image_path: Path to image file (.json or .pgm)

        Returns:
            2D array of pixel values (0=black, 255=white)
        """
        path = Path(image_path)

        if path.suffix == '.json':
            # Load sparse JSON format
            with open(path) as f:
                data = json.load(f)

            width = data["width"]
            height = data["height"]

            # Create white image
            image = [[255 for _ in range(width)] for _ in range(height)]

            # Fill in non-white pixels
            for pixel in data["pixels"]:
                x, y, value = pixel
                image[y][x] = value

            return image

        elif path.suffix == '.pgm':
            # Load PGM format
            with open(path) as f:
                lines = f.readlines()

            # Parse header
            if lines[0].strip() != 'P2':
                raise ValueError("Only P2 PGM format supported")

            # Skip comments
            i = 1
            while lines[i].startswith('#'):
                i += 1

            # Parse dimensions
            width, height = map(int, lines[i].split())
            i += 1

            # Parse max value
            max_val = int(lines[i].strip())
            i += 1

            # Parse pixel data
            image = []
            for line in lines[i:]:
                row = list(map(int, line.split()))
                image.append(row)

            return image

        else:
            raise ValueError(f"Unsupported image format: {path.suffix}")

    def detect_registration_marks(
        self,
        image: List[List[int]],
        expected_marks: List[Dict[str, Any]],
        dpi: int = 300
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Detect registration marks in image

        Args:
            image: 2D pixel array
            expected_marks: Expected mark positions from layout
            dpi: Image DPI

        Returns:
            Tuple of (detected_marks, success)
        """
        height = len(image)
        width = len(image[0]) if height > 0 else 0

        detected_marks = []

        for mark in expected_marks:
            expected_x = self._mm_to_pixels(mark["x_mm"], dpi)
            expected_y = self._mm_to_pixels(mark["y_mm"], dpi)
            expected_radius = self._mm_to_pixels(mark["size_mm"], dpi)

            # Search in area around expected position
            search_radius = 20  # pixels

            found = False
            best_match = None
            best_score = 0

            for dy in range(-search_radius, search_radius + 1, 5):
                for dx in range(-search_radius, search_radius + 1, 5):
                    test_x = expected_x + dx
                    test_y = expected_y + dy

                    # Check if this looks like a dark circle
                    score = self._is_dark_circle(image, test_x, test_y, expected_radius)

                    if score > best_score:
                        best_score = score
                        best_match = {"x": test_x, "y": test_y, "score": score}

            # Consider mark detected if score > 0.7
            if best_match and best_match["score"] > 0.7:
                detected_marks.append({
                    "expected_x": expected_x,
                    "expected_y": expected_y,
                    "detected_x": best_match["x"],
                    "detected_y": best_match["y"],
                    "confidence": best_match["score"]
                })
                found = True
            else:
                detected_marks.append({
                    "expected_x": expected_x,
                    "expected_y": expected_y,
                    "detected_x": None,
                    "detected_y": None,
                    "confidence": 0.0
                })

        # Success if at least 3 of 4 marks detected
        success = sum(1 for m in detected_marks if m["detected_x"] is not None) >= 3

        return detected_marks, success

    def _is_dark_circle(
        self,
        image: List[List[int]],
        cx: int,
        cy: int,
        radius: int
    ) -> float:
        """
        Check if there's a dark circle at given position

        Args:
            image: 2D pixel array
            cx, cy: Circle center
            radius: Circle radius

        Returns:
            Score 0-1 indicating how well it matches a dark circle
        """
        height = len(image)
        width = len(image[0]) if height > 0 else 0

        if cx < radius or cy < radius or cx >= width - radius or cy >= height - radius:
            return 0.0

        # Count dark pixels in circle
        dark_count = 0
        total_count = 0

        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx*dx + dy*dy <= radius*radius:
                    x = cx + dx
                    y = cy + dy

                    if 0 <= x < width and 0 <= y < height:
                        total_count += 1
                        if image[y][x] < 128:  # Dark threshold
                            dark_count += 1

        if total_count == 0:
            return 0.0

        # Should be mostly dark
        dark_ratio = dark_count / total_count

        # Also check that surrounding area is white (not part of larger shape)
        outer_radius = int(radius * 1.5)
        white_count = 0
        outer_count = 0

        for dy in range(-outer_radius, outer_radius + 1):
            for dx in range(-outer_radius, outer_radius + 1):
                dist_sq = dx*dx + dy*dy
                if radius*radius < dist_sq <= outer_radius*outer_radius:
                    x = cx + dx
                    y = cy + dy

                    if 0 <= x < width and 0 <= y < height:
                        outer_count += 1
                        if image[y][x] > 200:  # White threshold
                            white_count += 1

        white_ratio = white_count / outer_count if outer_count > 0 else 0

        # Good registration mark: dark center, white surround
        score = dark_ratio * 0.7 + white_ratio * 0.3

        return score

    def detect_bubble_fill(
        self,
        image: List[List[int]],
        cx: int,
        cy: int,
        radius: int,
        threshold: float = 0.3
    ) -> Tuple[bool, float]:
        """
        Detect if a bubble is filled

        Args:
            image: 2D pixel array
            cx, cy: Bubble center
            radius: Bubble radius
            threshold: Fill threshold (0-1)

        Returns:
            Tuple of (is_filled, confidence)
        """
        height = len(image)
        width = len(image[0]) if height > 0 else 0

        if cx < 0 or cy < 0 or cx >= width or cy >= height:
            return False, 0.0

        # Count dark pixels in bubble interior
        dark_count = 0
        total_count = 0

        # Check slightly smaller radius to avoid edge
        check_radius = max(1, radius - 2)

        for dy in range(-check_radius, check_radius + 1):
            for dx in range(-check_radius, check_radius + 1):
                if dx*dx + dy*dy <= check_radius*check_radius:
                    x = cx + dx
                    y = cy + dy

                    if 0 <= x < width and 0 <= y < height:
                        total_count += 1
                        if image[y][x] < 128:  # Dark threshold
                            dark_count += 1

        if total_count == 0:
            return False, 0.0

        fill_ratio = dark_count / total_count

        # Bubble is filled if fill ratio exceeds threshold
        is_filled = fill_ratio >= threshold

        # Confidence based on how clear the fill is
        if is_filled:
            # High fill ratio = high confidence
            confidence = min(0.99, fill_ratio / threshold)
        else:
            # Low fill ratio = high confidence it's NOT filled
            confidence = min(0.99, 1.0 - (fill_ratio / threshold))

        return is_filled, confidence

    def extract_answers(
        self,
        image: List[List[int]],
        template_layout: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Extract answers from image

        Args:
            image: 2D pixel array
            template_layout: Template layout data

        Returns:
            Tuple of (answers, metadata)
        """
        dpi = template_layout["page_info"]["dpi"]

        # Detect registration marks
        registration_marks = template_layout.get("registration_marks", [])
        detected_marks, rect_success = self.detect_registration_marks(
            image, registration_marks, dpi
        )

        # Extract answers
        answers = []

        for q_layout in template_layout["questions"]:
            q_id = q_layout["question_id"]
            q_type = q_layout["type"]
            q_num = q_layout.get("question_number", 0)

            if q_type in ["multiple_choice", "true_false"] and "answer_fields" in q_layout:
                # Bubble detection
                extracted_answer = None
                max_confidence = 0.0
                filled_bubbles = []

                for field in q_layout["answer_fields"]:
                    fx = self._mm_to_pixels(field["x_mm"], dpi)
                    fy = self._mm_to_pixels(field["y_mm"], dpi)
                    radius = self._mm_to_pixels(field.get("radius_mm", 3), dpi)

                    is_filled, confidence = self.detect_bubble_fill(
                        image, fx, fy, radius
                    )

                    if is_filled:
                        filled_bubbles.append({
                            "label": field["label"],
                            "confidence": confidence
                        })

                        if confidence > max_confidence:
                            extracted_answer = field["label"]
                            max_confidence = confidence

                # Check for multiple fills (ambiguous answer)
                flags = []
                if len(filled_bubbles) > 1:
                    flags.append("multiple_bubbles_filled")
                    max_confidence *= 0.5  # Reduce confidence
                elif len(filled_bubbles) == 0:
                    flags.append("no_bubble_filled")
                    max_confidence = 0.0

                answer = {
                    "question_id": q_id,
                    "question_number": q_num,
                    "question_type": q_type,
                    "extracted_answer": extracted_answer,
                    "confidence": round(max_confidence, 3),
                    "extraction_method": "bubble_detection"
                }

                if flags:
                    answer["flags"] = flags

                answers.append(answer)

            elif q_type in ["short_answer", "essay"] and "ocr_region" in q_layout:
                # OCR simulation
                ocr = q_layout["ocr_region"]
                ox = self._mm_to_pixels(ocr["x_mm"], dpi)
                oy = self._mm_to_pixels(ocr["y_mm"], dpi)
                ow = self._mm_to_pixels(ocr["width_mm"], dpi)
                oh = self._mm_to_pixels(ocr["height_mm"], dpi)

                # Check if there's any writing (dark pixels in region)
                dark_count = 0
                total_count = 0

                for y in range(oy, min(oy + oh, len(image))):
                    for x in range(ox, min(ox + ow, len(image[0]) if len(image) > 0 else 0)):
                        if 0 <= y < len(image) and 0 <= x < len(image[0]):
                            total_count += 1
                            if image[y][x] < 200:  # Consider anything not bright white
                                dark_count += 1

                density = dark_count / total_count if total_count > 0 else 0

                # Simulate OCR result
                if density > 0.05:  # Some writing detected
                    extracted_answer = "[OCR text detected]"
                    confidence = min(0.85, density * 5)  # Higher density = more confident
                else:
                    extracted_answer = ""
                    confidence = 0.90  # High confidence that it's blank

                answer = {
                    "question_id": q_id,
                    "question_number": q_num,
                    "question_type": q_type,
                    "extracted_answer": extracted_answer,
                    "confidence": round(confidence, 3),
                    "extraction_method": "ocr_simulation",
                    "flags": ["requires_manual_review"] if density > 0.05 else []
                }

                answers.append(answer)

        # Build metadata
        metadata = {
            "rectification": {
                "markers_detected": sum(1 for m in detected_marks if m["detected_x"] is not None),
                "markers_expected": len(registration_marks),
                "rectification_applied": rect_success
            },
            "quality_metrics": {
                "overall_confidence": round(sum(a["confidence"] for a in answers) / len(answers), 3) if answers else 0.0,
                "low_confidence_count": sum(1 for a in answers if a["confidence"] < 0.7),
                "flags_count": sum(len(a.get("flags", [])) for a in answers)
            }
        }

        return answers, metadata

    def scan_image(
        self,
        image_path: str,
        template_layout: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Scan image file using computer vision

        Args:
            image_path: Path to image file
            template_layout: Template layout data

        Returns:
            Scan result dictionary
        """
        start_time = time.time()

        # Load image
        try:
            image = self.load_image(image_path)
        except Exception as e:
            print(f"Error loading image: {e}", file=sys.stderr)
            raise

        # Extract answers
        answers, metadata = self.extract_answers(image, template_layout)

        processing_time = (time.time() - start_time) * 1000

        # Build scan result
        result = {
            "version": "1.0.0",
            "scan_metadata": {
                "scan_timestamp": datetime.utcnow().isoformat() + 'Z',
                "image_source": image_path,
                "scanner_version": self.version,
                "processing_time_ms": round(processing_time, 2)
            },
            "identification": {
                "version_id": "detected",  # Would extract from ID fields in full implementation
                "student_id": "detected",
                "confidence": {
                    "version_id": 0.0,
                    "student_id": 0.0
                }
            },
            "rectification": metadata["rectification"],
            "answers": answers,
            "quality_metrics": metadata["quality_metrics"]
        }

        return result

    def scan_synthetic(
        self,
        student_id: str,
        version_id: str,
        template_layout: Dict[str, Any],
        question_order: Dict[str, Any],
        accuracy: float = 0.95
    ) -> Dict[str, Any]:
        """
        Generate synthetic scan results (for testing/demo - backward compatibility)

        Args:
            student_id: Student identifier
            version_id: Test version
            template_layout: Template layout data
            question_order: Question order data with correct answers
            accuracy: Simulated scanning accuracy (0-1)

        Returns:
            Scan result dictionary
        """
        start_time = time.time()

        # Get questions for this version
        version_data = question_order["versions"].get(version_id, {})
        questions = version_data.get("questions", [])

        # Simulate answer extraction
        answers = []
        for i, layout_q in enumerate(template_layout["questions"]):
            q_id = layout_q["question_id"]
            q_type = layout_q["type"]

            # Find corresponding question in question_order
            question_data = None
            for q in questions:
                if q["question_id"] == q_id:
                    question_data = q
                    break

            if not question_data:
                continue

            # Simulate answer extraction based on accuracy
            correct_answer = question_data.get("correct_answer")

            # Randomly decide if answer is correct (based on accuracy)
            is_correct = random.random() < accuracy

            if q_type in ["multiple_choice", "true_false"]:
                if is_correct:
                    extracted_answer = correct_answer
                    confidence = random.uniform(0.85, 0.99)
                else:
                    # Wrong answer - pick random different option
                    options = question_data.get("options", [])
                    wrong_options = [opt["label"] for opt in options if opt["label"] != correct_answer]
                    if wrong_options:
                        extracted_answer = random.choice(wrong_options)
                    else:
                        extracted_answer = correct_answer
                    confidence = random.uniform(0.70, 0.95)

                answer = {
                    "question_id": q_id,
                    "question_number": question_data.get("question_number", i + 1),
                    "question_type": q_type,
                    "extracted_answer": extracted_answer,
                    "confidence": round(confidence, 3),
                    "extraction_method": "bubble_detection"
                }

            elif q_type == "short_answer":
                if is_correct:
                    extracted_answer = correct_answer
                    confidence = random.uniform(0.75, 0.95)
                else:
                    # Simulate OCR errors
                    extracted_answer = self._simulate_ocr_error(correct_answer)
                    confidence = random.uniform(0.60, 0.85)

                answer = {
                    "question_id": q_id,
                    "question_number": question_data.get("question_number", i + 1),
                    "question_type": q_type,
                    "extracted_answer": extracted_answer,
                    "confidence": round(confidence, 3),
                    "extraction_method": "ocr"
                }

            else:  # essay or other
                answer = {
                    "question_id": q_id,
                    "question_number": question_data.get("question_number", i + 1),
                    "question_type": q_type,
                    "extracted_answer": "[OCR text would be here]",
                    "confidence": 0.0,
                    "extraction_method": "ocr",
                    "flags": ["manual_review_required"]
                }

            answers.append(answer)

        processing_time = (time.time() - start_time) * 1000

        # Build scan result
        result = {
            "version": "1.0.0",
            "scan_metadata": {
                "scan_timestamp": datetime.utcnow().isoformat() + 'Z',
                "image_source": f"synthetic_{student_id}_{version_id}",
                "scanner_version": self.version,
                "processing_time_ms": round(processing_time, 2)
            },
            "identification": {
                "version_id": version_id,
                "student_id": student_id,
                "confidence": {
                    "version_id": 0.99,
                    "student_id": 0.98
                }
            },
            "rectification": {
                "markers_detected": 4,
                "markers_expected": 4,
                "rectification_applied": True,
                "skew_angle": round(random.uniform(-2, 2), 2)
            },
            "answers": answers,
            "quality_metrics": {
                "overall_confidence": round(sum(a["confidence"] for a in answers) / len(answers), 3) if answers else 0.0,
                "low_confidence_count": sum(1 for a in answers if a["confidence"] < 0.7),
                "flags_count": sum(len(a.get("flags", [])) for a in answers)
            }
        }

        return result

    def _mm_to_pixels(self, mm: float, dpi: int) -> int:
        """Convert millimeters to pixels"""
        return int(mm * dpi / 25.4)

    def _simulate_ocr_error(self, text: str) -> str:
        """Simulate common OCR errors"""
        errors = [
            lambda t: t.replace('o', '0'),
            lambda t: t.replace('l', '1'),
            lambda t: t.replace('i', '1'),
            lambda t: t.lower(),
            lambda t: t.upper(),
            lambda t: t + ' ',
            lambda t: t[:-1] if len(t) > 1 else t
        ]

        if random.random() < 0.3:  # 30% chance of error
            return random.choice(errors)(text)
        return text


def main():
    parser = argparse.ArgumentParser(
        description='Extract answers from scanned test images',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Scan actual test image (JSON format)
    testscan test_s001_v1.json \\
        --layout template_layout.json \\
        --output scan_result.json

    # Synthetic scan (for testing/backward compatibility)
    testscan --synthetic s001 v1 \\
        --layout template_layout.json \\
        --question-order question_order.json \\
        --output scan_result.json

    # Batch scans
    for img in test_images/*.json; do
      testscan "$img" --layout template_layout.json \\
        --output "scans/$(basename "$img" .json)_result.json"
    done
        """
    )

    parser.add_argument('image', nargs='?', type=str,
                        help='Input image file (.json or .pgm)')
    parser.add_argument('--layout', type=str, required=True,
                        help='Template layout JSON file')
    parser.add_argument('--synthetic', nargs=2, metavar=('STUDENT_ID', 'VERSION_ID'),
                        help='Generate synthetic scan result (testing mode)')
    parser.add_argument('--question-order', type=str,
                        help='Question order JSON (required for synthetic mode)')
    parser.add_argument('--accuracy', type=float, default=0.95,
                        help='Simulated accuracy for synthetic scans (default: 0.95)')
    parser.add_argument('--output', '-o', type=str,
                        help='Output JSON file (default: stdout)')
    parser.add_argument('--tier', type=str, default='free',
                        choices=['free', 'pro', 'enterprise'],
                        help='Tier level (default: free)')
    parser.add_argument('--seed', type=int, help='Random seed for reproducibility')

    args = parser.parse_args()

    # Set random seed if provided
    if args.seed:
        random.seed(args.seed)

    # Load template layout
    try:
        with open(args.layout, 'r') as f:
            template_layout = json.load(f)
    except FileNotFoundError:
        print(f"Error: Layout file '{args.layout}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing layout JSON: {e}", file=sys.stderr)
        sys.exit(1)

    scanner = ImageScanner(tier=args.tier)

    # Generate synthetic scan
    if args.synthetic:
        student_id, version_id = args.synthetic

        if not args.question_order:
            print("Error: --question-order required for synthetic mode", file=sys.stderr)
            sys.exit(1)

        try:
            with open(args.question_order, 'r') as f:
                question_order = json.load(f)
        except FileNotFoundError:
            print(f"Error: Question order file '{args.question_order}' not found", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error parsing question order JSON: {e}", file=sys.stderr)
            sys.exit(1)

        result = scanner.scan_synthetic(
            student_id,
            version_id,
            template_layout,
            question_order,
            accuracy=args.accuracy
        )

        print(f"Generated synthetic scan for student {student_id}, version {version_id}", file=sys.stderr)

    # Scan real image
    elif args.image:
        result = scanner.scan_image(args.image, template_layout)
        print(f"Scanned image: {args.image}", file=sys.stderr)

    else:
        print("Error: Either provide an image file or use --synthetic mode", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # Output
    json_output = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"Successfully wrote scan result to {args.output}", file=sys.stderr)
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(json_output)


if __name__ == '__main__':
    main()
