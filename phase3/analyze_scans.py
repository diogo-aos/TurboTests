#!/usr/bin/env python3
"""Analyze testscan accuracy across distortion levels"""

import json
from pathlib import Path

# Load question order for correct answers
with open('phase3/output/e2e_test/question_order.json') as f:
    question_order = json.load(f)

# Analyze each scan result
results = []

for scan_file in sorted(Path('phase3/test_images/scan_results').glob('*.json')):
    with open(scan_file) as f:
        scan = json.load(f)

    # Extract distortion level and student ID
    parts = scan_file.stem.split('_')
    if parts[0] == 'clean':
        distortion = 'clean'
        student_id = parts[1]
        version_id = parts[2]
    elif parts[0] == 'slight':
        distortion = 'slight'
        student_id = parts[2]
        version_id = parts[3]
    elif parts[0] == 'heavy':
        distortion = 'heavy'
        student_id = parts[2]
        version_id = parts[3]
    else:
        continue

    # Get correct answers for this version
    version_data = question_order['versions'][version_id]

    # Compare results
    total = 0
    correct = 0
    avg_confidence = 0.0

    for answer in scan['answers']:
        q_id = answer['question_id']
        q_type = answer['question_type']

        # Only check MC/TF (short answer OCR is simulated)
        if q_type in ['multiple_choice', 'true_false']:
            # Find correct answer
            correct_answer = None
            for q in version_data['questions']:
                if q['question_id'] == q_id:
                    correct_answer = q['correct_answer']
                    break

            if correct_answer:
                total += 1
                if str(answer['extracted_answer']) == str(correct_answer):
                    correct += 1
                avg_confidence += answer['confidence']

    accuracy = (correct / total * 100) if total > 0 else 0
    avg_confidence = (avg_confidence / total) if total > 0 else 0

    results.append({
        'distortion': distortion,
        'student': student_id,
        'version': version_id,
        'accuracy': accuracy,
        'confidence': avg_confidence,
        'markers_detected': scan['rectification']['markers_detected'],
        'processing_time': scan['scan_metadata']['processing_time_ms']
    })

# Print summary
print("=" * 80)
print("TESTSCAN ACCURACY ANALYSIS")
print("=" * 80)
print()

for distortion_level in ['clean', 'slight', 'heavy']:
    print(f"{distortion_level.upper()} DISTORTION:")
    print("-" * 60)

    level_results = [r for r in results if r['distortion'] == distortion_level]

    if level_results:
        avg_acc = sum(r['accuracy'] for r in level_results) / len(level_results)
        avg_conf = sum(r['confidence'] for r in level_results) / len(level_results)
        avg_markers = sum(r['markers_detected'] for r in level_results) / len(level_results)
        avg_time = sum(r['processing_time'] for r in level_results) / len(level_results)

        print(f"  Average Accuracy:   {avg_acc:.1f}%")
        print(f"  Average Confidence: {avg_conf:.3f}")
        print(f"  Markers Detected:   {avg_markers:.1f} / 4")
        print(f"  Processing Time:    {avg_time:.1f} ms")
        print()

        for r in level_results:
            print(f"    {r['student']} ({r['version']}): {r['accuracy']:.0f}% accuracy, {r['confidence']:.3f} confidence")

    print()

print("=" * 80)
