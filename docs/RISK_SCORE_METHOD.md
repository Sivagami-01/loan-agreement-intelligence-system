# Risk Score Method (Plain-English Guide)

## What This Score Means

This score is **a relative indicator of contract risk from the clauses found, NOT a probability of default and NOT financial or legal advice**. It aggregates clause-level risk labels (`Low`, `Medium`, `High`, `Critical`) across seven standard loan categories into a deterministic `0–100` number so two readers get the exact same score for the same clauses regardless of clause ordering.

---

## Formula (`mean_top3`, deterministic, zero LLM calls)

1. **Severity points per clause**:
   - `Low` = `1`
   - `Medium` = `2`
   - `High` = `3`
   - `Critical` = `4`
2. **Per-category risk (`0` to `1`)**:
   - In each of the 7 categories, take the **top `3` clauses** by severity points (ties broken deterministically by page ascending, then `clause_id`).
   - `category_risk = mean(points of those top clauses) / 4`.
   - If a category has `1` or `2` clauses, take the mean of those available (`k = 1` or `2`).
   - If a category has `0` clauses, `category_risk = 0` and it is marked `"No clause found in this document"`.
3. **Category weights (sum = `1.00`)**:
   - `Default conditions`: `0.25`
   - `Penalties and charges`: `0.20`
   - `Financial terms`: `0.15`
   - `Repayment`: `0.15`
   - `Collateral`: `0.10`
   - `Termination`: `0.10`
   - `Covenants`: `0.05`
4. **Weighted total score (`0.0` to `100.0`)**:
   - `score = 100 × sum(weight × category_risk)`, rounded to `1` decimal place.
   - Each included clause contributes `weight × points / (4 × k) × 100` points (where `k` is the number of top clauses averaged in that category), so all clause contributions sum to the unrounded score.
5. **Risk level & Critical floor rule**:
   - Score bands: `Low` (`< 25`), `Moderate` (`25` to `< 50`), `High` (`50` to `< 75`), `Critical` (`>= 75`).
   - **Floor rule** (`floor_rule: true` in `config/score.yaml`): if **any** clause in the document is `Critical`, the final `level` is raised to at least `High` (recording `critical_floor_applied: true` and `level_before_floor`), so a dangerous sudden-acceleration or collateral-loss clause cannot be masked into `Low` or `Moderate` by mild terms elsewhere.

---

## Worked Example (Reproduced in `test_4b_score.py` T3)

Suppose a document has:
- `Default conditions`: `High` (`3`), `Medium` (`2`) -> `k=2`, `mean = 2.5`, `category_risk = 2.5 / 4 = 0.625`
  - Contributions: `High` = `0.25 × 3 / (4 × 2) × 100 = 9.375`, `Medium` = `0.25 × 2 / (4 × 2) × 100 = 6.25` -> subtotal `15.625`
- `Penalties and charges`: `Low` (`1`), `Low` (`1`), `Medium` (`2`), `High` (`3`) -> top 3 = `[High, Medium, Low]`, `k=3`, `mean = 2.0`, `category_risk = 2.0 / 4 = 0.5` -> subtotal `10.0`
- `Financial terms`: `Medium` (`2`) -> `k=1`, `category_risk = 2 / 4 = 0.5` -> subtotal `7.5`
- `Repayment`: none -> `category_risk = 0` (`"No clause found in this document"`) -> subtotal `0.0`
- `Collateral`: `High` (`3`) -> `k=1`, `category_risk = 3 / 4 = 0.75` -> subtotal `7.5`
- `Termination`: `Critical` (`4`) -> `k=1`, `category_risk = 4 / 4 = 1.0` -> subtotal `10.0`
- `Covenants`: `Low` (`1`) -> `k=1`, `category_risk = 1 / 4 = 0.25` -> subtotal `1.25`

Sum of contributions = `15.625 + 10.0 + 7.5 + 0 + 7.5 + 10.0 + 1.25 = 51.875` -> **Score = `51.9`**, **Level = `High`** (`critical_floor_applied: false` because raw level is already `High`).

---

## Variants and Pre-Registered Decision Rule (`padded_top3`)

Because `mean_top3` divides only by the number of clauses found in a category (`k = 1, 2, or 3`), adding `Low` clauses to a `1`- or `2`-clause category dilutes its average (`18.8 -> 10.4` in a single-category `High` test), and a single `Critical` clause in `Default conditions` reaches `25.0` points on its own.

Under **`padded_top3`**:
- Take the top `3` clauses in each category (ties: page ascending, then `clause_id`).
- If a category has `0` clauses, `category_risk = 0` (`"No clause found"`).
- If a category has `1` or `2` clauses, pad the missing slots with `1` point (`Low`): `category_risk = (sum of real clauses + missing_slots * 1) / 12`.
- Each real clause contributes `weight * points / 12 * 100` points, and missing slots appear as one line `"padding (missing clauses counted as Low)"` contributing `weight * missing_slots / 12 * 100`, so all contributions still sum to the score.

**Pre-registered decision rule** (recorded before running on the labeled documents):
> padded_top3 becomes the default if (a) adding Low clauses to a category with 1 or 2 clauses never changes the score, (b) the monotonic test (raising any severity never lowers the score) passes on all clauses of all 13 documents, (c) a category with exactly one clause can reach at most 0.5 risk.

If all three pass, `config/score.yaml` switches `method` to `padded_top3`; otherwise `mean_top3` stays the default.

**Outcome**: All three checks passed (`(a)` zero dilution for 1–2 clause categories, `(b)` 100% monotonic across 200 upgrades in 13 documents, `(c)` max single-clause category risk = `0.500 <= 0.5`), so **`padded_top3` was adopted as the default in [`config/score.yaml`](file:///C:/finalYear/config/score.yaml)**.

---

## Reading the Level

- **Unvalidated plan bands**: The `Low (<25)`, `Moderate (25–<50)`, `High (50–<75)`, and `Critical (>=75)` thresholds come from [`docs/MASTER_PLAN.md`](file:///C:/finalYear/docs/MASTER_PLAN.md) and are **not calibrated** on empirical default or loss outcomes.
- **Narrow observed range & Critical-floor effect**: Across the `13` labeled documents with `padded_top3`, silver scores fell between **`41.2` and `51.7`** (`47.9–62.1` under `mean_top3`): only **`3` reach `High` by score alone** (`50.0–51.7`) and **`6` more are `High` only because of the Critical floor** (`41.2–49.2` before floor). Under `mean_top3`, `12/13` were `High`.
- **`Critical` band practically unreachable**: Reaching `Critical (>=75)` under `padded_top3` requires `3` or more `High`/`Critical` clauses in nearly every category (the highest observed score is `51.7`). Therefore, **the numeric score and the list of `Critical` clauses are the main output, and the risk level label is advisory**.
- **UI display rule**: The app must show the **numeric score together with the category breakdown, per-category `evidence_strength` (`strong` >=3 clauses, `limited` 1–2, `none` 0), any Critical floor `level_explanation`, and this sample range (`41.2–51.7`) — NEVER the risk level badge alone**.
- **Page availability note**: Two SEC documents (`000002/27566/0000945836-96-000035_3.txt` and `000081/810113/0000950116-04-002411_4.txt`) omit page numbers in the silver labels; drivers from those clauses display `page = "not available"`.
- **Information tool only**: This output is an informational contract-reading aid, **not financial or legal advice**.

---

## Limitations

1. **Selected-clause sample only**: The `209` pilot clauses are only clauses a labeler selected as risk clauses; running over a full, uncurated document will produce different clause mixes.
2. **SEC vs Indian MITC asymmetry**: US SEC corporate loan agreements and Indian RBI MITC summaries are not directly comparable (MITCs contain few covenant clauses, leaving `Covenants` and other categories sparse or absent).
3. **Unvalidated thresholds**: The `25 / 50 / 75` score boundaries come from the design plan (`docs/MASTER_PLAN.md`), not from empirical calibration against loan defaults or borrower outcomes.
4. **Silver & predicted inputs**: Current document scores use LLM-assisted silver labels (`risk_final.csv`) or classifier predictions (`risk_pred_*.csv`); no human-validated document risk ranking exists yet.
5. **Dilution sensitivity in `mean_top3` and `blend`**: Because `mean_top3` averages up to `3` clauses per category, adding `Low` clauses to a sparse category (`1` `High` + `2` `Low`) reduces `category_risk` (`0.75 -> 0.417`), whereas `max` ignores additional harmless clauses (see Stage 4b dilution and sensitivity checks in `docs/WORK_REPORT.md`).
