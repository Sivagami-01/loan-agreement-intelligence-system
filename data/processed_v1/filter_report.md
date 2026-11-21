# Clean-set filter report

- Input documents: 18508
- Clean documents: 11901
- Classification counts: {'CANDIDATE_UNVERIFIED': 1897, 'DUPLICATE': 350, 'LIKELY_LOAN_AGREEMENT': 15525, 'NEEDS_MANUAL_REVIEW': 77, 'NOT_LOAN_AGREEMENT': 262, 'RELATED_DOCUMENT_AMENDMENT': 397}

## Removed counts by individual reason

Counts below are independent (a document may fail more than one condition):

- not_likely_loan_agreement: 2983
- not_primary_contract: 5101
- duplicate: 350
- length_under_5000: 94

## Exclusive first-failure counts

These sequential counts are mutually exclusive and sum with the clean set to the input total:

- not_likely_loan_agreement: 2983
- not_primary_contract: 3619
- duplicate: 0
- length_under_5000: 5

## Split counts and group isolation

- Train: 8330
- Val: 1786
- Test: 1785
- Human-verified documents identified in review data: 3
- Gold-reviewed documents forced to test: 2
- Additional human-verified gold_extra documents in test: 1
- Documents added back by canonical SHA-256 deduplication: 168
- Company overlaps (train/val, train/test, val/test): 0, 0, 0
- Zero company overlap: yes

Human-verified review rows are resolved through document IDs and recorded source paths. All reviewed companies are assigned to test. Gold documents that fail clean-set filters are listed separately in gold_extra.csv and remain part of the test set without being mixed into clean_loans.csv.

Reviewed documents outside the clean set:

- `000082/827156/0000950153-01-500650_2.txt`: primary_contract is not 1

For repeated SHA-256 hashes, only non-canonical copies are duplicate-flagged; canonical copies are selected from canonical_duplicate_document_id or, when absent, the lexically smallest doc_id. Grouping by company uses the recorded company value. Rows with a missing company are isolated by document ID.

The split assignment is seeded with 42 and assigns whole companies to approximate document-level 70/15/15 targets; companies containing gold-reviewed documents are forced into test.
