# Indian text threshold proposal

> Superseded. The candidate values in this historical proposal (0.10 / 0.30 / 0.65) were not adopted. The active thresholds remain 0.12 / 0.40 / 0.45; see `threshold_proposal_v2.md` for the OCR-based reassessment.

## Current threshold values inspected

- Expected-script share < 0.12: BAD.
- Expected-script share < 0.40: SUSPICIOUS (unless BAD rule applies).
- Symbol ratio > 0.45 on at least 30 visible characters: BAD.
- Fewer than 20 alphabetic letters: BAD.
- Any `(cid:...)`, private-use character, replacement character, or run of 8+ non-word/non-space characters: BAD.
- Script shares already use alphabetic characters only; punctuation, digits, whitespace, and symbols are excluded. The requested letter-only denominator is already implemented, so this alone does not change any class.

## Observed metrics by current class

| Current class | Pages | Expected-script share p10/p25/p50/p75/p90 | Symbol ratio p50/p90/max | Pages with PUA | Pages with CID |
|---|---:|---|---|---:|---:|
| GOOD | 92 | 0.403/0.407/0.426/0.455/0.487 | 0.037/0.077/0.278 | 0 | 0 |
| SUSPICIOUS | 116 | 0.268/0.310/0.338/0.364/0.383 | 0.040/0.053/0.105 | 0 | 0 |
| BAD | 32 | 0.260/0.307/0.335/0.402/0.439 | 0.064/0.102/0.174 | 27 | 0 |

## Proposed candidate thresholds (not a gold-quality claim)

- BAD if expected-script share < 0.10; SUSPICIOUS if < 0.30; otherwise GOOD for script-share check.
- BAD if symbol ratio > 0.65 (still requires at least 30 visible characters).
- Keep hard corruption checks unchanged: fewer than 20 letters, any CID/private-use/replacement character, or 8+ symbol run remains BAD.

Reasoning: current GOOD pages with a known expected script have script-share p10 of 0.403; SUSPICIOUS pages have p10 0.268, p25 0.310, median 0.338, and p90 0.383. This suggests the 0.40 cut partitions the pages sharply, but does not establish text failure; the bilingual-page concern motivates testing a 0.30 SUSPICIOUS boundary while retaining a 0.10 severe-loss boundary. Among current BAD pages, 27/32 contain private-use characters, so relaxing script share or symbol ratio does not excuse those corrupted pages. The 0.65 symbol cutoff is a cautious proposal; current observed pages have maximum symbol ratio below 0.30 in each class, so this cutoff changes no page by itself. Review calibration images before adopting permanently.

Candidate simulation over 240 pages: 183 GOOD, 25 SUSPICIOUS, 32 BAD. These values are proposed only; the verification script is run with them separately for report_v2.
