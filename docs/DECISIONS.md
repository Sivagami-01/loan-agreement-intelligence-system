# Decisions log

| Decision | Reason | Alternative considered |
|---|---|---|
| Use the ZIP first for annotation document text, then the existing unpacked folder; never extract the archive. | The archive is present and contains 18,508 text entries; `clean_loans.csv` resolves in full from it, while the unpacked folder is partial. | Use only the unpacked folder, which leaves clean-loan document coverage incomplete. |
| Treat all OCR comparisons and proposed threshold changes as machine evidence, never as human review or gold labels. | This preserves the user's separation between machine outputs and human annotation. | Promote machine metrics into labels, which is prohibited. |
| Keep the current Indian text thresholds at 0.12 / 0.40 / 0.45. | The user explicitly instructed that the trial 0.10 / 0.30 / 0.65 values must not be adopted. | Use the previous trial thresholds. |
| Exclude basename-only document matches unless the sheet evidence quote occurs exactly in the candidate text and the basename is unique. | Basenames can collide and could display the wrong contract. | Accept an ambiguous basename or a match without evidence. |
| Use small, local multilingual retrieval models only; do not call hosted services or use API keys. | The project disallows paid services, API keys, and cloud services. | Use a hosted embedding or answer-generation service. |
| Keep model files, evaluation outputs, OCR results, and generated reports under the explicitly permitted output folders. | Source and protected dataset folders must remain unchanged. | Write generated outputs alongside raw or friend data. |
| Retain the active OCR thresholds at 0.12 / 0.40 / 0.45; treat 0.10 / 0.30 / 0.65 as a historical trial only. | Letter-only share did not change classifications, and OCR comparison differences on bilingual pages do not justify promoting the trial rule. | Adopt the trial reduction in SUSPICIOUS pages without visual review. |
| Include only the four newly verified loan-product MITCs in the new loan corpus. | Eleven other new PDFs are unrelated formats or credit-card documents; they remain stored but are excluded. The minimum target of five qualifying new documents is still unmet. | Treat all publicly hosted lender PDFs as loan documents. |
