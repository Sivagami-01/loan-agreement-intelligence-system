# OCR verification summary

- Parsed Indian files/pages checked: 12 / 240.
- Current-rule classes: GOOD=92, SUSPICIOUS=116, BAD=32.
- OCR candidates: 151 Indian pages; 32 are hard-rule BAD.
- Flagged parser pages cross-checked: 7; 7 are OCR candidates under the current rule.
- OCR results saved: 151 candidate Indian pages and 19 CUAD pages.
- OCR failures: 0.
- Planned set: 26 pages (7 parser-flagged Indian + 19 CUAD). Expanded candidate set: 170 pages (+144 versus plan).

## Indian per-file counts

| Parsed file | Pages | GOOD | SUSPICIOUS | BAD | OCR candidates |
|---|---:|---:|---:|---:|---:|
| `03_dbs_mitc.json` | 2 | 2 | 0 | 0 | 0 |
| `04_dbs_mitc-ahl.json` | 4 | 4 | 0 | 0 | 0 |
| `06_clix_10.-CHFL_Policy-on-Interest-Rate-MITC-27May2025.json` | 11 | 11 | 0 | 0 | 0 |
| `09_muthoothomefin_MHIL-MITC.json` | 7 | 7 | 0 | 0 | 0 |
| `11_gichfindia_MOST-IMPORTANT-TERMS-1.json` | 5 | 5 | 0 | 0 | 0 |
| `12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam.json` | 42 | 22 | 14 | 6 | 21 |
| `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.json` | 29 | 1 | 23 | 5 | 28 |
| `14_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Hindi.json` | 29 | 2 | 22 | 5 | 27 |
| `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.json` | 31 | 1 | 24 | 6 | 31 |
| `16_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Bengali_1_.json` | 31 | 14 | 14 | 3 | 17 |
| `17_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Bengali.json` | 33 | 9 | 19 | 5 | 25 |
| `personal_business_loan_agreement.json` | 16 | 14 | 0 | 2 | 2 |

## Parser-flag cross-check

| File | Page | Source class | OCR class | Candidate | Machine verdict |
|---|---:|---|---|---|---|
| `12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam.json` | 32 | GOOD | GOOD | True | EXTRACTION_AND_OCR_OVERLAP |
| `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.json` | 22 | SUSPICIOUS | SUSPICIOUS | True | OCR_REMAINS_SUSPICIOUS |
| `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.json` | 23 | GOOD | SUSPICIOUS | True | EXTRACTION_AND_OCR_OVERLAP |
| `16_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Bengali_1_.json` | 23 | SUSPICIOUS | SUSPICIOUS | True | OCR_REMAINS_SUSPICIOUS |
| `17_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Bengali.json` | 25 | GOOD | SUSPICIOUS | True | TEXTS_DIFFER; MANUAL_REVIEW |
| `personal_business_loan_agreement.json` | 12 | BAD | BAD | True | OCR_REMAINS_SUSPICIOUS |
| `personal_business_loan_agreement.json` | 14 | BAD | BAD | True | OCR_REMAINS_SUSPICIOUS |

Detailed page metrics: `data\processed\page_verification.csv`.
Candidate list: `data\processed\ocr_candidates.csv`.
Hard-rule BAD list: `data\processed\hard_bad_pages.csv`.
Parsed OCR output: `data\processed\parsed_ocr`.
Threshold recommendation: `data\processed\threshold_proposal_v2.md`.
