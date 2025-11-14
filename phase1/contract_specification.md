# TurboTests Data Contract Specification

Version: 1.0.0
Date: 2025-11-14

## Overview

This document defines the data contracts (JSON schemas) that serve as the API between independent tools in the TurboTests system. Following UNIX philosophy, each tool is designed to do one thing well and communicate through well-defined JSON structures.

## Architecture

The TurboTests system consists of six modular tools connected through five JSON data contracts:

```
GIFT file ──> [gift2json] ──> questions.json ──┐
                                                 │
Config params ──> [configgen] ──> config.json ──┤
                                                 │
                                                 v
                            [docgen] ──> PDFs + template_layout.json + question_order.json
                                                 │
                                                 │
Image file ─────────────────────────────────────┘
                                                 │
                                                 v
                            [imagescan] ──> scan_result.json
                                                 │
                                                 v
                            [scorer] ──> scores.json
                                                 │
                                                 v
                            [report] ──> HTML/PDF/CSV reports
```

## Data Contracts

### 1. questions.json

**Producer:** `gift2json`
**Consumers:** `configgen`, `docgen`
**Schema:** `schemas/questions_schema.json`
**Example:** `examples/questions_example.json`

**Purpose:** Structured representation of test questions parsed from GIFT format.

**Key Features:**
- Supports multiple question types: multiple choice, short answer, essay, matching, true/false
- Includes metadata: difficulty, tags, points
- Pro/Enterprise features: partial credit rules, custom attributes, feedback, standards mapping
- Extensible for future question types

**Tier Variations:**
- **Free:** Multiple choice only
- **Pro:** + Short answer, difficulty tagging
- **Enterprise:** All types + custom attributes, standards mapping, feedback

**Validation Requirements:**
- All question IDs must be unique
- Question type must match available options (MC requires options array)
- Point values must be non-negative

---

### 2. config.json

**Producer:** `configgen`
**Consumers:** `docgen`
**Schema:** `schemas/config_schema.json`
**Example:** `examples/config_example.json`

**Purpose:** Configuration for test generation including distribution strategy, personalization, and tier restrictions.

**Key Features:**
- Test metadata: title, date, instructions, duration
- Distribution settings: versions, students, strategy (round robin, random, difficulty balanced, adaptive)
- Template customization: branding, headers, footers, personalization
- Scanning parameters: DPI, page size, registration mark density
- Tier restrictions: enforce feature limits per tier

**Tier Variations:**
- **Free:** Round robin distribution, basic template, no personalization
- **Pro:** + Difficulty balancing, randomization, student names, custom headers
- **Enterprise:** All strategies, adaptive balancing, photos, QR codes, watermarks

**Validation Requirements:**
- Distribution strategy must be in tier-allowed list
- Question types in restrictions must match tier capabilities
- Student count must not exceed tier maximum
- Version count must not exceed tier maximum

---

### 3. template_layout.json

**Producer:** `docgen`
**Consumers:** `imagescan`
**Schema:** `schemas/template_layout_schema.json`
**Example:** `examples/template_layout_example.json`

**Purpose:** Describes the physical layout of test PDFs for image recognition and scanning.

**Key Features:**
- Page dimensions in millimeters with DPI specification
- Registration marks (typically 4 corner markers) for image rectification
- ID fields for version and student identification (barcode, QR code, OCR text, bubble array)
- Precise answer field positions for each question
- Fill detection parameters (threshold, noise tolerance)

**Answer Field Types:**
- **Multiple choice / True-false:** Array of circle/box positions with labels
- **Short answer / Essay:** OCR region with expected line count

**Critical Coordinates:**
- All positions in millimeters from top-left origin
- Registration marks must be detectable and non-overlapping
- Answer fields must not overlap with text regions
- Coordinates assume portrait orientation unless specified

**Assumptions:**
- Standard page sizes: A4 (210x297mm), Letter (216x279mm), Legal (216x356mm)
- Expected scan DPI: 150, 200, 300, or 600
- Registration marks are high-contrast (black on white)
- Minimum mark size: 3mm diameter for reliable detection

---

### 4. scan_result.json

**Producer:** `imagescan`
**Consumers:** `scorer`
**Schema:** `schemas/scan_result_schema.json`
**Example:** `examples/scan_result_example.json`

**Purpose:** Extracted answers and metadata from scanned test images.

**Key Features:**
- Scan metadata: timestamp, source file, hash, processing time
- Identification: extracted version ID and student ID with confidence scores
- Rectification info: markers detected, skew correction, quality score
- Per-question answers with confidence and raw data
- Warnings and flags for manual review

**Answer Extraction:**
- **Multiple choice:** Selected option label (A, B, C, D) with fill percentages for all options
- **Short answer:** OCR text with alternative readings and confidence
- **No answer:** null with `no_answer` flag set

**Confidence Scoring:**
- Range: 0.0 (no confidence) to 1.0 (certain)
- Threshold for auto-scoring: typically 0.7-0.8
- Low confidence triggers manual review flag

**Warning Types:**
- `low_confidence`: Confidence below threshold
- `multiple_bubbles_filled`: More than one answer selected
- `no_bubble_filled`: No answer detected
- `unclear_mark`: Mark is ambiguous
- `ocr_failed`: OCR could not extract text
- `region_not_found`: Answer region not located
- `poor_image_quality`: Image quality insufficient

**Quality Metrics:**
- Average confidence across all answers
- Number of answers flagged for review
- Overall scan quality: excellent (>0.9), good (0.7-0.9), fair (0.5-0.7), poor (<0.5)

---

### 5. scores.json

**Producer:** `scorer`
**Consumers:** `report`
**Schema:** `schemas/scores_schema.json`
**Example:** `examples/scores_example.json`

**Purpose:** Scored test results with grades, statistics, and item analysis.

**Key Features:**
- Per-student scores with question-level detail
- Summary statistics: points, percentage, letter grade
- Class statistics: mean, median, standard deviation, grade distribution
- Item analysis: difficulty, discrimination index, point-biserial correlation
- Support for partial credit, curved grading, rubrics

**Scoring Models:**
- **basic_correct_incorrect:** Binary scoring (free tier)
- **partial_credit:** Fractional points for partially correct answers (pro tier)
- **rubric_based:** Custom scoring rubrics (enterprise tier)
- **curved:** Curved grading with multiple methods (enterprise tier)

**Per-Question Scoring:**
- Student answer vs. correct answer comparison
- Points earned / points possible
- Correctness flag
- Confidence from scan (flags low-confidence answers)
- Manual review flags

**Class Statistics (Pro/Enterprise):**
- Descriptive statistics: mean, median, std dev, min, max
- Grade distribution histogram
- Item analysis for each question:
  - Percent correct (difficulty measure)
  - Discrimination index: how well question separates high/low performers
  - Point-biserial correlation: correlation between question score and total score

**Grading Scale:**
- Configurable letter grade ranges
- Typically: A (90-100), B (80-89), C (70-79), D (60-69), F (0-59)
- Can include plus/minus grades (enterprise tier)

---

## End-to-End Data Flow

### Production Pipeline

```bash
# Step 1: Parse GIFT questions
gift2json exam_questions.gift > questions.json

# Step 2: Generate test configuration
configgen --tier pro \
          --versions 3 \
          --students 30 \
          --strategy difficulty_balanced \
          --output config.json

# Step 3: Generate test PDFs
docgen questions.json config.json \
       --template template.typ \
       --output pdfs/
# Produces:
#   - pdfs/student_s001_version_v1.pdf
#   - pdfs/student_s002_version_v2.pdf
#   - ... (30 PDFs total)
#   - template_layout.json
#   - question_order.json (maps student -> version -> question order)

# Step 4: Print and administer tests (manual step)
```

### Scanning Pipeline

```bash
# Step 1: Scan filled tests (images in scans/ directory)

# Step 2: Extract answers from scanned images
for image in scans/*.jpg; do
  imagescan "$image" \
            --layout template_layout.json \
            --output json/$( basename "$image" .jpg).json
done

# Step 3: Score the tests
scorer --scan-results json/*.json \
       --question-order question_order.json \
       --answer-key questions.json \
       --output scores.json

# Step 4: Generate report
report scores.json \
       --format html \
       --output report.html
```

### Alternative: Streaming Pipeline

```bash
# Stream scans through scoring to report
for image in scans/*.jpg; do
  imagescan "$image" --layout template_layout.json
done | \
  scorer --answer-key questions.json \
         --question-order question_order.json | \
  report --format html --output results.html
```

---

## Assumptions and Requirements

### Image Scanning

**Scan Quality:**
- Minimum DPI: 150 (300 recommended for OCR)
- Image format: JPEG, PNG, TIFF
- Color mode: Grayscale or RGB (converted internally)
- File size: < 50MB per image

**Physical Requirements:**
- Clean, uncrumpled paper
- High contrast marks (dark pencil or pen on white paper)
- No stray marks near answer fields
- All 4 registration marks visible and unobscured

**Supported Distortions:**
- Skew: up to ±15 degrees (correctable)
- Perspective: minor perspective distortion (correctable with 4 corner marks)
- Rotation: any rotation (correctable)

**Not Supported:**
- Severe creasing or tears through answer regions
- Water damage or significant discoloration
- Marks that obscure registration marks

### Answer Field Detection

**Bubble/Box Fill Threshold:**
- Default: 60% of area filled
- Adjustable per tier:
  - Free: Fixed at 60%
  - Pro: Adjustable 40-80%
  - Enterprise: Adjustable 20-90% with noise tolerance levels

**Multiple Marks:**
- If multiple bubbles exceed threshold: flagged as `multiple_bubbles_filled`
- Highest fill percentage wins (if auto-scoring enabled)
- Otherwise: flagged for manual review

**OCR Text Extraction:**
- Engine: Tesseract (free), Tesseract v5 (pro), multiple engines (enterprise)
- Language: English (configurable)
- Expected: Printed or clear handwriting
- Confidence threshold: 70% (adjustable in pro/enterprise)

### Tier Restrictions

**Feature Enforcement:**
- Tools validate tier restrictions from config.json
- Invalid features for tier → error with clear message
- Example: Free tier user tries difficulty_balanced strategy → rejected

**Tier Progression:**
- Free → Pro → Enterprise
- Higher tiers inherit all lower tier features
- Tier set in config.json, enforced by all tools

---

## Schema Validation

All tools must validate input against schemas before processing:

```python
import jsonschema

def validate_questions(data):
    with open('schemas/questions_schema.json') as f:
        schema = json.load(f)
    jsonschema.validate(instance=data, schema=schema)
```

**Validation Failures:**
- Must produce clear error messages indicating:
  - Which field failed validation
  - Expected value/format
  - Actual value received
- Exit with non-zero status code
- No partial processing (fail fast)

---

## Versioning Strategy

**Semantic Versioning:**
- Schema version format: `MAJOR.MINOR.PATCH`
- Current version: `1.0.0`

**Version Compatibility:**
- **MAJOR:** Breaking changes (incompatible schema changes)
- **MINOR:** Backward-compatible additions (new optional fields)
- **PATCH:** Clarifications, documentation updates

**Version Checking:**
- All tools must check schema version in input files
- Reject files with incompatible major version
- Warn on minor version mismatch
- Ignore patch version differences

---

## Testing Strategy

### Unit Tests (Per Schema)

Each schema should have:
- **Valid examples:** Confirmed to pass validation
- **Invalid examples:** Confirmed to fail validation with specific errors
- **Edge cases:** Empty arrays, null values, boundary values

### Integration Tests (Across Schemas)

- **Round-trip test:** questions.json → docgen → template_layout.json → imagescan → scan_result.json → scorer → scores.json
- **Synthetic data:** Generate filled tests programmatically, verify extraction accuracy
- **Data consistency:** Ensure question IDs, student IDs, version IDs match across all files

### Fixtures

The `examples/` directory contains valid examples for each schema. Use these as:
- Reference implementations
- Test fixtures
- Documentation examples
- Starting points for new tests

---

## Extension Points

### Adding New Question Types

1. Update `questions_schema.json` with new type enum value
2. Define required fields for new type
3. Update `template_layout_schema.json` for rendering
4. Update `scan_result_schema.json` for extraction
5. Update `scores_schema.json` for scoring
6. Bump MINOR version

### Adding Tier Features

1. Add feature flags to `config_schema.json` in `tier_restrictions`
2. Document tier availability in this specification
3. Update tools to check restrictions
4. Bump MINOR version

### Changing Coordinate System

If coordinate system needs to change (e.g., pixels instead of mm):
- This is a BREAKING change → bump MAJOR version
- Provide migration tool to convert old layouts to new format
- Maintain backward compatibility for one major version

---

## FAQ

**Q: Why millimeters instead of pixels for coordinates?**
A: Resolution-independent. Same layout works at 150 DPI or 600 DPI. Conversion to pixels happens in `imagescan` based on actual scan DPI.

**Q: Can I mix question types in a single test?**
A: Yes, `questions.json` supports heterogeneous question arrays. The tier restrictions determine which types are allowed.

**Q: What if a student bubbles two answers?**
A: The `imagescan` tool detects this and sets `warnings: ["multiple_bubbles_filled"]` and `flags.multiple_answers: true`. The `scorer` can then apply a policy (e.g., mark incorrect, take first answer, flag for manual review).

**Q: How do I add support for a new barcode format?**
A: Update `template_layout_schema.json` to add the new type to the `id_fields.*.type` enum. Update `docgen` to generate it and `imagescan` to decode it. This is a MINOR version bump (backward compatible - old tools ignore unknown types).

**Q: Can tools be written in different languages?**
A: Absolutely. The JSON contracts are language-agnostic. `gift2json` could be Python, `docgen` could be Rust with Typst, `imagescan` could be C++ with OpenCV, etc. As long as they produce/consume valid JSON, they interoperate.

**Q: What if I want to add a new statistical metric?**
A: Add it to `class_statistics` or `question_analysis` in `scores_schema.json` as an optional field. MINOR version bump. Old `report` tools will ignore unknown fields.

---

## Summary

The Phase 1 data contracts establish a solid foundation for the TurboTests system:

✅ **Clear boundaries:** Each tool has well-defined inputs and outputs
✅ **Testable:** Schemas enable automated validation
✅ **Extensible:** Optional fields and versioning support growth
✅ **Interoperable:** Language-agnostic JSON contracts
✅ **Debuggable:** Human-readable intermediate files
✅ **Flexible:** Tier system enables business model experimentation

**Next Steps (Phase 2):**
- Implement `gift2json` tool
- Implement `configgen` tool
- Implement `report` tool
- Create test fixtures for each tool
- Validate round-trip with example data
