# Local loan-label review app

The app reads the original sheets under `data/processed_v1/annotation_sheets/` without changing them. It writes human-entered labels only under `data/processed/labels/`. Machine proposals are never treated as labels until you explicitly click/save a human decision.

## Run

From the project root:

```powershell
python -m pip install streamlit
python -m streamlit run tools\review_app.py
```

The review app is local and does not send document text to a hosted service.

The sidebar defaults to the first 30 documents and allows up to all 60. `Only documents with available text` is enabled by default; the banner reports available and skipped document counts, and the expander lists each skipped ID and reason. Source lookup prefers the ZIP (read-only) and falls back to the unpacked folder. No files are extracted into `data/friend`.

Each tab resumes from its own saved CSV. Key-field actions are `Correct`, `Edit`, `Not present`, and `Unsure`; not-present/unsure values remain blank. Risk severity starts empty. The app shows up to 20 clauses per document, prioritizing keyword hits. Q&A starts from the four blank rows per document; copy an exact passage from the displayed source segment into the selected-text box, then use the copy button.

Outputs:

- `data/processed/labels/key_info_labeled.csv`
- `data/processed/labels/risk_labeled.csv`
- `data/processed/labels/qa_labeled.csv`

To print counts and refresh `data/processed/labels/progress.md`:

```powershell
python scripts\label_progress.py
```
