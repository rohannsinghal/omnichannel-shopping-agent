#!/usr/bin/env python3
"""
Skin Master SLM — Raw Data Acquisition Script
Lead ML Data Engineer: Batch download of open-source dermatology,
skincare, and cosmetic datasets from Hugging Face.

Usage:
    pip install datasets huggingface_hub
    python download_datasets.py
"""

import os
import json
from datasets import load_dataset

# ── Output directory ──────────────────────────────────────────────────────────
RAW_DATA_DIR = "raw_data"
os.makedirs(RAW_DATA_DIR, exist_ok=True)

# ── Dataset registry ──────────────────────────────────────────────────────────
# Each entry:
#   "id"      : HuggingFace dataset identifier
#   "split"   : which split to pull ('train', 'all', etc.)
#   "filename": output .jsonl filename inside raw_data/
#   "note"    : why this dataset is relevant to Skin Master
#
# Additional high-value datasets added beyond the original brief:
#   • gamino/wiki_medical_terms          — Medical terminology backbone
#   • lavita/medical-qa-datasets         — Broad medical QA corpus
#   • medalpaca/medical_meadow_wikidoc   — WikiDoc medical knowledge
#   • Mohammed-Altaf/medical-qa-150k     — Large medical QA for coverage
#   • Dataset-Skin-Lesion (ISIC-aligned) — Clinical lesion descriptions

DATASETS = [
    # ── Core dermatology / skincare targets ───────────────────────────────
    {
        "id": "Mreeb/Dermatology-Question-Answer-Dataset-For-Fine-Tuning",
        "split": "train",
        "filename": "Mreeb_Dermatology_QA.jsonl",
        "note": "Primary derm QA fine-tuning corpus",
    },
    {
        "id": "kingabzpro/dermatology-qa-firecrawl-dataset",
        "split": "train",
        "filename": "Kingabz_Dermatology_QA.jsonl",
        "note": "Web-crawled dermatology QA pairs",
    },
    {
        "id": "yavuzyilmaz/cosmetic-ingredients",
        "split": "train",
        "filename": "Cosmetic_Ingredients.jsonl",
        "note": "Cosmetic ingredient data for cosmetic-chemist persona",
    },
    {
        "id": "keivalya/MedQuad-MedicalQnADataset",
        "split": "train",
        "filename": "MedQuad_MedicalQnA.jsonl",
        "note": "Broad medical QA — will be filtered for skin in later step",
    },
    # ── Supplementary high-value additions ───────────────────────────────
    {
        "id": "gamino/wiki_medical_terms",
        "split": "train",
        "filename": "Wiki_Medical_Terms.jsonl",
        "note": "Medical terminology definitions — strong dermatology vocabulary base",
    },
    {
        "id": "medalpaca/medical_meadow_wikidoc",
        "split": "train",
        "filename": "MedAlpaca_WikiDoc.jsonl",
        "note": "WikiDoc medical knowledge — covers skin conditions extensively",
    },
    {
        "id": "Mohammed-Altaf/medical-qa-150k",
        "split": "train",
        "filename": "Medical_QA_150k.jsonl",
        "note": "Large-scale medical QA for general coverage and rare conditions",
    },
    {
        "id": "lavita/medical-qa-datasets",
        "split": "train",
        "filename": "Lavita_Medical_QA.jsonl",
        "note": "Aggregated medical QA — diverse question styles for robustness",
    },
]

# ── Helper: save a HuggingFace Dataset to .jsonl ──────────────────────────────
def save_as_jsonl(hf_dataset, filepath: str) -> int:
    """
    Serialize every row of a HuggingFace Dataset object to a .jsonl file.
    Returns the total number of rows written.
    """
    rows_written = 0
    with open(filepath, "w", encoding="utf-8") as fh:
        for row in hf_dataset:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows_written += 1
    return rows_written


# ── Helper: resolve the best available split ──────────────────────────────────
def resolve_split(dataset_dict, preferred: str = "train"):
    """
    Return the preferred split if it exists, otherwise fall back to the
    first available split. Handles datasets that only expose 'test' etc.
    """
    available = list(dataset_dict.keys())
    if preferred in available:
        return dataset_dict[preferred]
    print(f"    ⚠  Split '{preferred}' not found. Available: {available}")
    fallback = available[0]
    print(f"    ↳  Falling back to split: '{fallback}'")
    return dataset_dict[fallback]


# ── Main download loop ────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("  Skin Master — Raw Dataset Acquisition")
    print(f"  Output directory : {os.path.abspath(RAW_DATA_DIR)}")
    print(f"  Datasets queued  : {len(DATASETS)}")
    print("=" * 65)

    summary = []  # collect (filename, rows | error) for final report

    for idx, entry in enumerate(DATASETS, start=1):
        ds_id    = entry["id"]
        filename = entry["filename"]
        note     = entry["note"]
        split    = entry["split"]
        out_path = os.path.join(RAW_DATA_DIR, filename)

        print(f"\n[{idx}/{len(DATASETS)}] {ds_id}")
        print(f"  Purpose : {note}")
        print(f"  Output  : {out_path}")

        try:
            # load_dataset returns a DatasetDict (split-keyed) by default
            dataset_dict = load_dataset(ds_id, trust_remote_code=True)
            hf_split     = resolve_split(dataset_dict, preferred=split)

            rows = save_as_jsonl(hf_split, out_path)
            print(f"  ✅  Success — {rows:,} rows saved.")
            summary.append((filename, rows, None))

        except ValueError as exc:
            # Raised when a dataset needs a specific config name
            msg = f"ValueError — possibly needs a config arg: {exc}"
            print(f"  ❌  {msg}")
            summary.append((filename, 0, msg))

        except FileNotFoundError as exc:
            msg = f"Dataset not found on HuggingFace Hub: {exc}"
            print(f"  ❌  {msg}")
            summary.append((filename, 0, msg))

        except PermissionError as exc:
            # Gated datasets without a valid HF token
            msg = f"Gated / private dataset — HF token required: {exc}"
            print(f"  ❌  {msg}")
            summary.append((filename, 0, msg))

        except Exception as exc:  # noqa: BLE001
            # Catch-all so one bad dataset never halts the pipeline
            msg = f"{type(exc).__name__}: {exc}"
            print(f"  ❌  Unexpected error — skipping. {msg}")
            summary.append((filename, 0, msg))

    # ── Final summary table ───────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  DOWNLOAD SUMMARY")
    print("=" * 65)
    total_rows = 0
    for fname, rows, err in summary:
        if err:
            print(f"  ✗  {fname:<45}  ERROR")
        else:
            print(f"  ✓  {fname:<45}  {rows:>10,} rows")
            total_rows += rows

    succeeded = sum(1 for _, _, e in summary if e is None)
    failed    = len(summary) - succeeded
    print("-" * 65)
    print(f"  Datasets succeeded : {succeeded} / {len(DATASETS)}")
    print(f"  Datasets failed    : {failed}")
    print(f"  Total rows on disk : {total_rows:,}")
    print("=" * 65)
    print("  Next step: run the cleaning + merge pipeline on raw_data/")
    print("=" * 65)


if __name__ == "__main__":
    main()