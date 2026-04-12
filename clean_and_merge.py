#!/usr/bin/env python3
"""
Skin Master SLM — Clean, Filter, Standardise & Merge Pipeline
Lead ML Data Engineer

Reads every .jsonl from raw_data/, applies schema normalisation,
domain filtering, and deduplication, then writes a single
processed_data/skin_master_training_data.jsonl ready for fine-tuning.

Usage:
    python clean_and_merge.py
"""

import os
import json

# ── Directory / file config ───────────────────────────────────────────────────
RAW_DATA_DIR   = "raw_data"
OUTPUT_DIR     = "processed_data"
OUTPUT_FILE    = os.path.join(OUTPUT_DIR, "skin_master_training_data.jsonl")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Domain keyword filter ─────────────────────────────────────────────────────
# Applied to the "general" medical files to extract only skin-relevant rows.
# Extend this list freely — the more specific, the higher signal your data.
SKIN_KEYWORDS = [
    # Anatomy & physiology
    "skin", "epidermis", "dermis", "hypodermis", "sebum", "sebaceous",
    "melanin", "melanocyte", "keratin", "keratinocyte", "collagen",
    "elastin", "pore", "follicle", "sweat gland",
    # Common conditions
    "acne", "eczema", "psoriasis", "rosacea", "dermatitis", "rash",
    "hives", "urticaria", "vitiligo", "alopecia", "dandruff",
    "seborrhea", "impetigo", "cellulitis", "folliculitis",
    "carbuncle", "furuncle", "abscess", "wart", "verruca",
    "molluscum", "herpes", "shingles", "ringworm", "tinea",
    "scabies", "lice", "pediculosis", "sunburn", "photosensitivity",
    # Cosmetic / formulation
    "moisturizer", "moisturiser", "sunscreen", "spf", "retinol",
    "retinoid", "niacinamide", "hyaluronic", "ceramide", "peptide",
    "exfoliant", "aha", "bha", "glycolic", "salicylic", "lactic acid",
    "toner", "serum", "cleanser", "emollient", "humectant", "occlusive",
    "comedogenic", "non-comedogenic", "dimethicone", "glycerin",
    "zinc oxide", "titanium dioxide",
    # Clinical / procedural
    "dermatology", "dermatologist", "dermatologic", "biopsy",
    "excision", "cryotherapy", "phototherapy", "laser", "botox",
    "filler", "chemical peel", "microdermabrasion", "patch test",
    # Skin descriptors
    "itching", "pruritus", "erythema", "lesion", "macule", "papule",
    "pustule", "vesicle", "bulla", "nodule", "plaque", "scale",
    "crust", "ulcer", "scar", "keloid", "hyperpigmentation",
    "hypopigmentation", "wrinkle", "fine line", "puffiness",
]

# Lower-case set for O(1) substring matching
SKIN_KEYWORDS_LOWER = [kw.lower() for kw in SKIN_KEYWORDS]

# ── Files that are 100 % domain-specific — keep every row ────────────────────
DOMAIN_SPECIFIC_FILES = {
    "Mreeb_Dermatology_QA.jsonl",
    "Kingabz_Dermatology_QA.jsonl",
    "Cosmetic_Ingredients.jsonl",
}

# ── Files that need keyword filtering ────────────────────────────────────────
FILTER_REQUIRED_FILES = {
    "MedQuad_MedicalQnA.jsonl",
    "Wiki_Medical_Terms.jsonl",
    "MedAlpaca_WikiDoc.jsonl",
    # Safety net: any file not in DOMAIN_SPECIFIC_FILES gets filtered
}


# ─────────────────────────────────────────────────────────────────────────────
# Schema normalisation
# ─────────────────────────────────────────────────────────────────────────────
# Priority-ordered key candidates for each target field.
# The extractor walks the list and returns the first non-empty value found.

INSTRUCTION_KEYS = [
    "instruction", "question", "input", "query",
    "term",          # Wiki_Medical_Terms
    "title",         # WikiDoc articles
    "ingredient",    # Cosmetic_Ingredients
    "word",
    "prompt",
    "problem",
]

OUTPUT_KEYS = [
    "output", "answer", "response", "solution",
    "definition",    # Wiki_Medical_Terms
    "content",       # WikiDoc articles
    "description",   # Cosmetic_Ingredients
    "explanation",
    "text",
    "reply",
]


def extract_field(row: dict, key_candidates: list[str]) -> str:
    """
    Walk `key_candidates` in priority order and return the first non-empty
    string value found in `row`.  Returns "" if nothing matches.
    """
    for key in key_candidates:
        value = row.get(key, "")
        if isinstance(value, str) and value.strip():
            return value.strip()
        # Some datasets nest the answer inside a list or dict — flatten safely
        if isinstance(value, list) and value:
            flat = " ".join(str(v) for v in value if v)
            if flat.strip():
                return flat.strip()
    return ""


def normalise(row: dict) -> dict | None:
    """
    Convert an arbitrary raw row into the canonical
    {"instruction": "...", "output": "..."} schema.
    Returns None if either field is empty after extraction.
    """
    instruction = extract_field(row, INSTRUCTION_KEYS)
    output      = extract_field(row, OUTPUT_KEYS)

    if not instruction or not output:
        return None

    return {"instruction": instruction, "output": output}


# ─────────────────────────────────────────────────────────────────────────────
# Keyword filter
# ─────────────────────────────────────────────────────────────────────────────

def is_skin_relevant(record: dict) -> bool:
    """
    Return True if either the instruction or output contains at least one
    dermatology / skincare keyword (case-insensitive substring match).
    """
    haystack = (record["instruction"] + " " + record["output"]).lower()
    return any(kw in haystack for kw in SKIN_KEYWORDS_LOWER)


# ─────────────────────────────────────────────────────────────────────────────
# Per-file processing
# ─────────────────────────────────────────────────────────────────────────────

def process_file(
    filepath: str,
    filename: str,
    seen_instructions: set,
    out_fh,
) -> tuple[int, int, int]:
    """
    Stream-process a single .jsonl file.

    Returns (kept, dropped_schema, dropped_filter, dropped_dupe)
    as a 4-tuple so the caller can log per-file stats.
    """
    kept             = 0
    dropped_schema   = 0   # could not extract instruction / output
    dropped_filter   = 0   # failed keyword filter
    dropped_dupe     = 0   # duplicate instruction

    needs_filter = filename not in DOMAIN_SPECIFIC_FILES

    with open(filepath, "r", encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            # ── Parse JSON ───────────────────────────────────────────────
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError:
                dropped_schema += 1
                continue

            # ── Schema normalisation ─────────────────────────────────────
            record = normalise(row)
            if record is None:
                dropped_schema += 1
                continue

            # ── Keyword filter (general medical files only) ──────────────
            if needs_filter and not is_skin_relevant(record):
                dropped_filter += 1
                continue

            # ── Deduplication (exact instruction match) ───────────────────
            instr_key = record["instruction"].lower()
            if instr_key in seen_instructions:
                dropped_dupe += 1
                continue

            seen_instructions.add(instr_key)

            # ── Write canonical row ──────────────────────────────────────
            out_fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            kept += 1

    return kept, dropped_schema, dropped_filter, dropped_dupe


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 68)
    print("  Skin Master — Clean, Filter & Merge Pipeline")
    print(f"  Input  : {os.path.abspath(RAW_DATA_DIR)}/")
    print(f"  Output : {os.path.abspath(OUTPUT_FILE)}")
    print("=" * 68)

    # Discover all .jsonl files in raw_data/
    all_files = sorted(
        f for f in os.listdir(RAW_DATA_DIR) if f.endswith(".jsonl")
    )

    if not all_files:
        print(f"\n⚠  No .jsonl files found in '{RAW_DATA_DIR}/'. Exiting.")
        return

    print(f"\n  Found {len(all_files)} file(s) to process.\n")

    # Shared deduplication state across ALL files
    seen_instructions: set[str] = set()

    # Aggregate counters
    total_kept           = 0
    total_drop_schema    = 0
    total_drop_filter    = 0
    total_drop_dupe      = 0

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_fh:
        for filename in all_files:
            filepath     = os.path.join(RAW_DATA_DIR, filename)
            filter_label = "✦ FULL KEEP" if filename in DOMAIN_SPECIFIC_FILES \
                           else "⊛ FILTERED"

            print(f"  ┌─ {filename}  [{filter_label}]")

            kept, d_schema, d_filter, d_dupe = process_file(
                filepath, filename, seen_instructions, out_fh
            )

            total_in = kept + d_schema + d_filter + d_dupe
            print(f"  │   Rows in          : {total_in:>7,}")
            print(f"  │   ✅  Kept          : {kept:>7,}")
            print(f"  │   ✗  Bad schema    : {d_schema:>7,}")
            print(f"  │   ✗  Off-topic     : {d_filter:>7,}")
            print(f"  │   ✗  Duplicate     : {d_dupe:>7,}")
            print(f"  └─ ──────────────────────────────\n")

            total_kept        += kept
            total_drop_schema += d_schema
            total_drop_filter += d_filter
            total_drop_dupe   += d_dupe

    # ── Final summary ─────────────────────────────────────────────────────────
    grand_total = total_kept + total_drop_schema + total_drop_filter + total_drop_dupe
    retention   = (total_kept / grand_total * 100) if grand_total else 0

    print("=" * 68)
    print("  PIPELINE COMPLETE — FINAL SUMMARY")
    print("=" * 68)
    print(f"  Total rows ingested      : {grand_total:>8,}")
    print(f"  ✅  Rows kept (clean)    : {total_kept:>8,}  ({retention:.1f}%)")
    print(f"  ✗  Dropped — schema      : {total_drop_schema:>8,}")
    print(f"  ✗  Dropped — off-topic   : {total_drop_filter:>8,}")
    print(f"  ✗  Dropped — duplicate   : {total_drop_dupe:>8,}")
    print("-" * 68)
    print(f"  Output file              : {OUTPUT_FILE}")
    print(f"  Unique instructions      : {len(seen_instructions):>8,}")
    print("=" * 68)
    print("  Next step: tokenise + split into train/eval sets.")
    print("=" * 68)


if __name__ == "__main__":
    main()