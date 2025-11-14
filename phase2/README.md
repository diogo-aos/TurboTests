# Phase 2: Zero-Dependency Tools

Phase 2 implements the three core tools that have no dependencies on other tools in the pipeline. These tools are pure functions that transform input to output according to the data contracts defined in Phase 1.

## Implemented Tools

### 1. `gift2json` - GIFT Format Parser

Converts GIFT format question files to structured JSON matching the questions schema.

**Input:** `.gift` file (GIFT format text)
**Output:** `questions.json` (matching Phase 1 schema)

**Features:**
- Parses multiple choice, true/false, and short answer questions
- Tier-aware question type support (free/pro/enterprise)
- Auto-generates question IDs or uses custom titles
- Validates output against schema (when jsonschema available)
- Comprehensive error handling

**Usage:**
```bash
# Basic usage
python3 tools/gift2json.py fixtures/sample_questions.gift --output questions.json

# With tier and metadata
python3 tools/gift2json.py input.gift \
  --tier pro \
  --title "Midterm Exam" \
  --author "Dr. Smith" \
  --output questions.json

# Validate output
python3 tools/gift2json.py input.gift --validate --output questions.json
```

**Tier Support:**
- **Free:** multiple_choice, true_false
- **Pro:** + short_answer
- **Enterprise:** + essay, matching

### 2. `configgen` - Configuration Generator

Generates test configuration files with tier-aware settings and validation.

**Input:** Command-line parameters
**Output:** `config.json` (matching Phase 1 schema)

**Features:**
- Tier-based limits enforcement (versions, students, strategies)
- Distribution strategy configuration
- Template and personalization settings
- Student list generation or import
- Scanning configuration

**Usage:**
```bash
# Basic configuration
python3 tools/configgen.py \
  --title "Midterm Exam" \
  --versions 3 \
  --students 30 \
  --output config.json

# Advanced with tier features
python3 tools/configgen.py \
  --title "Final Exam" \
  --versions 5 \
  --students 50 \
  --tier pro \
  --strategy difficulty_balanced \
  --randomize-questions \
  --template branded \
  --output config.json

# Load students from file
python3 tools/configgen.py \
  --title "Quiz" \
  --versions 2 \
  --students 20 \
  --students-file students.csv \
  --output config.json
```

**Tier Limits:**
- **Free:** max 3 versions, 30 students, round_robin only, basic template
- **Pro:** max 10 versions, 100 students, random/difficulty_balanced, branded template
- **Enterprise:** unlimited, adaptive strategy, watermarked template

### 3. `report` - Results Report Generator

Generates human-readable reports from scoring results in multiple formats.

**Input:** `scores.json` (matching Phase 1 schema)
**Output:** HTML, Markdown, or PDF report

**Features:**
- Multiple output formats (HTML, Markdown)
- Tier-based analytics levels
- Responsive HTML with CSS
- Class statistics (pro/enterprise)
- Question analysis (enterprise)
- Grade distributions

**Usage:**
```bash
# HTML report
python3 tools/report.py scores.json \
  --format html \
  --output report.html

# Markdown report
python3 tools/report.py scores.json \
  --format markdown \
  --output report.md

# Pro tier with class statistics
python3 tools/report.py scores.json \
  --format html \
  --tier pro \
  --template detailed \
  --output report.html
```

**Tier Features:**
- **Free:** basic template, individual scores only, HTML/Markdown
- **Pro:** + class statistics, detailed template, mean/std dev, CSV export
- **Enterprise:** + question analysis, comprehensive template, visualizations, PDF

## Project Structure

```
phase2/
├── README.md                   # This file
├── tools/
│   ├── gift2json.py           # GIFT parser
│   ├── configgen.py           # Config generator
│   └── report.py              # Report generator
├── tests/
│   ├── test_gift2json.py      # Tests for gift2json
│   ├── test_configgen.py      # Tests for configgen
│   └── test_report.py         # Tests for report
└── fixtures/
    ├── sample_questions.gift  # Sample GIFT file
    ├── test_output.json       # Test output from gift2json
    ├── test_config.json       # Test output from configgen
    ├── test_report.html       # Test HTML report
    └── test_report.md         # Test Markdown report
```

## Testing

All tools have comprehensive unit tests. Run tests with:

```bash
# Run all Phase 2 tests
cd phase2/tests
python3 -m unittest discover -v

# Run individual tool tests
python3 test_gift2json.py
python3 test_configgen.py
python3 test_report.py
```

**Test Coverage:**
- 40 total tests
- 100% pass rate
- Tests cover:
  - Basic functionality
  - Tier restrictions and validation
  - Edge cases and error handling
  - Schema compliance
  - Integration with Phase 1 examples

## Design Principles

### 1. Zero Dependencies
These tools have no dependencies on other tools in the pipeline. They can be tested and used independently.

### 2. Tier-Aware
All tools enforce tier restrictions:
- Feature availability based on tier
- Validation of inputs against tier limits
- Clear error messages when tier limits exceeded

### 3. Schema Compliance
All outputs strictly match Phase 1 schemas:
- `gift2json` → `questions_schema.json`
- `configgen` → `config_schema.json`
- `report` uses `scores_schema.json`

### 4. Pure Functions
Tools are stateless transformations:
- Input → Processing → Output
- No side effects beyond file I/O
- Deterministic and testable

### 5. Unix Philosophy
- Each tool does one thing well
- Tools can be composed via pipes
- Text (JSON) as universal interface
- Tools work together via standard formats

## Examples

### End-to-End Workflow (Preview)

While Phase 2 tools can be used independently, here's how they'll eventually compose:

```bash
# 1. Convert GIFT to JSON
python3 tools/gift2json.py questions.gift --tier pro -o questions.json

# 2. Generate configuration
python3 tools/configgen.py \
  --title "Midterm" --versions 3 --students 30 \
  --tier pro -o config.json

# 3. [Phase 3: Generate PDFs - not yet implemented]
# python3 tools/docgen.py questions.json config.json --output pdfs/

# 4. [Phase 3: Scan and score - not yet implemented]
# python3 tools/imagescan.py scan.jpg --layout template_layout.json
# python3 tools/scorer.py scan_result.json question_order.json -o scores.json

# 5. Generate report
python3 tools/report.py scores.json --format html -o report.html
```

## Next Steps

Phase 3 will implement the dependent tools:
- `docgen` - Generate test PDFs (depends on questions.json + config.json)
- `imagescan` - Extract answers from scans (depends on template_layout.json)
- `scorer` - Score extracted answers (depends on scan_result.json + question_order.json)

## Notes

- All tools include `--help` for detailed usage information
- Tools validate inputs and provide clear error messages
- Tier enforcement prevents accidental usage of premium features
- Tests can be run independently or as a suite
- Tools are compatible with Python 3.6+
