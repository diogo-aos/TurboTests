
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
