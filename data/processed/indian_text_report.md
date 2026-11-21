# Indian-language text verification

Expected-script share is measured among alphabetic characters; Latin/other is reported separately. Pages are heuristic triage, not a translation-quality judgment.

| Parsed file | Pages | Good | Suspicious | Bad | Pages to look at |
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

**Totals:** 92 good, 116 suspicious, 32 bad pages.
**Review images:** `data\processed\review_images`.
