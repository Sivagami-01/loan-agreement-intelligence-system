# MASTER PLAN: AI Loan Agreement Analysis and Explainable Risk Assessment System

OWNER: solo student, no finance knowledge. Make decisions yourself, explain loan terms in one line, record every decision in docs\DECISIONS.md (decision, reason, alternative).

GOAL: user uploads a loan agreement (PDF or scan; English and Indian languages). System returns: concise + detailed summary; key info (lender, borrower, amount, interest rate, tenure, repayment/EMI, fees, late-payment charges, prepayment/foreclosure, collateral, dates, default, penalties, termination); Q&A chatbot with page/clause citations; explainable risk score 0-100 with contributing clauses; translation into Hindi, Tamil, Bengali, Punjabi, Malayalam. REAL documents only, no synthetic data. Quality target: close to Claude/ChatGPT/Gemini, achieved with an LLM API + grounding + verification. Be honest about uncertainty: "not found in this document" is a valid answer.

RULES FOR EVERY TOOL
- Environment: Windows, Python 3.13, C:\finalYear. API key only in env var GEMINI_API_KEY (never print, never write to files, never in logs).
- Read-only: data\raw, data\friend, data\processed_v1, data\processed\parsed. Write only to data\processed, scripts, src, app, web, tools, docs.
- Every extracted value carries a verbatim quote + page/location; a script verifies the quote occurs in the source text (whitespace-normalised). Unverified values are dropped or marked "needs checking". Never invent labels.
- Write real .py files, UTF-8, re-runnable, print progress, log failures and continue.
- After EACH stage: append results (counts, metrics, failures) to docs\WORK_REPORT.md, then STOP and tell me the name of the next stage. Do not start the next stage on your own.

CURRENT STATE
- Data and the pipeline pieces exist (parser, Tesseract OCR eng/hin/ben/pan/mal, clause splitter, Streamlit review app, labeling guideline docs\labeling_guideline.md, weak retrieval baseline Hit@5 30.7%).
- Test material: 3 human-verified documents (data\friend\04_annotated_data\gold_standard_extraction_v1.csv), 36 source-verified Q&A (qa_evaluation_candidates.csv), pilot LLM-assisted silver labels in data\processed\labels\llm_assisted\ (reduced scope: 10 documents, in progress), 16 Indian loan documents in data\raw\08_indian_bank_loans (see data\processed\indian_source_scope.csv), 60 annotation documents in data\processed_v1\annotation_sheets read from data\friend\01_loan_agreements\publicly_filed_contracts.zip (zipfile).

STAGE 1: PILOT LABELS (Claude Code only)
Label the 10 shortest annotation documents: 16 key fields; about 20 risk clauses each (category + severity Low/Medium/High/Critical + rationale; conservative); 4 Q&A each (1 unanswerable); 5 concise+detailed summaries; independent second pass on 3 docs with agreement scores; 20% spot-check sheet. Efficiency: one document at a time, targeted searches, never print more than 3,000 characters at once, save after each document.
DONE WHEN: files in data\processed\labels\llm_assisted\ exist, quote-verified rate >= 95%, agreement_report.md written.

STAGE 2: INGESTION AND GROUNDING CORE (Gemini/Antigravity)
a) PDF ingestion: text per page with markers [[PAGE n]]; per-page quality check; for bad pages compare Tesseract vs Gemini image/PDF input on my 240 Indian pages and 20 SROIE images (character error rate), keep the better per language; tables extracted as structured data.
b) Long-context first: if document + markers fits in the model context, answer from the whole text; else hybrid retrieval (BM25 + embeddings + reranker, clause chunks with heading/page, 10-20% overlap). Automatic and logged.
c) Answer contract (JSON): answer, quotes[{text,page,clause}], confidence, route. Script rejects quotes not found verbatim; retry once; else "not found in this document". A second LLM verifier pass checks the quotes support the answer.
d) Question router: document fact / explain-a-term / calculation / not-in-document / advice-or-legal (information only, recommend a professional).
DONE WHEN: 100% of returned quotes verified on a 50-question test; ingestion report for 20 PDFs; OCR CER table.

STAGE 3: FEATURES
Key-info extractor (16 fields incl. late-payment charges, prepayment/foreclosure, governing law), concise + detailed summaries (every number/date/amount in a summary must occur in the source), Q&A, and tested Python calculators (EMI, total interest, prepayment/foreclosure cost, penal charges; the LLM only extracts inputs, the UI shows formula and inputs). Evaluate: key-field precision/recall/F1 (3 verified docs and silver labels reported separately), Q&A correctness, abstention accuracy on unanswerable questions, citation-page accuracy, ROUGE/BERTScore vs silver summaries.
DONE WHEN: metrics table in docs\EVALUATION.md.

STAGE 4: RISK ANALYSIS AND INDIA RULES PACK
Clause split -> LLM rubric classification per clause (category, severity, rationale, exact quote, page, "what to ask the lender") in parallel with caching and temperature 0 -> deterministic formula: severity points Low=1, Medium=2, High=3, Critical=4; per category = mean of top 3 clause severities / 4; weights default 0.25, penalties and charges 0.20, financial terms 0.15, repayment 0.15, collateral 0.10, termination 0.10, covenants 0.05; score = 100 x weighted sum; levels Low <25, Moderate 25-50, High 50-75, Critical >=75 -> explanation with top 5 contributing clauses. Same input must give the same score. Report untuned results first, then tune weights on labeled data. India rules pack data\rules\india_rules.yaml: search for the CURRENT official RBI rules on key fact statements, prepayment/foreclosure charges, penal charges, interest reset; record source URL and retrieval date for each; mark unverified ones "unverified"; add "possible issue" flags to the risk report. UI text: information only, not legal or financial advice.
DONE WHEN: determinism test passes; risk macro-F1 (category and severity) reported untuned and tuned; rules pack has sources.

STAGE 5: TRANSLATION
Gemini translation of summaries, key fields and answers into the five languages; a script verifies numbers, dates and amounts are unchanged; compare with IndicTrans2 on a small sample.

STAGE 6: EVALUATION HARNESS
scripts\evaluate_all.py regression suite: golden Q&A, key-field gold, unanswerable questions, adversarial questions (prompt injection inside a document, asking for legal advice, asking about another document), Indian documents. Report quote-exists rate, key-field F1, Q&A correctness, abstention accuracy, citation accuracy, risk macro-F1, latency and cost per document. Write docs\EVALUATION.md with tables and limitations (US-centred data, small gold set, silver labels, judgment-based severity).

STAGE 7: APP
FastAPI backend (upload, status, key info, summaries, Q&A, risk, translation) and React + Vite frontend: upload with per-stage progress, tabs Summary / Key Info (value + quote + page) / Chat (citations jump to page) / Risk (gauge, top clauses, what to ask the lender) / Language selector, a "needs checking" badge when verification fails. Tests included.

STAGE 8: DEMO AND REPORT
Make 3 demo documents work flawlessly (one English SEC agreement, one Indian MITC, one scanned page). Draft the report: method, how labels were made (silver vs verified), results tables, limitations.