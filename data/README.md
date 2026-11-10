# Assignment corpus — Income Tax (India)

Everything in this folder is committed to the repository **except one file**:

- `Income-tax-Act-1961_2026_2026-06-18_02-47-37_b9326c_en.pdf` (~171 MB) — the complete Income-tax Act 1961 as amended to 2026.

It exceeds GitHub's 100 MB file limit, so it is attached as an asset of a **GitHub Release** in this repository.

## Get it in one step

1. Open this repository's **Releases** page (`https://github.com/BITSSAP2025AugAPIBP3Sections/VoiceBotAssignment/releases`).
2. Download the asset matching the filename above.
3. Place it **in this `data/` folder** (keep the exact filename).

`python src/rag/ingest.py` picks up every `*.pdf` present here — it works with or without the big Act file, but without it your bot loses the full Act text, which is needed for sections 80C, 115BBH, 194S, 206C, 112A, and residential-status questions in the official test bank.
