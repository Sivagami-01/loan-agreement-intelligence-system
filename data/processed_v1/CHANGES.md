# Changes and refreshed counts

Updated by `scripts/build_processed_v1.py`. Existing source data was read-only.

## Changes made

- Repeated SHA-256 groups now retain one canonical document: the inventory's `canonical_duplicate_document_id` when it identifies a member of that hash group; otherwise the lexically smallest `doc_id`. Only the non-canonical group members are duplicate-flagged.
- Standardized the year column as `contract_year` in manifest and clean-set outputs.
- All three human-verified gold documents are assigned to the test set. Any reviewed document outside clean criteria is listed separately in `gold_extra.csv`.
- Selected 60 non-gold test documents between 30,000 and 400,000 characters, stratified by `contract_year`.
- Risk clauses are limited to control-file `default_section`/`covenant_section` ranges or clauses matching the requested keyword list. The set is balanced toward 25 clauses per document and capped at 1,500 total.
- Risk keywords: default, penalt, late charge, prepay, fee, interest rate, collateral, security interest, guarant, terminat, acceleration, covenant.
- Created four blank QA rows for each of 30 selected documents.
- Removed duplicate normalized annotation rows using `(document_id, field_name, candidate_value, review_status)` as the de-duplication key.

## Counts

- Manifest documents: 18508
- Repeated SHA-256 groups: 317
- Documents in repeated SHA-256 groups: 667
- Non-canonical duplicate copies flagged: 350
- Clean documents under the previous duplicate rule: 11733
- Clean documents after this change: 11901
- Documents added back by canonical hash deduplication: 168
- Gold documents identified: 3
- Clean gold documents in test: 2
- Additional `gold_extra` documents in test: 1
- Train / validation / test clean counts: 8330 / 1786 / 1785
- Company overlaps between clean splits: 0 / 0 / 0
- Normalized annotation rows after de-duplication: 234
- Duplicate annotation rows removed: 39
- Annotation-sheet documents: 60
- Key-info rows: 960
- Risk clause rows: 1500 (target 1500)
- QA documents / blank rows: 30 / 120

## Risk clauses per selected document

| doc_id | clauses |
|---|---:|
| `000000/8063/0000950152-08-004105_2.txt` | 27 |
| `000002/21665/0000950130-02-005479_4.txt` | 26 |
| `000002/27566/0000945836-96-000035_3.txt` | 26 |
| `000002/27996/0000897101-01-500697_3.txt` | 26 |
| `000003/34563/0001104659-09-014658_2.txt` | 26 |
| `000003/38984/0000038984-97-000026_6.txt` | 26 |
| `000006/64279/0000831259-06-000028_2.txt` | 26 |
| `000006/65873/0000065873-03-000056_3.txt` | 26 |
| `000006/66895/0000930661-97-000035_3.txt` | 26 |
| `000007/78749/0000950152-05-008319_2.txt` | 26 |
| `000008/89800/0000950123-10-066683_3.txt` | 26 |
| `000009/97052/0000097052-05-000014_2.txt` | 26 |
| `000010/100885/0000889812-95-000124_3.txt` | 26 |
| `000010/104897/0000950123-11-030926_2.txt` | 26 |
| `000035/350692/0000950134-04-001249_9.txt` | 26 |
| `000035/352915/0000893220-97-001362_3.txt` | 26 |
| `000035/354908/0001193125-06-206877_2.txt` | 26 |
| `000035/354908/0001193125-11-051695_3.txt` | 26 |
| `000070/709283/0000709283-03-000001_5.txt` | 26 |
| `000071/711039/0000711039-95-000025_2.txt` | 26 |
| `000072/721371/0000950152-00-004012_2.txt` | 26 |
| `000074/749251/0000950123-04-013195_2.txt` | 26 |
| `000074/749872/0000950152-01-001872_2.txt` | 26 |
| `000075/750004/0000922423-04-002111_8.txt` | 26 |
| `000080/801898/0000801898-05-000120_4.txt` | 26 |
| `000081/810113/0000950116-04-002411_4.txt` | 7 |
| `000084/849547/0000950128-00-000940_5.txt` | 26 |
| `000085/858877/0001193125-07-185320_2.txt` | 26 |
| `000087/876645/0000891618-03-004250_9.txt` | 6 |
| `000087/879526/0000950137-00-003670_2.txt` | 26 |
| `000087/879526/0000950137-97-003748_2.txt` | 26 |
| `000088/885725/0001104659-15-027462_2.txt` | 26 |
| `000088/885975/0000950134-98-000678_6.txt` | 26 |
| `000089/890491/0000950123-02-006213_3.txt` | 26 |
| `000091/910079/0000910079-99-000004_3.txt` | 26 |
| `000092/922521/0000950005-97-000330_3.txt` | 26 |
| `000092/923118/0000923118-98-000047_4.txt` | 26 |
| `000092/923118/0000923118-99-000019_4.txt` | 26 |
| `000092/925645/0001140361-14-041859_2.txt` | 26 |
| `000094/949158/0000950123-10-087123_2.txt` | 26 |
| `000102/1020258/0000950144-98-001112_2.txt` | 26 |
| `000102/1022222/0000950130-97-001335_15.txt` | 26 |
| `000103/1037949/0000950134-01-502040_5.txt` | 26 |
| `000103/1039213/0000912057-97-018811_19.txt` | 26 |
| `000104/1041426/0000950144-99-003055_2.txt` | 4 |
| `000104/1042893/0000899243-01-501236_3.txt` | 26 |
| `000104/1042893/0000899243-97-001570_6.txt` | 26 |
| `000104/1046032/0000950115-00-000847_2.txt` | 26 |
| `000105/1052667/0000912057-00-028795_20.txt` | 26 |
| `000105/1058033/0001005477-99-003520_9.txt` | 26 |
| `000106/1063193/0001047469-99-002665_2.txt` | 26 |
| `000110/1109357/0000950137-06-011523_2.txt` | 26 |
| `000111/1113099/0000950152-04-001887_3.txt` | 26 |
| `000112/1122787/0001012870-03-003181_12.txt` | 26 |
| `000113/1135971/0001135971-09-000032_12.txt` | 26 |
| `000113/1135971/0001571049-16-010732_2.txt` | 26 |
| `000131/1317630/0000950123-11-015028_2.txt` | 26 |
| `000131/1317630/0000950124-07-006359_2.txt` | 26 |
| `000131/1317630/0001104659-13-091575_2.txt` | 26 |
| `000136/1365555/0001144204-12-044354_2.txt` | 26 |
