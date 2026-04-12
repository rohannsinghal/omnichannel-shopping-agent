#!/usr/bin/env python3
"""
merge_and_clean.py
------------------
Lead ML Data Engineer script for the Skin Master SLM training pipeline.

Responsibilities:
  1. Load and write File 1 (medical foundation) as-is.
  2. Load File 2 (conversational tone), strip ChatGPT citation artifacts via regex,
     and write each row 3× (oversampling to anchor conversational tone).
  3. Log row counts, removed-tag counts, and final output size.
"""

import json
import re

# ── Path Configuration ────────────────────────────────────────────────────────

FILE_1_PATH = "/Users/admin/omnichannel-agent/processed_data/skin_master_training_data.jsonl"
FILE_2_PATH = "/Users/admin/omnichannel-agent/raw_data/gpt_scraped_sq.jsonl"
OUTPUT_PATH = "/Users/admin/omnichannel-agent/merged_skin_data.jsonl"

OVERSAMPLE_FACTOR = 3  # Number of times File 2 rows are written

# ── Regex Pattern ─────────────────────────────────────────────────────────────

# Matches ChatGPT citation artifacts of the form:
#   :contentReference[oaicite:19]{index=19}
# along with any surrounding whitespace so no double-spaces are left behind.
CITATION_PATTERN = re.compile(
    r'\s*:contentReference\[oaicite:\d+\]\{index=\d+\}\s*'
)


def clean_output_field(text: str) -> tuple[str, int]:
    """
    Remove all ChatGPT citation artifacts from a string.

    Args:
        text: The raw `output` field value from File 2.

    Returns:
        A tuple of (cleaned_text, number_of_tags_removed).
    """
    matches = CITATION_PATTERN.findall(text)
    tags_removed = len(matches)
    cleaned = CITATION_PATTERN.sub(" ", text).strip()
    # Collapse any runs of multiple spaces left after substitution
    cleaned = re.sub(r' {2,}', ' ', cleaned)
    return cleaned, tags_removed


def load_jsonl(filepath: str) -> list[dict]:
    """
    Read a JSONL file and return a list of parsed JSON objects.
    Skips blank lines silently.

    Args:
        filepath: Absolute path to the .jsonl file.

    Returns:
        List of dicts, one per valid line.
    """
    records = []
    with open(filepath, "r", encoding="utf-8") as fh:
        for line_num, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"  [WARN] Skipping malformed JSON at line {line_num}: {exc}")
    return records


# ── Main Pipeline ─────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  Skin Master SLM — merge_and_clean.py")
    print("=" * 60)

    total_tags_removed = 0
    total_rows_written = 0

    with open(OUTPUT_PATH, "w", encoding="utf-8") as out_fh:

        # ── Step 1: Medical Foundation (File 1) ──────────────────────────────
        print(f"\n[1/2] Loading medical foundation data …\n      {FILE_1_PATH}")
        file1_records = load_jsonl(FILE_1_PATH)
        file1_count = len(file1_records)

        for record in file1_records:
            out_fh.write(json.dumps(record, ensure_ascii=False) + "\n")

        total_rows_written += file1_count
        print(f"      ✔  {file1_count:,} rows written (1×, no modifications)")

        # ── Step 2: Conversational Tone (File 2) — clean + oversample ────────
        print(f"\n[2/2] Loading conversational tone data …\n      {FILE_2_PATH}")
        file2_records = load_jsonl(FILE_2_PATH)
        file2_count = len(file2_records)

        cleaned_records = []
        for record in file2_records:
            if "output" in record and isinstance(record["output"], str):
                cleaned_text, n_removed = clean_output_field(record["output"])
                record["output"] = cleaned_text
                total_tags_removed += n_removed
            cleaned_records.append(record)

        # Write each cleaned record OVERSAMPLE_FACTOR times
        for _ in range(OVERSAMPLE_FACTOR):
            for record in cleaned_records:
                out_fh.write(json.dumps(record, ensure_ascii=False) + "\n")

        file2_written = file2_count * OVERSAMPLE_FACTOR
        total_rows_written += file2_written
        print(f"      ✔  {file2_count:,} rows cleaned and written {OVERSAMPLE_FACTOR}× "
              f"= {file2_written:,} rows")

    # ── Step 3: Validation Report ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  PIPELINE SUMMARY")
    print("=" * 60)
    print(f"  File 1 rows processed   : {file1_count:>8,}")
    print(f"  File 2 rows processed   : {file2_count:>8,}")
    print(f"  Citation tags removed   : {total_tags_removed:>8,}")
    print(f"  Oversample factor       : {OVERSAMPLE_FACTOR:>8}×")
    print(f"  Total rows in output    : {total_rows_written:>8,}")
    print(f"  Output file             : {OUTPUT_PATH}")

    if total_tags_removed == 0:
        print("\n  [INFO] No citation tags found — File 2 may already be clean,")
        print("         or the pattern did not match. Double-check a sample row.")
    else:
        print(f"\n  [OK] Regex cleaning confirmed: {total_tags_removed:,} artifact(s) stripped.")

    print("=" * 60)
    print("  Done. Training file is ready.\n")


if __name__ == "__main__":
    main()