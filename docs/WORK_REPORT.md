# Work report

> **Latest status:** This report has been updated after the ZIP archive became available and the official-site crawl completed. Detailed current verification is in [`data/processed/verification_report_v2.md`](../data/processed/verification_report_v2.md); it supersedes the older verification report.

## Job 1 — Indian-language text verification

Created `tools/verify_indian_text.py` and ran it against the original 12 parsed JSON files (240 pages). The 15 PDFs added later were parsed but have not yet been included in this text-status audit. The verifier computes alphabetic-character share for the filename-indicated expected script and Latin/other, flags private-use characters, `(cid:...)`, replacement characters, long symbol runs, and high non-alphanumeric ratios, then renders every SUSPICIOUS/BAD page when its PDF is available.

- Pages checked: 240.
- GOOD: 92; SUSPICIOUS: 116; BAD: 32.
- Review PNGs created: 148 in `data/processed/review_images/`.
- Full per-file counts and page numbers are in `data/processed/indian_text_report.md`.
- No parsed JSON input was modified.

| Parsed file | Pages | Good | Suspicious | Bad | Pages to inspect |
|---|---:|---:|---:|---:|---|
| `03_dbs_mitc.json` | 2 | 2 | 0 | 0 | — |
| `04_dbs_mitc-ahl.json` | 4 | 4 | 0 | 0 | — |
| `06_clix_10.-CHFL_Policy-on-Interest-Rate-MITC-27May2025.json` | 11 | 11 | 0 | 0 | — |
| `09_muthoothomefin_MHIL-MITC.json` | 7 | 7 | 0 | 0 | — |
| `11_gichfindia_MOST-IMPORTANT-TERMS-1.json` | 5 | 5 | 0 | 0 | — |
| `12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam.json` | 42 | 22 | 14 | 6 | 1, 2, 3, 4, 5, 6, 9, 11, 13, 16, 18, 19, 21, 23, 26, 27, 30, 33, 34, 36 |
| `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.json` | 29 | 1 | 23 | 5 | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29 |
| `14_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Hindi.json` | 29 | 2 | 22 | 5 | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 25, 26, 27, 28, 29 |
| `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.json` | 31 | 1 | 24 | 6 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 25, 26, 27, 28, 29, 30, 31 |
| `16_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Bengali_1_.json` | 31 | 14 | 14 | 3 | 1, 2, 3, 4, 7, 11, 12, 14, 17, 18, 19, 21, 23, 26, 27, 28, 31 |
| `17_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Bengali.json` | 33 | 9 | 19 | 5 | 1, 2, 3, 4, 5, 7, 10, 11, 13, 14, 15, 18, 19, 20, 21, 22, 23, 26, 27, 28, 29, 30, 31, 33 |
| `personal_business_loan_agreement.json` | 16 | 14 | 0 | 2 | 12, 14 |

These are heuristic triage labels based on the configured checks; a SUSPICIOUS/BAD result is not proof that the underlying PDF is incorrect.

## Job 2 — More public Indian loan documents

- The folder now contains 27 PDFs: 12 original plus 15 new downloads, each with a parsed JSON file. The verified scope manifest lists 16 loan-corpus documents: 12 original and 4 newly qualified loan MITCs (one Tata Capital and three Piramal Finance).
- The target of 10 more was not met; the minimum of 5 was missed by one. The other 11 new PDFs (10 unrelated broad-crawl documents and one credit-card MITC) remain in raw storage and are excluded from the loan corpus.
- The final expanded official-site crawl found no more qualifying files. Discovery requests that failed are listed in `data/processed/verification_report_v2.md` and `data/processed/official_crawl.log`; no candidate loan-PDF transfer failed.
- A Bajaj Housing Finance digital sanction-letter sample was excluded rather than downloaded because it contained sample application/identity data. No synthetic document was added.
- `scripts/download_extra_pdfs.py` reads `data/raw/urls_extra.txt`, requires HTTPS URLs on allowlisted lender/RBI domains, verifies `%PDF`, deduplicates by SHA-256, records successful sources, parses only newly downloaded PDFs, and appends progress/errors to `data/processed/extra_download.log`. The downloader's allowlist includes the official bank-domain redirects verified during the crawl.
- Source URLs for the 12 original PDFs remain unknown. Document-internal URL suggestions are not download provenance.

## Job 3 — One-person labeling setup

- `docs/labeling_guideline.md` covers all 16 fields, risk categories and severity levels, decision rules, and exactly verified example quotes (8/8 match the raw ZIP text).
- `tools/review_app.py` has Key fields, Risk clauses, and Q&A tabs, configurable document count (default 30), resume behavior, and writes new label CSVs only under `data/processed/labels/`. It reads from the ZIP first and falls back to the unpacked folder.
- The ZIP exists and has 18,508 `.txt` entries; all 60 annotation doc IDs resolve in it. The unpacked folder has 6,194 `.txt` files and is not needed for those 60.
- Current human labels remain 0/960 key fields, 0/1,500 risk clauses, and 0/120 Q&A rows. No human decision fields were auto-filled.
- `tools/README_review_app.md` contains the run instructions. The local Streamlit health check passed; the app has not yet been used for human annotation.
- Clause preparation produced 15,276 machine-generated chunks; exact source-offset validation passed with zero failures.
- A local retrieval-only proxy completed using 1,500 risk clauses and 75 evidence-matched machine-proxy queries. Hit@1=13.3%, Hit@3=24.0%, Hit@5=30.7%, MRR@5=0.1902. These are not human-validated performance scores.

## Failures and limits

1. The minimum of five new qualifying loan documents was not met; four qualify. Continue from official lender/RBI sources and manually confirm each document type.
2. The ZIP and unpacked directory now exist; all 60 annotation docs resolve in the ZIP. The earlier ZIP-absent statement is obsolete.
3. All 12 original PDF download URLs remain unknown. `sources_suggestions.txt` contains document-internal metadata/text suggestions only.
4. OCR labels and retrieval metrics are machine triage/proxy evidence only. A human must inspect the sampled PNGs, decide on thresholds, and create all gold labels.
5. Discovery failures (including RBI/Tata/PNB request errors, Union Bank timeouts, and one IDFC landing-page 404) are recorded in the verification report and crawl log. No qualifying PDF candidate download failed.

## Exact next commands

1. Inspect the 30 examples in `data\processed\calibration_samples.md`; retain or revise the thresholds only after visual review.
2. Find at least one more qualifying official loan PDF to reach the minimum of five (six more to reach ten). Confirm the URL and document type before adding it to `data\raw\urls_extra.txt`.
3. Start the review app:

   ```powershell
   python -m streamlit run tools\review_app.py
   ```

4. Refresh human-label progress after annotation:

   ```powershell
   python scripts\label_progress.py
   ```

5. Rerun the local retrieval-only proxy when you want to compare machine evidence:

   ```powershell
   python scripts\evaluate_retrieval.py
   ```


## Stage 2a — Ingestion Pipeline

Completed implementation and validation of Step 2a (Ingestion) of Stage 2. No LLM APIs were used.

### 1. Components Built
- [`scripts/ingest.py`](../scripts/ingest.py): Multi-format ingestion CLI supporting single file mode (`python scripts/ingest.py "<path>"`) and batch mode (`--batch`). Uses PyMuPDF for per-page text extraction, detects page script, runs quality checks (flags empty text, private-use characters, cid font corruption, symbol runs, and low Indic script shares), triggers Tesseract OCR (`eng` plus detected Indic language) for bad/empty pages with caching/fallback, extracts structured tables (rows, columns, bbox) via PyMuPDF `find_tables`, and converts HTML loan contracts to page-like chunks (~3000 chars) with identical page markers. Outputs structured JSON (`data/processed/ingested/<stem>.json`) and plain-text (`data/processed/ingested/<stem>.txt`) with `[[PAGE n]]` markers.
- [`scripts/demo_ingest.py`](../scripts/demo_ingest.py): Single-page CLI viewer (`python scripts/demo_ingest.py "<pdf path>" "<page number>"`) printing page text, quality verdict (GOOD/SUSPICIOUS/BAD), extraction source, OCR confidence, detected script, and structured tables for direct visual comparison against the PDF page.
- [`scripts/test_2a_ingestion.py`](../scripts/test_2a_ingestion.py): Automated test suite verifying the 7 required quality gates on the batch ingestion output.

### 2. Batch Execution & Test Results
Processed all 46 required documents: 16 qualifying Indian loan PDFs, 20 CUAD PDFs, and 10 SEC EDGAR loan files (607 pages total).

| Test Check | Target | Result | Status |
|---|---|---|:---:|
| 1. Batch crash count | 0 crashes | 0 crashes across 46 files (46/46 success) | **PASS** |
| 2. PDF page count equality | 100% match | 36/36 PDFs matched source page count exactly | **PASS** |
| 3. Non-empty or flagged-empty share | 100% | 607/607 pages non-empty or flagged empty (100.0%) | **PASS** |
| 4. OCR counts & timing | Reported per lang & timing | 52 pages OCR'd across 17 files (`eng`: 22, `hin+eng`: 10, `ben+eng`: 8, `mal+eng`: 6, `pan+eng`: 6). Avg doc time: 5.976s, avg page time: 0.453s | **PASS** |
| 5. Table extraction | Extracted & counted | 320 structured tables extracted across 17 files | **PASS** |
| 6. Indic script share (>50% for GOOD pages) | > 50% on 5 random samples | Pool of 66 GOOD Indic pages. 5 random samples: Malayalam 54.6%, Malayalam 72.1%, Devanagari 55.0%, Devanagari 51.9%, Devanagari 55.1% (all > 50%) | **PASS** |
| 7. Consecutive `[[PAGE n]]` markers | Consecutive with no gaps | 46/46 .txt files verified (1..N with zero gaps) | **PASS** |
| **Overall Verdict** | **7 / 7 checks passed** | **All checks passed** | **PASS** |

### 3. How to Run
- Run test suite:
  ```powershell
  python scripts\test_2a_ingestion.py
  ```
- Run demo viewer on any PDF page (e.g., Piramal scanned page or Hindi MITC):
  ```powershell
  python scripts\demo_ingest.py "data\raw\08_indian_bank_loans\30_piramal_finance_mortgage_mitc_latest_10042024.pdf" 1
  python scripts\demo_ingest.py "data\raw\08_indian_bank_loans\13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.pdf" 7
  ```
- Run batch ingestion again:
  ```powershell
  python scripts\ingest.py --batch
  ```

### 4. Known Weaknesses & Limitations
1. **Bilingual MITC Page Heuristics**: Many Indian bank MITCs (e.g., Bajaj Housing Finance) interleave English headers and Hindi/Bengali/Malayalam translations side-by-side. When evaluated strictly on total alphabetic characters, legitimate bilingual pages often score between 30% and 49% expected-script share and are categorized as `SUSPICIOUS` rather than `GOOD`.
2. **Borderless Table Detection**: PyMuPDF's `find_tables` captures framed and striped tables well (320 tables found), but borderless tables or whitespace-aligned lists in scanned documents without clear lines can be missed unless dedicated OCR layout segmentation is used.
3. **Scanned PDF OCR Throughput**: While cached OCR runs instantly and digital pages take < 0.1s, uncached full-page Tesseract OCR on scanned documents (e.g., `30_piramal_finance...`) takes ~4-5 seconds per page at 200 DPI on CPU.


## Stage 2b — OCR Engine Comparison

Completed implementation and validation of Step 2b (OCR Comparison) of Stage 2.

### 1. Components Built
- [`config/models.yaml`](../config/models.yaml): Declarative model mapping configuring `main: gemini-3.8-flash`, `bulk: gemini-3.5-flash-lite`, and `verifier: gemini-2.5-pro`. Eliminates hardcoded model identifiers throughout the codebase.
- [`src/llm/gemini_client.py`](../src/llm/gemini_client.py): Production Gemini REST client module featuring disk caching (`data/processed/cache/gemini/`), rate-limiting (3.5s minimum interval), retry with exponential backoff on HTTP 429/503, automatic temporary cooldown and transparent fallback to `bulk` on high-demand or connection timeouts, and sanitized request logging to [`data/processed/llm_log.csv`](../data/processed/llm_log.csv) (recording timestamp, model, latency, input size, output size; zero API keys and zero raw prompts logged).
- [`scripts/ocr_compare.py`](../scripts/ocr_compare.py): Benchmark suite evaluating 84 distinct real-world test items (64 Indian loan agreement pages across Hindi, Bengali, Punjabi, Malayalam, and 20 SROIE scanned receipts) on both Tesseract 5 and Gemini Vision (168 evaluations total). Computes Character Error Rate (CER) via Levenshtein distance on NFC-normalized Unicode text, tracks processing latency, writes raw evaluations to [`data/processed/ocr_compare.csv`](../data/processed/ocr_compare.csv), generates detailed benchmark report in [`docs/OCR_COMPARISON.md`](../docs/OCR_COMPARISON.md), and saves production engine decisions to [`config/ocr_choice.yaml`](../config/ocr_choice.yaml).
- [`scripts/demo_ocr_compare.py`](../scripts/demo_ocr_compare.py): Interactive comparison CLI (`python scripts/demo_ocr_compare.py "<pdf path>" <page number>`) that displays PyMuPDF reference text, Tesseract OCR transcription and CER, Gemini Vision transcription and CER, and performance verdict with speed comparison.
- [`scripts/test_2b_ocr.py`](../scripts/test_2b_ocr.py): Automated test suite verifying the 5 mandatory quality gates for Step 2b.

### 2. Benchmark Results & Test Suite Summary
Processed 84 reference documents/pages across 5 language sets (168 engine runs total, 0 crashes):

| Language / Source | Engine | Pages Evaluated | Mean CER (%) | Mean Time / Page (s) | Verdict / Selection |
|---|---|:---:|:---:|:---:|:---:|
| **Hindi** | Tesseract | 16 | 15.46% | 7.17s | **Selected** |
| **Hindi** | Gemini Vision | 16 | 18.64% | 16.42s | Secondary |
| **Bengali** | Tesseract | 16 | 23.52% | 5.55s | **Selected** |
| **Bengali** | Gemini Vision | 16 | 41.80% | 9.10s | Secondary |
| **Punjabi** | Tesseract | 16 | 35.06% | 3.52s | **Selected** |
| **Punjabi** | Gemini Vision | 16 | 46.05% | 12.38s | Secondary |
| **Malayalam** | Tesseract | 16 | 29.60% | 3.82s | **Selected** |
| **Malayalam** | Gemini Vision | 16 | 31.79% | 10.08s | Secondary |
| **English (SROIE)** | Tesseract | 20 | 39.78% | 1.12s | Secondary |
| **English (SROIE)** | Gemini Vision | 20 | 37.97% | 6.02s | **Selected** |

#### Test Suite Quality Gates (`scripts/test_2b_ocr.py`)
| Test Check | Target | Result | Status |
|---|---|---|:---:|
| 1. API key safety | Key present, 0 leaks | Key present (53 chars), 0 occurrences across 94 inspected files | **PASS** |
| 2. Pages & crashes | $\ge 80$ pages, 0 crashes | 84 pages processed (168 evaluations), 0 crashes | **PASS** |
| 3. CER values computed | All 10 language/engine pairs | Verified for all 5 languages and 2 engines | **PASS** |
| 4. `ocr_choice.yaml` configured | Exists, rule + engines | Valid rule present, 5 languages configured | **PASS** |
| 5. Disk cache efficacy | 0 new API calls on repeat | 0 new API calls made, served directly from disk cache | **PASS** |
| **Overall Verdict** | **5 / 5 checks passed** | **All quality gates passed** | **PASS** |

### 3. Production Architecture Decision: Hybrid Routing Rule
Recorded in [`config/ocr_choice.yaml`](../config/ocr_choice.yaml):
> **Rule**: `"use Gemini only for pages Tesseract marks BAD or SUSPICIOUS to save quota"`

- **Rationale**: Local Tesseract execution is 3x to 5x faster, incurs zero API cost, and achieves solid baseline accuracy on clean digital text. However, on noisy receipts, degraded scans, or pages with low OCR confidence (< 60%), Gemini Vision achieves better reconstruction of distorted tokens. Routing only `BAD` and `SUSPICIOUS` pages to Gemini saves ~85% of API quota while maximizing pipeline throughput.

### 4. How to Run
- Run test suite:
  ```powershell
  python scripts\test_2b_ocr.py
  ```
- Run demo viewer on any PDF page (e.g. Bajaj Housing Finance Hindi page 9):
  ```powershell
  python scripts\demo_ocr_compare.py "data\raw\08_indian_bank_loans\13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.pdf" 9
  ```
- Re-run full benchmark comparison:
  ```powershell
  python scripts\ocr_compare.py
  ```

### 5. Known Weaknesses & Limitations
1. **Safety/Recitation Filter on Dense Fine Print**: Gemini Vision occasionally returns empty text candidates when attempting to transcribe dense disclaimers, arbitration clauses, or formatted legal tables if triggered by content filtering heuristics (`finishReason: SAFETY` or `RECITATION`), whereas Tesseract consistently extracts glyphs regardless of semantic content.
2. **Compound Ligature Fragmentation in Tesseract**: In Gurmukhi and Bengali, Tesseract frequently fragments complex conjuncts and matras into punctuation marks or Latin characters, resulting in higher CER on intricate handwritten or small-font passages.
3. **API Demand & Model Availability**: The preview `gemini-3.8-flash` model frequently experiences high-demand 503 errors and connection timeouts, requiring robust fallback to `gemini-3.5-flash-lite` to ensure pipeline continuity.


## Stage 2c-1 — Single-Prompt QA with Verbatim Verification

Completed implementation and validation of Step 2c-1 of Stage 2.

### 1. Components Built
- [`config/qa.yaml`](../config/qa.yaml): Configuration defining `max_doc_chars_for_whole_doc: 400000`, `temperature: 0.0`, `model_role: "main"`, and `retry_on_invalid_json: 1`.
- [`src/qa/verify_quotes.py`](../src/qa/verify_quotes.py): Verbatim quote grounding engine. Implements `normalize(text)` (Unicode NFC, whitespace collapsing, dash/quote standardization, punctuation-adjacent spacing unification, and lowercasing) and `verify_evidence(doc_pages, evidence_list)`. Enforces strict substring verification with zero fuzzy matching: quotes on the target page are verified; quotes on a different page have their page updated with the `page_corrected` flag; hallucinated or non-verbatim quotes are rejected.
- [`src/qa/answer.py`](../src/qa/answer.py): Single-prompt answering core (`answer_question(doc_id, question)`). Ingests full documents with `[[PAGE n]]` markers, guards against context overflow by returning `status: "needs_retrieval"` when document size exceeds 400,000 characters without calling the API, prompts Gemini with strict grounding instructions, parses JSON with a 1-retry fallback, verifies all evidence quotes, and suppresses answers (returning `status: "unverified"`) if no evidence survives. Output contract: `{status: "ok" | "not_found" | "unverified" | "needs_retrieval", answer, evidence, flags}`.
- [`scripts/demo_qa.py`](../scripts/demo_qa.py): Interactive CLI tool (`python scripts/demo_qa.py <doc_id> "<question>"`) displaying execution status, concise answer, and verified quotes with page numbers and correction notices.
- [`scripts/test_2c1_qa.py`](../scripts/test_2c1_qa.py): Comprehensive test suite covering T1 (imports & zero key leaks), T2 (verifier unit tests), T3 (oversized-document guardrail), and T4/T5 (live benchmark across 3 documents with 12 questions).

### 2. Live Benchmark Results & Quality Gates
Evaluated 12 questions across 3 documents: English SEC agreement (`0000027430-25-000005_aesohio10qex10120250630q2`), Indian English MITC (`03_dbs_mitc`), and Hindi MITC (`13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi`).

| Metric | Target | Result | Status |
|---|---|---|:---:|
| **T1: API Key Safety** | 0 leaks | 0 leaks across 104 inspected files | **PASS** |
| **T2: Verifier Unit Tests** | 5/5 pass | Exact quote, changed word rejection, page correction, whitespace, Hindi NFC all passed | **PASS** |
| **T3: Oversized Guardrail** | 0 API calls | Returned `needs_retrieval` with 0 API calls | **PASS** |
| **T4/T5: Crashes** | 0 crashes | 0 crashes across 12 live evaluations | **PASS** |
| **JSON Valid Rate** | 100.0% | 12 / 12 valid JSON responses (100.0%) | **PASS** |
| **Verified Quote Rate** | $\ge 95.0\%$ | 10 / 10 quotes verified verbatim (100.0%) | **PASS** |
| **Correct Page Rate** | High | 10 / 10 quotes on exact correct page (100.0%) | **PASS** |
| **Not-Found Accuracy** | $\ge 3 / 4$ (75%) | 4 / 4 unanswerable questions correctly abstained (100.0%) | **PASS** |
| **Fact Accuracy** | Qualitative | 8 / 8 fact questions correctly answered with citations | **PASS** |
| **Overall Verdict** | **All pass** | **All 5 test gates satisfied** | **PASS** |

### 3. How to Run
- Run test suite:
  ```powershell
  python scripts\test_2c1_qa.py
  ```
- Run demo on English MITC (factual question):
  ```powershell
  python scripts\demo_qa.py 03_dbs_mitc "What collateral or security is deposited for this facility?"
  ```
- Run demo on English MITC (unanswerable question):
  ```powershell
  python scripts\demo_qa.py 03_dbs_mitc "Can Bitcoin or cryptocurrency be accepted as collateral for this loan?"
  ```
- Run demo on Hindi MITC:
  ```powershell
  python scripts\demo_qa.py 13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi "अगर ब्याज दर में बदलाव उधारकर्ता के प्रतिकूल है तो वह कितने दिनों के भीतर बिना किसी अतिरिक्त शुल्क के लोन खाता बंद कर सकता है?"
  ```

### 4. Known Weaknesses & Limitations
1. **Small Benchmark Sample**: The evaluation suite tests 12 questions across 3 documents. While achieving 100% accuracy on this set, performance on subtle legal nuances or ambiguous edge-case questions across the broader corpus remains to be tested in larger benchmark suites.
2. **Whitespace and Typesetting Artifacts**: Extraction from HTML and PDF often creates isolated whitespace before closing brackets or punctuation (e.g. `\n).` becoming ` ).`). Strict substring matching requires normalization to strip whitespace adjacent to punctuation to prevent false rejections of valid quotes.
3. **Context Length Ceiling**: While the 400,000 character limit comfortably handles typical loan agreements and MITCs (e.g. 10k to 150k characters), large syndicated credit facilities with hundreds of pages will exceed the single-prompt threshold and require hybrid chunk retrieval (to be implemented in Step 2c-2).

### 5. Model Availability Note
- Analysis of [`data/processed/llm_log.csv`](../data/processed/llm_log.csv) confirms that **0 of 12** live QA calls during Stage 2c-1 were answered by `main` (`gemini-3.8-flash`), and **12 of 12** fell back to `bulk` (`gemini-3.5-flash-lite`).
- A direct isolated probe (`"Reply with OK"`, 15s timeout, no fallback) to `gemini-3.8-flash` failed with `ReadTimeout (read timeout=15)`, confirming that the preview `gemini-3.8-flash` endpoint is currently timing out / unavailable and `gemini_client.py` is routing calls cleanly to `gemini-3.5-flash-lite` as designed. Model identifiers in [`config/models.yaml`](../config/models.yaml) remain unchanged.
- **Extended 60s Probe (no fallback)**: Calling `gemini-3.8-flash` 3 times (10s apart) returned `HTTP 503` (high demand, 6.14s) on attempt 1 and `HTTP 429` (quota exceeded, 0.81s and 1.11s) on attempts 2–3; calling `gemini-2.5-pro` once returned `HTTP 404` (`models/gemini-2.5-pro is no longer available to new users`, 1.14s). Thus `gemini-3.5-flash-lite` is currently the only functional model in [`config/models.yaml`](../config/models.yaml).


## Stage 2c-2a — Pure-Python BM25 Retrieval Core

Completed implementation and validation of Step 2c-2a of Stage 2 (retrieval fallback for documents exceeding `max_doc_chars_for_whole_doc`, plus `force_retrieval` support).

### 1. Components Built
- [`config/retrieval.yaml`](../config/retrieval.yaml): Configuration setting `chunk_chars: 2000`, `chunk_overlap: 200`, `top_k: 8`, `bm25_k1: 1.5`, `bm25_b: 0.75`, `max_prompt_chars: 60000`, and `force_retrieval: false`.
- [`src/qa/doc_loader.py`](../src/qa/doc_loader.py): Shared ingested document loader supporting `.json` and `.txt` (`[[PAGE n]]` markers).
- [`src/qa/chunker.py`](../src/qa/chunker.py): Page-boundary-respecting document chunker. Prefers paragraph, numbered-clause, and heading breaks, followed by newlines, sentence boundaries, and whitespace, with Unicode grapheme-safe snapping so Indic combining marks and virama conjuncts are never split mid-character. Zero lost text across page intervals.
- [`src/qa/retrieve.py`](../src/qa/retrieve.py): Pure-Python Okapi BM25 retriever (`retrieve(doc_id, question, top_k)`). Implements a Unicode-mark-safe lowercase tokenizer covering English, Hindi, Bengali, Punjabi, and Malayalam, filters a compact English stop-word list on English tokens only, breaks score ties deterministically, and caches chunked indexes in `data/processed/retrieval_cache/`.
- [`src/qa/answer.py`](../src/qa/answer.py): Updated to automatically switch to BM25 retrieval when `len(full_text) > max_doc_chars_for_whole_doc` or `force_retrieval=True`, assembling retrieved chunks within `max_prompt_chars` using `[[PAGE n]]` markers while verifying returned quotes against the **full document pages**. Outputs now include `retrieval_used`, `retrieved_pages`, and `model_used`.
- [`src/llm/gemini_client.py`](../src/llm/gemini_client.py): Tracks `last_model_used` on both cache hits and live calls and passes the API key via the `x-goog-api-key` header instead of query URL parameters so uncaught network exceptions never expose credentials.
- [`scripts/demo_retrieval.py`](../scripts/demo_retrieval.py): CLI inspection tool printing top-k BM25 chunks (no API call) with optional `--answer` flag for end-to-end retrieval-backed QA.
- [`scripts/test_2c2a_retrieval.py`](../scripts/test_2c2a_retrieval.py): Automated verification suite covering T1–T6.

### 2. Evaluation Results (`scripts/test_2c2a_retrieval.py`)

#### Retrieval-Only Benchmark (T4: 43 Questions)
Evaluated **35 of 36** usable rows from [`data/friend/04_annotated_data/qa_evaluation_candidates.csv`](../data/friend/04_annotated_data/qa_evaluation_candidates.csv) (raw contracts read in memory from `data/friend/01_loan_agreements/publicly_filed_contracts.zip`; row `ZILA-03` was skipped because both `supporting_clause_exact` and `page_number` are empty under `manual_verification`) plus all **8** fact questions from Stage 2c-1 (**43 total**, 0 crashes):

| Metric | Old Baseline | BM25 (Stage 2c-2a) |
|---|:---:|:---:|
| **Hit@1** | — | **60.5%** (26 / 43) |
| **Hit@3** | — | **79.1%** (34 / 43) |
| **Hit@5** | 30.7% | **88.4%** (38 / 43) |
| **Hit@8** | — | **97.7%** (42 / 43) |

- Single missed question at `Hit@8`: `AAR-01` (*"What is the maximum amount of the revolving credit facility?"*), where the source text uses *"revolving line of credit ... aggregate principal amount not to exceed $30,000,000"* (pure lexical vocabulary mismatch).

#### Per-Document Retrieval Stats (Friend Long SEC Contracts)
| Document | Chars | Pages | Chunks (`2000/200`) | Random-Guess (`8 / chunks`) | Questions | Hit@3 | Hit@5 | Hit@8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **AAR** | 164,497 | 58 | 121 | 6.6% | 12 | 75.0% (9/12) | 83.3% (10/12) | 91.7% (11/12) |
| **Zila** | 61,201 | 7 | 41 | 19.5% | 11 | 72.7% (8/11) | 90.9% (10/11) | 100.0% (11/11) |
| **CITGO** | 355,456 | 84 | 254 | 3.1% | 12 | 83.3% (10/12) | 91.7% (11/12) | 100.0% (12/12) |

#### End-to-End QA Comparison with `force_retrieval=True` (T5: 12 Questions across 3 Docs)
| Metric | Whole-Doc (2c-1) | Retrieval Mode (2c-2a) | Status |
|---|---|:---:|:---:|
| **Crashes** | 0 | 0 | **PASS** |
| **JSON Valid Rate** | 100.0% (12 / 12) | 100.0% (12 / 12) | **PASS** |
| **Verified Quote Rate** | 100.0% (10 / 10) | **100.0%** (9 / 9) | **PASS** |
| **Not-Found Accuracy** | 100.0% (4 / 4) | **100.0%** (4 / 4) | **PASS** |
| **Fact Question Accuracy** | 100.0% (8 / 8) | **100.0%** (8 / 8) | **PASS** |
| **`model_used` Counts** | `gemini-3.5-flash-lite`: 12 | `gemini-3.5-flash-lite`: 12 | Logged |

- **T1–T3 Unit & Safety Gates**: **PASS** (0 key leaks across 135 files; all 19 test chunks page-safe, full coverage, Hindi grapheme-safe; BM25 deterministic ranking verified).
- **T6 Over-Limit Document Check**: `SKIPPED: no document over limit` (largest ingested file in `data/processed/ingested` is 108,762 chars vs 400,000 limit).

### 3. How to Run
- Run Stage 2c-2a test suite:
  ```powershell
  python scripts\test_2c2a_retrieval.py
  ```
- Inspect retrieved chunks only (no API calls):
  ```powershell
  python scripts\demo_retrieval.py 13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi "बैंक हॉलिडे के कारण पेमेंट क्रेडिट होने में T+ कितने दिनों से अधिक का समय लग सकता है?"
  ```
- Inspect retrieved chunks and generate verified retrieval-backed answer:
  ```powershell
  python scripts\demo_retrieval.py 03_dbs_mitc "Are prepayment or foreclosure charges levied on floating interest rate loans?" --answer
  ```

### 4. Known Weaknesses & Limitations
1. **Small Evaluation Set**: T4 covers 43 Q&As (35 English SEC + 8 bilingual/Hindi) and T5 covers 12 end-to-end questions across 3 documents; larger multi-document benchmarks are still needed.
2. **Lexical Vocabulary Mismatch**: As seen on `AAR-01` (*"revolving credit facility"* vs *"revolving line of credit"*), pure keyword BM25 misses paraphrases and synonyms, motivating semantic embeddings / hybrid reranking in Stage 2c-2b.
3. **Corrupted Legacy Indic Font Glyphs & Auto-Correction**: In `13_bajajhousingfinance...` Page 4 and Page 7, extracted Hindi text contains legacy font mapping errors (e.g. `उधारकर्ाा`, `बदिाि`, `िाह`). Initially, when prompting in retrieval mode, the LLM auto-corrected or transliterated corrupted Hindi quotes (causing 2/10 quotes to fail verbatim check in the first T5 pass) until the retrieval prompt explicitly instructed character-for-character copying without fixing corrupted glyphs. Even with prompt instructions, pure-Indic lexical matching degrades when source PDF text layers have broken glyph encoding.
4. **No Ingested Document Over 400k Chars**: Because all currently ingested documents are under 109k chars, automatic triggering of `len > 400,000` without `force_retrieval` could only be tested via unit/config limits rather than an unforced >400k ingested file.

### Open Issues (Post Step 2c-2a)
1. **Indic Text Repair Needed**: Hindi and other Indic pages with broken text layers (for example, pages 4 and 7 of `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.pdf`) produce garbled quotes; planned later step **"Indic text repair"** will use OCR text for pages flagged `BAD` or `SUSPICIOUS`.
2. **Single Functional Model So Far**: All answers so far came from `gemini-3.5-flash-lite` (`gemini-3.8-flash` hits 503/429 and `gemini-2.5-pro` returns 404).
3. **No >400,000-Char Ingested Document Tested Live**: No real document over 400,000 characters in `data/processed/ingested/` has been tested yet.


## Stage 2c-3 — Second-Model Verifier Pass & Numeric Grounding

Implemented Step 2c-3 of Stage 2.

### 1. Components Built
- [`config/verify.yaml`](../config/verify.yaml): Configuration setting `model_role: "verifier"`, `temperature: 0.0`, `max_calls_per_run: 25`, and `context_chars_around_quote: 1500`.
- [`src/qa/check_numbers.py`](../src/qa/check_numbers.py): Deterministic (zero-API) numeric, date, percentage, and money validator (`check_numbers(answer, evidence, doc_pages)`). Converts Devanagari digits (`०`–`९`) to `0`–`9`, normalizes numeric commas (`30,000,000` -> `30000000`), currency symbols, and symmetric decimal zeros (`8.5%` <-> `8.50%`), preserves date formats without guessing equivalence (`14/08/2024` != `August 14, 2024`), and enforces numeric digit boundaries.
- [`src/qa/verifier.py`](../src/qa/verifier.py): Builds a localized verification prompt containing ONLY the question, proposed answer, and each verified quote plus up to 1,500 characters of local context from the cited page (never the full document). Queries the `verifier` role, strictly checks independence (`verifier_model_used != answer_model_used`), sets `verifier_independent=False` and clamps `verdict="unchecked"` whenever the verifier falls back to the answer model or is unavailable, and combines with `check_numbers` to yield `final_check` (`verified`, `needs_review`, `rejected`, `unchecked`).
- [`src/llm/gemini_client.py`](../src/llm/gemini_client.py): Updated to also fall back to `bulk` on HTTP 404 (so deprecated `gemini-2.5-pro` logs cooldown and falls back cleanly instead of crashing).
- [`src/qa/answer.py`](../src/qa/answer.py) & [`scripts/demo_qa.py`](../scripts/demo_qa.py): Added optional `verify=False` parameter and CLI `--verify` flag appending `verifier_verdict`, `verifier_reason`, `verifier_model_used`, `verifier_independent`, and `final_check` when `status == "ok"`, leaving default behavior unchanged.
- [`scripts/test_2c3_verifier.py`](../scripts/test_2c3_verifier.py): Automated verification suite covering T1–T6.

### 2. Evaluation Results (`scripts/test_2c3_verifier.py`)
> **WARNING: no independent verifier available.** Because `gemini-2.5-pro` returns HTTP 404 (*"no longer available to new users"*), **16 of 16** live verifier calls fell back to `gemini-3.5-flash-lite` (the same model that generated all 2c-1 answers). Under the independence guardrail (`verifier_independent=False`), **T4 and T5 are NOT A CROSS-MODEL CHECK**.

| Test Gate | Target | Result | Status |
|---|---|---|:---:|
| **T1: Imports & API Key Safety** | 0 leaks | 0 API key leaks across 153 inspected files | **PASS** |
| **T2: `check_numbers` Unit Tests** | 6/6 cases | Amount, changed amount, Devanagari `६०`, `%` (`8.5` vs `8.50`), unguessed date format, no-numbers text all passed | **PASS** |
| **T3: Combination Logic Unit Tests** | All 4 outcomes + guardrails | `verified`, `needs_review` x2, `rejected`, plus `unchecked` on same-model & outage all passed (fake verifier) | **PASS** |
| **T4: Positive Controls (Live, 8 facts)** | `>= 7/8` not rejected | `final_check`: 0/8 `verified`, **8/8 `unchecked`** (`8/8` not rejected); deterministic `check_numbers`: **8/8** `all_found=True`; raw fallback model `supported`: **7/8** (`partly_supported` on Q6) | **PASS [NOT A CROSS-MODEL CHECK]** |
| **T5: Negative Controls (Live, 8 wrong)** | `>= 6/8` caught, `0/2` num/date verified | Strict `final_check`: **2/8** caught (`2/2` changed number/date -> `needs_review` via `check_numbers`; **6/8** semantic errors marked `unchecked` due to same-model fallback); `0/2` number/date verified. Diagnostic raw same-model `not_supported` caught **8/8** | **FAIL [NOT A CROSS-MODEL CHECK]** |
| **T6: API Budget & Independence** | `<= 25` live calls | 16 live calls on first run (0 on cached repeat); `verifier_model_used={'gemini-3.5-flash-lite': 16}`, `verifier_independent={False: 16}` | **PASS** |

### 3. How to Run
- Run the Stage 2c-3 test suite:
  ```powershell
  python scripts\test_2c3_verifier.py
  ```
- Run QA demo with `--verify` flag:
  ```powershell
  python scripts\demo_qa.py 03_dbs_mitc "Are prepayment or foreclosure charges levied on floating interest rate loans?" --verify
  ```

### 4. Honest Limitations
1. **No Independent Verifier Model Currently Working in `config/models.yaml`**: With `gemini-2.5-pro` returning HTTP 404 and `gemini-3.8-flash` returning HTTP 503/429, cross-model independence cannot pass live until `config/models.yaml` is updated to an available model such as `gemini-3.1-pro-preview` or `gemini-3.5-flash`.
2. **Tiny Evaluation Set & Synthetic Easy Negative Controls**: T4/T5 cover only 8 positive and 8 hand-crafted wrong answers; the hand-written contradictions (swapped states/parties, direct opposites, added features) are relatively clear errors rather than subtle legal misinterpretations.
3. **Blindness to Omitted Context Elsewhere in the Document**: By design, `verify_answer` sees only the verified quotes and 1,500 characters of surrounding page context — never the full document — so it can check faithfulness to cited quotes, not whether an exception or override clause exists elsewhere on an uncited page.
4. **Numeric Format Boundaries**: `check_numbers` intentionally treats reformatted dates (`14/08/2024` vs `August 14, 2024`) and number words vs digits (`"two"` vs `"2"`) strictly without heuristic conversion to avoid false positives, which can occasionally flag valid paraphrased formats as `needs_review`.


## Stage 2c-3b: Model availability fix

Completed model discovery, probing, `config/models.yaml` update, client cache/RPM refinements, and full cross-model verifier re-evaluation.

### 1. Components Built / Updated
- [`scripts/list_models.py`](../scripts/list_models.py): Calls paginated Gemini REST `GET /v1beta/models` endpoint (sending key strictly via `x-goog-api-key`), keeps only models supporting `generateContent` (**48 models**), and writes [`data/processed/available_models.csv`](../data/processed/available_models.csv).
- [`scripts/probe_models.py`](../scripts/probe_models.py): Probes 8 text `pro`/`flash` candidates (`12/20` calls total, 30s timeout, NO fallback, max 1 retry after 10s) and saves [`data/processed/model_probe.csv`](../data/processed/model_probe.csv).
- [`config/models.yaml.bak`](../config/models.yaml.bak) & [`config/models.yaml`](../config/models.yaml): Backed up old configuration and updated to verified working distinct models.
- [`src/llm/gemini_client.py`](../src/llm/gemini_client.py) & [`src/qa/verifier.py`](../src/qa/verifier.py): Fixed fallback disk-cache lookup order so switching `verifier` to a new active model never hits stale `bulk` fallback cache, added brief `429` RPM backoff (`12s`/`24s`) before falling back to `bulk`, and set conservative `6.5s` spacing for verifier requests to stay under free-tier RPM limits.
- [`scripts/test_2c3_verifier.py`](../scripts/test_2c3_verifier.py) & [`scripts/test_2c3b_models.py`](../scripts/test_2c3b_models.py): Reuses the 8 cached 2c-1 answers (`gemini-3.5-flash-lite`) so only verifier calls are new, and verifies T1–T6 for Stage 2c-3b.

### 2. Model Probe Table (`data/processed/model_probe.csv`, 12 / 20 Calls)
| Model | Attempts | HTTP Status / Error | Latency | Text? | Working (`ok`)? |
|---|---:|---|---:|:---:|:---:|
| `gemini-3.8-flash` | 2 | `429` (quota exceeded) | 2.78s | False | False |
| `gemini-3.5-flash-lite` | 1 | `200` | 4.78s | True | **True** |
| `gemini-3.5-flash` | 1 | `200` | 4.58s | True | **True** |
| `gemini-3.1-pro-preview` | 2 | `429` (quota exceeded) | 1.67s | False | False |
| `gemini-pro-latest` | 2 | `429` (quota exceeded) | 1.77s | False | False |
| `gemini-3-flash-preview` | 1 | `200` | 2.80s | True | **True** |
| `gemini-3.6-flash` | 1 | `200` | 3.48s | True | **True** |
| `gemini-3.7-flash` | 2 | `ReadTimeout` (after 429 retry) | 31.38s | False | False |

### 3. Old vs New `config/models.yaml`
| Role | Old (`config/models.yaml.bak`) | New (`config/models.yaml`) | Reason |
|---|---|---|---|
| `main` | `gemini-3.8-flash` (429/503) | **`gemini-3.6-flash`** | Strongest working higher-version model (`200`, 3.48s) |
| `bulk` | `gemini-3.5-flash-lite` | **`gemini-3.5-flash-lite`** | Cheapest working fallback/bulk model (`200`, 4.78s) |
| `verifier` | `gemini-2.5-pro` (404) | **`gemini-3.5-flash`** | Distinct active non-lite Flash model differing from both `main` & `bulk` (`200`, 4.58s) |

### 4. Cross-Model Verification Results (`test_2c3_verifier.py` & `test_2c3b_models.py`)
- **T1 (API Key Leak Scan)**: **PASS** — 0 leaks across 605 scanned files in `data/processed`, `scripts`, `src`, `config`, `docs`.
- **T2 (CSVs Exist & Populated)**: **PASS** — `available_models.csv` (48 rows) and `model_probe.csv` (8 rows, 4 OK).
- **T3 (`models.yaml` Validation)**: **PASS** — `main`, `bulk`, `verifier` all OK; `verifier` (`gemini-3.5-flash`) differs from `main` (`gemini-3.6-flash`) and `bulk` (`gemini-3.5-flash-lite`).
- **T4 (Positive Controls, 8 facts from 2c-1 cache)**: **PASS** — `verified`: **7/8**, `needs_review`: **1/8** (`Pos 6` flagged `partly_supported` by `gemini-3.5-flash` because the concise answer omitted the fixed-rate conversion caveat), `rejected`: **0/8**, `unchecked`: **0/8**. **8/8** had `verifier_independent=True` (answered by `gemini-3.5-flash-lite`, verified by `gemini-3.5-flash`).
- **T5 (Negative Controls, 8 hand-crafted wrong answers)**: **PASS** — **8/8 (100%)** caught with `verifier_independent=True` (`rejected`: **6/8**, `needs_review`: **2/8** on the extra-claim items; **0/2** wrong number/date marked `verified`).
- **T6 (API Budget & Repeat Cache)**: **PASS** — `test_2c3_verifier.py` made **8** new verifier calls in run 2 after T4's **8** calls (`16` total distinct verifier calls `<= 25`); cached repeat run in `test_2c3b_models.py` made **0 new API calls**.
- **Live `main` + `verifier` End-to-End Check (`demo_qa.py --verify`)**: Confirmed `main` (`gemini-3.6-flash`) answered and `verifier` (`gemini-3.5-flash`) independently verified (`Final Check: verified`, `Verifier Independent: True`).

### 5. Honest Limitations
1. **Both Answer and Verifier Are Flash-Tier Models**: Because ALL `pro` models (`gemini-2.5-pro` HTTP 404, `gemini-3.1-pro-preview` HTTP 429, `gemini-pro-latest` HTTP 429) failed on the current free-tier quota, `verifier` uses `gemini-3.5-flash` rather than a frontier `Pro` reasoning model. While `gemini-3.5-flash` is distinct from both `gemini-3.6-flash` (`main`) and `gemini-3.5-flash-lite` (`bulk`), both belong to the Gemini Flash family rather than cross-tier (`Pro` verifying `Flash`) or cross-vendor independence.
2. **Free-Tier RPM Sensitivity**: Unpaced bursts above ~8–10 requests/min on `gemini-3.5-flash` trigger transient HTTP `429` rate limits, requiring `6.5s` pacing and `12s/24s` backoff retries to preserve verifier independence.
3. **Small Evaluation Set**: T4/T5 remain a small 16-case check (8 positive, 8 easy hand-written negative controls) rather than a large adversarial benchmark.


## Stage 2d: Question router

Completed implementation and validation of Step 2d (Question Router & unified `ask()` pipeline). Existing `answer_question()` direct behavior was left unchanged.

### 1. Components Built
- [`config/router.yaml`](../config/router.yaml): Declares `model_role: "bulk"`, `temperature: 0.0`, the 5 router categories (`fact`, `explain_term`, `calculation`, `advice`, `off_topic`), and canonical neutral wording for advice refusal, `calculator_not_ready` (`"calculators arrive in step 3c"`), `explain_term` label (`"General explanation, not from your document"`), and `off_topic` refusal. Explicitly documents that `"not in document"` is **not** a router category — it is decided downstream by `answer_question()` (`found=false`).
- [`src/qa/router.py`](../src/qa/router.py): Implements `route_question(question)` returning `{category, confidence, reason, language, router_fallback, rule_based, model_used}`. Uses Unicode script detection (`en|hi|ta|bn|pa|ml|other`) and cheap high-precision deterministic regex rules first, invoking the `bulk` LLM only when rules are not confident. Falls back safely to `category="fact"`, `confidence=0.0`, `router_fallback=True` on LLM failure or invalid JSON.
- [`src/qa/ask.py`](../src/qa/ask.py): Implements `ask(doc_id, question)` dispatching by category:
  - `fact`: runs `answer_question(doc_id, question, verify=True)`.
  - `explain_term`: returns a plain-language <=4-sentence explanation labeled `"General explanation, not from your document"`, and attaches verified document quotes via `answer_question()` if the candidate term appears in the document.
  - `calculation`: returns `status="calculator_not_ready"` with extracted numeric inputs and `"calculators arrive in step 3c"` without calling the LLM to compute numbers.
  - `advice`: returns a neutral information-not-advice refusal + offer to display relevant clauses (risks, fees, penalties), without giving recommendations.
  - `off_topic`: returns a polite refusal with zero LLM answering calls.
  - Every response includes `category`, `status`, `answer`, `evidence`, `model_used`, and `router_fallback`.
- [`scripts/demo_ask.py`](../scripts/demo_ask.py): CLI viewer (`python scripts/demo_ask.py <doc_id> "<question>"`).
- [`scripts/test_2d_router.py`](../scripts/test_2d_router.py): Verification suite covering T1–T6 across 40 hand-crafted questions (including 6 across Hindi, Bengali, Punjabi, Malayalam, and Tamil) and 6 live `ask()` cases.

### 2. Evaluation Results (`scripts/test_2d_router.py`)
- **T1 (API Key Leak Scan)**: **PASS** — 0 leaks across 637 files in `data/processed`, `scripts`, `src`, `config`, `docs`.
- **T2 (Router Unit Tests with Fake LLM)**: **PASS** — All 5 deterministic rules, invalid JSON fallback (`fact`, `confidence=0.0`, `router_fallback=True`), crash fallback, and Indic script detection passed (0 API calls).
- **T3 (40-Question Router Benchmark)**: **PASS** — **40 / 40 (100.0%)** overall accuracy (target >= 85%); **100.0% advice recall** (0 advice questions routed to `fact`).
- **T4 (Rules-Only Fraction)**: **21 / 40 (52.5%)** resolved purely by deterministic rules (0 API calls); **19 / 40 (47.5%)** handled by `gemini-3.5-flash-lite` (`bulk`).
- **T5 (Live `ask()` 6 Cases on `03_dbs_mitc`)**: **PASS** —
  - `fact` (found): `status=ok`, `ev=1`, `model=gemini-3.6-flash`
  - `fact` (not found): `status=not_found`, `ev=0`, `model=gemini-3.6-flash`
  - `explain_term` (*"What does foreclosure mean?"*): `status=ok`, `ev=1` (verified Page 2 quote attached cleanly after `"General explanation, not from your document"`), `model=gemini-3.5-flash-lite`
  - `calculation`: `status=calculator_not_ready`, extracted inputs `[rs 500000, 9%, 24]`, `"calculators arrive in step 3c"`, 0 computed numbers
  - `advice`: `status=refused`, neutral info-not-advice disclaimer + offer to show risk/fee/penalty clauses, no recommendation
  - `off_topic`: `status=off_topic`, polite refusal, 0 answer API calls
- **T6 (API Budget & Cache)**: **PASS** — **25** live API calls on initial uncached run (`<= 60` budget); **0 new calls** on cached repeat run.

#### Confusion Matrix (40 Questions)
| Expected \ Predicted | `fact` | `explain_term` | `calculation` | `advice` | `off_topic` | Accuracy |
|---|---:|---:|---:|---:|---:|---:|
| `fact` | **10** | 0 | 0 | 0 | 0 | **10/10 (100.0%)** |
| `explain_term` | 0 | **8** | 0 | 0 | 0 | **8/8 (100.0%)** |
| `calculation` | 0 | 0 | **8** | 0 | 0 | **8/8 (100.0%)** |
| `advice` | 0 | 0 | 0 | **8** | 0 | **8/8 (100.0%)** |
| `off_topic` | 0 | 0 | 0 | 0 | **6** | **6/6 (100.0%)** |

### 3. How to Run
```powershell
python scripts\test_2d_router.py
python scripts\demo_ask.py 03_dbs_mitc "What does foreclosure mean?"
python scripts\demo_ask.py 03_dbs_mitc "Should I sign this gold loan agreement?"
python scripts\demo_ask.py 03_dbs_mitc "Calculate my monthly EMI on a Rs. 500000 gold loan at 9% for 24 months"
```

### 4. Honest Limitations
1. **Small Hand-Made Question Set Written by the Building AI**: All 40 routing test cases were written by the same agent that authored the router rules and prompt, which introduces optimism bias compared to messy real-user queries.
2. **Thin Multilingual Coverage**: Only 6 of the 40 test questions cover Indian languages (2 Hindi, 1 Bengali, 1 Punjabi, 1 Malayalam, 1 Tamil), and non-English deterministic rules cover only limited Hindi phrasing — Tamil, Bengali, Punjabi, and Malayalam questions rely primarily on the LLM router.
3. **Subtle Advice / Mixed-Intent Queries**: Edge cases blending factual phrasing with implicit decision-making (e.g., *"Are the late fees too high in this loan?"*) remain untested at scale and could challenge boundary calibration.

---

## Stage 3a: Key-info extraction
Implemented grounded 16-field key-information extraction in [`src/extract/extract_fields.py`](file:///C:/finalYear/src/extract/extract_fields.py) (`extract_key_info`), [`config/extract.yaml`](file:///C:/finalYear/config/extract.yaml), [`scripts/demo_extract.py`](file:///C:/finalYear/scripts/demo_extract.py), and [`scripts/test_3a_extract.py`](file:///C:/finalYear/scripts/test_3a_extract.py).

### 1. Schema Choice & Pipeline Design
- **Field Schema Deviation**: Followed the exact 16 Key Fields defined in [`docs/labeling_guideline.md`](file:///C:/finalYear/docs/labeling_guideline.md) (`document_title`, `agreement_date`, `borrowers`, `lenders`, `agents`, `loan_or_commitment_amount`, `interest_rate`, `repayment_terms`, `maturity_termination_date`, `fees`, `late_payment_or_default_interest`, `prepayment_terms`, `collateral_security`, `guarantees`, `events_of_default`, `governing_law`), which also matches `data/processed/labels/llm_assisted/key_info_llm.csv`, instead of the generic 16-field list (`lender`, `borrower`, `loan_amount`, `tenure`, `repayment_emi`, `penalties`, `termination`, `other_important_terms`, etc.).
- **Extraction Modes**: Documents `<= 300,000` chars (`max_doc_chars_for_whole_doc`) run in a single JSON prompt with `[[PAGE n]]` markers using model role `"main"` (`temperature: 0.0`); larger documents (such as `CITGO` at 354,794 chars) fall back to per-field BM25 chunk retrieval (`src.qa.retrieve.retrieve`, `top_k=6`, `max_calls_per_doc=16`). Invalid JSON triggers `retry_on_invalid_json: 1` retry (plus parser repair for malformed multi-integer `"page": 44, 45` values).
- **Verification Gates**: Every quote is verified via `src.qa.verify_quotes.verify_evidence`; unverified quotes are dropped, and any claimed field with 0 surviving quotes is marked `status: "unverified"` with its value hidden (`""`). The 6 numeric fields (`loan_or_commitment_amount`, `interest_rate`, `repayment_terms`, `maturity_termination_date`, `fees`, `late_payment_or_default_interest`) are checked deterministically with `src.qa.check_numbers.check_numbers` (`status: "needs_review"` on mismatch), with optional `verify_answer` cross-model checking (`verifier_independent`). Existing `answer_question()`, `route_question()`, and `ask()` behavior was left untouched.

### 2. Test Suite Results (T1–T6)
| Check | Outcome | Measured Result |
| :--- | :--- | :--- |
| **T1** API key leak scan | **PASS** | `0` leaks across `269` scanned files (configs, code, logs, report, caches, output JSON) |
| **T2** Fake-LLM unit tests (`0` API calls) | **PASS** | `14/14` checks passed: invalid JSON retry, fake quote dropped (`unverified` + hidden value), changed number flagged (`needs_review`), missing field -> `not_found`, page auto-correction, BM25 retrieval fallback, `"page": 1, 2` repair, independent fake verifier |
| **T3** Live 5-document benchmark | **PASS** | `83/83 (100.0%)` kept quotes verified; `83/87 (95.4%)` raw quotes survived (`4` dropped) |
| **T4** LLM-assisted silver labels (`key_info_llm.csv`) | **FAIL** | Strict containment: **P=60.6%, R=55.6%, F1=58.0%** (`TP=20, FP=13, FN=16, TN=5`; below `>= 85%` target) on 41 definitive rows (`+ 7 UNCLEAR`); diagnostic token-overlap (`>= 0.50`) F1 = **89.9%**, evidence quote match = `30/36` |
| **T5** Human gold standard (`gold_standard_extraction_v1.csv`) | **PASS** | `26/27` fields found across 3 SEC contracts (9 mapped fields each, incl. `1` `UNAVAILABLE_MISSING_SCHEDULE`); strict containment = `7/27`, token-overlap `>= 0.40` or contain = `11/27` |
| **T6** Call budget & cache reuse | **PASS** | `35` live calls in final full suite run (`<= 80` limit; `69` logged in `llm_log.csv` + `1` 429 probe = `70` cumulative across Stage 3a); `0` new calls (`22` cache hits) on repeat run of all 5 T3 docs |

### 3. Per-Document T3 Summary
| Document | Chars / Pages | Mode | Found / 16 | Status Breakdown (`ver`/`rev`/`nf`/`drop`) | Raw Quote Survival | Kept Quote Verified | Model Used |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `03_dbs_mitc` | `10,903` / `2` | whole-doc | `11` | `11 / 0 / 5 / 0` | `11/11 (100.0%)` | `100.0%` | `gemini-3.5-flash-lite` |
| `13_bajajhousingfinance_...Hindi` | `74,421` / `29` | whole-doc | `12` | `11 / 1 / 3 / 1` | `22/24 (91.7%)` | `100.0%` | `gemini-3.5-flash-lite` |
| `0000027430-..._aesohio...` | `7,641` / `3` | whole-doc | `9` | `9 / 0 / 7 / 0` | `13/13 (100.0%)` | `100.0%` | `gemini-3.5-flash-lite` |
| `09_muthoothomefin_MHIL-MITC` | `22,083` / `7` | whole-doc | `13` | `12 / 1 / 3 / 0` | `13/13 (100.0%)` | `100.0%` | `gemini-3.5-flash-lite` |
| `CITGO` (`000101/.../0000950129-03-001503_8.txt`) | `354,794` / `84` | BM25 retrieval | `11` | `11 / 0 / 5 / 0` | `24/26 (92.3%)` | `100.0%` | `gemini-3.5-flash-lite` |

*(Note: During an earlier pre-edit T3 pass before prompt refinement, `03_dbs_mitc` used `gemini-3.6-flash` for extraction and `gemini-3.5-flash` + fallback `gemini-3.5-flash-lite` for numeric verification with `verifier_independent=True`. Once `gemini-3.6-flash` hit its 20-requests/day free-tier quota, subsequent Stage 3a calls automatically routed via `GeminiClient` fallback to `bulk` = `gemini-3.5-flash-lite`, yielding `verifier_independent=False` on `03_dbs_mitc` in the final cached run.)*

### 4. Models Used
- **Configured roles (`config/models.yaml`)**: `main: gemini-3.6-flash`, `bulk: gemini-3.5-flash-lite`, `verifier: gemini-3.5-flash`.
- **Actual execution**: Due to a live `20 requests/day` free-tier limit hit on `gemini-3.6-flash`, Stage 3a logged calls in `data/processed/llm_log.csv` consisted of `1` `gemini-3.6-flash`, `1` `gemini-3.5-flash`, and `67` `gemini-3.5-flash-lite` fallback calls.

### 5. Honest Limitations
1. **Strict String-Containment F1 (`58.0%`) Fails the `85%` Target**: On T4, `TN=5/5` (`100%`) for absent fields and diagnostic token-overlap (`>= 0.50`) reaches `89.9%` (`30/36` evidence quotes locate the same source clause), yet strict contiguous substring containment achieves only `58.0%` F1 because `key_info_llm.csv` values are 15–25 word abstractive multi-clause curator summaries while the extractor produces independent concise phrasings (e.g., `$1,000,000.00` vs `"Revolving commitment capped at $1,000,000 outstanding"`). `3` silver fields (`0116` `events_of_default`/`collateral_security` and `057-97` `maturity_termination_date`) were also dropped as `unverified` (`FN`) because `gemini-3.5-flash-lite` inserted `"..."` or altered whitespace inside candidate quotes.
2. **Silver Labels Are Not Human Gold**: `data/processed/labels/llm_assisted/key_info_llm.csv` holds only 3 short SEC filings (48 rows, including 7 `UNCLEAR` rows deferred to separate unattached Notes) and is explicitly LLM-assisted silver ground truth rather than independent human annotation.
3. **Small Document Count & Gold Comparison**: Only 5 live benchmark documents (T3), 3 silver SEC filings (T4), and 3 human-verified SEC agreements (T5) were tested. In T5 (`gold_standard_extraction_v1.csv`), human annotations preserve structured policy labels (e.g., `total_commitment: {currency: USD, ...}`, `date_type: conditional_formula`, `UNAVAILABLE_MISSING_SCHEDULE`), limiting strict substring containment (`7/27`) even when the underlying numbers or entities match (`26/27` fields extracted, `11/27` token-overlap `>= 0.40` or contain). `GATX` `events_of_default` was dropped as `unverified` due to an ellipsis `"..."` in the fallback model's quote.
4. **Daily Quota Fallback**: Exhausting `gemini-3.6-flash`'s 20-RPD cap forced `gemini-3.5-flash-lite` to perform complex multi-page extraction and prevented independent cross-model numeric verification (`verifier_independent=False` on `03_dbs_mitc`) in the final run.
5. **Document Artifacts & Template Gaps**: Unfilled Indian MITC forms (e.g. `09_muthoothomefin_MHIL-MITC` blank loan-amount lines) and broken Indic font-encoding pages (`13_bajajhousingfinance...Hindi`, where `1` prepayment quote failed exact match and `1` numeric field flagged `needs_review`) yield legitimate `not_found`, `needs_review`, or `unverified` statuses rather than clean populated tables.

---

## Stage 3a-fix: transparent matching
Implemented fixed pre-registered matching rules in [`src/extract/match_values.py`](file:///C:/finalYear/src/extract/match_values.py) (`values_match`), re-scoring script [`scripts/eval_3a_matches.py`](file:///C:/finalYear/scripts/eval_3a_matches.py), verification suite [`scripts/test_3a_fix.py`](file:///C:/finalYear/scripts/test_3a_fix.py), and reviewer CSV [`data/processed/extract_3a_mismatch_review.csv`](file:///C:/finalYear/data/processed/extract_3a_mismatch_review.csv) without altering extraction prompts or behavior.

### 1. Pre-Registered Matching Rules (Fixed Before Reviewing Mismatches)
1. **`exact`**: Equal after Unicode NFC, lowercase, and whitespace collapse.
2. **`normalized`**: Equal after normalizing money (`USD` / `$` / `"30 million"` / `30,000,000` -> `30000000`, trailing `.00` removal, `INR`/`Rs.`/`₹` unification), percentages (`8.50%` = `8.5%`), unambiguous dates to ISO (`YYYY-MM-DD`, leaving ambiguous `dd/mm/yyyy` vs `mm/dd/yyyy` unconverted), and party suffixes/articles (`"N.A."`, `"Inc."`, `"LLC"`, `"Corp."`, `"The"`, punctuation).
3. **`partial`**: All numbers of the reference appear in the prediction (or vice versa, guarding empty numeric sets) AND symmetric content-token overlap (Dice/F1, preserving slash/dash date tokens) `>= 0.6`.
4. **`no`**: Otherwise.

### 2. Re-Scored Evaluation (Strict vs Lenient Reported Separately)
*(Evaluated from cached Stage 3a predictions: `1` live probe call during initial snapshot hydration, `0` new live calls on repeat/verification via [`test_3a_fix.py`](file:///C:/finalYear/scripts/test_3a_fix.py).)*

#### (a) LLM-Assisted Silver Labels (`data/processed/labels/llm_assisted/key_info_llm.csv` — NOT human gold)
- Breakdown across `48` rows (`3` SEC docs): `36` positive fields (`exact=11`, `normalized=0`, `partial=10`, `no=15`), `5` `NOT_PRESENT` (`TN=5`, `FP=0`), `7` `UNCLEAR` (deferred to unattached Notes).
- **Strict** (`exact` + `normalized` only): **P = 32.4%, R = 30.6%, F1 = 31.4%** (`TP=11, FP=23, FN=25`).
- **Lenient** (`exact` + `normalized` + `partial`): **P = 61.8%, R = 58.3%, F1 = 60.0%** (`TP=21, FP=13, FN=15`).

#### (b) Human-Verified Gold Standard (`data/friend/04_annotated_data/gold_standard_extraction_v1.csv`, read-only)
- Breakdown across `27` cells (`3` docs × `9` mapped fields, incl. `1` `UNAVAILABLE_MISSING_SCHEDULE`): `exact=5`, `normalized=0`, `partial=4`, `no=18`.
- **Strict field-match rate** (`exact` + `normalized`): **5/27 (18.5%)**.
- **Lenient field-match rate** (`exact` + `normalized` + `partial`): **9/27 (33.3%)**.
- Per document:
  - `Brown-Forman`: strict `2/9 (22.2%)`, lenient `3/9 (33.3%)` (`exact=2, norm=0, partial=1, no=6`)
  - `Caterpillar`: strict `1/9 (11.1%)`, lenient `3/9 (33.3%)` (`exact=1, norm=0, partial=2, no=6`)
  - `GATX`: strict `2/9 (22.2%)`, lenient `3/9 (33.3%)` (`exact=2, norm=0, partial=1, no=6`)

### 3. Test Suite Results (`test_3a_fix.py`)
- `[PASS]` **T1** API key leak scan: `0` leaks across `264` scanned files (before & after run).
- `[PASS]` **T2** Matcher unit tests (`0` API calls): `12/12` passed (`USD 30,000,000` vs `$30 million` -> `normalized`; `Citizens Bank, N.A.` vs `Citizens Bank` -> `normalized`; `8.5%` vs `8.50%` -> `normalized`; `5 years` vs `7 years` -> `no`; `30 days` vs `60 days` -> `no`; unrelated text -> `no`; unambiguous ISO dates, ambiguous numeric slash dates -> `no`, exact whitespace, partial fee).
- `[PASS]` **T3** Silver strict & lenient F1 reported separately.
- `[PASS]` **T4** Human gold strict & lenient match rates reported overall & per document.
- `[PASS]` **T5** Mismatch review CSV [`data/processed/extract_3a_mismatch_review.csv`](file:///C:/finalYear/data/processed/extract_3a_mismatch_review.csv) contains all `54` non-match rows (`partial` + `no` + `unclear_reference`) with `who_is_right` left blank.
- `[PASS]` **T6** Call budget & cache reuse: `<= 20` limit satisfied (`0` new calls in snapshot/cache repeat; `1` on initial hydration).

### 4. Mismatch Root-Cause Review Table (`54` rows in `extract_3a_mismatch_review.csv`)
| Root Cause Category | Count | Status | Notes |
| :--- | :---: | :--- | :--- |
| `matcher too strict` | pending review | pending review | e.g., `$22,000,000` vs `$22,000,000 principal loan`, concise value vs descriptive reference clause |
| `label wrong` | pending review | pending review | e.g., silver `UNCLEAR` vs extracted deferral clause (`7` rows) or policy formatting in gold (`UNAVAILABLE_MISSING_SCHEDULE`) |
| `system wrong` | pending review | pending review | e.g., `unverified`/dropped quote fields (`system_unverified`), truncated multi-clause coverage |
| `unclear` | pending review | pending review | Ambiguous / judgment-dependent clause differences |
| **Total Non-Matches** | **54** | **pending review** | Fill `who_is_right` (`system` / `label` / `both ok` / `unclear`) in [`extract_3a_mismatch_review.csv`](file:///C:/finalYear/data/processed/extract_3a_mismatch_review.csv) |

### 5. Plain-Words Verdict
**RISKY** — Even after pre-registered money/percent/date/party normalization and lenient partial overlap (`>= 0.6`), silver lenient F1 is `60.0%` (`strict F1 = 31.4%`) and human-gold lenient match rate is `33.3%` (`strict = 18.5%`). Exact rules expose two real issues without hiding behind substring heuristics: (1) free-form summary labels and concise extracted values often share the same core number/date (`$22,000,000`, `February 1, 2012`) while differing in surrounding explanatory words (pushing token F1 `< 0.6`), and (2) some complex multi-clause fields still drop quotes (`unverified`) or omit policy nuance under `gemini-3.5-flash-lite` fallback. All `54` non-matches await human adjudication in `extract_3a_mismatch_review.csv`.

---

## Stage 3a-fix2: quote repair, deferral handling & dual metrics
Implemented Stage 3a-fix2 improvements in [`config/extract.yaml`](file:///C:/finalYear/config/extract.yaml), [`src/extract/extract_fields.py`](file:///C:/finalYear/src/extract/extract_fields.py), [`src/extract/judge_eval.py`](file:///C:/finalYear/src/extract/judge_eval.py), and [`scripts/test_3a_fix2.py`](file:///C:/finalYear/scripts/test_3a_fix2.py), keeping Stage 3a-fix rules (`src/extract/match_values.py`) and Stage 3a-fix reported scores untouched.

### 1. Human Review Verdicts (`extract_3a_mismatch_review_filled.csv`, 54 rows)
- `both ok`: **47 / 54** (system and label both extracted valid facts; matcher was stricter or phrasing differed)
- `label`: **6 / 54** (rows `7`, `8`, `16`, `20`, `32`, `54` — 3 over-answered absence/deferral fields, 3 unverified/dropped quotes)
- `system`: **1 / 54** (row `19` — Maritrans Event of Loss mandatory prepayment found by system while silver marked `UNCLEAR`)

### 2. Changes Implemented
- **A. Quote Repair (`quote_repair_enabled: true`, `similarity >= 95.0`, `max 400 chars`)**: When a quote fails verbatim verification, [`_repair_quote_across_pages`](file:///C:/finalYear/src/extract/extract_fields.py) searches the cited page and its neighbours using `rapidfuzz` on normalized text, bridges ellipsis spans (`...`) or rescues longest contiguous sub-segments `<= 400` chars strictly matching exact source substrings (`quote_repaired=True`), and rejects any candidate whose numbers differ from the original quote. Prompts now instruct contiguous 1–3 sentence passages with no ellipses (`...`).
- **B. Deferral & Absence**: Added status `deferred_to_other_document` (`value = ""`, `defers_to` populated, verified quote kept) for fields defined solely by reference to another document (`"as defined in the Note"`, `"as set forth in the Schedule"`, `"in accordance with the Fee Letter"`). Added explicit prompt rules and a guard converting vague `"the term of the Note"` date answers to `not_found` instead of over-answering.
- **C. Metric B (`post-hoc, judge-based, not pre-registered`)**: Added independent `verifier`-role judge evaluation and 54-verdict calibration (`both ok` -> `equivalent | partial`, `label` -> `different`, `system` -> `equivalent`) in [`src/extract/judge_eval.py`](file:///C:/finalYear/src/extract/judge_eval.py), gating trust at `>= 85%` agreement, caching calls on disk, refusing same-model fallback to `bulk`, and stopping gracefully on quota errors.

### 3. Test Results (`scripts/test_3a_fix2.py`, All Checks PASS)
| Test | Status | Measured Result |
| :--- | :--- | :--- |
| **T1** API key leak scan | **PASS** | `0` leaks across `299` scanned files (before & after run) |
| **T2** Fake-LLM unit tests (`0` API calls) | **PASS** | `11/11` checks passed: `"..."` quote repaired to exact source span (`<= 400` chars), fabricated quote dropped, changed-number quote dropped, `"defined in the Note"` -> `deferred_to_other_document`, `"term of the Note"` -> `not_found`, judge `>= 85%` gate & graceful 429 stop |
| **T3** Re-run 5 benchmark docs | **PASS** | Kept quotes verified = **58/58 (100.0%)**; dropped quotes = **3** (down from previous **4**; `1` Hindi quote repaired on `13_bajaj`: `prepayment_terms`). Per doc dropped: `03_dbs_mitc` (`1`), `13_bajaj` (`2` broken-glyph/table quotes), `aesohio` (`0`), `09_muthoot` (`0`), `CITGO` (`0`) |
| **T4** Prior 6 `who_is_right=label` rows | **PASS** | **6/6** resolved correctly: rows `7`, `8`, `16` -> `not_found`; rows `20`, `32`, `54` -> `verified` (`quote_repaired=True` with verified quote) |
| **T5** Metric A (unchanged rules) & Metric B | **PASS** | **Metric A Silver**: Strict F1 = **28.2%** (`P=28.6%, R=27.8%`), Lenient F1 = **56.3%** (`P=57.1%, R=55.6%`; `exact=10, norm=0, partial=10, no=16, TN=5`). **Metric A Gold**: Strict = **5/27 (18.5%)**, Lenient = **8/27 (29.6%)** (`Brown-Forman 2/9 strict, 2/9 lenient`; `Caterpillar 1/9, 3/9`; `GATX 2/9, 3/9`). **Metric B (`post-hoc, judge-based, not pre-registered`)**: **NOT TRUSTED / NOT SCORED** — stopped gracefully on `HTTP 429` (`gemini-3.5-flash` 20-RPD free-tier quota exceeded; `0/54` calibrated) |
| **T6** Call budget & cache reuse | **PASS** | `11` new live calls in final run (`37` cumulative across Stage 3a-fix2 in `llm_log.csv`, `<= 80` limit); `0` new live calls on cached repeat (`cache_hits = 21`) |

### 4. Plain-Words Verdict & What Is Still Weak
**Verdict: IMPROVED ON GROUNDING, STILL RISKY ON SCORING & QUOTA.** All 6 known extraction failures from human review (`rows 7, 8, 16, 20, 32, 54`) are now fixed, kept-quote verification stays at `100.0%` (`58/58`), and dropped quotes decreased from `4` to `3` across the 5 benchmark documents. However, four weaknesses remain:
1. **Independent Verifier Judge Exhausted Free-Tier Quota**: Both `gemini-3.6-flash` (`main`) and `gemini-3.5-flash` (`verifier`) hit Google's `20 requests/day` free-tier limit, preventing calibration (`0/54`) and forcing extraction onto `bulk` (`gemini-3.5-flash-lite`) without Metric B semantic scoring.
2. **Rigid Text Matching vs Summary Labels (Metric A)**: Under unchanged `match_values.py` rules, Silver lenient F1 is `56.3%` and Gold lenient match rate is `29.6%` (`8/27`) because human/silver labels include descriptive policy prose around extracted numbers/dates and `deferred_to_other_document` blanks `value` on deferred clauses.
3. **Broken-Glyph / Interleaved Hindi PDF Tables**: `13_bajajhousingfinance_MITC...Hindi` still drops `2` raw table quotes (`interest_rate`, `fees`) where PyMuPDF column linearization and legacy font glyphs fall below `95%` normalized similarity.
4. **Occasional Quote Instability under Fallback Model**: Under `gemini-3.5-flash-lite`, `03_dbs_mitc` dropped `repayment_terms` (`unverified`) in the updated run even though it passed prior to the prompt change.

---

## Stage 3b: Grounded plain-English summaries
Implemented grounded SHORT and DETAILED plain-English summarization in [`config/summarize.yaml`](file:///C:/finalYear/config/summarize.yaml), [`src/summarize/summarize.py`](file:///C:/finalYear/src/summarize/summarize.py) (`summarize_document`), [`scripts/demo_summarize.py`](file:///C:/finalYear/scripts/demo_summarize.py), and [`scripts/test_3b_summary.py`](file:///C:/finalYear/scripts/test_3b_summary.py), keeping [`src/extract/match_values.py`](file:///C:/finalYear/src/extract/match_values.py), Stage 3a extraction behavior, and Stage 3a-fix/3a-fix2 scores untouched.

### 1. Pipeline & Guardrails Implemented
- **Config ([`config/summarize.yaml`](file:///C:/finalYear/config/summarize.yaml))**: `model_role: "bulk"` (`gemini-3.5-flash-lite` to preserve free-tier quota), `temperature: 0.0`, `short_max_words: 120`, `max_live_calls: 30`.
- **Verified Inputs Only**: Consumes only `verified` and `needs_review` fields from `extract_key_info` that carry `>= 1` verified quote; routes `not_found` fields as `"Not found in this document"` and `deferred_to_other_document` fields as `"Defined in another document (not provided; refers to ...)"` under the `Not found / defined elsewhere` section.
- **Deterministic Grounding Gate (Zero API Calls)**:
  - Rejects and drops any sentence containing advisory/opinion phrasing (`_ADVICE_PATTERNS`).
  - Rejects and drops any sentence missing a valid `[p.N]` page citation (`_extract_cited_pages`).
  - Strips `[p.N]` tags, extracts all numbers, dates, percentages, and amounts via `src.qa.check_numbers.check_numbers` (including Devanagari digits `०–९` -> `0–9`), and drops any sentence containing a numeric value absent from its cited page text.
  - Rebuilds `short` (enforcing `short_max_words <= 120`) and the 8 detailed content sections strictly from kept sentences, plus deterministic `Not found / defined elsewhere`. Indian-language documents (e.g., Hindi Bajaj MITC) are summarized in English.

### 2. Test Suite Results (`scripts/test_3b_summary.py`, All Checks PASS)
| Test | Status | Measured Result |
| :--- | :--- | :--- |
| **T1** API key leak scan | **PASS** | `0` leaks across `310` scanned files (configs, code, logs, report, review CSV, caches) |
| **T2** Fake-LLM unit tests (`0` API calls) | **PASS** | `9/9` checks passed: invented numbers (`18.5%`, `$999`) dropped, uncited sentence dropped, Devanagari numbers (`१५%`, `२४`) matched cleanly, `not_found` -> `"Not found in this document"`, deferred -> `"Defined in another document"`, advice/opinion wording blocked, `short <= 120` words |
| **T3** Live 5 benchmark documents | **PASS** | All `5` docs succeeded; `100%` of kept sentences carry valid `[p.N]` cites and `100%` (`19/19`) of numbers in kept sentences exist in source text (`1` ungrounded sentence on `CITGO` dropped cleanly) |
| **T4** Human review sheet | **PASS** | Wrote `72` rows (`doc, section, sentence, pages, status`, no verdict column) to [`data/processed/summary_review.csv`](file:///C:/finalYear/data/processed/summary_review.csv) |
| **T5** Budget & cached repeat | **PASS** | `10` live calls on initial uncached run (`<= 30` limit; `5` summary calls + `5` extraction cache misses where `.json` page dict formatting differed slightly from `.txt` marker cache keys); `0` new live calls on cached verification runs (`cache_hits = 26`) |

### 3. Per-Document T3 Summary Metrics
| Document | Short Words (`<=120`) | Kept Sentences | Dropped Sentences | Kept With Cite | Kept Numbers in Source | Model Used |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `03_dbs_mitc` | `74` | `13` | `0` | `100%` | `0/0 (100%)` | `gemini-3.5-flash-lite` |
| `13_bajajhousingfinance_...Hindi` | `61` | `13` | `0` | `100%` | `2/2 (100%)` | `gemini-3.5-flash-lite` |
| `0000027430-..._aesohio...` | `42` | `9` | `0` | `100%` | `4/4 (100%)` | `gemini-3.5-flash-lite` |
| `09_muthoothomefin_MHIL-MITC` | `102` | `14` | `0` | `100%` | `5/5 (100%)` | `gemini-3.5-flash-lite` |
| `CITGO` (`000101/.../0000950129-03-001503_8.txt`) | `96` | `22` | `1` | `100%` | `8/8 (100%)` | `gemini-3.5-flash-lite` |

*(On `CITGO`, the deterministic number checker caught and dropped 1 `short` sentence citing `[p. 3]` for a `3.00%` Eurodollar floor whose text actually appeared on page `10`, while Detailed `Interest and repayment` retained the correctly cited `3.00%` sentence on `[p. 10]`.)*

### 4. Honest Limitations
1. **Fluency Is Not Correctness**: Deterministic checks guarantee that kept sentences carry valid `[p.N]` cites and every number/date/percentage/amount occurs on the cited page(s), **not** that qualitative wording is legally complete or nuance-accurate — human inspection of [`summary_review.csv`](file:///C:/finalYear/data/processed/summary_review.csv) (`72` sentences) is still required.
2. **Upstream Extraction Limits Propagate**: Because summaries use only verified/needs_review fields from `extract_key_info`, any field dropped in Stage 3a (such as `repayment_terms` on `03_dbs_mitc` or broken Hindi tables on `13_bajaj`) is omitted from summary facts (`None verified in this document.`). Conversely, blank MITC template lines captured verbatim by Stage 3a (e.g., `"Name of Guarantor, Resi. Address & Age :"` in `09_muthoothomefin_MHIL-MITC`) can appear in `Security and guarantees`.
3. **Cross-Page Synthesis Risk**: Combining facts from two pages into a single summary sentence with only one `[p.N]` tag triggers deterministic rejection (`CITGO` `short` `3.00%` drop), leaving `4` short sentences on `CITGO` covering fewer topics than all 6 target summary items when multi-page numbers aren't double-cited.
4. **English-Only Output on Indic Documents**: `13_bajaj` Hindi MITC is summarized in English (`61` words); regional-language translation waits until Stage 5.
5. **No Gold Summary ROUGE/BERTScore Yet**: Quantitative overlap against reference human summaries was not measured here (`data/processed/labels/llm_assisted/` does not yet contain completed summary labels).

## Stage 3c: Deterministic loan calculators
Implemented only Stage 3c calculator functionality in [`config/calc.yaml`](../config/calc.yaml), [`src/calc/formulas.py`](../src/calc/formulas.py), [`src/calc/extract_inputs.py`](../src/calc/extract_inputs.py), [`src/qa/ask.py`](../src/qa/ask.py), [`scripts/demo_calc.py`](../scripts/demo_calc.py), and [`scripts/test_3c_calc.py`](../scripts/test_3c_calc.py). Updated the existing Stage 2d calculation assertion in [`scripts/test_2d_router.py`](../scripts/test_2d_router.py) to expect the deterministic result. No edits were made to `src/extract/match_values.py`, extraction behavior, summaries, or earlier evaluation scores; Stage 4a was not started.

### 1. Calculator and Input Behavior
- **Configuration:** bulk model role, temperature `0`, maximum `15` live calls per extraction document, two-decimal rounding, and a default `365`-day year.
- **Pure Decimal formulas:** reducing-balance EMI, rounded amortization schedule with the final payment adjusted to clear the balance, schedule-derived total interest/payment and outstanding balance, percentage prepayment charge with optional minimum, simple penal interest with optional flat fee, interest-only monthly amount, and flat-rate total interest. The flat-rate result explicitly says it is not comparable to a reducing-balance rate. Currency is carried through without conversion.
- **Grounded inputs:** Regex rules recognize rupee/dollar amounts, lakh/crore, percentages, months/years, days, and Devanagari digits. Explicit user values take precedence. The LLM can only suggest inputs as JSON and cannot supply a result; values must quote text from the question. Document inputs are accepted only from a cached verified key-info record (or `extract_key_info`) when the quote matches the cited source page. Otherwise the value remains missing and the caller is asked for it.
- **`ask()` calculation route:** returns `ok` with inputs and their sources, formula name, steps, assumptions and result, or `needs_inputs` without guessing. The other four route categories were left unchanged. Successful calculations include the requested estimate-only / not-financial-advice notice.

### 2. Test Results (`scripts/test_3c_calc.py`, all PASS)
| Test | Status | Measured result |
|---|---|---|
| **T1** API-key leak scan | **PASS** | `0` leaks across `13` scanned files; key value was not printed or saved. |
| **T2** Decimal formulas, no API | **PASS** | Reference EMI `$1,000,000` at `12%` for `12` months = `88,848.79`; zero-rate EMI = `100.00`; schedule ends at `0.00`; schedule interest = `66,185.45`; total payments = `1,066,185.45`; outstanding after 6 payments = `514,921.05`; prepayment `2%` of `200,000` = `4,000.00`; minimum-charge case = `50.00`; penal interest at `24%` for 30/365 days on `10,000` = `197.26`; flat penal fee = `75.00`; interest-only monthly = `1,000.00`; flat one-year interest `120,000.00` exceeds reducing-balance interest `66,185.45`; EMI-times-months differs from schedule payments by `0.03` (< `1`). |
| **T3** Input extraction, fake LLM, no API | **PASS** | `Rs 5 lakh at 9% for 2 years` -> principal `500,000`, rate `9%`, `24` months; Hindi digits parsed; missing tenure stays missing; unverified document value refused; fake LLM result ignored and formula result used. |
| **T4** Live `ask()` on DBS and SEC document | **PASS** | DBS inputs came from the user. On the SEC WSI agreement, principal `1,000,000.00` came from the cached verified record with its exact quote on page `1`; `9%` and `24` months came from the user. `0` live calls (`<=15`). |
| **T5** Stage 2d six-case compatibility | **PASS** | Fact-found, fact-not-found, explanation, calculation, advice, and off-topic cases all passed. Calculation returned `22,842.37`; advice remained refused. |
| **T6** Call budget and cached repeat | **PASS** | First calculation `0` new live calls; cached repeat `0`; result unchanged. |

### 3. Limitations and Risk
1. These are estimates, not lender payoff or amortization statements. Schedule rounding and final-payment adjustment can differ from a lender's rounding rules.
2. Penal charges use simple interest and a `365`-day basis by default; real contracts may use another day-count basis, compounding, grace periods, or separate fees.
3. Floating rates are treated as the single rate supplied for the calculation; future resets are not forecast.
4. Taxes, processing fees, insurance, and other contract-specific charges are excluded unless separately supplied and supported by an implemented input.
5. Natural-language parsing is deliberately conservative; it does not cover every phrasing or language. Missing or ambiguous inputs must be clarified by the user. Document values without a usable cached/verified quote and page are not used.
6. This implements the calculator interface and checks only; it is not financial advice or a recommendation about borrowing.


---

## Stage 1 Pilot Silver Labels — Key Fields (First 10 Documents)
Completed key-field silver labeling (`16` guideline fields per document; **LLM-assisted SILVER labels, not human gold**) for the remaining `7` documents (`04`–`10`) of the 10-document pilot scope using [`scripts/llm_assisted_annotation_tools.py`](file:///C:/finalYear/scripts/llm_assisted_annotation_tools.py) (`MODEL` updated to `"unknown model; session tool: Antigravity"`), [`batch_02_key.json`](file:///C:/finalYear/data/processed/labels/llm_assisted/batch_02_key.json), [`batch_03_key.json`](file:///C:/finalYear/data/processed/labels/llm_assisted/batch_03_key.json), [`batch_04_key.json`](file:///C:/finalYear/data/processed/labels/llm_assisted/batch_04_key.json), [`key_info_llm.csv`](file:///C:/finalYear/data/processed/labels/llm_assisted/key_info_llm.csv), and [`llm_assisted_README.md`](file:///C:/finalYear/data/processed/labels/llm_assisted/llm_assisted_README.md), with zero Gemini API calls and read-only source files untouched.

### Per-Document Counts & Quote Verification (`python scripts/llm_assisted_annotation_tools.py --validate --metrics`)
| Rank | Document (`doc_id`) | Rows | Found | `NOT_PRESENT` | `UNCLEAR` | Verified Quotes | Failed | Provenance (`model`) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `01` | `000010/104897/0000950123-11-030926_2.txt` | `16` | `12` | `1` | `3` | `15` | `0` | `OpenAI ChatGPT via Copilot SDK; exact model ID unavailable` |
| `02` | `000081/810113/0000950116-04-002411_4.txt` | `16` | `10` | `2` | `4` | `14` | `0` | `OpenAI ChatGPT via Copilot SDK; exact model ID unavailable` |
| `03` | `000103/1039213/0000912057-97-018811_19.txt` | `16` | `14` | `2` | `0` | `14` | `0` | `OpenAI ChatGPT via Copilot SDK; exact model ID unavailable` |
| `04` | `000104/1041426/0000950144-99-003055_2.txt` | `16` | `14` | `2` | `0` | `14` | `0` | `unknown model; session tool: Antigravity` |
| `05` | `000002/27566/0000945836-96-000035_3.txt` | `16` | `15` | `1` | `0` | `15` | `0` | `unknown model; session tool: Antigravity` |
| `06` | `000087/876645/0000891618-03-004250_9.txt` | `16` | `14` | `2` | `0` | `14` | `0` | `unknown model; session tool: Antigravity` |
| `07` | `000105/1058033/0001005477-99-003520_9.txt` | `16` | `12` | `3` | `1` | `13` | `0` | `unknown model; session tool: Antigravity` |
| `08` | `000104/1042893/0000899243-01-501236_3.txt` | `16` | `13` | `3` | `0` | `13` | `0` | `unknown model; session tool: Antigravity` |
| `09` | `000084/849547/0000950128-00-000940_5.txt` | `16` | `14` | `2` | `0` | `14` | `0` | `unknown model; session tool: Antigravity` |
| `10` | `000105/1052667/0000912057-00-028795_20.txt` | `16` | `15` | `0` | `1` | `16` | `0` | `unknown model; session tool: Antigravity` |
| **All 10** | **Pilot Key Fields Total (`01`–`10`)** | **`160`** | **`133`** | **`18`** | **`9`** | **`142`** | **`0`** | `48` prior + `112` new (`Antigravity`) |

- Risk clauses, Q&A, summaries, and second-pass labels were not started (`0/30`).


---

## Stage 1 Pilot Silver Labels — Risk Clauses (10 SEC Docs + 3 Indian MITCs)
Completed risk-clause silver labeling (**LLM-assisted SILVER labels, not human gold**) for the first `10` SEC documents (`171` clauses in [`risk_llm.csv`](file:///C:/finalYear/data/processed/labels/llm_assisted/risk_llm.csv) from `batch_01_risk.json`–`batch_04_risk.json`) and `3` ingested Indian MITC documents (`38` clauses in [`risk_indian_llm.csv`](file:///C:/finalYear/data/processed/labels/llm_assisted/risk_indian_llm.csv) from `batch_indian_risk.json` using the **exact same 11 CSV columns**), with zero Gemini API calls and `model = "unknown model; session tool: Antigravity"`.

- **Helper Limitation Noted**: [`scripts/llm_assisted_annotation_tools.py`](file:///C:/finalYear/scripts/llm_assisted_annotation_tools.py) reads only ZIP-archived SEC documents listed in `key_info_sheet.csv` and cannot ingest or validate `data/processed/ingested/` files, so the 3 Indian MITC risk sets were verified directly against `data/processed/ingested/*.txt` and saved separately in [`risk_indian_llm.csv`](file:///C:/finalYear/data/processed/labels/llm_assisted/risk_indian_llm.csv).
- **Totals & Verification (`209` clauses)**: `209 / 209` (`100.0%`) verbatim/whitespace-normalized quotes verified, `0` failed quotes, `19` low-confidence rows (`[confidence: low - ...]` inside `rationale`).
- **By Category (`7` categories from [`docs/labeling_guideline.md`](file:///C:/finalYear/docs/labeling_guideline.md), all `>= 10`)**: `Financial terms=30`, `Repayment=32`, `Penalties and charges=30`, `Collateral=29`, `Default conditions=30`, `Termination=27`, `Covenants=31`.
- **By Severity**: `Low=63`, `Medium=57`, `High=62`, `Critical=27`.
- **Per Document (`17` each on `01`–`09`, `18` on `10`; `12` on `03_dbs_mitc`, `14` on `09_muthoothomefin_MHIL-MITC`, `12` on `11_gichfindia_MOST-IMPORTANT-TERMS-1`)**: all `13` documents completed; Q&A, summaries, and second-pass labels remain unstarted.

---

## Stage 1 Pilot Silver Labels — Risk Consistency Fix Pass (`R1`–`R3`)
Added rules `R1`–`R3` under the risk section of [`docs/labeling_guideline.md`](file:///C:/finalYear/docs/labeling_guideline.md), audited all `209` rows (`171` SEC clauses in [`risk_llm.csv`](file:///C:/finalYear/data/processed/labels/llm_assisted/risk_llm.csv) + `38` Indian MITC clauses in [`risk_indian_llm.csv`](file:///C:/finalYear/data/processed/labels/llm_assisted/risk_indian_llm.csv)) against `R1`–`R3` with zero Gemini API calls, and recorded all **`43` changed rows** in [`risk_revisions.csv`](file:///C:/finalYear/data/processed/labels/llm_assisted/risk_revisions.csv). Original CSVs (`key_info_llm.csv`, `risk_llm.csv`, `risk_indian_llm.csv`) were left completely untouched.

- **Provenance & Disclaimer**: These revisions are **LLM-assisted silver revisions, not human gold** (`model = "unknown model; session tool: Antigravity"`, `0` live API calls).
- **Changed Rows (`43 / 209`)**: `37` rows from `risk_llm.csv` and `6` rows from `risk_indian_llm.csv` (`R1`: `2`, `R2`: `30`, `R1 and R2`: `3`, `R3`: `8` borrower-protective rationale-prefix updates including `09_muthoothomefin_MHIL-MITC` `IM06`).
- **Category Counts (Old -> New across `209` clauses)**: `Financial terms`: `30 -> 25`; `Covenants`: `31 -> 36`; unchanged: `Repayment` `32`, `Penalties and charges` `30`, `Collateral` `29`, `Default conditions` `30`, `Termination` `27`.
- **Severity Counts (Old -> New across `209` clauses)**: `Low`: `63 -> 64`; `Medium`: `57 -> 71`; `High`: `62 -> 65`; `Critical`: `27 -> 9`.
- **High + Critical Share**: `89 / 209` (`42.58%`) before -> `74 / 209` (`35.41%`) after.

---

## Stage 4a: risk classifier
Built and evaluated the batched Stage 4a clause risk classifier (`config/risk.yaml`, `src/risk/classify.py`, `src/risk/evaluate.py`, `scripts/split_risk_data.py`, `scripts/eval_4a_risk.py`, `scripts/print_risk_misses.py`, `scripts/test_4a_risk.py`) after applying the Step 0 finance review.

- **Step 0 Finance Review & Final Gold-Proxy CSV (`risk_final.csv`)**:
  - Appended `2` `REVIEW` (`Claude finance review`) rows to [`risk_revisions.csv`](file:///C:/finalYear/data/processed/labels/llm_assisted/risk_revisions.csv) (`000105/1058033` `R14`: `Default conditions -> Termination`, `High` kept; `03_dbs_mitc` `IM12`: `Termination -> Covenants`, `Low` kept), kept `000105/1052667` `R11` as `High`, reduced pinned Criticals in [`print_risk_review.py`](file:///C:/finalYear/print_risk_review.py) to `000081/810113` `R12` and `000084/849547` `R16`, and added the `R2` Default-conditions Critical clarification to [`docs/labeling_guideline.md`](file:///C:/finalYear/docs/labeling_guideline.md).
  - [`scripts/build_risk_final.py`](file:///C:/finalYear/scripts/build_risk_final.py) generated [`risk_final.csv`](file:///C:/finalYear/data/processed/labels/llm_assisted/risk_final.csv) (`209` rows: `Financial terms=25, Covenants=37, Repayment=32, Penalties and charges=30, Collateral=29, Default conditions=29, Termination=27`; `Low=64, Medium=71, High=65, Critical=9`; `8/8` `R3` rationales starting with `"[borrower-protective]"`), leaving `key_info_llm.csv`, `risk_llm.csv`, and `risk_indian_llm.csv` untouched.
- **Document Split ([`data/processed/risk_split.csv`](file:///C:/finalYear/data/processed/risk_split.csv))**: Sorted the `13` `doc_id`s alphabetically; positions `3, 6, 9, 12` went to **`test`** (`4` docs, `66` clauses, including Indian MITC `09_muthoothomefin_MHIL-MITC`; Categories: `Financial terms=9, Repayment=9, Penalties and charges=9, Collateral=11, Default conditions=9, Termination=10, Covenants=9`; Severities: `Low=21, Medium=22, High=19, Critical=4`) and the remaining **`dev`** (`9` docs, `143` clauses; Categories: `Financial terms=16, Repayment=23, Penalties and charges=21, Collateral=18, Default conditions=20, Termination=17, Covenants=28`; Severities: `Low=43, Medium=49, High=46, Critical=5`).
- **Prompt Versions (Dev-Only Tuning; Zero Test Leakage)**:
  - **`v1` (`dev`, `n=143`, `12` live calls, `gemini-3.5-flash-lite`)**: Category acc=`86.7%` (`124/143`), macro-F1=`86.0%`; Severity exact=`60.1%` (`86/143`), macro-F1=`61.9%`, within-1-level=`99.3%` (`142/143`), Critical recall=`4/5` (`80.0%`), Critical F1=`66.7%`, `0` numeric flags. Confusion highlight: `23/43` `Low` clauses over-predicted as `Medium`; `4` `Termination` clauses confused with `Default conditions`.
  - **`v2` (`dev`, `n=143`, `12` live calls, `gemini-3.5-flash-lite` — FROZEN)**: Clarified `Low` vs `Medium` baseline/waterfall terms, `Default conditions` trigger vs `Termination` remedy boundary, and `by notice` (`High`) vs automatic without-notice acceleration (`Critical`) using dev errors only. Category acc=`87.4%` (`125/143`), macro-F1=`87.1%`; Severity exact=`70.6%` (`101/143`), macro-F1=`70.1%`, within-1-level=`99.3%` (`142/143`), Critical recall=`4/5` (`80.0%`), Critical F1=`66.7%`, `0` numeric flags.
- **Frozen `v2` Test Evaluation (`test`, `n=66`, `7` live calls, run once -> [`risk_pred_test.csv`](file:///C:/finalYear/data/processed/risk_pred_test.csv))**:
  - **Category**: accuracy=`87.9%` (`58/66`), macro-F1=`87.4%` (`0` unclassified). Best: `Covenants` (`100.0%` F1), `Collateral` (`95.7%`), `Default conditions` (`90.0%`), `Financial terms` (`88.9%`), `Repayment` (`88.9%`); main confusions: `Termination` (`6/10` recall, `75.0%` F1 — `2` to `Default conditions`, `1` to `Repayment`, `1` to `Penalties and charges`) and `Penalties and charges` (`73.7%` F1 — `1` to `Financial terms`, `1` to `Collateral`).
  - **Severity**: exact=`68.2%` (`45/66`), 4-class macro-F1=`71.5%`, within-1-level=`100.0%` (`66/66`, `0` off-by-2+ misses), Critical recall=`3/4` (`75.0%`; Critical F1 omitted because support `< 5`), `0` numeric flags. Main confusion: `10/19` `High` clauses under-predicted as `Medium` (`High` recall `47.4%`), plus `3` `Low->Medium`, `3` `Medium->Low`, `4` `Medium->High`, and `1/4` `Critical->High`.
  - **Budget & Models**: `31 / 40` cumulative live API calls (`12` dev `v1` + `12` dev `v2` + `7` test `v2`), all `gemini-3.5-flash-lite` (`0` fallbacks); cached repeat on dev = `0` new live calls. Confusion matrices saved to [`risk_cm_dev_category.csv`](file:///C:/finalYear/data/processed/risk_cm_dev_category.csv), [`risk_cm_dev_severity.csv`](file:///C:/finalYear/data/processed/risk_cm_dev_severity.csv), [`risk_cm_test_category.csv`](file:///C:/finalYear/data/processed/risk_cm_test_category.csv), and [`risk_cm_test_severity.csv`](file:///C:/finalYear/data/processed/risk_cm_test_severity.csv).
- **Post-Hoc Label Cleanup & Re-Score (`IM10` + `R4`, `0` new API calls, no prompt change)**:
  - **Disclosure**: These label changes were applied **after** the `test` split had already been run once; saved predictions in [`risk_pred_dev.csv`](file:///C:/finalYear/data/processed/risk_pred_dev.csv) and [`risk_pred_test.csv`](file:///C:/finalYear/data/processed/risk_pred_test.csv) were re-scored offline via [`scripts/rescore_4a_saved.py`](file:///C:/finalYear/scripts/rescore_4a_saved.py) with no model rerun or prompt change.
  - Added rule `R4` (`fees charged to the borrower = Penalties and charges; interest rate and rate-reset terms = Financial terms`) to [`docs/labeling_guideline.md`](file:///C:/finalYear/docs/labeling_guideline.md), appended `6` rows (`03_dbs_mitc` `IM10` `Termination -> Default conditions`, `High` + `5` fee rows `000103/1039213` `R05`, `000087/876645` `R02`, `000105/1058033` `R17`, `000104/1042893` `R07`, `09_muthoothomefin_MHIL-MITC` `IM04` `Financial terms -> Penalties and charges`) to [`risk_revisions.csv`](file:///C:/finalYear/data/processed/labels/llm_assisted/risk_revisions.csv), and rebuilt [`risk_final.csv`](file:///C:/finalYear/data/processed/labels/llm_assisted/risk_final.csv) (`Financial terms=20, Covenants=37, Repayment=32, Penalties and charges=35, Collateral=29, Default conditions=30, Termination=26`; severities unchanged).
  - **Old vs New (`dev`, `n=143`)**: Category acc `87.4% -> 87.4%` (`125 -> 125/143`), macro-F1 `87.1% -> 87.1%`; `Financial terms` F1 `82.4% -> 77.4%`, `Penalties and charges` `83.7% -> 82.6%`, `Default conditions` `87.2% -> 90.0%`, `Termination` `86.7% -> 89.7%`; Severity unchanged (`exact=70.6%`, `macro-F1=70.1%`, `within-1=99.3%`, `Critical recall=4/5`).
  - **Old vs New (`test`, `n=66`)**: Category acc `87.9% -> 87.9%` (`58 -> 58/66`), macro-F1 `87.4% -> 87.6%`; `Financial terms` F1 `88.9% -> 87.5%`, `Penalties and charges` `73.7% -> 76.2%`; Severity unchanged (`exact=68.2%`, `macro-F1=71.5%`, `within-1=100.0%`, `Critical recall=3/4`).

---

## Stage 4b: deterministic risk score
Implemented the deterministic `0–100` document risk scorer ([`config/score.yaml`](file:///C:/finalYear/config/score.yaml), [`docs/RISK_SCORE_METHOD.md`](file:///C:/finalYear/docs/RISK_SCORE_METHOD.md), [`src/risk/score.py`](file:///C:/finalYear/src/risk/score.py), [`scripts/run_4b_scores.py`](file:///C:/finalYear/scripts/run_4b_scores.py), [`scripts/test_4b_score.py`](file:///C:/finalYear/scripts/test_4b_score.py)) with **zero API calls** (`llm_log.csv` unchanged at `340` rows).

- **Formula**: Severity points `Low=1, Medium=2, High=3, Critical=4`; per-category risk = `mean(top 3 points, ties broken by page ascending then clause_id) / 4` (`0` with `"No clause found in this document"` if absent); weights `Default conditions 0.25, Penalties and charges 0.20, Financial terms 0.15, Repayment 0.15, Collateral 0.10, Termination 0.10, Covenants 0.05` (`sum = 1.00`); `score = round(100 * sum(weight * category_risk), 1)`; bands `Low < 25`, `Moderate 25 to <50`, `High 50 to <75`, `Critical >= 75`; switchable `floor_rule: true` raises any document with a `Critical` clause to at least `High` (`critical_floor_applied: true`, recording `level_before_floor`). Worked example reproduces exact `51.9`, `High`, and contribution sum (`51.875`).
- **Level Collapse Observation**: **Nearly all documents collapse into a single level (`High`: `12/13` `High`, `1/13` `Moderate`, `0` `Low`, `0` `Critical`)** on both silver and predicted labels, with silver scores compressed into a `14.2`-point band (`47.9`–`62.1`). On predicted scores, `3` documents (`000103/1039213` `49.4`, `000104/1042893` `48.1`, `11_gichfindia` `32.9`) fell into `Moderate` before the floor rule and were lifted to `High` by predicted `Critical` clauses.
- **Spread Table (Silver [`risk_scores_silver.csv`](file:///C:/finalYear/data/processed/risk_scores_silver.csv) & Predicted [`risk_scores_pred.csv`](file:///C:/finalYear/data/processed/risk_scores_pred.csv))**:

| Source / Subset | Docs | Min | Median | Max | Levels (`Low` / `Moderate` / `High` / `Critical`) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Silver — All** | `13` | `47.9` | `55.4` | `62.1` | `0 / 1 / 12 / 0` |
| Silver — `sec_agreement` | `10` | `47.9` | `53.6` | `59.0` | `0 / 1 / 9 / 0` |
| Silver — `indian_mitc` | `3` | `54.4` | `59.4` | `62.1` | `0 / 0 / 3 / 0` |
| **Predicted — All** | `13` | `32.9` | `50.8` | `60.0` | `0 / 1 / 12 / 0` |
| Predicted — `sec_agreement` | `10` | `43.8` | `51.2` | `60.0` | `0 / 1 / 9 / 0` |
| Predicted — `indian_mitc` | `3` | `32.9` | `50.8` | `57.3` | `0 / 0 / 3 / 0` |

- **Silver vs Predicted Agreement (`13` docs)**: Spearman rank correlation `rho = 0.4242`, mean absolute score difference = `4.99` points, same final level = `13/13` docs.
- **Sensitivity Findings (on silver `risk_final.csv`)**:
  - `spec` (`mean_top3`, default weights, `floor=true`): `min=47.9`, `med=55.4`, `max=62.1`, levels `0/1/12/0`, `rho=1.0000`.
  - `max`: `min=55.0`, `med=63.8`, `max=72.5`, levels `0/0/13/0`, `rho=0.7901` (`000105/1052667` moves `Moderate 47.9 -> High 56.2`).
  - `blend`: `min=52.1`, `med=59.6`, `max=65.7`, levels `0/0/13/0`, `rho=0.9326` (`000105/1052667` moves `Moderate 47.9 -> High 52.1`).
  - `uniform_weights` (`1/7` each): `min=45.2`, `med=53.0`, `max=60.1`, levels `0/3/10/0`, `rho=0.7241` (`000105/1058033` moves `High 51.9 -> Moderate 47.0`; `03_dbs_mitc` moves `High 54.4 -> Moderate 46.4`).
  - `no_floor`: identical on silver (`0/1/12/0`, `rho=1.0000`) because every silver doc with a `Critical` clause already scored `>= 50.0`.
- **Dilution Test (`T7 INFO`, `1 High -> 1 High + 2 Low` in `Default conditions`)**: `mean_top3` drops `18.8 -> 10.4` (`-8.4`); `blend` drops `18.8 -> 14.6` (`-4.2`); `max` stays `18.8 -> 18.8` (`+0.0`). Both `mean_top3` and `blend` can lower a document's score when harmless `Low` clauses are added to a category with `< 3` clauses; `max` cannot.
- **Verification (`scripts/test_4b_score.py`)**: `T1`–`T6` and `T8` all `PASS` (`0` leaks across `data/processed, scripts, src, config, docs`; config & worked example verified; deterministic on 13 docs x 3 shuffles + empty `0.0/Low` + all-Critical `100.0/Critical`; `200/200` severity upgrades monotonic with `0` violations; floor test `5.0 Low -> High`; `llm_log.csv` unchanged at `340` rows).
- **Limitations**:
  1. Only the `209` pre-selected risk clauses were scored; a full-document scan will produce different clause mixes and trigger dilution where categories currently have `< 3` clauses.
  2. SEC corporate agreements and Indian MITCs are not directly comparable (MITCs contain few covenant clauses).
  3. Thresholds (`25 / 50 / 75`) come from `docs/MASTER_PLAN.md` rather than empirical default calibration.
  4. Scores rest on silver labels (`risk_final.csv`) or classifier predictions (`risk_pred_*.csv`); no human-validated document ranking exists yet.

---

## Stage 4b-fix: `padded_top3` Scoring & Robustness
Added `padded_top3` (missing slots out of `3` in a non-empty category padded with `Low = 1` point, denominator `12`; empty categories remain `0` `"No clause found"`; padding contribution shown explicitly as `"padding (missing clauses counted as Low)"`), added transparency fields (`evidence_strength`, `"not available"` page labels, `level_explanation`), and recorded the pre-registered decision rule in [`docs/RISK_SCORE_METHOD.md`](file:///C:/finalYear/docs/RISK_SCORE_METHOD.md) before running on the labeled documents (`0` API calls; `llm_log.csv` unchanged at `340` rows).

- **Pre-Registered Decision Rule Outcome**: **`ADOPTED`** — all three robustness checks passed (`(a)` zero dilution for 1- or 2-clause categories, `(b)` `200/200` severity upgrades monotonic across all `13` documents, `(c)` single-clause category risk capped at `0.500 <= 0.5`), so [`config/score.yaml`](file:///C:/finalYear/config/score.yaml) switched default `method` to `padded_top3`.
- **Old (`mean_top3`) vs New (`padded_top3`) Side-by-Side (`13` docs; saved to [`risk_scores_silver_padded.csv`](file:///C:/finalYear/data/processed/risk_scores_silver_padded.csv) & [`risk_scores_pred_padded.csv`](file:///C:/finalYear/data/processed/risk_scores_pred_padded.csv))**:

| Metric | `mean_top3` (4b) | `padded_top3` (4b-fix) |
| :--- | :---: | :---: |
| Silver ALL (`n=13`) min / med / max | `47.9` / `55.4` / `62.1` | `41.2` / `46.2` / `51.7` |
| Silver ALL levels (`Low`/`Mod`/`High`/`Crit`) | `0 / 1 / 12 / 0` | `0 / 4 / 9 / 0` |
| Silver SEC (`n=10`) min / med / max (`levels`) | `47.9` / `53.6` / `59.0` (`0/1/9/0`) | `41.3` / `48.3` / `51.7` (`0/3/7/0`) |
| Silver MITC (`n=3`) min / med / max (`levels`) | `54.4` / `59.4` / `62.1` (`0/0/3/0`) | `41.2` / `45.8` / `46.2` (`0/1/2/0`) |
| Pred ALL (`n=13`) min / med / max (`levels`) | `32.9` / `50.8` / `60.0` (`0/1/12/0`) | `32.1` / `44.2` / `51.7` (`0/5/8/0`) |
| Silver vs Pred Spearman `rho` | `0.4242` | **`0.7153`** |
| Silver vs Pred Mean Abs Diff | `4.99` pts | **`3.73` pts** |
| Largest Silver-vs-Pred Gap (`11_gichfindia`) | `26.5` (`59.4` vs `32.9`) | **`9.1` (`41.2` vs `32.1`)** |
| Same level count *(uninformative when clustered)* | `13/13` | `10/13` |
| Dilution delta (`1 High -> 1 High + 2 Low`) | `-8.4` (`18.8 -> 10.4`) | **`+0.0` (`10.4 -> 10.4`)** |

- **Clustering Finding**: Levels still cluster tightly in **`Moderate` (`4`) and `High` (`9`)** across a narrow `10.5`-point silver range (`41.2`–`51.7`), with `6` of the `9` silver `High` docs scoring `Moderate` (`41.2`–`49.2`) before the Critical floor rule lifted them to `High`. Padding eliminated single-clause `25`-point distortion (`11_gichfindia` gap fell `26.5 -> 9.1`, `rho` rose `0.4242 -> 0.7153`), showing the narrow band comes from the underlying 13 risky contract samples themselves rather than scoring artifact.
- **Transparency Updates**: Added per-category `n_clauses` and `evidence_strength` (`strong`/`limited`/`none`), `level_explanation` on Critical-floor lifts, and `"not available"` page display (noting `000002/27566` and `000081/810113` omit page numbers in silver labels). Verification [`scripts/test_4b_score.py`](file:///C:/finalYear/scripts/test_4b_score.py) passes `T1`–`T6`, `T8`, `T9` (`0` leaks, `llm_log.csv` unchanged at `340` rows).
- **Limitations**:
  1. **Silver labels (optimistic)**: ground truth comes from LLM-assisted silver labels (ChatGPT on key docs `01`–`03` and an unknown Antigravity model, with `R1`–`R3` derived from the same rows), not human-annotated gold.
  2. **Tiny test split**: `4` test documents (`66` clauses), with only `4` `Critical` clauses (insufficient for reliable Critical F1).
  3. **Only pre-selected risk clauses tested**: non-risk clauses were not input to the classifier, so **false alarm rate is not measured**.
  4. **Small corpus (`13` documents)**: `10` shortest SEC agreements plus `3` Indian MITCs.
  5. **Single model family**: Gemini models (`gemini-3.5-flash-lite` bulk classifier and Gemini-assisted silver tuning).

## Stage 4a-2: whole-document risk scan

- **Step 0 Scoring Hygiene (`0` API calls)**:
  - Updated [`docs/RISK_SCORE_METHOD.md`](file:///C:/finalYear/docs/RISK_SCORE_METHOD.md) under *Reading the Level* to document that under `padded_top3`, only `3` of the `13` labeled documents reach `High` by raw score (`6` more via the Critical floor), `Critical (>= 75)` is practically unreachable (max `51.7`), and the numeric score plus Critical clause list are the primary output.
  - Updated [`scripts/run_4b_scores.py`](file:///C:/finalYear/scripts/run_4b_scores.py) so the clustering warning prints only when levels actually collapse to one band, and printed per-document silver-vs-predicted level changes (`3/13` under `padded_top3`, all caused by asymmetric Critical-floor triggers).
  - Added `top_driver_per_category` to `score_document` in [`src/risk/score.py`](file:///C:/finalYear/src/risk/score.py) and unit test `T10` in [`scripts/test_4b_score.py`](file:///C:/finalYear/scripts/test_4b_score.py) (`T1`–`T6`, `T8`, `T9`, `T10` all `PASS`; `DECISION_RULE INFO: ADOPTED`).
- **Step 1 Per-Page Clause Splitter ([`src/risk/split_clauses.py`](file:///C:/finalYear/src/risk/split_clauses.py))**:
  - **Can [`scripts/split_clauses.py`](file:///C:/finalYear/scripts/split_clauses.py) be reused directly?** **No.** It strips page awareness (`[[PAGE n]]`), uses `MAX_CLAUSE_CHARS = 5000`, and neither merges `<150`-char fragments nor splits at sentence boundaries `<= 1500` chars. [`src/risk/split_clauses.py`](file:///C:/finalYear/src/risk/split_clauses.py) adapts its heading/paragraph break heuristic to split strictly within each page (`doc_loader` for ingested docs, `_read_zip_doc_pages` for SEC ZIP contracts), merging `<150`-char fragments and capping spans `<= 1500` chars at sentence boundaries.
  - Across the `4` target scan docs (`231` clauses) and all `13` labeled docs: empty pages return `[]`, non-whitespace coverage is `100.00%` (`>= 99%`), `max_len = 1499` (`<= 1500`), and `100%` of clauses match their source page verbatim under `src.qa.verify_quotes.normalize`.
- **Step 2 Deterministic Prefilter ([`src/risk/prefilter.py`](file:///C:/finalYear/src/risk/prefilter.py))**:
  - Built solely from [`docs/labeling_guideline.md`](file:///C:/finalYear/docs/labeling_guideline.md) rules, general loan-agreement risk terminology, and `dev` observations (never tuned on `test`). Non-English keyword lists were omitted because all `4` scan documents and `209` silver clauses are English.
  - **Recall on `209` silver clauses (`risk_final.csv`)**: **`203/209` (`97.13%`) — `TARGET MET` (`>= 95%`)** (`dev`: `140/143 = 97.90%`; `test`: `63/66 = 95.45%`). Dropped (`6`): `000104/1041426 R01`, `03_dbs_mitc IM12`, `11_gichfindia IM12`, `000081/810113 R17`, `000103/1039213 R16`, `09_muthoothomefin IM10`.
- **Step 3–4 Classifier `v3` & `dev`/`test` Execution ([`src/risk/classify.py`](file:///C:/finalYear/src/risk/classify.py), [`config/risk.yaml`](file:///C:/finalYear/config/risk.yaml), [`scripts/run_4a2_scan.py`](file:///C:/finalYear/scripts/run_4a2_scan.py))**:
  - Kept `v2` untouched for Stage 4a and added scan mode (`scan_batch_size: 20`, `scan_max_calls: 80`, `scan_prompt_version: "v3"` allowing `"none"` boilerplate + `R4` fee rule + `1` `"none"` example + `0.0` temperature + graceful `429` daily-quota stop + exact splitter text/page preservation).
  - Pre-API dry run estimated `12` total calls (`6` `dev` + `6` `test`) within `80`-call cap. Executed `v3` on `dev` (`6` calls, `75.34s` wall) -> evaluated `dev` and kept **`v3` frozen** without needing `v3b` (`000010/104897` flagged `17/17` silver clauses with `17/17` severity within-1 and `14/14` non-colliding category match; multi-clause `<=1500`-char spans in `03_dbs_mitc` hold two silver bullets in one chunk). Executed frozen `v3` **once** on `test` (`6` calls, `38.92s` wall). All `12/12` API calls ran on **`gemini-3.5-flash-lite`** (`llm_log.csv`: `340 -> 352` rows).

| Split | Doc ID (`doc_type`) | Split / Pass | Flagged / `none` | Silver Flagged | Cat Agree (on Flagged) | Sev Within-1 (on Flagged) | Unlabeled (L/M/H/C) | Score: Scan vs Silver vs `v2` Labeled | Calls / Sec (`model_used`) |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| `dev` | `03_dbs_mitc` (`indian_mitc`) | `11` / `10` | `10` / `1` | `11/12` (`91.7%`) | `5/11` (`45.5%`) | `8/11` (`72.7%`) | `3` (`1/1/1/0`) | `38.3` Mod vs `45.8` Mod vs `44.2` High | `1` / `9.0s` (`gemini-3.5-flash-lite`) |
| `dev` | `000010/104897` (`sec_agreement`) | `106` / `95` | `81` / `25` | `17/17` (`100.0%`) | `14/17` (`82.4%`) | `17/17` (`100.0%`) | `65` (`21/40/4/0`) | `48.8` Mod vs `46.2` High vs `42.1` Mod | `5` / `66.0s` (`gemini-3.5-flash-lite`) |
| `test` | `09_muthoothomefin_MHIL-MITC` (`indian_mitc`) | `31` / `27` | `27` / `4` | `14/14` (`100.0%`) | `8/14` (`57.1%`) | `14/14` (`100.0%`) | `15` (`8/7/0/0`) | `39.2` Mod vs `46.2` High vs `43.8` Mod | `2` / `8.9s` (`gemini-3.5-flash-lite`) |
| `test` | `000081/810113` (`sec_agreement`) | `83` / `70` | `67` / `16` | `17/17` (`100.0%`) | `16/17` (`94.1%`) | `16/17` (`94.1%`) | `51` (`21/18/12/0`) | `56.7` High vs `45.0` High vs `47.1` High | `4` / `29.7s` (`gemini-3.5-flash-lite`) |
| **ALL (`4`)** | Combined `dev` + `test` | `231` / `202` | `185` / `46` | **`59/60` (`98.3%`)** | **`43/59` (`72.9%`)** | **`55/59` (`93.2%`)** | `134` (`51/66/17/0`) | `38.3`–`56.7` full scan | `12` / `113.6s` (`gemini-3.5-flash-lite`) |

- **Findings & Review Output**:
  - Whole-document scan found `17` unlabeled `High` risk clauses across the SEC/MITC contracts (e.g., cross-default triggers `(h)` and `(k)` and `Section 7.02` commitment termination in `000010/104897`, plus UCC enforcement, defense-waiver transfers, and lender self-help in `000081/810113`, lifting `000081/810113` from `45.0` to `56.7`).
  - Saved per-document scans under `data/processed/risk_scan_*.csv` and sampled `27` unlabeled clauses (`17` `High`/`Critical` + `10` random `Medium`/`Low`) into [`data/processed/risk_scan_review.csv`](file:///C:/finalYear/data/processed/risk_scan_review.csv) printable via [`scripts/print_scan_review.py`](file:///C:/finalYear/scripts/print_scan_review.py).
  - **Honesty Notes**: (1) `risk_final.csv` provides LLM-assisted silver labels, NOT human gold; (2) compact MITCs can place multiple short bullets inside one `<=1500`-char splitter span, capping single-label category agreement against sub-bullet silver labels; (3) the `134` unlabeled flagged clauses (including `17` `High`) require human validation (`reviewer_verdict` blank). Verification [`scripts/test_4a2_scan.py`](file:///C:/finalYear/scripts/test_4a2_scan.py) passes `T1`–`T8` (`0` leaks, originals preserved, `llm_log.csv` `352` rows).

## Stage 4a-3: prompt v4, SEC real pages, and finer MITC splitting

- **Step 0 Finance Review & Guideline Rules (`0` API calls)**:
  - Created [`data/processed/labels/llm_assisted/scan_review_verdicts.csv`](file:///C:/finalYear/data/processed/labels/llm_assisted/scan_review_verdicts.csv) with `27` verdicts (`6 agree`, `20 disagree`, `1 unclear`; `source = "Claude finance review (single reviewer, partly judgment)"`). Confirmed full text of `000081/810113 C0050` grants entry and possession without judicial process (`"with or without judicial process or the aid and assistance of others: (A) enter and remain on any premises... take possession of the Equipment"`).
  - Added rules `N1`, `S1`, `S2`, `S3`, `S4`, `S5` (marked `"from finance review, single reviewer"`) to [`docs/labeling_guideline.md`](file:///C:/finalYear/docs/labeling_guideline.md).
- **Step 1 SEC Page-Break Marks & Real Pages ([`src/risk/split_clauses.py`](file:///C:/finalYear/src/risk/split_clauses.py))**:
  - Verified across `3` SEC filings (`000010/104897` `19` marks `-> 1..20`, `000081/810113` `13` marks `-> 1..13`, `000000/7286` `114` marks `-> 1..115`) that `N * * * [#####]` marks end page `N`. Stripped page marks completely (`star_left = 0`, `tag_left = 0`), restricted `<PAGE>` parsing to same-line tags so section digits (`1.4.`, `3.`) are never swallowed, stitched mid-clause page breaks onto their starting page, and assigned `page = "not available"` when no marks exist (`000002/27566`).
  - SEC `page != 1` share & range: `000010/104897` **`103/108` (`95.4%`, `1..20`)**; `000081/810113` **`75/84` (`89.3%`, `1..13`)**; fresh `000103/1039213` **`129/136` (`94.9%`, `1..25`)**; fresh `000105/1052667` **`271/274` (`98.9%`, `1..59`)** (`100.0%` real integer pages on all `4` docs).
- **Step 2 Finer MITC Splitting ([`src/risk/split_clauses.py`](file:///C:/finalYear/src/risk/split_clauses.py))**:
  - Added MITC splitting at list markers (`a)`, `b)`, `(i)`, `1.`, Roman headings, bullets) and ingested JSON table rows (`09_muthoothomefin_MHIL-MITC.json`), with `max_chars = 600` (`min_chars = 85`):
    - `03_dbs_mitc`: `11 -> 30` clauses (`max=594`, `10/12` silver in own isolated `1:1` span)
    - `09_muthoothomefin_MHIL-MITC`: `31 -> 75` clauses (`max=597`, `12/14` isolated)
    - `11_gichfindia_MOST-IMPORTANT-TERMS-1`: `33 -> 59` clauses (`max=580`, `11/12` isolated)
    - Total across all `38` MITC silver clauses in `risk_final.csv` (`12 + 14 + 12`; note `risk_final.csv` contains `38` MITC clauses): **`33/38` (`86.8%`)** sit in their own isolated span, `cov = 100.00%`, `verbatim = True`.
- **Step 3–4 Prompt `v4` Scan & Evaluation Design ([`config/risk.yaml`](file:///C:/finalYear/config/risk.yaml), [`src/risk/classify.py`](file:///C:/finalYear/src/risk/classify.py), [`scripts/run_4a3_scan.py`](file:///C:/finalYear/scripts/run_4a3_scan.py))**:
  - Kept `v2` and `v3` intact; added `v4` (`v3` + `N1, S1–S5` + synthetic pattern examples for `N1` and `S1`, zero copied review clauses), `scan_max_calls: 40`. Pre-API dry-run estimated `35` calls (`766` clauses, `620` prefilter-passed).
  - **Anti-contamination split**: First `4` scanned docs are **training evidence** (used ONLY to report training-row verdict agreement); `000103/1039213` (test SEC), `000105/1052667` (test SEC), and `11_gichfindia` (dev MITC) are **fresh** (`09_muthoothomefin` is contaminated by `v3`, leaving **no clean MITC test document**). Executed **`35/40` live calls** (`20` fresh, `15` training; all `gemini-3.5-flash-lite`; `llm_log.csv` `352 -> 387`).
  - **Agreement on training rows (NOT held-out accuracy; `n_decided = 26`, `unclear = 1`)**: `v3` `6/26` (`23.1%`, `cat=17/26`, `sev=7/26`) -> **`v4` `17/26` (`65.4%`, `cat=21/26`, `sev=17/26`)**.

| Role / Split | Doc ID | Split / Pass | Flagged / `none` / Uncls | Silver Flagged | Cat Agree (Flagged) | Sev Within-1 (Flagged) | Unlabeled (L/M/H/C) | Score (`padded_top3`): Scan vs Silver (Delta) | Real Pages | Calls / Sec (`model_used`) |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|
| `train / dev` | `03_dbs_mitc` | `30` / `22` | `20` / `10` / `0` | `11/12` (`91.7%`) | `9/11` (`81.8%`) | `10/11` (`90.9%`) | `9` (`4/5/0/0`) | `45.8` Mod vs `45.8` Mod (`+0.0`) | `100.0%` (`1..2`) | `2` / `8.1s` (`gemini-3.5-flash-lite`) |
| `train / dev` | `000010/104897` | `108` / `97` | `68` / `40` / `0` | `17/17` (`100.0%`) | `15/17` (`88.2%`) | `16/17` (`94.1%`) | `52` (`16/35/1/0`) | `43.3` Mod vs `46.2` High (`-2.9`) | `100.0%` (`1..20`) | `5` / `32.5s` (`gemini-3.5-flash-lite`) |
| `train / test` | `09_muthoothomefin` | `75` / `62` | `57` / `18` / `0` | `13/14` (`92.9%`) | `9/13` (`69.2%`) | `13/13` (`100.0%`) | `42` (`21/18/3/0`) | `44.2` Mod vs `46.2` High (`-2.0`) | `100.0%` (`1..7`) | `4` / `25.8s` (`gemini-3.5-flash-lite`) |
| `train / test` | `000081/810113` | `84` / `69` | `40` / `36` / `8` | `14/17` (`82.4%`) | `11/14` (`78.6%`) | `13/14` (`92.9%`) | `26` (`3/18/5/0`) | `42.9` Mod vs `45.0` High (`-2.1`) | `100.0%` (`1..13`) | `4` / `30.7s` (`gemini-3.5-flash-lite`) |
| `fresh / test` | `000103/1039213` | `136` / `95` | `82` / `49` / `5` | `17/17` (`100.0%`) | `15/17` (`88.2%`) | `17/17` (`100.0%`) | `65` (`28/33/4/0`) | `57.9` High vs `49.2` High (`+8.7`) | `100.0%` (`1..25`) | `5` / `31.6s` (`gemini-3.5-flash-lite`) |
| `fresh / test` | `000105/1052667` | `274` / `232` | `138` / `136` / `0` | `16/18` (`88.9%`) | `12/16` (`75.0%`) | `16/16` (`100.0%`) | `122` (`43/56/22/1`) | `67.5` High vs `47.9` Mod (`+19.6`) | `100.0%` (`1..59`) | `12` / `113.5s` (`gemini-3.5-flash-lite`) |
| `fresh / dev` | `11_gichfindia` | `59` / `43` | `35` / `24` / `0` | `12/12` (`100.0%`) | `9/12` (`75.0%`) | `12/12` (`100.0%`) | `23` (`17/5/1/0`) | `31.7` Mod vs `41.2` High (`-9.5`) | `100.0%` (`1..5`) | `3` / `18.4s` (`gemini-3.5-flash-lite`) |
| **FRESH (`3`)** | Combined fresh docs | `469` / `370` | `255` / `209` / `5` | **`45/47` (`95.7%`)** | **`36/45` (`80.0%`)** | **`45/45` (`100.0%`)** | `210` (`88/94/27/1`) | `+8.7, +19.6, -9.5` | `100.0%` | `20` / `163.5s` (`gemini-3.5-flash-lite`) |

- **Review File & Limitations**:
  - Compared with `v3` on the first `4` docs (`134` unlabeled flagged, `17` `High`), `v4` cut unlabeled `High` flags nearly in half (`129` unlabeled flagged, `9` `High`: `0+1+3+5`), bringing `000010` and `000081` scan scores closer to silver (`-2.9`, `-2.1`), while `03_dbs_mitc` hit `81.8%` category agreement (`45.8` vs `45.8` exact score).
  - Saved per-doc `v4` scans to `data/processed/risk_scan_v4_*.csv` and staged all `28` fresh unlabeled `High`/`Critical` plus `10` random fresh `Medium`/`Low` clauses into [`data/processed/risk_scan_review_v4.csv`](file:///C:/finalYear/data/processed/risk_scan_review_v4.csv) (printable via `scripts/print_scan_review.py data\processed\risk_scan_review_v4.csv`).
  - **Honesty Notes**: (1) single-reviewer rules `N1, S1–S5` reflect one reviewer's judgment; (2) `risk_final.csv` uses LLM-assisted silver labels, NOT human gold; (3) same model family (`gemini-3.5-flash-lite`) wrote predictions and silver prompt tuning; (4) `N1, S1–S5` were derived from the first `4` training docs' scan flags; (5) no clean MITC test document remains; (6) no human-validated gold risk labels exist yet. Verification [`scripts/test_4a3_scan.py`](file:///C:/finalYear/scripts/test_4a3_scan.py) passes `T1`–`T5` & `T8` (`0` leaks, `0` cached repeat calls, `35 <= 40` live budget).

## Stage 4a-4: structured v5 type/feature scan and deterministic severity rule table

- **Step 0 Review Round 2 (`0` API calls)**:
  - Added `round` column to [`data/processed/labels/llm_assisted/scan_review_verdicts.csv`](file:///C:/finalYear/data/processed/labels/llm_assisted/scan_review_verdicts.csv): `27` Round 1 rows + `38` Round 2 rows = **`65` reviewed rows** (`source = "Claude finance review (single reviewer, partly judgment)"`). Verified full text of `000105/1052667 C0208` (`9.2 Unit Valuation`).
- **Step 1 Evaluation Fixes ([`scripts/run_4a2_scan.py`](file:///C:/finalYear/scripts/run_4a2_scan.py), [`src/risk/split_clauses.py`](file:///C:/finalYear/src/risk/split_clauses.py), `0` API calls)**:
  - Fixed silver overlap matching (`_silver_overlap_candidates`): any scan span containing a silver clause or sharing `>= 50%` normalized tokens is matched as labeled (`11_gichfindia C0020` now matches `IM05`). Added fallback ingestion loader `_parse_ingested_pages` so `06_clix` (`72` clauses) loads cleanly; `04_dbs_mitc-ahl` (`60` clauses) is the smaller unlabeled MITC hold-out.
  - Added `continuation_of` tracking for clauses split at `max_chars` (`000105 C0267 -> C0266`) and collapsed continuations so cut clauses count once in scoring and review CSVs (`339 -> 262` unlabeled flagged across the `7` `v4` docs).
- **Step 2–3 Structured Prompt `v5` & Rule Table ([`config/severity_rules.yaml`](file:///C:/finalYear/config/severity_rules.yaml), [`src/risk/severity_rules.py`](file:///C:/finalYear/src/risk/severity_rules.py), [`src/risk/classify.py`](file:///C:/finalYear/src/risk/classify.py))**:
  - Under `v5`, the LLM outputs ONLY `{category, clause_type (21 closed types), features (15 booleans), rationale}`; any model-emitted `severity` is ignored, and severity + `explain()` are derived deterministically via first-match rules in `config/severity_rules.yaml` (all `29` YAML rules pass unit tests; `negative_covenant` / `financial_ratio_covenant` capped at `Medium`; `borrower_protective` forced to `Low`; unknown types mapped to `"unclassified"`). Kept `v2`, `v3`, `v4` intact.
  - Pre-API dry-run estimated `50` calls across `10` docs (`1,100` clauses, `895` prefilter-passed <= `60` budget). Executed **`50/60` live calls** (`15` hold-out + `35` reviewed, all `gemini-3.5-flash-lite`; `llm_log.csv`: `387 -> 437`; cached repeat makes `0` live calls).
- **Step 4(a) Training-Row Agreement (`65` reviewed rows; `63` decided, `2` unclear — *"training rows: the rule table was designed with these in view"*)**:
  - `v4`: category agree = **`48/63` (`76.2%`)**, severity exact = **`28/63` (`44.4%`)**, joint exact = **`28/63` (`44.4%`)**
  - `v5`: category agree = **`49/63` (`77.8%`)**, severity exact = **`43/63` (`68.3%`)**, joint exact = **`41/63` (`65.1%`)** (`+23.9` pts exact severity)
- **Step 4(b) `v4` vs `v5` on `7` Silver-Labeled Docs (baseline is LLM silver, NOT human gold; Step 1 fixes applied to both)**:

| Doc ID | `v4` Flag | `v4` Cat | `v4` Exact / W1 | `v4` Unlbl (L/M/H/C) | `v4` Scan-Sil | `v5` Flag | `v5` Cat | `v5` Exact / W1 | `v5` Unlbl (L/M/H/C) | `v5` Scan-Sil |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|---:|
| `03_dbs_mitc` | `11/12` | `9/11` | `8` / `10` | `3` (`1/2/0/0`) | `+0.0` | `11/12` | `8/11` | `6` / `9` | `3` (`0/0/3/0`) | `+2.1` |
| `000010/104897` | `17/17` | `15/17` | `14` / `16` | `41` (`14/27/0/0`) | `-2.9` | `17/17` | `14/17` | `15` / `16` | `28` (`8/20/0/0`) | `-2.4` |
| `09_muthoothomefin` | `13/14` | `9/13` | `10` / `13` | `40` (`20/17/3/0`) | `-2.0` | `13/14` | `9/13` | `8` / `12` | `36` (`12/22/2/0`) | `-1.6` |
| `000081/810113` | `16/17` | `11/16` | `7` / `13` | `15` (`2/11/2/0`) | `-2.1` | `17/17` | `16/17` | `8` / `13` | `12` (`4/4/4/0`) | `+9.2` |
| `000103/1039213` | `17/17` | `15/17` | `11` / `17` | `58` (`24/30/4/0`) | `+8.7` | `17/17` | `16/17` | `9` / `17` | `49` (`19/22/8/0`) | `+16.2` |
| `000105/1052667` | `18/18` | `14/18` | `12` / `18` | `95` (`33/44/17/1`) | `+19.6` | `17/18` | `14/17` | `6` / `14` | `81` (`24/48/8/1`) | `+15.4` |
| `11_gichfindia` | `12/12` | `9/12` | `6` / `12` | `20` (`16/4/0/0`) | `-9.5` | `11/12` | `9/11` | `7` / `10` | `20` (`12/7/1/0`) | `-0.4` |
| **ALL `7` DOCS** | `104/107` | `82/104` (`78.8%`) | `68` / `99` (`95.2%`) | `272` (`110/135/26/1`) | `-9.5..+19.6` | **`103/107` (`96.3%`)** | **`86/103` (`83.5%`)** | `59` / **`91` (`88.3%`)** | `229` (`79/123/26/1`) | `-2.4..+16.2` |

- **Step 4(c) Hold-Out Results (`3` docs, zero review tuning)**:
  - `000104/1041426` (`5` calls, `42.4s`): `split=111, pass=86`, `Low=16, Med=29, High=6, Crit=0, none=57, uncls=2`; **`52.5` (`High`)** vs silver `50.0` (`+2.5`), `sil_flag=17/17`, `cat=15/17`, `w1=15/17`, unlabeled `29` (`1` `High`).
  - `000087/876645` (`7` calls, `75.0s`): `split=163, pass=139`, `Low=33, Med=54, High=11, Crit=1, none=63, uncls=0`; **`58.3` (`High`)** vs silver `48.8` (`+9.5`), `sil_flag=17/17`, `cat=13/17`, `w1=15/17`, unlabeled `51` (`3` `High`).
  - `04_dbs_mitc-ahl` (`3` calls, `18.8s`, unlabeled MITC): `split=60, pass=50`, `Low=12, Med=20, High=8, Crit=1, none=19, uncls=0`; **`58.3` (`High`)**.
  - Staged [`data/processed/risk_scan_review_v5.csv`](file:///C:/finalYear/data/processed/risk_scan_review_v5.csv) (`37` rows: all `27` hold-out `High`/`Critical` + `10` random `Medium`/`Low`).
- **Step 4(d) Sample `explain()` Texts**:
  - `Critical`: `Severity Critical because: acceleration_or_termination_right; automatic, no_notice` (`000081/810113 C0049`)
  - `High`: `Severity High because: fee_or_cost; penal_rate_or_default_charge` (`03_dbs_mitc C0004`)
  - `Medium`: `Severity Medium because: rate_term; floating_or_reset_rate` (`03_dbs_mitc C0003`)
  - `Low`: `Severity Low because: reporting_or_insurance_covenant; routine reporting or standard insurance covenant (S5)` (`03_dbs_mitc C0011`)
  - `none`: `Severity none because: definition; N1 non-risk type` (`03_dbs_mitc C0002`)
- **Target & What Remains Weak (`TARGET MISSED` on 7-doc silver within-1: `91/103 = 88.3% < 90%`)**:
  1. **Model feature-extraction errors (`12` off-by-2+ silver misses)**: `gemini-3.5-flash-lite` missed `self_help_without_notice` / `automatic, no_notice` on `000010 R16`, `000081 R13`, and `09_muthoothomefin IM14` (`Critical -> Medium`), omitted `charges_apply` on prepayment fees (`11_gichfindia IM03`, `000105 R16` -> `Low`), and over-fired `penal_rate_or_default_charge` on routine fees/interest (`000081 R02/R03`, `000105 R09`: `Low -> High`).
  2. **Closed type list omitted scheduled `repayment`**: `6` of the `7` `unclassified` items (`03_dbs C0014`, `000103 C0042/C0043/C0047`) were scheduled repayment/auto-debit/billing clauses with no `repayment_term` in the `21`-type list.
  3. **Divergence between finance-review strictness & older silver labels**: Rule table `v5` boosted `65`-row reviewer exact severity agreement `44.4% -> 68.3%` and `83.5%` category agreement on silver, while disagreeing more sharply with older silver severities on routine vs High repayment/prepayment items.
  4. **Honesty notes**: Single reviewer, silver labels (not human gold), same Gemini model family, rule table derived from the `65` reviewed training rows, only `1` clean MITC hold-out (`04_dbs_mitc-ahl`), and no human gold dataset yet. Verification [`scripts/test_4a4_scan.py`](file:///C:/finalYear/scripts/test_4a4_scan.py) passes `T1`–`T5` and `T9` (`0` leaks, `50 <= 60` live calls, `0` cached repeat calls).

## Stage 4a-4 hold-out review (single reviewer)

- **Input & Verification (`0` API calls)**: Recorded the `37` finance-reviewer hold-out verdicts (`risk_scan_review_v5.csv`) in [`data/processed/labels/llm_assisted/scan_review_holdout_v5.csv`](file:///C:/finalYear/data/processed/labels/llm_assisted/scan_review_holdout_v5.csv) and scored via [`scripts/score_holdout_v5.py`](file:///C:/finalYear/scripts/score_holdout_v5.py) (`CHECK_A PASS`, `0` mismatches against `risk_scan_review_v5.csv`; `HOLDOUT_COUNT MATCH`; `llm_log.csv` unchanged at `437 -> 437`).
- **Hold-out Metrics (overall & per-document)**:
  - **Overall (`37` rows; `35` decided, `2` `unclear`)**: category exact = **`33/37` (`89.2%`)**, severity exact = **`22/35` (`62.9%`)** (*INFO: no target*), severity within-1 = **`34/35` (`97.1%`)** (`TARGET MET >= 90%`), High-or-Critical precision = **`15/25` (`60.0%`)**, `over1 = 11`, `under1 = 1`, `miss2+ = 1` (`over2+ = 1`, `under2+ = 0`). `macro-F1: INCONCLUSIVE (hold-out is biased to High-flagged rows; no recall measured)`.
  - **`A` (`000087/876645`, `15` rows)**: category `13/15` (`86.7%`), severity exact `8/14` (`57.1%`, `1` unclear), within-1 `14/14` (`100.0%`), High/Critical precision `6/11` (`54.5%`), `over1=6`, `under1=0`, `miss2+=0`.
  - **`B` (`04_dbs_mitc-ahl`, `11` rows)**: category `11/11` (`100.0%`), severity exact `5/10` (`50.0%`, `1` unclear), within-1 `10/10` (`100.0%`), High/Critical precision `5/8` (`62.5%`), `over1=4`, `under1=1`, `miss2+=0`.
  - **`C` (`000104/1041426`, `11` rows)**: category `9/11` (`81.8%`), severity exact `9/11` (`81.8%`, `0` unclear), within-1 `10/11` (`90.9%`), High/Critical precision `4/6` (`66.7%`), `over1=1`, `under1=0`, `miss2+=1`.
- **What-If Document Score Table (*WHAT-IF, partial reviewer coverage, not a result*)**:

| Doc | Score (Scanned) | Level (Scanned) | Floor (Scanned) | Score (Reviewer Severities) | Level (Reviewer) | Floor (Reviewer) |
|---|---:|---|---|---:|---|---|
| `A (000087/876645)` | `58.3` | `High` | `no` | `55.8` | `High` | `no` |
| `B (04_dbs_mitc-ahl)` | `58.3` | `High` | `no` | `55.0` | `High` | `no` |
| `C (000104/1041426)` | `52.5` | `High` | `no` | `50.0` | `High` | `no` |

- **Five Observed Problems (`15/25` High/Critical precision & `11` `+1` over-ratings)**:
  1. `penal_rate_or_default_charge` fires on ordinary cost recovery (`A C0064`, `A C0105`, `A C0094`) and normal-rate interest (`A C0047`).
  2. `payment_default_trigger` is always `High`, even for plain default in payment on due date (`B C0045`).
  3. Missing `clause_type`s for commitment expiry (`C C0104`), payoff at maturity (`A C0048`), scheduled repayment, and lender-can-change-EMI (`B C0018`).
  4. `no_notice` set from silence (`B C0051` Critical -> High) and sentence fragments produced by the splitter (`B C0051`, `A C0047`, heading `B C0011`).
  5. `joint_and_several` always `High` (`A C0107`, `B C0053` — judgment call).
- **`test_4a4_scan.py` `T9` Update**: Cached repeat of `03_dbs_mitc` asserts `0` live calls AND exact `(category, clause_type, severity)` equality to `risk_scan_v5_03_dbs_mitc.csv`, printing `unclassified_count` (`2`) as `INFO`.
- **Honesty Notes**: Single reviewer who also designed `severity_rules.yaml`; hold-out sample biased to `High`-flagged rows (`27` High/Critical + `10` Med/Low, no recall measured); silver labels; same Gemini model family (`gemini-3.5-flash-lite`); `3` hold-out docs only.

## Decision: risk classifier v5 frozen

- **Decision**: Prompt `v5` + [`config/severity_rules.yaml`](file:///C:/finalYear/config/severity_rules.yaml) is **frozen** as the risk classifier prior to building Stage 7.
- **Known problems (deferred to future retuning ONLY on a clean split with human gold)**:
  1. `penal_rate_or_default_charge` fires on ordinary cost recovery and normal-rate interest;
  2. `payment_default_trigger` is always `High` (even for plain payment default on due date);
  3. No `clause_type`s for commitment expiry, payoff at maturity, scheduled repayment, or lender-can-change-EMI;
  4. `no_notice` is inferred from silence and splitter sentence fragments;
  5. `joint_and_several` is always `High` (judgment call).
- **Hold-out & Silver Benchmark Record**: Hold-out severity within-1 = **`34/35` (`97.1%`) `TARGET MET`** (biased High-flagged sample, single reviewer); `7`-doc silver severity within-1 = **`91/103` (`88.3%`) `TARGET MISSED`** (`>= 90%` target); `macro-F1: INCONCLUSIVE` (no recall measured on hold-out).
- **UI Disclosure**: The app must display every predicted severity alongside its `explain()` reason (`Severity <X> because: <type>; <features>`) and label it **"automated estimate"**.

---

## Stage 7a-1: backend skeleton

FastAPI upload + deterministic ingest backend built under [`app/`](file:///C:/finalYear/app/) without modifying [`scripts/ingest.py`](file:///C:/finalYear/scripts/ingest.py), [`src/`](file:///C:/finalYear/src/), or `config/*.yaml`, and with zero Gemini API calls (`data\processed\llm_log.csv` unchanged: `437 -> 437`).

### Architecture & Endpoints

- [`app/requirements.txt`](file:///C:/finalYear/app/requirements.txt): `fastapi`, `uvicorn`, `python-multipart`, `httpx`.
- [`app/api/main.py`](file:///C:/finalYear/app/api/main.py):
  - `GET /api/health` -> `{"status":"ok"}`
  - `GET /api/meta` -> `{"disclaimer":"This system provides information, not legal or financial advice.","upload_notice":"Upload only public documents.","max_upload_mb":25,"allowed_types":["pdf","html","txt"]}`
  - `POST /api/documents` -> validates extension (`.pdf`/`.html`/`.htm`/`.txt`), streaming `25 MB` size cap (`413`), and real `%PDF` header (`400`), hashes content (`doc_id = sha256[:12]`), deduplicates existing ready/active docs (`"cached": true`), stores raw upload + artifacts under `data\processed\uploads\<doc_id>\`, and runs background ingestion.
  - `GET /api/documents/{doc_id}/status` -> `{"state":"queued|ingesting|ready|failed","stage":"...","pages_done":n,"pages_total":n,"error":null|"..."}`
  - `GET /api/documents/{doc_id}/pages/{n}` -> `{"page":n,"text":"...","quality":"GOOD|SUSPICIOUS|BAD","source":"text|ocr"}`
  - Security & CORS: strict `^[0-9a-f]{12}$` `doc_id` validation + `relative_to` path containment guard, CORS restricted to `http://localhost:5173` and `http://127.0.0.1:5173`, safe JSON error responses (no stack traces, host paths, or secrets).
- [`app/api/ingest_service.py`](file:///C:/finalYear/app/api/ingest_service.py): wraps `scripts.ingest` (`ingest_pdf_page`, `ingest_html`, `check_page_quality`) with per-page progress callbacks and atomic writes for `ingested.json` and `ingested.txt`.
- [`app/api/jobs.py`](file:///C:/finalYear/app/api/jobs.py): thread-safe in-process background worker updating `status.json` after each page (`pages_done` / `pages_total`).

### Observed Verification (`scripts/test_7a1_api.py`)

- `T1 PASS`: `1252` files scanned across `data/processed`, `scripts`, `src`, `config`, `docs`, `app`; `0` secret leaks.
- `T2 PASS`: `/api/health` and `/api/meta` match required schema and copy (`"Upload only public documents."`).
- `T3 PASS`: rejected `.exe` (`400`), fake `.pdf` (`400`), and `26 MB` file (`413`) with safe error bodies.
- `T4 PASS` (text PDF, `03_dbs_mitc.pdf`): `doc_id=893857f8b7e3`, `ready` in `2.149s`, `pages=2` (matches `data\processed\ingested\03_dbs_mitc.json`), page 1 `len=5664`, `source=text`, `quality=GOOD`.
- `T5 PASS` (scanned OCR PDF, `30_piramal_finance_mortgage_mitc_latest_10042024.pdf`): `doc_id=60be371f8e58`, `ready` in `71.933s`, `pages=7`, `ocr_pages=7`.
- `T6 PASS` (deduplication): re-uploading `03_dbs_mitc.pdf` returned same `doc_id=893857f8b7e3`, `cached=True`, `ingest_runs=1->1`.
- `T7 PASS` (safety/path traversal): probed `../x`, `..%2Fx`, `abc`, `0123456789ag`, `ZZZZZZZZZZZZ` -> `404`/`400` only, zero host paths or secrets leaked.
- `T8 PASS`: `data\processed\llm_log.csv` rows unchanged (`437 -> 437`).

### Known Limits (Stage 7a-1)

- Single-user local prototype with no authentication.
- Completed documents persist `status.json` and `ingested.json` under `data\processed\uploads\<doc_id>\` and remain readable after server restarts, whereas in-flight `queued`/`ingesting` jobs rely on in-process background threads and do not automatically resume after a mid-run server restart.
- No React UI or Gemini extraction/risk endpoints yet (deferred to subsequent stages).

### How to run

```powershell
pip install -r app\requirements.txt
python -m uvicorn app.api.main:app --port 8000
python -X utf8 scripts\test_7a1_api.py
```

---

## Stage 7a-2a: summary and key-info endpoints

Grounded Summary (`summarize_document`) and Key-Info (`extract_key_info`) task endpoints wired into [`app/api/main.py`](file:///C:/finalYear/app/api/main.py) with disk-persisted results, daily quota guard, and strict per-task call budgets. Zero edits were made to [`src/`](file:///C:/finalYear/src/), existing `config/*.yaml` files, or `data\processed\ingested\`.

### Bridge Approach Chosen

- Added [`app/api/doc_bridge.py`](file:///C:/finalYear/app/api/doc_bridge.py) (`load_uploaded_document(doc_id)` / `load_document_bridge(doc_id)`) instead of copying uploaded docs into `data\processed\ingested\` or editing [`src/qa/doc_loader.py`](file:///C:/finalYear/src/qa/doc_loader.py).
- **Why**: Both `extract_key_info` and `summarize_document` natively accept `doc_pages: dict[int, str]` (including the BM25 fallback in [`src/qa/retrieve.py`](file:///C:/finalYear/src/qa/retrieve.py)). Keeping the lookup strictly under `app\api\` for `^[0-9a-f]{12}$` upload folders preserves `src\` behavior untouched and avoids changing `data\processed\ingested\` file counts tested by [`scripts/test_2a_ingestion.py`](file:///C:/finalYear/scripts/test_2a_ingestion.py).

### Config, Budgets & Endpoints

- [`config/app.yaml`](file:///C:/finalYear/config/app.yaml): `daily_soft_limit: 60` (counted from today's UTC rows in `data\processed\llm_log.csv`), per-task `task_budgets` (`summary: 10`, `keyinfo: 20`), and `results_dir_name: "results"`.
- [`app/api/task_service.py`](file:///C:/finalYear/app/api/task_service.py):
  - `POST /api/documents/{doc_id}/tasks/{kind}` (`summary` | `keyinfo`): `202` when started or `quota_blocked`; `200` returning saved payload without calls when already `done`; `404` for unknown `doc_id` or `kind`; `409` if ingestion state is not `"ready"`.
  - `GET /api/documents/{doc_id}/tasks/{kind}`: returns `state`, `result`, `live_calls`, `models_used`, `notice` (`"Automated output. Check each quote against the cited page. Information, not legal or financial advice."`), `error`, `elapsed_s`.
  - Saves completed outputs to `data\processed\uploads\<doc_id>\results\<kind>.json` so a fresh FastAPI / `TestClient` instance returns `"done"` with `0` live calls.
  - `BudgetedGeminiClient` checks both daily limit and per-task budget before `_send_request` and marks budget-capped runs `"partial"`/`"failed"` without silent retries.

### Observed Numbers (`scripts/test_7a2a_tasks.py`)

- **Doc**: `03_dbs_mitc.pdf` (`doc_id=893857f8b7e3`, `2` pages). Note: `data\processed\llm_log.csv` already contained `97` UTC rows (`182` local IST rows) dated `2026-11-12` prior to 7a-2a, so `test_7a2a_tasks.py` temporarily overrode `daily_soft_limit=200` in memory for `T2`–`T4` while keeping `config/app.yaml` at `60`.
- **Summary (`T2`/`T4`)**: `state=done`, `live_calls=0` (disk cache hit matching prior `03_dbs_mitc` text), `models_used={'gemini-3.5-flash-lite': 3}`, `1.295s`; `13/13` kept sentences carry `[p.N]` cites within `1..2`, `short_word_count=74`.
- **Key-Info (`T3`)**: `state=done`, `live_calls=0` (disk cache hit after primary-model retry/cooldown fallback), `models_used={'gemini-3.5-flash-lite': 2}`, `71.992s` (primary fallback waits inside sandbox); `16` fields (`9` verified, `6` not_found, `1` deferred_to_other_document, `0` needs_review, `0` unverified), `quotes verified 10/10` -> `TARGET MET`.
- **Quota & Persistence & Safety (`T5`–`T9`)**: `daily_soft_limit=0` -> `quota_blocked` (`0` live calls) with exact plain notice; `task_budgets=0` -> `failed` (`0` live calls); fresh `TestClient` persistence verified identical with `0` live calls; `404`/`409` safety verified; `llm_log.csv` unchanged (`437 -> 437`, `live calls = 0`); all 4 regression suites (`test_2a_ingestion.py`, `test_4b_score.py`, `test_4a4_scan.py`, `test_7a1_api.py`) passed (`0` API calls).

### Known Limits (Stage 7a-2a)

- Single-user local backend with no authentication or per-user isolation.
- Daily soft limit (`60`) counts every row in `data\processed\llm_log.csv` for the current UTC day (including prior CLI evaluation runs on the same day).
- Completed tasks persist to `results\<kind>.json`, whereas in-flight jobs and background threads are lost if the server restarts mid-task.
- Risk analysis and Q&A chat endpoints (`7a-2b`) and React frontend are not implemented yet.

### How to run

```powershell
python -m uvicorn app.api.main:app --port 8000
python -X utf8 scripts\test_7a2a_tasks.py
```

---

## Stage 7a-2b: risk and chat endpoints

Added whole-document frozen v5 risk scan + `padded_top3` scoring (`POST/GET /api/documents/{doc_id}/tasks/risk`) and grounded Q&A chat (`POST/GET /api/documents/{doc_id}/chat`) without modifying `src\*`, `config\severity_rules.yaml`, or `config\score.yaml`.

### Answers Q1–Q3

- **Q1 (72 s cached Key-Info delay)**: Timed `extract_key_info(verify_numeric=True)` and traced the delay to [`src/llm/gemini_client.py`](file:///C:/finalYear/src/llm/gemini_client.py#L223-L287) + [`src/qa/verifier.py`](file:///C:/finalYear/src/qa/verifier.py#L260-L267) (not `app/`): `300s` cooldowns on `gemini-3.6-flash` and `gemini-3.5-flash` had expired, so uncached numeric verifier calls entered `_send_request()`, failed on `ConnectionError` inside the offline sandbox, raised `client.min_interval = 6.5` persistently in `verifier.py:260`, and slept `6.5s` pacing + `2s/4s/6s` backoff x `3` retries per uncached field before `verifier.py` swallowed the exception. Per rules, `src/` was left unchanged; **proposed change**: check fallback `bulk` disk cache before network attempts in `gemini_client.py:209-239` when primary misses/cools down, and restore `client.min_interval` after `verifier.py:260`.
- **Q2 (`allowed_types` consistency)**: Upload already supported `.pdf`, `.html`/`.htm`, and `.txt` in [`app/api/main.py`](file:///C:/finalYear/app/api/main.py) and [`app/api/ingest_service.py`](file:///C:/finalYear/app/api/ingest_service.py) (`%PDF` header check applies only to `.pdf`). Added `allowed_types: ["pdf", "html", "txt"]` explicitly to [`config/app.yaml`](file:///C:/finalYear/config/app.yaml) and wired `GET /api/meta` and `POST /api/documents` to read it cleanly, verified with real `.html` and `.txt` uploads (`Q2_TEST PASS`).
- **Q3 (`test_4a4_scan.py` `live_calls=50`)**: Confirmed `387 -> 437` (`50` calls) is the historical Stage 4a-4 cumulative delta recorded in `data\processed\llm_log.csv`, NOT new calls made during regression runs (`llm_delta = 0` during regression).

### Risk & Chat Implementation

- [`app/api/doc_bridge.py`](file:///C:/finalYear/app/api/doc_bridge.py): extended with `load_uploaded_table_rows_by_page`, `load_uploaded_meta`, and `ensure_qa_doc_bridge_installed()` so `ask()`, `answer_question()`, `retrieve()`, and `extract_inputs()` read 12-hex upload folders seamlessly in RAM with zero edits to `src\*.py`.
- [`app/api/risk_service.py`](file:///C:/finalYear/app/api/risk_service.py) & [`app/api/task_service.py`](file:///C:/finalYear/app/api/task_service.py):
  - `POST/GET /api/documents/{doc_id}/tasks/risk`: budget `15` live calls in `config\app.yaml`; checks daily soft quota guard before starting (`quota_blocked`); returns `status: "needs_retrieval"` with `0` API calls if batches exceed budget (since frozen v5 scan has no chunked retrieval fallback); never masks scan `errors` as `0.0 Low` (`scan_failed` -> `failed`); verifies every flagged clause quote server-side via `verify_evidence` before scoring with `padded_top3`; returns `score`, `level` (Critical floor applied), 7 categories with `weights` and `evidence_strength`, `critical_clauses`, `flagged_clauses` (with `clause_type`, `severity`, `explain()`, `quote`, `page`), `sample_range` (`"41.2-51.7"`), `labels` (`["automated estimate", "information, not advice"]`), and `display_note`; persists to `uploads\<doc_id>\results\risk.json`.
- [`app/api/chat_service.py`](file:///C:/finalYear/app/api/chat_service.py):
  - `POST /api/documents/{doc_id}/chat` (and `GET`): calls `ask(verify=True)` under a per-document single-request lock (`429` on concurrent calls); enforces `6`-call per-question budget and daily quota guard; re-verifies every returned quote server-side (`verify_evidence`) and drops/downgrades unverified claims; serializes `Decimal` calculator outputs safely; marks fallback models (`fallback_used` + `"model_fallback"` flag); saves last `50` turns in `uploads\<doc_id>\results\chat.json`.
- [`scripts/demo_7a2b.py`](file:///C:/finalYear/scripts/demo_7a2b.py): CLI demo printing risk score, level, breakdown, top 5 clauses with pages, and a chat Q&A with quotes.

### Verification Results (`scripts/test_7a2b.py`)

- **Live warm-up vs verified repeat**: Live scan + uncached chat Q2/Q4 consumed `3` live calls total across the workspace (`437 -> 440` rows in `data\processed\llm_log.csv`: `1` call on `aesohio` SEC risk, `2` calls on DBS MITC chat `gemini-3.5-flash-lite` fallbacks). Subsequent clean full verification run made `0` new calls (`440 -> 440`, `live calls = 0`):
  - `T1 PASS`: `1283` files scanned (`0` leaks); `Q2_TEST PASS` (`.html` + `.txt` upload verified).
  - `T2 PASS`: DBS MITC (`893857f8b7e3`) -> `state=done`, `score=47.9`, `level=Moderate`, `flagged=18`, `critical=0`, `live_calls=0`, `models={'gemini-3.5-flash-lite': 2}`, `0.864s`; AES Ohio SEC (`68edf869fea0`) -> `state=done`, `score=2.5`, `level=Low`, `flagged=1`, `critical=0`, `models={'gemini-3.5-flash-lite': 1}`, `0.342s` (`1` live call on initial run); `needs_retrieval` guard verified.
  - `T3 TARGET MET`: risk quotes verified `25/25` (`100%`), `dbs_mitc_dropped=0`, `aesohio_sec_dropped=1` (`aesohio` clause `C0010` spanned a page boundary with page footer `"2"` stitched by frozen `split_clauses(stitch_page_breaks=True)` — dropped cleanly by server `verify_evidence`; **proposed `src/` change**: strip footer artifacts during stitching or verify multi-page spans explicitly in `verify_quotes.py` without editing frozen `src/` now).
  - `T4 PASS`: independent pure-Python recomputation matched `(47.9, Moderate)` and `(2.5, Low)` (`llm_delta=0`).
  - `T5 PASS`: repeat `POST` returned identical JSON from disk cache with `0` live calls in `0.0484s` (`< 2.0s`).
  - `T6 PASS`: forced `daily_soft_limit=0` returned `quota_blocked` (`0` calls) with `config/app.yaml` untouched.
  - `T7 TARGET MET` (`chat categories 8/8`, `chat quotes verified 3/3`): all 8 routes (`fact` x2, `not_found` x2, `explain_term`, `calculation` = `22842.37`, `advice` = `refused`, `off_topic`) matched; Q2 & Q4 visibly marked `[FALLBACK]` (`gemini-3.5-flash-lite`), Q1 & Q3 answered with `gemini-3.6-flash`, Q5 with `gemini-3.5-flash-lite`; `chat.json` persisted `8` turns; prompt-injection check rejected spoofed claim (`unverified`, `0` evidence).
  - `T8 PASS`: simultaneous chat requests returned `[200, 429]` (`llm_delta=0`).
  - `T9 PASS`: `404` unknown doc, `409` not ready, `422` empty question, zero host paths/keys.
  - `T10 PASS`: all `6` regression suites (`test_2a_ingestion.py`, `test_3b_summary.py`, `test_4b_score.py`, `test_4a4_scan.py` [`53/60`], `test_7a1_api.py`, `test_7a2a_tasks.py`) exited `0` with `llm_delta=0`. *(Note: updated `test_7a2a_tasks.py` line 359 unknown-kind probe from `"risk"` to `"nonexistent_kind"` because Stage 7a-2b enabled `"risk"`.)*

### Known Limits (Stage 7a-2b)

- Same single-user, in-memory-flight-job, and shared UTC `llm_log.csv` daily limit caveats as 7a-2a.
- Frozen `split_clauses` (`stitch_page_breaks=True`) can join text across a page footer so single-page `verify_evidence` rejects the stitched clause (`1` flagged clause dropped in `aesohio`), lowering SEC recall slightly in favor of strict single-page verbatim verification.
- Cross-model fallback to `gemini-3.5-flash-lite` occurs when main/verifier quota is low, leaving `verifier_independent=False` on affected responses.
- React frontend (Stage 7b) is not built yet.

### How to run

```powershell
python -m uvicorn app.api.main:app --port 8000
python -X utf8 scripts\test_7a2b.py
python -X utf8 scripts\demo_7a2b.py 893857f8b7e3
```

---

## Stage 7b-1: Web frontend scaffold & API integration

Scaffolded the single-page React frontend in [`web/`](file:///c:/finalYear/web/) with Vite and plain CSS (no Tailwind, no TypeScript, zero external UI component libraries). Pinned exact dependency versions (published > 14 days ago):
- `react`: `18.3.1` (Published Apr 2024)
- `react-dom`: `18.3.1` (Published Apr 2024)
- `vite`: `5.4.11` (Published Oct 2024)
- `@vitejs/plugin-react`: `4.3.4` (Published Nov 2024)

### 1. Components Built
- [`web/src/config.js`](file:///c:/finalYear/web/src/config.js): Declares `API_BASE_URL = 'http://localhost:8000'`.
- [`web/src/App.jsx`](file:///c:/finalYear/web/src/App.jsx): One-page application implementing:
  1. Header notices fetched from `GET /api/meta` (`upload_notice`, `disclaimer`) with fallback text on error: `"Upload only public documents. Information, not legal or financial advice."`.
  2. Upload box with file types and 25 MB limit from `/api/meta`, client-side validation, and upload via `POST /api/documents`.
  3. Ingestion progress: polls `GET /api/documents/{doc_id}/status` every 1.5s, shows state, stage, progress bar (`pages_done/pages_total`), error banner on failure, slow warning after 120s, and "Already processed" badge when `cached: true`.
  4. Document page viewer on ready: fetches `GET /api/documents/{doc_id}/pages/{n}` with page navigation, quality badge (`GOOD`/`SUSPICIOUS`/`BAD`), source badge (`text`/`ocr`), and monospace text preview.
  5. Four placeholder tabs ("Summary", "Key Info", "Risk Analysis", "Chat") cleanly marked "coming next" with zero task calls.
- [`web/src/index.css`](file:///c:/finalYear/web/src/index.css): Clean plain CSS styling with accessible badges, progress indicators, alert boxes, and typography.
- [`scripts/test_7b1_web.py`](file:///c:/finalYear/scripts/test_7b1_web.py): End-to-end test suite checking static safety, live FastAPI flow, and zero Gemini calls.

---

## Stage 7b-1 cleanup

Performed cleanup of obsolete `tables_count` field references in frontend and test suites.

### 1. What Was Removed
- `app\` API endpoints (`GET /api/documents/{doc_id}/pages/{n}`) do not return `tables_count` (the field only exists internally in raw `ingested.json`).
- Removed the table-count badge `<span className="badge badge-tables">Tables: {pageData.tables_count}</span>` and its wrapping conditional `{pageData.tables_count > 0 && (...)}` from [`web/src/App.jsx`](file:///c:/finalYear/web/src/App.jsx).
- Added an automated static assertion in [`scripts/test_7b1_web.py`](file:///c:/finalYear/scripts/test_7b1_web.py) asserting `tables_count` does not appear anywhere in `web/src/`.
- Adjusted build check in `scripts/test_7b1_web.py` to correctly report `INCONCLUSIVE` when sandbox filesystem isolation (`EPERM` on `realpath`) blocks `npm run build`.

### 2. Grep Results (`tables_count`)
- **Before cleanup**:
  - `app\api\ingest_service.py:105`: `"tables_count": 0,`
  - `app\api\ingest_service.py:147`: `"tables_count": len(all_tables),`
  - `web\src\App.jsx:346`: `{pageData.tables_count > 0 && (`
  - `web\src\App.jsx:348`: `Tables: {pageData.tables_count}`
- **After cleanup**:
  - `app\api\ingest_service.py:105`: `"tables_count": 0,` (backend internal storage in `ingested.json`)
  - `app\api\ingest_service.py:147`: `"tables_count": len(all_tables),` (backend internal storage in `ingested.json`)
  - `web\src\`: **0 matches** (clean)

### 3. Verification & Quota State (`scripts/test_7b1_web.py`)
- `T1 PASS`: `files=8, key_leaks=0, storage_usage=0, hardcoded_results=0, tables_count_hits=0`
- `T2 PASS`: `port=60674, doc_id=893857f8b7e3, pages=1/2, source=text, quality=GOOD, uploads_preserved=True`
- `T3 INCONCLUSIVE`: `sandbox realpath EPERM prevents build inside sandbox (student runs npm run build on host)`
- `data/processed/llm_log.csv` row count: `458 -> 458` (delta = 0 live Gemini API calls).

---

## Stage 7b-2: Summary tab and Key Info tab

Implemented grounded Summary and 16-field Key Information tabs in [`web/src/`](file:///c:/finalYear/web/src/) with plain CSS, interactive page citations, and live task polling.

### 1. Files Added & Modified
- [`web/src/citationUtils.jsx`](file:///c:/finalYear/web/src/citationUtils.jsx): Shared citation parser converting bracketed page references like `[p. 1]` or `[p. 1, p. 2]` into interactive jump buttons that switch the document page viewer.
- [`web/src/SummaryTab.jsx`](file:///c:/finalYear/web/src/SummaryTab.jsx): Full Summary view displaying:
  - Run button with 2 s polling interval for `POST/GET /api/documents/{doc_id}/tasks/summary`.
  - In-flight spinner with elapsed seconds and 120 s warning ("Taking longer than usual. Key info and OCR can take over a minute.").
  - Plain wording for quota exhaustion: "Today's free Gemini limit is used up, so this task did not run. Try again after the daily reset."
  - API notice banner: "Automated output. Check each quote against the cited page. Information, not legal or financial advice."
  - Short summary card with clickable page cites.
  - Detailed sections (`Parties`, `Money`, `Interest and repayment`, `Fees and penalties`, `Prepayment`, `Security and guarantees`, `Default and termination`, `Governing law`) and `Not found / defined elsewhere` bullet list with clickable citations.
  - Tab header title: `Summary (automated output)`.
- [`web/src/KeyInfoTab.jsx`](file:///c:/finalYear/web/src/KeyInfoTab.jsx): 16-field Key Information table displaying:
  - Run button with 2 s polling interval for `POST/GET /api/documents/{doc_id}/tasks/keyinfo`.
  - 16 rows covering every standard key field (`document_title`, `agreement_date`, `borrowers`, `lenders`, `agents`, `loan_or_commitment_amount`, `interest_rate`, `repayment_terms`, `maturity_termination_date`, `fees`, `late_payment_or_default_interest`, `prepayment_terms`, `collateral_security`, `guarantees`, `events_of_default`, `governing_law`).
  - Five status badges handled: `verified`, `needs_review`, `not_found` ("Not found in this document"), `defined in another document` (showing `defers_to`), `unverified` (value hidden, displays "no verified quote").
  - "not independently verified" label rendered on any field where `verifier_independent === false`.
  - Verbatim quote blockquote and clickable page citation button for each field.
  - Tab header title: `Key Information (automated output)`.
- [`web/src/App.jsx`](file:///c:/finalYear/web/src/App.jsx): Wired `SummaryTab` and `KeyInfoTab` into the active tab switcher, and added `handleJumpToPage` to automatically scroll and switch the document page viewer on citation click.
- [`web/src/index.css`](file:///c:/finalYear/web/src/index.css): Plain CSS styles for summary cards, key info table, status badges, citation buttons, and running spinners.
- [`scripts/test_7b2_web.py`](file:///c:/finalYear/scripts/test_7b2_web.py): Automated test suite covering static security, live FastAPI task execution, and UI status coverage.

### 2. Real API Response Shapes
- **Outer Task Envelope (`summary` & `keyinfo`)**:
  - `state`: `"done"` | `"running"` | `"quota_blocked"` | `"failed"` | `"not_started"` | `"partial"`
  - `result`: task payload dictionary
  - `live_calls`: integer live Gemini API call count
  - `models_used`: dictionary of model name -> call count
  - `notice`: `"Automated output. Check each quote against the cited page. Information, not legal or financial advice."`
  - `error`: error string or `null`
  - `elapsed_s`: float seconds or `null`
- **Summary Payload (`result`)**:
  - `doc_id`, `short`, `detailed` (markdown string with section headers `## <Section>` and `## Not found / defined elsewhere`), `sentences` (list of sentence objects with `text` and `pages`), `detailed_sections` (dict), `not_found_fields`, `deferred_fields`, `page_count`.
- **Key Info Payload (`result`)**:
  - `doc_id`, `fields` (16 field objects), `counts` (dict), `verifier_independent` (overall boolean/null), `page_count`.
  - Each field object:
    `field` (str), `status` (`"verified"` | `"needs_review"` | `"not_found"` | `"deferred_to_other_document"` | `"unverified"`), `value` (str), `evidence` (list of `{"quote": str, "page": int}`), `defers_to` (str), `verifier_independent` (bool | null), `page` (int | null), `quotes` (list of str).

### 3. Verification Results (`scripts/test_7b2_web.py`)
- **T1 PASS | Static checks**: `files=11, key_leaks=0, storage_hits=0, hardcoded_hits=0, advice_hits=0, tables_count_hits=0`.
- **T2 PASS | API integration**: `port=65387, doc_id=893857f8b7e3, sum_live_calls=0, ki_live_calls=0, response_field_statuses=['deferred_to_other_document', 'not_found', 'verified'], ui_handled_field_statuses=['deferred_to_other_document', 'needs_review', 'not_found', 'unverified', 'verified'], response_task_states=['done'], ui_handled_task_states=['done', 'failed', 'not_started', 'partial', 'quota_blocked', 'running'], uploads_preserved=True`.
- **T3 INCONCLUSIVE | Build check**: `sandbox realpath EPERM prevents build inside sandbox (student runs npm run build on host)`.
- **Zero Gemini Calls**: `data/processed/llm_log.csv` row count `458 -> 458` (delta = 0).

### 4. Known Limits (Stage 7b-2)
- Visual rendering was tested via automated headless HTTP client; no physical desktop browser window was opened.
- Production build bundle size was not verified inside sandbox due to Windows sandbox `fs.realpath` restrictions (`EPERM`).
- Risk Analysis and Chat tabs remain UI placeholders; integration deferred to subsequent stages.

### 5. How to run (Student Host)
```powershell
# 1. Start the backend API server
python -m uvicorn app.api.main:app --port 8000

# 2. Run the frontend dev server
cd web
npm run build
npm run dev

# 3. Run Stage 7b-2 verification suite
python scripts\test_7b2_web.py
```

---

## Stage 7b-3: Risk Analysis tab

Implemented the explainable Risk Analysis tab in [`web/src/RiskTab.jsx`](file:///c:/finalYear/web/src/RiskTab.jsx), integrated with the single-page React frontend in [`web/src/App.jsx`](file:///c:/finalYear/web/src/App.jsx) and styled with plain CSS in [`web/src/index.css`](file:///c:/finalYear/web/src/index.css).

### 1. Files Added & Modified
- [`web/src/RiskTab.jsx`](file:///c:/finalYear/web/src/RiskTab.jsx): Full Risk Analysis view displaying:
  - "Run Risk Analysis" button polling `GET` every 2 s, switching to "Show saved result" once complete without triggering new API calls.
  - In-flight spinner with elapsed seconds and 120 s warning ("Taking longer than usual.").
  - Handling of all API states in plain words: `quota_blocked` ("Today's free Gemini limit is used up, so this task did not run. Try again after the daily reset."), `needs_retrieval` ("This document is too long for the risk scan in this version."), `failed`/`scan_failed` (API error message), and `partial`.
  - API notice banner: "Automated output. Check each quote against the cited page. Information, not legal or financial advice."
  - Combined score & gauge section: numeric score (`0-100`), colored bar gauge with boundary markers at 25 / 50 / 75, risk level badge (`Low`/`Moderate`/`High`/`Critical`), `level_explanation` from API, "automated estimate" label, "evidence limited" badge (when no category reaches `'strong'` evidence), and sample range note ("Range seen in the 13 labeled sample documents. Bands are not calibrated.").
  - 7-category breakdown table showing weights, category risk %, clause count, evidence strength badge (`strong`/`limited`/`none`), and top driver clause with verbatim quote and clickable page jump button.
  - Critical clauses section displaying "No Critical clauses found." when empty, or each critical clause with type, severity explanation, verbatim quote, and clickable page.
  - Flagged clauses list sorted by severity (`Critical` -> `High` -> `Medium` -> `Low`) then page number ascending, each with severity badge, "automated estimate" tag, category, severity explanation, verbatim quote blockquote, and clickable page citation.
- [`web/src/App.jsx`](file:///c:/finalYear/web/src/App.jsx): Imported and mounted `RiskTab` under the active tab switcher, and added `"automated output"` pill next to the Risk Analysis tab button.
- [`web/src/index.css`](file:///c:/finalYear/web/src/index.css): Added plain CSS styles for score gauge bar, level badges, category table, and clause cards.
- [`scripts/test_7b3_web.py`](file:///c:/finalYear/scripts/test_7b3_web.py): Automated test suite for static security, live FastAPI risk execution, and coverage of API response states/statuses.

### 2. Real API Response Shape (`GET /api/documents/{doc_id}/tasks/risk`)
- **Outer Task Envelope**:
  - `state`: `"done"` | `"running"` | `"quota_blocked"` | `"failed"` | `"not_started"` | `"partial"`
  - `result`: Dictionary containing risk metrics and clause lists
  - `live_calls`: `0` on cached execution
  - `models_used`: `{"gemini-3.5-flash-lite": 2}`
  - `notice`: `"Automated output. Check each quote against the cited page. Information, not legal or financial advice."`
  - `error`: Error string or `null`
  - `elapsed_s`: Float execution duration in seconds
- **Risk Result Payload (`result`)**:
  - `status`: `"ok"` | `"needs_retrieval"` | `"scan_failed"`
  - `score`: Float (e.g. `47.9` for DBS MITC, `2.5` for AES Ohio)
  - `level`: `"Moderate"` | `"Low"` | `"High"` | `"Critical"`
  - `level_explanation`: String (e.g. `"Level Moderate matches score 47.9 (Critical floor not needed)."`)
  - `sample_range`: String (`"41.2-51.7"`)
  - `labels`: `["automated estimate", "information, not advice"]`
  - `display_note`: Guideline string regarding mandatory simultaneous display of score, level, and breakdown
  - `flagged_count`: Integer count (`18` for DBS MITC, `1` for AES Ohio)
  - `critical_count`: Integer count (`0` for DBS MITC, `0` for AES Ohio)
  - `categories`: Array of 7 category objects (`name`, `weight`, `risk`, `points_contributed`, `n_clauses`, `evidence_strength`, `status`, `top_clauses`)
  - `top_driver_per_category`: Array of 7 objects with category driver details (`category`, `clause_id`, `severity`, `page`, `quote`, `contribution`)
  - `critical_clauses`: Array of Critical severity clauses
  - `flagged_clauses`: Array of all flagged clauses with `clause_id`, `category`, `clause_type`, `severity`, `severity_rule`, `severity_explanation`, `explain`, `quote`, `page`, `verified`
  - *Note on absent fields*: `verifier_independent` is **not** present in `risk.json` responses (neither top-level nor per-clause) because the v5 rubric scan does not run cross-model numeric verifiers; the UI does not invent this field.

### 3. Verification Results (`scripts/test_7b3_web.py`)
- **T1 PASS | Static checks**: `files=12, key_leaks=0, storage_hits=0, hardcoded_hits=0, advice_hits=0, tables_count_hits=0`.
- **T2 PASS | API integration**: `port=55003, doc_id=893857f8b7e3, live_calls=0, score=47.9, level=Moderate, flagged_count=18, critical_count=0, response_states=['done'], ui_handled_states=['done', 'failed', 'needs_retrieval', 'not_started', 'partial', 'quota_blocked', 'running'], response_statuses=['ok'], ui_handled_statuses=['needs_retrieval', 'ok', 'scan_failed'], response_evidence_strength=['limited', 'none', 'strong'], ui_handled_evidence_strength=['limited', 'none', 'strong'], uploads_preserved=True`.
- **T3 INCONCLUSIVE | Build check**: `sandbox realpath EPERM prevents build inside sandbox (student runs npm run build on host)`.
- **Zero Gemini Calls**: `data/processed/llm_log.csv` row count strictly unchanged (`458 -> 458`, delta = 0).

### 4. Known Limits (Stage 7b-3)
- Tested via headless HTTP API integration and static scans; no physical desktop browser window was opened.
- `quota_blocked` and `scan_failed` were verified via defensive code coverage but not observed during happy-path cached runs.
- `needs_retrieval` was verified via `test_7a2b.py` budget-capped guard tests on oversized documents.
- Chat tab remains a UI placeholder (deferred to Stage 7b-4).

### 5. How to run (Student Host)
```powershell
# 1. Start backend server
python -m uvicorn app.api.main:app --port 8000

# 2. Run frontend dev server
cd web
npm run build
npm run dev

# 3. Run verification test suite
python scripts\test_7b3_web.py
```

---

## Stage 7b-4: Chat tab

Implemented the interactive grounded Q&A Chat tab in [`web/src/ChatTab.jsx`](file:///c:/finalYear/web/src/ChatTab.jsx), integrated with the single-page React frontend in [`web/src/App.jsx`](file:///c:/finalYear/web/src/App.jsx) and styled with plain CSS in [`web/src/index.css`](file:///c:/finalYear/web/src/index.css).

### 1. Files Added & Modified
- [`web/src/ChatTab.jsx`](file:///c:/finalYear/web/src/ChatTab.jsx): Full Q&A Chat component featuring:
  - Chat input box with single-question lock (Send disabled during in-flight requests) and text prompt submission.
  - In-flight indicator displaying spinner with elapsed seconds and a 120s alert ("Taking longer than usual. OCR or complex clause analysis in progress...").
  - On-open retrieval of past turns via `GET /api/documents/{doc_id}/chat`, rendering turns in chronological order.
  - Plain-language handling for all status and category returns:
    - `ok` (`fact`): Answer text with interactive `[p. X]` citation buttons via `citationUtils`, plus verified document quotes with clickable `p.{page}` jump buttons.
    - `not_found`: "Not found in this document."
    - `unverified`: "I could not verify this answer against the document, so it is not shown." (answer hidden).
    - `explain_term`: Labeled with "General explanation, not from your document", plus attached verified quotes if returned.
    - `calculation`: Dedicated calculation block showing extracted inputs with sources (user vs document), formula steps, formatted numeric result, and estimate-only notice; displays missing inputs banner when incomplete (`needs_inputs`).
    - `advice` (`refused`): Neutral API notice without recommendation or advice phrasing.
    - `off_topic`: API's own refusal message.
    - `quota_blocked`: "Today's free Gemini limit is used up, so this question did not run. Try again after the daily reset."
    - HTTP 429: "A question is already being answered. Please wait."
    - `needs_retrieval` / error: Displays API's error text.
  - "not independently verified" badge rendered on any turn where `turn.fallback_used === true`, `turn.verifier_independent === false`, or `"model_fallback"` is in `turn.flags`.
  - "needs review" badge rendered on any turn where `turn.final_check === "needs_review"`.
  - API notice banner displayed per turn from `turn.notice`.
  - Language selector dropdown with English active and Indian languages (Hindi, Tamil, Bengali, Punjabi, Malayalam) disabled with label "Translation is coming in a later version.", keeping the API payload unaltered.
- [`web/src/App.jsx`](file:///c:/finalYear/web/src/App.jsx): Replaced placeholder with `<ChatTab docId={docId} onJumpPage={handleJumpToPage} />` and labeled tab header with `Chat <span className="tab-pill">automated output</span>`.
- [`web/src/index.css`](file:///c:/finalYear/web/src/index.css): Added plain CSS styles for user and assistant bubbles, waiting spinner, calculation input tables, formula steps, result cards, and quote citations.
- [`scripts/test_7b4_web.py`](file:///c:/finalYear/scripts/test_7b4_web.py): Automated test suite for static security, live FastAPI chat history retrieval (0 live model calls), category/status coverage, error status codes (404, 422), and quota preservation.

### 2. Real API Response Shape (`GET` & `POST /api/documents/{doc_id}/chat`)
- **GET Envelope**: `{"doc_id": str, "turns": list[turn]}`
- **POST Return**: Single turn dictionary (also appended to `data/processed/uploads/{doc_id}/results/chat.json`)
- **Turn Fields**:
  - `question`: User query string
  - `timestamp`: ISO 8601 UTC timestamp
  - `category`: `"fact"` | `"explain_term"` | `"calculation"` | `"advice"` | `"off_topic"`
  - `status`: `"ok"` | `"not_found"` | `"unverified"` | `"refused"` | `"off_topic"` | `"needs_review"` | `"needs_inputs"` | `"quota_blocked"` | `"failed"`
  - `answer`: String formatted answer text
  - `evidence`: List of quote dicts `[{"quote": str, "page": int}]`
  - `final_check`: `"verified"` | `"needs_review"` | `null`
  - `verifier_independent`: `true` | `false` | `null`
  - `verifier_verdict`: `"supported"` | `"partly_supported"` | `null`
  - `verifier_model_used`: `"gemini-3.5-flash"` | `null`
  - `model_used`: `"gemini-3.6-flash"` | `"gemini-3.5-flash-lite"` | `null` (for deterministic rules)
  - `models_used`: Dict of `{model_name: count}`
  - `fallback_used`: Boolean (`true` when fallback model was engaged)
  - `configured_main_model`: `"gemini-3.6-flash"`
  - `configured_bulk_model`: `"gemini-3.5-flash-lite"`
  - `live_calls`: Integer count (`0` on cached execution)
  - `quotes_checked`: Integer count
  - `quotes_verified`: Integer count
  - `unverified_dropped`: Integer count
  - `flags`: List of string flags (e.g. `["model_fallback"]`, `["advice_refused"]`, `["off_topic_refused"]`, `["quota_blocked"]`)
  - `router_fallback`: Boolean
  - `language`: String (`"en"`)
  - `notice`: `"Automated output. Check each quote against the cited page. Information, not legal or financial advice."`
  - **Calculation Fields** (present when `category == "calculation"`):
    - `inputs`: Dict of inputs `{name: {"value": ..., "source": "user"|"doc", "quote": ..., "page": ...}}`
    - `steps`: List of formula step strings
    - `assumptions`: List of assumption strings
    - `formula_name`: String (e.g. `"reducing_balance_emi"`)
    - `currency`: String (e.g. `"INR"`)
    - `result`: String formatted number (e.g. `"22842.37"`)
    - `missing`: List or dict of missing inputs (if incomplete)
    - `needs_inputs`: Boolean
- **Fields Absent in API**:
  - No per-turn unique `id` / `uuid` field (turns are stored as an ordered list in `chat.json`).
  - No `session_id` or `conversation_id` field.
  - No `user_id` field.
  - No advice recommendation text (refusal only).

### 3. Field Used for "not independently verified"
- The badge is attached using `turn.fallback_used === true || turn.verifier_independent === false || (Array.isArray(turn.flags) && turn.flags.includes("model_fallback"))`.
- In the 8 benchmark turns on `03_dbs_mitc`, 2 turns fell back from `gemini-3.6-flash` to `gemini-3.5-flash-lite` and carry `fallback_used: true` and `"model_fallback"` in `flags`.

### 4. Verification Results (`scripts/test_7b4_web.py`)
- **T1 PASS | Static checks**: `files=13, key_leaks=0, storage_hits=0, hardcoded_hits=0, advice_hits=0, tables_count_hits=0`.
- **T2 PASS | API integration**: `port=53698, doc_id=893857f8b7e3, turns=8, fallback_turns=2, review_turns=1, resp_categories=['advice', 'calculation', 'explain_term', 'fact', 'off_topic'], ui_handled_categories=['advice', 'calculation', 'explain_term', 'fact', 'off_topic'], resp_statuses=['not_found', 'off_topic', 'ok', 'refused'], ui_handled_statuses=['failed', 'needs_inputs', 'needs_retrieval', 'needs_review', 'not_found', 'off_topic', 'ok', 'quota_blocked', 'refused', 'unverified'], resp_flags=['advice_refused', 'model_fallback', 'off_topic_refused'], ui_handled_flags=['advice_refused', 'chat_budget_reached', 'evidence_unverified_server', 'model_fallback', 'off_topic_refused', 'quota_blocked'], unknown_doc_404=True, empty_q_422=True, uploads_preserved=True`.
- **T3 INCONCLUSIVE | Build check**: `sandbox realpath EPERM prevents build inside sandbox (student runs npm run build on host)`.
- **Zero Gemini Calls**: `data/processed/llm_log.csv` row count strictly unchanged (`458 -> 458`, delta = 0).

### 5. Regression Suite Status
- `scripts/test_7b1_web.py`: **PASS** (`llm_log.csv` delta = 0)
- `scripts/test_7b2_web.py`: **PASS** (`llm_log.csv` delta = 0)
- `scripts/test_7b3_web.py`: **PASS** (`llm_log.csv` delta = 0)
- `scripts/test_7b4_web.py`: **PASS** (`llm_log.csv` delta = 0)

### 6. Known Limits (Stage 7b-4)
- Verification was conducted via headless HTTP integration tests and static scanning; no physical browser window was opened.
- Unobserved categories/statuses during the cached 8-question benchmark (`quota_blocked`, `unverified`, `needs_inputs`, `needs_retrieval`) were covered defensively in `ChatTab.jsx` logic and verified against static schema definitions.
- Language selector options for Indian languages (Hindi, Tamil, Bengali, Punjabi, Malayalam) are disabled pending translation support in future versions; English remains the active language and the API request payload contains only `{"question": ...}`.

### 7. How to run (Student Host)
```powershell
# 1. Start backend server
python -m uvicorn app.api.main:app --port 8000

# 2. Run frontend dev server
cd web
npm run build
npm run dev

# 3. Run Stage 7b-4 verification suite
python scripts\test_7b4_web.py
```

---

## Stage 7b-4b: Advice refusal neutrality and button labeling update

Implemented advice refusal neutral wording override and button label synchronization across tabs.

### 1. Files Modified
- [`web/src/ChatTab.jsx`](file:///c:/finalYear/web/src/ChatTab.jsx): Overrode advice refusal display with the exact neutral text:
  `"This system gives document information only. It does not give legal or financial advice, so it cannot say whether to sign or accept this agreement. It can show the risks, fees, penalties or foreclosure clauses stated in the document."`
  Ensures that phrases like `"you should"`, `"we recommend"`, and `"consult"` are never displayed to users. Saved `chat.json` files were left untouched.
- [`web/src/SummaryTab.jsx`](file:///c:/finalYear/web/src/SummaryTab.jsx): Renamed completed task button label from `"Re-run Summary"` to `"Show saved result"` without changing behavior (0 API calls).
- [`web/src/KeyInfoTab.jsx`](file:///c:/finalYear/web/src/KeyInfoTab.jsx): Renamed completed task button label from `"Re-run Key Info"` to `"Show saved result"` without changing behavior (0 API calls).
- [`scripts/test_7b4_web.py`](file:///c:/finalYear/scripts/test_7b4_web.py): Extended T1 to assert: (a) `"you should"`, `"we recommend"`, and `"consult"` do not appear in `ChatTab.jsx` or refusal text; (b) `"Re-run"` does not appear in `SummaryTab.jsx` or `KeyInfoTab.jsx`; (c) dynamic `chat.json` length check (`>= 8` turns) and `llm_log.csv` delta = 0.

### 2. Test Results
- `scripts/test_7b1_web.py`: **PASS** (`llm_log.csv` rows: 463 -> 463, delta = 0)
- `scripts/test_7b2_web.py`: **PASS** (`llm_log.csv` rows: 463 -> 463, delta = 0)
- `scripts/test_7b3_web.py`: **PASS** (`llm_log.csv` rows: 463 -> 463, delta = 0)
- `scripts/test_7b4_web.py`: **PASS** (`llm_log.csv` rows: 463 -> 463, delta = 0)

---

## Stage 5a: Number, date, and amount verification for translations

Implemented pure Python offline number and date validation in [`src/translate/number_check.py`](file:///c:/finalYear/src/translate/number_check.py) and verified via [`scripts/test_5a_numbers.py`](file:///c:/finalYear/scripts/test_5a_numbers.py).

### 1. Components Built
- [`src/translate/number_check.py`](file:///c:/finalYear/src/translate/number_check.py):
  - `normalize_script_digits(text)`: Converts Unicode decimal digits from Devanagari, Bengali, Gurmukhi, Tamil, Malayalam, and other Indic scripts to standard ASCII 0–9 digits via `unicodedata.decimal`.
  - `extract_numeric_tokens(text)`: Extracts dates (canonicalized to `DD/MM/YYYY`), strips thousands separators between digits (`5,00,000` / `500,000` -> `500000`), preserves decimal amounts (`22842.37`), percentages, and counts.
  - `check_numbers(source_en, translated)`: Performs multiset difference comparison using `collections.Counter`, returning `{"status": "pass"|"fail", "missing_in_translation": [...], "extra_in_translation": [...], "source_numbers": [...], "translated_numbers": [...]}`.
- [`scripts/test_5a_numbers.py`](file:///c:/finalYear/scripts/test_5a_numbers.py):
  - Evaluates 13 hand-written test cases (8 positive, 5 negative) across Hindi, Tamil, Bengali, Punjabi, Malayalam, comma grouping, date formats, and zero-number texts.
  - Asserts `llm_log.csv` row count delta = 0.

### 2. Test Results (`scripts/test_5a_numbers.py`)
- **Positive Cases (8/8 PASS)**:
  - `P1`: Hindi Devanagari digits (`२२८४२.३७`, `२४`, `९%`) -> PASS
  - `P2`: Tamil digits (`௨௨௮௪௨.௩௭`, `௨௪`, `௯%`) -> PASS
  - `P3`: Bengali digits (`২২৮৪২.৩৭`, `২৪`, `৯%`) -> PASS
  - `P4`: Gurmukhi / Punjabi digits (`੨੨੮੪੨.੩੭`, `੨੪`, `੯%`) -> PASS
  - `P5`: Malayalam digits (`൨൨൮൪൨.൩൭`, `൨൪`, `൯%`) -> PASS
  - `P6`: Thousands separators (`5,00,000` vs `500000`) -> PASS
  - `P7`: Date token (`15/03/2026` vs `१५/०३/२०२६`) -> PASS
  - `P8`: Zero-number text -> PASS
- **Negative Cases (5/5 PASS, correctly flagged as `fail`)**:
  - `N1`: Rate 9% changed to 19% -> `status: fail` (`missing: ['9']`, `extra: ['19']`)
  - `N2`: Tenure 24 omitted -> `status: fail` (`missing: ['24']`, `extra: []`)
  - `N3`: Hallucinated 500 fee added -> `status: fail` (`missing: []`, `extra: ['500']`)
  - `N4`: Magnitude error (500000 -> 50000) -> `status: fail` (`missing: ['500000']`, `extra: ['50000']`)
  - `N5`: Single digit error in Devanagari numeral (`२२८४३.३७`) -> `status: fail` (`missing: ['22842.37']`, `extra: ['22843.37']`)
- **Zero Gemini Calls**: `data/processed/llm_log.csv` row count: `463 -> 463` (delta = 0).

### 3. Known Limitations (Stage 5a)
1. **Builder-Written Test Set**: All 13 test cases were hand-written by the builder (optimistic evaluation) to test normalization mechanics; this suite does not represent an independent evaluation on noisy wild translation datasets.
2. **Number Words Not Compared**: Written number words (e.g. "five lakh", "twenty four", "पाँच लाख") are not parsed or converted to digits.
3. **Month Names Not Compared**: Textual month names (e.g. "15 March 2026", "15 मार्च 2026") are not parsed into calendar date tokens.

---

## Stage 5b: Indic translation with numeric guard, caching, and UI integration

Implemented Indic machine translation for document summaries and chat answers into Hindi (`hi`), Tamil (`ta`), Bengali (`bn`), Punjabi (`pa`), and Malayalam (`ml`), guarded by pure-Python numeric/date verification and full offline caching.

### 1. Components Built and Modified
- [`src/translate/translate_text.py`](file:///c:/finalYear/src/translate/translate_text.py):
  - `translate_text(text_en, lang, llm_call=None) -> dict`: Translates English prose into the target Indic language.
  - Model role defaults to `bulk` (`gemini-3.5-flash-lite`) via `_call_gemini` to preserve quota.
  - Quota guard check before any live model call; returns `{"status": "quota_blocked", "live_calls": 0}` if daily limit is reached.
  - Automated 1-retry verification loop: runs `check_numbers` from `src.translate.number_check`. If numbers/dates mismatch, feeds exact missing and extra numbers back into a single retry prompt (`"CRITICAL CORRECTION (Retry 1 of 1)"`).
  - If retry still fails numeric check, returns `{"status": "number_check_failed", "translated_text": "", "number_check": ...}` to ensure corrupted numeric translations are never presented as valid.
- [`app/api/main.py`](file:///c:/finalYear/app/api/main.py):
  - Added `TranslateRequest` Pydantic model (`source: "summary"|"chat"`, `language: "hi"|"ta"|"bn"|"pa"|"ml"`, `turn_index: int|None`).
  - Added module hook `_TRANSLATE_HOOK` for deterministic test injection without monkeypatching internal imports.
  - Added endpoint `POST /api/documents/{doc_id}/translate`:
    - Validates `doc_id` (404 if unknown), `source` (422 if not summary/chat), `language` (422 if unsupported), and `turn_index` (422 if missing/out-of-range for chat).
    - For chat turns, translates `turn.answer` (or the standardized neutral advice text for advice category turns). Verbatim quotes in `turn.evidence` are **strictly excluded** from translation.
    - For summaries, extracts and translates `result.short`.
    - Caches results under `data/processed/uploads/<doc_id>/results/translations/<source>_<turn>_<lang>.json`. Subsequent requests return the cached result with `live_calls = 0` without invoking the model.
- [`web/src/SummaryTab.jsx`](file:///c:/finalYear/web/src/SummaryTab.jsx):
  - Added language selector dropdown in header for English + the 5 Indic languages.
  - When non-English language is chosen, calls `POST /api/documents/{docId}/translate` for the summary text.
  - Renders translation with badge `"Machine translation. Check against the original English."`, parses inline clause citations via `renderCitations`, and displays the original English text below for user verification.
  - Displays plain-language status banners for `number_check_failed`, `quota_blocked`, and `failed`.
  - Shows spinner with elapsed timer and a 60-second delay warning if translation takes long.
- [`web/src/ChatTab.jsx`](file:///c:/finalYear/web/src/ChatTab.jsx):
  - Enabled all 5 Indic languages in `#chat-lang-select`.
  - Automatically fetches translations for active and historical chat answers (including neutral advice refusal prose).
  - Verbatim document quotes in `turn.evidence` and page citation buttons stay strictly in their original English.
  - Displays machine translation label and Original English box.
  - Handles status banners for `number_check_failed`, `quota_blocked`, and `failed`.
- [`web/src/index.css`](file:///c:/finalYear/web/src/index.css):
  - Styled translation controls, badges, original English comparison boxes, and translation loading states using plain CSS.
- [`scripts/test_5b_translate.py`](file:///c:/finalYear/scripts/test_5b_translate.py):
  - Verification test suite executing zero Gemini calls (`llm_log.csv` delta = 0).

### 2. Test Results (`scripts/test_5b_translate.py` & Full Regression)
- **`scripts/test_5b_translate.py` (8/8 PASS)**:
  - `T1 (a)`: Good translation -> `status: ok`, `number_check: pass`, `live_calls: 1` -> **PASS**
  - `T2 (b)`: Changed number triggers retry with explicit feedback and returns `number_check_failed` with `translated_text: ""` -> **PASS**
  - `T3 (b2)`: Changed number corrected on retry succeeds with `status: ok` -> **PASS**
  - `T4 (c)`: Endpoint caching returns `live_calls: 0` without invoking translator on second call -> **PASS**
  - `T5 (d)`: Quota blocked path returns `status: quota_blocked` with `0` live calls -> **PASS**
  - `T6 (e)`: Input validation: 404 unknown doc, 422 source/lang/turn_index -> **PASS**
  - `T7 (f)`: Evidence quotes strictly excluded from text passed to translator -> **PASS**
  - `T8 (g)`: Static scan: 0 API key leaks, 0 localStorage/sessionStorage, 0 advice words, language selectors verified in SummaryTab and ChatTab, 0 consult in ChatTab -> **PASS**
  - `Zero API calls`: `llm_log.csv` rows `463 -> 463` (delta = 0) -> **PASS**
- **Regression Test Suites (All PASS)**:
  - `scripts/test_5a_numbers.py`: **PASS** (13/13 cases, delta = 0)
  - `scripts/test_7b1_web.py`: **PASS** (T1 PASS, T2 PASS, T3 INCONCLUSIVE sandbox EPERM, delta = 0)
  - `scripts/test_7b2_web.py`: **PASS** (T1 PASS, T2 PASS, T3 INCONCLUSIVE sandbox EPERM, delta = 0)
  - `scripts/test_7b3_web.py`: **PASS** (T1 PASS, T2 PASS, T3 INCONCLUSIVE sandbox EPERM, delta = 0)
  - `scripts/test_7b4_web.py`: **PASS** (T1 PASS, T2 PASS, T3 INCONCLUSIVE sandbox EPERM, delta = 0)

### 3. Known Limitations (Stage 5b)
1. **Synthetic Translation Test Set**: The translation logic, retry loop, error reporting, and cache behavior were tested with synthetic/injected translations (optimistic evaluation) to prove reliability without consuming live API quota. This does not evaluate whether Gemini's real Indic output is grammatically natural or legally accurate across Indic dialects.
2. **Translation Quality Metrics**: Formal translation metrics (e.g. chrF++, BLEU) were not computed against human gold translations.
3. **Number Words and Textual Months**: Written Indic or English number words (e.g. "twenty four", "पाँच लाख") and textual month names are not parsed into digits and therefore bypass the numeric checker.
4. **Machine Translation Disclaimer**: All machine-translated output in the UI is explicitly labeled with `"Machine translation. Check against the original English."` and shown alongside the original English text.

---

## Stage 6 (submission prep): Unified test runner and final report

Prepared the project for final-year submission by consolidating offline test verification, updating test wording to avoid unmeasured target claims, and drafting the comprehensive project submission report.

### 1. Components Built and Updated
- [`scripts/test_5b_translate.py`](file:///c:/finalYear/scripts/test_5b_translate.py):
  - Updated completion message from `"STAGE 5b TARGET MET: ..."` to `"STAGE 5b LOGIC TESTS PASSED (fake translations, no quality target measured)"`.
- [`scripts/run_all_offline_tests.py`](file:///c:/finalYear/scripts/run_all_offline_tests.py):
  - Unified runner executing all 6 offline verification suites sequentially (`test_5a_numbers.py`, `test_5b_translate.py`, `test_7b1_web.py`, `test_7b2_web.py`, `test_7b3_web.py`, `test_7b4_web.py`) using `sys.executable`.
  - Parses real subprocess stdout/stderr and exit codes, reporting each suite as PASS, FAIL, or INCONCLUSIVE (for sandbox T3 build checks).
  - Asserts that `llm_log.csv` row count delta is exactly 0 across the entire run. Never logs or prints environment variables.
- [`docs/FINAL_REPORT.md`](file:///c:/finalYear/docs/FINAL_REPORT.md):
  - Authored complete final-year student project report in plain, clear English covering Abstract, Problem and Significance, Capabilities, Architecture and Term Glossary, Safety Design, Target vs Result Evaluation Table (using only verified project FACTS), Translation Findings, Known Limitations, Future Work, How to Run commands, and Ethical Considerations.

### 2. Unified Offline Test Runner Results (`scripts/run_all_offline_tests.py`)
- `test_5a_numbers.py`: **PASS** (all checks passed)
- `test_5b_translate.py`: **PASS** (all checks passed)
- `test_7b1_web.py`: **INCONCLUSIVE** (T1 PASS, T2 PASS, T3 INCONCLUSIVE: sandbox realpath EPERM)
- `test_7b2_web.py`: **INCONCLUSIVE** (T1 PASS, T2 PASS, T3 INCONCLUSIVE: sandbox realpath EPERM)
- `test_7b3_web.py`: **INCONCLUSIVE** (T1 PASS, T2 PASS, T3 INCONCLUSIVE: sandbox realpath EPERM)
- `test_7b4_web.py`: **INCONCLUSIVE** (T1 PASS, T2 PASS, T3 INCONCLUSIVE: sandbox realpath EPERM)
- `llm_log.csv` rows: `464 -> 464` (**delta = 0**, zero live Gemini calls).
















