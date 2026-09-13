<!-- quiron:shared-quiz-me-evidence:start -->
4. When the user passes this vault's self-explain gate (correct or partial,
   according to the vault-specific grading rules), persist the explanation as
   Quiron evidence:
   - Save the user's explanation in the vault's normal explanation location.
   - Use a real vault-relative path for that explanation; never use a placeholder.
   - Run `uv run --directory C:\SANTIAGO\quiron quiron evidence --add --vault <this vault> --card <card_path> --kind explained --ref <explanation_path>`.
   - Add `--scope <scope>` when the explanation covers only part of the concept.
   - If no explanation file was written, do not record `explained` evidence.
   - If the card is not mapped to a concept, report that Quiron skipped the record.
<!-- quiron:shared-quiz-me-evidence:end -->
