# Local retrieval-only baseline

- Corpus: 1,500 risk-clause passages from 60 annotation documents.
- Queries evaluated: 75; corpus file failures: 0.
- Encoder: `intfloat/multilingual-e5-small`; CPU, local model weights; FAISS inner-product index over L2-normalized embeddings.
- This is a **machine-evidence proxy**, not gold-label evaluation: queries use field names plus machine-proposed candidate values, and relevant passages are located by matching the sheet's machine evidence quote. No human labels or answers were generated.
- Q&A sheet rows remain blank; no Q&A benchmark could be evaluated without human-written questions and answers.

| Metric | Result |
|---|---:|
| Hit@1 | 10/75 (13.3%) |
| Hit@3 | 18/75 (24.0%) |
| Hit@5 | 23/75 (30.7%) |
| MRR@5 | 0.1902 |

Per-query machine-only outcomes: `data\processed\retrieval_eval.csv`.
Do not interpret these proxy metrics as human-validated performance.
