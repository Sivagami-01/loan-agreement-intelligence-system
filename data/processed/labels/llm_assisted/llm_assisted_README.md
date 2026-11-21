# LLM-assisted silver labels

**IMPORTANT:** These are **LLM-assisted SILVER labels, not human gold labels**. Evidence quotes are checked against the source text (`data/friend/01_loan_agreements/publicly_filed_contracts.zip` for SEC contracts; `data/processed/ingested/*.txt` for Indian MITC documents), accepting exact matches or whitespace-normalized matches. A successful automatic check confirms that the quote occurs in the extracted text; it does not certify legal interpretation or source text completeness.

The helper reads the original annotation sheets and ZIP without modifying them. It selects the 30 shortest documents in the approved 30,000-225,000-character range. Labels are appended in three-document batches, and already verified rows are skipped so a completed batch can be rerun safely. Batch JSON files are manually prepared inputs to the append command.

## Current progress

- **Key fields (pilot scope: first 10 documents)**: **10 of 10 pilot documents complete (`160` rows across ranks `01`–`10`; overall `10/30` in helper selection order)**:
  - **Total counts (`160` rows)**: `133` found, `18` `NOT_PRESENT`, `9` `UNCLEAR`, **`142` quotes verified**, `0` failures (`100.0%` quote verification).
  - **Docs `01`–`03` (`48` rows, `batch_01_key.json`)**: `36` found, `5` `NOT_PRESENT`, `7` `UNCLEAR`, `43` verified quotes (`0` failures). Written on `2026-11-11` (`model`: `"OpenAI ChatGPT via Copilot SDK; exact model ID unavailable"`).
  - **Docs `04`–`10` (`112` rows, `batch_02_key.json`, `batch_03_key.json`, `batch_04_key.json`)**: `97` found, `13` `NOT_PRESENT`, `2` `UNCLEAR`, `99` verified quotes (`0` failures). Written on `2026-11-12` (`model`: `"unknown model; session tool: Antigravity"`).
- **Risk clauses (`209` total clauses across `13` documents; `209/209` quotes verified, `0` failures, `19` low-confidence rows)**:
  - **SEC pilot docs `01`–`10` (`risk_llm.csv`, `batch_01_risk.json`–`batch_04_risk.json`)**: `171` clauses (`17` each on docs `01`–`09`, `18` on doc `10`), `171/171` quotes verified (`0` failures), `model`: `"unknown model; session tool: Antigravity"`. Severities: `Low=52`, `Medium=43`, `High=52`, `Critical=24`.
  - **Indian MITC docs (`risk_indian_llm.csv`, `batch_indian_risk.json`)**: `38` clauses across `03_dbs_mitc` (`12`), `09_muthoothomefin_MHIL-MITC` (`14`), and `11_gichfindia_MOST-IMPORTANT-TERMS-1` (`12`), `38/38` quotes verified (`0` failures), `model`: `"unknown model; session tool: Antigravity"`. Stored in `risk_indian_llm.csv` using the **exact same 11 CSV columns** as `risk_llm.csv` because `scripts/llm_assisted_annotation_tools.py` resolves only ZIP SEC contracts listed in `key_info_sheet.csv` and cannot verify ingested MITC files.
  - **Combined category totals (`7` guideline categories, each `>= 10`)**: `Financial terms=30`, `Repayment=32`, `Penalties and charges=30`, `Collateral=29`, `Default conditions=30`, `Termination=27`, `Covenants=31`.
  - **Combined severity totals**: `Low=63`, `Medium=57`, `High=62`, `Critical=27` (`19` marked `[confidence: low - ...]` inside `rationale`).
- **Risk-label consistency fix pass (`risk_revisions.csv`, rules `R1`–`R3`)**: **LLM-assisted silver revisions, not human gold** (`0` Gemini API calls; `model`: `"unknown model; session tool: Antigravity"`). Added consistency rules `R1`–`R3` to `docs/labeling_guideline.md` and logged **`43` changed rows** across `209` total clauses in `risk_revisions.csv` (`37` from `risk_llm.csv`, `6` from `risk_indian_llm.csv`; `risk_llm.csv`, `risk_indian_llm.csv`, and `key_info_llm.csv` were not overwritten):
  - **By rule**: `R1` = `2`, `R2` = `30`, `R1 and R2` = `3`, `R3` = `8` (rationale-prefix `[borrower-protective]` updates with unchanged category/severity, including `09_muthoothomefin_MHIL-MITC` `IM06`).
  - **Old vs New Category (`209`)**: `Financial terms` `30 -> 25`, `Covenants` `31 -> 36`; unchanged: `Repayment=32`, `Penalties and charges=30`, `Collateral=29`, `Default conditions=30`, `Termination=27`.
  - **Old vs New Severity (`209`)**: `Low` `63 -> 64`, `Medium` `57 -> 71`, `High` `62 -> 65`, `Critical` `27 -> 9`.
  - **High + Critical share**: `89 / 209` (`42.58%`) before -> `74 / 209` (`35.41%`) after.
- Q&A, summaries, second-pass agreement, and human spot-checks have not yet been completed.

## Provenance note

- These files (`key_info_llm.csv`, `risk_llm.csv`, `risk_indian_llm.csv`, `risk_revisions.csv`, and `batch_*_key.json` / `batch_*_risk.json`) are **LLM-assisted silver labels/revisions, not human gold**.
- The `label_source` column retains `"claude_code_llm_assisted"` for schema continuity across batches, while `model` states the actual generating runtime (`"OpenAI ChatGPT via Copilot SDK; exact model ID unavailable"` for `batch_01_key.json`; `"unknown model; session tool: Antigravity"` in `scripts/llm_assisted_annotation_tools.py` for key-field docs `04`–`10` and all risk-clause batches because the session model ID is not directly exposed).

## Commands

Run these from PowerShell:

```powershell
$python = 'C:\Users\shivu\AppData\Local\Programs\Python\Python313\python.exe'
$helper = 'C:\finalYear\scripts\llm_assisted_annotation_tools.py'

# See the selected document list and current completion counts.
& $python $helper --status

# Inspect the next three source documents and their candidate evidence.
& $python $helper --inspect-key-batch 1

# Append a manually reviewed batch after preparing its JSON in this folder.
& $python $helper --append-json 'C:\finalYear\data\processed\labels\llm_assisted\batch_02_key.json'

# Check saved rows, evidence verification, and per-part progress.
& $python $helper --validate
& $python $helper --metrics
& $python $helper --status
```

Batch indices are zero-based. Use `--inspect-batch N` for the corresponding risk-clause inspection. Do not copy LLM-assisted labels into human fields or describe them as human-reviewed.
