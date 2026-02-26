---
name: jp-furigana-review-fix
description: Review and repair missing furigana annotations in Japanese vocabulary JSON files (especially examples[].ja / examples[].japanese). Use when Codex needs to (1) run an automated furigana audit script, (2) list and track annotation errors, (3) search for each problematic keyword/context, and (4) patch files iteratively with re-audits until clean.
---

# JP Furigana Review & Fix Workflow

Use this skill to run a repeatable loop: **scan -> inspect -> search -> fix -> rescan**.

## Quick Start

1. Run the audit script on one file or a full level directory.
2. Save machine-readable findings to a JSON report file.
3. For each error, search target JSON by expression/context before editing.
4. Patch only the affected example sentence(s).
5. Re-run the audit script; repeat until errors are 0.

## Commands

- Single file audit:
  - `python3 skills/jp-furigana-review-fix/scripts/review_furigana_json.py new_word/N3/word_n3_part01.json --output /tmp/n3_part01_furigana_report.json`
- Directory audit:
  - `python3 skills/jp-furigana-review-fix/scripts/review_furigana_json.py new_word/N3 --output /tmp/n3_all_furigana_report.json`

If you lose track during editing, run the same command again to refresh the error list.

## Repair Loop (strict order)

1. **Audit**
   - Run script and read summary + detailed errors.
   - Keep the output JSON report path for recovery.
2. **Prioritize**
   - Group by file -> entry_idx/expression -> example_idx.
3. **Search Before Edit**
   - Use `rg` with the expression or a short context snippet from `full_text`.
   - Confirm exact sentence location in the target JSON.
4. **Patch**
   - Add furigana using `漢字[かな]` style.
   - Preserve existing JSON structure and punctuation.
5. **Re-audit**
   - Re-run script on edited file(s).
   - Stop only when `total_errors == 0` for intended scope.

## Annotation Rule Enforced by Script

- Any kanji character (`[一-龥々〆〤]`) not covered by an annotation block `漢字[かな]` is flagged.
- Existing annotated chunks are considered valid and skipped.
- Detection scope is `examples[].ja` then fallback `examples[].japanese`.

## Resources

- Script: `scripts/review_furigana_json.py`
- Report schema and troubleshooting: `references/report-format.md`
