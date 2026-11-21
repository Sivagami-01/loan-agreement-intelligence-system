# Project Guide: AI Loan Agreement Analyzer

This report explains the project as it is implemented in the repository: its purpose, architecture, tools, upload/OCR flow, analysis features, risk calculation, chatbot, storage, limitations, and how to run it. It is intended to be readable on its own and can also be given to another AI assistant as project context.

> **Important:** This is a document-reading aid, not legal or financial advice. Its generated outputs can be incomplete or wrong. Always inspect the original agreement and get qualified professional advice for decisions.

## 1. Project at a glance

The project is a web application for exploring loan agreements and similar credit documents. A user uploads a PDF, HTML, or TXT file. The backend extracts page text (using OCR when a PDF page has no usable text), then offers optional analysis tasks:

1. A short and detailed summary.
2. Extraction of 16 key agreement fields.
3. A question-answering chat grounded in the uploaded document.
4. An explainable, heuristic risk scan and 0–100 score.
5. On-demand translation of the short summary and chat responses to five Indic languages.
6. Calculations through the chat flow, such as estimated EMI, total interest/payment, and selected charges.
7. A page-text viewer so the user can inspect the extracted source and navigate from citations.

Analysis tasks are requested separately rather than all being run automatically at upload. Uploading and ingestion prepares the document; clicking a task or asking the chatbot triggers the relevant analysis.

## 2. Technology stack and tools

| Area | Technologies in this repository | Role |
|---|---|---|
| Browser UI | React 18, JavaScript/JSX, CSS | Upload form, progress, tabs, document page viewer, chat and results |
| Frontend dev/build | Vite 5 | Local development server and frontend production build |
| API server | Python, FastAPI, Uvicorn, Pydantic | REST endpoints, request validation, background work and API responses |
| PDF processing | PyMuPDF (`fitz`) | Reads PDFs page by page, renders scanned pages, and attempts table extraction |
| OCR | Tesseract 5, `pytesseract`, Pillow | Local OCR for scanned or unusable PDF text pages |
| Language model | Google Gemini REST API, called through Python `requests` | Structured extraction, summaries, QA, risk classification, and translation |
| Retrieval | Project's own pure-Python BM25 implementation | Finds relevant chunks in long documents; no vector database or embedding model |
| Configuration and persistence | YAML, JSON, CSV, filesystem | Settings, document data, task results, caches, histories, and API-call logs |
| Testing / research scripts | Python scripts under `scripts/` | Ingestion, OCR comparison, retrieval, feature tests, scoring, evaluation, and demos |

Important configuration files:

- `config/models.yaml`: Gemini model aliases (main, bulk, verifier).
- `config/app.yaml`: allowed uploads, task budgets, daily API soft limit, output folder name, and notices.
- `config/ocr_choice.yaml`: OCR engine selection notes/settings. It documents the intended hybrid policy but does not, by itself, mean the live upload path calls Gemini Vision.
- `config/qa.yaml`, `config/retrieval.yaml`, `config/extract.yaml`, `config/summarize.yaml`, `config/risk.yaml`, `config/severity_rules.yaml`, `config/score.yaml`, and `config/calc.yaml`: individual feature settings.

The API key is read from the `GEMINI_API_KEY` environment variable. It should not be placed in source code or committed files.

## 3. Architecture

The project has three main layers:

1. **React frontend (`web/src/`)** sends HTTP requests and displays results.
2. **FastAPI backend (`app/api/`)** validates uploads, manages document/task state, calls analysis modules, and persists results.
3. **Analysis modules (`src/`)** implement ingestion support, retrieval, extraction, summaries, QA, calculations, risk classification/scoring, and translation. `scripts/` contains the CLI ingestion/evaluation and demonstration tools.

### Request flow

```text
Browser (React)
  -> FastAPI endpoint
  -> filesystem document/results
  -> analysis module in src/ and, where needed, Gemini API
  -> deterministic checks / scoring
  -> JSON response
  -> React renders result and page citations
```

### Main API endpoints

The routes are defined in `app/api/main.py`:

- `GET /api/health`: simple API health response.
- `GET /api/meta`: allowed file types, upload size and user notices.
- `POST /api/documents`: validates and stores an upload, starts ingestion.
- `GET /api/documents/{doc_id}/status`: returns ingestion progress/status.
- `GET /api/documents/{doc_id}/pages/{n}`: returns extracted text and quality/source for a page.
- `POST /api/documents/{doc_id}/tasks/{kind}` and `GET .../tasks/{kind}`: start/read `summary`, `keyinfo`, or `risk` tasks.
- `POST /api/documents/{doc_id}/chat` and `GET .../chat`: submit a question/read persisted chat history.
- `POST /api/documents/{doc_id}/translate`: translate a summary or selected chat turn.

## 4. Upload, ingestion, and OCR

### Upload checks and document identity

The browser accepts PDF, HTML/HTM, and TXT files; the API applies a 25 MB size limit. The API checks the extension, non-empty content, and basic content signatures (for example, `%PDF` for a PDF). It sanitizes the display filename and computes SHA-256 over the uploaded bytes. The first 12 hex characters become the `doc_id`, allowing identical file contents to map to the same ID.

The file is stored beneath `data/processed/uploads/<doc_id>/`. Metadata is written as JSON. Ingestion runs in a background thread, and the UI polls the status endpoint to display page progress.

### PDF text extraction and OCR

For each PDF page, the upload ingestion path (`app/api/ingest_service.py` calling `scripts/ingest.py`) works roughly as follows:

1. PyMuPDF first reads the page's embedded text layer.
2. The code detects a likely script/language from text characters; if that does not work, it can use language clues in the filename. Supported Indic-script heuristics include Devanagari/Hindi, Bengali, Gurmukhi/Punjabi, and Malayalam; otherwise it defaults to English.
3. A page-quality check looks for empty text, PDF font artifacts such as `(cid:...)`, private-use or replacement characters, long symbol runs, low text density, and (for Indic pages) low expected-script share. It labels a page `GOOD`, `SUSPICIOUS`, or `BAD`.
4. If the embedded text is `BAD` or empty, it renders the page at 200 DPI and invokes local Tesseract through `pytesseract`. Indic pages use the detected Indic language pack plus English (for example, `hin+eng`).
5. It assesses the OCR text and stores the final page text, quality label, source (`text` or `ocr`), OCR confidence/language, and any table data.
6. Page text is written with markers such as `[[PAGE 1]]`, preserving page boundaries for citations and downstream processing.

PyMuPDF's table-finding support is also used to extract some PDF tables into structured rows. It is a heuristic; borderless tables and complex scanned layouts can be missed.

**Important current-code distinction:** `config/ocr_choice.yaml` and `docs/OCR_COMPARISON.md` describe a Tesseract/Gemini Vision comparison and a proposed/recorded hybrid selection policy. The live upload ingestion function shown in `scripts/ingest.py` uses cached OCR if available, otherwise Tesseract for pages it decides need OCR; it does not invoke Gemini Vision as the fallback there. Gemini Vision is used by OCR comparison tooling, not automatically by that upload-page OCR function. Do not describe production upload OCR as automatically switching to Gemini unless the code is changed.

### HTML and TXT

- HTML is converted into page-like text by the existing ingestion helper, then normalized into the same page-oriented format.
- TXT files with `[[PAGE n]]` markers keep those page boundaries. Unmarked TXT is split into approximate chunks using paragraph boundaries and a target chunk size; these are synthetic text pages, not original PDF pages.

### OCR comparison findings

`docs/OCR_COMPARISON.md` records an experiment on 84 items (64 Indian loan-document pages and 20 receipt images), comparing Tesseract and Gemini Vision using character error rate (CER) and latency. It reports mixed results: the recorded selection favored Tesseract for Hindi/Bengali/Punjabi/Malayalam and Gemini for English receipts, while noting empty model responses, ground-truth limitations, and model availability issues. These are benchmark results, not a guarantee of OCR quality for every uploaded file.

## 5. Storage and caching

The app does **not** use a conventional relational or NoSQL database. It stores files on disk and uses in-memory Python dictionaries/locks for active process state.

Typical uploaded-document layout:

```text
data/processed/uploads/<doc_id>/
  source.pdf | source.html | source.txt
  meta.json
  status.json
  ingested.json
  ingested.txt
  results/
    summary.json
    keyinfo.json
    risk.json
    chat.json
    translations/...
```

Other persisted data includes:

- BM25 retrieval cache under `data/processed/retrieval_cache/`.
- Gemini response cache under `data/processed/cache/gemini/`.
- Sanitized API call metrics in `data/processed/llm_log.csv` (timestamp, model, latency, input/output sizes; not raw prompts or API keys).
- Evaluation datasets/results and OCR outputs under `data/processed/`.

JSON writes in the app use a temporary file followed by replacement to reduce the chance of leaving a partially written result. The active job/task dictionaries are in memory; they are not a durable distributed queue and do not coordinate across multiple server processes.

## 6. Summary feature

The summary task is implemented in `src/summarize/summarize.py`, called through the task service.

1. The summarizer obtains verified key-field facts first if they were not already available.
2. It builds a Gemini prompt for a short summary (configured maximum: 120 words) and structured detailed sections such as Parties, Money, Interest and repayment, Fees and penalties, Prepayment, Security and guarantees, Default and termination, and Governing law.
3. Each generated sentence is checked before it is kept:
   - It must include a page citation in the expected `[p.N]` format and cite a page that exists.
   - Numbers/dates/amounts in the sentence are checked against the cited source page(s).
   - Opinion/advice-like sentences are dropped.
   - Short-summary word count is capped.
4. Missing or externally referenced key fields are represented as “not found” or “defined elsewhere” rather than being silently invented.
5. The accepted summary and validation information are saved to JSON and rendered in the Summary tab.

This is a deterministic filter, not a full legal entailment proof: matching the cited page and validating its numeric tokens does not prove that every non-numeric sentence is a perfect interpretation of the source.

## 7. Key-information extraction

The key-info task requests 16 configured fields from `config/extract.yaml`:

1. Document title.
2. Agreement date.
3. Borrowers.
4. Lenders.
5. Agents.
6. Loan or commitment amount.
7. Interest rate.
8. Repayment terms.
9. Maturity/termination date or tenure.
10. Fees.
11. Late-payment/default interest.
12. Prepayment terms.
13. Collateral/security.
14. Guarantees.
15. Events of default.
16. Governing law.

For documents within the configured whole-document limit, the extractor asks Gemini for structured output over the document. For longer documents it retrieves relevant chunks separately for fields using BM25. It parses the expected JSON, allows a configured retry for invalid JSON, and then checks each field:

- Evidence quote must match a source page under the project's normalized exact-substring rules.
- A quote found on a different page can have its page corrected and flagged.
- Quote repair can search for a near-identical contiguous source span within configured length/similarity limits, primarily to handle OCR whitespace/hyphenation artifacts. It does not justify inventing a quote.
- Selected numeric fields can receive additional numeric consistency checking.
- Fields can be `verified`, `not_found`, `unverified`, `needs_review`, or `deferred_to_other_document` (among other flags/status details).

The UI shows the field, status, value, evidence quote, and page. A quote can be used to jump to the page viewer. Extraction is fallible; the project report records that field-level evaluation did not meet its target.

## 8. Chatbot and question answering

### Step 1: Intent routing

`src/qa/ask.py` calls `src/qa/router.py`. The router detects supported Indic scripts and first tries deterministic phrase rules. It assigns one of:

- `fact`: asks what the uploaded agreement says.
- `explain_term`: asks for a general explanation of a finance/legal term.
- `calculation`: asks for a numeric calculation.
- `advice`: asks for a recommendation, such as whether to sign or accept.
- `off_topic`: unrelated questions.

If deterministic rules are not confident, the router asks Gemini for a small JSON classification. A router failure safely falls back to `fact`, after which the answerer still applies its document-grounding checks.

### Step 2: Factual answers and long-document retrieval

For `fact` questions, `src/qa/answer.py`:

1. Loads the extracted page text.
2. Uses the whole document when it is below the configured limit (400,000 characters in `config/qa.yaml`) and retrieval is not forced.
3. Otherwise chunks the text while respecting page boundaries and retrieves up to the configured number of relevant chunks with pure-Python BM25. Current retrieval configuration uses 2,000-character chunks, 200-character overlap, top 8 chunks, and a 60,000-character context ceiling.
4. Sends Gemini a prompt requiring a JSON response with `found`, `answer`, and `evidence` (`quote`, `page`). The prompt instructs it to use only the provided document and return “Not found in this document” when evidence is absent.
5. Parses the JSON, with one retry for malformed output.
6. Checks evidence against the full document page texts—not merely the retrieved excerpt. Quote matching normalizes Unicode NFC, whitespace, quote/dash variants, and case, then requires an exact normalized substring. There is no fuzzy quote matching in this QA verifier. If the page is wrong but the quote occurs elsewhere, the page can be corrected; unsupported quotes are dropped.
7. If a positive answer has no surviving verified evidence, it is returned as `unverified` with the answer suppressed. The system can also run a separate answer-verifier step that checks whether evidence supports the answer; whether that verifier is truly independent depends on the configured/available models.

BM25 is keyword/statistical retrieval, not semantic embeddings. If a relevant passage is not among the retrieved chunks, the model may abstain even if the answer appears elsewhere in a very long document.

### Step 3: Other question types

- **Term explanation:** Gemini produces a short general explanation explicitly labeled as not from the document. If a matching term is found in the document, the system may append a separate quoted document-based answer.
- **Advice request:** Returns a neutral refusal and offers to surface clauses, fees, or risks. It does not recommend signing or rejecting a loan.
- **Off-topic:** Returns a brief scope refusal.
- **Chat history:** The backend persists the most recent 50 turns for each uploaded document in `results/chat.json`.

The React chat can display citations and navigate to cited pages. It also offers translation for eligible chat turns.

## 9. Calculations

Calculations are part of the chat feature; there is no separate calculator tab. The router sends calculation questions to `src/calc/extract_inputs.py`.

Input handling:

1. Deterministic patterns first parse figures, rates, units (including lakh/crore), terms, days, currency, and operation clues from the user's question.
2. Missing required inputs may be filled from document-derived, quote-verified key information.
3. If necessary, Gemini may map explicit numbers in the question to named inputs, but it is instructed not to calculate or guess. Candidate values are accepted only when the quoted input text occurs in the question and its number/unit is consistent.
4. If required values remain missing, the chatbot asks the user rather than inventing them.
5. Python `Decimal` arithmetic performs the actual calculations, with configured rounding (2 decimal places by default).

Implemented formula functions include:

- EMI using the standard reducing-balance formula (with a separate zero-interest case).
- Monthly amortization schedule, outstanding balance after a number of payments, total interest, and total payment.
- Prepayment charge as the greater of a percentage charge and an optional minimum charge.
- Penal charge as simple annualized penal interest for the specified days plus a flat fee.
- Interest-only monthly payment.
- Flat-rate simple total interest.

Results include formula names, steps, and assumptions. They are estimates: actual lender schedules may differ because of fees, taxes, rounding conventions, rate changes, day-count rules, or payment dates. APR is mentioned in some older project descriptions but is not implemented as a calculator in the current `src/calc/formulas.py`.

## 10. Risk analysis: clause scan and score

Risk analysis has two separate parts: **finding/classifying candidate clauses** and **computing the numeric score**.

### 10.1 Candidate clause preparation

`app/api/risk_service.py` loads the uploaded document, infers a rough document type (SEC-style agreement versus Indian MITC), then calls `src/risk/split_clauses.py`.

- SEC agreements are split using page markers such as `<PAGE>` or `* * *` page breaks, with logic to stitch some clauses across page breaks. Typical clause bounds are 150–1,500 characters.
- Indian MITC documents are split more finely using page boundaries, headings, paragraphs, list markers, and extracted table rows. Typical bounds are 85–600 characters.
- Every candidate retains a clause ID and page/location.

The deterministic prefilter (`src/risk/prefilter.py`) searches for loan-risk keywords—interest/rates, repayment, fees, collateral, defaults, termination, covenants, remedies, and related concepts. Clauses with no configured keyword hits are not sent to the model. This saves calls, but it can miss a relevant clause that uses unexpected language.

### 10.2 Model classification and deterministic severity rules

Candidate clauses are batched (current scan batch size: 20). Gemini is prompted to assign a category and structured clause type/features. The active v5 pipeline derives severity through `src/risk/severity_rules.py`, a deterministic first-match rule table in `config/severity_rules.yaml`; it ignores any free-form severity the model might return. This makes severity assignment repeatable for the same extracted clause type/features, but the upstream model's category/type/features can still be wrong.

Current categories are **seven**, not eight:

1. Default conditions.
2. Penalties and charges.
3. Financial terms.
4. Repayment.
5. Collateral.
6. Termination.
7. Covenants.

The classifier also has a `none` option for non-risk material. The configured severity scale is Low, Medium, High, Critical, with points 1, 2, 3, 4 respectively. Rules consider clause type and boolean features such as automatic acceleration, absence of notice, cure period, self-help seizure, action beyond pledged collateral, and broad/uncapped indemnity. The fired rule and explanation are retained for transparency.

### 10.3 Quote verification before scoring

Before a model-classified clause can be displayed or scored, the backend verifies the original clause text against the extracted text on its page. Unverified clauses are dropped. Thus, quote verification checks that the text exists; it does **not** certify that the model selected the correct risk category, feature set, or severity.

### 10.4 Current padded-top-three score calculation

The live configuration in `config/score.yaml` uses `method: padded_top3`. The exact formula is implemented in `src/risk/score.py`.

**Severity points**

| Severity | Points |
|---|---:|
| Low | 1 |
| Medium | 2 |
| High | 3 |
| Critical | 4 |

For each category:

1. Sort recognized, verified clauses by severity points, highest first. Ties are resolved deterministically using page, clause ID, and quote.
2. Keep at most the top three clauses.
3. If the category has 1 or 2 clauses, fill the unused top-three slots with padding worth 1 point each (equivalent to Low).
4. If the category has no clauses, its category risk is set to zero and marked “No clause found”; it is **not** padded.
5. For categories with at least one clause:

   `category_risk = (sum of selected clause points + padding points) / 12`

   The denominator is `3 slots × 4 maximum points`.

The category weights in `config/score.yaml` sum to 1:

| Category | Weight |
|---|---:|
| Default conditions | 0.25 |
| Penalties and charges | 0.20 |
| Financial terms | 0.15 |
| Repayment | 0.15 |
| Collateral | 0.10 |
| Termination | 0.10 |
| Covenants | 0.05 |

The raw weighted score is:

`raw_score = 100 × Σ(category_weight × category_risk)`

The displayed score is rounded to one decimal place. Each real clause and each padding slot is assigned its contribution, so the category breakdown and top drivers explain the total.

**Example:** suppose “Default conditions” has one Critical clause (4 points). The two missing slots are padded as Low (1 point each), so category risk is `(4 + 1 + 1) / 12 = 0.5`. Its weighted contribution is `100 × 0.25 × 0.5 = 12.5` points.

### 10.5 Risk levels and Critical floor

The configured score bands are:

- Low: score below 25.
- Moderate: 25 to below 50.
- High: 50 to below 75.
- Critical: 75 or above.

There is an additional configured **Critical-clause floor**: if any verified clause is classified Critical, the displayed level is raised to at least High, even when the numeric score is below 50. The output includes whether the floor was applied and an explanation. It does not automatically raise the level to Critical.

The UI/report should show the numeric score, category breakdown, evidence strength, Critical clauses, and any floor explanation—not just the level label. Evidence strength is based on the number of classified clauses in a category: none (0), limited (1–2), strong (3 or more).

### 10.6 Risk interpretation and limitations

This score is a **heuristic summary of clauses detected by this pipeline**. It is not a probability that the borrower will default, a measure of fairness, a regulatory compliance result, or a recommendation about taking a loan. The configured bands are not empirically calibrated against actual borrower losses/defaults. A missing clause can mean either the agreement does not contain it or the scan failed to retrieve/classify it. Very long documents can return `needs_retrieval` because the risk pipeline has a scan-call budget and does not have a retrieval-based risk fallback in the current service. The UI also displays a sample score range (41.2–51.7) as context from project evaluation data; it is not a universal expected range.

## 11. Translation

The translation endpoint supports:

- Hindi (`hi`)
- Tamil (`ta`)
- Bengali (`bn`)
- Punjabi (`pa`)
- Malayalam (`ml`)

Currently the UI offers translation of the **short summary** and eligible **chat turns**; it does not translate every key-info field or the detailed summary.

The backend sends eligible English prose to Gemini with instructions not to add facts and to preserve numbers/dates. `src/translate/number_check.py` compares numeric/date tokens in the source and translation. If the first translation fails the token check, the system retries once with feedback. If the second attempt still fails, the invalid translation is not returned as a successful result. Translation outputs are cached as files. The check is only a numeric/date consistency guard; it does not prove the translation is legally or linguistically accurate. Legal terminology may be mistranslated and should be reviewed by a fluent subject-matter expert.

Verbatim evidence quotes are treated separately from prose so the system does not translate a source quote and then present it as if it were still verbatim.

## 12. Quotas, API calls, and error states

`config/app.yaml` sets a daily soft limit of 60 live Gemini calls and per-task budgets (summary 10, key-info 20, risk 15, chat 6). The task service counts logged calls using the configured quota timezone and can return a clean `quota_blocked` result. Task outputs are saved and can be served from cache. The Gemini client also has response caching, rate limiting, retry/fallback behavior, and sanitized logging.

Common visible states include not started, queued/running, done, partial, failed, quota blocked, and (for risk) needs retrieval. A cached completed result can be displayed without re-running all model work.

## 13. Frontend experience

The single-page React application in `web/src/App.jsx`:

1. Loads API metadata and notices.
2. Validates the selected file on the client and posts it to the API.
3. Polls ingestion progress and loads page 1 when ready.
4. Displays extracted page text with source/quality badges and previous/next navigation.
5. Provides Summary, Key Info, Risk Analysis, and Chat tabs.
6. Passes page-jump handlers to the feature tabs so citations can navigate to the source page.

Summary, key-info, and risk work are initiated with buttons and polled until a result is available. Chat submits questions directly. The UI warns users that uploads should be public and that results are informational only.

## 14. Data and project repository layout

- `app/api/`: FastAPI application, task coordination, upload ingestion wrapper, chat and risk services.
- `src/qa/`: document loading, chunking, BM25 retrieval, routing, answering, quote verification, answer verification.
- `src/extract/`: extraction schema, key-field extraction and value matching.
- `src/summarize/`: summary generation and validation.
- `src/calc/`: input extraction and deterministic calculation formulas.
- `src/risk/`: clause splitting, keyword prefilter, model classification, severity rules, scoring.
- `src/translate/`: translation and numeric-token checks.
- `src/llm/`: Gemini client and configuration-driven model calls.
- `scripts/`: ingestion, data preparation, demos, comparisons, evaluation and offline test scripts.
- `config/`: YAML configuration for supported feature behavior.
- `web/`: React/Vite user interface.
- `data/raw/`, `data/friend/`, and `data/processed/`: document inputs, evaluation/annotation resources, and generated processing artifacts. Treat the raw/friend corpus as source/evaluation material rather than application database tables.
- `docs/`: project report, decisions, risk method, OCR comparison, work reports, and this guide.

Project reports describe an ingestion/evaluation corpus of 46 documents and 607 pages (16 Indian loan documents, 20 CUAD documents, and 10 SEC loan documents). These corpus-processing figures describe the evaluation/data scripts; they do not imply that all of those documents are loaded into the running web app.

## 15. Dataset: sources, preparation, annotation, and use

There is not just one project dataset. The repository has several related collections used for different jobs: a large public-contract text archive, a smaller set of Indian loan-product documents, a document-ingestion/OCR benchmark set, annotation/evaluation material, and AI-assisted silver labels. They must not be conflated.

### 15.1 Main public-contract text archive

The primary large text source is:

`data/friend/01_loan_agreements/publicly_filed_contracts.zip`

The archive contains **18,508 `.txt` contract entries**. Their path/document identifiers resemble public filing identifiers and the project reports describe these as publicly filed SEC/EDGAR-style agreements. The archive is not made up exclusively of loan contracts. The preparation pipeline reads candidate metadata and source text, screens for likely loan/credit agreements, calculates SHA-256 hashes, and applies quality/duplicate rules before making a clean loan subset.

`scripts/build_processed_v1.py` and its generated reports describe this process:

- The manifest contains 18,508 candidate documents.
- The resulting clean loan set contains **11,901 documents** after the documented selection and duplicate handling.
- The clean set is split by **company**, not by individual document, into 8,330 train, 1,786 validation, and 1,785 test documents. The split is deterministic (seed 42); the same company is kept in only one split to reduce company-level leakage.
- The preparation report identifies three human-reviewed/reference documents and reserves them for test; two meet the clean filters and one is retained separately as a `gold_extra`.
- Duplicate detection uses SHA-256. Canonical copies are retained, and duplicate copies are flagged rather than treated as independent examples.
- `manifest.csv`, `clean_loans.csv`, `filter_report.md`, `quality_report.md`, `field_mapping.csv`, and `CHANGES.md` record document scope, filtering, splits, and transformations.

This large archive supports document selection, citation/evidence lookup, research scripts, and preparation of annotation material. It is **not a database** and the full 11,901-document set is not automatically used by every app request.

### 15.2 Indian loan/MITC PDF collection

The Indian collection is stored under `data/raw/08_indian_bank_loans/` with a scope record in `data/processed/indian_source_scope.csv`. A **MITC** is a lender's “Most Important Terms and Conditions” disclosure document.

- There are 27 PDFs in the folder, but the current loan-corpus manifest marks **16 as in scope**: 12 pre-existing PDFs and 4 later additions (one Tata Capital MITC and three Piramal Finance MITCs).
- The 12 pre-existing PDFs include DBS, Clix/CHFL, Muthoot Homefin, GICHF, Bajaj Housing Finance, and a personal/business loan agreement. The set includes English and Indic-language documents, including Hindi, Bengali, Punjabi/Gurmukhi, and Malayalam or bilingual pages.
- The four later additions have official Tata Capital/Piramal Finance URLs recorded in the source manifest. The original source URLs for the 12 pre-existing files are not recorded, so the project cannot claim verified download provenance for those 12 based on the current manifest alone.
- The other 11 newer PDFs remain in raw storage but are excluded from this loan corpus because they are unrelated document types or a credit-card MITC. A sample containing personal/identity information was excluded rather than used.

The original URLs and provenance caveat are important: “in the project folder” does not always mean “downloaded from a currently verified official URL.” The manifest stores SHA-256 hashes and scope decisions so the files can be identified consistently.

### 15.3 CUAD and other test material

The project also uses CUAD-related contract material and SEC/EDGAR contract text for general contract-processing experiments. The Stage 2a ingestion report describes a 46-document batch:

| Group in the reported batch | Documents | Purpose |
|---|---:|---|
| In-scope Indian loan PDFs | 16 | Test loan-document ingestion and Indic-language handling |
| CUAD contract PDFs | 20 | Additional contract ingestion/OCR examples; contextual contract material |
| SEC EDGAR loan files | 10 | Long public loan agreements and clause-oriented testing |
| **Total** | **46** | **607 pages** |

This is a processing/evaluation batch, not the live app's permanent corpus and not a set of training examples. Separately, the OCR comparison experiment used **64 Indian loan-document pages and 20 SROIE receipt images** (84 items) to compare OCR engines. SROIE receipts are an OCR benchmark only; they are not loan-agreement examples. The CUAD material is also not interchangeable with the Indian loan corpus.

The Stage 2a work report says the 46-document batch completed without crashes and covered 607 pages. It reports 52 pages OCR-processed across 17 files, 320 extracted tables across 17 files, and page-marker checks passing for all 46 text outputs. These are batch-level processing measurements, not labels or model-accuracy scores.

### 15.4 Preparation and quality-control steps

The data preparation work follows this general sequence:

1. **Identify and scope sources.** Use public contract text and lender-hosted loan/MITC documents. Record the filename, source URL where known, document type, language, inclusion/exclusion decision, and hash. Unknown provenance is recorded as unknown rather than filled in by guessing.
2. **Screen documents.** Classify likely loan agreements versus unrelated contracts, policies, privacy terms, or credit-card disclosures. Filter by primary-contract status, sufficient text length, and duplicate hash as applicable.
3. **Preserve the source.** Keep original source material read-only. Generated manifests, normalized annotations, page text, OCR results, and evaluation sheets are written to processed/output folders.
4. **Extract text by page.** Read PDF text layers; use OCR for pages needing it; preserve page markers; record quality metadata; and attempt table extraction.
5. **Check source integrity.** Record hashes, page counts, text lengths, encoding indicators, and quote/page evidence. A quote-presence check means that text occurs in the extracted source; it does not prove that the interpretation or label is correct.
6. **Create versioned evaluation splits and review sheets.** Keep documents from a company in one split. Create separate blank rows for key fields, risk clauses, and Q&A rather than making up labels.
7. **Separate proposal from decision.** Automated/model-generated values are marked as candidates or silver labels. Human decisions, uncertainty, source evidence, reviewer/date, and any second review must be recorded separately before calling data approved gold.

### 15.5 What “labeling” and “annotation” mean here

**Annotation** means adding structured information to a source document so a program or evaluator can refer to it consistently. A **label** is one of those structured decisions. For this project, the annotation should be traceable to a source quote and page/section.

#### Key-information annotation

A reviewer examines a loan document and records the applicable 16 fields: title, date, parties, amount, interest, repayment, maturity/termination, fees, late/default charges, prepayment, collateral, guarantees, defaults, and governing law. Each record should include:

- The proposed/approved value, or a status such as absent, unclear, or deferred to another document.
- An exact evidence quote and page/section locator.
- A reason for uncertainty or cross-reference when relevant.
- Review decision, reviewer identity, date, and second-review/adjudication details where required.

`not_present` means the term is not found after checking the relevant document. `unclear` means the source is unreadable, incomplete, or ambiguous. `deferred` means the agreement expressly points to a separate note, schedule, fee letter, or other instrument; the missing document's terms must not be guessed. This distinction prevents silence or an unavailable schedule from being mislabeled as a known loan term.

#### Risk-clause annotation

A reviewer selects a relevant clause and records its clause text, page, clause type/category, severity (`Low`, `Medium`, `High`, `Critical`), evidence, and reviewer rationale. Risk severity is a judgment under the rubric, considering the trigger, cure/notice, discretion, scope, and possible consequence. It is not simply a word lookup, and a category or severity is not a legal conclusion.

There is a taxonomy difference across repository artifacts: the production risk scanner/configuration uses **seven scoring categories**, while the human labeling guideline and some annotation schemas include an eighth `Other` category. The production score cannot score `Other` with the current seven-category weights. Treat this as a version/schema mismatch when comparing labels with app output.

#### Q&A annotation

A QA example pairs a question with an expected answer/status, supporting source clause/quote, page/section, and review status. It may also record whether a question is answerable from the document. These examples test retrieval and answering; they are not key-field labels or risk labels.

### 15.6 Annotation sheets and review status

The `data/processed_v1/` preparation report currently describes:

| Review material | Scope | Current meaning |
|---|---:|---|
| Key-information sheet | 60 documents × 16 fields = **960 rows** | Blank human-review fields; candidate review tasks, not 960 completed human labels |
| Risk-clause sheet | **1,500 clauses** from those 60 documents | Candidate clause excerpts; category/severity/reviewer label columns blank |
| QA sheet | 30 documents × 4 = **120 blank rows** | Questions/answers still need human preparation |
| Normalized existing annotation records | **234 rows** after removing 39 duplicate rows | Merged existing reviews/proposals with normalized field aliases; not automatically approved gold |

The 60 documents are selected from the public-contract archive within a text-length range (30,000–400,000 characters), stratified by contract year, and not identified as gold documents. Risk candidate clauses are selected using control-file sections or risk keywords, balanced across documents and capped at 1,500. The QA sheet creates four blank question rows for each of 30 selected documents. The build script explicitly does not generate human risk labels, rationales, questions, answers, or approvals.

### 15.7 Existing source-backed QA examples

`data/friend/04_annotated_data/qa_evaluation_candidates.csv` contains **36 source-backed question/evidence candidates across three contracts**. Rows include topic, question, expected answerability/status, expected answer, supporting clause, section/page, and review status. The project work report describes these as source-verified candidates. A retrieval evaluation used 35 usable rows from this sheet (one row had no supporting quote/page) plus eight factual questions from another small test set, making 43 queries for the reported BM25 Hit@K results.

These are useful for testing whether search can surface the expected evidence. They are a small evaluation set, not a representative sample of all borrower questions, and retrieval hit rate is not the same as end-to-end answer accuracy.

### 15.8 AI-assisted “silver” labels versus human “gold”

These terms must be kept distinct:

- **Silver labels** are model/AI-assisted suggestions checked for evidence occurrence and consistency. They help explore task schemas and build provisional comparisons, but can contain model errors and are not independent human truth.
- **Gold labels** are intended to be source-verified human decisions under a documented rubric, with uncertainty, provenance, and review/adjudication recorded. They should be frozen as evaluation references and kept separate from prompt examples or tuning data.

The existing `data/processed/labels/llm_assisted/llm_assisted_README.md` reports:

- **Key-field silver:** 10 pilot documents × 16 fields = **160 rows**; 133 `found`, 18 `NOT_PRESENT`, 9 `UNCLEAR`; 142 quotes automatically verified, 0 quote-verification failures. These are AI-assisted silver labels, not human gold.
- **Risk-clause silver:** **209 clauses across 13 documents** (10 SEC pilot documents and 3 Indian MITCs); 209/209 quotes reported as verified. A later consistency revision pass changed 43 rows under the rubric rules R1–R3. These revisions remain silver, not independent human labels.
- **Not completed in that pilot:** Q&A silver labels, summary references, a second-pass agreement study, and human spot-checks were not completed according to the README.

The separate human-review workspace records a newer key-info review phase:

- Four candidate batches (DBS, Bajaj Housing Finance, Muthoot Homefin, and CITGO) contain **64 fields total** (16 each). The project owner/user recorded acceptance decisions for all 64 entries.
- Their status counts are 32 `EXPLICIT`, 19 `DEFERRED`, 9 `NOT_PRESENT`, and 4 `UNCLEAR`.
- These are **user-accepted candidates, not a finalized Gold dataset**. The four `UNCLEAR` items still need recorded independent review or adjudication; review-event provenance is incomplete; visual verification is partial for some documents; and no completed second review is claimed.
- The file `KEY_INFO_GOLD_APPROVED.csv` is listed as future/not created. No approved human risk-clause Gold dataset is reported.
- An older `gold_standard_extraction_v1.csv` contains 27 records across three SEC contracts and records approved statuses, but an audit identified conflicting earlier status fields and reviewer identity/approval evidence that was not independently authenticated. It can be described as a historical file recorded as approved, but its provenance discrepancy should be resolved before treating it as unquestioned benchmark truth.
- `manual_gold_review_initial_3.csv` has 27 populated review records but `needs_review` statuses; it is not approved gold.

Thus, both statements—“there are no human labels in the blank 960/1,500/120 review sheets” and “some smaller reviewed candidate records exist”—can be true. They refer to different files and stages. Always say **which dataset/file and review status** is being described.

### 15.9 How the dataset helps the project

The datasets support different purposes:

| Data purpose | How it helps |
|---|---|
| Public source contracts | Develop and test text extraction, clause splitting, document loading, and source-grounded evidence workflows |
| Indian MITC PDFs | Test lender-specific disclosure formats, multilingual pages, scanned pages, and OCR/text-quality edge cases |
| CUAD / general contract samples | Provide additional contract layouts and OCR/ingestion examples outside the Indian loan-product set |
| Key-field annotations | Define what “loan amount,” “interest,” “fee,” “default,” etc. mean and provide a reference for evaluating extraction |
| Risk-clause annotations | Apply a consistent category/severity rubric and assess clause-level classification |
| QA examples | Test whether retrieval finds supporting clauses and whether answers cite the correct passage/page |
| OCR reference pages | Compare engines using CER and help identify language/page-quality cases that need attention |
| Gold/provisional labels | Separate evaluated human references from model suggestions and expose uncertainty/missing companion documents |

The project does **not** fine-tune or train Gemini or a custom model on these datasets. Gemini is called at runtime for supported tasks; Python rules and BM25 provide deterministic processing/retrieval. The dataset primarily supports development, prompt/rule calibration, regression tests, OCR comparison, and evaluation.

### 15.10 Dataset limits and what not to claim

- The raw/public archive is broad and includes non-loan contracts; only subsets are filtered for particular experiments.
- The 46-document/607-page ingestion batch, 84-item OCR comparison set, 18,508-entry public-contract archive, 60-document review sheets, 10-document key-field silver pilot, and 13-document risk silver pilot are **different scopes**. Their counts should never be added together as if they were unique records.
- The official provenance of all original Indian PDFs is not known. Only the later in-scope additions have source URLs recorded in the manifest.
- Machine quote matching checks text presence; it does not validate field correctness, risk judgment, legal meaning, or full-document OCR accuracy.
- Most large annotation sheets remain blank. Four small accepted candidate batches are not final Gold. An older 27-row reference file has an audit caveat. Human Gold coverage is therefore limited and should be reported with the exact source/status.
- The dataset is not balanced across jurisdictions, lenders, document types, languages, or risk outcomes. Reported benchmark metrics are small-sample and should not be generalized to all loan agreements.
- Keep personal, confidential, or customer-specific documents out of public datasets and demos. The app warns users to upload public documents; any uploaded text sent to Gemini is processed by a third-party service under that provider's terms.

## 16. Evaluation and known limitations

The detailed numbers and caveats are in `docs/FINAL_REPORT.md`, `docs/WORK_REPORT.md`, and `docs/OCR_COMPARISON.md`. Key takeaways in the existing final report:

- Some evaluated sets achieved 100% quote-existence verification. This measures whether a quote can be found in text, not whether the answer's interpretation is correct.
- Reported key-field extraction F1 was below the project's target (silver strict F1 28.2%, lenient F1 56.3%). There is no large independent expert-annotated gold set.
- BM25 retrieval Hit@5 was reported at 88.4% on a 43-question retrieval benchmark; this is retrieval evidence, not proof of correct final chatbot answers in general use.
- Risk severity agreement was reported at 88.3% within one severity level on a small silver dataset; risk score bands remain heuristic and uncalibrated.
- Translation numeric checks do not measure semantic fluency/legal correctness.
- OCR quality depends on scan clarity, language-pack availability, page layout, and extraction quality. Indic text can be difficult, especially in bilingual documents and tables.
- The current risk scan has seven categories, although an older final-report abstract refers to eight. Use the current configuration and code as ground truth for this implementation.
- Some older documentation describes broader feature plans or stronger guarantees than the present implementation. In particular, APR calculator support is not present in the current formulas module, and upload OCR does not call Gemini Vision automatically.

These are real limitations, not just presentation details. A technically valid quote, a completed API task, or a deterministic score does not mean that the system's interpretation is legally authoritative.

## 17. Running locally

Run commands from the repository root in Windows PowerShell. Install the project dependencies and ensure Tesseract (with required language packs for desired Indic OCR) is installed/configured. Set `GEMINI_API_KEY` in the environment for live Gemini features.

```powershell
pip install -r app\requirements.txt
```

Start the backend in one terminal:

```powershell
python -m uvicorn app.api.main:app --port 8000
```

Install frontend dependencies once and start Vite in another terminal:

```powershell
cd web
npm install
npm run dev
```

Open `http://localhost:5173`. The API health check is `http://127.0.0.1:8000/api/health`.

To run the repository's offline test runner from the root:

```powershell
python scripts\run_all_offline_tests.py
```

The offline suite is intended to avoid live Gemini calls; individual benchmark/demo scripts may make live calls unless their instructions say otherwise. Check each script before running it.

## 18. Short presentation summary

> The AI Loan Agreement Analyzer is a React and FastAPI application that ingests loan agreements, extracts page-level text from PDFs/HTML/TXT, and uses Gemini plus deterministic Python checks to produce summaries, key agreement fields, document-grounded Q&A, risk-clause findings, translations, and calculations. It uses Tesseract OCR for scanned/poor-text PDF pages in the upload path and pure-Python BM25 retrieval for long-document question answering. It stores documents and results as files rather than using a database. Factual outputs are paired with source quotes/pages where available; numeric calculators use Python Decimal formulas. Risk findings are classified from candidate clauses, quotes are checked against source pages, and a weighted padded-top-three score is computed across seven categories. The system is an informational aid only: model classification, OCR, extraction, translation, and risk scoring can be wrong, and the risk bands are not calibrated legal or default predictions.
