# OCR-based threshold reassessment (v2)

## Active rule

- Expected-script share below **0.12**: BAD.
- Expected-script share below **0.40**: SUSPICIOUS.
- Non-alphanumeric symbol ratio above **0.45** (at least 30 visible characters): BAD.
- Keep hard corruption rules: fewer than 20 letters, any private-use or replacement character, any `(cid:...)`, or an 8+ character symbol run is BAD.

## Evidence from 300-DPI OCR comparison

- Pages evaluated: 240; source classes: 240.
- Hard-rule BAD pages: 32; OCR candidate pages: 151.
- Candidate pages are machine triage only. OCR output and the source/OCR metrics are not human review or gold labels.

| Source class | Pages | Source script share p10 / p50 / p90 | OCR script share p50 | OCR confidence p50 | Similarity p50 | Word Jaccard p50 |
|---|---:|---|---:|---:|---:|---:|
| GOOD | 92 | 40.3% / 42.6% / 48.7% | 40.8% | 88.514 | 83.3% | 70.6% |
| SUSPICIOUS | 116 | 27.0% / 33.9% / 38.5% | 32.4% | 88.209 | 73.6% | 66.3% |
| BAD | 32 | 27.5% / 33.6% / 44.1% | 35.4% | 87.569 | 73.9% | 64.3% |

## Proposal

**Retain 0.12 / 0.40 / 0.45. Do not adopt the earlier 0.10 / 0.30 / 0.65 trial.** The OCR comparisons are useful for identifying pages that merit review, but OCR agreement is not a truth label: a high overlap can preserve the same extraction error, and a low overlap can result from OCR/layout differences on bilingual tables. No threshold change is justified without hand-checking the rendered pages against the PDF images.

The historical `threshold_proposal.md` is marked superseded; this v2 assessment is the current recommendation.
