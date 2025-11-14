
Creating and scanning tests for automatic scoring. Separate answer sheets are used.

# Lifecycle
## Production
1. Input: Questions in GIFT format.
2. Convert questions to structured format (e.g. JSON).
3. Input: Configuration for test creation (e.g. JSON)
	1. How many versions to produce
	2. How many students
	3. Test header
	4. etc.
4. From structured questions, configuration and Typst template, create Typst documents for each student (distribute students by versions).
	- The document should have a unique identifier for scanning.
	- Save a structured file with the correspondence (student-id).
	- Save a structured file with the order of questions and answers for each student (this will be needed for scoring)
5. Render the Typst documents

## Scanning
1. Input: Image of the test filled (photo, scan, etc.)
2. Scan and rectify (from markers) image.
3. Scan the questions from the rectified image.
4. Store the questions in a structured format, for each student.
5. Score the questions and output report in structured format
	1. Cross check the question scans with the stored structured file with student-question correspondence.
6. Optionally, produce report in human readable format (e.g. using pandoc).


## Assets
- Typst jinja2 template with markers for scanning and rectification


## Dependencies
- Typst
- opencv?
- pandoc?
- ...


# UNIX philosophy - Modular Tools (Each Does One Thing)

**1. `gift2json`** — Parse GIFT format → JSON questions

- Input: `.gift` file
- Output: `questions.json`
- No side effects, pure transformation

**2. `configgen`** — Create test configuration

- Input: number of versions, students, options
- Output: `config.json` with distribution strategy
- Simple config builder

**3. `docgen`** — Generate test PDFs

- Input: `questions.json` + `config.json`
- Output: PDFs + `student_mapping.json` + `question_order.json`
- One job: render documents

**4. `imagescan`** — Process scanned image → extract answers

- Input: image file (+ reference `question_order.json`)
- Output: `scan_result.json` with extracted answers + confidence
- Pure image processing, no scoring logic

**5. `scorer`** — Score answers

- Input: `scan_result.json` + `question_order.json`
- Output: `scores.json`
- Only knows how to compare answers

**6. `report`** — Format results for humans

- Input: `scores.json`
- Output: HTML/markdown/PDF report
- Presentation only, no logic

## Composition Example

```bash
# Create tests
gift2json questions.gift | \
  configgen --versions 3 --students 30 | \
  docgen --template template.typ --output ./pdfs

# Scan and score
for image in scans/*.jpg; do
  imagescan "$image" --reference question_order.json
done | \
  scorer --answer-key question_order.json | \
  report --format html --output results.html
```

Or a simple shell orchestrator script ties them together.

## Benefits

- **Testable**: each tool tested independently with fixtures
- **Reusable**: swap any component (e.g., different scanner, different report format)
- **Debuggable**: inspect JSON between stages
- **Extensible**: add new tools without touching existing ones
- **Flexible**: users can use pieces individually or chain them

Would you want me to rewrite the Phase 1-5 prompts using this modular structure instead?

## Revised version of imagescan

> The imagescan needs more than the image. To extract the answers, it needs some sort of layout configuration, no?

**Exactly right.** Good catch.

`imagescan` needs:

- Where the registration marks are
- Where each answer field is located (pixel coordinates)
- Answer field type (circle, box, text line, etc.)
- Image resolution/DPI expectations
- Fill thresholds

This should be a **separate configuration file** produced by `docgen`.

## Revised Structure

**`docgen`** now outputs two things:

1. PDFs (as before)
2. **`template_layout.json`** — describes the template geometry

```json
{
  "registration_marks": [[10, 10], [10, 287], [200, 10], [200, 287]],
  "version_id_field": {"x": 20, "y": 20, "width": 40, "height": 10},
  "student_id_field": {"x": 160, "y": 20, "width": 40, "height": 10},
  "questions": [
    {
      "question_id": "q1",
      "type": "multiple_choice",
      "answer_fields": [
        {"label": "A", "x": 30, "y": 50, "radius": 5},
        {"label": "B", "x": 60, "y": 50, "radius": 5}
      ]
    }
  ],
  "dpi": 300
}
```

**`imagescan`** input becomes:

```
imagescan image.jpg --layout template_layout.json
```

## Updated Pipe

```bash
docgen questions.json config.json --output ./pdfs
# outputs: pdfs/ + template_layout.json + question_order.json

for image in scans/*.jpg; do
  imagescan "$image" --layout template_layout.json
done | \
  scorer --answer-key question_order.json | \
  report --format html
```

This way `imagescan` is **reusable** across different test templates, and the layout is **testable/debuggable** as a first-class artifact.


# Granular parameters in the core tools

> To allow me to experiment with different models for feature tears, what more knobs could be introduced in the core tools?


Excellent idea. Make the tools **data-driven** so you can experiment with tiers by adjusting config, not code. Here's what I'd add:

## Feature Knobs by Tool

### `gift2json`

```json
{
  "question_types_supported": ["multiple_choice", "short_answer", "essay", "matching"],
  "allow_question_metadata": true,
  "allow_custom_attributes": true,
  "allow_difficulty_tagging": true,
  "allow_standards_mapping": true,
  "max_questions": null
}
```

**Tier experiment:**

- Free: `question_types_supported: ["multiple_choice"]`
- Pro: `+ "short_answer"`
- Enterprise: all types + custom attributes

### `configgen`

```json
{
  "distribution_strategies": ["round_robin", "random", "difficulty_balanced", "adaptive"],
  "allow_randomize_questions": true,
  "allow_randomize_options": true,
  "allow_difficulty_balancing": true,
  "allow_type_balancing": true,
  "version_limits": null
}
```

**Tier experiment:**

- Free: `distribution_strategies: ["round_robin"]` only
- Pro: `+ ["random", "difficulty_balanced"]`
- Enterprise: all + adaptive balancing

### `docgen`

```json
{
  "templates_available": ["basic", "branded", "watermarked"],
  "allow_student_name_personalization": false,
  "allow_student_photo": false,
  "allow_custom_header_footer": false,
  "allow_timestamp_embedding": false,
  "allow_qr_code_students": false,
  "registration_mark_density": "standard",
  "max_marker_configs": null
}
```

**Tier experiment:**

- Free: `templates_available: ["basic"]`, all personalization `false`
- Pro: `+ "branded"`, `allow_student_name_personalization: true`
- Enterprise: all + `allow_student_photo`, `allow_timestamp_embedding`

### `imagescan`

```json
{
  "ocr_engines_available": ["pytesseract"],
  "confidence_threshold_adjustable": false,
  "noise_tolerance_levels": ["standard"],
  "marker_detection_strategies": ["corner_only"],
  "allow_partial_scans": false,
  "allow_batch_duplicate_detection": false,
  "max_scans_parallel": 1
}
```

**Tier experiment:**

- Free: single OCR, fixed threshold, `max_scans_parallel: 1`
- Pro: `confidence_threshold_adjustable: true`, `max_scans_parallel: 4`, `noise_tolerance_levels: ["relaxed", "standard"]`
- Enterprise: multiple OCR engines, `allow_partial_scans: true`, `max_scans_parallel: 16`

### `scorer`

```json
{
  "scoring_models": ["basic_correct_incorrect"],
  "allow_partial_credit": false,
  "allow_question_weighting": false,
  "allow_curved_grading": false,
  "allow_rubric_selection": false,
  "confidence_penalty_enabled": false,
  "grade_distributions_available": 1
}
```

**Tier experiment:**

- Free: `scoring_models: ["basic_correct_incorrect"]` only
- Pro: `+ allow_partial_credit`, `+ allow_question_weighting`, multiple `grade_distributions_available: 3`
- Enterprise: all + `allow_rubric_selection`, `allow_curved_grading`

### `report`

```json
{
  "report_templates_available": ["basic_pdf"],
  "analytics_level": "none",
  "include_metrics": ["score", "grade"],
  "export_formats": ["pdf"],
  "visualization_types": [],
  "include_item_analysis": false,
  "include_learning_curves": false,
  "include_peer_comparison": false,
  "class_report_enabled": false
}
```

**Tier experiment:**

- Free: `analytics_level: "none"`, `export_formats: ["pdf"]`, `include_metrics: ["score", "grade"]`
- Pro: `analytics_level: "basic"`, `+ export_formats: ["csv", "html"]`, `+ include_metrics: ["mean", "std_dev"]`, `class_report_enabled: true`
- Enterprise: `analytics_level: "advanced"`, all formats, all metrics, `+ visualization_types: ["histogram", "scatter"]`, all analytics

## Master Tier Configuration

New top-level file: `tier_config.json`

```json
{
  "tiers": {
    "free": {
      "gift2json": { "question_types_supported": ["multiple_choice"] },
      "configgen": { "distribution_strategies": ["round_robin"] },
      "docgen": { "templates_available": ["basic"] },
      "imagescan": { "ocr_engines_available": ["pytesseract"] },
      "scorer": { "scoring_models": ["basic_correct_incorrect"] },
      "report": { "analytics_level": "none", "export_formats": ["pdf"] }
    },
    "pro": {
      "gift2json": { "question_types_supported": ["multiple_choice", "short_answer"] },
      "configgen": { "distribution_strategies": ["round_robin", "random", "difficulty_balanced"] },
      "docgen": { "templates_available": ["basic", "branded"], "allow_student_name_personalization": true },
      "imagescan": { "confidence_threshold_adjustable": true, "max_scans_parallel": 4 },
      "scorer": { "scoring_models": ["basic_correct_incorrect", "partial_credit"], "allow_question_weighting": true },
      "report": { "analytics_level": "basic", "export_formats": ["pdf", "csv", "html"], "class_report_enabled": true }
    },
    "enterprise": {
      "gift2json": { "allow_custom_attributes": true, "allow_standards_mapping": true },
      "configgen": { "distribution_strategies": ["round_robin", "random", "difficulty_balanced", "adaptive"] },
      "docgen": { "templates_available": ["basic", "branded", "watermarked"], "allow_student_photo": true },
      "imagescan": { "ocr_engines_available": ["pytesseract", "tesseract_v5", "paddle_ocr"], "allow_partial_scans": true },
      "scorer": { "allow_curved_grading": true, "allow_rubric_selection": true },
      "report": { "analytics_level": "advanced", "include_learning_curves": true }
    }
  }
}
```

## Implementation Pattern

Each tool gets a `--tier` flag or loads from env:

```bash
gift2json questions.gift --tier pro --config tier_config.json

# Or Python API:
gift2json(gift_file, tier="pro", tier_config=load_json("tier_config.json"))
```

Each tool **validates** against its tier config at startup:

```python
def gift2json(gift_file, tier="free", tier_config=None):
    config = tier_config["tiers"][tier]["gift2json"]
    
    # Parse
    questions = parse_gift(gift_file)
    
    # Validate: reject unsupported types
    for q in questions:
        if q.type not in config["question_types_supported"]:
            raise ValueError(f"Tier '{tier}' doesn't support {q.type}")
    
    return questions
```

## Benefits

✅ **Experiment in seconds** — just edit `tier_config.json`, re-run pipeline  
✅ **A/B test tiers** — run same workflow with different configs  
✅ **No code changes** — business logic stays in config  
✅ **Audit trail** — `tier_config.json` in git shows pricing history  
✅ **Easy to add tiers** — add `"startup": {...}` tier without touching tools  
✅ **Transparent** — users can see exactly what their tier includes

## Experiment Ideas

- **"Scanner quality"**: Free gets single OCR + low confidence threshold; Pro gets multiple OCR engines + adjustable thresholds
- **"Analytics depth"**: Free gets scores; Pro gets item difficulty; Enterprise gets learning curves
- **"Distribution fairness"**: Free gets round-robin; Pro/Enterprise get adaptive balancing
- **"Time-to-results"**: Free scans sequentially (1 at a time); Pro gets 4 parallel; Enterprise unlimited
- **"Personalization"**: Free generic tests; Pro adds student names; Enterprise adds photos + watermarks


