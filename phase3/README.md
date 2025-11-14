# Phase 3: Document Generation (docgen)

Phase 3 implements the `docgen` tool, the first dependent tool in the pipeline. It takes questions and configuration as inputs and generates test documents along with layout metadata.

## Implemented Tool

### `docgen` - Test Document Generator

Generates test documents in Typst format, along with layout and question order metadata.

**Input:**
- `questions.json` (from gift2json, Phase 2)
- `config.json` (from configgen, Phase 2)

**Output:**
- Typst source files (`.typ`) for each student
- `template_layout.json` - Physical layout for scanning
- `question_order.json` - Question/answer mapping for scoring

**Features:**
- Multiple distribution strategies (round_robin, random, difficulty_balanced)
- Question randomization across versions
- Answer option shuffling (for MC questions)
- Student-to-version assignment
- Registration marks for scanning
- Support for multiple question types (MC, TF, short answer, essay)
- Generates scannable test layouts

**Usage:**
```bash
# Basic usage
python3 tools/docgen.py questions.json config.json --output ./output/

# With reproducible random seed
python3 tools/docgen.py questions.json config.json \
  --output ./tests/midterm/ \
  --seed 42
```

## Output Structure

```
output/
├── template_layout.json      # Physical layout for scanning
├── question_order.json        # Question/answer mapping
└── typst/
    ├── s001_v1.typ           # Student 1, Version 1
    ├── s002_v2.typ           # Student 2, Version 2
    ├── s003_v1.typ           # Student 3, Version 1
    └── ...
```

### template_layout.json

Describes the physical layout of tests for scanning:
- Page dimensions and DPI
- Registration mark positions (4 corners)
- ID field locations (version, student)
- Question answer regions
- Answer field coordinates (for MC/TF)
- OCR regions (for short answer/essay)
- Fill detection parameters

### question_order.json

Maps questions to students and versions:
- Version definitions with question order
- Correct answers for each question
- Student-to-version assignments
- Question metadata (type, points, text)

## Distribution Strategies

### round_robin
Questions are rotated across versions. Each version gets all questions in a different order.

Example with 5 questions, 3 versions:
- Version 1: Q1, Q2, Q3, Q4, Q5
- Version 2: Q2, Q3, Q4, Q5, Q1
- Version 3: Q3, Q4, Q5, Q1, Q2

### random
Questions are randomly shuffled for each version (requires seed for reproducibility).

### difficulty_balanced
Attempts to balance difficulty across versions (requires difficulty tags on questions).

## Typst Document Generation

Generated `.typ` files include:
- Registration marks in all 4 corners
- Test title and metadata
- Student name and ID
- Version identifier
- Question text with proper formatting
- Answer bubbles for MC/TF questions
- Text boxes for short answer/essay questions

### Compiling to PDF

If Typst is installed:
```bash
# Compile single file
typst compile output/typst/s001_v1.typ

# Compile all files
for file in output/typst/*.typ; do
  typst compile "$file"
done
```

## Testing

Comprehensive test suite with 12 tests:

```bash
# Run tests
python3 tests/test_docgen.py
```

**Test Coverage:**
- Basic generation workflow
- Template layout structure
- Question order structure
- Distribution strategies
- Student assignment
- Typst file generation
- Answer field layouts
- OCR region placement
- Custom student lists
- Multiple page sizes
- Integration with Phase 2

## End-to-End Pipeline

Full workflow from GIFT format to test documents:

```bash
# 1. Convert GIFT to JSON
python3 phase2/tools/gift2json.py questions.gift \
  --tier pro \
  --title "Midterm Exam" \
  --output questions.json

# 2. Generate configuration
python3 phase2/tools/configgen.py \
  --title "Midterm Exam" \
  --versions 3 \
  --students 30 \
  --tier pro \
  --strategy difficulty_balanced \
  --randomize-questions \
  --output config.json

# 3. Generate test documents
python3 phase3/tools/docgen.py \
  questions.json config.json \
  --output ./output/ \
  --seed 12345

# 4. Compile PDFs (if Typst installed)
cd output/typst && for f in *.typ; do typst compile "$f"; done
```

## Design Principles

### 1. Reproducibility
Random operations accept a seed parameter for reproducible test generation.

### 2. Scanner-Ready Output
Templates include registration marks and precise coordinate data for automated scanning.

### 3. Flexible Layout
Supports multiple page sizes (A4, Letter, Legal) and answer field types (circles, boxes).

### 4. Version Fairness
Distribution strategies ensure fair test versions with equivalent difficulty.

### 5. Composition
Cleanly composes with Phase 2 tools via JSON contracts - no tight coupling.

## Question Order Schema

The `question_order.json` format (inferred, not in Phase 1 schemas):

```json
{
  "version": "1.0.0",
  "test_info": {
    "title": "Test Title",
    "date": "2025-11-14"
  },
  "versions": {
    "v1": {
      "version_id": "v1",
      "questions": [
        {
          "question_number": 1,
          "question_id": "q1",
          "question_type": "multiple_choice",
          "question_text": "Question text...",
          "correct_answer": "B",
          "points": 2,
          "options": [...]
        }
      ]
    }
  },
  "student_assignments": {
    "s001": "v1",
    "s002": "v2"
  }
}
```

## Examples

### Basic 3-Version Test

```bash
python3 phase3/tools/docgen.py questions.json config.json \
  --output ./midterm/
```

Generates:
- 3 question orderings (rotated)
- Student assignments balanced across versions
- Template layout with scanner coordinates
- Typst files for each student

### Randomized Test

```bash
python3 phase3/tools/docgen.py questions.json config.json \
  --output ./quiz/ \
  --seed 42
```

With `randomize_questions: true` in config, questions are shuffled differently for each version while maintaining reproducibility.

## Integration Points

### Inputs (from Phase 2)
- Phase 2 `gift2json` → `questions.json`
- Phase 2 `configgen` → `config.json`

### Outputs (for future phases)
- `template_layout.json` → Phase 3 `imagescan` (not yet implemented)
- `question_order.json` → Phase 3 `scorer` (not yet implemented)
- Typst files → External compilation with `typst`

## Notes

- Typst compilation is optional - the tool generates source files only
- Registration marks positioned at 4 corners for robust rectification
- Answer bubbles positioned with precise mm coordinates
- Layout adapts to question types automatically
- All outputs match Phase 1 schemas (template_layout.json)
- question_order.json schema inferred from requirements

## Next Steps

Remaining Phase 3 tools (not yet implemented):
- `imagescan` - Extract answers from scanned images
- `scorer` - Score extracted answers against correct answers

Then Phase 4 will focus on composition and end-to-end testing.
