# Input data schema

Schema inventory of the supplied 01, 02 (contextual CUAD), and 04 data folders. Examples are clipped to at most 100 characters. Row counts exclude CSV headers.

## File type inventory

- CSV and CSV-formatted backup files: 34
- JSON files: 3
- JSONL files: 1
- ZIP archives: 1
- `.txt` files in 01_loan_agreements: 6194
- `.txt` files in 02_cuad: 0
- `.txt` files in 04_annotated_data: 0

## CSV and backup files
- **Large classification table:** `loan_agreement_candidate_inventory.csv` (18,508 rows; `review_status` carries document classification).

### `02_cuad-20261110T071043Z-1-001\02_cuad\master_clauses.csv`
- Data rows: 510; columns: 83; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `Filename` | `CybergyHoldingsInc_20140520_10-Q_EX-10.27_8605784_EX-10.27_Affiliate Agreement.pdf` |
| `Document Name` | `['MARKETING AFFILIATE AGREEMENT']` |
| `Document Name-Answer` | `MARKETING AFFILIATE AGREEMENT` |
| `Parties` | `['BIRCH FIRST GLOBAL INVESTMENTS INC.', 'MA', 'Marketing Affiliate', 'MOUNT KNOWLEDGE HOLDINGS IN...` |
| `Parties-Answer` | `Birch First Global Investments Inc. ("Company"); Mount Kowledge Holdings Inc. ("Marketing Affilia...` |
| `Agreement Date` | `['8th day of May 2014', 'May 8, 2014']` |
| `Agreement Date-Answer` | `5/8/14` |
| `Effective Date` | `['This agreement shall begin upon the date of its execution by MA and acceptance in writing by Co...` |
| `Effective Date-Answer` | `7/11/06` |
| `Expiration Date` | `['This agreement shall begin upon the date of its execution by MA and acceptance in writing by Co...` |
| `Expiration Date-Answer` | `12/31/14` |
| `Renewal Term` | `['This agreement shall begin upon the date of its execution by MA and acceptance in writing by Co...` |
| `Renewal Term-Answer` | `successive 1 year` |
| `Notice Period To Terminate Renewal` | `['This Agreement may be terminated by either party at the expiration of its term or any renewal t...` |
| `Notice Period To Terminate Renewal- Answer` | `30 days` |
| `Governing Law` | `['This Agreement is accepted by Company in the State of Nevada and shall be governed by and const...` |
| `Governing Law-Answer` | `Nevada` |
| `Most Favored Nation` | `[]` |
| `Most Favored Nation-Answer` | `No` |
| `Competitive Restriction Exception` | `[]` |
| `Competitive Restriction Exception-Answer` | `No` |
| `Non-Compete` | `[]` |
| `Non-Compete-Answer` | `No` |
| `Exclusivity` | `[]` |
| `Exclusivity-Answer` | `No` |
| `No-Solicit Of Customers` | `[]` |
| `No-Solicit Of Customers-Answer` | `No` |
| `No-Solicit Of Employees` | `[]` |
| `No-Solicit Of Employees-Answer` | `No` |
| `Non-Disparagement` | `['Company shall not specify the business practices of MA, nor regulate the manner in which MA sha...` |
| `Non-Disparagement-Answer` | `Yes` |
| `Termination For Convenience` | `[]` |
| `Termination For Convenience-Answer` | `No` |
| `Rofr/Rofo/Rofn` | `[]` |
| `Rofr/Rofo/Rofn-Answer` | `No` |
| `Change Of Control` | `[]` |
| `Change Of Control-Answer` | `No` |
| `Anti-Assignment` | `['MA may not assign, sell, lease or otherwise transfer in whole or in party any of the rights gra...` |
| `Anti-Assignment-Answer` | `Yes` |
| `Revenue/Profit Sharing` | `[]` |
| `Revenue/Profit Sharing-Answer` | `No` |
| `Price Restrictions` | `[]` |
| `Price Restrictions-Answer` | `No` |
| `Minimum Commitment` | `['INITIAL ORDER COMMITMENT - MA commits to purchase a minimum of 100 Units in aggregate within th...` |
| `Minimum Commitment-Answer` | `Yes` |
| `Volume Restriction` | `[]` |
| `Volume Restriction-Answer` | `No` |
| `Ip Ownership Assignment` | `[]` |
| `Ip Ownership Assignment-Answer` | `No` |
| `Joint Ip Ownership` | `[]` |
| `Joint Ip Ownership-Answer` | `No` |
| `License Grant` | `['Company hereby grants MA, during the term of this Agreement, the right to use Company and/or Co...` |
| `License Grant-Answer` | `Yes` |
| `Non-Transferable License` | `[]` |
| `Non-Transferable License-Answer` | `No` |
| `Affiliate License-Licensor` | `[]` |
| `Affiliate License-Licensor-Answer` | `No` |
| `Affiliate License-Licensee` | `[]` |
| `Affiliate License-Licensee-Answer` | `No` |
| `Unlimited/All-You-Can-Eat-License` | `[]` |
| `Unlimited/All-You-Can-Eat-License-Answer` | `No` |
| `Irrevocable Or Perpetual License` | `[]` |
| `Irrevocable Or Perpetual License-Answer` | `No` |
| `Source Code Escrow` | `[]` |
| `Source Code Escrow-Answer` | `No` |
| `Post-Termination Services` | `[]` |
| `Post-Termination Services-Answer` | `No` |
| `Audit Rights` | `['MA shall keep accurate records of the sales of the Technology and Maintenance, including Client...` |
| `Audit Rights-Answer` | `Yes` |
| `Uncapped Liability` | `[]` |
| `Uncapped Liability-Answer` | `No` |
| `Cap On Liability` | `['The foregoing states the entire liability of Company with respect to infringement of intellectu...` |
| `Cap On Liability-Answer` | `Yes` |
| `Liquidated Damages` | `[]` |
| `Liquidated Damages-Answer` | `No` |
| `Warranty Duration` | `["COMPANY'S SOLE AND EXCLUSIVE LIABILITY FOR THE WARRANTY PROVIDED IN SUBPARAGRAH (A) HEREOF SHAL...` |
| `Warranty Duration-Answer` | `Yes` |
| `Insurance` | `[]` |
| `Insurance-Answer` | `No` |
| `Covenant Not To Sue` | `[]` |
| `Covenant Not To Sue-Answer` | `No` |
| `Third Party Beneficiary` | `[]` |
| `Third Party Beneficiary-Answer` | `No` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000001_14693_0000950144-06-011821_2_txt.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000001/14693/0000950144-06-011821_2.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `CREDIT AGREEMENT` |
| `evidence_excerpt` | `CREDIT AGREEMENT` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000001_17206_0000017206-96-000015_2_txt.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000001/17206/0000017206-96-000015_2.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `CREDIT AGREEMENT` |
| `evidence_excerpt` | `CREDIT AGREEMENT` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000001_18498_0000950144-04-003716_4_txt.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000001/18498/0000950144-04-003716_4.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `CREDIT AGREEMENT` |
| `evidence_excerpt` | `CREDIT AGREEMENT` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000003_37472_0000897101-10-000801_2_txt.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000003/37472/0000897101-10-000801_2.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `CREDIT AGREEMENT` |
| `evidence_excerpt` | `CREDIT AGREEMENT` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000004_43196_0000912057-96-022806_2_txt.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000004/43196/0000912057-96-022806_2.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `LOAN AGREEMENT` |
| `evidence_excerpt` | `LOAN AGREEMENT` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000004_45919_0001193125-11-224475_2_txt.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000004/45919/0001193125-11-224475_2.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `TERM LOAN AGREEMENT` |
| `evidence_excerpt` | `TERM LOAN AGREEMENT` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000005_54681_0001045969-01-500886_3_txt.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000005/54681/0001045969-01-500886_3.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `CREDIT AGREEMENT` |
| `evidence_excerpt` | `CREDIT AGREEMENT` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000005_54681_0001045969-01-500886_3_txt_2.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000005/54681/0001045969-01-500886_3.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `CREDIT AGREEMENT` |
| `evidence_excerpt` | `CREDIT AGREEMENT` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000007_72331_0001564590-15-004835_2_txt.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000007/72331/0001564590-15-004835_2.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `TERM LOAN FACILITY` |
| `evidence_excerpt` | `TERM LOAN FACILITY` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000007_74303_0000950130-02-000134_3_txt.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000007/74303/0000950130-02-000134_3.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `CREDIT AGREEMENT` |
| `evidence_excerpt` | `CREDIT AGREEMENT` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000007_74303_0000950130-02-000134_3_txt_2.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000007/74303/0000950130-02-000134_3.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `CREDIT AGREEMENT` |
| `evidence_excerpt` | `CREDIT AGREEMENT` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000007_77159_0001144204-09-061109_2_txt.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000007/77159/0001144204-09-061109_2.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `CREDIT AGREEMENT` |
| `evidence_excerpt` | `CREDIT AGREEMENT` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000007_77159_0001144204-09-061109_2_txt_2.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000007/77159/0001144204-09-061109_2.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `CREDIT AGREEMENT` |
| `evidence_excerpt` | `CREDIT AGREEMENT` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000031_313478_0000899243-01-000763_3_txt.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000031/313478/0000899243-01-000763_3.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `CREDIT AGREEMENT` |
| `evidence_excerpt` | `CREDIT AGREEMENT` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000071_717605_0001104659-05-009169_2_txt.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000071/717605/0001104659-05-009169_2.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `CREDIT AGREEMENT` |
| `evidence_excerpt` | `CREDIT AGREEMENT` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000078_780118_0000780118-97-000007_3_txt.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000078/780118/0000780118-97-000007_3.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `RESTATED REVOLVING CREDIT AGREEMENT` |
| `evidence_excerpt` | `RESTATED REVOLVING CREDIT AGREEMENT` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000078_786110_0000891618-99-001792_2_txt.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000078/786110/0000891618-99-001792_2.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `2.1. TERM LOAN FACILITY.............................................................7` |
| `evidence_excerpt` | `2.1.  TERM LOAN FACILITY.............................................................7` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000087_871763_0001193125-04-171228_2_txt.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000087/871763/0001193125-04-171228_2.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `FIVE YEAR CREDIT AGREEMENT` |
| `evidence_excerpt` | `FIVE YEAR CREDIT AGREEMENT` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000091_912242_0001104659-11-026841_2_txt.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000091/912242/0001104659-11-026841_2.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `$1,500,000,000 REVOLVING LOAN FACILITY` |
| `evidence_excerpt` | `$1,500,000,000 REVOLVING LOAN FACILITY` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\batch_review_000091_917491_0000897069-03-001407_5_txt.csv`
- Data rows: 13; columns: 8; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000091/917491/0000897069-03-001407_5.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `LOAN AGREEMENT` |
| `evidence_excerpt` | `LOAN AGREEMENT` |
| `section_reference` | `Cover / agreement opening` |
| `evidence_assessment` | `Relevant source text was located. This is only a text-presence finding; human review must confirm...` |
| `review_status` | `evidence_found` |
| `reviewer_notes` | `unknown means no reliable title was identified in the inspected opening; it is not evidence that ...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\caterpillar_first_review.csv`
- Data rows: 13; columns: 7; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000001/18230/0001104659-11-052126_5.txt` |
| `field_name` | `document_title` |
| `candidate_value` | `CREDIT AGREEMENT` |
| `evidence_excerpt` | `CREDIT AGREEMENT` |
| `section_reference` | `Cover page` |
| `review_status` | `supported` |
| `reviewer_notes` | `User confirmed the title against the cover wording during interactive manual review.` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\clause_annotations_template.csv`
- Data rows: 0; columns: 9; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `` |
| `page_number` | `` |
| `clause_text` | `` |
| `clause_type` | `` |
| `risk_category` | `` |
| `severity` | `` |
| `evidence` | `` |
| `reviewer_notes` | `` |
| `review_status` | `` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\contract_review_queue.csv`
- Data rows: 100; columns: 9; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000000/4187/0000892303-01-500007_3.txt` |
| `source_path` | `datasets/01_loan_agreements/publicly_filed_contracts/000000/4187/0000892303-01-500007_3.txt` |
| `candidate_keywords` | `loan agreement; borrower; lender; principal; repayment; collateral; security` |
| `current_candidate_status` | `candidate_unverified` |
| `manual_verification` | `not_verified` |
| `review_status` | `needs_review` |
| `company` | `INDUSTRIAL SERVICES AMER INC` |
| `file_status` | `available` |
| `sample_excerpt` | `LOAN AGREEMENT Principal $3,000,000.00 Loan Date Maturity 06-30-2002 Loan No. 81145 Call 04A0 Col...` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\gold_standard_extraction_v1.csv`
- Data rows: 27; columns: 35; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000001/14693/0000950144-06-011821_2.txt` |
| `source_path` | `000001/14693/0000950144-06-011821_2.txt` |
| `field` | `document_title` |
| `gold_value` | `BRIDGE CREDIT AGREEMENT` |
| `gold_status` | `KNOWN` |
| `evidence_quote` | `BRIDGE CREDIT AGREEMENT` |
| `evidence_location` | `Title block, source line 9` |
| `reviewer_identity` | `Lead (personal name not recorded)` |
| `decision` | `ACCEPTED` |
| `rationale` | `Lead verification and final adjudication: confirmed the proposed annotation as submitted after re...` |
| `review_date` | `2026-11-04` |
| `approval_status` | `APPROVED` |
| `source_sha256` | `1b51ef30e988ab8ae173fa3e6df51e72f71e7f93037e8b0cedf9cf685f8043b8` |
| `guide_version` | `1.0.0` |
| `agreement_name` | `Brown-Forman` |
| `approved_annotation_value` | `BRIDGE CREDIT AGREEMENT` |
| `original_proposed_value` | `BRIDGE CREDIT AGREEMENT` |
| `existing_pilot_value` | `BRIDGE CREDIT AGREEMENT` |
| `existing_machine_candidate` | `BRIDGE CREDIT AGREEMENT` |
| `applicable_policy_rule` | `Field definition; R5, R6, R7` |
| `decision_explanation` | `Retain the instrument title exactly as printed; do not substitute the acquisition or permanent-fa...` |
| `missing_information_or_ambiguity` | `Complete lender roster, lender commitments, and subsequent assignments are unavailable in this te...` |
| `all_evidence_quotes_json` | `["BRIDGE CREDIT AGREEMENT"]` |
| `approval_evidence_reference` | `Lead_Final_Approval_Record.md, "Latest written Lead approval" section` |
| `lead_approval_date` | `2026-11-04` |
| `verification_reviewer_designation` | `Lead` |
| `verification_reviewer_identity` | `NOT_RECORDED` |
| `verification_review_date` | `2026-11-04` |
| `adjudication_reviewer_designation` | `Lead` |
| `adjudication_reviewer_identity` | `NOT_RECORDED` |
| `final_adjudication_date` | `2026-11-04` |
| `lead_review_status` | `APPROVED` |
| `final_approval_status` | `APPROVED` |
| `gold_standard_status` | `GOLD_STANDARD_APPROVED` |
| `initial_annotation_status` | `STUDENT_DECISION_ACCEPTED_PENDING_LEAD_REVIEW` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\key_fields_template.csv`
- Data rows: 100; columns: 13; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000000/4187/0000892303-01-500007_3.txt` |
| `lender` | `` |
| `borrower` | `` |
| `principal_amount` | `` |
| `currency` | `` |
| `interest_rate` | `` |
| `loan_tenure` | `` |
| `repayment_frequency` | `` |
| `fees` | `` |
| `collateral` | `` |
| `agreement_date` | `` |
| `maturity_date` | `` |
| `review_status` | `needs_review` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\loan_agreement_batch_2_review.csv`
- Data rows: 72; columns: 27; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000082/827156/0000950153-01-500650_2.txt` |
| `source_path` | `datasets/01_loan_agreements/publicly_filed_contracts/000082/827156/0000950153-01-500650_2.txt` |
| `source_sha256` | `7100d49193be4fc4a309d03d3c266447b5910bba25585056c1d4ecc8b9e1522f` |
| `document_title` | `LOAN AGREEMENT` |
| `agreement_type` | `Commercial bank line-of-credit loan agreement` |
| `field` | `document_title` |
| `proposed_value` | `LOAN AGREEMENT` |
| `evidence_status` | `SOURCE_SUPPORTED` |
| `supporting_quote` | `LOAN AGREEMENT                     EXHIBIT 10-0` |
| `source_location` | `Cover/title block, line 6` |
| `applicable_policy_rule` | `R5, R6, R7` |
| `missing_information_or_ambiguity` | `No title ambiguity.` |
| `reason_for_proposed_value` | `The cover identifies the instrument.` |
| `proposal_status` | `PROPOSED_NEEDS_HUMAN_REVIEW` |
| `further_investigation` | `NO` |
| `reviewer_decision` | `ACCEPTED AS PROPOSED` |
| `reviewer_correction` | `` |
| `reviewer_rationale` | `Accepted as proposed; no separate rationale provided by reviewer.` |
| `review_date` | `2026-11-04` |
| `second_reviewer_identity` | `` |
| `second_reviewer_decision` | `` |
| `second_reviewer_date` | `` |
| `independent_verification` | `` |
| `supervisor_adjudicator` | `` |
| `adjudication_decision` | `` |
| `final_approval_status` | `` |
| `gold_standard_status` | `` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\loan_agreement_batch_2_review.csv.pre_000127_acceptance_20261106.bak`
- Data rows: 72; columns: 27; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000082/827156/0000950153-01-500650_2.txt` |
| `source_path` | `datasets/01_loan_agreements/publicly_filed_contracts/000082/827156/0000950153-01-500650_2.txt` |
| `source_sha256` | `7100d49193be4fc4a309d03d3c266447b5910bba25585056c1d4ecc8b9e1522f` |
| `document_title` | `LOAN AGREEMENT` |
| `agreement_type` | `Commercial bank line-of-credit loan agreement` |
| `field` | `document_title` |
| `proposed_value` | `LOAN AGREEMENT` |
| `evidence_status` | `SOURCE_SUPPORTED` |
| `supporting_quote` | `LOAN AGREEMENT                     EXHIBIT 10-0` |
| `source_location` | `Cover/title block, line 6` |
| `applicable_policy_rule` | `R5, R6, R7` |
| `missing_information_or_ambiguity` | `No title ambiguity.` |
| `reason_for_proposed_value` | `The cover identifies the instrument.` |
| `proposal_status` | `PROPOSED_NEEDS_HUMAN_REVIEW` |
| `further_investigation` | `NO` |
| `reviewer_decision` | `ACCEPTED AS PROPOSED` |
| `reviewer_correction` | `` |
| `reviewer_rationale` | `Accepted as proposed; no separate rationale provided by reviewer.` |
| `review_date` | `2026-11-04` |
| `second_reviewer_identity` | `` |
| `second_reviewer_decision` | `` |
| `second_reviewer_date` | `` |
| `independent_verification` | `` |
| `supervisor_adjudicator` | `` |
| `adjudication_decision` | `` |
| `final_approval_status` | `` |
| `gold_standard_status` | `` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\loan_agreement_candidate_inventory.csv`
- Data rows: 18508; columns: 23; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000000/1750/0000895813-98-000136_4.txt` |
| `source_path` | `datasets/01_loan_agreements/publicly_filed_contracts/000000/1750/0000895813-98-000136_4.txt` |
| `source_sha256` | `643aa0b10b55c3d7f5c981cf89326e6fd7bdac732c568e96b01d162ca01801fb` |
| `preliminary_agreement_type` | `LOAN_OR_CREDIT_AGREEMENT` |
| `candidate_classification` | `LIKELY_LOAN_FINANCING` |
| `evidence_supporting_classification` | `CREDIT AGREEMENT | ================================================= CREDIT AGREEMENT BETWEEN AAR...` |
| `document_title` | `CREDIT AGREEMENT` |
| `duplicate_group` | `sha256:d543422c3d1c1df590bca78130b9e868115539e7892c49262157e3e0f681ec6b` |
| `review_status` | `LIKELY_LOAN_AGREEMENT` |
| `reason_for_inclusion_or_exclusion` | `Opening title identifies a loan/credit financing instrument; this is a preliminary screen, not hu...` |
| `company` | `AAR CORP` |
| `file_size_bytes` | `164497` |
| `source_chars_scanned` | `164497` |
| `source_scan_truncated` | `false` |
| `encoding_replacement_characters` | `0` |
| `control_manifest_status` | `IN_BOTH_CONTROL_MANIFESTS` |
| `existing_candidate_record` | `no` |
| `existing_review_queue_record` | `no` |
| `pilot_gold_record` | `no` |
| `prior_candidate_status` | `candidate_unverified` |
| `prior_review_status` | `needs_review` |
| `candidate_reclassification` | `candidate_unverified -> LIKELY_LOAN_AGREEMENT` |
| `canonical_duplicate_document_id` | `000000/3146/0001193125-10-242410_2.txt` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\manual_gold_review_initial_3.csv`
- Data rows: 27; columns: 13; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000001/14693/0000950144-06-011821_2.txt` |
| `source_path` | `datasets/01_loan_agreements/publicly_filed_contracts/000001/14693/0000950144-06-011821_2.txt` |
| `field` | `document_title` |
| `machine_candidate_value` | `BRIDGE CREDIT AGREEMENT` |
| `extractor_status` | `candidate` |
| `report_evaluation_outcome` | `supported` |
| `machine_evidence` | `BRIDGE CREDIT AGREEMENT` |
| `annotation_queue_status` | `needs_review` |
| `human_verified_value` | `BRIDGE CREDIT AGREEMENT` |
| `human_evidence_quote` | `BRIDGE CREDIT AGREEMENT` |
| `human_evidence_location` | `Cover / agreement opening, title block` |
| `human_reviewer_notes` | `Decision: supported. The exact cover title matches the machine candidate.` |
| `reviewer_status` | `needs_review` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\manual_gold_review_initial_3.pre_encoding_repair_20261013_162352.bak`
- Data rows: 27; columns: 13; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000001/14693/0000950144-06-011821_2.txt` |
| `source_path` | `datasets/01_loan_agreements/publicly_filed_contracts/000001/14693/0000950144-06-011821_2.txt` |
| `field` | `document_title` |
| `machine_candidate_value` | `BRIDGE CREDIT AGREEMENT` |
| `extractor_status` | `candidate` |
| `report_evaluation_outcome` | `supported` |
| `machine_evidence` | `BRIDGE CREDIT AGREEMENT` |
| `annotation_queue_status` | `needs_review` |
| `human_verified_value` | `BRIDGE CREDIT AGREEMENT` |
| `human_evidence_quote` | `BRIDGE CREDIT AGREEMENT` |
| `human_evidence_location` | `Cover / agreement opening, title block` |
| `human_reviewer_notes` | `Decision: supported. The exact cover title matches the machine candidate.` |
| `reviewer_status` | `needs_review` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\manual_gold_review_initial_3.pre_encoding_repair_20261013_222538.bak`
- Data rows: 27; columns: 13; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `000001/14693/0000950144-06-011821_2.txt` |
| `source_path` | `datasets/01_loan_agreements/publicly_filed_contracts/000001/14693/0000950144-06-011821_2.txt` |
| `field` | `document_title` |
| `machine_candidate_value` | `BRIDGE CREDIT AGREEMENT` |
| `extractor_status` | `candidate` |
| `report_evaluation_outcome` | `supported` |
| `machine_evidence` | `BRIDGE CREDIT AGREEMENT` |
| `annotation_queue_status` | `needs_review` |
| `human_verified_value` | `BRIDGE CREDIT AGREEMENT` |
| `human_evidence_quote` | `BRIDGE CREDIT AGREEMENT` |
| `human_evidence_location` | `Cover / agreement opening, title block` |
| `human_reviewer_notes` | `Decision: supported. The exact cover title matches the machine candidate.` |
| `reviewer_status` | `needs_review` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\qa_evaluation_candidates.csv`
- Data rows: 36; columns: 12; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `case_id` | `AAR-01` |
| `document_id` | `AAR` |
| `source_file` | `datasets/01_loan_agreements/publicly_filed_contracts/000000/1750/0000895813-98-000136_4.txt` |
| `topic` | `loan_amount` |
| `question` | `What is the maximum amount of the revolving credit facility?` |
| `expected_status` | `answerable` |
| `expected_answer` | `The agreement describes a revolving line of credit in an aggregate amount not to exceed $10,000,000.` |
| `supporting_clause_exact` | `to the Borrower a revolving line of credit for loans in an aggregate amount not to exceed $10,000...` |
| `section_reference` | `Recitals` |
| `page_number` | `1` |
| `review_status` | `source_verified` |
| `review_note` | `Quotation transcribed from the agreement recital.` |

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\qa_reference_template.csv`
- Data rows: 0; columns: 6; detected text encoding: utf-8-sig
| Column | Example (max 100 chars) |
|---|---|
| `document_id` | `` |
| `question` | `` |
| `reference_answer` | `` |
| `supporting_clause` | `` |
| `page_number` | `` |
| `review_status` | `` |

## JSON files

### `01_loan_agreements-20261110T071036Z-1-001\01_loan_agreements\breakpoint_file.json`
- Top-level object with 14526 keys; example top-level key: `000031/313616/0000313616-98-000010_5.txt`
| Key / nested field | Type(s) | Example (max 100 chars) |
|---|---|---|
| `<key>` | `NoneType, dict` | `{"covenant_section":{"1":{"breakpoints":[{"line":0,"depth":1},{"line":7,"depth":2},{"line":11,"de...` |
| `<key>.covenant_section` | `dict` | `{"1":{"breakpoints":[{"line":0,"depth":1},{"line":7,"depth":2},{"line":11,"depth":3},{"line":13,"...` |
| `<key>.covenant_section.<key>` | `dict` | `{"breakpoints":[{"line":0,"depth":1},{"line":7,"depth":2},{"line":11,"depth":3},{"line":13,"depth...` |
| `<key>.covenant_section.<key>.breakpoints` | `list` | `[{"line":0,"depth":1},{"line":7,"depth":2},{"line":11,"depth":3},{"line":13,"depth":3},{"line":15...` |
| `<key>.covenant_section.<key>.breakpoints[]` | `dict` | `{"line":0,"depth":1}` |
| `<key>.covenant_section.<key>.breakpoints[].depth` | `int` | `1` |
| `<key>.covenant_section.<key>.breakpoints[].line` | `int` | `0` |
| `<key>.covenant_section.<key>.common_depth_1` | `int` | `0` |
| `<key>.default_section` | `dict` | `{"1":{"breakpoints":[{"line":7,"depth":1},{"line":11,"depth":1},{"line":13,"depth":2},{"line":15,...` |
| `<key>.default_section.<key>` | `dict` | `{"breakpoints":[{"line":7,"depth":1},{"line":11,"depth":1},{"line":13,"depth":2},{"line":15,"dept...` |
| `<key>.default_section.<key>.breakpoints` | `list` | `[{"line":7,"depth":1},{"line":11,"depth":1},{"line":13,"depth":2},{"line":15,"depth":2},{"line":1...` |
| `<key>.default_section.<key>.breakpoints[]` | `dict` | `{"line":7,"depth":1}` |
| `<key>.default_section.<key>.breakpoints[].depth` | `int` | `1` |
| `<key>.default_section.<key>.breakpoints[].line` | `int` | `7` |
| `<key>.default_section.<key>.common_depth1` | `int` | `0` |

### `01_loan_agreements-20261110T071036Z-1-001\01_loan_agreements\main_control_file.json`
- Top-level object with 14526 keys; example top-level key: `000031/313616/0000313616-98-000010_5.txt`
| Key / nested field | Type(s) | Example (max 100 chars) |
|---|---|---|
| `<key>` | `dict` | `{"company":"DANAHER CORP","day":7,"month":9,"year":1990,"packageid":5131,"filehandle":"0000313616...` |
| `<key>.cnum` | `int` | `4403` |
| `<key>.company` | `str` | `DANAHER CORP` |
| `<key>.covenant_section` | `dict` | `{"1":{"top_line":4919,"bottom_line":5358},"2":{"top_line":5358,"bottom_line":5720}}` |
| `<key>.covenant_section.<key>` | `dict` | `{"top_line":4919,"bottom_line":5358}` |
| `<key>.covenant_section.<key>.bottom_line` | `int` | `5358` |
| `<key>.covenant_section.<key>.top_line` | `int` | `4919` |
| `<key>.day` | `int` | `7` |
| `<key>.default_section` | `dict` | `{"1":{"top_line":5721,"bottom_line":5916}}` |
| `<key>.default_section.<key>` | `dict` | `{"top_line":5721,"bottom_line":5916}` |
| `<key>.default_section.<key>.bottom_line` | `int` | `5916` |
| `<key>.default_section.<key>.top_line` | `int` | `5721` |
| `<key>.filehandle` | `str` | `0000313616-98-000010_5` |
| `<key>.gvkey` | `int` | `3735` |
| `<key>.index_page` | `str` | `edgar/data/313616/0000313616-98-000010-index.htm` |
| `<key>.month` | `int` | `9` |
| `<key>.packageid` | `int` | `5131` |
| `<key>.primary_contract` | `int` | `1` |
| `<key>.seq` | `int` | `5` |
| `<key>.year` | `int` | `1990` |

### `02_cuad-20261110T071043Z-1-001\02_cuad\CUAD_v1.json`
- Top-level object with 2 keys; example top-level key: `version`
| Key / nested field | Type(s) | Example (max 100 chars) |
|---|---|---|
| `data` | `list` | `[{"title":"LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGREEMENT","paragraphs":[{"qas":[{"answers":...` |
| `data[]` | `dict` | `{"title":"LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGREEMENT","paragraphs":[{"qas":[{"answers":[...` |
| `data[].paragraphs` | `list` | `[{"qas":[{"answers":[{"text":"DISTRIBUTOR AGREEMENT","answer_start":44}],"id":"LIMEENERGYCO_09_09...` |
| `data[].paragraphs[]` | `dict` | `{"qas":[{"answers":[{"text":"DISTRIBUTOR AGREEMENT","answer_start":44}],"id":"LIMEENERGYCO_09_09_...` |
| `data[].paragraphs[].context` | `str` | `EXHIBIT 10.6                                DISTRIBUTOR AGREEMENT           THIS  DISTRIBUTOR  AG...` |
| `data[].paragraphs[].qas` | `list` | `[{"answers":[{"text":"DISTRIBUTOR AGREEMENT","answer_start":44}],"id":"LIMEENERGYCO_09_09_1999-EX...` |
| `data[].paragraphs[].qas[]` | `dict` | `{"answers":[{"text":"DISTRIBUTOR AGREEMENT","answer_start":44}],"id":"LIMEENERGYCO_09_09_1999-EX-...` |
| `data[].paragraphs[].qas[].answers` | `list` | `[{"text":"DISTRIBUTOR AGREEMENT","answer_start":44}]` |
| `data[].paragraphs[].qas[].answers[]` | `dict` | `{"text":"DISTRIBUTOR AGREEMENT","answer_start":44}` |
| `data[].paragraphs[].qas[].answers[].answer_start` | `int` | `44` |
| `data[].paragraphs[].qas[].answers[].text` | `str` | `DISTRIBUTOR AGREEMENT` |
| `data[].paragraphs[].qas[].id` | `str` | `LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGREEMENT__Document Name` |
| `data[].paragraphs[].qas[].is_impossible` | `bool` | `False` |
| `data[].paragraphs[].qas[].question` | `str` | `Highlight the parts (if any) of this contract related to "Document Name" that should be reviewed ...` |
| `data[].title` | `str` | `LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGREEMENT` |
| `version` | `str` | `aok_v1.0` |

## JSONL files

### `04_annotated_data-20261110T071045Z-1-001\04_annotated_data\provisional_machine_extraction_v1.jsonl`
- Records: 15523
| Key / nested field | Type(s) | Example (max 100 chars) |
|---|---|---|
| `annotation_method` | `str` | `app.services.loan_extractor.extract_loan_information` |
| `annotation_status` | `str` | `PROVISIONAL_MACHINE_OUTPUT_NOT_GOLD` |
| `candidate_classification` | `str` | `LIKELY_LOAN_FINANCING` |
| `classification_confidence_calibration` | `str` | `NOT_CALIBRATED` |
| `classification_review_status` | `str` | `LIKELY_LOAN_AGREEMENT` |
| `confidence_calibration` | `str` | `NOT_CALIBRATED` |
| `confidence_estimate` | `NoneType` | `` |
| `dataset_version` | `str` | `1.0.0` |
| `document_id` | `str` | `000000/1750/0000895813-98-000136_4.txt` |
| `fields` | `dict` | `{"document_title":{"proposed_value":"CREDIT AGREEMENT","extractor_status":"candidate","evidence":...` |
| `fields.borrower` | `dict` | `{"proposed_value":"AAR CORP.","extractor_status":"candidate","evidence":"AAR CORP., a Delaware co...` |
| `fields.borrower.confidence_calibration` | `str` | `NOT_CALIBRATED` |
| `fields.borrower.confidence_estimate` | `NoneType` | `` |
| `fields.borrower.evidence` | `str` | `AAR CORP., a Delaware corporation (the "Borrower")` |
| `fields.borrower.evidence_provenance` | `list` | `[{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"AAR\n   CORP., a Delaware...` |
| `fields.borrower.evidence_provenance[]` | `dict` | `{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"AAR\n   CORP., a Delaware ...` |
| `fields.borrower.evidence_provenance[].document_id` | `str` | `000000/1750/0000895813-98-000136_4.txt` |
| `fields.borrower.evidence_provenance[].page_number` | `NoneType` | `` |
| `fields.borrower.evidence_provenance[].paragraph` | `NoneType` | `` |
| `fields.borrower.evidence_provenance[].review_record` | `NoneType` | `` |
| `fields.borrower.evidence_provenance[].section` | `str` | `ARTICLE XIV` |
| `fields.borrower.evidence_provenance[].source_end` | `int` | `11943` |
| `fields.borrower.evidence_provenance[].source_start` | `int` | `11890` |
| `fields.borrower.evidence_provenance[].source_text` | `str` | `AAR    CORP., a Delaware corporation (the "Borrower")` |
| `fields.borrower.evidence_provenance[].table_row` | `NoneType` | `` |
| `fields.borrower.extractor_status` | `str` | `candidate` |
| `fields.borrower.proposed_value` | `str` | `AAR CORP.` |
| `fields.borrower.provenance_status` | `str` | `available` |
| `fields.borrower.validation_status` | `str` | `PROVISIONAL_EXACT_SOURCE_SPANS` |
| `fields.default_related_clauses` | `dict` | `{"proposed_value":null,"extractor_status":"requires_review","evidence":"ARTICLE VII DEFAULTS ----...` |
| `fields.default_related_clauses.confidence_calibration` | `str` | `NOT_CALIBRATED` |
| `fields.default_related_clauses.confidence_estimate` | `NoneType` | `` |
| `fields.default_related_clauses.evidence` | `str` | `ARTICLE VII DEFAULTS -------- The occurrence of any one or more of the following events shall con...` |
| `fields.default_related_clauses.evidence_provenance` | `list` | `[{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"ARTICLE VII\n\n          ...` |
| `fields.default_related_clauses.evidence_provenance[]` | `dict` | `{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"ARTICLE VII\n\n           ...` |
| `fields.default_related_clauses.evidence_provenance[].document_id` | `str` | `000000/1750/0000895813-98-000136_4.txt` |
| `fields.default_related_clauses.evidence_provenance[].page_number` | `NoneType` | `` |
| `fields.default_related_clauses.evidence_provenance[].paragraph` | `NoneType, str` | `7.2.` |
| `fields.default_related_clauses.evidence_provenance[].review_record` | `NoneType` | `` |
| `fields.default_related_clauses.evidence_provenance[].section` | `str` | `ARTICLE VII` |
| `fields.default_related_clauses.evidence_provenance[].source_end` | `int` | `118451` |
| `fields.default_related_clauses.evidence_provenance[].source_start` | `int` | `118241` |
| `fields.default_related_clauses.evidence_provenance[].source_text` | `str` | `ARTICLE VII                                    DEFAULTS                                   -------...` |
| `fields.default_related_clauses.evidence_provenance[].table_row` | `NoneType` | `` |
| `fields.default_related_clauses.extractor_status` | `str` | `requires_review` |
| `fields.default_related_clauses.proposed_value` | `NoneType` | `` |
| `fields.default_related_clauses.provenance_status` | `str` | `available` |
| `fields.default_related_clauses.validation_status` | `str` | `NO_CANDIDATE` |
| `fields.document_title` | `dict` | `{"proposed_value":"CREDIT AGREEMENT","extractor_status":"candidate","evidence":"CREDIT AGREEMENT"...` |
| `fields.document_title.confidence_calibration` | `str` | `NOT_CALIBRATED` |
| `fields.document_title.confidence_estimate` | `NoneType` | `` |
| `fields.document_title.evidence` | `str` | `CREDIT AGREEMENT` |
| `fields.document_title.evidence_provenance` | `list` | `[{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"CREDIT AGREEMENT","review...` |
| `fields.document_title.evidence_provenance[]` | `dict` | `{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"CREDIT AGREEMENT","review_...` |
| `fields.document_title.evidence_provenance[].document_id` | `str` | `000000/1750/0000895813-98-000136_4.txt` |
| `fields.document_title.evidence_provenance[].page_number` | `NoneType` | `` |
| `fields.document_title.evidence_provenance[].paragraph` | `NoneType` | `` |
| `fields.document_title.evidence_provenance[].review_record` | `NoneType` | `` |
| `fields.document_title.evidence_provenance[].section` | `str` | `EXHIBIT 4.8` |
| `fields.document_title.evidence_provenance[].source_end` | `int` | `307` |
| `fields.document_title.evidence_provenance[].source_start` | `int` | `291` |
| `fields.document_title.evidence_provenance[].source_text` | `str` | `CREDIT AGREEMENT` |
| `fields.document_title.evidence_provenance[].table_row` | `NoneType` | `` |
| `fields.document_title.extractor_status` | `str` | `candidate` |
| `fields.document_title.proposed_value` | `str` | `CREDIT AGREEMENT` |
| `fields.document_title.provenance_status` | `str` | `available` |
| `fields.document_title.validation_status` | `str` | `PROVISIONAL_EXACT_SOURCE_SPANS` |
| `fields.fees_and_charges` | `dict` | `{"proposed_value":null,"extractor_status":"requires_review","evidence":"ther agrees to pay to the...` |
| `fields.fees_and_charges.confidence_calibration` | `str` | `NOT_CALIBRATED` |
| `fields.fees_and_charges.confidence_estimate` | `NoneType` | `` |
| `fields.fees_and_charges.evidence` | `str` | `ther agrees to pay to the Lender a commitment fee of .30% (or if the Borrower no longer has an In...` |
| `fields.fees_and_charges.evidence_provenance` | `list` | `[{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"ther agrees to pay to the...` |
| `fields.fees_and_charges.evidence_provenance[]` | `dict` | `{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"ther agrees to pay to the ...` |
| `fields.fees_and_charges.evidence_provenance[].document_id` | `str` | `000000/1750/0000895813-98-000136_4.txt` |
| `fields.fees_and_charges.evidence_provenance[].page_number` | `NoneType` | `` |
| `fields.fees_and_charges.evidence_provenance[].paragraph` | `NoneType, str` | `2.4.` |
| `fields.fees_and_charges.evidence_provenance[].review_record` | `NoneType` | `` |
| `fields.fees_and_charges.evidence_provenance[].section` | `str` | `ARTICLE II` |
| `fields.fees_and_charges.evidence_provenance[].source_end` | `int` | `46382` |
| `fields.fees_and_charges.evidence_provenance[].source_start` | `int` | `46095` |
| `fields.fees_and_charges.evidence_provenance[].source_text` | `str` | `ther agrees to pay to the Lender a    commitment fee of .30% (or if the Borrower no longer has an...` |
| `fields.fees_and_charges.evidence_provenance[].table_row` | `NoneType` | `` |
| `fields.fees_and_charges.extractor_status` | `str` | `requires_review` |
| `fields.fees_and_charges.proposed_value` | `NoneType` | `` |
| `fields.fees_and_charges.provenance_status` | `str` | `available` |
| `fields.fees_and_charges.validation_status` | `str` | `NO_CANDIDATE` |
| `fields.interest_rate` | `dict` | `{"proposed_value":null,"extractor_status":"requires_review","evidence":"\"Alternate Base Rate\" m...` |
| `fields.interest_rate.confidence_calibration` | `str` | `NOT_CALIBRATED` |
| `fields.interest_rate.confidence_estimate` | `NoneType` | `` |
| `fields.interest_rate.evidence` | `str` | `"Alternate Base Rate" means, for any day, a rate of interest per annum equal to the higher of (i)...` |
| `fields.interest_rate.evidence_provenance` | `list` | `[{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"\"Alternate Base Rate\" m...` |
| `fields.interest_rate.evidence_provenance[]` | `dict` | `{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"\"Alternate Base Rate\" me...` |
| `fields.interest_rate.evidence_provenance[].document_id` | `str` | `000000/1750/0000895813-98-000136_4.txt` |
| `fields.interest_rate.evidence_provenance[].page_number` | `NoneType` | `` |
| `fields.interest_rate.evidence_provenance[].paragraph` | `NoneType` | `` |
| `fields.interest_rate.evidence_provenance[].review_record` | `NoneType` | `` |
| `fields.interest_rate.evidence_provenance[].section` | `str` | `ARTICLE I` |
| `fields.interest_rate.evidence_provenance[].source_end` | `int` | `15187` |
| `fields.interest_rate.evidence_provenance[].source_start` | `int` | `14970` |
| `fields.interest_rate.evidence_provenance[].source_text` | `str` | `"Alternate Base Rate" means, for any day, a rate of interest per    annum equal to the higher of ...` |
| `fields.interest_rate.evidence_provenance[].table_row` | `NoneType` | `` |
| `fields.interest_rate.extractor_status` | `str` | `requires_review` |
| `fields.interest_rate.proposed_value` | `NoneType` | `` |
| `fields.interest_rate.provenance_status` | `str` | `available` |
| `fields.interest_rate.validation_status` | `str` | `NO_CANDIDATE` |
| `fields.lender` | `dict` | `{"proposed_value":"THE NORTHERN TRUST COMPANY","extractor_status":"candidate","evidence":"THE NOR...` |
| `fields.lender.confidence_calibration` | `str` | `NOT_CALIBRATED` |
| `fields.lender.confidence_estimate` | `NoneType` | `` |
| `fields.lender.evidence` | `str` | `THE NORTHERN TRUST COMPANY, an Illinois banking corporation (the "Lender")` |
| `fields.lender.evidence_provenance` | `list` | `[{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"THE NORTHERN TRUST\n   CO...` |
| `fields.lender.evidence_provenance[]` | `dict` | `{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"THE NORTHERN TRUST\n   COM...` |
| `fields.lender.evidence_provenance[].document_id` | `str` | `000000/1750/0000895813-98-000136_4.txt` |
| `fields.lender.evidence_provenance[].page_number` | `NoneType` | `` |
| `fields.lender.evidence_provenance[].paragraph` | `NoneType` | `` |
| `fields.lender.evidence_provenance[].review_record` | `NoneType` | `` |
| `fields.lender.evidence_provenance[].section` | `str` | `ARTICLE XIV` |
| `fields.lender.evidence_provenance[].source_end` | `int` | `12026` |
| `fields.lender.evidence_provenance[].source_start` | `int` | `11949` |
| `fields.lender.evidence_provenance[].source_text` | `str` | `THE NORTHERN TRUST    COMPANY, an Illinois banking corporation (the "Lender")` |
| `fields.lender.evidence_provenance[].table_row` | `NoneType` | `` |
| `fields.lender.extractor_status` | `str` | `candidate` |
| `fields.lender.proposed_value` | `str` | `THE NORTHERN TRUST COMPANY` |
| `fields.lender.provenance_status` | `str` | `available` |
| `fields.lender.validation_status` | `str` | `PROVISIONAL_EXACT_SOURCE_SPANS` |
| `fields.loan_facility_amount` | `dict` | `{"proposed_value":"$10,000,000","extractor_status":"requires_review","evidence":"s requested the ...` |
| `fields.loan_facility_amount.confidence_calibration` | `str` | `NOT_CALIBRATED` |
| `fields.loan_facility_amount.confidence_estimate` | `NoneType` | `` |
| `fields.loan_facility_amount.evidence` | `str` | `s requested the Lender to make available to the Borrower a revolving line of credit for loans in ...` |
| `fields.loan_facility_amount.evidence_provenance` | `list` | `[{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"s requested the Lender to...` |
| `fields.loan_facility_amount.evidence_provenance[]` | `dict` | `{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"s requested the Lender to ...` |
| `fields.loan_facility_amount.evidence_provenance[].document_id` | `str` | `000000/1750/0000895813-98-000136_4.txt` |
| `fields.loan_facility_amount.evidence_provenance[].page_number` | `NoneType` | `` |
| `fields.loan_facility_amount.evidence_provenance[].paragraph` | `NoneType` | `` |
| `fields.loan_facility_amount.evidence_provenance[].review_record` | `NoneType` | `` |
| `fields.loan_facility_amount.evidence_provenance[].section` | `str` | `ARTICLE XIV` |
| `fields.loan_facility_amount.evidence_provenance[].source_end` | `int` | `12424` |
| `fields.loan_facility_amount.evidence_provenance[].source_start` | `int` | `12160` |
| `fields.loan_facility_amount.evidence_provenance[].source_text` | `str` | `s requested the Lender to make available    to the Borrower a revolving line of credit for loans ...` |
| `fields.loan_facility_amount.evidence_provenance[].table_row` | `NoneType` | `` |
| `fields.loan_facility_amount.extractor_status` | `str` | `requires_review` |
| `fields.loan_facility_amount.proposed_value` | `str` | `$10,000,000` |
| `fields.loan_facility_amount.provenance_status` | `str` | `available` |
| `fields.loan_facility_amount.validation_status` | `str` | `PROVISIONAL_EXACT_SOURCE_SPANS` |
| `fields.maturity_date` | `dict` | `{"proposed_value":"the twentieth (20th) Payment Date following the Revolving Credit Termination D...` |
| `fields.maturity_date.confidence_calibration` | `str` | `NOT_CALIBRATED` |
| `fields.maturity_date.confidence_estimate` | `NoneType` | `` |
| `fields.maturity_date.evidence` | `str` | `"Facility Termination Date" means the twentieth (20th) Payment Date following the Revolving Credi...` |
| `fields.maturity_date.evidence_provenance` | `list` | `[{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"\"Facility Termination Da...` |
| `fields.maturity_date.evidence_provenance[]` | `dict` | `{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"\"Facility Termination Dat...` |
| `fields.maturity_date.evidence_provenance[].document_id` | `str` | `000000/1750/0000895813-98-000136_4.txt` |
| `fields.maturity_date.evidence_provenance[].page_number` | `NoneType` | `` |
| `fields.maturity_date.evidence_provenance[].paragraph` | `NoneType` | `` |
| `fields.maturity_date.evidence_provenance[].review_record` | `NoneType` | `` |
| `fields.maturity_date.evidence_provenance[].section` | `str` | `ARTICLE I` |
| `fields.maturity_date.evidence_provenance[].source_end` | `int` | `25734` |
| `fields.maturity_date.evidence_provenance[].source_start` | `int` | `25615` |
| `fields.maturity_date.evidence_provenance[].source_text` | `str` | `"Facility Termination Date" means the twentieth (20th) Payment    Date following the Revolving Cr...` |
| `fields.maturity_date.evidence_provenance[].table_row` | `NoneType` | `` |
| `fields.maturity_date.extractor_status` | `str` | `requires_review` |
| `fields.maturity_date.proposed_value` | `str` | `the twentieth (20th) Payment Date following the Revolving Credit Termination Date` |
| `fields.maturity_date.provenance_status` | `str` | `available` |
| `fields.maturity_date.validation_status` | `str` | `PROVISIONAL_EXACT_SOURCE_SPANS` |
| `fields.repayment_terms` | `dict` | `{"proposed_value":null,"extractor_status":"requires_review","evidence":"Revolving Credit Terminat...` |
| `fields.repayment_terms.confidence_calibration` | `str` | `NOT_CALIBRATED` |
| `fields.repayment_terms.confidence_estimate` | `NoneType` | `` |
| `fields.repayment_terms.evidence` | `str` | `Revolving Credit Termination Date shall be repaid in full on the Revolving Credit Termination Dat...` |
| `fields.repayment_terms.evidence_provenance` | `list` | `[{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"Revolving Credit\n       ...` |
| `fields.repayment_terms.evidence_provenance[]` | `dict` | `{"document_id":"000000/1750/0000895813-98-000136_4.txt","source_text":"Revolving Credit\n        ...` |
| `fields.repayment_terms.evidence_provenance[].document_id` | `str` | `000000/1750/0000895813-98-000136_4.txt` |
| `fields.repayment_terms.evidence_provenance[].page_number` | `NoneType` | `` |
| `fields.repayment_terms.evidence_provenance[].paragraph` | `NoneType, str` | `(b)` |
| `fields.repayment_terms.evidence_provenance[].review_record` | `NoneType` | `` |
| `fields.repayment_terms.evidence_provenance[].section` | `str` | `ARTICLE II` |
| `fields.repayment_terms.evidence_provenance[].source_end` | `int` | `44912` |
| `fields.repayment_terms.evidence_provenance[].source_start` | `int` | `44597` |
| `fields.repayment_terms.evidence_provenance[].source_text` | `str` | `Revolving Credit         Termination Date shall be repaid in full on the Revolving Credit        ...` |
| `fields.repayment_terms.evidence_provenance[].table_row` | `NoneType` | `` |
| `fields.repayment_terms.extractor_status` | `str` | `requires_review` |
| `fields.repayment_terms.proposed_value` | `NoneType` | `` |
| `fields.repayment_terms.provenance_status` | `str` | `available` |
| `fields.repayment_terms.validation_status` | `str` | `NO_CANDIDATE` |
| `preliminary_agreement_type` | `str` | `LOAN_OR_CREDIT_AGREEMENT` |
| `source_path` | `str` | `datasets/01_loan_agreements/publicly_filed_contracts/000000/1750/0000895813-98-000136_4.txt` |
| `source_sha256` | `str` | `643aa0b10b55c3d7f5c981cf89326e6fd7bdac732c568e96b01d162ca01801fb` |

## ZIP archives

### `01_loan_agreements-20261110T071036Z-1-001\01_loan_agreements\publicly_filed_contracts.zip`
- File members: 18508; example member: `000000/6845/0000950131-94-001485_2.txt`
- Member schema: ZIP path/name, uncompressed byte size, compressed byte size; text members are UTF-8/byte-decoded with replacement for this example.
- Example text (max 100 chars): `  <PAGE>                                   CREDIT AGREEMENT                                       be`

## Plain-text documents

The 01 corpus uses `.txt` contract documents. Each document's value is decoded text; document ID/path is the corresponding relative path. The manifest contains per-document character lengths and SHA-256 values. Example text from the first available unpacked file:

- Example (max 100 chars): ` <Page>                              REVOLVING LOAN AGREEMENT            This REVOLVING LOAN AGREEME`
