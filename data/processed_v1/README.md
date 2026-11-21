# Processed v1 outputs

All generated files are in `processed_v1`; source files were read-only and were not extracted or modified.

## Output files

- `SCHEMA.md`: CSV/backup columns and row counts; JSON/JSONL keys and examples; ZIP member counts; text document inventory and examples. Includes CUAD as contextual schema only.
- `manifest.csv`: one row per candidate inventory document with `contract_year`. Uses unpacked files when present and streams remaining content directly from the ZIP; SHA-256 and decoded character length are calculated from the actual bytes.
- `clean_loans.csv`: LIKELY_LOAN_AGREEMENT, primary_contract=1, canonical SHA-256 copy, and at least 5,000 characters; company-grouped split included.
- `gold_extra.csv`: human-verified gold documents outside the clean filters, explicitly retained in test as gold_extra.
- `filter_report.md`: independent and exclusive filter removal counts plus split counts and company-overlap checks.
- `annotations_normalized.csv`: merged rows from the 21 per-document review CSVs; field aliases normalized, review statuses casefolded and separator-normalized, and source field/value retained.
- `field_mapping.csv`: observed input field-name to canonical field-name mapping.
- `quality_report.md`: encoding, size, boilerplate, language heuristics, and shortest/longest document reports.
- `annotation_sheets/key_info_sheet.csv`: 60 test documents in the 30,000-400,000 character range, stratified by contract year, with 16 requested fields.
- `annotation_sheets/risk_clause_sheet.csv`: about 1,500 relevant clauses from those 60 documents, filtered by main-control ranges or risk-keyword matches and balanced across documents; label columns blank.
- `annotation_sheets/qa_sheet.csv`: four blank QA rows for each of 30 selected test documents.
- `CHANGES.md`: requested changes, deduplication effect, gold extras, sample counts, and clause counts per document.
- `processing_errors.log`

## Final counts

- Manifest documents: 18508
- Clean documents: 11901
- Train documents: 8330
- Validation documents: 1786
- Test documents: 1785
- Human-verified documents identified: 3
- Clean gold-reviewed documents forced to test: 2
- Gold-extra documents in test: 1
- Documents added back by canonical hash deduplication: 168
- Documents in repeated SHA-256 groups: 667
- Duplicate-flagged documents: 350
- Normalized review rows: 234
- Duplicate normalized rows removed: 39
- Repeated SHA-256 groups: 317
- Observed field mappings: 17
- Annotation-sheet documents: 60
- Key-info rows: 960
- Risk-clause rows: 1500
- Risk clause target: 1500
- Minimum risk clauses per selected document: 4
- Maximum risk clauses per selected document: 27
- QA-sheet documents: 30
- Blank QA rows: 120
- Documents with encoding replacements: 1
- Empty documents: 0
- Documents under 5,000 characters: 94
- Boilerplate heuristic matches: 0
- Non-English heuristic matches: 0
- Train/validation company overlap: 0
- Train/test company overlap: 0
- Validation/test company overlap: 0

Document-level split assignment is deterministic (seed 42) and whole companies remain in one split. Companies containing records with the exact normalized status `source_verified` or `manual_verification` are assigned to test. No risk category, severity, rationale, question, answer, or human annotation value is generated.
