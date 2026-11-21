# Indian-language text verification

Expected-script share is measured among alphabetic characters; Latin/other is reported separately. Pages are heuristic triage, not a translation-quality judgment.
Thresholds: bad expected-script share < 0.10; suspicious < 0.30; symbol ratio > 0.65.

| Parsed file | Pages | Good | Suspicious | Bad | Pages to look at |
|---|---:|---:|---:|---:|---|
| `03_dbs_mitc.json` | 2 | 2 | 0 | 0 | — |
| `04_dbs_mitc-ahl.json` | 4 | 4 | 0 | 0 | — |
| `06_clix_10.-CHFL_Policy-on-Interest-Rate-MITC-27May2025.json` | 11 | 11 | 0 | 0 | — |
| `09_muthoothomefin_MHIL-MITC.json` | 7 | 7 | 0 | 0 | — |
| `11_gichfindia_MOST-IMPORTANT-TERMS-1.json` | 5 | 5 | 0 | 0 | — |
| `12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam.json` | 42 | 35 | 1 | 6 | 1, 2, 3, 4, 5, 6, 9 |
| `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.json` | 29 | 19 | 5 | 5 | 1, 2, 3, 5, 6, 8, 12, 14, 21, 25 |
| `14_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Hindi.json` | 29 | 19 | 5 | 5 | 1, 2, 3, 5, 6, 8, 10, 12, 14, 22 |
| `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.json` | 31 | 15 | 10 | 6 | 1, 2, 3, 4, 7, 8, 9, 11, 12, 13, 14, 17, 18, 19, 21, 22 |
| `16_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Bengali_1_.json` | 31 | 26 | 2 | 3 | 1, 2, 3, 27, 28 |
| `17_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Bengali.json` | 33 | 26 | 2 | 5 | 1, 2, 3, 5, 7, 30, 31 |
| `personal_business_loan_agreement.json` | 16 | 14 | 0 | 2 | 12, 14 |

**Totals:** 183 good, 25 suspicious, 32 bad pages.
**Review images:** `data\processed\review_images`.
