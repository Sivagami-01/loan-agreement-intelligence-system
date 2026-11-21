# Verification report

Verification performed against the current workspace inputs. No files in `data/raw`, `data/friend`, or `data/processed_v1` were changed. Human labels were not created.

## Check 1 - ZIP and source text

| Source | Exists | .txt files | Key-info doc_ids resolved |
|---|---:|---:|---:|
| `publicly_filed_contracts.zip` | No | N/A | 0/60 |
| `publicly_filed_contracts/` | Yes | 6194 | 26/60 |

ZIP Test-Path result: **False**. ZIP size: **N/A (file absent) bytes**. Unique doc_ids: **60**. Resolved in neither source: **34**.

**Source behavior:** the review app reads the unpacked file first, then falls back to the ZIP (including a ZIP member with an optional path prefix). `label_progress.py` reads label/source sheets and reports counts in both sources; it does not read document text. The ZIP is absent in this workspace, so 34 documents cannot currently be opened.

### Unresolved doc_ids

```text
000002/27566/0000945836-96-000035_3.txt
000002/27996/0000897101-01-500697_3.txt
000003/34563/0001104659-09-014658_2.txt
000003/38984/0000038984-97-000026_6.txt
000007/78749/0000950152-05-008319_2.txt
000008/89800/0000950123-10-066683_3.txt
000010/100885/0000889812-95-000124_3.txt
000035/350692/0000950134-04-001249_9.txt
000035/352915/0000893220-97-001362_3.txt
000035/354908/0001193125-06-206877_2.txt
000071/711039/0000711039-95-000025_2.txt
000074/749251/0000950123-04-013195_2.txt
000084/849547/0000950128-00-000940_5.txt
000085/858877/0001193125-07-185320_2.txt
000087/876645/0000891618-03-004250_9.txt
000087/879526/0000950137-00-003670_2.txt
000088/885725/0001104659-15-027462_2.txt
000088/885975/0000950134-98-000678_6.txt
000092/922521/0000950005-97-000330_3.txt
000092/925645/0001140361-14-041859_2.txt
000102/1020258/0000950144-98-001112_2.txt
000104/1041426/0000950144-99-003055_2.txt
000104/1042893/0000899243-01-501236_3.txt
000104/1042893/0000899243-97-001570_6.txt
000104/1046032/0000950115-00-000847_2.txt
000105/1058033/0001005477-99-003520_9.txt
000106/1063193/0001047469-99-002665_2.txt
000110/1109357/0000950137-06-011523_2.txt
000112/1122787/0001012870-03-003181_12.txt
000113/1135971/0001135971-09-000032_12.txt
000113/1135971/0001571049-16-010732_2.txt
000131/1317630/0000950123-11-015028_2.txt
000131/1317630/0001104659-13-091575_2.txt
000136/1365555/0001144204-12-044354_2.txt
```

## Check 2 - Indian-text threshold calibration

The existing script already computes expected-script share over alphabetic characters only. The letter-only rerun therefore has identical classifications. Latin letter share and non-alphanumeric ratio are included in [calibration_samples.md](./calibration_samples.md), with 10 reproducible examples per current class and page images.

| Rule | BAD threshold | SUSPICIOUS threshold | Symbol-ratio BAD threshold | Totals GOOD/SUSPICIOUS/BAD |
|---|---:|---:|---:|---:|
| Current | 0.12 | 0.40 | 0.45 | 92/116/32 |
| Proposed trial | 0.10 | 0.30 | 0.65 | 183/25/32 |

| Parsed file | Pages | Current G/S/B | Letter-only G/S/B | Proposed v2 G/S/B | Proposed pages to inspect |
|---|---:|---:|---:|---:|---|
| `03_dbs_mitc.json` | 2 | 2/0/0 | 2/0/0 | 2/0/0 | none |
| `04_dbs_mitc-ahl.json` | 4 | 4/0/0 | 4/0/0 | 4/0/0 | none |
| `06_clix_10.-CHFL_Policy-on-Interest-Rate-MITC-27May2025.json` | 11 | 11/0/0 | 11/0/0 | 11/0/0 | none |
| `09_muthoothomefin_MHIL-MITC.json` | 7 | 7/0/0 | 7/0/0 | 7/0/0 | none |
| `11_gichfindia_MOST-IMPORTANT-TERMS-1.json` | 5 | 5/0/0 | 5/0/0 | 5/0/0 | none |
| `12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam.json` | 42 | 22/14/6 | 22/14/6 | 35/1/6 | 1, 2, 3, 4, 5, 6, 9 |
| `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.json` | 29 | 1/23/5 | 1/23/5 | 19/5/5 | 1, 2, 3, 5, 6, 8, 12, 14, 21, 25 |
| `14_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Hindi.json` | 29 | 2/22/5 | 2/22/5 | 19/5/5 | 1, 2, 3, 5, 6, 8, 10, 12, 14, 22 |
| `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.json` | 31 | 1/24/6 | 1/24/6 | 15/10/6 | 1, 2, 3, 4, 7, 8, 9, 11, 12, 13, 14, 17, 18, 19, 21, 22 |
| `16_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Bengali_1_.json` | 31 | 14/14/3 | 14/14/3 | 26/2/3 | 1, 2, 3, 27, 28 |
| `17_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Bengali.json` | 33 | 9/19/5 | 9/19/5 | 26/2/5 | 1, 2, 3, 5, 7, 30, 31 |
| `personal_business_loan_agreement.json` | 16 | 14/0/2 | 14/0/2 | 14/0/2 | 12, 14 |

Proposed metric distribution and rationale are in [threshold_proposal.md](./threshold_proposal.md). The trial report is [indian_text_report_v2.md](./indian_text_report_v2.md); the prior `indian_text_report.md` was retained. Sample text and PNGs are in [calibration_samples.md](./calibration_samples.md) and `data/processed/review_images/`.

### Parser OCR flags cross-check

| Parsed file | Page | parse_docs.py flag | Proposed class |
|---|---:|---:|---|
| `12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam.json` | 32 | Yes | GOOD |
| `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.json` | 22 | Yes | GOOD |
| `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.json` | 23 | Yes | GOOD |
| `16_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Bengali_1_.json` | 23 | Yes | GOOD |
| `17_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Bengali.json` | 25 | Yes | GOOD |
| `personal_business_loan_agreement.json` | 12 | Yes | BAD |
| `personal_business_loan_agreement.json` | 14 | Yes | BAD |

Proposed SUSPICIOUS/BAD pages: **57**; parse_docs.py OCR flags: **7**; overlap: **2**; deduplicated union requiring OCR/review: **62**, versus **26 planned** (**36 more**). Five of seven parser-flagged Bajaj pages are GOOD under the proposed rule; the two flagged personal-business pages are BAD.

## Check 3 - Guideline quote verification

Every example under the severity headings is tested against raw unpacked text, or the ZIP if present. All eight final quotes matched character-for-character.

| Severity | doc_id | Quote length | Result | Raw line |
|---|---|---:|---|---:|
| Low | `000070/709283/0000709283-03-000001_5.txt` | 81 | EXACT_RAW | 1896 |
| Low | `000074/749872/0000950152-01-001872_2.txt` | 70 | EXACT_RAW | 1336 |
| Medium | `000002/21665/0000950130-02-005479_4.txt` | 77 | EXACT_RAW | 2712 |
| Medium | `000075/750004/0000922423-04-002111_8.txt` | 59 | EXACT_RAW | 5116 |
| High | `000080/801898/0000801898-05-000120_4.txt` | 162 | EXACT_RAW | 1639 |
| High | `000000/8063/0000950152-08-004105_2.txt` | 123 | EXACT_RAW | 2175 |
| Critical | `000000/8063/0000950152-08-004105_2.txt` | 164 | EXACT_RAW | 2249 |
| Critical | `000000/8063/0000950152-08-004105_2.txt` | 162 | EXACT_RAW | 2264 |

Final quote counts: **8 EXACT_RAW**, **0 WHITESPACE_ONLY**, **0 NOT_FOUND**.

## Check 4 - Indian PDF source details

SHA-256 and exact byte size are computed from each PDF. Lender/URL/date strings are document-text or PDF-metadata suggestions, not verified source URLs. Full extracted suggestions are in [sources_suggestions.txt](./sources_suggestions.txt).

| PDF | Size (bytes) | SHA-256 | Lender found in document | URL found in document | Date found in document/metadata |
|---|---:|---|---|---|---|
| `03_dbs_mitc.pdf` | 161204 | `893857f8b7e3e8257e283ed37d8d691a85fbd9c80760814d1bab5d700dc52225` | DBS Bank: DBS Bank | none | 09082022 (date-like text in PDF metadata title; format not inferred); 2024-12-23 (PDF metadata creationDate); 2024-12-23 (PDF metadata modDate) |
| `04_dbs_mitc-ahl.pdf` | 76931 | `87b5f84e96c17978546a25dfb767a82093c7c961da4da2404f0f9f92a42013e5` | DBS Bank: DBS Bank India | none | Apr24 (date-like text in PDF metadata title; format not inferred) |
| `06_clix_10.-CHFL_Policy-on-Interest-Rate-MITC-27May2025.pdf` | 262945 | `4795e509ef1d57a7e91f60f101a8c5f4713d2123f28f02a12a97f702627ec85d` | none | none | February 15, 2018; 2025-06-23 (PDF metadata creationDate); 2025-06-23 (PDF metadata modDate) |
| `09_muthoothomefin_MHIL-MITC.pdf` | 997535 | `50f40c7486d4c20a11fe3a3e9fd95fb82c6751a9bb3208508a68614d2641615c` | Muthoot Homefin: Muthoot Homefin (India) | www.muthoothomefin.com | 1st Jun'26 (date-like text in PDF metadata title; format not inferred); 2026-06-01 (PDF metadata creationDate); 2026-06-01 (PDF metadata modDate) |
| `11_gichfindia_MOST-IMPORTANT-TERMS-1.pdf` | 716006 | `b37899e4272307f573813eaacf856506ac274815da4b3e0f3782e07970d3855c` | GIC Housing Finance: GIC HOUSING FINANCE | none | 2019-04-23 (PDF metadata creationDate); 2019-04-23 (PDF metadata modDate) |
| `12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam.pdf` | 790069 | `11ed76337f990f997f57e4cd55fb9484a075e6782b322c5c0a371ec8c7b43c36` | Bajaj Housing Finance: BAJAJ HOUSING FINANCE LIMITED | none | 2026-06-03 (PDF metadata creationDate); 2026-06-03 (PDF metadata modDate) |
| `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.pdf` | 756188 | `71acab13de7cc245c09c6f6499ab386d7af3386d9219fc46577267d36ae1c776` | Bajaj Housing Finance: BAJAJ HOUSING FINANCE LIMITED | none | 2026-06-23 (PDF metadata creationDate); 2026-06-24 (PDF metadata modDate) |
| `14_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Hindi.pdf` | 738940 | `cfcdd47a9dd210b38c94d6482db4ccebf01768d70f8f2610d4ce5812ea2f6424` | Bajaj Housing Finance: BAJAJ HOUSING FINANCE LIMITED | none | 2026-02-09 (PDF metadata creationDate); 2026-02-11 (PDF metadata modDate) |
| `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.pdf` | 672991 | `adfb89b824074f2f948df7688014279b82c39a3105619ebb79bc4abe2841e0ea` | Bajaj Housing Finance: BAJAJ HOUSING FINANCE LIMITED | none | 2026-04-28 (PDF metadata creationDate); 2026-04-28 (PDF metadata modDate) |
| `16_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Bengali_1_.pdf` | 759173 | `0c8b4d408da548761e9ae4e73697d37b2d0ca7b246f43dae8c89874d8dc09336` | Bajaj Housing Finance: BAJAJ HOUSING FINANCE LIMITED | none | 2026-04-28 (PDF metadata creationDate); 2026-04-28 (PDF metadata modDate) |
| `17_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Bengali.pdf` | 906247 | `5c773ff70665dbbe76388cd841857f7754d978109eb388768a7077f189ae5ff5` | Bajaj Housing Finance: BAJAJ HOUSING FINANCE LIMITED | none | 2026-06-03 (PDF metadata creationDate); 2026-06-03 (PDF metadata modDate) |
| `personal_business_loan_agreement.pdf` | 1061057 | `280c3739ea6a97dadecd73d2c705bedf70d3b5b0932f45ba3aafb2ee1a5d6615` | none | none | 2015-02-24 (PDF metadata creationDate); 2015-02-25 (PDF metadata modDate) |

PDF count: **12**. Files with no URL text detected inside the PDF: **11**.

### Files with no URL found inside the document

- `03_dbs_mitc.pdf`
- `04_dbs_mitc-ahl.pdf`
- `06_clix_10.-CHFL_Policy-on-Interest-Rate-MITC-27May2025.pdf`
- `11_gichfindia_MOST-IMPORTANT-TERMS-1.pdf`
- `12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam.pdf`
- `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.pdf`
- `14_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Hindi.pdf`
- `15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.pdf`
- `16_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Bengali_1_.pdf`
- `17_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Bengali.pdf`
- `personal_business_loan_agreement.pdf`

**Source URL provenance:** the original download/source URLs are not recorded for any of the 12 PDFs. The Muthoot PDF contains `www.muthoothomefin.com`, but that is only a URL printed inside the document and does not establish where the PDF was downloaded from. Do not copy document-internal URLs into the provenance column without checking.

## Decisions / manual follow-up

1. Restore the absent ZIP or otherwise provide access to the **34 unresolved doc_id** files before labeling all 60 documents. The app can then use its ZIP fallback.
2. Compare the 30 sample excerpts with the PNGs in `review_images/`; decide by hand whether to accept the proposed 0.10/0.30/0.65 thresholds. No thresholds are adopted as gold truth.
3. Decide whether the deduplicated **62-page** OCR/review workload is acceptable versus the planned 26.
4. Find and record official source/download URLs manually for all 12 PDFs. Only one URL was detected inside a PDF; none of the download-source URLs are established.
5. Review the document-found lender/date suggestions in `sources_suggestions.txt`; do not treat PDF metadata dates as publication dates.

### Next command

Open the calibration examples before deciding the thresholds:

```powershell
notepad data\processed\calibration_samples.md
```
