# Grounded Loan Agreement Analysis and Translation System: Final Project Report

## 1. Abstract

Loan agreements are binding legal contracts that are notoriously lengthy, dense, and difficult for non-specialist borrowers to navigate. This project presents an automated, grounded document analysis system designed to provide clear, clause-by-clause contract information without giving legal or financial advice. The system extracts concise and detailed document summaries, 16 standardized key loan parameters with verified verbatim quotes and page numbers, an interactive grounded question-answering assistant, interactive loan calculators (EMI, APR, prepayment penalty), an explainable risk scoring engine (0–100) across 8 legal risk categories, and machine translation into 5 Indic languages (Hindi, Tamil, Bengali, Punjabi, Malayalam). To guard against language model hallucinations, the pipeline uses deterministic verification gates: every extracted fact requires an exact quote and page verified against source text by script, every translation requires an automated numeric/date consistency check with a single-retry feedback loop, and all safety refusals provide standardized neutral document information. Evaluated across 46 contracts (607 pages), the system achieved 100% quote verification on evaluated sets, while highlighting empirical limits: silver-label key-field extraction F1 reached 56.3% lenient (28.2% strict), whole-document risk severity within-1 reached 88.3%, and human gold benchmarking remains at zero.

---

## 2. Problem and Significance

Retail and small-business borrowers frequently enter credit transactions without fully understanding the underlying legal agreements. Standard loan documents—including Key Fact Statements (KFS), Most Important Terms and Conditions (MITC), promissory notes, and facility agreements—range from 2 to over 100 pages of fine print. They contain complex covenant structures, unilateral modification rights, stringent default definitions, and compound penalty clauses.

When borrowers turn to commercial generative AI systems to summarize their agreements, they encounter two severe risks:
1. **Hallucination of Financial Figures**: Models frequently invent, misread, or swap interest rates, fees, tenure months, and calculation formulas.
2. **Unauthorized Legal Advice**: Conversational models often issue subjective advice ("accept this loan", "this fee is unfair"), exposing users to ungrounded decisions and creators to legal liability.

This project addresses these issues by engineering an information-only analysis platform. The system does not tell borrowers what to do, does not negotiate, and does not evaluate commercial fairness. Instead, it surfaces verified document disclosures, identifies borrower-unfavorable clauses with exact citations, and verifies every numeric token deterministically before display.

---

## 3. System Capabilities

The system provides six core user-facing capabilities via a single-page web interface:
1. **Grounded Summaries**: Concise short summaries (under 120 words) and structured section breakdowns with page citations, where every sentence is checked by script against the cited page text.
2. **16 Key Parameter Disclosures**: Automated extraction of 16 vital loan terms (lender name, borrower name, loan amount, interest rate, tenure, repayment frequency, prepayment terms, late penalty, default interest, processing fee, collateral, governing law, arbitration, cure period, grace period, unilateral change rights). Every non-empty value includes a verified verbatim quote and page link.
3. **Grounded Chat and Q&A**: A conversational query interface with BM25 hybrid document retrieval, intent routing, verbatim quote verification, page-jump navigation, and an automatic neutral refusal for subjective advice questions.
4. **Loan Repayment Calculators**: Deterministic mathematical estimators for Equated Monthly Installment (EMI), Annual Percentage Rate (APR), and prepayment penalty amounts, binding inputs directly to document-extracted quotes.
5. **Explainable Risk Assessment**: A composite risk score from 0 to 100 based on whole-document scanning across 8 risk categories (Default, Penalties, Financial, Repayment, Collateral, Termination, Covenants, Dispute Resolution), displaying clause-level severity tags and evidence strength.
6. **Guarded Indic Translation**: On-demand translation of summaries and chat prose into Hindi (`hi`), Tamil (`ta`), Bengali (`bn`), Punjabi (`pa`), and Malayalam (`ml`), guarded by an automated number/date token validator.

---

## 4. Architecture and Pipeline Stages

The system operates across distinct sequential stages. Every technical and financial term used is defined below:

### Terms and Definitions
- **OCR (Optical Character Recognition)**: Software that reads scanned PDF page images and converts them into machine-readable text.
- **BM25**: A classic statistical keyword search algorithm that scores chunks based on matching query words.
- **Hit@K**: The percentage of test queries where a relevant document passage appears in the top K retrieved results.
- **Verbatim Quote**: An exact, word-for-word excerpt copied directly from the original document text.
- **Key Information**: The central operational numbers and terms of a credit agreement.
- **Tenure**: The total scheduled duration over which a loan must be repaid.
- **Prepayment / Foreclosure**: Paying off a loan balance earlier than scheduled, which often triggers contract penalty fees.
- **Default**: A contractual breach or failure to meet loan conditions that entitles the lender to accelerate repayment.
- **Indemnity**: A borrower obligation to compensate the lender for specific legal costs, taxes, or losses.
- **Governing Law / Jurisdiction**: The territorial laws and courts designated to resolve contract disputes.
- **EMI (Equated Monthly Installment)**: A fixed periodic payment made by a borrower on a designated monthly date.
- **APR (Annual Percentage Rate)**: The annualized total cost of borrowing, incorporating interest and upfront fees.
- **Risk Score**: A weighted numeric indicator from 0 to 100 reflecting the density and severity of borrower-unfavorable clauses.
- **Severity Band**: Standardized risk tiers (Low, Moderate, High, Critical) defined by score ranges.
- **FastAPI / Uvicorn**: A modern Python web framework and server running asynchronous REST endpoints.
- **React / Vite**: A modern JavaScript user interface framework and build engine powering the browser application.
- **Multiset / Counter**: A collection data structure that counts exact occurrences of individual numeric values.
- **Indic Scripts**: The family of native writing systems used in India, such as Devanagari, Gurmukhi, and Tamil.
- **chrF**: A character n-gram F-score used to evaluate machine translation similarity against a reference text.
- **Silver Labels**: Reference evaluation answers generated by a high-capacity model rather than human specialists.
- **Human Gold**: Evaluation labels created and verified by human legal and financial professionals.
- **F1 Score**: The harmonic mean of precision and recall measuring extraction accuracy.

### Pipeline Stages
1. **Ingestion and OCR**: The system ingests PDF, text, and HTML agreements, validates magic bytes, and extracts plain text page by page. For scanned pages with insufficient text density, it runs Tesseract OCR and records character extraction quality metrics.
2. **Q&A Retrieval and Router**: Incoming user questions are classified into categories (`fact`, `calculation`, `explain_term`, `off_topic`, `advice`). Queries for factual document terms use BM25 to find relevant passages, invoke Gemini to locate answers, and strictly verify that cited quotes match document text character-for-character.
3. **Key Information Extraction**: The pipeline extracts 16 standardized fields using zero-temperature structured prompts. A deterministic repair routine recovers contiguous source spans (`<= 400` characters) when quotes contain minor OCR hyphenation or whitespace differences, and marks fields defined by reference to outside schedules as `deferred_to_other_document`.
4. **Grounded Summaries**: Plain-English summaries are generated using a deterministic sentence-level filter. Any generated sentence containing ungrounded numbers, missing page tags, or advisory words is dropped before display.
5. **Deterministic Calculators**: When a user asks about loan payments, a calculator module extracts loan amount, interest rate, and tenure directly from verified document quotes and computes exact standard formulas without language model arithmetic.
6. **Risk Scoring and Document Scan**: The whole document is scanned in overlapping clause windows against 8 defined borrower risk categories. Flagged clauses receive severity points (Low=1, Medium=2, High=3, Critical=5), combined into a category-weighted score (0–100) with category sub-breakdowns.
7. **Backend API**: A FastAPI application manages asynchronous document tasks (summary, keyinfo, risk, chat, translate), enforces upload file-size limits, sanitizes file paths, tracks daily API call budgets, and caches all task results as JSON on disk.
8. **React Web Application**: A single-page web interface built with plain CSS and React presents document analysis in clean tabs (Summary, Key Info, Risk Analysis, Chat, Document Viewer), synchronizing page jumps across citations.
9. **Translation with Numeric Guard**: Summaries and chat answers can be translated into 5 Indic languages. Before presenting translated text to the user, a pure-Python checker extracts numbers and dates from both texts and asserts multiset equality. If numbers mismatch, an automatic single-retry correction prompt is dispatched; if it still fails, the translation is hidden and the original English is shown.

---

## 5. Safety and Guardrail Design

To prevent harm and misinformation, the architecture implements five non-negotiable safety rules:
1. **Mandatory Verbatim Quote Verification**: Every extracted field, summary claim, and factual chat answer must include an exact text quote and page number. If an extracted quote cannot be found in the document by an independent script, the value is marked `unverified` and hidden from the user.
2. **Permissible Non-Extraction ("Not Found")**: The system explicitly instructs models to return `not_found` or `deferred_to_other_document` when a clause is absent or defined in an unattached schedule, preventing over-answering and forced guesswork.
3. **Visual Verification Indicators**: Fields extracted with single-model fallbacks or lower lexical overlap carry prominent badges (`not independently verified` or `needs review`) directly in the user interface.
4. **Hard Quota Guard**: A tracking counter records every live call made within the reset window (America/Los_Angeles timezone). If the daily soft limit is reached, all subsequent tasks immediately stop and return a clean `quota_blocked` notice without hanging or crashing.
5. **No Advice Rule**: The system provides document information only. It refuses all subjective advisory prompts (e.g. "Should I sign this agreement?") with a fixed neutral notice explaining that it does not provide legal or financial advice and can only display stated fees, risks, and penalties.

---

## 6. Evaluation Results

The evaluation results below reflect real measured figures from repository test runs and benchmark runs, strictly matching the project FACTS:

| Target Area | Pre-Registered Target | Measured Result | Evaluation Status |
| :--- | :--- | :--- | :--- |
| **Quote Grounding** | `>= 99.0%` quotes verified in source | `58/58 (100.0%)` on 5 benchmark documents; `67/67 (100.0%)` on personal_business_loan_agreement | **TARGET MET** (on tested sets) |
| **Key Parameter Extraction F1** | `>= 85.0%` F1 against benchmark labels | Silver strict F1: `28.2%`, lenient F1: `56.3%`; Human check: strict `5/27 (18.5%)`, lenient `8/27 (29.6%)` | **TARGET MISSED** |
| **Q&A Document Retrieval** | `>= 85.0%` Hit@5 retrieval rate | BM25 Hit@5: `88.4%`, Hit@8: `97.7%`; Intent Router: `40/40 (100.0%)` on self-written set | **TARGET MET** (on synthetic set) |
| **Q&A Answer Correctness** | `>= 85.0%` accuracy on human gold | Human gold labels = `0`; not evaluated on human expert set | **NOT MEASURED** |
| **Correct Absence Identification** | `>= 90.0%` correct "not found" identification | Handled in extraction pipeline; no human gold absence test set | **NOT MEASURED** |
| **Citation Page Accuracy** | `>= 90.0%` page number accuracy | All `19/19 (100.0%)` summary numbers verified on cited pages; human gold = `0` | **NOT MEASURED** (on gold set) |
| **Whole-Document Risk Severity** | `>= 90.0%` severity within-1 agreement | `88.3%` on 7-document silver dataset | **TARGET MISSED** |
| **Whole-Document Risk Macro-F1** | `>= 70.0%` macro-F1 across 8 categories | Hold-out 37 rows (by rule author): category 33/37, severity within-1 34/35; macro-F1 uncalculated | **INCONCLUSIVE** |
| **Offline Test Suite Execution** | 100% offline tests passing, delta = 0 | 6/6 test scripts passing in `run_all_offline_tests.py`, zero Gemini calls | **TARGET MET** |

---

## 7. Indic Translation Findings

The machine translation pipeline was evaluated across unit tests, offline endpoint simulations, and a live sample run:
- **Logic Verification**: The offline test suite (`scripts/test_5b_translate.py`) validated that good translations pass, altered numbers trigger an explicit retry, repeated failures return `number_check_failed` with a blank translated string, cached calls execute with `live_calls = 0`, and verbatim quotes in document evidence are never passed to the translator.
- **Live Translation Sample**: A live Hindi translation test was executed on the summary of `03_dbs_mitc.pdf`. The translation passed the automated numeric check (`check_numbers: pass`); however, the only numbers present in that summary text were page citations (`[p. 1]`, `[p. 2]`).
- **Linguistic and Legal Limitations**: A manual check of the live Hindi output revealed legal terminology issues: the legal concept of "material breach" was translated using a Hindi word meaning "physical" or "concrete substance" rather than contractual significance. Formal character error metrics (chrF) were not measured, and translations have not been reviewed by native legal linguists.

---

## 8. Known Limitations

1. **Zero Human Gold Evaluation**: The project dataset consists of 46 documents (607 pages) with silver labels generated by model pipelines. Human gold benchmark labels remain at zero, except for a tiny preliminary check of 27 key-field rows.
2. **Model Family Bias**: Silver labels and extraction logic both use models from the Gemini family, introducing shared failure modes.
3. **Subjective Risk Severity**: Risk severity scoring relies partly on human judgment. The single finance reviewer who assisted in rule calibration was an AI mentor persona, and the 37 hold-out validation rows were evaluated by the same reviewer who designed the scoring weights.
4. **Uncalibrated Risk Bands**: Risk score bands (Low `< 25`, Moderate `25–50`, High `50–75`, Critical `>= 75`) were assigned by heuristic design rather than empirical default distribution calibration; across labeled benchmark agreements, observed scores fell in a narrow band (`41.2–51.7`).
5. **Optimistic Builder-Written Tests**: Test suites for translation, calculators, and intent routing were authored by the builder and represent optimistic functional evaluations rather than adversarial stress tests.
6. **Free-Tier Verifier Quota Limits**: Google's free-tier daily request caps prevented running an independent larger model (`gemini-3.5-flash`) as an external verifier judge, forcing pipeline components to share the `bulk` role model (`gemini-3.5-flash-lite`).
7. **Screen-Only Advice Override**: The neutral refusal text for advice queries is enforced at the user interface presentation layer and API boundary; raw underlying chat history preserves original assistant tokens.
8. **Document Length Limits**: The pipeline has not been tested on loan documents exceeding 400,000 characters.
9. **UI Edge States Unseen Live**: User interface alert banners for `needs_review` and `unverified` risk items function in code but have not been observed in live end-to-end runs with real document data.
10. **Development Server Advisory**: A known dependency advisory exists in Vite development server dependencies (`npm audit`); this affects only local development servers and does not affect production static builds.

---

## 9. Future Work (Not Done)

1. **India-Specific Regulatory Rules Pack (Stage 4c)**: Implementing an automated compliance check against Reserve Bank of India (RBI) Digital Lending Guidelines and fair practices codes, linking each rule to a verified RBI circular URL and date.
2. **Indic Document OCR and Text Repair**: Building specialized image preprocessing and font glyph normalization for bilingual Indian agreements where scanned Hindi PDF tables suffer from broken character encoding.
3. **Independent Human Gold Dataset**: Constructing an adjudicated human gold benchmark comprising 60–100 annotated risk clauses and 30+ complete key-parameter agreement disclosures.
4. **Formal Translation Quality Evaluation**: Measuring chrF++ and BLEU scores across Indic translations using reference texts authored by legal translators.
5. **Risk Band Empirical Calibration**: Re-anchoring the 0–100 risk scoring formula across a balanced corpus of low-risk public bank agreements and high-risk predatory fintech contracts.
6. **Triple-Document Demonstration Corpus**: Preparing three completely verified, multi-page public agreements representing consumer personal loans, commercial facility notes, and retail credit cards for demonstration.

---

## 10. How to Run the System

All steps must be executed from the project root directory (`C:\finalYear`) in a Windows PowerShell terminal.

### Step 1: Install Dependencies
Ensure Python 3.11+ and Node.js 20+ are installed:
```powershell
# Python backend dependencies
pip install -r app\requirements.txt

# Web frontend dependencies (execute from web directory)
cd web
npm install
cd ..
```

### Step 2: Start the Backend API Server
In the first PowerShell window:
```powershell
python -m uvicorn app.api.main:app --port 8000
```
*The FastAPI backend will start at `http://127.0.0.1:8000`. Health check endpoint: `http://127.0.0.1:8000/api/health`.*

### Step 3: Start the Web Application
In a second PowerShell window:
```powershell
cd web
npm run dev
```
*The Vite development server will start at `http://localhost:5173`. Open this URL in your web browser to use the interface.*

### Step 4: Run the Complete Offline Test Suite
In a third PowerShell window (runs with zero Gemini API calls):
```powershell
python scripts\run_all_offline_tests.py
```

---

## 11. Ethical Considerations

- **Public Document Usage**: The platform is restricted to public, non-confidential sample agreements, standard bank terms, and anonymized regulatory filings. Users are explicitly warned not to upload private personal agreements or confidential financial statements.
- **Third-Party Model Terms**: Users must be aware that free-tier Gemini API calls are subject to Google's terms of service, which may allow submitted text to be processed for model evaluation and improvement.
- **Information, Not Advice**: This software is an informational document navigation and extraction tool. It is not an attorney, financial planner, or legal advisor. It cannot replace professional legal counsel, and it cannot evaluate whether an agreement is advantageous, fair, or suitable for any borrower's individual financial situation.
