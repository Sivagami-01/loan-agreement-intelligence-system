# Verification report v2

This report supersedes the earlier `verification_report.md`. The ZIP archive is now present; the earlier report's ZIP-absent result is stale. No human labels were created. The protected archive/annotation inputs were not changed; 15 new PDFs and parsed JSON files were added, and source records were appended in the designated Indian-loan folder. No existing PDF was overwritten or deleted.

## Check 1 — ZIP and source text

| Source | Exists | Size / `.txt` count | Key-info doc IDs resolved |
|---|---:|---:|---:|
| `data/friend/01_loan_agreements/publicly_filed_contracts.zip` | Yes | 1,363,946,017 bytes; 18,508 `.txt` entries | 60/60 |
| `data/friend/01_loan_agreements/publicly_filed_contracts/` | Yes | 6,194 `.txt` files | 0/60 needed as fallback |

`Test-Path` result for the ZIP: **True**. The 60 unique `doc_id` values resolve in the ZIP; none are unresolved.

**Actual source behavior:** `tools/review_app.py` and the labeling-context preparation use the ZIP as the preferred source and the unpacked folder as fallback. `scripts/label_progress.py` also checks both locations when reporting availability. Current progress reports all 60 documents present in the ZIP.

## Check 2 — Indian-text threshold calibration

The verifier's active thresholds are `bad_script_share=0.12`, `suspicious_script_share=0.40`, and `symbol_share=0.45`. Expected-script and Latin shares use alphabetic characters only. The hard corruption checks include empty/very short text, private-use characters, `(cid:...)`, replacement characters, and long symbol runs.

| Classification run | GOOD | SUSPICIOUS | BAD |
|---|---:|---:|---:|
| Active thresholds, original 12 parsed files | 92 | 116 | 32 |
| Letter-only share calculation | 92 | 116 | 32 |
| Historical trial thresholds `0.10 / 0.30 / 0.65` | 183 | 25 | 32 |

Excluding digits, whitespace, punctuation, and symbols does not change the active-rule classifications: that denominator was already letters-only. The trial thresholds reduce SUSPICIOUS pages but do not change the 32 BAD pages. OCR comparison showed substantial source/OCR differences on some bilingual pages, so the trial is not adopted; keep `0.12 / 0.40 / 0.45` active pending manual image review.

### Per-file counts

The letter-only counts equal the active counts. The trial column is the historical `0.10 / 0.30 / 0.65` run.

| Parsed file | Pages | Active G/S/B | Letter-only G/S/B | Trial G/S/B |
|---|---:|---:|---:|---:|
| `03_dbs_mitc.json` | 2 | 2/0/0 | 2/0/0 | 2/0/0 |
| `04_dbs_mitc-ahl.json` | 4 | 4/0/0 | 4/0/0 | 4/0/0 |
| `06_clix_10.-CHFL_Policy-on-Interest-Rate-MITC-27May2025.json` | 11 | 11/0/0 | 11/0/0 | 11/0/0 |
| `09_muthoothomefin_MHIL-MITC.json` | 7 | 7/0/0 | 7/0/0 | 7/0/0 |
| `11_gichfindia_MOST-IMPORTANT-TERMS-1.json` | 5 | 5/0/0 | 5/0/0 | 5/0/0 |
| `12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam.json` | 42 | 22/14/6 | 22/14/6 | 35/1/6 |
| `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.json` | 29 | 1/23/5 | 1/23/5 | 19/5/5 |
| `14_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Hindi.json` | 29 | 2/22/5 | 2/22/5 | 19/5/5 |
| `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.json` | 31 | 1/24/6 | 1/24/6 | 15/10/6 |
| `16_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Bengali_1_.json` | 31 | 14/14/3 | 14/14/3 | 26/2/3 |
| `17_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Bengali.json` | 33 | 9/19/5 | 9/19/5 | 26/2/5 |
| `personal_business_loan_agreement.json` | 16 | 14/0/2 | 14/0/2 | 14/0/2 |
| **Total** | **240** | **92/116/32** | **92/116/32** | **183/25/32** |

`calibration_samples.md` contains 10 fixed-seed samples per active class (seed 42), each with the requested character metrics, a redacted first-300-character excerpt, and an image path. GOOD-page samples were rendered under `review_images/good_samples/`. The proposed threshold report and page images are retained; samples are machine triage, not gold labels.

### Parser-flag cross-check and OCR workload

| Parser-flagged page | Trial status |
|---|---|
| Malayalam MITC, page 32 | GOOD |
| Hindi MITC, page 22 | GOOD |
| Punjabi MITC, page 23 | GOOD |
| Bengali MITC, page 23 | GOOD |
| Bengali MITC, page 25 | GOOD |
| `personal_business_loan_agreement`, page 12 | BAD |
| `personal_business_loan_agreement`, page 14 | BAD |

Under the trial rule, 57 pages are SUSPICIOUS/BAD; their union with the 7 parser-flagged Indian pages is **62 Indian pages**. Adding the 19 separately planned CUAD pages gives **81 total**, 55 above the 26-page plan. Under the retained active rule, the OCR pipeline produced **151 Indian candidates plus 19 CUAD pages = 170 pages**, 144 above plan. The 7 parser-flagged Indian pages were all candidates under the active rule. OCR was completed for all 151 Indian candidates and 19 CUAD pages with 0 processing failures.

Detailed files: `page_verification.csv`, `ocr_candidates.csv`, `hard_bad_pages.csv`, `parser_ocr_flag_crosscheck.csv`, `ocr_verification_summary.md`, and `threshold_proposal_v2.md`.

## Check 3 — Guideline quote verification

All eight severity examples were checked against raw text, using ZIP-first lookup. Every quote is an exact character-for-character match; no whitespace-only or missing quotes remain.

| Severity | doc_id | Length | Result | Raw line |
|---|---|---:|---|---:|
| Low | `000070/709283/0000709283-03-000001_5.txt` | 81 | EXACT_RAW | 1896 |
| Low | `000074/749872/0000950152-01-001872_2.txt` | 70 | EXACT_RAW | 1336 |
| Medium | `000002/21665/0000950130-02-005479_4.txt` | 77 | EXACT_RAW | 2712 |
| Medium | `000075/750004/0000922423-04-002111_8.txt` | 59 | EXACT_RAW | 5116 |
| High | `000080/801898/0000801898-05-000120_4.txt` | 162 | EXACT_RAW | 1639 |
| High | `000000/8063/0000950152-08-004105_2.txt` | 123 | EXACT_RAW | 2175 |
| Critical | `000000/8063/0000950152-08-004105_2.txt` | 164 | EXACT_RAW | 2249 |
| Critical | `000000/8063/0000950152-08-004105_2.txt` | 162 | EXACT_RAW | 2264 |

Final: **8 EXACT_RAW, 0 WHITESPACE_ONLY, 0 NOT_FOUND**. The detailed verification is in `guideline_quote_check.csv`.

## Check 4 — Original 12 Indian PDF details

The table gives current sizes and SHA-256 values. Lender, URL, and date suggestions are extracted only from PDF metadata and first-page text; they are not source-provenance claims.

| PDF | Size (bytes) | SHA-256 |
|---|---:|---|
| `03_dbs_mitc.pdf` | 161204 | `893857f8b7e3e8257e283ed37d8d691a85fbd9c80760814d1bab5d700dc52225` |
| `04_dbs_mitc-ahl.pdf` | 76931 | `87b5f84e96c17978546a25dfb767a82093c7c961da4da2404f0f9f92a42013e5` |
| `06_clix_10.-CHFL_Policy-on-Interest-Rate-MITC-27May2025.pdf` | 262945 | `4795e509ef1d57a7e91f60f101a8c5f4713d2123f28f02a12a97f702627ec85d` |
| `09_muthoothomefin_MHIL-MITC.pdf` | 997535 | `50f40c7486d4c20a11fe3a3e9fd95fb82c6751a9bb3208508a68614d2641615c` |
| `11_gichfindia_MOST-IMPORTANT-TERMS-1.pdf` | 716006 | `b37899e4272307f573813eaacf856506ac274815da4b3e0f3782e07970d3855c` |
| `12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam.pdf` | 790069 | `11ed76337f990f997f57e4cd55fb9484a075e6782b322c5c0a371ec8c7b43c36` |
| `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.pdf` | 756188 | `71acab13de7cc245c09c6f6499ab386d7af3386d9219fc46577267d36ae1c776` |
| `14_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Hindi.pdf` | 738940 | `cfcdd47a9dd210b38c94d6482db4ccebf01768d70f8f2610d4ce5812ea2f6424` |
| `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.pdf` | 672991 | `adfb89b824074f2f948df7688014279b82c39a3105619ebb79bc4abe2841e0ea` |
| `16_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Bengali_1_.pdf` | 759173 | `0c8b4d408da548761e9ae4e73697d37b2d0ca7b246f43dae8c89874d8dc09336` |
| `17_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Bengali.pdf` | 906247 | `5c773ff70665dbbe76388cd841857f7754d978109eb388768a7077f189ae5ff5` |
| `personal_business_loan_agreement.pdf` | 1061057 | `280c3739ea6a97dadecd73d2c705bedf70d3b5b0932f45ba3aafb2ee1a5d6615` |

No original download/source URL is known for any of the 12. Eleven have no URL printed inside the PDF; Muthoot contains `www.muthoothomefin.com`, which is not proof of download provenance. `sources_suggestions.txt` has all detected lender/date/URL suggestions and hashes. Verify these manually before treating them as metadata.

## Public-source collection status

- The folder contains **27 PDFs and 27 parsed JSON files**: 12 original plus 15 new files.
- The scope manifest classifies **16/27 as loan-corpus eligible**: 12 original and 4 newly qualified loan-product MITCs (one Tata Capital and three Piramal Finance).
- The other 11 new PDFs remain in raw storage because existing raw files were not to be deleted: 10 initial broad-crawl documents outside the requested formats and 1 credit-card MITC. They are excluded from the loan corpus.
- The user's minimum of 5 new qualifying documents was **not met** (4 qualify); 6 more would be needed to reach the target of 10.
- The expanded crawl found no more qualifying documents. No candidate loan-PDF download failed; the following discovery requests failed: RBI `https://www.rbi.org.in/robots.txt` (418); Tata Capital `https://www.tatacapital.com/sitemap-blog.xml` (404) and `https://www.tatacapital.com/blog/sitemap_index.xml` (502); PNB `https://pnb.bank.in/robots.txt` (404); Union Bank `https://www.unionbankofindia.co.in/robots.txt`, `https://www.unionbankofindia.co.in/sitemap.xml`, and `https://www.unionbankofindia.co.in/` (timeouts); IDFC FIRST `https://www.idfcfirst.bank.in/content/idfcfirstbank/enpersonal-banking/loans/personal-loan/quick-loan` (404).
- A Bajaj Housing Finance digital sanction-letter sample was excluded rather than downloaded because inspection indicated sample application/identity data. No synthetic document was added.
- `official_crawl.log`, `official_pdf_candidates.csv`, and `indian_source_scope.csv` contain crawl details, candidate outcomes, and the per-file scope decision. `sources.txt` records the newly downloaded files; original source URLs remain unknown.
- The manual URL downloader now appends progress and per-URL failures to `extra_download.log` while continuing to the next URL.

## Labeling, parser, and retrieval status

- Current human labels: **0/960 key fields**, **0/1,500 risk clauses**, **0/120 Q&A rows**. No gold labels were invented or populated.
- The app uses ZIP-first source resolution with unpacked fallback. The ZIP resolves all 60 documents.
- The review app passed a local HTTP health check; five OCR language smoke tests passed. The interactive labeling workflow still needs a human to use it.
- Clause preparation produced 15,276 machine-generated chunks; source-offset integrity validation had zero failures.
- Local retrieval-only baseline completed on 1,500 risk-clause passages and 75 evidence-matched machine-proxy queries: Hit@1 10/75 (13.3%), Hit@3 18/75 (24.0%), Hit@5 23/75 (30.7%), MRR@5 0.1902. These are not human-validated performance metrics, and no Q&A benchmark was run.
- The first full-corpus retrieval attempt was stopped as too slow. The smaller retry succeeded; both attempts are noted in `retrieval_eval_attempts.log`.

## Manual decisions and next commands

1. Inspect the 30 sample pages and decide whether to retain the active OCR thresholds. The current recommendation is to retain `0.12 / 0.40 / 0.45`; do not treat OCR or trial classifications as truth.
2. Find at least one more qualifying official loan PDF to meet the minimum of five (six more to reach ten). Confirm URLs manually; do not use the 11 excluded files as loan-corpus documents.
3. Check source metadata suggestions by hand. Download URLs for all 12 original PDFs remain unknown.
4. Label all key fields, risk clauses, and Q&A rows yourself; the relevant decision columns remain empty.

From `C:\finalYear`, run:

```powershell
python -m streamlit run tools\review_app.py
```

In another terminal, refresh label counts:

```powershell
python scripts\label_progress.py
```

For the local retrieval-only baseline:

```powershell
python scripts\evaluate_retrieval.py
```
