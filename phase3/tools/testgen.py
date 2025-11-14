#!/usr/bin/env python3
"""
testgen - Generate test document images for scanning

Creates synthetic scanned test images with realistic distortions.
Uses only Python standard library (no external dependencies).

Usage:
    testgen --layout template_layout.json --output tests/ --students s001,s002,s003
"""

import argparse
import json
import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple


class TestImageGenerator:
    """Generates test document images as 2D arrays"""

    def __init__(self, width: int = 2100, height: int = 2970):
        """
        Initialize generator

        Args:
            width: Image width in pixels (default: 2100 = 210mm @ 300dpi)
            height: Image height in pixels (default: 2970 = 297mm @ 300dpi)
        """
        self.width = width
        self.height = height
        self.dpi = 300  # Assume 300 DPI

    def mm_to_pixels(self, mm: float) -> int:
        """Convert millimeters to pixels"""
        return int(mm * self.dpi / 25.4)

    def create_blank_test(self) -> List[List[int]]:
        """Create a blank test image (white background)"""
        return [[255 for _ in range(self.width)] for _ in range(self.height)]

    def draw_circle(self, image: List[List[int]], x: int, y: int, radius: int, filled: bool = True, value: int = 0):
        """Draw a circle on the image"""
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx*dx + dy*dy <= radius*radius:
                    px, py = x + dx, y + dy
                    if 0 <= px < self.width and 0 <= py < self.height:
                        if filled or dx*dx + dy*dy >= (radius-2)*(radius-2):
                            image[py][px] = value

    def draw_rectangle(self, image: List[List[int]], x: int, y: int, width: int, height: int, value: int = 0):
        """Draw a rectangle outline"""
        # Top and bottom
        for dx in range(width):
            px = x + dx
            if 0 <= px < self.width:
                if 0 <= y < self.height:
                    image[y][px] = value
                if 0 <= y + height < self.height:
                    image[y + height][px] = value

        # Left and right
        for dy in range(height):
            py = y + dy
            if 0 <= py < self.height:
                if 0 <= x < self.width:
                    image[py][x] = value
                if 0 <= x + width < self.width:
                    image[py][x + width] = value

    def fill_rectangle(self, image: List[List[int]], x: int, y: int, width: int, height: int, value: int = 0):
        """Draw a filled rectangle"""
        for dy in range(height):
            for dx in range(width):
                px, py = x + dx, y + dy
                if 0 <= px < self.width and 0 <= py < self.height:
                    image[py][px] = value

    def generate_test_image(
        self,
        student_id: str,
        version_id: str,
        template_layout: Dict[str, Any],
        question_order: Dict[str, Any],
        answers: Dict[str, str],
        add_noise: bool = True
    ) -> List[List[int]]:
        """
        Generate a filled test image

        Args:
            student_id: Student identifier
            version_id: Test version
            template_layout: Template layout specification
            question_order: Question order with correct answers
            answers: Dictionary of question_id -> student's answer
            add_noise: Whether to add realistic noise

        Returns:
            2D array representing grayscale image (0=black, 255=white)
        """
        image = self.create_blank_test()

        # Draw registration marks
        for mark in template_layout["registration_marks"]:
            x = self.mm_to_pixels(mark["x_mm"])
            y = self.mm_to_pixels(mark["y_mm"])
            radius = self.mm_to_pixels(mark["size_mm"])
            self.draw_circle(image, x, y, radius, filled=True, value=0)

        # Draw question answer fields
        for q_layout in template_layout["questions"]:
            q_id = q_layout["question_id"]

            # Draw answer region boundary (for visualization)
            region = q_layout["answer_region"]
            rx = self.mm_to_pixels(region["x_mm"])
            ry = self.mm_to_pixels(region["y_mm"])
            rw = self.mm_to_pixels(region["width_mm"])
            rh = self.mm_to_pixels(region["height_mm"])

            # Draw answer fields
            if "answer_fields" in q_layout:
                # Multiple choice / True-False - draw bubbles
                for field in q_layout["answer_fields"]:
                    fx = self.mm_to_pixels(field["x_mm"])
                    fy = self.mm_to_pixels(field["y_mm"])

                    # Draw bubble outline
                    if field["field_type"] == "circle":
                        radius = self.mm_to_pixels(field.get("radius_mm", 3))
                        self.draw_circle(image, fx, fy, radius, filled=False, value=0)

                        # Fill if this is the student's answer
                        student_answer = answers.get(q_id)
                        if student_answer == field["label"]:
                            # Add slight imperfection to fill
                            fill_radius = radius - 1
                            self.draw_circle(image, fx, fy, fill_radius, filled=True, value=50)

            elif "ocr_region" in q_layout:
                # Short answer / Essay - draw text box
                ocr = q_layout["ocr_region"]
                ox = self.mm_to_pixels(ocr["x_mm"])
                oy = self.mm_to_pixels(ocr["y_mm"])
                ow = self.mm_to_pixels(ocr["width_mm"])
                oh = self.mm_to_pixels(ocr["height_mm"])
                self.draw_rectangle(image, ox, oy, ow, oh, value=0)

                # Simulate handwritten text (just random marks)
                if q_id in answers:
                    # Add some scribbles to simulate text
                    for i in range(5):
                        tx = ox + 5 + i * 10
                        ty = oy + oh // 2
                        self.fill_rectangle(image, tx, ty, 8, 2, value=80)

        # Add noise if requested
        if add_noise:
            self._add_noise(image, intensity=10)

        return image

    def _add_noise(self, image: List[List[int]], intensity: int = 10):
        """Add random noise to image"""
        for y in range(0, self.height, 5):  # Sparse noise for performance
            for x in range(0, self.width, 5):
                if random.random() < 0.1:  # 10% of pixels
                    noise = random.randint(-intensity, intensity)
                    image[y][x] = max(0, min(255, image[y][x] + noise))

    def apply_distortions(
        self,
        image: List[List[int]],
        rotation: float = 0.0,
        skew: float = 0.0,
        noise_level: int = 10
    ) -> List[List[int]]:
        """
        Apply realistic distortions to image

        Args:
            image: Input image
            rotation: Rotation angle in degrees (small angles only)
            skew: Skew factor (0-0.1 recommended)
            noise_level: Noise intensity (0-50)

        Returns:
            Distorted image
        """
        # Apply rotation (small angles only)
        if abs(rotation) > 0.1:
            image = self._apply_rotation(image, rotation)

        # Apply skew
        if abs(skew) > 0.001:
            image = self._apply_skew(image, skew)

        # Add noise
        if noise_level > 0:
            self._add_noise(image, intensity=noise_level)

        return image

    def _apply_rotation(self, image: List[List[int]], angle: float) -> List[List[int]]:
        """
        Apply rotation to image using simple nearest-neighbor interpolation

        Args:
            image: Input image
            angle: Rotation angle in degrees

        Returns:
            Rotated image
        """
        height = len(image)
        width = len(image[0]) if height > 0 else 0

        # Convert to radians
        theta = -angle * math.pi / 180.0

        # Create output image
        rotated = [[255 for _ in range(width)] for _ in range(height)]

        # Rotation center
        cx = width / 2
        cy = height / 2

        # Apply rotation
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)

        for y in range(height):
            for x in range(width):
                # Translate to origin
                tx = x - cx
                ty = y - cy

                # Rotate
                rx = tx * cos_theta - ty * sin_theta
                ry = tx * sin_theta + ty * cos_theta

                # Translate back
                src_x = int(rx + cx)
                src_y = int(ry + cy)

                # Copy pixel if in bounds
                if 0 <= src_x < width and 0 <= src_y < height:
                    rotated[y][x] = image[src_y][src_x]

        return rotated

    def _apply_skew(self, image: List[List[int]], skew: float) -> List[List[int]]:
        """
        Apply horizontal skew to image

        Args:
            image: Input image
            skew: Skew factor

        Returns:
            Skewed image
        """
        height = len(image)
        width = len(image[0]) if height > 0 else 0

        # Create output image
        skewed = [[255 for _ in range(width)] for _ in range(height)]

        for y in range(height):
            # Calculate horizontal shift based on vertical position
            shift = int(skew * (y - height / 2))

            for x in range(width):
                src_x = x - shift

                if 0 <= src_x < width:
                    skewed[y][x] = image[y][src_x]

        return skewed

    def save_pgm(self, image: List[List[int]], filename: str):
        """
        Save image as PGM (Portable GrayMap) format

        PGM is a simple, text-based image format that can be read by most tools
        """
        with open(filename, 'w') as f:
            # PGM header
            f.write("P2\n")
            f.write(f"{self.width} {self.height}\n")
            f.write("255\n")

            # Write pixel data
            for row in image:
                f.write(" ".join(str(p) for p in row) + "\n")

    def save_compact(self, image: List[List[int]], filename: str):
        """Save image in compact JSON format (for testscan to read)"""
        # Compress by only storing non-white pixels
        compressed = {
            "width": self.width,
            "height": self.height,
            "format": "sparse",
            "pixels": []
        }

        for y in range(self.height):
            for x in range(self.width):
                if image[y][x] < 255:  # Not white
                    compressed["pixels"].append([x, y, image[y][x]])

        with open(filename, 'w') as f:
            json.dump(compressed, f)


def main():
    parser = argparse.ArgumentParser(
        description='Generate synthetic test document images',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--layout', type=str, required=True,
                        help='Template layout JSON file')
    parser.add_argument('--question-order', type=str, required=True,
                        help='Question order JSON file')
    parser.add_argument('--output', '-o', type=str, required=True,
                        help='Output directory')
    parser.add_argument('--students', type=str,
                        help='Comma-separated student IDs (default: all from question_order)')
    parser.add_argument('--accuracy', type=float, default=0.90,
                        help='Answer accuracy (0-1, default: 0.90)')
    parser.add_argument('--noise', type=int, default=10,
                        help='Noise level (0-50, default: 10)')
    parser.add_argument('--rotation', type=float, default=0.0,
                        help='Rotation angle in degrees (default: 0)')
    parser.add_argument('--skew', type=float, default=0.0,
                        help='Skew factor (default: 0, try 0.01-0.05 for subtle skew)')
    parser.add_argument('--format', type=str, default='json',
                        choices=['json', 'pgm'],
                        help='Output format (default: json)')
    parser.add_argument('--seed', type=int, help='Random seed')

    args = parser.parse_args()

    if args.seed:
        random.seed(args.seed)

    # Load layout and question order
    with open(args.layout) as f:
        template_layout = json.load(f)

    with open(args.question_order) as f:
        question_order = json.load(f)

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine students to generate
    if args.students:
        student_ids = args.students.split(',')
    else:
        student_ids = list(question_order["student_assignments"].keys())

    generator = TestImageGenerator()

    # Generate test for each student
    for student_id in student_ids:
        version_id = question_order["student_assignments"][student_id]
        version_data = question_order["versions"][version_id]

        # Generate answers (some correct, some wrong based on accuracy)
        answers = {}
        for q in version_data["questions"]:
            q_id = q["question_id"]
            correct_answer = q["correct_answer"]

            # Randomly decide if correct
            if random.random() < args.accuracy:
                answers[q_id] = correct_answer
            else:
                # Pick wrong answer
                if "options" in q and q["options"]:
                    wrong_options = [opt["label"] for opt in q["options"] if opt["label"] != correct_answer]
                    if wrong_options:
                        answers[q_id] = random.choice(wrong_options)
                    else:
                        answers[q_id] = correct_answer
                else:
                    answers[q_id] = "Wrong Answer"

        # Generate image
        print(f"Generating test for {student_id} (version {version_id})...", file=sys.stderr)
        image = generator.generate_test_image(
            student_id,
            version_id,
            template_layout,
            question_order,
            answers,
            add_noise=True
        )

        # Apply distortions
        image = generator.apply_distortions(
            image,
            rotation=args.rotation,
            skew=args.skew,
            noise_level=args.noise
        )

        # Save
        if args.format == 'pgm':
            filename = output_dir / f"{student_id}_{version_id}.pgm"
            generator.save_pgm(image, str(filename))
        else:  # json
            filename = output_dir / f"{student_id}_{version_id}.json"
            generator.save_compact(image, str(filename))

        print(f"  Saved: {filename}", file=sys.stderr)

    print(f"\nGenerated {len(student_ids)} test images", file=sys.stderr)


if __name__ == '__main__':
    main()
